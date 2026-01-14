-- Migration: Value Path v2
-- Description: Add structured enrichment columns for auto-generated VP with surgical updates
-- Date: 2025-01-05

-- =========================
-- VP Steps: Add v2 columns
-- =========================

-- Actor persona for this step
ALTER TABLE vp_steps
ADD COLUMN IF NOT EXISTS actor_persona_id UUID REFERENCES personas(id);

ALTER TABLE vp_steps
ADD COLUMN IF NOT EXISTS actor_persona_name TEXT;

-- Features used in this step
-- Format: [{feature_id, feature_name, role: 'core'|'supporting'}]
ALTER TABLE vp_steps
ADD COLUMN IF NOT EXISTS features_used JSONB DEFAULT '[]'::jsonb;

-- User-facing narrative (what the user experiences)
ALTER TABLE vp_steps
ADD COLUMN IF NOT EXISTS narrative_user TEXT;

-- System narrative (what happens behind the scenes)
ALTER TABLE vp_steps
ADD COLUMN IF NOT EXISTS narrative_system TEXT;

-- Business rules applied during this step (aggregated from features)
ALTER TABLE vp_steps
ADD COLUMN IF NOT EXISTS rules_applied JSONB DEFAULT '[]'::jsonb;

-- External integrations triggered (aggregated from features)
ALTER TABLE vp_steps
ADD COLUMN IF NOT EXISTS integrations_triggered JSONB DEFAULT '[]'::jsonb;

-- Key UI elements for this step (from features' ui_requirements)
ALTER TABLE vp_steps
ADD COLUMN IF NOT EXISTS ui_highlights JSONB DEFAULT '[]'::jsonb;

-- Generation tracking
ALTER TABLE vp_steps
ADD COLUMN IF NOT EXISTS generation_status TEXT DEFAULT 'none'
  CHECK (generation_status IN ('none', 'generated', 'stale'));

ALTER TABLE vp_steps
ADD COLUMN IF NOT EXISTS generated_at TIMESTAMPTZ;

-- Staleness tracking
ALTER TABLE vp_steps
ADD COLUMN IF NOT EXISTS is_stale BOOLEAN DEFAULT false;

ALTER TABLE vp_steps
ADD COLUMN IF NOT EXISTS stale_reason TEXT;

-- Consultant edit protection
ALTER TABLE vp_steps
ADD COLUMN IF NOT EXISTS consultant_edited BOOLEAN DEFAULT false;

ALTER TABLE vp_steps
ADD COLUMN IF NOT EXISTS consultant_edited_at TIMESTAMPTZ;

-- Confirmation status (matches features/personas pattern)
-- Note: vp_steps may already have a 'status' column, this adds explicit confirmation
ALTER TABLE vp_steps
ADD COLUMN IF NOT EXISTS confirmation_status TEXT DEFAULT 'ai_generated'
  CHECK (confirmation_status IN ('ai_generated', 'confirmed_consultant', 'confirmed_client', 'needs_client'));

ALTER TABLE vp_steps
ADD COLUMN IF NOT EXISTS has_signal_evidence BOOLEAN DEFAULT false;
-- If true and confirmation_status is ai_generated, auto-promote to confirmed

-- =========================
-- VP Change Queue: Track changes for surgical updates
-- =========================

CREATE TABLE IF NOT EXISTS vp_change_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  change_type TEXT NOT NULL CHECK (change_type IN (
    'feature_enriched',
    'feature_updated',
    'persona_enriched',
    'persona_updated',
    'signal_ingested',
    'evidence_attached',
    'research_confirmed'
  )),
  entity_type TEXT NOT NULL CHECK (entity_type IN ('feature', 'persona', 'signal', 'evidence')),
  entity_id UUID NOT NULL,
  entity_name TEXT,
  change_details JSONB DEFAULT '{}'::jsonb,
  affected_step_ids UUID[] DEFAULT '{}',
  processed BOOLEAN DEFAULT false,
  processed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Index for finding unprocessed changes
CREATE INDEX IF NOT EXISTS idx_vp_change_queue_unprocessed
ON vp_change_queue(project_id, processed, created_at)
WHERE processed = false;

-- Index for finding changes by entity
CREATE INDEX IF NOT EXISTS idx_vp_change_queue_entity
ON vp_change_queue(entity_type, entity_id);

-- =========================
-- VP Generation Log: Track full regenerations
-- =========================

CREATE TABLE IF NOT EXISTS vp_generation_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  generation_type TEXT NOT NULL CHECK (generation_type IN ('full', 'surgical')),
  steps_created INT DEFAULT 0,
  steps_updated INT DEFAULT 0,
  steps_preserved INT DEFAULT 0,
  input_features_count INT DEFAULT 0,
  input_personas_count INT DEFAULT 0,
  impact_ratio DECIMAL(5,4), -- For surgical: % of steps affected
  trigger_reason TEXT, -- What triggered this generation
  model_used TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ,
  error TEXT
);

-- =========================
-- Indexes for VP steps
-- =========================

CREATE INDEX IF NOT EXISTS idx_vp_steps_generation_status
ON vp_steps(project_id, generation_status);

CREATE INDEX IF NOT EXISTS idx_vp_steps_stale
ON vp_steps(project_id, is_stale)
WHERE is_stale = true;

CREATE INDEX IF NOT EXISTS idx_vp_steps_actor_persona
ON vp_steps(actor_persona_id);

-- =========================
-- Comments
-- =========================

COMMENT ON COLUMN vp_steps.actor_persona_id IS
  'Primary persona who is the actor in this step';

COMMENT ON COLUMN vp_steps.features_used IS
  'Features involved in this step: [{feature_id, feature_name, role}]';

COMMENT ON COLUMN vp_steps.narrative_user IS
  'User-facing narrative describing what happens from the user perspective';

COMMENT ON COLUMN vp_steps.narrative_system IS
  'Behind-the-scenes narrative describing system behaviors';

COMMENT ON COLUMN vp_steps.rules_applied IS
  'Business rules active during this step (aggregated from features)';

COMMENT ON COLUMN vp_steps.integrations_triggered IS
  'External integrations used in this step (aggregated from features)';

COMMENT ON COLUMN vp_steps.ui_highlights IS
  'Key UI elements shown during this step';

COMMENT ON COLUMN vp_steps.generation_status IS
  'Generation state: none (manual), generated (auto), stale (needs update)';

COMMENT ON COLUMN vp_steps.consultant_edited IS
  'If true, preserve this step content during regeneration';

COMMENT ON COLUMN vp_steps.has_signal_evidence IS
  'If true, step has evidence from client signals (auto-confirms)';

COMMENT ON TABLE vp_change_queue IS
  'Queue of changes that may affect VP steps, for surgical update processing';

COMMENT ON TABLE vp_generation_log IS
  'Log of VP generation runs for tracking and debugging';
