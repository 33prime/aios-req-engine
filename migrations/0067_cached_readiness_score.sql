-- Migration: 0067_cached_readiness_score.sql
-- Description: Add cached readiness score to projects for fast list queries
-- Date: 2026-01-15

-- Add cached readiness score column
ALTER TABLE projects ADD COLUMN IF NOT EXISTS cached_readiness_score NUMERIC
  CHECK (cached_readiness_score >= 0 AND cached_readiness_score <= 1);

-- Add last_readiness_calc timestamp to track when score was calculated
ALTER TABLE projects ADD COLUMN IF NOT EXISTS readiness_calculated_at TIMESTAMPTZ;

-- Index for sorting by readiness score
CREATE INDEX IF NOT EXISTS idx_projects_readiness_score ON projects(cached_readiness_score) WHERE cached_readiness_score IS NOT NULL;
