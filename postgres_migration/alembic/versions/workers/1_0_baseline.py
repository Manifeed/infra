"""workers database baseline

Revision ID: 1_0
Revises:
Create Date: 2026-05-14 00:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "1_0"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("CREATE SEQUENCE IF NOT EXISTS worker_task_execution_id_seq AS BIGINT"))

    op.create_table(
        "worker_sessions",
        sa.Column("session_id", sa.String(length=64), primary_key=True),
        sa.Column("api_key_id", sa.Integer(), nullable=False),
        sa.Column("worker_type", sa.String(length=64), nullable=False),
        sa.Column("worker_version", sa.String(length=80), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("worker_type IN ('rss_scrapper')", name="ck_worker_sessions_worker_type"),
    )
    op.create_index(
        "idx_worker_sessions_api_key_expires_at",
        "worker_sessions",
        ["api_key_id", "expires_at"],
        unique=False,
    )

    op.create_table(
        "worker_leases",
        sa.Column("lease_id", sa.String(length=64), primary_key=True),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("payload_ref", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("result_status", sa.String(length=16), nullable=True),
        sa.Column("result_nonce", sa.String(length=64), nullable=True),
        sa.Column("signature_hash", sa.String(length=64), nullable=False),
        sa.Column("result_signature_hash", sa.String(length=64), nullable=True),
        sa.CheckConstraint("task_type IN ('rss.fetch', 'embed.source')", name="ck_worker_leases_task_type"),
        sa.CheckConstraint(
            "result_status IS NULL OR result_status IN ('completed', 'failed')",
            name="ck_worker_leases_result_status",
        ),
        sa.ForeignKeyConstraint(["session_id"], ["worker_sessions.session_id"], ondelete="CASCADE"),
    )
    op.create_index(
        "idx_worker_leases_session_expires_at",
        "worker_leases",
        ["session_id", "expires_at"],
        unique=False,
    )
    op.create_index(
        "idx_worker_leases_task_type_expires_at",
        "worker_leases",
        ["task_type", "expires_at"],
        unique=False,
    )

    op.create_table(
        "worker_jobs",
        sa.Column("job_id", sa.String(length=64), primary_key=True),
        sa.Column("job_kind", sa.String(length=32), nullable=False),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("worker_version", sa.String(length=80), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("task_total", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("task_processed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("item_total", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("item_success", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("item_error", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.CheckConstraint("job_kind IN ('rss_scrape', 'source_embedding')", name="ck_worker_jobs_job_kind"),
        sa.CheckConstraint("task_type IN ('rss.fetch', 'embed.source')", name="ck_worker_jobs_task_type"),
        sa.CheckConstraint(
            "status IN ('queued', 'processing', 'paused', 'finalizing', 'cancelled', 'completed', 'completed_with_errors', 'failed')",
            name="ck_worker_jobs_status",
        ),
        sa.CheckConstraint("task_total >= 0", name="ck_worker_jobs_task_total"),
        sa.CheckConstraint("task_processed >= 0", name="ck_worker_jobs_task_processed"),
        sa.CheckConstraint("item_total >= 0", name="ck_worker_jobs_item_total"),
        sa.CheckConstraint("item_success >= 0", name="ck_worker_jobs_item_success"),
        sa.CheckConstraint("item_error >= 0", name="ck_worker_jobs_item_error"),
    )
    op.create_index("idx_worker_jobs_requested_at", "worker_jobs", ["requested_at", "job_id"], unique=False)

    op.create_table(
        "worker_tasks",
        sa.Column("task_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("worker_version", sa.String(length=80), nullable=True),
        sa.Column(
            "ref_ids",
            postgresql.ARRAY(sa.BigInteger()),
            nullable=False,
            server_default=sa.text("'{}'::bigint[]"),
        ),
        sa.Column("execution_id", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claim_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("item_total", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("item_success", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("item_error", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("claim_owner", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["worker_jobs.job_id"], ondelete="CASCADE"),
        sa.CheckConstraint("task_type IN ('rss.fetch', 'embed.source')", name="ck_worker_tasks_task_type"),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'cancelled', 'completed', 'failed')",
            name="ck_worker_tasks_status",
        ),
        sa.CheckConstraint("attempt_count >= 0", name="ck_worker_tasks_attempt_count"),
        sa.CheckConstraint("item_total > 0", name="ck_worker_tasks_item_total"),
        sa.CheckConstraint("item_success >= 0", name="ck_worker_tasks_item_success"),
        sa.CheckConstraint("item_error >= 0", name="ck_worker_tasks_item_error"),
        sa.CheckConstraint("cardinality(ref_ids) = item_total", name="ck_worker_tasks_ref_ids_cardinality"),
    )
    op.create_index(
        "idx_worker_tasks_status_execution_id",
        "worker_tasks",
        ["status", "execution_id"],
        unique=False,
    )
    op.create_index("idx_worker_tasks_job_id_status", "worker_tasks", ["job_id", "status"], unique=False)
    op.create_index(
        "idx_worker_tasks_pending_claim_order",
        "worker_tasks",
        ["task_type", "requested_at", "task_id"],
        unique=False,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "idx_worker_tasks_expired_processing_claims",
        "worker_tasks",
        ["task_type", "claim_expires_at", "task_id"],
        unique=False,
        postgresql_where=sa.text("status = 'processing'"),
    )

    op.create_table(
        "worker_runtime_counters",
        sa.Column("counter_name", sa.String(length=64), primary_key=True),
        sa.Column("counter_value", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "admin_job_automation_settings",
        sa.Column("singleton_key", sa.String(length=32), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("interval_minutes", sa.Integer(), nullable=False, server_default=sa.text("30")),
        sa.Column("last_cycle_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_ingest_job_id", sa.String(length=128), nullable=True),
        sa.Column("current_embed_job_id", sa.String(length=128), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("admin_job_automation_settings")
    op.drop_table("worker_runtime_counters")

    op.drop_index("idx_worker_tasks_expired_processing_claims", table_name="worker_tasks")
    op.drop_index("idx_worker_tasks_pending_claim_order", table_name="worker_tasks")
    op.drop_index("idx_worker_tasks_job_id_status", table_name="worker_tasks")
    op.drop_index("idx_worker_tasks_status_execution_id", table_name="worker_tasks")
    op.drop_table("worker_tasks")

    op.drop_index("idx_worker_jobs_requested_at", table_name="worker_jobs")
    op.drop_table("worker_jobs")

    op.drop_index("idx_worker_leases_task_type_expires_at", table_name="worker_leases")
    op.drop_index("idx_worker_leases_session_expires_at", table_name="worker_leases")
    op.drop_table("worker_leases")

    op.drop_index("idx_worker_sessions_api_key_expires_at", table_name="worker_sessions")
    op.drop_table("worker_sessions")

    op.execute(sa.text("DROP SEQUENCE IF EXISTS worker_task_execution_id_seq"))
