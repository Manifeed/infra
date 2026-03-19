"""add rss catalog sync state table

Revision ID: v1_1_add_rss_catalog_sync_state
Revises: v1_initialization
Create Date: 2026-03-16 00:30:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "v1_1_add_rss_catalog_sync_state"
down_revision = "v1_initialization"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rss_catalog_sync_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("last_applied_revision", sa.String(length=64), nullable=True),
        sa.Column("last_seen_revision", sa.String(length=64), nullable=True),
        sa.Column(
            "last_sync_status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'success'"),
        ),
        sa.Column("last_sync_error", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "last_sync_status IN ('success', 'failed')",
            name="ck_rss_catalog_sync_state_status",
        ),
    )


def downgrade() -> None:
    op.drop_table("rss_catalog_sync_state")
