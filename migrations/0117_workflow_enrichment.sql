-- Migration 0117: Add enrichment columns to workflows table for batch AI analysis
-- One LLM call per workflow analyzes all steps together, producing per-step enrichments
-- plus workflow-level strategic unlocks and transformation narrative.

ALTER TABLE workflows
  ADD COLUMN IF NOT EXISTS enrichment_data JSONB,
  ADD COLUMN IF NOT EXISTS enrichment_status TEXT DEFAULT 'pending'
    CHECK (enrichment_status IN ('pending', 'enriched', 'failed')),
  ADD COLUMN IF NOT EXISTS enrichment_attempted_at TIMESTAMPTZ;

COMMENT ON COLUMN workflows.enrichment_data IS 'Batch AI analysis: transformation narrative, strategic unlocks, cross-step insights';
COMMENT ON COLUMN workflows.enrichment_status IS 'Status of batch AI enrichment: pending, enriched, failed';
COMMENT ON COLUMN workflows.enrichment_attempted_at IS 'When batch AI enrichment was last attempted';
