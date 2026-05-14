"""move worker task payload storage to compact refs and add runtime counters

Revision ID: 1_8
Revises: 1_7
Create Date: 2026-05-12 00:00:00.000000

"""

from __future__ import annotations

import os

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "1_8"
down_revision = "1_7"
branch_labels = None
depends_on = None


def _target() -> str:
    return os.getenv("MIGRATION_TARGET", "content").strip().lower()


def upgrade() -> None:
    if _target() != "workers":
        return
    op.create_table(
        "worker_runtime_counters",
        sa.Column("counter_name", sa.String(length=64), primary_key=True),
        sa.Column("counter_value", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.add_column(
        "worker_tasks",
        sa.Column(
            "ref_ids",
            postgresql.ARRAY(sa.BigInteger()),
            nullable=False,
            server_default=sa.text("'{}'::bigint[]"),
        ),
    )
    op.add_column("worker_tasks", sa.Column("last_error", sa.Text(), nullable=True))
    op.add_column("worker_tasks", sa.Column("claim_owner", sa.String(length=255), nullable=True))
    op.alter_column(
        "worker_tasks",
        "payload",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        server_default=sa.text("'{}'::jsonb"),
        existing_nullable=False,
    )
    op.execute(
        sa.text(
            """
            UPDATE worker_tasks AS task
            SET ref_ids = CASE
                WHEN task.task_type = 'rss.fetch' THEN COALESCE(
                    (
                        SELECT array_agg((feed.value ->> 'feed_id')::bigint ORDER BY feed.ordinality)
                        FROM jsonb_array_elements(COALESCE(task.payload -> 'feeds', '[]'::jsonb))
                            WITH ORDINALITY AS feed(value, ordinality)
                        WHERE (feed.value ->> 'feed_id') IS NOT NULL
                    ),
                    '{}'::bigint[]
                )
                WHEN task.task_type = 'embed.source' THEN COALESCE(
                    NULLIF(
                        (
                            SELECT array_agg((source.value ->> 'id')::bigint ORDER BY source.ordinality)
                            FROM jsonb_array_elements(COALESCE(task.payload -> 'sources', '[]'::jsonb))
                                WITH ORDINALITY AS source(value, ordinality)
                            WHERE (source.value ->> 'id') IS NOT NULL
                        ),
                        '{}'::bigint[]
                    ),
                    (
                        SELECT COALESCE(array_agg(article_id.value::bigint ORDER BY article_id.ordinality), '{}'::bigint[])
                        FROM jsonb_array_elements_text(COALESCE(task.payload -> 'article_ids', '[]'::jsonb))
                            WITH ORDINALITY AS article_id(value, ordinality)
                    ),
                    '{}'::bigint[]
                )
                ELSE '{}'::bigint[]
            END
            """
        )
    )
    op.drop_constraint("ck_worker_tasks_item_total", "worker_tasks", type_="check")
    op.create_check_constraint(
        "ck_worker_tasks_item_total",
        "worker_tasks",
        "item_total > 0",
    )
    op.create_check_constraint(
        "ck_worker_tasks_ref_ids_cardinality",
        "worker_tasks",
        "cardinality(ref_ids) = item_total",
    )
    op.drop_index("idx_worker_tasks_task_type_status_requested_at", table_name="worker_tasks")
    op.drop_index("idx_worker_tasks_claim_expires_at", table_name="worker_tasks")
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


def downgrade() -> None:
    if _target() != "workers":
        return
    op.drop_index("idx_worker_tasks_expired_processing_claims", table_name="worker_tasks")
    op.drop_index("idx_worker_tasks_pending_claim_order", table_name="worker_tasks")
    op.create_index(
        "idx_worker_tasks_claim_expires_at",
        "worker_tasks",
        ["claim_expires_at"],
        unique=False,
    )
    op.create_index(
        "idx_worker_tasks_task_type_status_requested_at",
        "worker_tasks",
        ["task_type", "status", "requested_at"],
        unique=False,
    )
    op.drop_constraint("ck_worker_tasks_ref_ids_cardinality", "worker_tasks", type_="check")
    op.drop_constraint("ck_worker_tasks_item_total", "worker_tasks", type_="check")
    op.create_check_constraint(
        "ck_worker_tasks_item_total",
        "worker_tasks",
        "item_total >= 0",
    )
    op.alter_column(
        "worker_tasks",
        "payload",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        server_default=None,
        existing_nullable=False,
    )
    op.drop_column("worker_tasks", "claim_owner")
    op.drop_column("worker_tasks", "last_error")
    op.drop_column("worker_tasks", "ref_ids")
    op.drop_table("worker_runtime_counters")
