"""drop embedding projection tables

Revision ID: v1_6_drop_embedding_projection
Revises: v1_5_embed_finalization_idx
Create Date: 2026-03-20 10:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "v1_6_drop_embedding_projection"
down_revision = "v1_5_embed_finalization_idx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS embedding_projection_points")
    op.execute("DROP TABLE IF EXISTS embedding_projections")


def downgrade() -> None:
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
