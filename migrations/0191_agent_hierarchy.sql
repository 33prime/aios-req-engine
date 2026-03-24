-- Agent hierarchy: orchestrator → sub-agent → tools
-- Backwards compatible: existing agents get parent_agent_id=NULL, agent_role='peer'

-- Parent-child relationship for agent hierarchy
ALTER TABLE agents ADD COLUMN parent_agent_id UUID REFERENCES agents(id) ON DELETE CASCADE;
ALTER TABLE agents ADD COLUMN agent_role TEXT NOT NULL DEFAULT 'peer'
    CHECK (agent_role IN ('orchestrator', 'sub_agent', 'peer'));

-- Fast child lookups
CREATE INDEX idx_agents_parent ON agents(parent_agent_id) WHERE parent_agent_id IS NOT NULL;

-- Add orchestrator to agent_type enum
ALTER TABLE agents DROP CONSTRAINT agents_agent_type_check;
ALTER TABLE agents ADD CONSTRAINT agents_agent_type_check
    CHECK (agent_type IN ('classifier','matcher','predictor','watcher','generator','processor','orchestrator'));
