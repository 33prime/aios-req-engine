-- Competitor and design references
-- Stores competitors, design inspiration, and feature inspiration

CREATE TABLE IF NOT EXISTS competitor_references (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) NOT NULL,
    reference_type TEXT NOT NULL CHECK (reference_type IN ('competitor', 'design_inspiration', 'feature_inspiration')),
    name TEXT NOT NULL,
    url TEXT,
    category TEXT,  -- "Direct competitor", "Adjacent", "Design reference"
    strengths JSONB DEFAULT '[]'::jsonb,
    weaknesses JSONB DEFAULT '[]'::jsonb,
    features_to_study JSONB DEFAULT '[]'::jsonb,
    research_notes TEXT,
    screenshots JSONB DEFAULT '[]'::jsonb,
    source_signal_id UUID REFERENCES signals(id),
    revision_id UUID,  -- For future revision tracking
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_competitor_refs_project ON competitor_references(project_id);
CREATE INDEX IF NOT EXISTS idx_competitor_refs_type ON competitor_references(reference_type);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_competitor_references_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS competitor_references_updated_at ON competitor_references;
CREATE TRIGGER competitor_references_updated_at
    BEFORE UPDATE ON competitor_references
    FOR EACH ROW
    EXECUTE FUNCTION update_competitor_references_updated_at();
