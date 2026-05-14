"""switch embeddings to bge-m3 manifests and RSS-only worker keys

Revision ID: 1_5
Revises: 1_4
Create Date: 2026-05-06 00:00:00.000000

"""

from __future__ import annotations

import os

from alembic import op
import sqlalchemy as sa


revision = "1_5"
down_revision = "1_4"
branch_labels = None
depends_on = None


def _target() -> str:
    return os.getenv("MIGRATION_TARGET", "content").strip().lower()


def upgrade() -> None:
    target = _target()
    if target == "content":
        _upgrade_content()
    elif target == "identity":
        _upgrade_identity()
    elif target == "workers":
        _upgrade_workers()


def downgrade() -> None:
    target = _target()
    if target == "content":
        _downgrade_content()
    elif target == "identity":
        _downgrade_identity()
    elif target == "workers":
        _downgrade_workers()


def _upgrade_content() -> None:
    op.drop_index("idx_embedding_manifest_status", table_name="embedding_manifest")
    op.drop_table("embedding_manifest")
    op.create_table(
        "embedding_manifest",
        sa.Column("article_id", sa.BigInteger(), nullable=False),
        sa.Column("model_name", sa.String(length=160), nullable=False, server_default="BAAI/bge-m3"),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("qdrant_point_id", sa.String(length=64), nullable=True),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("status IN ('indexed', 'failed')", name="ck_embedding_manifest_status"),
        sa.ForeignKeyConstraint(["article_id"], ["articles.article_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("article_id"),
    )
    op.create_index("idx_embedding_manifest_status", "embedding_manifest", ["status"], unique=False)
    op.create_index("idx_embedding_manifest_model_name", "embedding_manifest", ["model_name"], unique=False)


def _upgrade_identity() -> None:
    op.execute(sa.text("DELETE FROM api_key_worker_usages WHERE worker_type = 'source_embedding'"))
    op.execute(sa.text("DELETE FROM user_api_keys WHERE worker_type = 'source_embedding'"))
    op.execute(sa.text("ALTER TABLE user_api_keys DROP CONSTRAINT IF EXISTS ck_user_api_keys_worker_type"))
    op.execute(sa.text("ALTER TABLE api_key_worker_usages DROP CONSTRAINT IF EXISTS ck_api_key_worker_usages_worker_type"))
    op.create_check_constraint(
        "ck_user_api_keys_worker_type",
        "user_api_keys",
        "worker_type IN ('rss_scrapper')",
    )
    op.create_check_constraint(
        "ck_api_key_worker_usages_worker_type",
        "api_key_worker_usages",
        "worker_type IN ('rss_scrapper')",
    )


def _upgrade_workers() -> None:
    op.execute(sa.text("DELETE FROM worker_sessions WHERE worker_type = 'source_embedding'"))
    op.execute(sa.text("ALTER TABLE worker_sessions DROP CONSTRAINT IF EXISTS ck_worker_sessions_worker_type"))
    op.create_check_constraint(
        "ck_worker_sessions_worker_type",
        "worker_sessions",
        "worker_type IN ('rss_scrapper')",
    )
    op.execute(
        sa.text(
            """
            UPDATE worker_jobs
            SET worker_version = NULL
            WHERE job_kind = 'source_embedding'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE worker_tasks
            SET worker_version = NULL
            WHERE task_type = 'embed.source'
            """
        )
    )


def _downgrade_content() -> None:
    op.drop_index("idx_embedding_manifest_model_name", table_name="embedding_manifest")
    op.drop_index("idx_embedding_manifest_status", table_name="embedding_manifest")
    op.drop_table("embedding_manifest")
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


def _downgrade_identity() -> None:
    op.execute(sa.text("ALTER TABLE user_api_keys DROP CONSTRAINT IF EXISTS ck_user_api_keys_worker_type"))
    op.execute(sa.text("ALTER TABLE api_key_worker_usages DROP CONSTRAINT IF EXISTS ck_api_key_worker_usages_worker_type"))
    op.create_check_constraint(
        "ck_user_api_keys_worker_type",
        "user_api_keys",
        "worker_type IN ('rss_scrapper', 'source_embedding')",
    )
    op.create_check_constraint(
        "ck_api_key_worker_usages_worker_type",
        "api_key_worker_usages",
        "worker_type IN ('rss_scrapper', 'source_embedding')",
    )


def _downgrade_workers() -> None:
    op.execute(sa.text("ALTER TABLE worker_sessions DROP CONSTRAINT IF EXISTS ck_worker_sessions_worker_type"))
    op.create_check_constraint(
        "ck_worker_sessions_worker_type",
        "worker_sessions",
        "worker_type IN ('rss_scrapper', 'source_embedding')",
    )
