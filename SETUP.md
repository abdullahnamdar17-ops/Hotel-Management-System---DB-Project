# Set up TiDB Cloud and deploy the Flask app on Vercel

Deploy the Flask application in this repository using its existing GitHub
repository and a TiDB Cloud MySQL-compatible database.

## 1. Create your free online database

1. Sign up or sign in at https://tidbcloud.com/.
2. Create a **Starter** instance and select **MySQL-compatible** mode.
   Choose **AWS** as the cloud provider to use the built-in SQL Editor.
3. Choose the free option and keep the spending limit at **$0**. No credit card
   is required to start within the free allowance.
4. When the instance is ready, open **Connect** and choose the public endpoint.
   Copy its host, port, and complete username, and set or copy its password.
   Use the exact username, including any prefix shown by TiDB Cloud.
5. Open the instance's SQL Editor. Paste the entire contents of
   `schema.tidb.sql` and press **Shift + Command + Enter** on your Mac to run
   all statements together. It creates and selects the
   `hotel_management_system` database, enables TiDB CHECK constraints globally
   with `SET GLOBAL`, and creates all eleven original tables and their relationships.

Run this only for a new, empty database. The script has no DROP TABLE commands.
`schema.mysql.sql` is the equivalent portable schema without the TiDB settings.

The current free allowance for an eligible MySQL-compatible Starter instance is
5 GiB of row storage, 5 GiB of columnar storage, and 50 million Request Units per
month. At the free limit, access can be restricted until usage resets. Verify
the plan details shown by TiDB when creating the instance.

## 2. Create the Vercel project

Import this GitHub repository at https://vercel.com/new after the Flask changes
are merged into its production branch.

- Framework Preset: **Flask**
- Root Directory: the folder containing `app.py` and `requirements.txt`
- Build Command: leave unset
- Output Directory: leave unset
- Python: 3.12, selected by `.python-version`

`vercel.json` selects Flask. There is no Dockerfile in this edition.

## 3. Add Vercel environment variables

Set these under **Project Settings → Environment Variables** for Preview and
Production. Redeploy after setting or changing them.

| Name | Value |
| --- | --- |
| `MYSQL_HOST` | TiDB's public database hostname |
| `MYSQL_PORT` | The port in TiDB's connection details, commonly `4000` |
| `MYSQL_USER` | The complete username from TiDB |
| `MYSQL_PASSWORD` | The database password |
| `MYSQL_DATABASE` | `hotel_management_system` |
| `MYSQL_SSL_VERIFY` | `true` |
| `SECRET_KEY` | A random secret generated below |
| `ADMIN_PASSWORD` | Your chosen staff sign-in password |
| `APP_TIMEZONE` | `Asia/Karachi`, or your property's timezone |

Generate a session secret on your laptop:

```sh
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

The staff password is separate from the database password. After deployment,
staff enter `ADMIN_PASSWORD` on the sign-in page. Credentials belong in Vercel's
environment settings. The `.env.example` file lists settings for reference and
is not loaded automatically. The connector verifies TLS using a system or
Certifi CA bundle. A private-CA MySQL provider can additionally use the
`MYSQL_SSL_CA_PEM` environment variable.

The deployed app requires its staff password and stable session secret before
it serves operational pages. If either is missing, it shows a setup page.

## 4. Check your deployment

Open the deployment URL and sign in with your staff password. Check all pages.
Empty lists are expected if you have not copied data. Create a test property,
room type, room, guest, booking, payment, and checked-out booking review. Refresh
the browser to confirm records persist.

The `/health` endpoint checks that the web app is running; it does not verify
database connectivity. Opening the operational pages verifies database reads.

## 5. Optionally copy your current local records

If you want the existing hotel data online, copy it before allowing anyone to
use the new database. The target must contain the eleven tables with no records.
Do not add test records before copying real data.

On your laptop, set the same `MYSQL_*` environment variables from step 3 for the
target database. The hosted service must be selected through these variables.
The data-copy command reads the original local connection details separately:

```sh
python3 manage.py check-db
python3 manage.py copy-local-data --source-secrets "/path/to/original/.streamlit/secrets.toml"
```

Replace the source path with your original local credentials file. The command
reads the source using a consistent, read-only snapshot and copies all eleven
tables in one target transaction. It preserves IDs, checks row counts, and
refuses a target that already contains application records. The source database
is unchanged. The copy is not continuous synchronization: afterward, the local
and cloud apps use separate databases unless you deliberately configure both
to use the same hosted service.

As an alternative to using TiDB's SQL Editor for initial table setup, first
create the empty database in TiDB, configure the target `MYSQL_*` variables on
your laptop, and run:

```sh
python3 manage.py init-db
```

That command enables TiDB CHECK constraints, creates the schema, and refuses to
run in a database containing any tables. MySQL/TiDB DDL is not transactional;
inspect the empty database if a schema operation fails before retrying.

## References checked November 10, 2026

- TiDB free quota and compatibility modes:
  https://docs.pingcap.com/tidbcloud/select-cluster-tier/?compatibility=mysql&plan=starter
- TiDB connection instructions for MySQL Connector/Python:
  https://docs.pingcap.com/developer/dev-guide-sample-application-python-mysql-connector/
- TiDB CHECK constraints:
  https://docs.pingcap.com/tidb/stable/constraints/
- Vercel Flask entry point and static files:
  https://vercel.com/docs/frameworks/backend/flask
