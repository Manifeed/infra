"""add article_url for reverse URL lookup

Revision ID: 1_7
Revises: 1_6
Create Date: 2026-05-11 00:00:00.000000

"""

from __future__ import annotations

import os

from alembic import op
import sqlalchemy as sa


revision = "1_7"
down_revision = "1_6"
branch_labels = None
depends_on = None


def _target() -> str:
    return os.getenv("MIGRATION_TARGET", "content").strip().lower()


def upgrade() -> None:
    if _target() != "content":
        return

    op.create_table(
        "article_url",
        sa.Column("article_url_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("article_id", sa.BigInteger(), nullable=False),
        sa.Column("url", sa.String(length=4000), nullable=False),
        sa.Column("normalized_url", sa.String(length=1000), nullable=False),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["article_id"], ["articles.article_id"], ondelete="CASCADE"),
        sa.UniqueConstraint("normalized_url", name="uq_article_url_normalized_url"),
    )
    op.create_index(
        "idx_article_url_article_id",
        "article_url",
        ["article_id"],
        unique=False,
    )


def downgrade() -> None:
    if _target() != "content":
        return

    op.drop_index("idx_article_url_article_id", table_name="article_url")
    op.drop_table("article_url")
