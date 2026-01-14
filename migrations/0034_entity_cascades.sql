-- Migration: Entity Relationship Cascades
-- Description: Add entity dependency graph, staleness tracking, and cascade infrastructure
-- Date: 2025-01-05

-- =============================================================================
-- 1. Expand VP Change Queue to Entity Change Queue
-- =============================================================================

-- Add new columns for expanded scope (keeping table name for backwards compatibility)
ALTER TABLE vp_change_queue
  ADD COLUMN IF NOT EXISTS target_entity_type TEXT,
  ADD COLUMN IF NOT EXISTS target_entity_ids UUID[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS cascade_type TEXT DEFAULT 'auto'
    CHECK (cascade_type IN ('auto', 'suggested', 'logged')),
  ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 0;

-- Update change_type constraint to include all entity changes
-- First drop the old constraint, then add new one
ALTER TABLE vp_change_queue DROP CONSTRAINT IF EXISTS vp_change_queue_change_type_check;

ALTER TABLE vp_change_queue ADD CONSTRAINT vp_change_queue_change_type_check
  CHECK (change_type IN (
    -- Existing types
    'feature_enriched',
    'feature_updated',
    'persona_enriched',
    'persona_updated',
    'signal_ingested',
    'evidence_attached',
    'research_confirmed',
    -- New types
    'vp_step_updated',
    'vp_step_created',
    'strategic_context_updated',
    'feature_priority_changed',
    'persona_goals_changed',
    'feature_created',
    'persona_created',
    'stakeholder_created',
    'stakeholder_updated'
  ));

-- Create index for priority processing
CREATE INDEX IF NOT EXISTS idx_entity_change_queue_priority
  ON vp_change_queue(project_id, processed, priority DESC, created_at);

-- =============================================================================
-- 2. Strategic Context Enhancements
-- =============================================================================

-- Add column to track which entities informed the strategic context
ALTER TABLE strategic_context
  ADD COLUMN IF NOT EXISTS source_entities JSONB DEFAULT '{}'::jsonb;
-- Format: {
--   personas: [{id, name, contribution}],
--   features: [{id, name, contribution}],
--   vp_steps: [{id, label, contribution}]
-- }

-- Add staleness tracking to strategic context
ALTER TABLE strategic_context
  ADD COLUMN IF NOT EXISTS is_stale BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS stale_reason TEXT,
  ADD COLUMN IF NOT EXISTS stale_since TIMESTAMPTZ;

-- =============================================================================
-- 3. Add Cascade Tracking to Existing Tables
-- =============================================================================

-- Features: track what made them stale
ALTER TABLE features
  ADD COLUMN IF NOT EXISTS is_stale BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS stale_reason TEXT,
  ADD COLUMN IF NOT EXISTS stale_since TIMESTAMPTZ;

-- Personas: track what made them stale
ALTER TABLE personas
  ADD COLUMN IF NOT EXISTS is_stale BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS stale_reason TEXT,
  ADD COLUMN IF NOT EXISTS stale_since TIMESTAMPTZ;

-- =============================================================================
-- 4. Entity Dependency Graph
-- =============================================================================

CREATE TABLE IF NOT EXISTS entity_dependencies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

  -- Source entity (the one that depends on target)
  source_entity_type TEXT NOT NULL
    CHECK (source_entity_type IN ('persona', 'feature', 'vp_step', 'strategic_context', 'stakeholder')),
  source_entity_id UUID NOT NULL,

  -- Target entity (the one being depended on)
  target_entity_type TEXT NOT NULL
    CHECK (target_entity_type IN ('persona', 'feature', 'vp_step', 'signal', 'research_chunk')),
  target_entity_id UUID NOT NULL,

  -- Dependency metadata
  dependency_type TEXT NOT NULL
    CHECK (dependency_type IN ('uses', 'targets', 'derived_from', 'informed_by', 'actor_of')),
  strength FLOAT DEFAULT 1.0 CHECK (strength >= 0 AND strength <= 1),

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE(project_id, source_entity_type, source_entity_id, target_entity_type, target_entity_id, dependency_type)
);

-- Indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_entity_deps_source
  ON entity_dependencies(project_id, source_entity_type, source_entity_id);

CREATE INDEX IF NOT EXISTS idx_entity_deps_target
  ON entity_dependencies(project_id, target_entity_type, target_entity_id);

CREATE INDEX IF NOT EXISTS idx_entity_deps_project
  ON entity_dependencies(project_id);

-- =============================================================================
-- 5. Trigger Functions for Automatic Staleness
-- =============================================================================

-- Function to mark dependent entities as stale when a source entity changes
CREATE OR REPLACE FUNCTION mark_dependents_stale()
RETURNS TRIGGER AS $$
DECLARE
  dep RECORD;
  entity_type_arg TEXT;
BEGIN
  entity_type_arg := TG_ARGV[0];

  -- Find all entities that depend on this one
  FOR dep IN
    SELECT source_entity_type, source_entity_id
    FROM entity_dependencies
    WHERE project_id = NEW.project_id
      AND target_entity_type = entity_type_arg
      AND target_entity_id = NEW.id
  LOOP
    -- Mark each dependent entity as stale based on its type
    CASE dep.source_entity_type
      WHEN 'feature' THEN
        UPDATE features
        SET is_stale = TRUE,
            stale_reason = entity_type_arg || ' updated',
            stale_since = now()
        WHERE id = dep.source_entity_id
          AND (is_stale IS NULL OR is_stale = FALSE);

      WHEN 'persona' THEN
        UPDATE personas
        SET is_stale = TRUE,
            stale_reason = entity_type_arg || ' updated',
            stale_since = now()
        WHERE id = dep.source_entity_id
          AND (is_stale IS NULL OR is_stale = FALSE);

      WHEN 'vp_step' THEN
        UPDATE vp_steps
        SET is_stale = TRUE,
            stale_reason = entity_type_arg || ' updated',
            stale_since = now()
        WHERE id = dep.source_entity_id
          AND (is_stale IS NULL OR is_stale = FALSE);

      WHEN 'strategic_context' THEN
        UPDATE strategic_context
        SET is_stale = TRUE,
            stale_reason = entity_type_arg || ' updated',
            stale_since = now()
        WHERE id = dep.source_entity_id
          AND (is_stale IS NULL OR is_stale = FALSE);

      ELSE
        -- Unknown type, skip
        NULL;
    END CASE;
  END LOOP;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 6. Create Triggers (with drop-if-exists for idempotency)
-- =============================================================================

-- Drop existing triggers if they exist
DROP TRIGGER IF EXISTS features_cascade_staleness ON features;
DROP TRIGGER IF EXISTS personas_cascade_staleness ON personas;
DROP TRIGGER IF EXISTS vp_steps_cascade_staleness ON vp_steps;

-- Trigger on features update (only on columns that exist from base table)
-- Using name only since other enrichment columns may not exist yet
DO $$
BEGIN
  -- Check if overview column exists (added by enrichment migration)
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'features' AND column_name = 'overview'
  ) THEN
    CREATE TRIGGER features_cascade_staleness
      AFTER UPDATE OF name, overview, target_personas, user_actions,
                      system_behaviors, rules, integrations
      ON features
      FOR EACH ROW
      WHEN (OLD.* IS DISTINCT FROM NEW.*)
      EXECUTE FUNCTION mark_dependents_stale('feature');
  ELSE
    -- Fallback: just trigger on name changes
    CREATE TRIGGER features_cascade_staleness
      AFTER UPDATE OF name
      ON features
      FOR EACH ROW
      WHEN (OLD.* IS DISTINCT FROM NEW.*)
      EXECUTE FUNCTION mark_dependents_stale('feature');
  END IF;
END $$;

-- Trigger on personas update
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'personas' AND column_name = 'overview'
  ) THEN
    CREATE TRIGGER personas_cascade_staleness
      AFTER UPDATE OF name, role, goals, pain_points, overview, key_workflows
      ON personas
      FOR EACH ROW
      WHEN (OLD.* IS DISTINCT FROM NEW.*)
      EXECUTE FUNCTION mark_dependents_stale('persona');
  ELSE
    CREATE TRIGGER personas_cascade_staleness
      AFTER UPDATE OF name, role, goals, pain_points
      ON personas
      FOR EACH ROW
      WHEN (OLD.* IS DISTINCT FROM NEW.*)
      EXECUTE FUNCTION mark_dependents_stale('persona');
  END IF;
END $$;

-- Trigger on vp_steps update
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'vp_steps' AND column_name = 'narrative_user'
  ) THEN
    CREATE TRIGGER vp_steps_cascade_staleness
      AFTER UPDATE OF label, description, narrative_user, narrative_system,
                      features_used, value_created
      ON vp_steps
      FOR EACH ROW
      WHEN (OLD.* IS DISTINCT FROM NEW.*)
      EXECUTE FUNCTION mark_dependents_stale('vp_step');
  ELSE
    CREATE TRIGGER vp_steps_cascade_staleness
      AFTER UPDATE OF label, description, value_created
      ON vp_steps
      FOR EACH ROW
      WHEN (OLD.* IS DISTINCT FROM NEW.*)
      EXECUTE FUNCTION mark_dependents_stale('vp_step');
  END IF;
END $$;

-- =============================================================================
-- 7. Function to Queue Entity Change
-- =============================================================================

CREATE OR REPLACE FUNCTION queue_entity_change(
  p_project_id UUID,
  p_change_type TEXT,
  p_entity_type TEXT,
  p_entity_id UUID,
  p_entity_name TEXT DEFAULT NULL,
  p_change_details JSONB DEFAULT '{}'::jsonb,
  p_target_entity_type TEXT DEFAULT NULL,
  p_target_entity_ids UUID[] DEFAULT '{}',
  p_cascade_type TEXT DEFAULT 'auto',
  p_priority INTEGER DEFAULT 0
) RETURNS UUID AS $$
DECLARE
  queue_id UUID;
BEGIN
  INSERT INTO vp_change_queue (
    project_id,
    change_type,
    entity_type,
    entity_id,
    entity_name,
    change_details,
    target_entity_type,
    target_entity_ids,
    cascade_type,
    priority
  ) VALUES (
    p_project_id,
    p_change_type,
    p_entity_type,
    p_entity_id,
    p_entity_name,
    p_change_details,
    p_target_entity_type,
    p_target_entity_ids,
    p_cascade_type,
    p_priority
  ) RETURNING id INTO queue_id;

  RETURN queue_id;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 8. Function to Clear Staleness
-- =============================================================================

CREATE OR REPLACE FUNCTION clear_entity_staleness(
  p_entity_type TEXT,
  p_entity_id UUID
) RETURNS BOOLEAN AS $$
BEGIN
  CASE p_entity_type
    WHEN 'feature' THEN
      UPDATE features
      SET is_stale = FALSE, stale_reason = NULL, stale_since = NULL
      WHERE id = p_entity_id;

    WHEN 'persona' THEN
      UPDATE personas
      SET is_stale = FALSE, stale_reason = NULL, stale_since = NULL
      WHERE id = p_entity_id;

    WHEN 'vp_step' THEN
      UPDATE vp_steps
      SET is_stale = FALSE, stale_reason = NULL, stale_since = NULL
      WHERE id = p_entity_id;

    WHEN 'strategic_context' THEN
      UPDATE strategic_context
      SET is_stale = FALSE, stale_reason = NULL, stale_since = NULL
      WHERE id = p_entity_id;

    ELSE
      RETURN FALSE;
  END CASE;

  RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 9. Comments
-- =============================================================================

COMMENT ON TABLE entity_dependencies IS
  'Graph of dependencies between entities - source depends on target';

COMMENT ON COLUMN entity_dependencies.source_entity_type IS
  'Entity type that has the dependency (would be affected if target changes)';

COMMENT ON COLUMN entity_dependencies.target_entity_type IS
  'Entity type being depended on (if this changes, source may become stale)';

COMMENT ON COLUMN entity_dependencies.dependency_type IS
  'Nature of dependency: uses (feature in step), targets (feature for persona), derived_from (evidence), informed_by (context), actor_of (persona acts in step)';

COMMENT ON COLUMN entity_dependencies.strength IS
  'Strength of dependency 0-1, where 1 means critical dependency';

COMMENT ON COLUMN vp_change_queue.cascade_type IS
  'How to handle: auto (process immediately), suggested (prompt user), logged (record only)';

COMMENT ON COLUMN vp_change_queue.priority IS
  'Processing priority (higher = process first)';

COMMENT ON FUNCTION mark_dependents_stale() IS
  'Trigger function that marks all dependent entities as stale when a source entity changes';

COMMENT ON FUNCTION queue_entity_change IS
  'Helper function to queue an entity change for cascade processing';

COMMENT ON FUNCTION clear_entity_staleness IS
  'Clear staleness flag from an entity (typically after regeneration)';
