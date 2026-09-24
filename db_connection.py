import os

import mysql.connector
import streamlit as st


def _database_setting(secret_name, environment_name, default=None):
    """Read Streamlit secrets first, with an environment-variable fallback."""
    try:
        return st.secrets["mysql"][secret_name]
    except (FileNotFoundError, KeyError):
        value = os.getenv(environment_name, default)
        if value is None:
            raise RuntimeError(
                f"Missing database setting '{secret_name}'. "
                "Add .streamlit/secrets.toml or set database environment variables."
            )
        return value


def get_connection():
    return mysql.connector.connect(
        host=_database_setting("host", "DB_HOST", "localhost"),
        user=_database_setting("user", "DB_USER"),
        password=_database_setting("password", "DB_PASSWORD"),
        database=_database_setting("database", "DB_NAME", "hotel_management_system"),
    )
