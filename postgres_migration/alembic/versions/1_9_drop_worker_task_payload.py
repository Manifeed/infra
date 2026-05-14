"""drop legacy worker task payload storage

Revision ID: 1_9
Revises: 1_8
Create Date: 2026-05-13 00:00:00.000000

"""

from __future__ import annotations

import os

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "1_9"
down_revision = "1_8"
branch_labels = None
depends_on = None


def _target() -> str:
    return os.getenv("MIGRATION_TARGET", "content").strip().lower()


def upgrade() -> None:
    if _target() != "workers":
        return
    op.drop_column("worker_tasks", "payload")


def downgrade() -> None:
    if _target() != "workers":
        return
    op.add_column(
        "worker_tasks",
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
