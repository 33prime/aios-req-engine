-- Migration: 0129_project_launch.sql
-- Smart Project Launch — pipeline tracking tables

-- ============================================================================
-- project_launches: tracks a multi-step launch pipeline for a project
-- ============================================================================
CREATE TABLE IF NOT EXISTS project_launches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'completed_with_errors', 'failed')),
    preferences JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_project_launches_project_id ON project_launches(project_id);

-- ============================================================================
-- launch_steps: individual steps within a launch pipeline
-- ============================================================================
CREATE TABLE IF NOT EXISTS launch_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    launch_id UUID NOT NULL REFERENCES project_launches(id) ON DELETE CASCADE,
    step_key TEXT NOT NULL,
    step_label TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'skipped')),
    depends_on TEXT[] NOT NULL DEFAULT '{}',
    job_id UUID REFERENCES jobs(id),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    result_summary TEXT,
    error_message TEXT,
    retry_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_launch_steps_launch_id ON launch_steps(launch_id);

-- ============================================================================
-- RLS policies (permissive for authenticated users)
-- ============================================================================
ALTER TABLE project_launches ENABLE ROW LEVEL SECURITY;
ALTER TABLE launch_steps ENABLE ROW LEVEL SECURITY;

CREATE POLICY "authenticated_select_project_launches"
    ON project_launches FOR SELECT TO authenticated USING (true);
CREATE POLICY "authenticated_insert_project_launches"
    ON project_launches FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "authenticated_update_project_launches"
    ON project_launches FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

CREATE POLICY "authenticated_select_launch_steps"
    ON launch_steps FOR SELECT TO authenticated USING (true);
CREATE POLICY "authenticated_insert_launch_steps"
    ON launch_steps FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "authenticated_update_launch_steps"
    ON launch_steps FOR UPDATE TO authenticated USING (true) WITH CHECK (true);
