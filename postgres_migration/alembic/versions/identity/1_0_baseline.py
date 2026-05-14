"""identity database baseline

Revision ID: 1_0
Revises:
Create Date: 2026-05-14 00:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "1_0"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
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
    op.create_index(
        "idx_user_sessions_revoked_retention",
        "user_sessions",
        ["revoked_at"],
        unique=False,
        postgresql_where=sa.text("revoked_at IS NOT NULL"),
    )
    op.create_index(
        "idx_user_sessions_user_active",
        "user_sessions",
        ["user_id", "expires_at"],
        unique=False,
        postgresql_where=sa.text("revoked_at IS NULL"),
    )

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
        sa.CheckConstraint("worker_type IN ('rss_scrapper')", name="ck_user_api_keys_worker_type"),
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
    op.execute(
        sa.text(
            """
            CREATE INDEX idx_user_api_keys_user_active_created
            ON user_api_keys (user_id, created_at DESC, id DESC)
            WHERE revoked_at IS NULL
            """
        )
    )

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
        sa.CheckConstraint("worker_type IN ('rss_scrapper')", name="ck_api_key_worker_usages_worker_type"),
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


def downgrade() -> None:
    op.drop_index("idx_api_key_worker_usages_worker_type", table_name="api_key_worker_usages")
    op.drop_index("idx_api_key_worker_usages_api_key_seen_at", table_name="api_key_worker_usages")
    op.drop_table("api_key_worker_usages")

    op.execute(sa.text("DROP INDEX IF EXISTS idx_user_api_keys_user_active_created"))
    op.drop_index("idx_user_api_keys_worker_type", table_name="user_api_keys")
    op.drop_index("idx_user_api_keys_user_id", table_name="user_api_keys")
    op.drop_table("user_api_keys")

    op.drop_index("idx_user_sessions_user_active", table_name="user_sessions")
    op.drop_index("idx_user_sessions_revoked_retention", table_name="user_sessions")
    op.drop_index("idx_user_sessions_expires_at", table_name="user_sessions")
    op.drop_index("idx_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")

    op.drop_table("users")
