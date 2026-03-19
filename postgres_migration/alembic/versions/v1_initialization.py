"""final schema baseline

Revision ID: v1_initialization
Revises:
Create Date: 2026-03-16 00:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "v1_initialization"
down_revision = None
branch_labels = None
depends_on = None

rss_feed_runtime_status_enum = postgresql.ENUM(
    "pending",
    "success",
    "not_modified",
    "error",
    name="rss_feed_runtime_status_enum",
    create_type=False,
)
worker_kind_enum = postgresql.ENUM(
    "rss_scrapper",
    "source_embedding",
    name="worker_kind_enum",
    create_type=False,
)
worker_runtime_kind_enum = postgresql.ENUM(
    "cpu",
    "gpu",
    "npu",
    "unknown",
    name="worker_runtime_kind_enum",
    create_type=False,
)
worker_job_kind_enum = postgresql.ENUM(
    "rss_scrape",
    "source_embedding",
    name="worker_job_kind_enum",
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
worker_task_status_enum = postgresql.ENUM(
    "pending",
    "processing",
    "completed",
    "failed",
    name="worker_task_status_enum",
    create_type=False,
)
rss_scrape_result_status_enum = postgresql.ENUM(
    "success",
    "not_modified",
    "error",
    name="rss_scrape_result_status_enum",
    create_type=False,
)
worker_auth_purpose_enum = postgresql.ENUM(
    "enroll",
    "auth",
    name="worker_auth_purpose_enum",
    create_type=False,
)


def upgrade() -> None:
    _create_enum_types()
    _create_feed_storage_tables()
    _create_source_storage_tables()
    _create_embedding_storage_tables()
    _create_rss_scraping_tables()
    _create_embedding_task_tables()
    _create_worker_management_tables()
    _create_embedding_projection_tables()
    _create_cleanup_functions()


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS public.cleanup_expired_job_data(interval)")
    op.execute("DROP FUNCTION IF EXISTS public.cleanup_expired_worker_auth_challenges(interval)")

    for table_name in (
        "embedding_projection_points",
        "embedding_projections",
        "worker_capabilities",
        "worker_runtime",
        "worker_auth_challenges",
        "worker_registry",
        "rss_embedding_results",
        "rss_embedding_task_items",
        "rss_embedding_tasks",
        "rss_embedding_jobs",
        "rss_scrape_result_sources",
        "rss_scrape_result_feeds",
        "rss_scrape_task_items",
        "rss_scrape_tasks",
        "rss_scrape_jobs",
        "rss_source_embeddings",
        "embedding_models",
        "rss_source_feeds",
        "rss_sources",
        "rss_feed_runtime",
        "rss_feed_tags",
        "rss_tags",
        "rss_feeds",
        "rss_company",
    ):
        op.drop_table(table_name)

    _drop_enum_types()


def _create_enum_types() -> None:
    bind = op.get_bind()
    for enum_type in (
        rss_feed_runtime_status_enum,
        worker_kind_enum,
        worker_runtime_kind_enum,
        worker_job_kind_enum,
        worker_job_status_enum,
        worker_task_status_enum,
        rss_scrape_result_status_enum,
        worker_auth_purpose_enum,
    ):
        enum_type.create(bind, checkfirst=True)


def _drop_enum_types() -> None:
    bind = op.get_bind()
    for enum_type in (
        worker_auth_purpose_enum,
        rss_scrape_result_status_enum,
        worker_task_status_enum,
        worker_job_status_enum,
        worker_job_kind_enum,
        worker_runtime_kind_enum,
        worker_kind_enum,
        rss_feed_runtime_status_enum,
    ):
        enum_type.drop(bind, checkfirst=True)


def _create_feed_storage_tables() -> None:
    op.create_table(
        "rss_company",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("host", sa.String(length=255), nullable=True),
        sa.Column("icon_url", sa.String(length=500), nullable=True),
        sa.Column("country", sa.CHAR(length=2), nullable=True),
        sa.Column("language", sa.CHAR(length=2), nullable=True),
        sa.Column(
            "fetchprotection",
            sa.SmallInteger(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.CheckConstraint(
            "fetchprotection >= 0 AND fetchprotection <= 2",
            name="ck_rss_company_fetchprotection",
        ),
        sa.UniqueConstraint("name", name="uq_rss_company_name"),
    )
    op.create_index("idx_rss_company_country", "rss_company", ["country"], unique=False)
    op.create_index("idx_rss_company_language", "rss_company", ["language"], unique=False)

    op.create_table(
        "rss_feeds",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("section", sa.String(length=50), nullable=True),
        sa.Column(
            "trust_score",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0.5"),
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.CheckConstraint(
            "trust_score >= 0.0 AND trust_score <= 1.0",
            name="ck_rss_feeds_trust_score",
        ),
        sa.ForeignKeyConstraint(["company_id"], ["rss_company.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("url", name="uq_rss_feeds_url"),
    )
    op.create_index("idx_rss_feeds_company_id", "rss_feeds", ["company_id"], unique=False)
    op.create_index(
        "idx_rss_feeds_enabled",
        "rss_feeds",
        ["enabled"],
        unique=False,
        postgresql_where=sa.text("enabled = true"),
    )

    op.create_table(
        "rss_feed_runtime",
        sa.Column("feed_id", sa.Integer(), primary_key=True),
        sa.Column(
            "last_status",
            rss_feed_runtime_status_enum,
            nullable=False,
            server_default=sa.text("'pending'::rss_feed_runtime_status_enum"),
        ),
        sa.Column("last_scraped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column(
            "consecutive_error_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("etag", sa.String(length=255), nullable=True),
        sa.Column("last_feed_update", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_article_published_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "consecutive_error_count >= 0",
            name="ck_rss_feed_runtime_consecutive_error_count",
        ),
        sa.ForeignKeyConstraint(["feed_id"], ["rss_feeds.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "idx_rss_feed_runtime_last_status",
        "rss_feed_runtime",
        ["last_status"],
        unique=False,
    )
    op.create_index(
        "idx_rss_feed_runtime_last_success_at",
        "rss_feed_runtime",
        ["last_success_at"],
        unique=False,
    )
    op.create_index(
        "idx_rss_feed_runtime_last_article_published_at",
        "rss_feed_runtime",
        ["last_article_published_at"],
        unique=False,
    )

    op.create_table(
        "rss_tags",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.UniqueConstraint("name", name="uq_rss_tags_name"),
    )

    op.create_table(
        "rss_feed_tags",
        sa.Column("feed_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["feed_id"], ["rss_feeds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["rss_tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("feed_id", "tag_id"),
    )
    op.create_index("idx_rss_feed_tags_tag_id", "rss_feed_tags", ["tag_id"], unique=False)


def _create_source_storage_tables() -> None:
    op.create_table(
        "rss_sources",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("TIMESTAMPTZ '1970-01-01 00:00:00+00'"),
        ),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("image_url", sa.String(length=1000), nullable=True),
        sa.Column("identity_key", sa.String(length=255), nullable=False),
        sa.UniqueConstraint("identity_key", name="uq_rss_sources_identity_key"),
    )
    op.create_index("idx_rss_sources_published_at", "rss_sources", ["published_at"], unique=False)
    op.create_index("idx_rss_sources_ingested_at", "rss_sources", ["ingested_at"], unique=False)
    op.create_index("idx_rss_sources_url", "rss_sources", ["url"], unique=False)

    op.create_table(
        "rss_source_feeds",
        sa.Column("feed_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["feed_id"], ["rss_feeds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["rss_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("feed_id", "source_id"),
    )
    op.create_index(
        "idx_rss_source_feeds_source_id",
        "rss_source_feeds",
        ["source_id"],
        unique=False,
    )
    op.create_index(
        "idx_rss_source_feeds_ingested_at",
        "rss_source_feeds",
        ["ingested_at"],
        unique=False,
    )


def _create_embedding_storage_tables() -> None:
    op.create_table(
        "embedding_models",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("code", name="uq_embedding_models_code"),
    )

    op.create_table(
        "rss_source_embeddings",
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("embedding_model_id", sa.Integer(), nullable=False),
        sa.Column("embedding", postgresql.ARRAY(sa.Float()), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["source_id"], ["rss_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["embedding_model_id"],
            ["embedding_models.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("source_id", "embedding_model_id"),
    )
    op.create_index(
        "idx_rss_source_embeddings_model_id",
        "rss_source_embeddings",
        ["embedding_model_id"],
        unique=False,
    )


def _create_rss_scraping_tables() -> None:
    op.create_table(
        "rss_scrape_jobs",
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
        sa.Column(
            "task_processed",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("feed_total", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "feed_success",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("feed_error", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("task_total >= 0", name="ck_rss_scrape_jobs_task_total"),
        sa.CheckConstraint(
            "task_processed >= 0",
            name="ck_rss_scrape_jobs_task_processed",
        ),
        sa.CheckConstraint("feed_total >= 0", name="ck_rss_scrape_jobs_feed_total"),
        sa.CheckConstraint(
            "feed_success >= 0",
            name="ck_rss_scrape_jobs_feed_success",
        ),
        sa.CheckConstraint("feed_error >= 0", name="ck_rss_scrape_jobs_feed_error"),
    )
    op.create_index(
        "idx_rss_scrape_jobs_requested_at",
        "rss_scrape_jobs",
        ["requested_at"],
        unique=False,
    )
    op.create_index("idx_rss_scrape_jobs_status", "rss_scrape_jobs", ["status"], unique=False)
    op.create_index(
        "idx_rss_scrape_jobs_finalized_at",
        "rss_scrape_jobs",
        ["finalized_at"],
        unique=False,
    )

    op.create_table(
        "rss_scrape_tasks",
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
        sa.Column("feed_total", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "feed_success",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("feed_error", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.ForeignKeyConstraint(["job_id"], ["rss_scrape_jobs.id"], ondelete="CASCADE"),
        sa.CheckConstraint("feed_total >= 0", name="ck_rss_scrape_tasks_feed_total"),
        sa.CheckConstraint(
            "feed_success >= 0",
            name="ck_rss_scrape_tasks_feed_success",
        ),
        sa.CheckConstraint("feed_error >= 0", name="ck_rss_scrape_tasks_feed_error"),
    )
    op.create_index(
        "idx_rss_scrape_tasks_job_id_status",
        "rss_scrape_tasks",
        ["job_id", "status"],
        unique=False,
    )
    op.create_index(
        "idx_rss_scrape_tasks_claim_expires_at",
        "rss_scrape_tasks",
        ["claim_expires_at"],
        unique=False,
    )

    op.create_table(
        "rss_scrape_task_items",
        sa.Column("task_id", sa.BigInteger(), nullable=False),
        sa.Column("feed_id", sa.Integer(), nullable=False),
        sa.Column("fetchprotection", sa.SmallInteger(), nullable=True),
        sa.Column("etag", sa.String(length=255), nullable=True),
        sa.Column("last_feed_update", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_article_published_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "fetchprotection IS NULL OR (fetchprotection >= 0 AND fetchprotection <= 2)",
            name="ck_rss_scrape_task_items_fetchprotection",
        ),
        sa.ForeignKeyConstraint(["task_id"], ["rss_scrape_tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["feed_id"], ["rss_feeds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("task_id", "feed_id"),
    )
    op.create_index(
        "idx_rss_scrape_task_items_feed_id",
        "rss_scrape_task_items",
        ["feed_id"],
        unique=False,
    )

    op.create_table(
        "rss_scrape_result_feeds",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.BigInteger(), nullable=False),
        sa.Column("feed_id", sa.Integer(), nullable=False),
        sa.Column("worker_id", sa.String(length=160), nullable=True),
        sa.Column("fetchprotection_used", sa.SmallInteger(), nullable=True),
        sa.Column("resolved_fetchprotection", sa.SmallInteger(), nullable=True),
        sa.Column(
            "status",
            rss_scrape_result_status_enum,
            nullable=False,
        ),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("new_etag", sa.String(length=255), nullable=True),
        sa.Column("last_feed_update", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_article_published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "fetchprotection_used IS NULL OR (fetchprotection_used >= 0 AND fetchprotection_used <= 2)",
            name="ck_rss_scrape_result_feeds_fetchprotection_used",
        ),
        sa.CheckConstraint(
            "resolved_fetchprotection IS NULL OR (resolved_fetchprotection >= 0 AND resolved_fetchprotection <= 2)",
            name="ck_rss_scrape_result_feeds_resolved_fetchprotection",
        ),
        sa.ForeignKeyConstraint(["job_id"], ["rss_scrape_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["rss_scrape_tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["feed_id"], ["rss_feeds.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "idx_rss_scrape_result_feeds_job_id",
        "rss_scrape_result_feeds",
        ["job_id"],
        unique=False,
    )
    op.create_index(
        "idx_rss_scrape_result_feeds_task_id",
        "rss_scrape_result_feeds",
        ["task_id"],
        unique=False,
    )
    op.create_index(
        "idx_rss_scrape_result_feeds_feed_id",
        "rss_scrape_result_feeds",
        ["feed_id"],
        unique=False,
    )
    op.create_index(
        "idx_rss_scrape_result_feeds_created_at",
        "rss_scrape_result_feeds",
        ["created_at"],
        unique=False,
    )

    op.create_table(
        "rss_scrape_result_sources",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("result_feed_id", sa.BigInteger(), nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("TIMESTAMPTZ '1970-01-01 00:00:00+00'"),
        ),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("image_url", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["result_feed_id"],
            ["rss_scrape_result_feeds.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["job_id"], ["rss_scrape_jobs.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "idx_rss_scrape_result_sources_result_feed_id",
        "rss_scrape_result_sources",
        ["result_feed_id"],
        unique=False,
    )
    op.create_index(
        "idx_rss_scrape_result_sources_job_id",
        "rss_scrape_result_sources",
        ["job_id"],
        unique=False,
    )


def _create_embedding_task_tables() -> None:
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
        sa.Column(
            "task_processed",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "embedding_total",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "embedding_success",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "embedding_error",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("embedding_model_id", sa.Integer(), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("task_total >= 0", name="ck_rss_embedding_jobs_task_total"),
        sa.CheckConstraint(
            "task_processed >= 0",
            name="ck_rss_embedding_jobs_task_processed",
        ),
        sa.CheckConstraint(
            "embedding_total >= 0",
            name="ck_rss_embedding_jobs_embedding_total",
        ),
        sa.CheckConstraint(
            "embedding_success >= 0",
            name="ck_rss_embedding_jobs_embedding_success",
        ),
        sa.CheckConstraint(
            "embedding_error >= 0",
            name="ck_rss_embedding_jobs_embedding_error",
        ),
        sa.ForeignKeyConstraint(
            ["embedding_model_id"],
            ["embedding_models.id"],
            ondelete="RESTRICT",
        ),
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
        sa.Column(
            "embedding_total",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "embedding_success",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "embedding_error",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.ForeignKeyConstraint(["job_id"], ["rss_embedding_jobs.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "embedding_total >= 0",
            name="ck_rss_embedding_tasks_embedding_total",
        ),
        sa.CheckConstraint(
            "embedding_success >= 0",
            name="ck_rss_embedding_tasks_embedding_success",
        ),
        sa.CheckConstraint(
            "embedding_error >= 0",
            name="ck_rss_embedding_tasks_embedding_error",
        ),
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
        sa.UniqueConstraint(
            "task_id",
            "item_no",
            name="uq_rss_embedding_task_items_task_item_no",
        ),
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
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["job_id"], ["rss_embedding_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["rss_embedding_tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["rss_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["embedding_model_id"],
            ["embedding_models.id"],
            ondelete="RESTRICT",
        ),
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


def _create_worker_management_tables() -> None:
    op.create_table(
        "worker_registry",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("worker_kind", worker_kind_enum, nullable=False),
        sa.Column("device_id", sa.String(length=100), nullable=False),
        sa.Column("public_key", sa.String(length=255), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=True),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column("platform", sa.String(length=120), nullable=True),
        sa.Column("arch", sa.String(length=120), nullable=True),
        sa.Column("worker_version", sa.String(length=80), nullable=True),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "enrolled_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("last_auth_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "worker_kind",
            "device_id",
            name="uq_worker_registry_kind_device",
        ),
        sa.UniqueConstraint("fingerprint", name="uq_worker_registry_fingerprint"),
    )

    op.create_table(
        "worker_auth_challenges",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("worker_id", sa.Integer(), nullable=False),
        sa.Column("purpose", worker_auth_purpose_enum, nullable=False),
        sa.Column("challenge", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["worker_id"], ["worker_registry.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "idx_worker_auth_challenges_worker_id_expires_at",
        "worker_auth_challenges",
        ["worker_id", "expires_at"],
        unique=False,
    )

    op.create_table(
        "worker_runtime",
        sa.Column("worker_id", sa.Integer(), primary_key=True),
        sa.Column("worker_name", sa.String(length=100), nullable=True),
        sa.Column(
            "runtime_kind",
            worker_runtime_kind_enum,
            nullable=False,
            server_default=sa.text("'unknown'::worker_runtime_kind_enum"),
        ),
        sa.Column("connection_state", sa.String(length=32), nullable=True),
        sa.Column("desired_state", sa.String(length=32), nullable=True),
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_job_kind", worker_job_kind_enum, nullable=True),
        sa.Column("current_task_id", sa.BigInteger(), nullable=True),
        sa.Column("current_execution_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "active_claim_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "active_claim_count >= 0",
            name="ck_worker_runtime_active_claim_count",
        ),
        sa.ForeignKeyConstraint(["worker_id"], ["worker_registry.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "idx_worker_runtime_last_seen_at",
        "worker_runtime",
        ["last_seen_at"],
        unique=False,
    )
    op.create_index(
        "idx_worker_runtime_active",
        "worker_runtime",
        ["active"],
        unique=False,
    )

    op.create_table(
        "worker_capabilities",
        sa.Column("worker_id", sa.Integer(), nullable=False),
        sa.Column("job_kind", worker_job_kind_enum, nullable=False),
        sa.Column("embedding_model_id", sa.Integer(), nullable=True),
        sa.Column("max_batch_size", sa.Integer(), nullable=True),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.CheckConstraint(
            "max_batch_size IS NULL OR max_batch_size >= 1",
            name="ck_worker_capabilities_max_batch_size",
        ),
        sa.ForeignKeyConstraint(["worker_id"], ["worker_registry.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["embedding_model_id"],
            ["embedding_models.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("worker_id", "job_kind"),
    )
    op.create_index(
        "idx_worker_capabilities_embedding_model_id",
        "worker_capabilities",
        ["embedding_model_id"],
        unique=False,
    )


def _create_embedding_projection_tables() -> None:
    op.create_table(
        "embedding_projections",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("embedding_model_id", sa.Integer(), nullable=False),
        sa.Column("projector_kind", sa.String(length=40), nullable=False),
        sa.Column("projection_version", sa.String(length=80), nullable=False),
        sa.Column("projector_state", sa.LargeBinary(), nullable=False),
        sa.Column("fitted_source_total", sa.Integer(), nullable=False),
        sa.Column("last_embedding_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "fitted_source_total >= 0",
            name="ck_embedding_projections_fitted_source_total",
        ),
        sa.ForeignKeyConstraint(
            ["embedding_model_id"],
            ["embedding_models.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "embedding_model_id",
            "projection_version",
            name="uq_embedding_projections_model_version",
        ),
    )
    op.create_index(
        "idx_embedding_projections_active",
        "embedding_projections",
        ["active"],
        unique=False,
    )

    op.create_table(
        "embedding_projection_points",
        sa.Column("projection_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("embedding_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "projected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["projection_id"],
            ["embedding_projections.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["source_id"], ["rss_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("projection_id", "source_id"),
    )
    op.create_index(
        "idx_embedding_projection_points_source_id",
        "embedding_projection_points",
        ["source_id"],
        unique=False,
    )


def _create_cleanup_functions() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.cleanup_expired_job_data(
            retention_interval interval DEFAULT '30 days'
        )
        RETURNS void
        LANGUAGE plpgsql
        AS $$
        BEGIN
            DELETE FROM rss_scrape_jobs
            WHERE COALESCE(finalized_at, finished_at, requested_at) < now() - retention_interval;

            DELETE FROM rss_embedding_jobs
            WHERE COALESCE(finalized_at, finished_at, requested_at) < now() - retention_interval;
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.cleanup_expired_worker_auth_challenges(
            retention_interval interval DEFAULT '7 days'
        )
        RETURNS void
        LANGUAGE plpgsql
        AS $$
        BEGIN
            DELETE FROM worker_auth_challenges
            WHERE COALESCE(used_at, expires_at) < now() - retention_interval;
        END;
        $$;
        """
    )
