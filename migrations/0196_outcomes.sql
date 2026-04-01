-- Outcomes System: the organizing principle for AIOS.
-- Two-table design: outcomes (core) + outcome_actors (per-persona state changes).
-- Plus outcome_entity_links (junction) and outcome_capabilities (Ways to Achieve).
-- Designed backward from playground-outcomes-discovery.html and playground-outcomes.html.

-- ══════════════════════════════════════════════════════════
-- Macro outcome on projects table
-- ══════════════════════════════════════════════════════════

ALTER TABLE projects ADD COLUMN IF NOT EXISTS macro_outcome TEXT;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS outcome_thesis TEXT;

-- ══════════════════════════════════════════════════════════
-- Core Outcomes
-- A core outcome groups 2+ actor outcomes under a single
-- state change statement. Example: "Critical documents are
-- accessible in a crisis — without lawyers"
-- ══════════════════════════════════════════════════════════

CREATE TABLE outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Identity
    title TEXT NOT NULL,                    -- State change statement
    description TEXT NOT NULL DEFAULT '',   -- Fuller context
    icon TEXT NOT NULL DEFAULT '◉',         -- Display icon

    -- Strength scoring (4 dimensions, 0-25 each, sum = 0-100)
    strength_score INTEGER NOT NULL DEFAULT 0
        CHECK (strength_score BETWEEN 0 AND 100),
    strength_dimensions JSONB NOT NULL DEFAULT '{
        "specificity": 0,
        "scenario": 0,
        "cost_of_failure": 0,
        "observable": 0
    }',

    -- Classification
    horizon TEXT NOT NULL DEFAULT 'h1'
        CHECK (horizon IN ('h1', 'h2', 'h3')),
    status TEXT NOT NULL DEFAULT 'candidate'
        CHECK (status IN ('candidate', 'confirmed', 'validated', 'achieved')),
    confirmation_status TEXT NOT NULL DEFAULT 'ai_generated'
        CHECK (confirmation_status IN ('ai_generated', 'needs_client', 'confirmed_consultant', 'confirmed_client')),

    -- Content (from playground UI)
    what_helps JSONB DEFAULT '[]',          -- Array of strings
    evidence JSONB DEFAULT '[]',            -- [{direction: "toward"|"away"|"reframe", text, signal_id, source_authority}]

    -- Provenance
    source_type TEXT NOT NULL DEFAULT 'system_generated'
        CHECK (source_type IN ('system_generated', 'consultant_created', 'intelligence_discovered')),
    generation_context JSONB DEFAULT '{}',  -- What entity patterns generated this

    -- Enrichment (same pipeline as entities)
    enrichment_intel JSONB DEFAULT '{}',

    -- Display
    display_order INTEGER NOT NULL DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_outcomes_project ON outcomes(project_id);
CREATE INDEX idx_outcomes_project_horizon ON outcomes(project_id, horizon);
CREATE INDEX idx_outcomes_project_order ON outcomes(project_id, display_order);

-- ══════════════════════════════════════════════════════════
-- Actor Outcomes: per-persona state changes within a core outcome.
-- Real columns for queryable fields (strength, status, sharpen_prompt).
-- Designed from playground: each actor outcome has its own
-- before/after, metric, strength, and sharpen prompt.
-- ══════════════════════════════════════════════════════════

CREATE TABLE outcome_actors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outcome_id UUID NOT NULL REFERENCES outcomes(id) ON DELETE CASCADE,
    persona_id UUID REFERENCES personas(id) ON DELETE SET NULL,

    -- Identity
    persona_name TEXT NOT NULL,             -- Denormalized for display (survives persona deletion)
    title TEXT NOT NULL,                    -- Persona-specific state change

    -- Before/After transform (the core of the actor outcome)
    before_state TEXT NOT NULL DEFAULT '',  -- "Today" state
    after_state TEXT NOT NULL DEFAULT '',   -- "Must be true" state

    -- Measurability
    metric TEXT NOT NULL DEFAULT '',        -- Observable/measurable criterion

    -- Strength (individual, 0-100, independent of core outcome strength)
    strength_score INTEGER NOT NULL DEFAULT 0
        CHECK (strength_score BETWEEN 0 AND 100),

    -- Status (independent lifecycle from core outcome)
    status TEXT NOT NULL DEFAULT 'not_started'
        CHECK (status IN ('not_started', 'emerging', 'confirmed', 'validated')),

    -- Sharpen prompt (generated when strength < 70, regenerated on dimension changes)
    sharpen_prompt TEXT,

    -- Evidence for this specific actor outcome
    evidence JSONB DEFAULT '[]',           -- [{direction, text, source, signal_id}]

    -- Display
    display_order INTEGER NOT NULL DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_outcome_actors_outcome ON outcome_actors(outcome_id);
CREATE INDEX idx_outcome_actors_persona ON outcome_actors(persona_id);
CREATE INDEX idx_outcome_actors_strength ON outcome_actors(strength_score)
    WHERE strength_score < 70;  -- Fast lookup for "needs sharpening"

-- ══════════════════════════════════════════════════════════
-- Outcome-Entity Links: which entities serve which outcomes.
-- link_type determines the relationship semantics.
-- surface_of links connect outcomes to solution_flow_steps.
-- ══════════════════════════════════════════════════════════

CREATE TABLE outcome_entity_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outcome_id UUID NOT NULL REFERENCES outcomes(id) ON DELETE CASCADE,
    entity_id UUID NOT NULL,
    entity_type TEXT NOT NULL,
    link_type TEXT NOT NULL DEFAULT 'serves'
        CHECK (link_type IN (
            'serves',       -- feature/workflow serves this outcome
            'blocks',       -- constraint/compliance blocks this outcome
            'enables',      -- capability/integration enables this outcome
            'measures',     -- KPI/business_driver measures progress toward this outcome
            'evidence_for', -- business_driver (pain/goal) is evidence supporting this outcome
            'surface_of'    -- solution_flow_step is a surface where this outcome materializes
        )),
    how_served TEXT,        -- Explanation of HOW this entity serves the outcome
    confidence TEXT NOT NULL DEFAULT 'ai_generated'
        CHECK (confidence IN ('ai_generated', 'confirmed_consultant', 'confirmed_client')),

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(outcome_id, entity_id, entity_type, link_type)
);

CREATE INDEX idx_oel_outcome ON outcome_entity_links(outcome_id);
CREATE INDEX idx_oel_entity ON outcome_entity_links(entity_id, entity_type);
CREATE INDEX idx_oel_surface ON outcome_entity_links(link_type)
    WHERE link_type = 'surface_of';

-- ══════════════════════════════════════════════════════════
-- Outcome Capabilities: "Ways to Achieve" per outcome.
-- Solution-side intelligence items: knowledge, scoring, decision, AI.
-- For the AI quadrant, links to the full agents table.
-- ══════════════════════════════════════════════════════════

CREATE TABLE outcome_capabilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    outcome_id UUID NOT NULL REFERENCES outcomes(id) ON DELETE CASCADE,

    -- Identity
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    quadrant TEXT NOT NULL
        CHECK (quadrant IN ('knowledge', 'scoring', 'decision', 'ai')),
    badge TEXT NOT NULL DEFAULT 'suggested'
        CHECK (badge IN ('created', 'suggested')),

    -- For AI quadrant: optional link to full agent record
    agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,

    -- Enrichment (same pipeline as entities)
    enrichment_intel JSONB DEFAULT '{}',

    -- Status
    confirmation_status TEXT NOT NULL DEFAULT 'ai_generated'
        CHECK (confirmation_status IN ('ai_generated', 'confirmed_consultant', 'confirmed_client')),

    -- Display
    display_order INTEGER NOT NULL DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_outcome_caps_outcome ON outcome_capabilities(outcome_id);
CREATE INDEX idx_outcome_caps_project ON outcome_capabilities(project_id);
CREATE INDEX idx_outcome_caps_quadrant ON outcome_capabilities(project_id, quadrant);

-- ══════════════════════════════════════════════════════════
-- RPC: match_outcomes
-- Vector search on outcomes via entity_vectors table.
-- Outcomes are stored in entity_vectors with entity_type='outcome'.
-- This is a convenience wrapper.
-- ══════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION match_outcomes(
    query_embedding vector(1536),
    match_count int,
    filter_project_id uuid
)
RETURNS TABLE (
    outcome_id uuid,
    title text,
    strength_score int,
    horizon text,
    status text,
    similarity float4
)
LANGUAGE plpgsql STABLE AS $$
BEGIN
    RETURN QUERY
    SELECT
        o.id AS outcome_id,
        o.title,
        o.strength_score,
        o.horizon,
        o.status,
        (1 - (ev.embedding <=> query_embedding))::float4 AS similarity
    FROM entity_vectors ev
    JOIN outcomes o ON o.id = ev.entity_id
    WHERE ev.project_id = filter_project_id
      AND ev.entity_type = 'outcome'
      AND ev.vector_type = 'identity'
    ORDER BY ev.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ══════════════════════════════════════════════════════════
-- RLS Policies
-- ══════════════════════════════════════════════════════════

ALTER TABLE outcomes ENABLE ROW LEVEL SECURITY;
ALTER TABLE outcome_actors ENABLE ROW LEVEL SECURITY;
ALTER TABLE outcome_entity_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE outcome_capabilities ENABLE ROW LEVEL SECURITY;

-- Service role: full access
CREATE POLICY outcomes_service ON outcomes FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY outcome_actors_service ON outcome_actors FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY oel_service ON outcome_entity_links FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY outcome_caps_service ON outcome_capabilities FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Authenticated: full CRUD
CREATE POLICY outcomes_auth ON outcomes FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY outcome_actors_auth ON outcome_actors FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY oel_auth ON outcome_entity_links FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY outcome_caps_auth ON outcome_capabilities FOR ALL TO authenticated USING (true) WITH CHECK (true);
