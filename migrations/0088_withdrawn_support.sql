-- Migration: Soft Delete (Withdrawn) Support for Documents and Signals
-- Description: Add withdrawn columns and update search RPCs to exclude withdrawn records
-- Author: Soft delete feature
-- Date: 2025-01-29

-- ============================================================================
-- Add withdrawn columns to document_uploads
-- ============================================================================

ALTER TABLE document_uploads
ADD COLUMN IF NOT EXISTS is_withdrawn BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS withdrawn_at TIMESTAMPTZ;

-- ============================================================================
-- Add withdrawn columns to signals
-- ============================================================================

ALTER TABLE signals
ADD COLUMN IF NOT EXISTS is_withdrawn BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS withdrawn_at TIMESTAMPTZ;

-- ============================================================================
-- Indexes for efficient filtering
-- ============================================================================

-- Partial index for non-withdrawn signals (most common query pattern)
CREATE INDEX IF NOT EXISTS idx_signals_not_withdrawn
ON signals (project_id) WHERE is_withdrawn IS NOT TRUE;

-- Partial index for non-withdrawn documents
CREATE INDEX IF NOT EXISTS idx_document_uploads_not_withdrawn
ON document_uploads (project_id) WHERE is_withdrawn IS NOT TRUE;

-- ============================================================================
-- Update match_signal_chunks to exclude withdrawn signals
-- ============================================================================

CREATE OR REPLACE FUNCTION public.match_signal_chunks(
  query_embedding vector(1536),
  match_count int,
  filter_project_id uuid default null
)
RETURNS TABLE (
  chunk_id uuid,
  signal_id uuid,
  chunk_index int,
  content text,
  start_char int,
  end_char int,
  similarity float4,
  chunk_metadata jsonb,
  signal_metadata jsonb
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    sc.id AS chunk_id,
    sc.signal_id,
    sc.chunk_index,
    sc.content,
    sc.start_char,
    sc.end_char,
    (1 - (sc.embedding <=> query_embedding))::float4 AS similarity,
    sc.metadata AS chunk_metadata,
    s.metadata AS signal_metadata
  FROM public.signal_chunks sc
  JOIN public.signals s ON s.id = sc.signal_id
  WHERE (filter_project_id IS NULL OR s.project_id = filter_project_id)
    AND (s.is_withdrawn IS NOT TRUE)  -- Exclude withdrawn signals
  ORDER BY sc.embedding <=> query_embedding
  LIMIT match_count;
$$;

-- ============================================================================
-- Update hybrid_search_chunks to exclude withdrawn signals
-- ============================================================================

CREATE OR REPLACE FUNCTION hybrid_search_chunks(
    query_text TEXT,
    query_embedding vector(1536),
    p_project_id UUID,
    match_count INTEGER DEFAULT 20,
    vector_weight FLOAT DEFAULT 0.7,
    keyword_weight FLOAT DEFAULT 0.3,
    filter_document_class TEXT DEFAULT NULL,
    filter_authority TEXT DEFAULT NULL,
    filter_section_type TEXT DEFAULT NULL
)
RETURNS TABLE (
    chunk_id UUID,
    signal_id UUID,
    content TEXT,
    metadata JSONB,
    vector_score FLOAT,
    keyword_score FLOAT,
    combined_score FLOAT,
    boosted_score FLOAT
) AS $$
DECLARE
    authority_boost FLOAT;
BEGIN
    RETURN QUERY
    WITH vector_results AS (
        -- Get top candidates by vector similarity
        SELECT
            sc.id,
            sc.signal_id,
            sc.content,
            sc.metadata,
            (1 - (sc.embedding <=> query_embedding))::FLOAT AS v_score
        FROM signal_chunks sc
        JOIN signals s ON sc.signal_id = s.id
        WHERE s.project_id = p_project_id
        AND (s.is_withdrawn IS NOT TRUE)  -- Exclude withdrawn signals
        AND (filter_document_class IS NULL
             OR sc.metadata->>'document_class' = filter_document_class)
        AND (filter_authority IS NULL
             OR sc.metadata->>'authority' = filter_authority)
        AND (filter_section_type IS NULL
             OR sc.metadata->>'section_type' = filter_section_type)
        ORDER BY sc.embedding <=> query_embedding
        LIMIT match_count * 3  -- Get more candidates for hybrid ranking
    ),
    keyword_results AS (
        -- Get keyword match scores for the vector candidates
        SELECT
            sc.id,
            ts_rank_cd(
                to_tsvector('english', sc.content),
                plainto_tsquery('english', query_text),
                32  -- Normalization: divide by document length
            )::FLOAT AS k_score
        FROM signal_chunks sc
        JOIN signals s ON sc.signal_id = s.id
        WHERE s.project_id = p_project_id
        AND (s.is_withdrawn IS NOT TRUE)  -- Exclude withdrawn signals
        AND to_tsvector('english', sc.content) @@ plainto_tsquery('english', query_text)
        AND (filter_document_class IS NULL
             OR sc.metadata->>'document_class' = filter_document_class)
        AND (filter_authority IS NULL
             OR sc.metadata->>'authority' = filter_authority)
    ),
    combined AS (
        SELECT
            v.id,
            v.signal_id,
            v.content,
            v.metadata,
            v.v_score,
            COALESCE(k.k_score, 0.0) AS k_score,
            (vector_weight * v.v_score + keyword_weight * COALESCE(k.k_score, 0.0))::FLOAT AS c_score,
            -- Authority boost: client=3x, consultant=2x, research=1.5x, other=1x
            CASE
                WHEN v.metadata->>'authority' = 'client' THEN 3.0
                WHEN v.metadata->>'authority' = 'consultant' THEN 2.0
                WHEN v.metadata->>'authority' = 'research' THEN 1.5
                ELSE 1.0
            END AS auth_boost
        FROM vector_results v
        LEFT JOIN keyword_results k ON v.id = k.id
    )
    SELECT
        c.id AS chunk_id,
        c.signal_id,
        c.content,
        c.metadata,
        c.v_score AS vector_score,
        c.k_score AS keyword_score,
        c.c_score AS combined_score,
        (c.c_score * c.auth_boost)::FLOAT AS boosted_score
    FROM combined c
    ORDER BY (c.c_score * c.auth_boost) DESC
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON COLUMN document_uploads.is_withdrawn IS
'Soft delete flag - withdrawn documents are excluded from retrieval but data is preserved';

COMMENT ON COLUMN document_uploads.withdrawn_at IS
'Timestamp when the document was withdrawn';

COMMENT ON COLUMN signals.is_withdrawn IS
'Soft delete flag - withdrawn signals are excluded from search but data is preserved';

COMMENT ON COLUMN signals.withdrawn_at IS
'Timestamp when the signal was withdrawn';
