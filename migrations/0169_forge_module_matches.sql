-- Track which Forge modules matched to which features (for feedback loop)
CREATE TABLE IF NOT EXISTS forge_module_matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id),
    feature_id UUID NOT NULL,
    module_slug TEXT NOT NULL,
    match_score FLOAT NOT NULL DEFAULT 0.0,
    match_reason TEXT DEFAULT '',
    horizon_suggestion TEXT,          -- H1/H2/H3 from co-occurrence
    resolved_decisions JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_forge_matches_project ON forge_module_matches(project_id);
CREATE INDEX idx_forge_matches_feature ON forge_module_matches(feature_id);

-- Upsert natural key: one match per (project, feature, module)
CREATE UNIQUE INDEX idx_forge_matches_unique
    ON forge_module_matches(project_id, feature_id, module_slug);
