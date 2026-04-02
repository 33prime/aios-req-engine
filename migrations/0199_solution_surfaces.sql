-- ══════════════════════════════════════════════════════════
-- Solution Surfaces — first-class entity for convergence map
--
-- Replaces solution_flow_steps for the Solution Flow tab.
-- Each surface represents a distinct user-facing screen/view
-- that serves one or more outcomes. Surfaces link to outcomes,
-- features, workflows, and to each other via evolution chains.
--
-- Cascade: when linked outcomes, features, or workflows change,
-- surfaces are marked stale via the existing entity_dependencies
-- graph and mark_dependents_stale() trigger.
-- ══════════════════════════════════════════════════════════

CREATE TABLE solution_surfaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- ── Identity ──
    title TEXT NOT NULL,
    description TEXT,
    route TEXT,                              -- e.g. /onboarding, /forecast
    horizon TEXT NOT NULL DEFAULT 'h1'
        CHECK (horizon IN ('h1', 'h2', 'h3')),

    -- ── Canvas positioning ──
    position_x FLOAT DEFAULT 0,
    position_y FLOAT DEFAULT 0,

    -- ── Evolution lineage ──
    evolves_from_id UUID REFERENCES solution_surfaces(id) ON DELETE SET NULL,

    -- ── Convergence (computed, cached on mutation) ──
    convergence_score INT DEFAULT 0,        -- count of linked outcomes
    is_cross_persona BOOLEAN DEFAULT FALSE, -- serves outcomes from 2+ actors
    convergence_insight TEXT,               -- why this convergence matters

    -- ── Experience definition ──
    experience JSONB DEFAULT '{}',
    -- Schema: {
    --   narr: "What using this feels like...",
    --   layout: "Guided wizard flow",
    --   elements: ["Progress stepper", "Input cards", ...],
    --   interaction: "Sequential, confidence-building",
    --   tone: "Warm and orienting",
    --   reference: "Typeform meets Stripe onboarding"
    -- }

    -- ── Roadmap insight (H2/H3 — how we get here) ──
    roadmap_insight TEXT,

    -- ── How each outcome is served ──
    how_served JSONB DEFAULT '{}',          -- {outcome_id: "explanation"}

    -- ── Linked entities (denormalized for fast canvas rendering) ──
    linked_outcome_ids UUID[] DEFAULT '{}',
    linked_feature_ids UUID[] DEFAULT '{}',
    linked_workflow_ids UUID[] DEFAULT '{}',

    -- ── Freshness (same pattern as features/personas/vp_steps) ──
    is_stale BOOLEAN DEFAULT FALSE,
    stale_reason TEXT,
    stale_since TIMESTAMPTZ,

    -- ── Status ──
    confirmation_status TEXT NOT NULL DEFAULT 'ai_generated'
        CHECK (confirmation_status IN (
            'ai_generated', 'needs_confirmation',
            'confirmed_consultant', 'confirmed_client',
            'needs_review'
        )),
    confirmed_by TEXT,
    confirmed_at TIMESTAMPTZ,

    -- ── Ordering ──
    sort_order INTEGER NOT NULL DEFAULT 0,

    -- ── Standard ──
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── Indexes ──
CREATE INDEX idx_surfaces_project ON solution_surfaces(project_id);
CREATE INDEX idx_surfaces_horizon ON solution_surfaces(project_id, horizon);
CREATE INDEX idx_surfaces_evolves ON solution_surfaces(evolves_from_id)
    WHERE evolves_from_id IS NOT NULL;
CREATE INDEX idx_surfaces_stale ON solution_surfaces(project_id, is_stale)
    WHERE is_stale = TRUE;

-- ── Updated_at trigger ──
CREATE TRIGGER solution_surfaces_updated_at
    BEFORE UPDATE ON solution_surfaces
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ══════════════════════════════════════════════════════════
-- Extend mark_dependents_stale() to handle solution_surface
-- ══════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION mark_dependents_stale()
RETURNS TRIGGER AS $$
DECLARE
  dep RECORD;
  entity_type_arg TEXT;
BEGIN
  entity_type_arg := TG_ARGV[0];

  FOR dep IN
    SELECT source_entity_type, source_entity_id
    FROM entity_dependencies
    WHERE project_id = NEW.project_id
      AND target_entity_type = entity_type_arg
      AND target_entity_id = NEW.id
  LOOP
    CASE dep.source_entity_type
      WHEN 'feature' THEN
        UPDATE features
        SET is_stale = TRUE, stale_reason = entity_type_arg || ' updated', stale_since = now()
        WHERE id = dep.source_entity_id AND (is_stale IS NULL OR is_stale = FALSE);

      WHEN 'persona' THEN
        UPDATE personas
        SET is_stale = TRUE, stale_reason = entity_type_arg || ' updated', stale_since = now()
        WHERE id = dep.source_entity_id AND (is_stale IS NULL OR is_stale = FALSE);

      WHEN 'vp_step' THEN
        UPDATE vp_steps
        SET is_stale = TRUE, stale_reason = entity_type_arg || ' updated', stale_since = now()
        WHERE id = dep.source_entity_id AND (is_stale IS NULL OR is_stale = FALSE);

      WHEN 'strategic_context' THEN
        UPDATE strategic_context
        SET is_stale = TRUE, stale_reason = entity_type_arg || ' updated', stale_since = now()
        WHERE id = dep.source_entity_id AND (is_stale IS NULL OR is_stale = FALSE);

      WHEN 'solution_surface' THEN
        UPDATE solution_surfaces
        SET is_stale = TRUE, stale_reason = entity_type_arg || ' updated', stale_since = now()
        WHERE id = dep.source_entity_id AND (is_stale IS NULL OR is_stale = FALSE);

      ELSE
        NULL;
    END CASE;
  END LOOP;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ── Cascade trigger: when a surface changes, propagate to dependents ──
CREATE TRIGGER surfaces_cascade_staleness
    AFTER UPDATE OF title, description, linked_outcome_ids,
        linked_feature_ids, linked_workflow_ids, experience, horizon
    ON solution_surfaces
    FOR EACH ROW
    EXECUTE FUNCTION mark_dependents_stale('solution_surface');

-- ══════════════════════════════════════════════════════════
-- RLS policies (match existing pattern)
-- ══════════════════════════════════════════════════════════

ALTER TABLE solution_surfaces ENABLE ROW LEVEL SECURITY;

CREATE POLICY "surfaces_select" ON solution_surfaces
    FOR SELECT TO authenticated
    USING (can_access_project(project_id));

CREATE POLICY "surfaces_insert" ON solution_surfaces
    FOR INSERT TO authenticated
    WITH CHECK (can_access_project(project_id));

CREATE POLICY "surfaces_update" ON solution_surfaces
    FOR UPDATE TO authenticated
    USING (can_access_project(project_id));

CREATE POLICY "surfaces_delete" ON solution_surfaces
    FOR DELETE TO authenticated
    USING (can_access_project(project_id));

-- Service role bypass
CREATE POLICY "surfaces_service_all" ON solution_surfaces
    FOR ALL TO service_role
    USING (true) WITH CHECK (true);
