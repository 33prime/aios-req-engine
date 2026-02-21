-- Pulse Engine: snapshot history + versioned config
-- Phase 2 of Pulse Engine buildout

-- Pulse snapshots: immutable log of computed pulse states
CREATE TABLE pulse_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    stage TEXT NOT NULL,
    stage_progress FLOAT NOT NULL DEFAULT 0,
    health JSONB NOT NULL DEFAULT '{}',
    actions JSONB NOT NULL DEFAULT '[]',
    risks JSONB NOT NULL DEFAULT '{}',
    forecast JSONB NOT NULL DEFAULT '{}',
    extraction_directive JSONB NOT NULL DEFAULT '{}',
    config_version TEXT NOT NULL DEFAULT '1.0',
    rules_fired JSONB NOT NULL DEFAULT '[]',
    trigger TEXT NOT NULL DEFAULT 'manual',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_pulse_snapshots_project_created
    ON pulse_snapshots (project_id, created_at DESC);
CREATE INDEX idx_pulse_snapshots_stage
    ON pulse_snapshots (stage);

-- Pulse configs: versioned tuning knobs (NULL project_id = global default)
CREATE TABLE pulse_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    version TEXT NOT NULL,
    label TEXT NOT NULL DEFAULT '',
    config JSONB NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT false,
    created_by UUID REFERENCES profiles(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_pulse_configs_project
    ON pulse_configs (project_id);
CREATE UNIQUE INDEX idx_pulse_configs_active
    ON pulse_configs (project_id) WHERE is_active = true;

-- RLS policies
ALTER TABLE pulse_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE pulse_configs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "pulse_snapshots_all" ON pulse_snapshots
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "pulse_configs_all" ON pulse_configs
    FOR ALL USING (true) WITH CHECK (true);
