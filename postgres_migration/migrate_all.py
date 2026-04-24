from __future__ import annotations

import os
import subprocess

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url


TARGETS = (
    ("content", "CONTENT_DATABASE_URL"),
    ("identity", "IDENTITY_DATABASE_URL"),
    ("workers", "WORKERS_DATABASE_URL"),
)


def main() -> None:
    for target, env_name in TARGETS:
        database_url = _require_env(env_name)
        _ensure_database(database_url)
        env = {
            **os.environ,
            "DATABASE_URL": database_url,
            "MIGRATION_TARGET": target,
        }
        subprocess.run(
            ["alembic", "-c", "alembic.ini", "upgrade", "head"],
            check=True,
            env=env,
        )


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _ensure_database(database_url: str) -> None:
    url = make_url(database_url)
    database_name = url.database
    if not database_name:
        raise RuntimeError(f"Database URL must include a database name: {database_url}")

    admin_url = url.set(database="postgres", drivername="postgresql")
    connect_kwargs = {
        "host": admin_url.host,
        "port": admin_url.port or 5432,
        "dbname": admin_url.database,
        "user": admin_url.username,
        "password": admin_url.password,
        "autocommit": True,
    }
    with psycopg.connect(**connect_kwargs) as connection:
        exists = connection.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (database_name,),
        ).fetchone()
        if exists is not None:
            return
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))


if __name__ == "__main__":
    main()
