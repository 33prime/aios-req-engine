-- Migration 0011: Chunk Metadata Indexes
-- Adds indexes on signal_chunks.metadata JSONB fields for faster filtering
-- Supports status-aware vector search and research/client authority filtering

-- Index for confirmation_status filtering (status-aware search)
CREATE INDEX IF NOT EXISTS idx_signal_chunks_confirmation_status
ON signal_chunks ((metadata->>'confirmation_status'));

-- Index for authority filtering (client vs research signals)
CREATE INDEX IF NOT EXISTS idx_signal_chunks_authority
ON signal_chunks ((metadata->>'authority'));

-- Index for section_type filtering (research section-based retrieval)
CREATE INDEX IF NOT EXISTS idx_signal_chunks_section_type
ON signal_chunks ((metadata->>'section_type'));

-- Comment explaining the indexes
COMMENT ON INDEX idx_signal_chunks_confirmation_status IS
'Speeds up filtering by chunk confirmation status (confirmed_client, confirmed_consultant, draft)';

COMMENT ON INDEX idx_signal_chunks_authority IS
'Speeds up filtering by signal authority (client, research)';

COMMENT ON INDEX idx_signal_chunks_section_type IS
'Speeds up filtering by research document section type (features_must_have, personas, risks, etc)';
