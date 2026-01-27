-- Migration: Project Memory System
-- Persistent memory storage for the Design Intelligence Agent

-- =============================================================================
-- Project Memory Document
-- =============================================================================
-- Stores the markdown memory document per project
-- This is the "semantic" memory - synthesized understanding

CREATE TABLE IF NOT EXISTS project_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- The full memory document (markdown)
    content TEXT NOT NULL DEFAULT '',

    -- Structured sections for faster updates (denormalized for convenience)
    project_understanding TEXT DEFAULT '',
    client_profile JSONB DEFAULT '{}',
    current_strategy JSONB DEFAULT '{}',
    open_questions JSONB DEFAULT '[]',

    -- Metadata
    version INTEGER NOT NULL DEFAULT 1,
    last_updated_by TEXT DEFAULT 'system',  -- 'di_agent', 'consultant', 'system'
    tokens_estimate INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(project_id)
);

-- =============================================================================
-- Decision Log
-- =============================================================================
-- Episodic memory for decisions - the "why" behind changes

CREATE TABLE IF NOT EXISTS project_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Decision details
    title TEXT NOT NULL,
    decision TEXT NOT NULL,
    rationale TEXT NOT NULL,

    -- Context
    alternatives_considered JSONB DEFAULT '[]',  -- [{option, why_rejected}]
    evidence_signal_ids UUID[] DEFAULT '{}',     -- Links to signals
    evidence_entity_ids UUID[] DEFAULT '{}',     -- Links to entities

    -- Attribution
    decided_by TEXT,                             -- 'client', 'consultant', 'di_agent'
    confidence FLOAT DEFAULT 0.8,

    -- Categorization
    decision_type TEXT DEFAULT 'feature',        -- 'feature', 'architecture', 'scope', 'pivot', 'terminology'
    affects_gates TEXT[] DEFAULT '{}',           -- Which gates this affects

    -- Validity tracking (decisions can be superseded)
    is_active BOOLEAN DEFAULT TRUE,
    superseded_by UUID REFERENCES project_decisions(id),
    superseded_at TIMESTAMPTZ,
    supersede_reason TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_project_decisions_project ON project_decisions(project_id);
CREATE INDEX idx_project_decisions_active ON project_decisions(project_id, is_active);
CREATE INDEX idx_project_decisions_type ON project_decisions(project_id, decision_type);

-- =============================================================================
-- Learning Journal
-- =============================================================================
-- Procedural memory - what worked, what didn't

CREATE TABLE IF NOT EXISTS project_learnings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Learning details
    title TEXT NOT NULL,
    context TEXT NOT NULL,           -- What happened
    learning TEXT NOT NULL,          -- What we learned

    -- Categorization
    learning_type TEXT DEFAULT 'insight',  -- 'insight', 'mistake', 'pattern', 'terminology'
    domain TEXT,                           -- 'client', 'domain', 'process', 'technical'

    -- Impact tracking
    times_applied INTEGER DEFAULT 0,       -- How often this learning was used
    last_applied_at TIMESTAMPTZ,
    success_rate FLOAT,                    -- When applied, how often successful

    -- Links
    source_signal_id UUID,
    source_action_log_id UUID,             -- Link to di_agent_logs if from agent action

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_project_learnings_project ON project_learnings(project_id);
CREATE INDEX idx_project_learnings_type ON project_learnings(project_id, learning_type);

-- =============================================================================
-- Memory Access Tracking
-- =============================================================================
-- Track what memories are accessed to implement decay/reinforcement

CREATE TABLE IF NOT EXISTS memory_access_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- What was accessed
    memory_type TEXT NOT NULL,       -- 'decision', 'learning', 'entity'
    memory_id UUID NOT NULL,

    -- Context
    accessed_by TEXT DEFAULT 'di_agent',
    access_context TEXT,             -- Why it was accessed

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_memory_access_project ON memory_access_log(project_id, created_at DESC);

-- =============================================================================
-- Triggers
-- =============================================================================

-- Auto-update updated_at on project_memory
CREATE OR REPLACE FUNCTION update_project_memory_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    NEW.version = OLD.version + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_project_memory_updated
    BEFORE UPDATE ON project_memory
    FOR EACH ROW
    EXECUTE FUNCTION update_project_memory_timestamp();

-- =============================================================================
-- Comments
-- =============================================================================

COMMENT ON TABLE project_memory IS 'Persistent semantic memory document for each project - the agent''s synthesized understanding';
COMMENT ON TABLE project_decisions IS 'Episodic memory of key decisions with full rationale - the "why" behind changes';
COMMENT ON TABLE project_learnings IS 'Procedural memory of patterns and learnings - what works for this project';
COMMENT ON TABLE memory_access_log IS 'Tracks memory access for decay/reinforcement algorithms';

COMMENT ON COLUMN project_memory.content IS 'Full markdown memory document - human readable, agent writable';
COMMENT ON COLUMN project_decisions.superseded_by IS 'Links to newer decision that replaced this one - enables decision history';
COMMENT ON COLUMN project_learnings.times_applied IS 'Reinforcement counter - frequently applied learnings are more valuable';
