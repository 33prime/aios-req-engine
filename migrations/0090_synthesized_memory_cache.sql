-- Migration: Synthesized Memory Cache
-- Caches the unified memory synthesis to avoid repeated LLM calls
-- Marked stale when underlying data changes, regenerated on demand

CREATE TABLE IF NOT EXISTS synthesized_memory_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- The synthesized markdown document
    content TEXT NOT NULL,

    -- When this synthesis was created
    synthesized_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Staleness tracking
    is_stale BOOLEAN NOT NULL DEFAULT FALSE,
    stale_reason TEXT,

    -- Hash of inputs to detect if underlying data changed
    inputs_hash TEXT,

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- One cache per project
    UNIQUE(project_id)
);

-- Index for quick lookups
CREATE INDEX idx_synthesized_memory_cache_project ON synthesized_memory_cache(project_id);
CREATE INDEX idx_synthesized_memory_cache_stale ON synthesized_memory_cache(project_id, is_stale);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_synthesized_memory_cache_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_synthesized_memory_cache_updated
    BEFORE UPDATE ON synthesized_memory_cache
    FOR EACH ROW
    EXECUTE FUNCTION update_synthesized_memory_cache_timestamp();

-- Comments
COMMENT ON TABLE synthesized_memory_cache IS 'Cached unified memory synthesis - combines project memory and knowledge graph';
COMMENT ON COLUMN synthesized_memory_cache.content IS 'LLM-generated markdown document synthesizing all memory sources';
COMMENT ON COLUMN synthesized_memory_cache.is_stale IS 'True when underlying data has changed since last synthesis';
COMMENT ON COLUMN synthesized_memory_cache.stale_reason IS 'What triggered the staleness (signal_processed, decision_added, etc.)';
COMMENT ON COLUMN synthesized_memory_cache.inputs_hash IS 'Hash of input data for change detection';
