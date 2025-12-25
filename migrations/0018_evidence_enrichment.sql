-- Migration: Evidence Enrichment
-- Description: Add evidence chain of custody metadata to signals and chunks
-- Date: 2025-12-25
-- Phase: 0 - Foundation

-- =========================
-- Enhance signals table for evidence display
-- =========================
ALTER TABLE signals
ADD COLUMN IF NOT EXISTS source_type TEXT,  -- 'transcript' | 'email' | 'doc' | 'note' | 'research'
ADD COLUMN IF NOT EXISTS source_label TEXT,  -- Human-readable label: 'Call 12/17', 'Email from Sarah'
ADD COLUMN IF NOT EXISTS source_timestamp TIMESTAMPTZ,  -- When the signal was created/recorded
ADD COLUMN IF NOT EXISTS source_metadata JSONB DEFAULT '{}'::jsonb;  -- {meeting_type, participants, document_name, etc.}

-- Update existing signals with inferred source_type based on signal_type
UPDATE signals
SET source_type = CASE
  WHEN signal_type IN ('email', 'transcript', 'note') THEN signal_type
  WHEN signal_type = 'file_text' THEN 'doc'
  WHEN signal_type LIKE '%research%' OR signal_type LIKE '%article%' THEN 'research'
  ELSE 'note'
END
WHERE source_type IS NULL;

-- Index for filtering by source type
CREATE INDEX IF NOT EXISTS idx_signals_source_type
  ON signals(project_id, source_type);

-- Index for source timestamp
CREATE INDEX IF NOT EXISTS idx_signals_source_timestamp
  ON signals(project_id, source_timestamp DESC NULLS LAST);

-- Comments
COMMENT ON COLUMN signals.source_type IS
  'Source type for evidence display: transcript, email, doc, note, research';

COMMENT ON COLUMN signals.source_label IS
  'Human-readable source label for evidence chips (e.g., "Call 12/17", "Email from Sarah Chen")';

COMMENT ON COLUMN signals.source_timestamp IS
  'Original timestamp when signal was created/recorded (distinct from created_at which is ingestion time)';

COMMENT ON COLUMN signals.source_metadata IS
  'Additional source metadata: {meeting_type, participants, document_name, page_count, etc.}';

-- =========================
-- Enhance signal_chunks for granular evidence
-- =========================
-- Note: signal_chunks.metadata already exists, but we're adding a comment to clarify expected structure
COMMENT ON COLUMN signal_chunks.metadata IS
  'Chunk-specific metadata: {timestamp: "14:32", page: 2, speaker: "Sarah", paragraph: 3, etc.}';

-- =========================
-- Create view for enhanced evidence retrieval
-- =========================
CREATE OR REPLACE VIEW evidence_chunks AS
SELECT
  sc.id AS chunk_id,
  sc.signal_id,
  sc.chunk_index,
  sc.content,
  sc.start_char,
  sc.end_char,
  sc.metadata AS chunk_metadata,
  s.project_id,
  s.source_type,
  s.source_label,
  s.source_timestamp,
  s.source_metadata,
  s.signal_type,
  s.source AS signal_source,
  s.created_at AS signal_created_at
FROM signal_chunks sc
JOIN signals s ON s.id = sc.signal_id;

COMMENT ON VIEW evidence_chunks IS
  'Joined view of chunks with signal metadata for rich evidence display';

-- =========================
-- Helper function to extract timestamp from chunk content
-- =========================
-- For transcripts, extract [HH:MM] or [HH:MM:SS] timestamps from content
CREATE OR REPLACE FUNCTION extract_timestamp_from_content(content TEXT)
RETURNS TEXT
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
  timestamp_match TEXT;
BEGIN
  -- Match [HH:MM] or [HH:MM:SS] pattern
  timestamp_match := substring(content FROM '\[(\d{1,2}:\d{2}(?::\d{2})?)\]');

  -- If no bracketed timestamp, try to find MM:SS or HH:MM:SS at start of line
  IF timestamp_match IS NULL THEN
    timestamp_match := substring(content FROM '^\s*(\d{1,2}:\d{2}(?::\d{2})?)\s');
  END IF;

  RETURN timestamp_match;
END;
$$;

COMMENT ON FUNCTION extract_timestamp_from_content IS
  'Extract timestamp from transcript chunk content (e.g., "[14:32]" → "14:32")';

-- =========================
-- Helper function to format evidence label
-- =========================
CREATE OR REPLACE FUNCTION format_evidence_label(
  source_type TEXT,
  source_label TEXT,
  chunk_timestamp TEXT,
  chunk_page INT
)
RETURNS TEXT
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
  -- Start with source label or type
  IF source_label IS NOT NULL AND source_label != '' THEN
    IF source_type = 'transcript' AND chunk_timestamp IS NOT NULL THEN
      RETURN source_label || ' @ ' || chunk_timestamp;
    ELSIF source_type = 'doc' AND chunk_page IS NOT NULL THEN
      RETURN source_label || ' p' || chunk_page;
    ELSE
      RETURN source_label;
    END IF;
  ELSE
    -- Fallback to type with details
    IF source_type = 'transcript' AND chunk_timestamp IS NOT NULL THEN
      RETURN 'Call @ ' || chunk_timestamp;
    ELSIF source_type = 'doc' AND chunk_page IS NOT NULL THEN
      RETURN 'Document p' || chunk_page;
    ELSE
      RETURN initcap(COALESCE(source_type, 'Signal'));
    END IF;
  END IF;
END;
$$;

COMMENT ON FUNCTION format_evidence_label IS
  'Format human-readable evidence label for display (e.g., "Call 12/17 @ 14:32", "OrgChart.pdf p2")';

-- =========================
-- Update match_signal_chunks function to include evidence metadata
-- =========================
CREATE OR REPLACE FUNCTION match_signal_chunks(
  query_embedding vector(1536),
  match_count int,
  filter_project_id uuid DEFAULT NULL
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
  signal_metadata jsonb,
  -- New evidence fields
  source_type text,
  source_label text,
  source_timestamp timestamptz,
  evidence_label text
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
    s.metadata AS signal_metadata,
    s.source_type,
    s.source_label,
    s.source_timestamp,
    format_evidence_label(
      s.source_type,
      s.source_label,
      (sc.metadata->>'timestamp')::text,
      (sc.metadata->>'page')::int
    ) AS evidence_label
  FROM signal_chunks sc
  JOIN signals s ON s.id = sc.signal_id
  WHERE (filter_project_id IS NULL OR s.project_id = filter_project_id)
  ORDER BY sc.embedding <=> query_embedding
  LIMIT match_count;
$$;

COMMENT ON FUNCTION match_signal_chunks IS
  'Enhanced vector similarity search with evidence metadata for rich display';
