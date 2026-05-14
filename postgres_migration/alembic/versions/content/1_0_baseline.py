"""content database baseline

Revision ID: 1_0
Revises:
Create Date: 2026-05-14 00:00:00.000000

"""

from __future__ import annotations

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


def upgrade() -> None:
    _RSS_FEED_RUNTIME_STATUS_ENUM.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "rss_company",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("host", sa.String(length=255), nullable=True),
        sa.Column("icon_url", sa.String(length=500), nullable=True),
        sa.Column("country", sa.CHAR(length=2), nullable=False, server_default=sa.text("'xx'")),
        sa.Column("fetchprotection", sa.SmallInteger(), nullable=False, server_default=sa.text("1")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.CheckConstraint(
            "fetchprotection >= 0 AND fetchprotection <= 2",
            name="ck_rss_company_fetchprotection",
        ),
        sa.UniqueConstraint("name", name="uq_rss_company_name"),
    )
    op.create_index("idx_rss_company_country", "rss_company", ["country"], unique=False)

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
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.Column("country", sa.String(length=2), nullable=False, server_default=sa.text("'xx'")),
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
    op.create_index(
        "idx_articles_country_published_at",
        "articles",
        ["country", "published_at"],
        unique=False,
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_articles_search_text_gin
            ON articles
            USING GIN (
                to_tsvector('simple', COALESCE(title, '') || ' ' || COALESCE(summary, ''))
            )
            """
        )
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

    op.create_table(
        "article_url",
        sa.Column("article_url_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("article_id", sa.BigInteger(), nullable=False),
        sa.Column("url", sa.String(length=4000), nullable=False),
        sa.Column("normalized_url", sa.String(length=1000), nullable=False),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["article_id"], ["articles.article_id"], ondelete="CASCADE"),
        sa.UniqueConstraint("normalized_url", name="uq_article_url_normalized_url"),
    )
    op.create_index("idx_article_url_article_id", "article_url", ["article_id"], unique=False)

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


def downgrade() -> None:
    op.drop_index("idx_embedding_manifest_model_name", table_name="embedding_manifest")
    op.drop_index("idx_embedding_manifest_status", table_name="embedding_manifest")
    op.drop_table("embedding_manifest")

    op.drop_index("idx_article_url_article_id", table_name="article_url")
    op.drop_table("article_url")

    op.drop_index("idx_article_feed_links_feed_id_article_id", table_name="article_feed_links")
    op.drop_table("article_feed_links")

    op.drop_index("idx_article_authors_article_id_position", table_name="article_authors")
    op.drop_index("idx_article_authors_author_id_article_id", table_name="article_authors")
    op.drop_table("article_authors")
    op.drop_table("authors")

    op.execute(sa.text("DROP INDEX IF EXISTS idx_articles_search_text_gin"))
    op.drop_index("idx_articles_country_published_at", table_name="articles")
    op.drop_index("uq_articles_content_key", table_name="articles")
    op.drop_index("idx_articles_company_id_published_at", table_name="articles")
    op.drop_index("idx_articles_published_at_brin", table_name="articles")
    op.drop_table("articles")

    op.drop_table("rss_catalog_sync_state")

    op.drop_index("idx_rss_feed_tags_tag_id", table_name="rss_feed_tags")
    op.drop_table("rss_feed_tags")
    op.drop_table("rss_tags")

    op.drop_index("idx_rss_feed_runtime_last_article_published_at", table_name="rss_feed_runtime")
    op.drop_index("idx_rss_feed_runtime_last_status", table_name="rss_feed_runtime")
    op.drop_table("rss_feed_runtime")

    op.drop_index("idx_rss_feeds_enabled", table_name="rss_feeds")
    op.drop_index("idx_rss_feeds_company_id", table_name="rss_feeds")
    op.drop_table("rss_feeds")

    op.drop_index("idx_rss_company_country", table_name="rss_company")
    op.drop_table("rss_company")

    _RSS_FEED_RUNTIME_STATUS_ENUM.drop(op.get_bind(), checkfirst=True)
