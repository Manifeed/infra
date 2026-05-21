"""article url normalization cleanup

Revision ID: 1_2
Revises: 1_1
Create Date: 2026-05-20 00:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "1_2"
down_revision = "1_1"
branch_labels = None
depends_on = None

_SQLITE_SAFE_BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "article_url_next",
        sa.Column("article_id", _SQLITE_SAFE_BIGINT, nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["article_id"], ["articles.article_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("url"),
    )
    op.execute(
        """
        INSERT INTO article_url_next (article_id, url, first_seen_at)
        SELECT article_id, normalized_url, first_seen_at
        FROM article_url
        """
    )
    op.drop_table("article_url")
    op.rename_table("article_url_next", "article_url")
    op.create_index("idx_article_url_article_id", "article_url", ["article_id"], unique=False)


def downgrade() -> None:
    op.create_table(
        "article_url_legacy",
        sa.Column("article_url_id", _SQLITE_SAFE_BIGINT, primary_key=True, autoincrement=True),
        sa.Column("article_id", _SQLITE_SAFE_BIGINT, nullable=False),
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
    op.execute(
        """
        INSERT INTO article_url_legacy (article_id, url, normalized_url, first_seen_at)
        SELECT article_id, url, url, first_seen_at
        FROM article_url
        """
    )
    op.drop_index("idx_article_url_article_id", table_name="article_url")
    op.drop_table("article_url")
    op.rename_table("article_url_legacy", "article_url")
    op.create_index("idx_article_url_article_id", "article_url", ["article_id"], unique=False)
