"""drop article themes

Revision ID: 1_5
Revises: 1_4
Create Date: 2026-05-22 00:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "1_5"
down_revision = "1_4"
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
	op.drop_index("idx_article_theme_theme_article_id", table_name="article_theme")
	op.drop_table("article_theme")
	_ARTICLE_THEME_ENUM.drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
	_ARTICLE_THEME_ENUM.create(op.get_bind(), checkfirst=True)
	op.create_table(
		"article_theme",
		sa.Column("article_id", sa.BigInteger(), nullable=False),
		sa.Column("theme", _ARTICLE_THEME_ENUM, nullable=False),
		sa.Column("confidence", sa.REAL(), nullable=True),
		sa.ForeignKeyConstraint(["article_id"], ["articles.article_id"], ondelete="CASCADE"),
		sa.PrimaryKeyConstraint("article_id", "theme"),
	)
	op.create_index(
		"idx_article_theme_theme_article_id",
		"article_theme",
		["theme", "article_id"],
		unique=False,
	)
