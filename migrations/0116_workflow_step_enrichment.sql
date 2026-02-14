-- Migration 0116: Add enrichment columns to vp_steps for on-demand AI analysis
-- Follows the same pattern as prototype enrichment (JSONB data + status + timestamp)

ALTER TABLE vp_steps
  ADD COLUMN IF NOT EXISTS enrichment_data JSONB,
  ADD COLUMN IF NOT EXISTS enrichment_status TEXT DEFAULT 'pending'
    CHECK (enrichment_status IN ('pending', 'enriched', 'failed')),
  ADD COLUMN IF NOT EXISTS enrichment_attempted_at TIMESTAMPTZ;

COMMENT ON COLUMN vp_steps.enrichment_data IS 'On-demand AI analysis: narrative, optimization suggestions, automation score';
COMMENT ON COLUMN vp_steps.enrichment_status IS 'Status of AI enrichment: pending, enriched, failed';
COMMENT ON COLUMN vp_steps.enrichment_attempted_at IS 'When AI enrichment was last attempted';
