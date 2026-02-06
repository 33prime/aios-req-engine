-- Migration: 0103_check_constraints_and_enum_refactor.sql
-- Description: Convert Postgres ENUM types to text+CHECK and add missing CHECK constraints
-- Date: 2026-02-06
--
-- Postgres ENUM types are hard to modify (can't remove values, ALTER TYPE needed to add).
-- Text columns with CHECK constraints are easier to migrate and equally performant.
--
-- Strategy: Drop defaults and dependent objects (partial indexes, RLS policies),
-- ALTER COLUMN TYPE text, re-add defaults, DROP TYPE, ADD CONSTRAINT, recreate dependents.

-- ============================================================================
-- Part 1a: meetings ENUM → text
-- ============================================================================

-- Drop partial index that references enum in WHERE clause
DROP INDEX IF EXISTS idx_meetings_upcoming;

ALTER TABLE meetings ALTER COLUMN meeting_type DROP DEFAULT;
ALTER TABLE meetings ALTER COLUMN meeting_type TYPE text;
ALTER TABLE meetings ALTER COLUMN meeting_type SET DEFAULT 'other';
DROP TYPE IF EXISTS meeting_type_enum;
ALTER TABLE meetings ADD CONSTRAINT meetings_meeting_type_check
  CHECK (meeting_type IN ('discovery', 'validation', 'review', 'other'));

ALTER TABLE meetings ALTER COLUMN status DROP DEFAULT;
ALTER TABLE meetings ALTER COLUMN status TYPE text;
ALTER TABLE meetings ALTER COLUMN status SET DEFAULT 'scheduled';
DROP TYPE IF EXISTS meeting_status_enum;
ALTER TABLE meetings ADD CONSTRAINT meetings_status_check
  CHECK (status IN ('scheduled', 'completed', 'cancelled'));

-- Recreate partial index with text comparison
CREATE INDEX IF NOT EXISTS idx_meetings_upcoming
  ON meetings(meeting_date, meeting_time) WHERE status = 'scheduled';

-- ============================================================================
-- Part 1b: collaboration_touchpoints ENUM → text
-- ============================================================================

ALTER TABLE collaboration_touchpoints ALTER COLUMN type TYPE text;
DROP TYPE IF EXISTS touchpoint_type;
ALTER TABLE collaboration_touchpoints ADD CONSTRAINT collab_touchpoints_type_check
  CHECK (type IN (
    'discovery_call', 'validation_round', 'follow_up_call',
    'prototype_review', 'feedback_session'
  ));

ALTER TABLE collaboration_touchpoints ALTER COLUMN status DROP DEFAULT;
ALTER TABLE collaboration_touchpoints ALTER COLUMN status TYPE text;
ALTER TABLE collaboration_touchpoints ALTER COLUMN status SET DEFAULT 'preparing';
DROP TYPE IF EXISTS touchpoint_status;
ALTER TABLE collaboration_touchpoints ADD CONSTRAINT collab_touchpoints_status_check
  CHECK (status IN (
    'preparing', 'ready', 'sent', 'in_progress', 'completed', 'cancelled'
  ));

-- ============================================================================
-- Part 1c: pending_items ENUM → text
-- ============================================================================

ALTER TABLE pending_items ALTER COLUMN item_type TYPE text;
DROP TYPE IF EXISTS pending_item_type;
ALTER TABLE pending_items ADD CONSTRAINT pending_items_item_type_check
  CHECK (item_type IN (
    'feature', 'persona', 'vp_step', 'question', 'document',
    'kpi', 'goal', 'pain_point', 'requirement'
  ));

ALTER TABLE pending_items ALTER COLUMN source DROP DEFAULT;
ALTER TABLE pending_items ALTER COLUMN source TYPE text;
ALTER TABLE pending_items ALTER COLUMN source SET DEFAULT 'manual';
DROP TYPE IF EXISTS pending_item_source;
ALTER TABLE pending_items ADD CONSTRAINT pending_items_source_check
  CHECK (source IN ('phase_workflow', 'needs_review', 'ai_generated', 'manual'));

-- ============================================================================
-- Part 1d: client_packages ENUM → text
-- Must drop 7 RLS policies across 5 tables that cast to package_status enum
-- ============================================================================

DROP POLICY IF EXISTS "Clients can view sent packages" ON client_packages;
DROP POLICY IF EXISTS "Clients can view action items in sent packages" ON package_action_items;
DROP POLICY IF EXISTS "Clients can complete action items" ON package_action_items;
DROP POLICY IF EXISTS "Clients can view asset suggestions" ON package_asset_suggestions;
DROP POLICY IF EXISTS "Clients can view questions in sent packages" ON package_questions;
DROP POLICY IF EXISTS "Clients can answer questions" ON package_questions;
DROP POLICY IF EXISTS "Clients can upload files" ON package_uploaded_files;

ALTER TABLE client_packages ALTER COLUMN status DROP DEFAULT;
ALTER TABLE client_packages ALTER COLUMN status TYPE text;
ALTER TABLE client_packages ALTER COLUMN status SET DEFAULT 'draft';
DROP TYPE IF EXISTS package_status;
ALTER TABLE client_packages ADD CONSTRAINT client_packages_status_check
  CHECK (status IN ('draft', 'ready', 'sent', 'partial_response', 'complete'));

-- Recreate all 7 policies with text comparisons (no enum casts)

CREATE POLICY "Clients can view sent packages" ON client_packages FOR SELECT TO authenticated
  USING (
    status IN ('sent', 'partial_response', 'complete')
    AND project_id IN (
      SELECT project_id FROM project_members
      WHERE user_id = (SELECT auth.uid()) AND role = 'client'
    )
  );

CREATE POLICY "Clients can view action items in sent packages" ON package_action_items FOR SELECT TO authenticated
  USING (package_id IN (
    SELECT cp.id FROM client_packages cp
    JOIN project_members pm ON pm.project_id = cp.project_id
    WHERE pm.user_id = (SELECT auth.uid()) AND pm.role = 'client'
      AND cp.status IN ('sent', 'partial_response', 'complete')
  ));

CREATE POLICY "Clients can complete action items" ON package_action_items FOR UPDATE TO authenticated
  USING (package_id IN (
    SELECT cp.id FROM client_packages cp
    JOIN project_members pm ON pm.project_id = cp.project_id
    WHERE pm.user_id = (SELECT auth.uid()) AND pm.role = 'client'
      AND cp.status IN ('sent', 'partial_response')
  ));

CREATE POLICY "Clients can view asset suggestions" ON package_asset_suggestions FOR SELECT TO authenticated
  USING (package_id IN (
    SELECT cp.id FROM client_packages cp
    JOIN project_members pm ON pm.project_id = cp.project_id
    WHERE pm.user_id = (SELECT auth.uid()) AND pm.role = 'client'
      AND cp.status IN ('sent', 'partial_response', 'complete')
  ));

CREATE POLICY "Clients can view questions in sent packages" ON package_questions FOR SELECT TO authenticated
  USING (package_id IN (
    SELECT cp.id FROM client_packages cp
    JOIN project_members pm ON pm.project_id = cp.project_id
    WHERE pm.user_id = (SELECT auth.uid()) AND pm.role = 'client'
      AND cp.status IN ('sent', 'partial_response', 'complete')
  ));

CREATE POLICY "Clients can answer questions" ON package_questions FOR UPDATE TO authenticated
  USING (package_id IN (
    SELECT cp.id FROM client_packages cp
    JOIN project_members pm ON pm.project_id = cp.project_id
    WHERE pm.user_id = (SELECT auth.uid()) AND pm.role = 'client'
      AND cp.status IN ('sent', 'partial_response')
  ));

CREATE POLICY "Clients can upload files" ON package_uploaded_files FOR INSERT TO authenticated
  WITH CHECK (package_id IN (
    SELECT cp.id FROM client_packages cp
    JOIN project_members pm ON pm.project_id = cp.project_id
    WHERE pm.user_id = (SELECT auth.uid()) AND pm.role = 'client'
      AND cp.status IN ('sent', 'partial_response')
  ));

-- ============================================================================
-- Part 2: Add missing CHECK constraints on status-like columns
-- ============================================================================

-- prototypes.status — includes 'analyzed' found in production data
ALTER TABLE prototypes ADD CONSTRAINT prototypes_status_check
  CHECK (status IN ('pending', 'generating', 'ready', 'failed', 'active', 'analyzed'))
  NOT VALID;
ALTER TABLE prototypes VALIDATE CONSTRAINT prototypes_status_check;

-- projects.collaboration_phase
ALTER TABLE projects ADD CONSTRAINT projects_collaboration_phase_check
  CHECK (collaboration_phase IN (
    'pre_discovery', 'discovery', 'validation', 'prototype', 'iteration'
  ))
  NOT VALID;
ALTER TABLE projects VALIDATE CONSTRAINT projects_collaboration_phase_check;
