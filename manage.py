"""Database setup and one-time copy from the original local MySQL database."""

import argparse
from contextlib import closing
import os
from pathlib import Path
import re
import sys
import tomllib

import mysql.connector

from db_connection import ConfigurationError, get_connection

TABLES = ("hotels","persons","guests","staff_roles","staff","room_types","rooms",
          "bookings","booking_rooms","payments","reviews")
ROOT = Path(__file__).resolve().parent


def table_names(connection):
    with closing(connection.cursor()) as cursor:
        cursor.execute("SHOW TABLES")
        return {row[0] for row in cursor.fetchall()}


def check_database(connection):
    missing = set(TABLES)-table_names(connection)
    if missing:
        raise ValueError("Missing application tables: " + ", ".join(sorted(missing)))


def initialize_database(connection):
    if table_names(connection):
        raise ValueError("Initialization requires an empty database. Existing tables were left untouched.")
    with closing(connection.cursor()) as cursor:
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        if "tidb" in version.lower():
            cursor.execute("SET GLOBAL tidb_enable_check_constraint = ON")
        schema = re.sub(r"--[^\n]*", "", (ROOT/"schema.mysql.sql").read_text())
        # This schema contains only simple CREATE TABLE/INDEX statements.
        for statement in schema.split(";"):
            if statement.strip():
                cursor.execute(statement)
    check_database(connection)


def copy_data(source, target):
    """Copy all eleven tables in one target transaction, preserving primary keys."""
    check_database(source)
    check_database(target)
    counts = {}
    source.start_transaction(consistent_snapshot=True, readonly=True)
    try:
        target.start_transaction()
        try:
            with closing(target.cursor()) as writer:
                for table in TABLES:
                    writer.execute(f"SELECT COUNT(*) FROM `{table}`")
                    if writer.fetchone()[0]:
                        raise ValueError("The target must have empty application tables. No records were copied.")
                for table in TABLES:
                    with closing(source.cursor()) as reader:
                        reader.execute(f"SELECT * FROM `{table}`")
                        columns = [item[0] for item in reader.description]
                        if not all(re.fullmatch(r"[a-zA-Z0-9_]+",column) for column in columns):
                            raise ValueError("Unexpected source column name.")
                        column_sql = ",".join(f"`{column}`" for column in columns)
                        placeholders = ",".join(["%s"]*len(columns))
                        insert = f"INSERT INTO `{table}` ({column_sql}) VALUES ({placeholders})"
                        counts[table] = 0
                        while batch := reader.fetchmany(250):
                            writer.executemany(insert,batch)
                            counts[table] += len(batch)
                for table in TABLES:
                    writer.execute(f"SELECT COUNT(*) FROM `{table}`")
                    if writer.fetchone()[0] != counts[table]:
                        raise ValueError("Row counts did not match. The copy was rolled back.")
            target.commit()
        except BaseException:
            target.rollback()
            raise
    finally:
        # Read-only snapshot: never commit changes to the source.
        source.rollback()
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=["check-db","init-db","copy-local-data"])
    parser.add_argument("--source-secrets",type=Path,help="Original local .streamlit/secrets.toml; used only as the data source.")
    args = parser.parse_args()
    if args.command in {"init-db","copy-local-data"} and not os.environ.get("MYSQL_HOST"):
        parser.error("Set MYSQL_* environment variables for the target database first.")
    try:
        with closing(get_connection()) as target:
            if args.command == "check-db":
                check_database(target)
                print("Connected successfully. All 11 application tables are present.")
            elif args.command == "init-db":
                initialize_database(target)
                print("Created all 11 application tables. No existing tables were deleted.")
            else:
                if not args.source_secrets:
                    parser.error("copy-local-data requires --source-secrets.")
                with args.source_secrets.open("rb") as handle:
                    source_settings = tomllib.load(handle)["mysql"]
                settings = {key:source_settings[key] for key in ["host","user","password","database"]}
                settings.update(port=int(source_settings.get("port",3306)),autocommit=True,connection_timeout=10)
                with closing(mysql.connector.connect(**settings)) as source:
                    counts = copy_data(source,target)
                print("Data copied and row counts verified. The source was read only.")
                for table,count in counts.items():
                    print(f"{table}: {count} rows")
    except mysql.connector.Error as exc:
        print(f"Database operation failed (error {exc.errno}). Check settings and permissions. No credentials are printed.",file=sys.stderr)
        return 1
    except (ConfigurationError,ValueError,KeyError,OSError) as exc:
        print(str(exc),file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
