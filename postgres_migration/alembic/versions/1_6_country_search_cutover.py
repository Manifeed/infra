"""replace source language filters with country

Revision ID: 1_6
Revises: 1_5
Create Date: 2026-05-07 00:00:00.000000

"""

from __future__ import annotations

import os

from alembic import op
import sqlalchemy as sa


revision = "1_6"
down_revision = "1_5"
branch_labels = None
depends_on = None


def _target() -> str:
    return os.getenv("MIGRATION_TARGET", "content").strip().lower()


def upgrade() -> None:
    if _target() != "content":
        return

    op.execute(sa.text("DROP INDEX IF EXISTS idx_rss_company_language"))
    op.execute(sa.text("UPDATE rss_company SET country = 'xx' WHERE country IS NULL OR country = ''"))
    op.alter_column(
        "rss_company",
        "country",
        existing_type=sa.CHAR(length=2),
        nullable=False,
        server_default=sa.text("'xx'"),
    )

    op.add_column(
        "articles",
        sa.Column("country", sa.String(length=2), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE articles AS article
            SET country = COALESCE(NULLIF(company.country, ''), 'xx')
            FROM rss_company AS company
            WHERE article.company_id = company.id
                AND (article.country IS NULL OR article.country = '')
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE articles AS article
            SET country = COALESCE(NULLIF(feed_company.country, ''), 'xx')
            FROM article_feed_links AS link
            JOIN rss_feeds AS feed
                ON feed.id = link.feed_id
            JOIN rss_company AS feed_company
                ON feed_company.id = feed.company_id
            WHERE link.article_id = article.article_id
                AND (article.country IS NULL OR article.country = '')
            """
        )
    )
    op.execute(sa.text("UPDATE articles SET country = 'xx' WHERE country IS NULL OR country = ''"))
    op.alter_column(
        "articles",
        "country",
        existing_type=sa.String(length=2),
        nullable=False,
        server_default=sa.text("'xx'"),
    )
    op.execute(sa.text("DROP INDEX IF EXISTS idx_articles_language_published_at"))
    op.create_index(
        "idx_articles_country_published_at",
        "articles",
        ["country", "published_at"],
        unique=False,
    )
    op.drop_column("articles", "language")
    op.drop_column("rss_company", "language")


def downgrade() -> None:
    if _target() != "content":
        return

    op.add_column("rss_company", sa.Column("language", sa.CHAR(length=2), nullable=True))
    op.add_column("articles", sa.Column("language", sa.String(length=16), nullable=True))
    op.execute(sa.text("UPDATE rss_company SET language = country"))
    op.execute(sa.text("UPDATE articles SET language = country"))
    op.create_index("idx_rss_company_language", "rss_company", ["language"], unique=False)
    op.drop_index("idx_articles_country_published_at", table_name="articles")
    op.create_index(
        "idx_articles_language_published_at",
        "articles",
        ["language", "published_at"],
        unique=False,
    )
    op.drop_column("articles", "country")
    op.alter_column(
        "rss_company",
        "country",
        existing_type=sa.CHAR(length=2),
        nullable=True,
        server_default=None,
    )
