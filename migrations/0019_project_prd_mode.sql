-- Migration: Project PRD Mode Tracking
-- Description: Add mode tracking for hybrid initial/maintenance pipeline
-- Date: 2025-12-25
-- Phase: 0 - Foundation

-- =========================
-- Create projects table if it doesn't exist
-- =========================
-- Note: Projects table may already exist in Supabase schema
-- This migration ensures required columns exist

CREATE TABLE IF NOT EXISTS projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =========================
-- Add PRD mode tracking columns
-- =========================
ALTER TABLE projects
ADD COLUMN IF NOT EXISTS prd_mode TEXT DEFAULT 'initial'
  CHECK (prd_mode IN ('initial', 'maintenance')),
ADD COLUMN IF NOT EXISTS baseline_finalized_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS baseline_finalized_by UUID,  -- References users(id) if user table exists
ADD COLUMN IF NOT EXISTS baseline_completeness_score NUMERIC CHECK (baseline_completeness_score >= 0 AND baseline_completeness_score <= 1);

-- Index for filtering by mode
CREATE INDEX IF NOT EXISTS idx_projects_prd_mode
  ON projects(prd_mode);

-- Index for baseline finalization
CREATE INDEX IF NOT EXISTS idx_projects_baseline_finalized
  ON projects(baseline_finalized_at DESC NULLS LAST);

-- =========================
-- Trigger for updated_at (if function exists)
-- =========================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'update_updated_at_column') THEN
    DROP TRIGGER IF EXISTS trg_projects_updated_at ON projects;
    CREATE TRIGGER trg_projects_updated_at
      BEFORE UPDATE ON projects
      FOR EACH ROW
      EXECUTE FUNCTION update_updated_at_column();
  END IF;
END $$;

-- =========================
-- Comments
-- =========================
COMMENT ON COLUMN projects.prd_mode IS
  'PRD pipeline mode: initial (generative build_state) → maintenance (surgical updates)';

COMMENT ON COLUMN projects.baseline_finalized_at IS
  'Timestamp when consultant finalized the baseline and switched to maintenance mode';

COMMENT ON COLUMN projects.baseline_finalized_by IS
  'User UUID who finalized the baseline';

COMMENT ON COLUMN projects.baseline_completeness_score IS
  'Completeness score (0-1) when baseline was finalized, or current score if not finalized';

-- =========================
-- Helper function to check if project is ready for maintenance mode
-- =========================
CREATE OR REPLACE FUNCTION is_baseline_ready(project_uuid UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
AS $$
  SELECT
    COALESCE(baseline_completeness_score, 0) >= 0.75
  FROM projects
  WHERE id = project_uuid;
$$;

COMMENT ON FUNCTION is_baseline_ready IS
  'Check if project baseline completeness score is >= 75% (ready to finalize)';

-- =========================
-- Backfill existing projects to initial mode
-- =========================
UPDATE projects
SET prd_mode = 'initial'
WHERE prd_mode IS NULL;
