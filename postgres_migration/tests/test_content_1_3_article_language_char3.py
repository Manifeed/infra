from __future__ import annotations

import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "content"
    / "1_3_article_language_char3.py"
)


def _load_migration_module():
    spec = importlib.util.spec_from_file_location("content_1_3_article_language_char3", MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load migration module from {MIGRATION_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_article_language_char3_migration_upgrade_and_downgrade(monkeypatch) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE articles (
                    article_id INTEGER PRIMARY KEY,
                    language CHAR(2) NOT NULL DEFAULT 'xx'
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO articles (article_id, language)
                VALUES (1, 'en'), (2, 'xx')
                """
            )
        )

        module = _load_migration_module()
        operations = Operations(MigrationContext.configure(connection))
        monkeypatch.setattr(module, "op", operations)

        module.upgrade()

        inspector = inspect(connection)
        upgraded_column = next(column for column in inspector.get_columns("articles") if column["name"] == "language")
        assert getattr(upgraded_column["type"], "length", None) == 3

        connection.execute(text("UPDATE articles SET language = 'arz' WHERE article_id = 2"))

        module.downgrade()

        inspector = inspect(connection)
        downgraded_column = next(column for column in inspector.get_columns("articles") if column["name"] == "language")
        downgraded_rows = connection.execute(
            text("SELECT article_id, language FROM articles ORDER BY article_id")
        ).mappings().all()
        assert getattr(downgraded_column["type"], "length", None) == 2
        assert downgraded_rows == [
            {"article_id": 1, "language": "en"},
            {"article_id": 2, "language": "xx"},
        ]
