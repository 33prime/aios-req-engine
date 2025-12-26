-- Migration 0022: Signal Impact Tracking Table
-- Purpose: Track reverse mappings from signals/chunks to entities for efficient impact analysis
-- Enables: "Which entities were influenced by this signal?" queries in O(1) time

CREATE TABLE IF NOT EXISTS signal_impact (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL,
  signal_id UUID NOT NULL REFERENCES signals(id) ON DELETE CASCADE,
  chunk_id UUID NOT NULL REFERENCES signal_chunks(id) ON DELETE CASCADE,

  -- Entity that was influenced by this chunk
  entity_type TEXT NOT NULL CHECK (entity_type IN ('prd_section', 'vp_step', 'feature', 'insight', 'persona')),
  entity_id UUID NOT NULL,

  -- How the chunk was used
  usage_context TEXT NOT NULL CHECK (usage_context IN ('evidence', 'enrichment')),
  confidence REAL, -- Optional confidence score for future use

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- Ensure no duplicate impact records
  UNIQUE(chunk_id, entity_type, entity_id)
);

-- Indexes for efficient querying

-- Query all entities influenced by a signal
CREATE INDEX idx_signal_impact_signal ON signal_impact(signal_id);

-- Query all entities influenced by a specific chunk
CREATE INDEX idx_signal_impact_chunk ON signal_impact(chunk_id);

-- Query all chunks that influenced a specific entity
CREATE INDEX idx_signal_impact_entity ON signal_impact(entity_type, entity_id);

-- Query all impact records for a project (ordered by recency)
CREATE INDEX idx_signal_impact_project ON signal_impact(project_id, created_at DESC);

-- Add comment for documentation
COMMENT ON TABLE signal_impact IS 'Tracks which signals/chunks influenced which entities (PRD sections, features, VP steps, insights, personas). Enables efficient reverse lookups for impact analysis and source provenance tracking.';
COMMENT ON COLUMN signal_impact.usage_context IS 'How the chunk was used: evidence (cited in evidence arrays) or enrichment (used for enrichment context)';
