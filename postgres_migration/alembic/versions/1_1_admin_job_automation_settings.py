"""move admin job automation settings into workers migration

Revision ID: 1_1
Revises: 1_0
Create Date: 2026-04-28 00:00:00.000000

"""

from __future__ import annotations

import os

from alembic import op
import sqlalchemy as sa


revision = "1_1"
down_revision = "1_0"
branch_labels = None
depends_on = None


def _target() -> str:
    return os.getenv("MIGRATION_TARGET", "content").strip().lower()


def upgrade() -> None:
    if _target() != "workers":
        return
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS admin_job_automation_settings (
                singleton_key VARCHAR(32) PRIMARY KEY,
                enabled BOOLEAN NOT NULL DEFAULT FALSE,
                interval_minutes INTEGER NOT NULL DEFAULT 30,
                last_cycle_started_at TIMESTAMPTZ NULL,
                current_ingest_job_id VARCHAR(128) NULL,
                current_embed_job_id VARCHAR(128) NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )


def downgrade() -> None:
    if _target() != "workers":
        return
    op.drop_table("admin_job_automation_settings")
