from __future__ import annotations

import os
import subprocess

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url


TARGETS = (
    ("content", "CONTENT_DATABASE_URL", "alembic_content.ini"),
    ("identity", "IDENTITY_DATABASE_URL", "alembic_identity.ini"),
    ("workers", "WORKERS_DATABASE_URL", "alembic_workers.ini"),
)


def main() -> None:
    for _, env_name, config_file in TARGETS:
        database_url = _require_env(env_name)
        _ensure_database(database_url)
        env = {
            **os.environ,
            "DATABASE_URL": database_url,
        }
        subprocess.run(
            ["alembic", "-c", config_file, "upgrade", "head"],
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

    for admin_database in _admin_database_candidates(database_name):
        admin_url = url.set(database=admin_database, drivername="postgresql")
        connect_kwargs = {
            "host": admin_url.host,
            "port": admin_url.port or 5432,
            "dbname": admin_url.database,
            "user": admin_url.username,
            "password": admin_url.password,
            "autocommit": True,
        }
        try:
            with psycopg.connect(**connect_kwargs) as connection:
                exists = connection.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (database_name,),
                ).fetchone()
                if exists is not None:
                    return
                connection.execute(
                    sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name))
                )
                return
        except psycopg.OperationalError:
            continue
    raise RuntimeError(
        "Unable to connect to an administrative database to create "
        f"{database_name!r}. Checked: {', '.join(_admin_database_candidates(database_name))}"
    )


def _admin_database_candidates(database_name: str) -> list[str]:
    candidates = [
        os.getenv("POSTGRES_ADMIN_DATABASE", "").strip(),
        database_name,
        "postgres",
        "template1",
    ]
    return [candidate for index, candidate in enumerate(candidates) if candidate and candidate not in candidates[:index]]


if __name__ == "__main__":
    main()
