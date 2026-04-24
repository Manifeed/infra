"""baseline schema split across content, identity and workers databases

Revision ID: 1_0
Revises:
Create Date: 2026-03-24 00:00:00.000000

"""

from __future__ import annotations

import os

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "1_0"
down_revision = None
branch_labels = None
depends_on = None

_RSS_FEED_RUNTIME_STATUS_ENUM = postgresql.ENUM(
    "pending",
    "success",
    "not_modified",
    "error",
    name="rss_feed_runtime_status",
    create_type=False,
)


def _target() -> str:
    return os.getenv("MIGRATION_TARGET", "content").strip().lower()


def upgrade() -> None:
    target = _target()
    if target == "content":
        _create_content_database()
        return
    if target == "identity":
        _create_identity_database()
        return
    if target == "workers":
        _create_workers_database()
        return
    raise RuntimeError(f"Unsupported MIGRATION_TARGET={target!r}")


def downgrade() -> None:
    target = _target()
    if target == "content":
        _drop_content_database()
        return
    if target == "identity":
        _drop_identity_database()
        return
    if target == "workers":
        _drop_workers_database()
        return
    raise RuntimeError(f"Unsupported MIGRATION_TARGET={target!r}")


def _create_content_database() -> None:
    _RSS_FEED_RUNTIME_STATUS_ENUM.create(op.get_bind(), checkfirst=True)
    _create_rss_catalog_tables()
    _create_article_storage_tables()
    _create_embedding_tables()


def _create_identity_database() -> None:
    _create_auth_tables()
    _create_api_key_worker_usage_table()


def _create_workers_database() -> None:
    op.execute(sa.text("CREATE SEQUENCE IF NOT EXISTS worker_task_execution_id_seq AS BIGINT"))
    _create_worker_gateway_tables()
    _create_worker_queue_tables()


def _drop_content_database() -> None:
    for index_name, table_name in (
        ("idx_embedding_manifest_status", "embedding_manifest"),
        ("idx_article_authors_article_id_position", "article_authors"),
        ("idx_article_authors_author_id_article_id", "article_authors"),
        ("idx_article_feed_links_feed_id_article_id", "article_feed_links"),
        ("idx_articles_company_id_published_at", "articles"),
        ("idx_articles_published_at_brin", "articles"),
        ("uq_articles_content_key", "articles"),
        ("idx_rss_feed_tags_tag_id", "rss_feed_tags"),
        ("idx_rss_feed_runtime_last_article_published_at", "rss_feed_runtime"),
        ("idx_rss_feed_runtime_last_status", "rss_feed_runtime"),
        ("idx_rss_feeds_enabled", "rss_feeds"),
        ("idx_rss_feeds_company_id", "rss_feeds"),
        ("idx_rss_company_language", "rss_company"),
        ("idx_rss_company_country", "rss_company"),
    ):
        op.drop_index(index_name, table_name=table_name)

    for table_name in (
        "embedding_manifest",
        "article_authors",
        "authors",
        "article_feed_links",
        "articles",
        "rss_catalog_sync_state",
        "rss_feed_tags",
        "rss_tags",
        "rss_feed_runtime",
        "rss_feeds",
        "rss_company",
    ):
        op.drop_table(table_name)

    _RSS_FEED_RUNTIME_STATUS_ENUM.drop(op.get_bind(), checkfirst=True)


def _drop_identity_database() -> None:
    for index_name, table_name in (
        ("idx_api_key_worker_usages_api_key_seen_at", "api_key_worker_usages"),
        ("idx_api_key_worker_usages_worker_type", "api_key_worker_usages"),
        ("idx_user_api_keys_worker_type", "user_api_keys"),
        ("idx_user_api_keys_user_id", "user_api_keys"),
        ("idx_user_sessions_expires_at", "user_sessions"),
        ("idx_user_sessions_user_id", "user_sessions"),
    ):
        op.drop_index(index_name, table_name=table_name)

    for table_name in (
        "api_key_worker_usages",
        "user_api_keys",
        "user_sessions",
        "users",
    ):
        op.drop_table(table_name)


def _drop_workers_database() -> None:
    for index_name, table_name in (
        ("idx_worker_tasks_status_execution_id", "worker_tasks"),
        ("idx_worker_tasks_claim_expires_at", "worker_tasks"),
        ("idx_worker_tasks_job_id_status", "worker_tasks"),
        ("idx_worker_tasks_task_type_status_requested_at", "worker_tasks"),
        ("idx_worker_jobs_requested_at", "worker_jobs"),
        ("idx_worker_leases_task_type_expires_at", "worker_leases"),
        ("idx_worker_leases_session_expires_at", "worker_leases"),
        ("idx_worker_sessions_api_key_expires_at", "worker_sessions"),
    ):
        op.drop_index(index_name, table_name=table_name)

    for table_name in (
        "worker_tasks",
        "worker_jobs",
        "worker_leases",
        "worker_sessions",
    ):
        op.drop_table(table_name)

    op.execute(sa.text("DROP SEQUENCE IF EXISTS worker_task_execution_id_seq"))


def _create_rss_catalog_tables() -> None:
    op.create_table(
        "rss_company",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("host", sa.String(length=255), nullable=True),
        sa.Column("icon_url", sa.String(length=500), nullable=True),
        sa.Column("country", sa.CHAR(length=2), nullable=True),
        sa.Column("language", sa.CHAR(length=2), nullable=True),
        sa.Column("fetchprotection", sa.SmallInteger(), nullable=False, server_default=sa.text("1")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
        sa.Column("trust_score", sa.Float(), nullable=False, server_default=sa.text("0.5")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
        sa.Column("last_scraped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "last_status",
            _RSS_FEED_RUNTIME_STATUS_ENUM,
            nullable=False,
            server_default=sa.text("'pending'::rss_feed_runtime_status"),
        ),
        sa.Column("etag", sa.String(length=255), nullable=True),
        sa.Column("last_feed_update", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_article_published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_error_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "consecutive_error_count >= 0",
            name="ck_rss_feed_runtime_consecutive_error_count",
        ),
        sa.CheckConstraint(
            "last_error_code IS NULL OR (last_error_code >= 100 AND last_error_code <= 599)",
            name="ck_rss_feed_runtime_last_error_code",
        ),
        sa.ForeignKeyConstraint(["feed_id"], ["rss_feeds.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_rss_feed_runtime_last_status", "rss_feed_runtime", ["last_status"], unique=False)
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

    op.create_table(
        "rss_catalog_sync_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("last_applied_revision", sa.String(length=64), nullable=True),
        sa.Column("last_seen_revision", sa.String(length=64), nullable=True),
        sa.Column("last_sync_status", sa.String(length=20), nullable=False, server_default=sa.text("'success'")),
        sa.Column("last_sync_error", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "last_sync_status IN ('success', 'failed')",
            name="ck_rss_catalog_sync_state_status",
        ),
    )


def _create_auth_tables() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("pseudo", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default=sa.text("'user'")),
        sa.Column("pp_id", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("api_access_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("pp_id >= 1 AND pp_id <= 8", name="ck_users_pp_id"),
        sa.CheckConstraint("role IN ('user', 'admin')", name="ck_users_role"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("pseudo", name="uq_users_pseudo"),
    )

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("token_hash", name="uq_user_sessions_token_hash"),
    )
    op.create_index("idx_user_sessions_user_id", "user_sessions", ["user_id"], unique=False)
    op.create_index("idx_user_sessions_expires_at", "user_sessions", ["expires_at"], unique=False)

    op.create_table(
        "user_api_keys",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("worker_type", sa.String(length=64), nullable=False),
        sa.Column("worker_number", sa.Integer(), nullable=False),
        sa.Column("key_prefix", sa.String(length=32), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("worker_number >= 1", name="ck_user_api_keys_worker_number"),
        sa.CheckConstraint("worker_type IN ('rss_scrapper', 'source_embedding')", name="ck_user_api_keys_worker_type"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("key_hash", name="uq_user_api_keys_key_hash"),
        sa.UniqueConstraint(
            "user_id",
            "worker_type",
            "worker_number",
            name="uq_user_api_keys_user_worker_type_worker_number",
        ),
    )
    op.create_index("idx_user_api_keys_user_id", "user_api_keys", ["user_id"], unique=False)
    op.create_index("idx_user_api_keys_worker_type", "user_api_keys", ["worker_type"], unique=False)


def _create_api_key_worker_usage_table() -> None:
    op.create_table(
        "api_key_worker_usages",
        sa.Column("api_key_id", sa.Integer(), nullable=False),
        sa.Column("worker_name", sa.String(length=100), nullable=False),
        sa.Column("worker_type", sa.String(length=64), nullable=False),
        sa.Column("worker_version", sa.String(length=80), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("use_count", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.CheckConstraint("use_count >= 1", name="ck_api_key_worker_usages_use_count"),
        sa.CheckConstraint(
            "worker_type IN ('rss_scrapper', 'source_embedding')",
            name="ck_api_key_worker_usages_worker_type",
        ),
        sa.ForeignKeyConstraint(["api_key_id"], ["user_api_keys.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("api_key_id", "worker_name"),
    )
    op.create_index(
        "idx_api_key_worker_usages_api_key_seen_at",
        "api_key_worker_usages",
        ["api_key_id", "last_seen_at"],
        unique=False,
    )
    op.create_index(
        "idx_api_key_worker_usages_worker_type",
        "api_key_worker_usages",
        ["worker_type"],
        unique=False,
    )


def _create_worker_gateway_tables() -> None:
    op.create_table(
        "worker_sessions",
        sa.Column("session_id", sa.String(length=64), primary_key=True),
        sa.Column("api_key_id", sa.Integer(), nullable=False),
        sa.Column("worker_type", sa.String(length=64), nullable=False),
        sa.Column("worker_version", sa.String(length=80), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("worker_type IN ('rss_scrapper', 'source_embedding')", name="ck_worker_sessions_worker_type"),
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


def _create_article_storage_tables() -> None:
    op.create_table(
        "articles",
        sa.Column("article_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("article_key", sa.CHAR(length=64), nullable=False),
        sa.Column("content_key", sa.CHAR(length=64), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("canonical_url", sa.String(length=1000), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(length=1000), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=True),
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["rss_company.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("article_key", name="uq_articles_article_key"),
    )
    op.create_index(
        "idx_articles_published_at_brin",
        "articles",
        ["published_at"],
        unique=False,
        postgresql_using="brin",
    )
    op.create_index(
        "idx_articles_company_id_published_at",
        "articles",
        ["company_id", "published_at"],
        unique=False,
    )
    op.create_index(
        "uq_articles_content_key",
        "articles",
        ["content_key"],
        unique=True,
        postgresql_where=sa.text("content_key IS NOT NULL"),
    )

    op.create_table(
        "authors",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("normalized_name", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.UniqueConstraint("normalized_name", name="uq_authors_normalized_name"),
    )

    op.create_table(
        "article_authors",
        sa.Column("article_id", sa.BigInteger(), nullable=False),
        sa.Column("author_id", sa.BigInteger(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["articles.article_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["authors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("article_id", "author_id"),
        sa.UniqueConstraint("article_id", "position", name="uq_article_authors_article_position"),
    )
    op.create_index(
        "idx_article_authors_author_id_article_id",
        "article_authors",
        ["author_id", "article_id"],
        unique=False,
    )
    op.create_index(
        "idx_article_authors_article_id_position",
        "article_authors",
        ["article_id", "position"],
        unique=False,
    )

    op.create_table(
        "article_feed_links",
        sa.Column("article_id", sa.BigInteger(), nullable=False),
        sa.Column("feed_id", sa.Integer(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["article_id"], ["articles.article_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["feed_id"], ["rss_feeds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("article_id", "feed_id"),
    )
    op.create_index(
        "idx_article_feed_links_feed_id_article_id",
        "article_feed_links",
        ["feed_id", "article_id"],
        unique=False,
    )


def _create_embedding_tables() -> None:
    op.create_table(
        "embedding_manifest",
        sa.Column("article_id", sa.BigInteger(), nullable=False),
        sa.Column("worker_version", sa.String(length=80), nullable=False),
        sa.Column("model_name", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("qdrant_point_id", sa.String(length=64), nullable=True),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.CheckConstraint("status IN ('indexed', 'failed')", name="ck_embedding_manifest_status"),
        sa.ForeignKeyConstraint(["article_id"], ["articles.article_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("article_id", "worker_version"),
    )
    op.create_index("idx_embedding_manifest_status", "embedding_manifest", ["status"], unique=False)


def _create_worker_queue_tables() -> None:
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
            "status IN ('queued', 'processing', 'finalizing', 'completed', 'completed_with_errors', 'failed')",
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
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
        sa.ForeignKeyConstraint(["job_id"], ["worker_jobs.job_id"], ondelete="CASCADE"),
        sa.CheckConstraint("task_type IN ('rss.fetch', 'embed.source')", name="ck_worker_tasks_task_type"),
        sa.CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed')", name="ck_worker_tasks_status"),
        sa.CheckConstraint("attempt_count >= 0", name="ck_worker_tasks_attempt_count"),
        sa.CheckConstraint("item_total >= 0", name="ck_worker_tasks_item_total"),
        sa.CheckConstraint("item_success >= 0", name="ck_worker_tasks_item_success"),
        sa.CheckConstraint("item_error >= 0", name="ck_worker_tasks_item_error"),
    )
    op.create_index(
        "idx_worker_tasks_task_type_status_requested_at",
        "worker_tasks",
        ["task_type", "status", "requested_at"],
        unique=False,
    )
    op.create_index(
        "idx_worker_tasks_status_execution_id",
        "worker_tasks",
        ["status", "execution_id"],
        unique=False,
    )
    op.create_index("idx_worker_tasks_job_id_status", "worker_tasks", ["job_id", "status"], unique=False)
    op.create_index("idx_worker_tasks_claim_expires_at", "worker_tasks", ["claim_expires_at"], unique=False)
