-- Migration: PRD Summary Section
-- Description: Add columns to prd_sections to support auto-generated executive summaries
-- Date: 2025-12-23

-- Add columns for summary section tracking
ALTER TABLE prd_sections
ADD COLUMN IF NOT EXISTS is_summary BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS summary_attribution JSONB DEFAULT '{}'::jsonb;

-- Index for quick summary section lookup
CREATE INDEX idx_prd_sections_is_summary ON prd_sections(project_id, is_summary) WHERE is_summary = true;

-- Comments
COMMENT ON COLUMN prd_sections.is_summary IS 'Indicates if this section is an auto-generated executive summary';
COMMENT ON COLUMN prd_sections.summary_attribution IS 'Attribution metadata: created_by, confirmed_by, run_id, generated_at';

-- Note: Summary sections will use standard prd_sections columns:
-- - slug: 'executive_summary' or similar
-- - fields: {tldr, what_needed_for_prototype, key_risks, estimated_complexity}
-- - status: follows standard workflow (draft, confirmed, etc.)
