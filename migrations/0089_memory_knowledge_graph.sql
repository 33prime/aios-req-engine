-- Migration: Memory Knowledge Graph
-- Adds knowledge graph structure for intelligent memory management
-- Facts (immutable) + Beliefs (evolving) + Insights (generated) connected by edges

-- =============================================================================
-- Memory Nodes
-- =============================================================================
-- The fundamental unit of knowledge - facts, beliefs, insights

CREATE TABLE IF NOT EXISTS memory_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Node classification
    node_type TEXT NOT NULL CHECK (node_type IN ('fact', 'belief', 'insight')),

    -- Content
    content TEXT NOT NULL,           -- The full knowledge content
    summary TEXT NOT NULL,           -- One-line summary for display

    -- Confidence (1.0 for facts, 0.0-1.0 for beliefs/insights)
    confidence FLOAT NOT NULL DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),

    -- Status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,  -- FALSE = archived
    archived_at TIMESTAMPTZ,
    archive_reason TEXT,

    -- Source attribution
    source_type TEXT CHECK (source_type IN ('signal', 'agent', 'user', 'synthesis', 'reflection')),
    source_id UUID,                  -- Link to signal_id, di_agent_logs.id, etc.

    -- Entity linking (optional - for connecting to features, personas, etc.)
    linked_entity_type TEXT CHECK (linked_entity_type IN ('feature', 'persona', 'vp_step', 'stakeholder', 'business_driver', 'competitor')),
    linked_entity_id UUID,

    -- For beliefs: categorization
    belief_domain TEXT,              -- 'client_priority', 'technical', 'market', 'user_need', 'constraint'

    -- For insights: categorization
    insight_type TEXT,               -- 'behavioral', 'contradiction', 'evolution', 'risk', 'opportunity'

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_memory_nodes_project ON memory_nodes(project_id);
CREATE INDEX idx_memory_nodes_project_type ON memory_nodes(project_id, node_type);
CREATE INDEX idx_memory_nodes_project_active ON memory_nodes(project_id, is_active) WHERE is_active = TRUE;
CREATE INDEX idx_memory_nodes_confidence ON memory_nodes(project_id, confidence DESC) WHERE is_active = TRUE;
CREATE INDEX idx_memory_nodes_linked_entity ON memory_nodes(linked_entity_type, linked_entity_id) WHERE linked_entity_id IS NOT NULL;

-- =============================================================================
-- Memory Edges
-- =============================================================================
-- Relationships between nodes - the graph structure

CREATE TABLE IF NOT EXISTS memory_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Edge endpoints
    from_node_id UUID NOT NULL REFERENCES memory_nodes(id) ON DELETE CASCADE,
    to_node_id UUID NOT NULL REFERENCES memory_nodes(id) ON DELETE CASCADE,

    -- Relationship type
    edge_type TEXT NOT NULL CHECK (edge_type IN (
        'supports',      -- Evidence for (fact supports belief)
        'contradicts',   -- Evidence against (fact contradicts belief)
        'caused_by',     -- Causal chain (decision caused_by fact)
        'leads_to',      -- Consequence (belief leads_to insight)
        'supersedes',    -- Replaces (new belief supersedes old)
        'related_to'     -- General semantic connection
    )),

    -- Edge strength (for weighted operations)
    strength FLOAT NOT NULL DEFAULT 1.0 CHECK (strength >= 0.0 AND strength <= 1.0),

    -- Explanation
    rationale TEXT,                  -- Why does this connection exist?

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Prevent duplicate edges of same type between same nodes
    UNIQUE(from_node_id, to_node_id, edge_type)
);

CREATE INDEX idx_memory_edges_project ON memory_edges(project_id);
CREATE INDEX idx_memory_edges_from ON memory_edges(from_node_id);
CREATE INDEX idx_memory_edges_to ON memory_edges(to_node_id);
CREATE INDEX idx_memory_edges_type ON memory_edges(project_id, edge_type);

-- =============================================================================
-- Belief History
-- =============================================================================
-- Audit trail of how beliefs evolve over time

CREATE TABLE IF NOT EXISTS belief_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id UUID NOT NULL REFERENCES memory_nodes(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- What changed
    previous_content TEXT,
    previous_confidence FLOAT,
    new_content TEXT,
    new_confidence FLOAT,

    -- Why it changed
    change_type TEXT NOT NULL CHECK (change_type IN (
        'confidence_increase',   -- More supporting evidence
        'confidence_decrease',   -- Contradicting evidence
        'content_refined',       -- Better understanding, same meaning
        'content_changed',       -- Meaning shifted
        'superseded',            -- Replaced by new belief
        'archived'               -- No longer relevant
    )),
    change_reason TEXT NOT NULL,

    -- What triggered the change
    triggered_by_node_id UUID REFERENCES memory_nodes(id),  -- The fact/signal that caused this
    triggered_by_synthesis_id UUID,                          -- Link to synthesis log

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_belief_history_node ON belief_history(node_id);
CREATE INDEX idx_belief_history_project ON belief_history(project_id, created_at DESC);

-- =============================================================================
-- Memory Synthesis Log
-- =============================================================================
-- Track synthesis/reflection runs

CREATE TABLE IF NOT EXISTS memory_synthesis_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- What ran
    synthesis_type TEXT NOT NULL CHECK (synthesis_type IN ('watcher', 'synthesizer', 'reflector')),

    -- Trigger info
    trigger_type TEXT NOT NULL,      -- 'signal_processed', 'importance_threshold', 'scheduled', 'manual'
    trigger_details JSONB DEFAULT '{}',

    -- Input stats
    input_facts_count INTEGER DEFAULT 0,
    input_beliefs_count INTEGER DEFAULT 0,

    -- Output stats
    facts_created INTEGER DEFAULT 0,
    beliefs_created INTEGER DEFAULT 0,
    beliefs_updated INTEGER DEFAULT 0,
    insights_created INTEGER DEFAULT 0,
    edges_created INTEGER DEFAULT 0,

    -- Cost tracking
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    model_used TEXT,
    estimated_cost_usd FLOAT,

    -- Timing
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,

    -- Status
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed')),
    error_message TEXT
);

CREATE INDEX idx_synthesis_log_project ON memory_synthesis_log(project_id, started_at DESC);
CREATE INDEX idx_synthesis_log_type ON memory_synthesis_log(project_id, synthesis_type);

-- =============================================================================
-- Triggers
-- =============================================================================

-- Auto-update updated_at on memory_nodes
CREATE OR REPLACE FUNCTION update_memory_node_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_memory_node_updated
    BEFORE UPDATE ON memory_nodes
    FOR EACH ROW
    EXECUTE FUNCTION update_memory_node_timestamp();

-- =============================================================================
-- Comments
-- =============================================================================

COMMENT ON TABLE memory_nodes IS 'Knowledge graph nodes - facts (immutable observations), beliefs (evolving interpretations), insights (generated patterns)';
COMMENT ON TABLE memory_edges IS 'Relationships between nodes - supports, contradicts, caused_by, leads_to, supersedes, related_to';
COMMENT ON TABLE belief_history IS 'Audit trail of how beliefs evolve with each change reason and trigger';
COMMENT ON TABLE memory_synthesis_log IS 'Tracking for memory agent runs - watcher, synthesizer, reflector';

COMMENT ON COLUMN memory_nodes.node_type IS 'fact=immutable observation, belief=evolving interpretation, insight=generated pattern';
COMMENT ON COLUMN memory_nodes.confidence IS '1.0 for facts, 0.0-1.0 for beliefs/insights based on evidence strength';
COMMENT ON COLUMN memory_nodes.linked_entity_type IS 'Optional link to project entities for cross-referencing';
COMMENT ON COLUMN memory_edges.edge_type IS 'supports=evidence for, contradicts=evidence against, caused_by=causal, leads_to=consequence, supersedes=replaces';
COMMENT ON COLUMN memory_edges.strength IS 'Edge weight for graph algorithms, 1.0=strong connection';
