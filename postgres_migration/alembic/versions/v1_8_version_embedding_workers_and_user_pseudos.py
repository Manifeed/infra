"""version embedding workers and add user pseudos

Revision ID: v1_8_embedding_workers_pseudos
Revises: v1_7_auth_worker_api_keys
Create Date: 2026-03-22 00:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "v1_8_embedding_workers_pseudos"
down_revision = "v1_7_auth_worker_api_keys"
branch_labels = None
depends_on = None

worker_kind_enum = postgresql.ENUM(
    "rss_scrapper",
    "source_embedding",
    name="worker_kind_enum",
    create_type=False,
)
worker_job_status_enum = postgresql.ENUM(
    "queued",
    "processing",
    "finalizing",
    "completed",
    "completed_with_errors",
    "failed",
    name="worker_job_status_enum",
    create_type=False,
)
worker_job_kind_enum = postgresql.ENUM(
    "rss_scrape",
    "source_embedding",
    name="worker_job_kind_enum",
    create_type=False,
)
worker_task_status_enum = postgresql.ENUM(
    "pending",
    "processing",
    "completed",
    "failed",
    name="worker_task_status_enum",
    create_type=False,
)


def upgrade() -> None:
    _add_user_pseudos()
    _add_api_key_worker_numbers()
    _add_worker_runtime_version()
    _recreate_embedding_tables()


def downgrade() -> None:
    _drop_new_embedding_tables()
    _recreate_legacy_embedding_tables()

    op.drop_column("worker_runtime", "worker_version")
    op.drop_constraint(
        "uq_user_api_keys_user_worker_type_worker_number",
        "user_api_keys",
        type_="unique",
    )
    op.drop_column("user_api_keys", "worker_number")
    op.drop_constraint("uq_users_pseudo", "users", type_="unique")
    op.drop_column("users", "pseudo")


def _add_user_pseudos() -> None:
    op.add_column("users", sa.Column("pseudo", sa.String(length=80), nullable=True))
    op.execute(
        """
        DO $$
        DECLARE
            user_row RECORD;
            base_candidate TEXT;
            candidate TEXT;
            suffix INTEGER;
        BEGIN
            FOR user_row IN
                SELECT id, split_part(email, '@', 1) AS email_local
                FROM users
                ORDER BY id ASC
            LOOP
                base_candidate := regexp_replace(lower(user_row.email_local), '[^a-z0-9]+', '-', 'g');
                base_candidate := btrim(base_candidate, '-');
                IF base_candidate IS NULL OR base_candidate = '' THEN
                    base_candidate := 'user';
                END IF;

                candidate := base_candidate;
                suffix := 0;
                WHILE EXISTS (
                    SELECT 1
                    FROM users
                    WHERE pseudo = candidate
                        AND id <> user_row.id
                ) LOOP
                    suffix := suffix + 1;
                    candidate := base_candidate || '-' || suffix::TEXT;
                END LOOP;

                UPDATE users
                SET pseudo = candidate
                WHERE id = user_row.id;
            END LOOP;
        END
        $$;
        """
    )
    op.alter_column("users", "pseudo", existing_type=sa.String(length=80), nullable=False)
    op.create_unique_constraint("uq_users_pseudo", "users", ["pseudo"])


def _add_api_key_worker_numbers() -> None:
    op.add_column("user_api_keys", sa.Column("worker_number", sa.Integer(), nullable=True))
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY user_id, worker_type
                    ORDER BY created_at ASC, id ASC
                ) AS worker_number
            FROM user_api_keys
        )
        UPDATE user_api_keys AS api_key
        SET worker_number = ranked.worker_number
        FROM ranked
        WHERE api_key.id = ranked.id
        """
    )
    op.alter_column("user_api_keys", "worker_number", existing_type=sa.Integer(), nullable=False)
    op.create_unique_constraint(
        "uq_user_api_keys_user_worker_type_worker_number",
        "user_api_keys",
        ["user_id", "worker_type", "worker_number"],
    )


def _add_worker_runtime_version() -> None:
    op.add_column("worker_runtime", sa.Column("worker_version", sa.String(length=80), nullable=True))


def _recreate_embedding_tables() -> None:
    _drop_legacy_embedding_tables()

    op.create_table(
        "rss_embedding_jobs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column(
            "status",
            worker_job_status_enum,
            nullable=False,
            server_default=sa.text("'queued'::worker_job_status_enum"),
        ),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("task_total", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("task_processed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("embedding_total", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("embedding_success", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("embedding_error", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("worker_version", sa.String(length=80), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("task_total >= 0", name="ck_rss_embedding_jobs_task_total"),
        sa.CheckConstraint("task_processed >= 0", name="ck_rss_embedding_jobs_task_processed"),
        sa.CheckConstraint("embedding_total >= 0", name="ck_rss_embedding_jobs_embedding_total"),
        sa.CheckConstraint("embedding_success >= 0", name="ck_rss_embedding_jobs_embedding_success"),
        sa.CheckConstraint("embedding_error >= 0", name="ck_rss_embedding_jobs_embedding_error"),
    )
    op.create_index(
        "idx_rss_embedding_jobs_requested_at",
        "rss_embedding_jobs",
        ["requested_at"],
        unique=False,
    )
    op.create_index(
        "idx_rss_embedding_jobs_status",
        "rss_embedding_jobs",
        ["status"],
        unique=False,
    )
    op.create_index(
        "idx_rss_embedding_jobs_finalized_at",
        "rss_embedding_jobs",
        ["finalized_at"],
        unique=False,
    )
    op.create_index(
        "idx_rss_embedding_jobs_worker_version_status",
        "rss_embedding_jobs",
        ["worker_version", "status"],
        unique=False,
    )

    op.create_table(
        "rss_embedding_tasks",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            worker_task_status_enum,
            nullable=False,
            server_default=sa.text("'pending'::worker_task_status_enum"),
        ),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claim_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("embedding_total", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("embedding_success", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("embedding_error", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.ForeignKeyConstraint(["job_id"], ["rss_embedding_jobs.id"], ondelete="CASCADE"),
        sa.CheckConstraint("embedding_total >= 0", name="ck_rss_embedding_tasks_embedding_total"),
        sa.CheckConstraint("embedding_success >= 0", name="ck_rss_embedding_tasks_embedding_success"),
        sa.CheckConstraint("embedding_error >= 0", name="ck_rss_embedding_tasks_embedding_error"),
    )
    op.create_index(
        "idx_rss_embedding_tasks_job_id_status",
        "rss_embedding_tasks",
        ["job_id", "status"],
        unique=False,
    )
    op.create_index(
        "idx_rss_embedding_tasks_claim_expires_at",
        "rss_embedding_tasks",
        ["claim_expires_at"],
        unique=False,
    )

    op.create_table(
        "rss_embedding_task_items",
        sa.Column("task_id", sa.BigInteger(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("item_no", sa.Integer(), nullable=False),
        sa.CheckConstraint("item_no >= 1", name="ck_rss_embedding_task_items_item_no"),
        sa.ForeignKeyConstraint(["task_id"], ["rss_embedding_tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["rss_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("task_id", "source_id"),
        sa.UniqueConstraint("task_id", "item_no", name="uq_rss_embedding_task_items_task_item_no"),
    )
    op.create_index(
        "idx_rss_embedding_task_items_source_id",
        "rss_embedding_task_items",
        ["source_id"],
        unique=False,
    )

    op.create_table(
        "rss_embedding_results",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.BigInteger(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("worker_version", sa.String(length=80), nullable=False),
        sa.Column("worker_id", sa.String(length=160), nullable=True),
        sa.Column("embedding", postgresql.ARRAY(sa.Float()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["job_id"], ["rss_embedding_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["rss_embedding_tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["rss_sources.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "idx_rss_embedding_results_job_id",
        "rss_embedding_results",
        ["job_id"],
        unique=False,
    )
    op.create_index(
        "idx_rss_embedding_results_task_id",
        "rss_embedding_results",
        ["task_id"],
        unique=False,
    )
    op.create_index(
        "idx_rss_embedding_results_source_id",
        "rss_embedding_results",
        ["source_id"],
        unique=False,
    )
    op.create_index(
        "idx_rss_embedding_results_job_latest",
        "rss_embedding_results",
        ["job_id", "source_id", "worker_version", "created_at", "id"],
        unique=False,
    )

    op.create_table(
        "rss_source_embeddings",
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("worker_version", sa.String(length=80), nullable=False),
        sa.Column("embedding", postgresql.ARRAY(sa.Float()), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["source_id"], ["rss_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("source_id", "worker_version"),
    )
    op.create_index(
        "idx_rss_source_embeddings_worker_version_source",
        "rss_source_embeddings",
        ["worker_version", "source_id"],
        unique=False,
    )


def _drop_legacy_embedding_tables() -> None:
    op.drop_table("rss_embedding_results")
    op.drop_table("rss_embedding_task_items")
    op.drop_table("rss_embedding_tasks")
    op.drop_table("rss_embedding_jobs")
    op.drop_table("rss_source_embeddings")
    op.drop_table("embedding_models")


def _drop_new_embedding_tables() -> None:
    op.drop_table("rss_embedding_results")
    op.drop_table("rss_embedding_task_items")
    op.drop_table("rss_embedding_tasks")
    op.drop_table("rss_embedding_jobs")
    op.drop_table("rss_source_embeddings")


def _recreate_legacy_embedding_tables() -> None:
    op.create_table(
        "embedding_models",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("code", name="uq_embedding_models_code"),
    )

    op.create_table(
        "rss_source_embeddings",
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("embedding_model_id", sa.Integer(), nullable=False),
        sa.Column("embedding", postgresql.ARRAY(sa.Float()), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["source_id"], ["rss_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["embedding_model_id"], ["embedding_models.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("source_id", "embedding_model_id"),
    )
    op.create_index(
        "idx_rss_source_embeddings_model_id",
        "rss_source_embeddings",
        ["embedding_model_id"],
        unique=False,
    )

    op.create_table(
        "rss_embedding_jobs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column(
            "status",
            worker_job_status_enum,
            nullable=False,
            server_default=sa.text("'queued'::worker_job_status_enum"),
        ),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("task_total", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("task_processed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("embedding_total", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("embedding_success", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("embedding_error", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("embedding_model_id", sa.Integer(), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("task_total >= 0", name="ck_rss_embedding_jobs_task_total"),
        sa.CheckConstraint("task_processed >= 0", name="ck_rss_embedding_jobs_task_processed"),
        sa.CheckConstraint("embedding_total >= 0", name="ck_rss_embedding_jobs_embedding_total"),
        sa.CheckConstraint("embedding_success >= 0", name="ck_rss_embedding_jobs_embedding_success"),
        sa.CheckConstraint("embedding_error >= 0", name="ck_rss_embedding_jobs_embedding_error"),
        sa.ForeignKeyConstraint(["embedding_model_id"], ["embedding_models.id"], ondelete="RESTRICT"),
    )
    op.create_index(
        "idx_rss_embedding_jobs_requested_at",
        "rss_embedding_jobs",
        ["requested_at"],
        unique=False,
    )
    op.create_index(
        "idx_rss_embedding_jobs_status",
        "rss_embedding_jobs",
        ["status"],
        unique=False,
    )
    op.create_index(
        "idx_rss_embedding_jobs_finalized_at",
        "rss_embedding_jobs",
        ["finalized_at"],
        unique=False,
    )

    op.create_table(
        "rss_embedding_tasks",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            worker_task_status_enum,
            nullable=False,
            server_default=sa.text("'pending'::worker_task_status_enum"),
        ),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claim_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("embedding_total", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("embedding_success", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("embedding_error", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.ForeignKeyConstraint(["job_id"], ["rss_embedding_jobs.id"], ondelete="CASCADE"),
        sa.CheckConstraint("embedding_total >= 0", name="ck_rss_embedding_tasks_embedding_total"),
        sa.CheckConstraint("embedding_success >= 0", name="ck_rss_embedding_tasks_embedding_success"),
        sa.CheckConstraint("embedding_error >= 0", name="ck_rss_embedding_tasks_embedding_error"),
    )
    op.create_index(
        "idx_rss_embedding_tasks_job_id_status",
        "rss_embedding_tasks",
        ["job_id", "status"],
        unique=False,
    )
    op.create_index(
        "idx_rss_embedding_tasks_claim_expires_at",
        "rss_embedding_tasks",
        ["claim_expires_at"],
        unique=False,
    )

    op.create_table(
        "rss_embedding_task_items",
        sa.Column("task_id", sa.BigInteger(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("item_no", sa.Integer(), nullable=False),
        sa.CheckConstraint("item_no >= 1", name="ck_rss_embedding_task_items_item_no"),
        sa.ForeignKeyConstraint(["task_id"], ["rss_embedding_tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["rss_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("task_id", "source_id"),
        sa.UniqueConstraint("task_id", "item_no", name="uq_rss_embedding_task_items_task_item_no"),
    )
    op.create_index(
        "idx_rss_embedding_task_items_source_id",
        "rss_embedding_task_items",
        ["source_id"],
        unique=False,
    )

    op.create_table(
        "rss_embedding_results",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.BigInteger(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("embedding_model_id", sa.Integer(), nullable=False),
        sa.Column("worker_id", sa.String(length=160), nullable=True),
        sa.Column("embedding", postgresql.ARRAY(sa.Float()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["job_id"], ["rss_embedding_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["rss_embedding_tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["rss_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["embedding_model_id"], ["embedding_models.id"], ondelete="RESTRICT"),
    )
    op.create_index(
        "idx_rss_embedding_results_job_id",
        "rss_embedding_results",
        ["job_id"],
        unique=False,
    )
    op.create_index(
        "idx_rss_embedding_results_task_id",
        "rss_embedding_results",
        ["task_id"],
        unique=False,
    )
    op.create_index(
        "idx_rss_embedding_results_source_id",
        "rss_embedding_results",
        ["source_id"],
        unique=False,
    )
    op.create_index(
        "idx_rss_embedding_results_model_id",
        "rss_embedding_results",
        ["embedding_model_id"],
        unique=False,
    )
