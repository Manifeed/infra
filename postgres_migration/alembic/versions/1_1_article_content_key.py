"""add article content key for cross-feed deduplication

Revision ID: 1_1_article_content_key
Revises: 1_0_baseline
Create Date: 2026-04-12 00:00:00.000000

"""

from __future__ import annotations

from datetime import datetime
import hashlib
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from alembic import op
import sqlalchemy as sa


revision = "1_1_article_content_key"
down_revision = "1_0_baseline"
branch_labels = None
depends_on = None

_TRACKING_QUERY_PARAM_NAMES = frozenset(
    {
        "_ga",
        "_gl",
        "fbclid",
        "gclid",
        "mc_cid",
        "mc_eid",
        "xtor",
    }
)
_BACKFILL_BATCH_SIZE = 1000


def upgrade() -> None:
    op.add_column(
        "articles",
        sa.Column("content_key", sa.CHAR(length=64), nullable=True),
    )
    op.create_index(
        "idx_articles_content_key",
        "articles",
        ["content_key"],
        unique=False,
        postgresql_where=sa.text("content_key IS NOT NULL"),
    )
    _backfill_article_identity_data()


def downgrade() -> None:
    op.drop_index("idx_articles_content_key", table_name="articles")
    op.drop_column("articles", "content_key")


def _backfill_article_identity_data() -> None:
    bind = op.get_bind()
    article_rows = bind.execute(
        sa.text(
            """
            SELECT
                article.article_id,
                article.canonical_url,
                article.title,
                article.summary,
                article.published_at,
                company.name AS company_name
            FROM articles AS article
            LEFT JOIN rss_company AS company
                ON company.id = article.company_id
            ORDER BY article.article_id ASC
            """
        )
    ).mappings()

    pending_updates: list[dict[str, object]] = []
    while True:
        rows = article_rows.fetchmany(_BACKFILL_BATCH_SIZE)
        if not rows:
            break
        for row in rows:
            raw_canonical_url = (
                str(row["canonical_url"]).strip()
                if row["canonical_url"] is not None
                else None
            )
            normalized_canonical_url = _normalize_source_url(raw_canonical_url)
            pending_updates.append(
                {
                    "article_id": int(row["article_id"]),
                    "canonical_url": normalized_canonical_url,
                    "content_key": _build_article_content_key(
                        title=(str(row["title"]) if row["title"] is not None else None),
                        summary=(str(row["summary"]) if row["summary"] is not None else None),
                        company=(str(row["company_name"]) if row["company_name"] is not None else None),
                        published_at=row["published_at"],
                    ),
                }
            )
        bind.execute(
            sa.text(
                """
                UPDATE articles
                SET
                    canonical_url = :canonical_url,
                    content_key = :content_key
                WHERE article_id = :article_id
                """
            ),
            pending_updates,
        )
        pending_updates.clear()


def _build_article_content_key(
    *,
    title: str | None,
    summary: str | None,
    company: str | None,
    published_at: datetime | None,
) -> str | None:
    normalized_title = _normalize_article_identity_text(title)
    normalized_summary = _normalize_article_identity_text(summary)
    normalized_company = _normalize_article_identity_text(company)
    normalized_published_on = _normalize_article_identity_date(published_at)
    if not all(
        (
            normalized_title,
            normalized_summary,
            normalized_company,
            normalized_published_on,
        )
    ):
        return None

    content_identity = "|".join(
        [
            "content",
            normalized_title,
            normalized_summary,
            normalized_company,
            normalized_published_on,
        ]
    )
    return hashlib.sha256(content_identity.encode("utf-8")).hexdigest()


def _normalize_article_identity_text(value: str | None) -> str | None:
    if value is None:
        return None

    normalized_value = unicodedata.normalize("NFKD", value)
    normalized_value = "".join(
        character
        for character in normalized_value
        if not unicodedata.combining(character)
    )
    normalized_value = normalized_value.casefold()
    normalized_value = re.sub(r"[^a-z0-9]+", " ", normalized_value)
    normalized_value = re.sub(r"\s+", " ", normalized_value).strip()
    return normalized_value or None


def _normalize_article_identity_date(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.date().isoformat()


def _normalize_source_url(url: str | None) -> str | None:
    raw_url = (url or "").strip()
    if not raw_url:
        return None

    parsed_url = urlsplit(raw_url)
    scheme = parsed_url.scheme.lower()
    hostname = (parsed_url.hostname or "").lower()
    port = parsed_url.port

    netloc = hostname
    if parsed_url.username:
        netloc = f"{parsed_url.username}@{netloc}"
    if port is not None and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{netloc}:{port}"

    path = parsed_url.path or ""
    if path not in {"", "/"}:
        path = path.rstrip("/")

    filtered_query_params: list[tuple[str, str]] = []
    for query_key, query_value in parse_qsl(parsed_url.query, keep_blank_values=True):
        normalized_key = query_key.strip()
        if not normalized_key:
            continue
        normalized_key_lower = normalized_key.lower()
        if normalized_key_lower.startswith("utm_"):
            continue
        if normalized_key_lower.startswith("at_"):
            continue
        if normalized_key_lower in _TRACKING_QUERY_PARAM_NAMES:
            continue
        filtered_query_params.append((normalized_key, query_value))

    filtered_query_params.sort(key=lambda item: (item[0].lower(), item[1], item[0]))
    normalized_query = urlencode(filtered_query_params, doseq=True)
    normalized_url = urlunsplit((scheme, netloc, path, normalized_query, ""))
    if normalized_url.endswith("?"):
        return normalized_url[:-1]
    return normalized_url
