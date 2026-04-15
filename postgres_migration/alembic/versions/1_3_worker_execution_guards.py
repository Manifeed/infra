"""harden worker task execution and lease finalization

Revision ID: 1_3_worker_execution_guards
Revises: 1_2_unique_article_content_key
Create Date: 2026-04-15 18:30:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "1_3_worker_execution_guards"
down_revision = "1_2_unique_article_content_key"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("CREATE SEQUENCE IF NOT EXISTS worker_task_execution_id_seq AS BIGINT"))
    op.add_column(
        "worker_tasks",
        sa.Column("execution_id", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
    )
    op.create_index(
        "idx_worker_tasks_status_execution_id",
        "worker_tasks",
        ["status", "execution_id"],
        unique=False,
    )

    op.add_column(
        "worker_leases",
        sa.Column("result_status", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "worker_leases",
        sa.Column("result_signature_hash", sa.String(length=64), nullable=True),
    )
    op.create_check_constraint(
        "ck_worker_leases_result_status",
        "worker_leases",
        "result_status IS NULL OR result_status IN ('completed', 'failed')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_worker_leases_result_status", "worker_leases", type_="check")
    op.drop_column("worker_leases", "result_signature_hash")
    op.drop_column("worker_leases", "result_status")

    op.drop_index("idx_worker_tasks_status_execution_id", table_name="worker_tasks")
    op.drop_column("worker_tasks", "execution_id")
    op.execute(sa.text("DROP SEQUENCE IF EXISTS worker_task_execution_id_seq"))
