"""collapse worker lanes/classes and drop monitoring-only ingestion traces

Revision ID: 1_1_external_only_ingestion
Revises: 1_0_baseline
Create Date: 2026-03-25 00:00:00.000000

"""

from __future__ import annotations

from alembic import op


revision = "1_1_external_only_ingestion"
down_revision = "1_0_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE worker_jobs
        SET task_type = 'rss.fetch'
        WHERE task_type = 'rss.fetch.safe'
        """
    )
    op.execute(
        """
        UPDATE worker_tasks
        SET task_type = 'rss.fetch'
        WHERE task_type = 'rss.fetch.safe'
        """
    )
    op.execute(
        """
        UPDATE worker_leases
        SET task_type = 'rss.fetch'
        WHERE task_type = 'rss.fetch.safe'
        """
    )

    for table_name in (
        "worker_runtime_snapshots",
        "worker_quotas",
        "staging_feed_fetch_results",
        "staging_article_candidates",
        "staging_embedding_requests",
        "staging_embedding_results",
        "ingest_events",
        "dedup_decisions",
        "article_versions",
        "embedding_dead_letters",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")

    for statement in (
        "ALTER TABLE worker_sessions DROP COLUMN IF EXISTS worker_class CASCADE",
        "ALTER TABLE worker_sessions DROP COLUMN IF EXISTS opened_at CASCADE",
        "ALTER TABLE worker_sessions DROP COLUMN IF EXISTS last_seen_at CASCADE",
        "ALTER TABLE worker_sessions DROP COLUMN IF EXISTS connection_state CASCADE",
        "ALTER TABLE worker_sessions DROP COLUMN IF EXISTS client_fingerprint CASCADE",
        "ALTER TABLE worker_leases DROP COLUMN IF EXISTS queue_lane CASCADE",
        "ALTER TABLE worker_leases DROP COLUMN IF EXISTS issued_at CASCADE",
        "ALTER TABLE worker_leases DROP COLUMN IF EXISTS completed_at CASCADE",
        "ALTER TABLE worker_leases DROP COLUMN IF EXISTS failed_at CASCADE",
        "ALTER TABLE worker_jobs DROP COLUMN IF EXISTS queue_lane CASCADE",
        "ALTER TABLE worker_tasks DROP COLUMN IF EXISTS queue_lane CASCADE",
        "ALTER TABLE worker_tasks DROP COLUMN IF EXISTS last_error CASCADE",
        "ALTER TABLE worker_tasks DROP COLUMN IF EXISTS last_trace_id CASCADE",
        "ALTER TABLE worker_tasks DROP COLUMN IF EXISTS lease_id CASCADE",
        "ALTER TABLE embedding_manifest DROP COLUMN IF EXISTS source_worker_class CASCADE",
    ):
        op.execute(statement)


def downgrade() -> None:
    raise RuntimeError(
        "1_1_external_only_ingestion is destructive and cannot be downgraded automatically"
    )
