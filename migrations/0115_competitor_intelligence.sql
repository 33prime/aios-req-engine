-- Migration: 0115_competitor_intelligence
-- Adds deep analysis fields to competitor_references for competitor intelligence agent

ALTER TABLE competitor_references
  ADD COLUMN IF NOT EXISTS deep_analysis JSONB,
  ADD COLUMN IF NOT EXISTS deep_analysis_status TEXT DEFAULT 'pending'
    CHECK (deep_analysis_status IN ('pending', 'analyzing', 'completed', 'failed')),
  ADD COLUMN IF NOT EXISTS deep_analysis_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS scraped_pages JSONB DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS is_design_reference BOOLEAN DEFAULT false;

COMMENT ON COLUMN competitor_references.deep_analysis IS 'JSONB: feature_overlap, unique_to_them, unique_to_us, inferred_pains, inferred_benefits, positioning, threat_level';
COMMENT ON COLUMN competitor_references.scraped_pages IS 'Array of {url, title, scraped_at} for pages analyzed';
COMMENT ON COLUMN competitor_references.is_design_reference IS 'Whether this competitor also serves as a design reference';
