"""enable pgcrypto for rss finalizer bulk merge

Revision ID: v1_3_enable_pgcrypto
Revises: v1_2_rss_task_feed_unique
Create Date: 2026-03-17 18:00:00.000000

"""

from __future__ import annotations

from alembic import op


revision = "v1_3_enable_pgcrypto"
down_revision = "v1_2_rss_task_feed_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
