"""add source search indexes for content database

Revision ID: 1_4
Revises: 1_3
Create Date: 2026-05-06 00:00:00.000000

"""

from __future__ import annotations

import os

from alembic import op
import sqlalchemy as sa


revision = "1_4"
down_revision = "1_3"
branch_labels = None
depends_on = None


def _target() -> str:
    return os.getenv("MIGRATION_TARGET", "content").strip().lower()


def upgrade() -> None:
    if _target() != "content":
        return
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_articles_search_text_gin
            ON articles
            USING GIN (
                to_tsvector('simple', COALESCE(title, '') || ' ' || COALESCE(summary, ''))
            )
            """
        )
    )
    op.create_index(
        "idx_articles_language_published_at",
        "articles",
        ["language", "published_at"],
        unique=False,
    )


def downgrade() -> None:
    if _target() != "content":
        return
    op.drop_index("idx_articles_language_published_at", table_name="articles")
    op.execute(sa.text("DROP INDEX IF EXISTS idx_articles_search_text_gin"))
