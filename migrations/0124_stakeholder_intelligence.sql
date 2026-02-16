-- Migration: 0124_stakeholder_intelligence.sql
-- Stakeholder Intelligence Agent: logs table + profile tracking columns

-- ============================================================
-- stakeholder_intelligence_logs: Track SI agent invocations
-- ============================================================

CREATE TABLE IF NOT EXISTS stakeholder_intelligence_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stakeholder_id UUID NOT NULL REFERENCES stakeholders(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    trigger TEXT NOT NULL CHECK (trigger IN (
        'signal_processed', 'user_request', 'periodic', 'ci_agent_completed'
    )),
    trigger_context TEXT,

    -- Reasoning trace
    observation TEXT NOT NULL DEFAULT '',
    thinking TEXT NOT NULL DEFAULT '',
    decision TEXT NOT NULL DEFAULT '',

    -- Action
    action_type TEXT NOT NULL CHECK (action_type IN ('tool_call', 'guidance', 'stop')),
    tools_called JSONB DEFAULT '[]'::jsonb,
    guidance JSONB,
    action_summary TEXT,

    -- Results
    profile_completeness_before INT,
    profile_completeness_after INT,
    fields_affected TEXT[] DEFAULT '{}',

    -- Meta
    stop_reason TEXT,
    execution_time_ms INT,
    llm_model TEXT,
    success BOOLEAN NOT NULL DEFAULT true,
    error_message TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_si_logs_stakeholder
    ON stakeholder_intelligence_logs(stakeholder_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_si_logs_project
    ON stakeholder_intelligence_logs(project_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_si_logs_trigger
    ON stakeholder_intelligence_logs(trigger);

-- RLS
ALTER TABLE stakeholder_intelligence_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "si_logs_select" ON stakeholder_intelligence_logs
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "si_logs_insert" ON stakeholder_intelligence_logs
    FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "si_logs_service" ON stakeholder_intelligence_logs
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ============================================================
-- Add intelligence tracking columns to stakeholders
-- ============================================================

ALTER TABLE stakeholders
    ADD COLUMN IF NOT EXISTS profile_completeness INT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_intelligence_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS intelligence_version INT DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_stakeholders_intelligence
    ON stakeholders(project_id, profile_completeness, last_intelligence_at);

-- ============================================================
-- Extend created_by CHECK to include 'si_agent'
-- ============================================================

-- Drop old constraint and recreate with si_agent
ALTER TABLE stakeholders DROP CONSTRAINT IF EXISTS stakeholders_created_by_check;
ALTER TABLE stakeholders
    ADD CONSTRAINT stakeholders_created_by_check
    CHECK (created_by IN ('system', 'consultant', 'client', 'di_agent', 'si_agent'));
