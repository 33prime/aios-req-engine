-- Call strategy briefs — pre-call strategy and post-call goal-vs-got diff
CREATE TABLE call_strategy_briefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    meeting_id UUID REFERENCES meetings(id) ON DELETE SET NULL,
    recording_id UUID REFERENCES call_recordings(id) ON DELETE SET NULL,

    -- Strategy content
    stakeholder_intel JSONB DEFAULT '[]',
    mission_critical_questions JSONB DEFAULT '[]',
    call_goals JSONB DEFAULT '[]',
    deal_readiness_snapshot JSONB DEFAULT '{}',
    ambiguity_snapshot JSONB DEFAULT '{}',
    focus_areas JSONB DEFAULT '[]',
    project_awareness_snapshot JSONB DEFAULT '{}',

    -- Post-call diff (populated after analysis)
    goal_results JSONB DEFAULT NULL,
    readiness_delta JSONB DEFAULT NULL,

    -- Metadata
    generated_by TEXT DEFAULT 'system',
    model TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_strategy_briefs_project ON call_strategy_briefs(project_id);
CREATE INDEX idx_strategy_briefs_meeting ON call_strategy_briefs(meeting_id);
CREATE INDEX idx_strategy_briefs_recording ON call_strategy_briefs(recording_id);
