"""MySQL connections for Flask and setup commands; no Streamlit dependency."""

import os
from pathlib import Path
import ssl
import tempfile
import tomllib

import certifi
import mysql.connector


class ConfigurationError(ValueError):
    pass


def boolean(value, name):
    value = str(value).strip().lower()
    if value in {"true", "1", "yes", "on"}:
        return True
    if value in {"false", "0", "no", "off"}:
        return False
    raise ConfigurationError(f"{name} must be true or false.")


def connection_settings():
    required = ("host", "user", "password", "database")
    deployed = os.environ.get("VERCEL") == "1"
    uses_environment = any(f"MYSQL_{key.upper()}" in os.environ for key in required)
    if uses_environment or deployed:
        missing = [f"MYSQL_{key.upper()}" for key in required
                   if f"MYSQL_{key.upper()}" not in os.environ]
        if missing:
            raise ConfigurationError("Set " + ", ".join(missing) + ".")
        settings = {key: os.environ[f"MYSQL_{key.upper()}"] for key in required}
        settings["port"] = os.environ.get("MYSQL_PORT", "3306")
        verify = os.environ.get("MYSQL_SSL_VERIFY", "true")
        if deployed and (not settings["password"] or settings["host"].lower() in {"localhost", "127.0.0.1", "::1"}):
            raise ConfigurationError("Vercel requires a hosted database and its password.")
    else:
        local_path = Path(os.environ.get("HMS_LOCAL_SECRETS_FILE", ".streamlit/secrets.toml"))
        try:
            with local_path.open("rb") as handle:
                local = tomllib.load(handle)["mysql"]
            settings = {key: local[key] for key in required}
            settings["port"] = local.get("port", 3306)
            verify = local.get("ssl_verify_cert", False)
        except (FileNotFoundError, KeyError) as exc:
            raise ConfigurationError("Configure the MYSQL_* variables or a local .streamlit/secrets.toml file.") from exc
    try:
        settings["port"] = int(settings["port"])
        if not 1 <= settings["port"] <= 65535:
            raise ValueError
    except (TypeError, ValueError) as exc:
        raise ConfigurationError("MYSQL_PORT must be between 1 and 65535.") from exc
    verify = boolean(verify, "MYSQL_SSL_VERIFY")
    if deployed and not verify:
        raise ConfigurationError("Keep MYSQL_SSL_VERIFY=true on Vercel.")
    settings.update(ssl_verify_cert=verify, ssl_verify_identity=verify,
                    connection_timeout=10, autocommit=True, charset="utf8mb4",
                    collation="utf8mb4_unicode_ci")
    if verify:
        settings["ssl_ca"] = ssl.get_default_verify_paths().cafile or certifi.where()
    return settings


def get_connection():
    settings = connection_settings()
    certificate = os.environ.get("MYSQL_SSL_CA_PEM")
    if certificate:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", encoding="utf-8") as handle:
            handle.write(certificate)
            handle.flush()
            settings["ssl_ca"] = handle.name
            return mysql.connector.connect(**settings)
    return mysql.connector.connect(**settings)
