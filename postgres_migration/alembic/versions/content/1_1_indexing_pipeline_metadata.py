"""indexing pipeline metadata

Revision ID: 1_1
Revises: 1_0
Create Date: 2026-05-19 00:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "1_1"
down_revision = "1_0"
branch_labels = None
depends_on = None

_ARTICLE_THEME_ENUM = postgresql.ENUM(
    "economy",
    "sports",
    "society",
    "news",
    "politics",
    "technology",
    "science",
    "culture",
    "health",
    "environment",
    "world",
    "justice",
    "education",
    "business",
    "finance",
    "other",
    name="article_theme_enum",
    create_type=False,
)


def upgrade() -> None:
    _ARTICLE_THEME_ENUM.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "articles",
        sa.Column("language", sa.CHAR(length=2), nullable=False, server_default=sa.text("'xx'")),
    )
    op.create_index(
        "idx_articles_language_published_at",
        "articles",
        ["language", "published_at"],
        unique=False,
    )

    op.create_table(
        "article_theme",
        sa.Column("article_id", sa.BigInteger(), nullable=False),
        sa.Column("theme", _ARTICLE_THEME_ENUM, nullable=False),
        sa.Column("confidence", sa.REAL(), nullable=True),
        sa.ForeignKeyConstraint(["article_id"], ["articles.article_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("article_id", "theme"),
    )
    op.create_index("idx_article_theme_theme_article_id", "article_theme", ["theme", "article_id"], unique=False)

    op.create_table(
        "article_ner_mention",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("article_id", sa.BigInteger(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("score", sa.REAL(), nullable=True),
        sa.Column("start_offset", sa.Integer(), nullable=True),
        sa.Column("end_offset", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["article_id"], ["articles.article_id"], ondelete="CASCADE"),
    )
    op.create_index("idx_article_ner_mention_article_id", "article_ner_mention", ["article_id"], unique=False)
    op.create_index("idx_article_ner_mention_label_text", "article_ner_mention", ["label", "text"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_article_ner_mention_label_text", table_name="article_ner_mention")
    op.drop_index("idx_article_ner_mention_article_id", table_name="article_ner_mention")
    op.drop_table("article_ner_mention")

    op.drop_index("idx_article_theme_theme_article_id", table_name="article_theme")
    op.drop_table("article_theme")

    op.drop_index("idx_articles_language_published_at", table_name="articles")
    op.drop_column("articles", "language")

    _ARTICLE_THEME_ENUM.drop(op.get_bind(), checkfirst=True)
