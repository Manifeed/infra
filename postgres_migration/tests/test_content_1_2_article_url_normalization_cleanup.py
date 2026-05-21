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
    / "1_2_article_url_normalization_cleanup.py"
)


def _load_migration_module():
    spec = importlib.util.spec_from_file_location("content_1_2_article_url_normalization_cleanup", MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load migration module from {MIGRATION_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_article_url_cleanup_migration_upgrade_and_downgrade(monkeypatch) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE articles (article_id INTEGER PRIMARY KEY)"))
        connection.execute(text("INSERT INTO articles (article_id) VALUES (1), (2)"))
        connection.execute(
            text(
                """
                CREATE TABLE article_url (
                    article_url_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article_id INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    normalized_url TEXT NOT NULL UNIQUE,
                    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        connection.execute(text("CREATE INDEX idx_article_url_article_id ON article_url (article_id)"))
        connection.execute(
            text(
                """
                INSERT INTO article_url (article_id, url, normalized_url)
                VALUES
                    (1, 'https://example.com/a?utm_source=rss', 'https://example.com/a'),
                    (2, 'https://example.com/b?utm_source=rss', 'https://example.com/b')
                """
            )
        )

        module = _load_migration_module()
        operations = Operations(MigrationContext.configure(connection))
        monkeypatch.setattr(module, "op", operations)

        module.upgrade()

        inspector = inspect(connection)
        upgraded_columns = {column["name"] for column in inspector.get_columns("article_url")}
        upgraded_rows = connection.execute(
            text("SELECT article_id, url FROM article_url ORDER BY url")
        ).mappings().all()
        assert upgraded_columns == {"article_id", "url", "first_seen_at"}
        assert inspector.get_pk_constraint("article_url")["constrained_columns"] == ["url"]
        assert any(index["name"] == "idx_article_url_article_id" for index in inspector.get_indexes("article_url"))
        assert upgraded_rows == [
            {"article_id": 1, "url": "https://example.com/a"},
            {"article_id": 2, "url": "https://example.com/b"},
        ]

        module.downgrade()

        inspector = inspect(connection)
        downgraded_columns = {column["name"] for column in inspector.get_columns("article_url")}
        downgraded_rows = connection.execute(
            text("SELECT article_id, url, normalized_url FROM article_url ORDER BY article_url_id")
        ).mappings().all()
        assert downgraded_columns == {"article_url_id", "article_id", "url", "normalized_url", "first_seen_at"}
        assert inspector.get_pk_constraint("article_url")["constrained_columns"] == ["article_url_id"]
        assert any(index["name"] == "idx_article_url_article_id" for index in inspector.get_indexes("article_url"))
        assert downgraded_rows == [
            {"article_id": 1, "url": "https://example.com/a", "normalized_url": "https://example.com/a"},
            {"article_id": 2, "url": "https://example.com/b", "normalized_url": "https://example.com/b"},
        ]
