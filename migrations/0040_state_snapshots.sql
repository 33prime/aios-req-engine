-- State snapshots for caching project context
-- Used by all agents to get consistent 500-token context

CREATE TABLE IF NOT EXISTS state_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) UNIQUE NOT NULL,
    snapshot_text TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_entity_change_at TIMESTAMPTZ,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_state_snapshots_project ON state_snapshots(project_id);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_state_snapshots_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS state_snapshots_updated_at ON state_snapshots;
CREATE TRIGGER state_snapshots_updated_at
    BEFORE UPDATE ON state_snapshots
    FOR EACH ROW
    EXECUTE FUNCTION update_state_snapshots_updated_at();
