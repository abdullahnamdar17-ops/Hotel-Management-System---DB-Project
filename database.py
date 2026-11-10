"""One connection per request and explicit transactions for each write."""

from contextlib import contextmanager

from flask import current_app, g

from db_connection import get_connection


def get_db():
    if "database" not in g:
        factory = current_app.config.get("DATABASE_CONNECT") or get_connection
        g.database = factory()
    return g.database


def query(sql, params=(), *, one=False):
    cursor = get_db().cursor(dictionary=True, buffered=True)
    try:
        cursor.execute(sql, tuple(params))
        return cursor.fetchone() if one else cursor.fetchall()
    finally:
        cursor.close()


def execute(sql, params=()):
    cursor = get_db().cursor(buffered=True)
    try:
        cursor.execute(sql, tuple(params))
        return cursor.lastrowid
    finally:
        cursor.close()


@contextmanager
def transaction():
    connection = get_db()
    connection.start_transaction()
    try:
        yield
        connection.commit()
    except BaseException:
        connection.rollback()
        raise


def close_db(_error=None):
    connection = g.pop("database", None)
    if connection is not None:
        connection.close()
