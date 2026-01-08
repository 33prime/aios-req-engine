-- Migration: 0029_creative_briefs.sql
-- Purpose: Add creative_briefs table for persistent client/project context storage
-- Used for: Research agent seed context, auto-extraction from signals

-- Create creative_briefs table
CREATE TABLE IF NOT EXISTS creative_briefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL UNIQUE REFERENCES projects(id) ON DELETE CASCADE,

    -- Core fields (required for research)
    client_name TEXT,
    industry TEXT,
    website TEXT,

    -- Arrays for research context
    competitors JSONB DEFAULT '[]'::jsonb,
    focus_areas JSONB DEFAULT '[]'::jsonb,
    custom_questions JSONB DEFAULT '[]'::jsonb,

    -- Tracking
    completeness_score FLOAT DEFAULT 0,
    last_extracted_from UUID REFERENCES signals(id) ON DELETE SET NULL,

    -- Source tracking for each field (user vs extracted)
    field_sources JSONB DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Index for fast lookup by project
CREATE INDEX IF NOT EXISTS idx_creative_briefs_project ON creative_briefs(project_id);

-- Trigger to update updated_at on changes
CREATE OR REPLACE FUNCTION update_creative_briefs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_creative_briefs_updated_at ON creative_briefs;
CREATE TRIGGER trigger_creative_briefs_updated_at
    BEFORE UPDATE ON creative_briefs
    FOR EACH ROW
    EXECUTE FUNCTION update_creative_briefs_updated_at();

-- Comments
COMMENT ON TABLE creative_briefs IS 'Stores client/project context for research agent and auto-extraction';
COMMENT ON COLUMN creative_briefs.client_name IS 'Name of the client company';
COMMENT ON COLUMN creative_briefs.industry IS 'Industry/vertical of the client';
COMMENT ON COLUMN creative_briefs.website IS 'Client website URL';
COMMENT ON COLUMN creative_briefs.competitors IS 'Array of competitor names for research';
COMMENT ON COLUMN creative_briefs.focus_areas IS 'Key areas to focus research on';
COMMENT ON COLUMN creative_briefs.custom_questions IS 'Custom research questions from consultant';
COMMENT ON COLUMN creative_briefs.completeness_score IS 'Score 0-1 based on required fields filled';
COMMENT ON COLUMN creative_briefs.last_extracted_from IS 'Last signal that auto-updated this brief';
COMMENT ON COLUMN creative_briefs.field_sources IS 'Tracks source of each field value (user vs extracted)';
