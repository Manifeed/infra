"""article language char3

Revision ID: 1_3
Revises: 1_2
Create Date: 2026-05-21 00:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "1_3"
down_revision = "1_2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "articles",
        "language",
        existing_type=sa.CHAR(length=2),
        type_=sa.CHAR(length=3),
        existing_nullable=False,
        existing_server_default=sa.text("'xx'"),
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE articles
        SET language = 'xx'
        WHERE char_length(COALESCE(language, '')) > 2
        """
    )
    op.alter_column(
        "articles",
        "language",
        existing_type=sa.CHAR(length=3),
        type_=sa.CHAR(length=2),
        existing_nullable=False,
        existing_server_default=sa.text("'xx'"),
    )
