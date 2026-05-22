"""simplify indexing manifests

Revision ID: 1_4
Revises: 1_3
Create Date: 2026-05-22 12:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "1_4"
down_revision = "1_3"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def _drop_index_if_exists(*, table_name: str, index_name: str) -> None:
    if not _table_exists(table_name):
        return
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_indexes = {index["name"] for index in inspector.get_indexes(table_name)}
    if index_name in existing_indexes:
        op.drop_index(index_name, table_name=table_name)


def _drop_column_if_exists(*, table_name: str, column_name: str) -> None:
    if not _table_exists(table_name):
        return
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
    if column_name in existing_columns:
        op.drop_column(table_name, column_name)


def upgrade() -> None:
    _drop_index_if_exists(
        table_name="embedding_manifest",
        index_name="idx_embedding_manifest_model_name",
    )
    _drop_column_if_exists(table_name="embedding_manifest", column_name="qdrant_point_id")
    _drop_column_if_exists(table_name="embedding_manifest", column_name="model_name")

    _drop_index_if_exists(table_name="points_article", index_name="idx_points_article_model_name")
    _drop_column_if_exists(table_name="points_article", column_name="model_name")

    _drop_index_if_exists(
        table_name="article_theme_manifest",
        index_name="idx_article_theme_manifest_model_name",
    )
    _drop_column_if_exists(table_name="article_theme_manifest", column_name="model_name")

    _drop_index_if_exists(
        table_name="article_ner_manifest",
        index_name="idx_article_ner_manifest_model_name",
    )
    _drop_column_if_exists(table_name="article_ner_manifest", column_name="model_name")


def downgrade() -> None:
    op.add_column(
        "article_ner_manifest",
        sa.Column(
            "model_name",
            sa.String(length=160),
            nullable=False,
            server_default="urchade/gliner_multi-v2.1",
        ),
    )
    op.create_index(
        "idx_article_ner_manifest_model_name",
        "article_ner_manifest",
        ["model_name"],
        unique=False,
    )

    op.add_column(
        "article_theme_manifest",
        sa.Column(
            "model_name",
            sa.String(length=160),
            nullable=False,
            server_default="manifeed-theme-classifier",
        ),
    )
    op.create_index(
        "idx_article_theme_manifest_model_name",
        "article_theme_manifest",
        ["model_name"],
        unique=False,
    )

    op.add_column(
        "points_article",
        sa.Column(
            "model_name",
            sa.String(length=160),
            nullable=False,
            server_default="BAAI/bge-m3",
        ),
    )
    op.create_index("idx_points_article_model_name", "points_article", ["model_name"], unique=False)

    op.add_column(
        "embedding_manifest",
        sa.Column("model_name", sa.String(length=160), nullable=False, server_default="BAAI/bge-m3"),
    )
    op.add_column(
        "embedding_manifest",
        sa.Column("qdrant_point_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "idx_embedding_manifest_model_name",
        "embedding_manifest",
        ["model_name"],
        unique=False,
    )
