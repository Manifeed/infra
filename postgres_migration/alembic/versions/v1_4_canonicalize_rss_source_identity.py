"""canonicalize rss source identity around normalized urls

Revision ID: v1_4_rss_source_identity
Revises: v1_3_enable_pgcrypto
Create Date: 2026-03-17 19:30:00.000000

"""

from __future__ import annotations

from alembic import op


revision = "v1_4_rss_source_identity"
down_revision = "v1_3_enable_pgcrypto"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION normalize_rss_source_url(raw_url text)
        RETURNS text
        LANGUAGE plpgsql
        IMMUTABLE
        AS $$
        DECLARE
            trimmed_url text;
            working_url text;
            base_part text;
            query_part text;
            scheme_part text;
            rest_part text;
            authority_part text;
            path_part text;
            host_part text;
            port_part text;
            query_pair text;
            key_part text;
            value_part text;
            key_lower text;
            normalized_query_parts text[] := ARRAY[]::text[];
            normalized_query text;
        BEGIN
            trimmed_url := btrim(coalesce(raw_url, ''));
            IF trimmed_url = '' THEN
                RETURN '';
            END IF;

            working_url := split_part(trimmed_url, '#', 1);
            IF position('?' IN working_url) > 0 THEN
                base_part := split_part(working_url, '?', 1);
                query_part := substring(working_url FROM position('?' IN working_url) + 1);
            ELSE
                base_part := working_url;
                query_part := '';
            END IF;

            IF position('://' IN base_part) > 0 THEN
                scheme_part := lower(split_part(base_part, '://', 1));
                rest_part := substring(base_part FROM position('://' IN base_part) + 3);

                IF position('/' IN rest_part) > 0 THEN
                    authority_part := split_part(rest_part, '/', 1);
                    path_part := substring(rest_part FROM position('/' IN rest_part));
                ELSE
                    authority_part := rest_part;
                    path_part := '';
                END IF;

                IF position('@' IN authority_part) > 0 THEN
                    authority_part := split_part(authority_part, '@', 2);
                END IF;

                host_part := authority_part;
                port_part := '';
                IF authority_part ~ ':[0-9]+$' THEN
                    host_part := split_part(authority_part, ':', 1);
                    port_part := split_part(authority_part, ':', 2);
                END IF;

                host_part := lower(host_part);
                IF (scheme_part = 'http' AND port_part = '80')
                    OR (scheme_part = 'https' AND port_part = '443') THEN
                    port_part := '';
                END IF;

                base_part := scheme_part
                    || '://'
                    || host_part
                    || CASE
                        WHEN port_part = '' THEN ''
                        ELSE ':' || port_part
                    END
                    || COALESCE(path_part, '');
            END IF;

            IF base_part ~ '^https?://[^/]+/$' THEN
                base_part := left(base_part, length(base_part) - 1);
            ELSIF length(base_part) > 1 AND right(base_part, 1) = '/' THEN
                base_part := rtrim(base_part, '/');
            END IF;

            IF query_part = '' THEN
                RETURN base_part;
            END IF;

            FOR query_pair IN
                SELECT regexp_split_to_table(query_part, '&')
            LOOP
                IF query_pair = '' OR position('=' IN query_pair) = 0 THEN
                    CONTINUE;
                END IF;

                key_part := split_part(query_pair, '=', 1);
                value_part := substring(query_pair FROM position('=' IN query_pair) + 1);
                key_lower := lower(key_part);

                IF key_lower = '' THEN
                    CONTINUE;
                END IF;
                IF key_lower LIKE 'utm_%' THEN
                    CONTINUE;
                END IF;
                IF key_lower = ANY(
                    ARRAY[
                        '_ga',
                        '_gl',
                        'at_campaign',
                        'at_link',
                        'at_medium',
                        'fbclid',
                        'gclid',
                        'mc_cid',
                        'mc_eid',
                        'xtor'
                    ]
                ) THEN
                    CONTINUE;
                END IF;

                normalized_query_parts := array_append(normalized_query_parts, key_part || '=' || value_part);
            END LOOP;

            IF array_length(normalized_query_parts, 1) IS NULL THEN
                RETURN base_part;
            END IF;

            SELECT string_agg(normalized_pair, '&')
            INTO normalized_query
            FROM (
                SELECT normalized_pair
                FROM unnest(normalized_query_parts) AS normalized_pair
                ORDER BY
                    lower(split_part(normalized_pair, '=', 1)),
                    split_part(normalized_pair, '=', 2),
                    normalized_pair
            ) AS ordered_pairs;

            IF normalized_query = '' THEN
                RETURN base_part;
            END IF;

            RETURN base_part || '?' || normalized_query;
        END;
        $$;
        """
    )

    op.execute(
        """
        CREATE TEMP TABLE tmp_rss_source_canonical_map
        ON COMMIT DROP
        AS
        WITH normalized_sources AS (
            SELECT
                source.id AS source_id,
                normalize_rss_source_url(source.url) AS normalized_url,
                MIN(source.id) OVER (
                    PARTITION BY normalize_rss_source_url(source.url)
                ) AS canonical_source_id
            FROM rss_sources AS source
            WHERE normalize_rss_source_url(source.url) <> ''
        )
        SELECT
            source_id,
            canonical_source_id,
            normalized_url
        FROM normalized_sources
        """
    )
    op.execute(
        "CREATE INDEX tmp_rss_source_canonical_map_source_id_idx "
        "ON tmp_rss_source_canonical_map (source_id)"
    )
    op.execute(
        "CREATE INDEX tmp_rss_source_canonical_map_canonical_id_idx "
        "ON tmp_rss_source_canonical_map (canonical_source_id)"
    )

    op.execute(
        """
        CREATE TEMP TABLE tmp_rss_source_canonical_best
        ON COMMIT DROP
        AS
        SELECT DISTINCT ON (map.canonical_source_id)
            map.canonical_source_id,
            map.normalized_url,
            source.title,
            source.summary,
            source.author,
            source.image_url
        FROM tmp_rss_source_canonical_map AS map
        JOIN rss_sources AS source
            ON source.id = map.source_id
        ORDER BY
            map.canonical_source_id ASC,
            (source.summary IS NOT NULL) DESC,
            (source.author IS NOT NULL) DESC,
            (source.image_url IS NOT NULL) DESC,
            source.published_at DESC,
            source.id ASC
        """
    )

    op.execute(
        """
        UPDATE rss_sources AS source
        SET
            url = best.normalized_url,
            title = best.title,
            summary = COALESCE(best.summary, source.summary),
            author = COALESCE(best.author, source.author),
            image_url = COALESCE(best.image_url, source.image_url)
        FROM tmp_rss_source_canonical_best AS best
        WHERE source.id = best.canonical_source_id
        """
    )

    op.execute(
        """
        INSERT INTO rss_source_feeds (
            feed_id,
            source_id,
            ingested_at
        )
        SELECT
            link.feed_id,
            map.canonical_source_id,
            MIN(link.ingested_at) AS ingested_at
        FROM rss_source_feeds AS link
        JOIN tmp_rss_source_canonical_map AS map
            ON map.source_id = link.source_id
        GROUP BY
            link.feed_id,
            map.canonical_source_id
        ON CONFLICT (feed_id, source_id) DO UPDATE SET
            ingested_at = LEAST(rss_source_feeds.ingested_at, EXCLUDED.ingested_at)
        """
    )
    op.execute(
        """
        DELETE FROM rss_source_feeds AS link
        USING tmp_rss_source_canonical_map AS map
        WHERE link.source_id = map.source_id
            AND map.source_id <> map.canonical_source_id
        """
    )

    op.execute(
        """
        INSERT INTO rss_source_embeddings (
            source_id,
            embedding_model_id,
            embedding,
            updated_at
        )
        SELECT DISTINCT ON (map.canonical_source_id, embedding.embedding_model_id)
            map.canonical_source_id,
            embedding.embedding_model_id,
            embedding.embedding,
            embedding.updated_at
        FROM rss_source_embeddings AS embedding
        JOIN tmp_rss_source_canonical_map AS map
            ON map.source_id = embedding.source_id
        ORDER BY
            map.canonical_source_id ASC,
            embedding.embedding_model_id ASC,
            embedding.updated_at DESC,
            embedding.source_id ASC
        ON CONFLICT (source_id, embedding_model_id) DO UPDATE SET
            embedding = CASE
                WHEN EXCLUDED.updated_at >= rss_source_embeddings.updated_at
                    THEN EXCLUDED.embedding
                ELSE rss_source_embeddings.embedding
            END,
            updated_at = GREATEST(rss_source_embeddings.updated_at, EXCLUDED.updated_at)
        """
    )
    op.execute(
        """
        DELETE FROM rss_source_embeddings AS embedding
        USING tmp_rss_source_canonical_map AS map
        WHERE embedding.source_id = map.source_id
            AND map.source_id <> map.canonical_source_id
        """
    )

    op.execute(
        """
        DELETE FROM rss_embedding_task_items AS item
        USING tmp_rss_source_canonical_map AS map
        WHERE item.source_id = map.source_id
            AND map.source_id <> map.canonical_source_id
            AND EXISTS (
                SELECT 1
                FROM rss_embedding_task_items AS canonical_item
                WHERE canonical_item.task_id = item.task_id
                    AND canonical_item.source_id = map.canonical_source_id
            )
        """
    )
    op.execute(
        """
        WITH ranked_duplicate_items AS (
            SELECT
                item.ctid AS item_ctid,
                ROW_NUMBER() OVER (
                    PARTITION BY item.task_id, map.canonical_source_id
                    ORDER BY item.source_id ASC, item.item_no ASC
                ) AS row_number
            FROM rss_embedding_task_items AS item
            JOIN tmp_rss_source_canonical_map AS map
                ON map.source_id = item.source_id
            WHERE map.source_id <> map.canonical_source_id
        )
        DELETE FROM rss_embedding_task_items AS item
        USING ranked_duplicate_items AS ranked
        WHERE item.ctid = ranked.item_ctid
            AND ranked.row_number > 1
        """
    )
    op.execute(
        """
        UPDATE rss_embedding_task_items AS item
        SET source_id = map.canonical_source_id
        FROM tmp_rss_source_canonical_map AS map
        WHERE item.source_id = map.source_id
            AND map.source_id <> map.canonical_source_id
        """
    )

    op.execute(
        """
        UPDATE rss_embedding_results AS result
        SET source_id = map.canonical_source_id
        FROM tmp_rss_source_canonical_map AS map
        WHERE result.source_id = map.source_id
            AND map.source_id <> map.canonical_source_id
        """
    )

    op.execute(
        """
        INSERT INTO embedding_projection_points (
            projection_id,
            source_id,
            x,
            y,
            embedding_updated_at,
            projected_at
        )
        SELECT DISTINCT ON (point.projection_id, map.canonical_source_id)
            point.projection_id,
            map.canonical_source_id,
            point.x,
            point.y,
            point.embedding_updated_at,
            point.projected_at
        FROM embedding_projection_points AS point
        JOIN tmp_rss_source_canonical_map AS map
            ON map.source_id = point.source_id
        ORDER BY
            point.projection_id ASC,
            map.canonical_source_id ASC,
            point.embedding_updated_at DESC,
            point.projected_at DESC,
            point.source_id ASC
        ON CONFLICT (projection_id, source_id) DO UPDATE SET
            x = CASE
                WHEN EXCLUDED.embedding_updated_at >= embedding_projection_points.embedding_updated_at
                    THEN EXCLUDED.x
                ELSE embedding_projection_points.x
            END,
            y = CASE
                WHEN EXCLUDED.embedding_updated_at >= embedding_projection_points.embedding_updated_at
                    THEN EXCLUDED.y
                ELSE embedding_projection_points.y
            END,
            embedding_updated_at = GREATEST(
                embedding_projection_points.embedding_updated_at,
                EXCLUDED.embedding_updated_at
            ),
            projected_at = GREATEST(
                embedding_projection_points.projected_at,
                EXCLUDED.projected_at
            )
        """
    )
    op.execute(
        """
        DELETE FROM embedding_projection_points AS point
        USING tmp_rss_source_canonical_map AS map
        WHERE point.source_id = map.source_id
            AND map.source_id <> map.canonical_source_id
        """
    )

    op.execute(
        """
        DELETE FROM rss_sources AS source
        USING tmp_rss_source_canonical_map AS map
        WHERE source.id = map.source_id
            AND map.source_id <> map.canonical_source_id
        """
    )

    op.execute(
        """
        UPDATE rss_sources AS source
        SET
            url = best.normalized_url,
            identity_key = encode(
                digest('url|' || best.normalized_url, 'sha256'),
                'hex'
            )
        FROM tmp_rss_source_canonical_best AS best
        WHERE source.id = best.canonical_source_id
        """
    )
    op.execute(
        """
        UPDATE rss_sources AS source
        SET url = normalize_rss_source_url(source.url)
        WHERE normalize_rss_source_url(source.url) <> ''
            AND source.url <> normalize_rss_source_url(source.url)
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS normalize_rss_source_url(text)")
