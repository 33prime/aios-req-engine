-- Intelligence Briefing: session tracking, hypothesis columns, briefing cache
-- Supports the intelligence briefing system with temporal diff, tensions, hypotheses.

-- 1. Consultant session tracking for temporal diff
CREATE TABLE consultant_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    last_briefing_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    previous_briefing_at TIMESTAMPTZ,
    session_count INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(project_id, user_id)
);

CREATE INDEX idx_consultant_sessions_project ON consultant_sessions(project_id);
CREATE INDEX idx_consultant_sessions_user ON consultant_sessions(user_id);

-- RLS
ALTER TABLE consultant_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY consultant_sessions_select ON consultant_sessions
    FOR SELECT TO authenticated
    USING (can_access_project(project_id));

CREATE POLICY consultant_sessions_insert ON consultant_sessions
    FOR INSERT TO authenticated
    WITH CHECK (can_access_project(project_id));

CREATE POLICY consultant_sessions_update ON consultant_sessions
    FOR UPDATE TO authenticated
    USING (can_access_project(project_id));

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_consultant_sessions_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_consultant_sessions_updated
    BEFORE UPDATE ON consultant_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_consultant_sessions_timestamp();

-- 2. Hypothesis tracking on memory_nodes
ALTER TABLE memory_nodes
    ADD COLUMN IF NOT EXISTS hypothesis_status TEXT
        CHECK (hypothesis_status IN ('proposed', 'testing', 'graduated', 'rejected')),
    ADD COLUMN IF NOT EXISTS evidence_for_count INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS evidence_against_count INTEGER DEFAULT 0;

CREATE INDEX idx_memory_nodes_hypothesis ON memory_nodes(project_id, hypothesis_status)
    WHERE hypothesis_status IS NOT NULL;

-- 3. Briefing cache columns on synthesized_memory_cache
ALTER TABLE synthesized_memory_cache
    ADD COLUMN IF NOT EXISTS briefing_sections JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS narrative_version INTEGER DEFAULT 0;

COMMENT ON TABLE consultant_sessions IS 'Tracks when consultants last viewed a project briefing for temporal diff';
COMMENT ON COLUMN memory_nodes.hypothesis_status IS 'Hypothesis lifecycle: proposed → testing → graduated/rejected';
COMMENT ON COLUMN memory_nodes.evidence_for_count IS 'Cached count of supporting evidence edges';
COMMENT ON COLUMN memory_nodes.evidence_against_count IS 'Cached count of contradicting evidence edges';
COMMENT ON COLUMN synthesized_memory_cache.briefing_sections IS 'Cached intelligence briefing sections (JSONB)';
COMMENT ON COLUMN synthesized_memory_cache.narrative_version IS 'Incremented when narrative regenerated';
