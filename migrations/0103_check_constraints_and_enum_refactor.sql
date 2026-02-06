-- Migration: 0103_check_constraints_and_enum_refactor.sql
-- Description: Convert Postgres ENUM types to text+CHECK and add missing CHECK constraints
-- Date: 2026-02-06
--
-- Postgres ENUM types are hard to modify (can't remove values, ALTER TYPE needed to add).
-- Text columns with CHECK constraints are easier to migrate and equally performant.
--
-- Strategy: ALTER COLUMN TYPE text converts enum values to their text representation,
-- then DROP TYPE removes the enum, then ADD CONSTRAINT adds the CHECK.

-- ============================================================================
-- Part 1: Convert ENUM types to text + CHECK
-- ============================================================================

-- --- meetings table (0057) ---

-- meeting_type_enum → text
ALTER TABLE meetings ALTER COLUMN meeting_type TYPE text;
DROP TYPE IF EXISTS meeting_type_enum;
ALTER TABLE meetings ADD CONSTRAINT meetings_meeting_type_check
  CHECK (meeting_type IN ('discovery', 'validation', 'review', 'other'));

-- meeting_status_enum → text
ALTER TABLE meetings ALTER COLUMN status TYPE text;
DROP TYPE IF EXISTS meeting_status_enum;
-- Note: meetings.status already has idx_meetings_status index
ALTER TABLE meetings ADD CONSTRAINT meetings_status_check
  CHECK (status IN ('scheduled', 'completed', 'cancelled'));

-- --- collaboration_touchpoints table (0081) ---

-- touchpoint_type enum → text
ALTER TABLE collaboration_touchpoints ALTER COLUMN type TYPE text;
DROP TYPE IF EXISTS touchpoint_type;
ALTER TABLE collaboration_touchpoints ADD CONSTRAINT collab_touchpoints_type_check
  CHECK (type IN (
    'discovery_call', 'validation_round', 'follow_up_call',
    'prototype_review', 'feedback_session'
  ));

-- touchpoint_status enum → text
ALTER TABLE collaboration_touchpoints ALTER COLUMN status TYPE text;
DROP TYPE IF EXISTS touchpoint_status;
ALTER TABLE collaboration_touchpoints ADD CONSTRAINT collab_touchpoints_status_check
  CHECK (status IN (
    'preparing', 'ready', 'sent', 'in_progress', 'completed', 'cancelled'
  ));

-- --- pending_items table (0082) ---

-- pending_item_type enum → text
ALTER TABLE pending_items ALTER COLUMN item_type TYPE text;
DROP TYPE IF EXISTS pending_item_type;
ALTER TABLE pending_items ADD CONSTRAINT pending_items_item_type_check
  CHECK (item_type IN (
    'feature', 'persona', 'vp_step', 'question', 'document',
    'kpi', 'goal', 'pain_point', 'requirement'
  ));

-- pending_item_source enum → text
ALTER TABLE pending_items ALTER COLUMN source TYPE text;
DROP TYPE IF EXISTS pending_item_source;
ALTER TABLE pending_items ADD CONSTRAINT pending_items_source_check
  CHECK (source IN ('phase_workflow', 'needs_review', 'ai_generated', 'manual'));

-- --- client_packages table (0082) ---

-- package_status enum → text
ALTER TABLE client_packages ALTER COLUMN status TYPE text;
DROP TYPE IF EXISTS package_status;
ALTER TABLE client_packages ADD CONSTRAINT client_packages_status_check
  CHECK (status IN ('draft', 'ready', 'sent', 'partial_response', 'complete'));

-- ============================================================================
-- Part 2: Add missing CHECK constraints on status-like columns
-- ============================================================================

-- prototypes.status (0095) — no CHECK exists
-- Use NOT VALID to avoid scanning existing rows, then validate separately
ALTER TABLE prototypes ADD CONSTRAINT prototypes_status_check
  CHECK (status IN ('pending', 'generating', 'ready', 'failed', 'active'))
  NOT VALID;
ALTER TABLE prototypes VALIDATE CONSTRAINT prototypes_status_check;

-- projects.collaboration_phase (0081) — no CHECK exists
ALTER TABLE projects ADD CONSTRAINT projects_collaboration_phase_check
  CHECK (collaboration_phase IN (
    'pre_discovery', 'discovery', 'validation', 'prototype', 'iteration'
  ))
  NOT VALID;
ALTER TABLE projects VALIDATE CONSTRAINT projects_collaboration_phase_check;
