-- Migration: 0119_client_intelligence.sql
-- Client Intelligence Agent: logs table for agent invocations

-- ============================================================
-- client_intelligence_logs: Track agent reasoning and actions
-- ============================================================

CREATE TABLE IF NOT EXISTS client_intelligence_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    trigger TEXT NOT NULL CHECK (trigger IN (
        'new_client', 'stakeholder_added', 'project_milestone',
        'user_request', 'scheduled', 'enrichment_complete', 'signal_confirmed'
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

    -- Results
    profile_completeness_before INT,
    profile_completeness_after INT,
    sections_affected TEXT[] DEFAULT '{}',

    -- Meta
    stop_reason TEXT,
    execution_time_ms INT,
    llm_model TEXT,
    success BOOLEAN NOT NULL DEFAULT true,
    error_message TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ci_logs_client ON client_intelligence_logs(client_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ci_logs_trigger ON client_intelligence_logs(trigger);

-- RLS
ALTER TABLE client_intelligence_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "ci_logs_select" ON client_intelligence_logs
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "ci_logs_insert" ON client_intelligence_logs
    FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "ci_logs_service" ON client_intelligence_logs
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ============================================================
-- Add analysis fields to clients table
-- ============================================================

ALTER TABLE clients
    ADD COLUMN IF NOT EXISTS constraint_summary JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS role_gaps JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS vision_synthesis TEXT,
    ADD COLUMN IF NOT EXISTS organizational_context JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS profile_completeness INT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_analyzed_at TIMESTAMPTZ;
