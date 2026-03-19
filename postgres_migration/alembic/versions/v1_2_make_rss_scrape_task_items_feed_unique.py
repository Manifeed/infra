"""make rss scrape task items feed unique

Revision ID: v1_2_rss_task_feed_unique
Revises: v1_1_add_rss_catalog_sync_state
Create Date: 2026-03-16 12:00:00.000000

"""

from __future__ import annotations

from alembic import op


revision = "v1_2_rss_task_feed_unique"
down_revision = "v1_1_add_rss_catalog_sync_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        WITH ranked_items AS (
            SELECT
                task_id,
                feed_id,
                ROW_NUMBER() OVER (
                    PARTITION BY feed_id
                    ORDER BY task_id DESC
                ) AS row_number
            FROM rss_scrape_task_items
        )
        DELETE FROM rss_scrape_task_items AS item
        USING ranked_items
        WHERE item.task_id = ranked_items.task_id
            AND item.feed_id = ranked_items.feed_id
            AND ranked_items.row_number > 1
        """
    )
    op.drop_index("idx_rss_scrape_task_items_feed_id", table_name="rss_scrape_task_items")
    op.create_unique_constraint(
        "uq_rss_scrape_task_items_feed_id",
        "rss_scrape_task_items",
        ["feed_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_rss_scrape_task_items_feed_id",
        "rss_scrape_task_items",
        type_="unique",
    )
    op.create_index(
        "idx_rss_scrape_task_items_feed_id",
        "rss_scrape_task_items",
        ["feed_id"],
        unique=False,
    )
