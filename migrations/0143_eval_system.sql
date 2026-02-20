-- Eval Pipeline: prompt versioning, eval runs, and gap tracking
-- Supports the self-healing prototype generation loop

-- =============================================================================
-- prompt_versions — immutable prompt history per prototype
-- =============================================================================

CREATE TABLE prompt_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prototype_id UUID NOT NULL REFERENCES prototypes(id) ON DELETE CASCADE,
    version_number INT NOT NULL,
    prompt_text TEXT NOT NULL,
    parent_version_id UUID REFERENCES prompt_versions(id),
    generation_model TEXT,
    generation_chain TEXT,
    input_context_snapshot JSONB DEFAULT '{}',
    learnings_injected JSONB DEFAULT '[]',
    tokens_input INT DEFAULT 0,
    tokens_output INT DEFAULT 0,
    tokens_cache_read INT DEFAULT 0,
    tokens_cache_create INT DEFAULT 0,
    estimated_cost_usd NUMERIC(8,6) DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(prototype_id, version_number)
);

CREATE INDEX idx_prompt_versions_prototype ON prompt_versions(prototype_id);
CREATE INDEX idx_prompt_versions_parent ON prompt_versions(parent_version_id);


-- =============================================================================
-- eval_runs — one row per evaluation with split deterministic + LLM scores
-- =============================================================================

CREATE TABLE eval_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt_version_id UUID NOT NULL REFERENCES prompt_versions(id) ON DELETE CASCADE,
    prototype_id UUID NOT NULL REFERENCES prototypes(id) ON DELETE CASCADE,

    -- Deterministic scores
    det_handoff_present BOOLEAN DEFAULT FALSE,
    det_feature_id_coverage NUMERIC(5,4) DEFAULT 0,
    det_file_structure NUMERIC(5,4) DEFAULT 0,
    det_route_count NUMERIC(5,4) DEFAULT 0,
    det_jsdoc_coverage NUMERIC(5,4) DEFAULT 0,
    det_composite NUMERIC(5,4) DEFAULT 0,

    -- LLM-judged scores
    llm_feature_coverage NUMERIC(5,4) DEFAULT 0,
    llm_structure NUMERIC(5,4) DEFAULT 0,
    llm_mock_data NUMERIC(5,4) DEFAULT 0,
    llm_flow NUMERIC(5,4) DEFAULT 0,
    llm_feature_id NUMERIC(5,4) DEFAULT 0,
    llm_overall NUMERIC(5,4) DEFAULT 0,

    -- Combined
    overall_score NUMERIC(5,4) DEFAULT 0,
    action TEXT NOT NULL DEFAULT 'pending' CHECK (action IN ('pending', 'accept', 'retry', 'notify')),

    -- Context
    iteration_number INT NOT NULL DEFAULT 1,
    file_tree JSONB DEFAULT '[]',
    feature_scan JSONB DEFAULT '{}',
    handoff_content TEXT,
    recommendations JSONB DEFAULT '[]',

    -- Performance tracking
    deterministic_duration_ms INT DEFAULT 0,
    llm_duration_ms INT DEFAULT 0,
    tokens_input INT DEFAULT 0,
    tokens_output INT DEFAULT 0,
    tokens_cache_read INT DEFAULT 0,
    tokens_cache_create INT DEFAULT 0,
    estimated_cost_usd NUMERIC(8,6) DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_eval_runs_prototype ON eval_runs(prototype_id);
CREATE INDEX idx_eval_runs_prompt_version ON eval_runs(prompt_version_id);
CREATE INDEX idx_eval_runs_action ON eval_runs(action);


-- =============================================================================
-- eval_gaps — normalized gap records per eval run
-- =============================================================================

CREATE TABLE eval_gaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    eval_run_id UUID NOT NULL REFERENCES eval_runs(id) ON DELETE CASCADE,
    dimension TEXT NOT NULL CHECK (dimension IN (
        'feature_coverage', 'structure', 'mock_data', 'flow',
        'feature_id', 'handoff', 'jsdoc', 'route_count'
    )),
    description TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'medium' CHECK (severity IN ('high', 'medium', 'low')),
    feature_ids TEXT[] DEFAULT '{}',
    gap_pattern TEXT,
    resolved_in_run_id UUID REFERENCES eval_runs(id),
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_eval_gaps_run ON eval_gaps(eval_run_id);
CREATE INDEX idx_eval_gaps_dimension ON eval_gaps(dimension);
CREATE INDEX idx_eval_gaps_unresolved ON eval_gaps(eval_run_id)
    WHERE resolved_in_run_id IS NULL;


-- =============================================================================
-- ALTER prompt_template_learnings — add eval linkage
-- =============================================================================

ALTER TABLE prompt_template_learnings
    ADD COLUMN IF NOT EXISTS eval_run_id UUID REFERENCES eval_runs(id),
    ADD COLUMN IF NOT EXISTS dimension TEXT,
    ADD COLUMN IF NOT EXISTS gap_pattern TEXT;


-- =============================================================================
-- RLS — enable but no policies (backend-only via service_role)
-- =============================================================================

ALTER TABLE prompt_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE eval_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE eval_gaps ENABLE ROW LEVEL SECURITY;
