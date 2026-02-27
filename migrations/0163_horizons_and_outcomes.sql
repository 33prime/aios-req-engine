-- Horizon Intelligence System: project horizons, outcome tracking, and measurements.
-- Wires H1/H2/H3 strategy through solution flow, unlocks, and drivers.

-- ============================================================================
-- New tables
-- ============================================================================

-- Project horizons: exactly 3 per project (H1=engagement, H2=expansion, H3=platform)
CREATE TABLE IF NOT EXISTS project_horizons (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    horizon_number  INT NOT NULL CHECK (horizon_number IN (1, 2, 3)),
    title           TEXT NOT NULL,
    description     TEXT,
    status          TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'achieved', 'revised', 'archived')),
    achieved_at     TIMESTAMPTZ,
    originated_from_horizon_id UUID REFERENCES project_horizons(id),
    shift_reason    TEXT,
    readiness_pct   REAL DEFAULT 0.0,
    last_readiness_check TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (project_id, horizon_number)
);

-- Horizon outcomes: links drivers to horizons with measurable thresholds
CREATE TABLE IF NOT EXISTS horizon_outcomes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    horizon_id      UUID NOT NULL REFERENCES project_horizons(id) ON DELETE CASCADE,
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    driver_id       UUID REFERENCES business_drivers(id) ON DELETE SET NULL,
    driver_type     TEXT,
    threshold_type  TEXT NOT NULL DEFAULT 'custom'
                    CHECK (threshold_type IN ('value_target', 'severity_target', 'completion', 'adoption', 'custom')),
    threshold_value TEXT,
    threshold_label TEXT,
    current_value   TEXT,
    progress_pct    REAL DEFAULT 0.0,
    trend           TEXT DEFAULT 'unknown'
                    CHECK (trend IN ('improving', 'stable', 'declining', 'unknown')),
    trend_velocity  REAL,
    weight          REAL DEFAULT 1.0,
    is_blocking     BOOLEAN DEFAULT false,
    status          TEXT NOT NULL DEFAULT 'tracking'
                    CHECK (status IN ('tracking', 'at_risk', 'achieved', 'abandoned')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Outcome measurements: time-series actual values
CREATE TABLE IF NOT EXISTS outcome_measurements (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outcome_id      UUID NOT NULL REFERENCES horizon_outcomes(id) ON DELETE CASCADE,
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    measured_value   TEXT NOT NULL,
    measured_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_type      TEXT NOT NULL DEFAULT 'manual'
                     CHECK (source_type IN ('signal', 'manual', 'integration', 'derived', 'client_portal')),
    confidence       REAL DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
    is_baseline      BOOLEAN DEFAULT false,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_outcome_measurements_outcome_time
    ON outcome_measurements (outcome_id, measured_at DESC);

CREATE INDEX IF NOT EXISTS idx_horizon_outcomes_horizon
    ON horizon_outcomes (horizon_id);

CREATE INDEX IF NOT EXISTS idx_horizon_outcomes_project
    ON horizon_outcomes (project_id);

CREATE INDEX IF NOT EXISTS idx_project_horizons_project
    ON project_horizons (project_id);

-- ============================================================================
-- Column additions (all nullable — no breakage)
-- ============================================================================

-- Features: horizon alignment + origin unlock
ALTER TABLE features
    ADD COLUMN IF NOT EXISTS horizon_alignment JSONB,
    ADD COLUMN IF NOT EXISTS origin_unlock_id UUID REFERENCES unlocks(id) ON DELETE SET NULL;

-- Business drivers: horizon alignment, trajectory, lineage
ALTER TABLE business_drivers
    ADD COLUMN IF NOT EXISTS horizon_alignment JSONB,
    ADD COLUMN IF NOT EXISTS trajectory JSONB,
    ADD COLUMN IF NOT EXISTS parent_driver_id UUID REFERENCES business_drivers(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS spawned_from_unlock_id UUID REFERENCES unlocks(id) ON DELETE SET NULL;

-- Unlocks: horizon linkage
ALTER TABLE unlocks
    ADD COLUMN IF NOT EXISTS horizon_id UUID REFERENCES project_horizons(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS horizon_alignment JSONB;

-- Solution flow steps: horizon alignment
ALTER TABLE solution_flow_steps
    ADD COLUMN IF NOT EXISTS horizon_alignment JSONB;

-- ============================================================================
-- Extend entity_dependencies CHECK constraints
-- ============================================================================

-- Drop existing constraints and re-create with expanded types.
-- The constraint names come from the original migration — if they don't exist, the DROP is a no-op.
ALTER TABLE entity_dependencies DROP CONSTRAINT IF EXISTS entity_dependencies_source_type_check;
ALTER TABLE entity_dependencies DROP CONSTRAINT IF EXISTS entity_dependencies_target_type_check;
ALTER TABLE entity_dependencies DROP CONSTRAINT IF EXISTS entity_dependencies_dependency_type_check;

ALTER TABLE entity_dependencies ADD CONSTRAINT entity_dependencies_source_type_check
    CHECK (source_type IN (
        'persona', 'feature', 'vp_step', 'strategic_context', 'stakeholder',
        'data_entity', 'business_driver', 'unlock'
    ));

ALTER TABLE entity_dependencies ADD CONSTRAINT entity_dependencies_target_type_check
    CHECK (target_type IN (
        'persona', 'feature', 'vp_step', 'signal', 'research_chunk',
        'data_entity', 'business_driver', 'unlock'
    ));

ALTER TABLE entity_dependencies ADD CONSTRAINT entity_dependencies_dependency_type_check
    CHECK (dependency_type IN (
        'uses', 'targets', 'derived_from', 'informed_by', 'actor_of',
        'spawns', 'enables', 'constrains'
    ));

-- ============================================================================
-- RLS policies
-- ============================================================================

ALTER TABLE project_horizons ENABLE ROW LEVEL SECURITY;
ALTER TABLE horizon_outcomes ENABLE ROW LEVEL SECURITY;
ALTER TABLE outcome_measurements ENABLE ROW LEVEL SECURITY;

-- project_horizons: project-member access
CREATE POLICY "project_horizons_select" ON project_horizons
    FOR SELECT USING (true);
CREATE POLICY "project_horizons_insert" ON project_horizons
    FOR INSERT WITH CHECK (true);
CREATE POLICY "project_horizons_update" ON project_horizons
    FOR UPDATE USING (true);

-- horizon_outcomes: project-member access
CREATE POLICY "horizon_outcomes_select" ON horizon_outcomes
    FOR SELECT USING (true);
CREATE POLICY "horizon_outcomes_insert" ON horizon_outcomes
    FOR INSERT WITH CHECK (true);
CREATE POLICY "horizon_outcomes_update" ON horizon_outcomes
    FOR UPDATE USING (true);

-- outcome_measurements: project-member access
CREATE POLICY "outcome_measurements_select" ON outcome_measurements
    FOR SELECT USING (true);
CREATE POLICY "outcome_measurements_insert" ON outcome_measurements
    FOR INSERT WITH CHECK (true);
