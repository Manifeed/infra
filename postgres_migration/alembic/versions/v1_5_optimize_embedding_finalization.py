"""optimize embedding finalization access paths

Revision ID: v1_5_embed_finalization_idx
Revises: v1_4_rss_source_identity
Create Date: 2026-03-18 13:45:00.000000

"""

from __future__ import annotations

from alembic import op


revision = "v1_5_embed_finalization_idx"
down_revision = "v1_4_rss_source_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_rss_embedding_results_job_latest
        ON rss_embedding_results (
            job_id,
            source_id,
            embedding_model_id,
            created_at DESC,
            id DESC
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_rss_source_embeddings_model_source
        ON rss_source_embeddings (
            embedding_model_id,
            source_id
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_rss_source_embeddings_model_source")
    op.execute("DROP INDEX IF EXISTS idx_rss_embedding_results_job_latest")
