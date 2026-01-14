-- Company info entity (one per project)
-- Stores client company details for context

CREATE TABLE IF NOT EXISTS company_info (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) UNIQUE NOT NULL,
    name TEXT NOT NULL,
    industry TEXT,
    stage TEXT,  -- "Startup", "Growth", "Enterprise"
    size TEXT,   -- "1-10", "11-50", "51-200", "201-500", "500+"
    website TEXT,
    description TEXT,
    key_differentiators JSONB DEFAULT '[]'::jsonb,
    source_signal_id UUID REFERENCES signals(id),
    revision_id UUID,  -- For future revision tracking
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_company_info_project ON company_info(project_id);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_company_info_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS company_info_updated_at ON company_info;
CREATE TRIGGER company_info_updated_at
    BEFORE UPDATE ON company_info
    FOR EACH ROW
    EXECUTE FUNCTION update_company_info_updated_at();
