"""enforce unique content key for merged articles

Revision ID: 1_2_unique_article_content_key
Revises: 1_1_article_content_key
Create Date: 2026-04-12 00:30:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "1_2_unique_article_content_key"
down_revision = "1_1_article_content_key"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    duplicate_group_count = int(
        bind.execute(
            sa.text(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT content_key
                    FROM articles
                    WHERE content_key IS NOT NULL
                    GROUP BY content_key
                    HAVING COUNT(*) > 1
                ) AS duplicate_groups
                """
            )
        ).scalar_one()
        or 0
    )
    if duplicate_group_count > 0:
        raise RuntimeError(
            "Cannot create uq_articles_content_key while duplicate articles remain. "
            "Run backend/scripts/merge_duplicate_articles.py --apply first."
        )

    op.execute(sa.text("DROP INDEX IF EXISTS idx_articles_content_key"))
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_articles_content_key
            ON articles (content_key)
            WHERE content_key IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS uq_articles_content_key"))
    op.create_index(
        "idx_articles_content_key",
        "articles",
        ["content_key"],
        unique=False,
        postgresql_where=sa.text("content_key IS NOT NULL"),
    )
