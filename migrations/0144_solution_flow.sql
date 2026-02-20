-- Migration 0144: Solution Flow tables
-- Goal-oriented sequential flow that shows what the app actually does

-- Solution flow (one per project)
CREATE TABLE solution_flows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title TEXT NOT NULL DEFAULT 'Solution Flow',
    summary TEXT,
    generated_at TIMESTAMPTZ,
    confirmation_status TEXT NOT NULL DEFAULT 'ai_generated'
        CHECK (confirmation_status IN ('ai_generated', 'confirmed_consultant', 'confirmed_client', 'needs_client')),
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (project_id)
);

-- Solution flow steps
CREATE TABLE solution_flow_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flow_id UUID NOT NULL REFERENCES solution_flows(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    step_index INTEGER NOT NULL,
    phase TEXT NOT NULL CHECK (phase IN ('entry', 'core_experience', 'output', 'admin')),
    title TEXT NOT NULL,
    goal TEXT NOT NULL,
    actors TEXT[] DEFAULT '{}',
    information_fields JSONB DEFAULT '[]'::jsonb,
    mock_data_narrative TEXT,
    open_questions JSONB DEFAULT '[]'::jsonb,
    implied_pattern TEXT,
    confirmation_status TEXT NOT NULL DEFAULT 'ai_generated'
        CHECK (confirmation_status IN ('ai_generated', 'confirmed_consultant', 'confirmed_client', 'needs_client')),
    version INTEGER NOT NULL DEFAULT 1,
    linked_workflow_ids UUID[] DEFAULT '{}',
    linked_feature_ids UUID[] DEFAULT '{}',
    linked_data_entity_ids UUID[] DEFAULT '{}',
    evidence_ids UUID[] DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX idx_solution_flows_project ON solution_flows(project_id);
CREATE INDEX idx_solution_flow_steps_flow ON solution_flow_steps(flow_id, step_index);
CREATE INDEX idx_solution_flow_steps_project ON solution_flow_steps(project_id);

-- RLS (CRITICAL — must have policies or queries return empty in prod)
ALTER TABLE solution_flows ENABLE ROW LEVEL SECURITY;
CREATE POLICY "authenticated_read_solution_flows" ON solution_flows FOR SELECT TO authenticated USING (true);
CREATE POLICY "authenticated_write_solution_flows" ON solution_flows FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "authenticated_update_solution_flows" ON solution_flows FOR UPDATE TO authenticated USING (true);
CREATE POLICY "authenticated_delete_solution_flows" ON solution_flows FOR DELETE TO authenticated USING (true);
CREATE POLICY "service_role_all_solution_flows" ON solution_flows FOR ALL TO service_role USING (true);

ALTER TABLE solution_flow_steps ENABLE ROW LEVEL SECURITY;
CREATE POLICY "authenticated_read_solution_flow_steps" ON solution_flow_steps FOR SELECT TO authenticated USING (true);
CREATE POLICY "authenticated_write_solution_flow_steps" ON solution_flow_steps FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "authenticated_update_solution_flow_steps" ON solution_flow_steps FOR UPDATE TO authenticated USING (true);
CREATE POLICY "authenticated_delete_solution_flow_steps" ON solution_flow_steps FOR DELETE TO authenticated USING (true);
CREATE POLICY "service_role_all_solution_flow_steps" ON solution_flow_steps FOR ALL TO service_role USING (true);
