-- Migration: Enrichment Revisions Tracking
-- Description: Create table to track enrichment evolution and context for PRD sections, VP steps, and features
-- Date: 2025-12-23

CREATE TABLE IF NOT EXISTS enrichment_revisions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  entity_type TEXT NOT NULL CHECK (entity_type IN ('prd_section', 'vp_step', 'feature')),
  entity_id UUID NOT NULL,
  entity_label TEXT NOT NULL,
  revision_type TEXT NOT NULL CHECK (revision_type IN ('created', 'enriched', 'updated')),
  trigger_event TEXT,
  snapshot JSONB DEFAULT '{}'::jsonb,
  new_signals_count INT DEFAULT 0,
  new_facts_count INT DEFAULT 0,
  context_summary TEXT,
  run_id UUID,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Index for efficient entity revision lookups (ordered by recency)
CREATE INDEX idx_enrichment_revisions_entity ON enrichment_revisions(entity_type, entity_id, created_at DESC);

-- Index for project-level queries
CREATE INDEX idx_enrichment_revisions_project ON enrichment_revisions(project_id, created_at DESC);

-- Index for run_id lookup (audit trail)
CREATE INDEX idx_enrichment_revisions_run ON enrichment_revisions(run_id) WHERE run_id IS NOT NULL;

-- Comments
COMMENT ON TABLE enrichment_revisions IS 'Tracks enrichment evolution and context for PRD sections, VP steps, and features';
COMMENT ON COLUMN enrichment_revisions.entity_type IS 'Type of entity: prd_section, vp_step, or feature';
COMMENT ON COLUMN enrichment_revisions.entity_id IS 'UUID of the entity being tracked';
COMMENT ON COLUMN enrichment_revisions.entity_label IS 'Human-readable label (e.g., slug for PRD, step_index for VP)';
COMMENT ON COLUMN enrichment_revisions.revision_type IS 'Type of revision: created, enriched, or updated';
COMMENT ON COLUMN enrichment_revisions.trigger_event IS 'What triggered this revision (e.g., manual_enrich, auto_update)';
COMMENT ON COLUMN enrichment_revisions.snapshot IS 'JSONB snapshot of relevant entity data at this point in time';
COMMENT ON COLUMN enrichment_revisions.new_signals_count IS 'Number of new signals since last enrichment';
COMMENT ON COLUMN enrichment_revisions.new_facts_count IS 'Number of new facts since last enrichment';
COMMENT ON COLUMN enrichment_revisions.context_summary IS 'Human-readable context (e.g., "based on 5 new signals")';
COMMENT ON COLUMN enrichment_revisions.run_id IS 'Associated agent run ID for audit trail';
