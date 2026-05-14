"""extend worker job and task states for manual job control

Revision ID: 1_2
Revises: 1_1
Create Date: 2026-05-04 00:00:00.000000

"""

from __future__ import annotations

import os

from alembic import op
import sqlalchemy as sa


revision = "1_2"
down_revision = "1_1"
branch_labels = None
depends_on = None


def _target() -> str:
    return os.getenv("MIGRATION_TARGET", "content").strip().lower()


def upgrade() -> None:
    if _target() != "workers":
        return
    op.drop_constraint("ck_worker_jobs_status", "worker_jobs", type_="check")
    op.create_check_constraint(
        "ck_worker_jobs_status",
        "worker_jobs",
        "status IN ('queued', 'processing', 'paused', 'finalizing', 'cancelled', 'completed', 'completed_with_errors', 'failed')",
    )
    op.drop_constraint("ck_worker_tasks_status", "worker_tasks", type_="check")
    op.create_check_constraint(
        "ck_worker_tasks_status",
        "worker_tasks",
        "status IN ('pending', 'processing', 'cancelled', 'completed', 'failed')",
    )


def downgrade() -> None:
    if _target() != "workers":
        return
    op.drop_constraint("ck_worker_tasks_status", "worker_tasks", type_="check")
    op.create_check_constraint(
        "ck_worker_tasks_status",
        "worker_tasks",
        "status IN ('pending', 'processing', 'completed', 'failed')",
    )
    op.drop_constraint("ck_worker_jobs_status", "worker_jobs", type_="check")
    op.create_check_constraint(
        "ck_worker_jobs_status",
        "worker_jobs",
        "status IN ('queued', 'processing', 'finalizing', 'completed', 'completed_with_errors', 'failed')",
    )
