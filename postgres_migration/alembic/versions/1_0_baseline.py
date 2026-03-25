"""baseline schema for current runtime

Revision ID: 1_0_baseline
Revises:
Create Date: 2026-03-24 00:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "1_0_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
	_create_rss_catalog_tables()
	_create_auth_tables()
	_create_worker_gateway_tables()
	_create_article_storage_tables()
	_create_staging_tables()
	_create_embedding_tables()
	_create_audit_tables()
	_create_worker_queue_tables()


def downgrade() -> None:
	for index_name, table_name in (
		("idx_worker_tasks_claim_expires_at", "worker_tasks"),
		("idx_worker_tasks_job_id_status", "worker_tasks"),
		("idx_worker_tasks_task_type_status_requested_at", "worker_tasks"),
		("idx_worker_jobs_requested_at", "worker_jobs"),
		("idx_embedding_dead_letters_trace_id", "embedding_dead_letters"),
		("idx_embedding_dead_letters_article_key_created_at", "embedding_dead_letters"),
		("idx_dedup_decisions_article_key_decided_at", "dedup_decisions"),
		("idx_ingest_events_trace_id_created_at", "ingest_events"),
		("idx_embedding_manifest_article_key_status", "embedding_manifest"),
		("idx_staging_embedding_results_trace_id", "staging_embedding_results"),
		("idx_staging_embedding_results_article_key", "staging_embedding_results"),
		("idx_staging_embedding_requests_article_id_requested_at", "staging_embedding_requests"),
		("idx_staging_article_candidates_trace_id", "staging_article_candidates"),
		("idx_staging_article_candidates_article_key", "staging_article_candidates"),
		("idx_staging_feed_fetch_results_feed_id_fetched_at", "staging_feed_fetch_results"),
		("idx_staging_feed_fetch_results_trace_id", "staging_feed_fetch_results"),
		("idx_article_versions_article_id_captured_at", "article_versions"),
		("idx_article_feed_links_feed_id_last_seen_at", "article_feed_links"),
		("idx_articles_company_id_published_at", "articles"),
		("idx_articles_published_at_brin", "articles"),
		("idx_articles_shard_id_article_id", "articles"),
		("idx_worker_runtime_snapshots_session_seen_at", "worker_runtime_snapshots"),
		("idx_worker_leases_queue_lane_issued_at", "worker_leases"),
		("idx_worker_leases_task_type_expires_at", "worker_leases"),
		("idx_worker_leases_session_expires_at", "worker_leases"),
		("idx_worker_sessions_last_seen_at", "worker_sessions"),
		("idx_worker_sessions_api_key_expires_at", "worker_sessions"),
		("idx_user_api_keys_worker_type", "user_api_keys"),
		("idx_user_api_keys_user_id", "user_api_keys"),
		("idx_user_sessions_expires_at", "user_sessions"),
		("idx_user_sessions_user_id", "user_sessions"),
		("idx_rss_feed_tags_tag_id", "rss_feed_tags"),
		("idx_rss_feed_runtime_last_article_published_at", "rss_feed_runtime"),
		("idx_rss_feed_runtime_last_success_at", "rss_feed_runtime"),
		("idx_rss_feed_runtime_last_status", "rss_feed_runtime"),
		("idx_rss_feeds_enabled", "rss_feeds"),
		("idx_rss_feeds_company_id", "rss_feeds"),
		("idx_rss_company_language", "rss_company"),
		("idx_rss_company_country", "rss_company"),
	):
		op.drop_index(index_name, table_name=table_name)

	for table_name in (
		"worker_tasks",
		"worker_jobs",
		"embedding_dead_letters",
		"dedup_decisions",
		"ingest_events",
		"embedding_manifest",
		"staging_embedding_results",
		"staging_embedding_requests",
		"staging_article_candidates",
		"staging_feed_fetch_results",
		"article_versions",
		"article_feed_links",
		"articles",
		"worker_quotas",
		"worker_runtime_snapshots",
		"worker_leases",
		"worker_sessions",
		"user_api_keys",
		"user_sessions",
		"users",
		"rss_catalog_sync_state",
		"rss_feed_tags",
		"rss_tags",
		"rss_feed_runtime",
		"rss_feeds",
		"rss_company",
	):
		op.drop_table(table_name)


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
		sa.CheckConstraint("fetchprotection >= 0 AND fetchprotection <= 2", name="ck_rss_company_fetchprotection"),
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
		sa.CheckConstraint("trust_score >= 0.0 AND trust_score <= 1.0", name="ck_rss_feeds_trust_score"),
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
		sa.Column("last_status", sa.String(length=32), nullable=False, server_default=sa.text("'pending'")),
		sa.Column("last_scraped_at", sa.DateTime(timezone=True), nullable=True),
		sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
		sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
		sa.Column("last_error_message", sa.Text(), nullable=True),
		sa.Column("consecutive_error_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
		sa.Column("etag", sa.String(length=255), nullable=True),
		sa.Column("last_feed_update", sa.DateTime(timezone=True), nullable=True),
		sa.Column("last_article_published_at", sa.DateTime(timezone=True), nullable=True),
		sa.CheckConstraint("consecutive_error_count >= 0", name="ck_rss_feed_runtime_consecutive_error_count"),
		sa.ForeignKeyConstraint(["feed_id"], ["rss_feeds.id"], ondelete="CASCADE"),
	)
	op.create_index("idx_rss_feed_runtime_last_status", "rss_feed_runtime", ["last_status"], unique=False)
	op.create_index("idx_rss_feed_runtime_last_success_at", "rss_feed_runtime", ["last_success_at"], unique=False)
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
		sa.CheckConstraint("last_sync_status IN ('success', 'failed')", name="ck_rss_catalog_sync_state_status"),
	)


def _create_auth_tables() -> None:
	op.create_table(
		"users",
		sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
		sa.Column("email", sa.String(length=320), nullable=False),
		sa.Column("pseudo", sa.String(length=80), nullable=False),
		sa.Column("password_hash", sa.String(length=255), nullable=False),
		sa.Column("role", sa.String(length=20), nullable=False, server_default=sa.text("'user'")),
		sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
		sa.Column("api_access_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
		sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
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
		sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
		sa.UniqueConstraint("key_hash", name="uq_user_api_keys_key_hash"),
		sa.UniqueConstraint("user_id", "worker_type", "worker_number", name="uq_user_api_keys_user_worker_type_worker_number"),
	)
	op.create_index("idx_user_api_keys_user_id", "user_api_keys", ["user_id"], unique=False)
	op.create_index("idx_user_api_keys_worker_type", "user_api_keys", ["worker_type"], unique=False)


def _create_worker_gateway_tables() -> None:
	op.create_table(
		"worker_sessions",
		sa.Column("session_id", sa.String(length=64), primary_key=True),
		sa.Column("api_key_id", sa.Integer(), nullable=False),
		sa.Column("worker_type", sa.String(length=64), nullable=False),
		sa.Column("worker_class", sa.String(length=32), nullable=False),
		sa.Column("worker_version", sa.String(length=80), nullable=True),
		sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
		sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.Column("connection_state", sa.String(length=32), nullable=False),
		sa.Column("client_fingerprint", sa.String(length=255), nullable=True),
		sa.ForeignKeyConstraint(["api_key_id"], ["user_api_keys.id"], ondelete="CASCADE"),
	)
	op.create_index("idx_worker_sessions_api_key_expires_at", "worker_sessions", ["api_key_id", "expires_at"], unique=False)
	op.create_index("idx_worker_sessions_last_seen_at", "worker_sessions", ["last_seen_at"], unique=False)

	op.create_table(
		"worker_leases",
		sa.Column("lease_id", sa.String(length=64), primary_key=True),
		sa.Column("session_id", sa.String(length=64), nullable=False),
		sa.Column("task_type", sa.String(length=64), nullable=False),
		sa.Column("queue_lane", sa.String(length=32), nullable=False),
		sa.Column("payload_ref", sa.String(length=255), nullable=False),
		sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
		sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
		sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
		sa.Column("result_nonce", sa.String(length=64), nullable=True),
		sa.Column("signature_hash", sa.String(length=64), nullable=False),
		sa.ForeignKeyConstraint(["session_id"], ["worker_sessions.session_id"], ondelete="CASCADE"),
	)
	op.create_index("idx_worker_leases_session_expires_at", "worker_leases", ["session_id", "expires_at"], unique=False)
	op.create_index("idx_worker_leases_task_type_expires_at", "worker_leases", ["task_type", "expires_at"], unique=False)
	op.create_index("idx_worker_leases_queue_lane_issued_at", "worker_leases", ["queue_lane", "issued_at"], unique=False)

	op.create_table(
		"worker_runtime_snapshots",
		sa.Column("snapshot_id", sa.BigInteger(), primary_key=True, autoincrement=True),
		sa.Column("session_id", sa.String(length=64), nullable=False),
		sa.Column("seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.Column("active_task_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
		sa.Column("current_task_label", sa.String(length=255), nullable=True),
		sa.Column("last_error", sa.Text(), nullable=True),
		sa.Column("network_in_bytes", sa.BigInteger(), nullable=True),
		sa.Column("network_out_bytes", sa.BigInteger(), nullable=True),
		sa.Column("cpu_hint", sa.Float(), nullable=True),
		sa.Column("gpu_hint", sa.Float(), nullable=True),
		sa.CheckConstraint("active_task_count >= 0", name="ck_worker_runtime_snapshots_active_task_count"),
		sa.CheckConstraint("network_in_bytes IS NULL OR network_in_bytes >= 0", name="ck_worker_runtime_snapshots_network_in_bytes"),
		sa.CheckConstraint("network_out_bytes IS NULL OR network_out_bytes >= 0", name="ck_worker_runtime_snapshots_network_out_bytes"),
		sa.ForeignKeyConstraint(["session_id"], ["worker_sessions.session_id"], ondelete="CASCADE"),
	)
	op.create_index(
		"idx_worker_runtime_snapshots_session_seen_at",
		"worker_runtime_snapshots",
		["session_id", "seen_at"],
		unique=False,
	)

	op.create_table(
		"worker_quotas",
		sa.Column("quota_id", sa.BigInteger(), primary_key=True, autoincrement=True),
		sa.Column("scope_type", sa.String(length=32), nullable=False),
		sa.Column("scope_id", sa.String(length=128), nullable=False),
		sa.Column("task_type", sa.String(length=64), nullable=False),
		sa.Column("max_parallelism", sa.Integer(), nullable=False, server_default=sa.text("1")),
		sa.Column("max_rps", sa.Float(), nullable=True),
		sa.Column("max_daily_results", sa.Integer(), nullable=True),
		sa.Column("priority_weight", sa.Float(), nullable=False, server_default=sa.text("1.0")),
		sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.CheckConstraint("max_parallelism >= 0", name="ck_worker_quotas_max_parallelism"),
		sa.CheckConstraint("max_rps IS NULL OR max_rps >= 0", name="ck_worker_quotas_max_rps"),
		sa.CheckConstraint("max_daily_results IS NULL OR max_daily_results >= 0", name="ck_worker_quotas_max_daily_results"),
		sa.UniqueConstraint("scope_type", "scope_id", "task_type", name="uq_worker_quotas_scope_task_type"),
	)


def _create_article_storage_tables() -> None:
	op.create_table(
		"articles",
		sa.Column("article_id", sa.BigInteger(), primary_key=True, autoincrement=True),
		sa.Column("article_key", sa.CHAR(length=64), nullable=False),
		sa.Column("shard_id", sa.Integer(), nullable=False),
		sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
		sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.Column("canonical_url", sa.String(length=1000), nullable=True),
		sa.Column("title", sa.Text(), nullable=True),
		sa.Column("summary", sa.Text(), nullable=True),
		sa.Column("author", sa.Text(), nullable=True),
		sa.Column("image_url", sa.String(length=1000), nullable=True),
		sa.Column("language", sa.String(length=16), nullable=True),
		sa.Column("company_id", sa.Integer(), nullable=True),
		sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.Column("last_rss_job_at", sa.DateTime(timezone=True), nullable=True),
		sa.CheckConstraint("shard_id >= 0", name="ck_articles_shard_id"),
		sa.ForeignKeyConstraint(["company_id"], ["rss_company.id"], ondelete="SET NULL"),
		sa.UniqueConstraint("article_key", name="uq_articles_article_key"),
	)
	op.create_index("idx_articles_shard_id_article_id", "articles", ["shard_id", "article_id"], unique=False)
	op.create_index("idx_articles_published_at_brin", "articles", ["published_at"], unique=False, postgresql_using="brin")
	op.create_index("idx_articles_company_id_published_at", "articles", ["company_id", "published_at"], unique=False)

	op.create_table(
		"article_feed_links",
		sa.Column("article_id", sa.BigInteger(), nullable=False),
		sa.Column("feed_id", sa.Integer(), nullable=False),
		sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.Column("last_job_trace_id", sa.String(length=64), nullable=True),
		sa.Column("last_fetch_status", sa.String(length=32), nullable=True),
		sa.ForeignKeyConstraint(["article_id"], ["articles.article_id"], ondelete="CASCADE"),
		sa.ForeignKeyConstraint(["feed_id"], ["rss_feeds.id"], ondelete="CASCADE"),
		sa.PrimaryKeyConstraint("article_id", "feed_id"),
	)
	op.create_index("idx_article_feed_links_feed_id_last_seen_at", "article_feed_links", ["feed_id", "last_seen_at"], unique=False)

	op.create_table(
		"article_versions",
		sa.Column("version_id", sa.BigInteger(), primary_key=True, autoincrement=True),
		sa.Column("article_id", sa.BigInteger(), nullable=False),
		sa.Column("source_hash", sa.CHAR(length=64), nullable=False),
		sa.Column("title", sa.Text(), nullable=True),
		sa.Column("summary", sa.Text(), nullable=True),
		sa.Column("author", sa.Text(), nullable=True),
		sa.Column("image_url", sa.String(length=1000), nullable=True),
		sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.Column("producer_type", sa.String(length=64), nullable=False),
		sa.ForeignKeyConstraint(["article_id"], ["articles.article_id"], ondelete="CASCADE"),
	)
	op.create_index("idx_article_versions_article_id_captured_at", "article_versions", ["article_id", "captured_at"], unique=False)


def _create_staging_tables() -> None:
	op.create_table(
		"staging_feed_fetch_results",
		sa.Column("buffer_id", sa.BigInteger(), primary_key=True, autoincrement=True),
		sa.Column("trace_id", sa.String(length=64), nullable=False),
		sa.Column("lease_id", sa.String(length=64), nullable=True),
		sa.Column("worker_class", sa.String(length=32), nullable=False),
		sa.Column("worker_name", sa.String(length=160), nullable=False),
		sa.Column("feed_id", sa.Integer(), nullable=False),
		sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.Column("http_status", sa.Integer(), nullable=True),
		sa.Column("etag", sa.String(length=255), nullable=True),
		sa.Column("body_compressed", postgresql.BYTEA(), nullable=True),
		sa.Column("body_sha256", sa.CHAR(length=64), nullable=True),
		sa.ForeignKeyConstraint(["feed_id"], ["rss_feeds.id"], ondelete="CASCADE"),
		sa.ForeignKeyConstraint(["lease_id"], ["worker_leases.lease_id"], ondelete="SET NULL"),
	)
	op.create_index("idx_staging_feed_fetch_results_trace_id", "staging_feed_fetch_results", ["trace_id"], unique=False)
	op.create_index(
		"idx_staging_feed_fetch_results_feed_id_fetched_at",
		"staging_feed_fetch_results",
		["feed_id", "fetched_at"],
		unique=False,
	)

	op.create_table(
		"staging_article_candidates",
		sa.Column("candidate_id", sa.BigInteger(), primary_key=True, autoincrement=True),
		sa.Column("trace_id", sa.String(length=64), nullable=False),
		sa.Column("article_key", sa.CHAR(length=64), nullable=False),
		sa.Column("shard_id", sa.Integer(), nullable=False),
		sa.Column("feed_id", sa.Integer(), nullable=False),
		sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
		sa.Column("canonical_url", sa.String(length=1000), nullable=True),
		sa.Column("title", sa.Text(), nullable=True),
		sa.Column("summary", sa.Text(), nullable=True),
		sa.Column("author", sa.Text(), nullable=True),
		sa.Column("image_url", sa.String(length=1000), nullable=True),
		sa.Column("duplicate_hint", sa.Boolean(), nullable=False, server_default=sa.text("false")),
		sa.CheckConstraint("shard_id >= 0", name="ck_staging_article_candidates_shard_id"),
		sa.ForeignKeyConstraint(["feed_id"], ["rss_feeds.id"], ondelete="CASCADE"),
	)
	op.create_index("idx_staging_article_candidates_article_key", "staging_article_candidates", ["article_key"], unique=False)
	op.create_index("idx_staging_article_candidates_trace_id", "staging_article_candidates", ["trace_id"], unique=False)

	op.create_table(
		"staging_embedding_requests",
		sa.Column("request_id", sa.BigInteger(), primary_key=True, autoincrement=True),
		sa.Column("article_id", sa.BigInteger(), nullable=False),
		sa.Column("article_key", sa.CHAR(length=64), nullable=False),
		sa.Column("worker_version", sa.String(length=80), nullable=False),
		sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("0")),
		sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.Column("source_text_checksum", sa.CHAR(length=64), nullable=False),
		sa.ForeignKeyConstraint(["article_id"], ["articles.article_id"], ondelete="CASCADE"),
	)
	op.create_index(
		"idx_staging_embedding_requests_article_id_requested_at",
		"staging_embedding_requests",
		["article_id", "requested_at"],
		unique=False,
	)

	op.create_table(
		"staging_embedding_results",
		sa.Column("result_id", sa.BigInteger(), primary_key=True, autoincrement=True),
		sa.Column("trace_id", sa.String(length=64), nullable=False),
		sa.Column("lease_id", sa.String(length=64), nullable=True),
		sa.Column("article_key", sa.CHAR(length=64), nullable=False),
		sa.Column("worker_version", sa.String(length=80), nullable=False),
		sa.Column("vector_checksum", sa.CHAR(length=64), nullable=False),
		sa.Column("dimensions", sa.Integer(), nullable=False),
		sa.Column("norm", sa.Float(), nullable=True),
		sa.Column("worker_class", sa.String(length=32), nullable=False),
		sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.CheckConstraint("dimensions > 0", name="ck_staging_embedding_results_dimensions"),
		sa.ForeignKeyConstraint(["lease_id"], ["worker_leases.lease_id"], ondelete="SET NULL"),
	)
	op.create_index("idx_staging_embedding_results_article_key", "staging_embedding_results", ["article_key"], unique=False)
	op.create_index("idx_staging_embedding_results_trace_id", "staging_embedding_results", ["trace_id"], unique=False)


def _create_embedding_tables() -> None:
	op.create_table(
		"embedding_manifest",
		sa.Column("article_id", sa.BigInteger(), nullable=False),
		sa.Column("article_key", sa.CHAR(length=64), nullable=False),
		sa.Column("worker_version", sa.String(length=80), nullable=False),
		sa.Column("index_backend", sa.String(length=64), nullable=False),
		sa.Column("dimensions", sa.Integer(), nullable=False),
		sa.Column("vector_checksum", sa.CHAR(length=64), nullable=False),
		sa.Column("status", sa.String(length=32), nullable=False),
		sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
		sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
		sa.Column("failure_reason", sa.Text(), nullable=True),
		sa.Column("source_worker_class", sa.String(length=32), nullable=True),
		sa.CheckConstraint("dimensions > 0", name="ck_embedding_manifest_dimensions"),
		sa.ForeignKeyConstraint(["article_id"], ["articles.article_id"], ondelete="CASCADE"),
		sa.PrimaryKeyConstraint("article_id", "worker_version"),
	)
	op.create_index("idx_embedding_manifest_article_key_status", "embedding_manifest", ["article_key", "status"], unique=False)

	op.create_table(
		"embedding_dead_letters",
		sa.Column("dead_letter_id", sa.BigInteger(), primary_key=True, autoincrement=True),
		sa.Column("trace_id", sa.String(length=64), nullable=False),
		sa.Column("article_key", sa.CHAR(length=64), nullable=False),
		sa.Column("worker_version", sa.String(length=80), nullable=False),
		sa.Column("reason_code", sa.String(length=64), nullable=False),
		sa.Column("reason_message", sa.Text(), nullable=False),
		sa.Column("payload_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
		sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
	)
	op.create_index(
		"idx_embedding_dead_letters_article_key_created_at",
		"embedding_dead_letters",
		["article_key", "created_at"],
		unique=False,
	)
	op.create_index("idx_embedding_dead_letters_trace_id", "embedding_dead_letters", ["trace_id"], unique=False)


def _create_audit_tables() -> None:
	op.create_table(
		"ingest_events",
		sa.Column("event_id", sa.BigInteger(), primary_key=True, autoincrement=True),
		sa.Column("trace_id", sa.String(length=64), nullable=False),
		sa.Column("stage", sa.String(length=64), nullable=False),
		sa.Column("event_type", sa.String(length=64), nullable=False),
		sa.Column("severity", sa.String(length=16), nullable=False),
		sa.Column("object_type", sa.String(length=64), nullable=False),
		sa.Column("object_key", sa.String(length=255), nullable=False),
		sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
		sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
	)
	op.create_index("idx_ingest_events_trace_id_created_at", "ingest_events", ["trace_id", "created_at"], unique=False)

	op.create_table(
		"dedup_decisions",
		sa.Column("decision_id", sa.BigInteger(), primary_key=True, autoincrement=True),
		sa.Column("article_key", sa.CHAR(length=64), nullable=False),
		sa.Column("decision", sa.String(length=32), nullable=False),
		sa.Column("source", sa.String(length=32), nullable=False),
		sa.Column("trace_id", sa.String(length=64), nullable=True),
		sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
	)
	op.create_index("idx_dedup_decisions_article_key_decided_at", "dedup_decisions", ["article_key", "decided_at"], unique=False)


def _create_worker_queue_tables() -> None:
	op.create_table(
		"worker_jobs",
		sa.Column("job_id", sa.String(length=64), primary_key=True),
		sa.Column("job_kind", sa.String(length=32), nullable=False),
		sa.Column("task_type", sa.String(length=64), nullable=False),
		sa.Column("queue_lane", sa.String(length=32), nullable=True),
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
		sa.Column("queue_lane", sa.String(length=32), nullable=True),
		sa.Column("worker_version", sa.String(length=80), nullable=True),
		sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
		sa.Column("last_trace_id", sa.String(length=64), nullable=True),
		sa.Column("lease_id", sa.String(length=64), nullable=True),
		sa.ForeignKeyConstraint(["job_id"], ["worker_jobs.job_id"], ondelete="CASCADE"),
		sa.ForeignKeyConstraint(["lease_id"], ["worker_leases.lease_id"], ondelete="SET NULL"),
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
	op.create_index("idx_worker_tasks_job_id_status", "worker_tasks", ["job_id", "status"], unique=False)
	op.create_index("idx_worker_tasks_claim_expires_at", "worker_tasks", ["claim_expires_at"], unique=False)
