"""add user auth and worker api keys

Revision ID: v1_7_auth_worker_api_keys
Revises: v1_6_drop_embedding_projection
Create Date: 2026-03-20 00:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "v1_7_auth_worker_api_keys"
down_revision = "v1_6_drop_embedding_projection"
branch_labels = None
depends_on = None

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
worker_auth_purpose_enum = postgresql.ENUM(
    "enroll",
    "auth",
    name="worker_auth_purpose_enum",
    create_type=False,
)


def upgrade() -> None:
    _create_user_tables()
    _replace_worker_runtime_table()
    op.drop_table("worker_capabilities")
    op.drop_table("worker_auth_challenges")
    op.drop_table("worker_registry")
    op.execute("DROP FUNCTION IF EXISTS public.cleanup_expired_worker_auth_challenges(interval)")
    op.execute("DROP TYPE IF EXISTS worker_auth_purpose_enum")


def downgrade() -> None:
    op.drop_table("worker_runtime")
    op.drop_table("user_sessions")
    op.drop_table("user_api_keys")
    op.drop_table("users")

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
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_auth_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("worker_kind", "device_id", name="uq_worker_registry_kind_device"),
        sa.UniqueConstraint("fingerprint", name="uq_worker_registry_fingerprint"),
    )
    op.execute("CREATE TYPE worker_auth_purpose_enum AS ENUM ('enroll', 'auth')")
    op.create_table(
        "worker_auth_challenges",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("worker_id", sa.Integer(), nullable=False),
        sa.Column(
            "purpose",
            worker_auth_purpose_enum,
            nullable=False,
        ),
        sa.Column("challenge", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["worker_id"], ["worker_registry.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "idx_worker_auth_challenges_worker_id_expires_at",
        "worker_auth_challenges",
        ["worker_id", "expires_at"],
        unique=False,
    )
    op.create_table(
        "worker_capabilities",
        sa.Column("worker_id", sa.Integer(), nullable=False),
        sa.Column("job_kind", worker_job_kind_enum, nullable=False),
        sa.Column("embedding_model_id", sa.Integer(), nullable=True),
        sa.Column("max_batch_size", sa.Integer(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.CheckConstraint(
            "max_batch_size IS NULL OR max_batch_size >= 1",
            name="ck_worker_capabilities_max_batch_size",
        ),
        sa.ForeignKeyConstraint(["worker_id"], ["worker_registry.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["embedding_model_id"], ["embedding_models.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("worker_id", "job_kind"),
    )
    op.create_index(
        "idx_worker_capabilities_embedding_model_id",
        "worker_capabilities",
        ["embedding_model_id"],
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
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_job_kind", worker_job_kind_enum, nullable=True),
        sa.Column("current_task_id", sa.BigInteger(), nullable=True),
        sa.Column("current_execution_id", sa.BigInteger(), nullable=True),
        sa.Column("active_claim_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.CheckConstraint("active_claim_count >= 0", name="ck_worker_runtime_active_claim_count"),
        sa.ForeignKeyConstraint(["worker_id"], ["worker_registry.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_worker_runtime_last_seen_at", "worker_runtime", ["last_seen_at"], unique=False)
    op.create_index("idx_worker_runtime_active", "worker_runtime", ["active"], unique=False)


def _create_user_tables() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default=sa.text("'user'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("api_access_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("role IN ('user', 'admin')", name="ck_users_role"),
        sa.UniqueConstraint("email", name="uq_users_email"),
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
        sa.Column(
            "worker_type",
            worker_kind_enum,
            nullable=False,
        ),
        sa.Column("key_prefix", sa.String(length=32), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("key_hash", name="uq_user_api_keys_key_hash"),
    )
    op.create_index("idx_user_api_keys_user_id", "user_api_keys", ["user_id"], unique=False)
    op.create_index("idx_user_api_keys_worker_type", "user_api_keys", ["worker_type"], unique=False)


def _replace_worker_runtime_table() -> None:
    op.drop_table("worker_runtime")
    op.create_table(
        "worker_runtime",
        sa.Column("api_key_id", sa.Integer(), primary_key=True),
        sa.Column("worker_name", sa.String(length=100), nullable=True),
        sa.Column("connection_state", sa.String(length=32), nullable=True),
        sa.Column("desired_state", sa.String(length=32), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_job_kind", worker_job_kind_enum, nullable=True),
        sa.Column("current_task_id", sa.BigInteger(), nullable=True),
        sa.Column("current_execution_id", sa.BigInteger(), nullable=True),
        sa.Column("active_claim_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.CheckConstraint("active_claim_count >= 0", name="ck_worker_runtime_active_claim_count"),
        sa.ForeignKeyConstraint(["api_key_id"], ["user_api_keys.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_worker_runtime_last_seen_at", "worker_runtime", ["last_seen_at"], unique=False)
    op.create_index("idx_worker_runtime_active", "worker_runtime", ["active"], unique=False)
