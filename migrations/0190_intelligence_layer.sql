-- Intelligence Layer: first-class agents, tools, chat, and executions
-- Agents are spawned from solution flow steps but live independently.

-- ══════════════════════════════════════════════════════════
-- Agents
-- ══════════════════════════════════════════════════════════

CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    source_step_id UUID REFERENCES solution_flow_steps(id) ON DELETE SET NULL,

    -- Identity
    name TEXT NOT NULL,
    icon TEXT NOT NULL DEFAULT '⬡',
    agent_type TEXT NOT NULL DEFAULT 'processor'
        CHECK (agent_type IN ('classifier', 'matcher', 'predictor', 'watcher', 'generator', 'processor')),
    role_description TEXT NOT NULL DEFAULT '',

    -- Autonomy
    autonomy_level INTEGER NOT NULL DEFAULT 50 CHECK (autonomy_level BETWEEN 0 AND 100),
    can_do TEXT[] DEFAULT '{}',
    needs_approval TEXT[] DEFAULT '{}',
    cannot_do TEXT[] DEFAULT '{}',

    -- Human partner
    partner_role TEXT,
    partner_name TEXT,
    partner_initials TEXT,
    partner_color TEXT,
    partner_relationship TEXT,
    partner_escalations TEXT,

    -- Data access
    data_sources JSONB DEFAULT '[]'::jsonb,

    -- Pipeline dependencies (stored as agent IDs)
    depends_on_agent_ids UUID[] DEFAULT '{}',
    feeds_agent_ids UUID[] DEFAULT '{}',

    -- Intelligence metadata
    maturity TEXT NOT NULL DEFAULT 'learning'
        CHECK (maturity IN ('learning', 'reliable', 'expert')),
    technique TEXT DEFAULT 'llm'
        CHECK (technique IN ('llm', 'classification', 'embeddings', 'rules', 'hybrid')),
    rhythm TEXT DEFAULT 'on_demand'
        CHECK (rhythm IN ('triggered', 'always_on', 'on_demand', 'periodic')),
    automation_rate INTEGER DEFAULT 50 CHECK (automation_rate BETWEEN 0 AND 100),

    -- Narrative content
    daily_work_narrative TEXT,
    growth_narrative TEXT,
    consultant_insight TEXT,
    transform_before TEXT,
    transform_after TEXT,

    -- Chat context
    chat_intro TEXT,
    chat_suggestions TEXT[] DEFAULT '{}',

    -- Sample I/O for "See in Action"
    sample_input TEXT,
    sample_output JSONB DEFAULT '[]'::jsonb,

    -- Processing steps for animation (each: {label, tool_icon, tool_name})
    processing_steps JSONB DEFAULT '[]'::jsonb,

    -- Cascade effects (each: {target_agent_name, effect_description})
    cascade_effects JSONB DEFAULT '[]'::jsonb,

    -- Validation
    validation_status TEXT NOT NULL DEFAULT 'unvalidated'
        CHECK (validation_status IN ('unvalidated', 'validated', 'needs_review')),
    validated_at TIMESTAMPTZ,
    validated_behaviors JSONB DEFAULT '[]'::jsonb,

    -- Confidence tiers
    confidence_high INTEGER DEFAULT 0,
    confidence_medium INTEGER DEFAULT 0,
    confidence_low INTEGER DEFAULT 0,

    -- Ordering
    display_order INTEGER NOT NULL DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_agents_project ON agents(project_id);
CREATE INDEX idx_agents_source_step ON agents(source_step_id);

-- ══════════════════════════════════════════════════════════
-- Agent Tools
-- ══════════════════════════════════════════════════════════

CREATE TABLE agent_tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    name TEXT NOT NULL,
    icon TEXT NOT NULL DEFAULT '🔧',
    description TEXT NOT NULL DEFAULT '',
    example TEXT,
    data_touches TEXT[] DEFAULT '{}',
    reliability INTEGER DEFAULT 90 CHECK (reliability BETWEEN 0 AND 100),

    display_order INTEGER NOT NULL DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_agent_tools_agent ON agent_tools(agent_id);

-- ══════════════════════════════════════════════════════════
-- Agent Chat Messages
-- ══════════════════════════════════════════════════════════

CREATE TABLE agent_chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    role TEXT NOT NULL CHECK (role IN ('user', 'agent', 'system')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_agent_chat_agent_ts ON agent_chat_messages(agent_id, created_at);

-- ══════════════════════════════════════════════════════════
-- Agent Executions ("See in Action" runs)
-- ══════════════════════════════════════════════════════════

CREATE TABLE agent_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    input_text TEXT NOT NULL,
    output JSONB NOT NULL DEFAULT '[]'::jsonb,
    execution_time_ms INTEGER NOT NULL DEFAULT 0,
    model TEXT NOT NULL DEFAULT 'haiku',

    validation_verdict TEXT CHECK (validation_verdict IN ('confirmed', 'adjusted')),
    adjustment_notes TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_agent_executions_agent ON agent_executions(agent_id, created_at DESC);

-- ══════════════════════════════════════════════════════════
-- RLS Policies
-- ══════════════════════════════════════════════════════════

ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_tools ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_executions ENABLE ROW LEVEL SECURITY;

-- Service role: full access
CREATE POLICY agents_service ON agents FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY agent_tools_service ON agent_tools FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY agent_chat_service ON agent_chat_messages FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY agent_exec_service ON agent_executions FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Authenticated: read/write own project data
CREATE POLICY agents_auth_read ON agents FOR SELECT TO authenticated USING (true);
CREATE POLICY agents_auth_insert ON agents FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY agents_auth_update ON agents FOR UPDATE TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY agents_auth_delete ON agents FOR DELETE TO authenticated USING (true);

CREATE POLICY agent_tools_auth_read ON agent_tools FOR SELECT TO authenticated USING (true);
CREATE POLICY agent_tools_auth_insert ON agent_tools FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY agent_tools_auth_update ON agent_tools FOR UPDATE TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY agent_tools_auth_delete ON agent_tools FOR DELETE TO authenticated USING (true);

CREATE POLICY agent_chat_auth_read ON agent_chat_messages FOR SELECT TO authenticated USING (true);
CREATE POLICY agent_chat_auth_insert ON agent_chat_messages FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY agent_exec_auth_read ON agent_executions FOR SELECT TO authenticated USING (true);
CREATE POLICY agent_exec_auth_insert ON agent_executions FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY agent_exec_auth_update ON agent_executions FOR UPDATE TO authenticated USING (true) WITH CHECK (true);
