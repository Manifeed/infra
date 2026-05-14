"""partial and composite indexes for identity session and API key hot paths

Revision ID: 1_3
Revises: 1_2
Create Date: 2026-05-04 12:00:00.000000

"""

from __future__ import annotations

import os

from alembic import op
import sqlalchemy as sa


revision = "1_3"
down_revision = "1_2"
branch_labels = None
depends_on = None


def _target() -> str:
    return os.getenv("MIGRATION_TARGET", "content").strip().lower()


def upgrade() -> None:
    if _target() != "identity":
        return
    op.create_index(
        "idx_user_sessions_revoked_retention",
        "user_sessions",
        ["revoked_at"],
        unique=False,
        postgresql_where=sa.text("revoked_at IS NOT NULL"),
    )
    op.create_index(
        "idx_user_sessions_user_active",
        "user_sessions",
        ["user_id", "expires_at"],
        unique=False,
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX idx_user_api_keys_user_active_created
            ON user_api_keys (user_id, created_at DESC, id DESC)
            WHERE revoked_at IS NULL
            """
        )
    )


def downgrade() -> None:
    if _target() != "identity":
        return
    op.execute(sa.text("DROP INDEX IF EXISTS idx_user_api_keys_user_active_created"))
    op.drop_index("idx_user_sessions_user_active", table_name="user_sessions")
    op.drop_index("idx_user_sessions_revoked_retention", table_name="user_sessions")
