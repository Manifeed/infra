"""add auth session version columns

Revision ID: 1_1_auth_session_versions
Revises: 1_0_baseline
Create Date: 2026-04-03 00:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "1_1_auth_session_versions"
down_revision = "1_0_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "session_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.add_column(
        "user_sessions",
        sa.Column(
            "session_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.execute(
        """
        UPDATE user_sessions AS sessions
        SET session_version = users.session_version
        FROM users
        WHERE users.id = sessions.user_id
        """
    )
    op.alter_column("users", "session_version", server_default=None)
    op.alter_column("user_sessions", "session_version", server_default=None)


def downgrade() -> None:
    op.drop_column("user_sessions", "session_version")
    op.drop_column("users", "session_version")
