-- Migration: Phase 0 Consolidated
-- Description: All Phase 0 features in correct dependency order
-- Date: 2025-12-25
-- Replaces: 0016, 0017, 0018, 0019 (use this if those failed)

-- =========================
-- 1. Create projects table (if needed)
-- =========================
CREATE TABLE IF NOT EXISTS projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =========================
-- 2. Add confirmation status to existing tables
-- =========================

-- Features
ALTER TABLE features
ADD COLUMN IF NOT EXISTS confirmation_status TEXT DEFAULT 'ai_generated'
  CHECK (confirmation_status IN ('ai_generated', 'confirmed_consultant', 'needs_client', 'confirmed_client')),
ADD COLUMN IF NOT EXISTS confirmed_by UUID,
ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_features_confirmation_status
  ON features(project_id, confirmation_status);

-- VP Steps
ALTER TABLE vp_steps
ADD COLUMN IF NOT EXISTS confirmation_status TEXT DEFAULT 'ai_generated'
  CHECK (confirmation_status IN ('ai_generated', 'confirmed_consultant', 'needs_client', 'confirmed_client')),
ADD COLUMN IF NOT EXISTS confirmed_by UUID,
ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS sort_order NUMERIC;

UPDATE vp_steps SET sort_order = step_index * 10 WHERE sort_order IS NULL;

CREATE INDEX IF NOT EXISTS idx_vp_steps_confirmation_status
  ON vp_steps(project_id, confirmation_status);

CREATE INDEX IF NOT EXISTS idx_vp_steps_sort_order
  ON vp_steps(project_id, sort_order);

-- PRD Sections
ALTER TABLE prd_sections
ADD COLUMN IF NOT EXISTS confirmation_status TEXT DEFAULT 'ai_generated'
  CHECK (confirmation_status IN ('ai_generated', 'confirmed_consultant', 'needs_client', 'confirmed_client')),
ADD COLUMN IF NOT EXISTS confirmed_by UUID,
ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_prd_sections_confirmation_status
  ON prd_sections(project_id, confirmation_status);

-- =========================
-- 3. Create personas table
-- =========================
CREATE TABLE IF NOT EXISTS personas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL,
  slug TEXT NOT NULL,
  name TEXT NOT NULL,
  role TEXT,
  demographics JSONB DEFAULT '{}'::jsonb,
  psychographics JSONB DEFAULT '{}'::jsonb,
  goals TEXT[] DEFAULT ARRAY[]::TEXT[],
  pain_points TEXT[] DEFAULT ARRAY[]::TEXT[],
  description TEXT,
  related_features UUID[] DEFAULT ARRAY[]::UUID[],
  related_vp_steps UUID[] DEFAULT ARRAY[]::UUID[],
  confirmation_status TEXT DEFAULT 'ai_generated'
    CHECK (confirmation_status IN ('ai_generated', 'confirmed_consultant', 'needs_client', 'confirmed_client')),
  confirmed_by UUID,
  confirmed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(project_id, slug)
);

CREATE INDEX IF NOT EXISTS idx_personas_project ON personas(project_id);
CREATE INDEX IF NOT EXISTS idx_personas_confirmation_status ON personas(project_id, confirmation_status);

-- =========================
-- 4. Add evidence enrichment to signals
-- =========================
ALTER TABLE signals
ADD COLUMN IF NOT EXISTS source_type TEXT,
ADD COLUMN IF NOT EXISTS source_label TEXT,
ADD COLUMN IF NOT EXISTS source_timestamp TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS source_metadata JSONB DEFAULT '{}'::jsonb;

UPDATE signals
SET source_type = CASE
  WHEN signal_type IN ('email', 'transcript', 'note') THEN signal_type
  WHEN signal_type = 'file_text' THEN 'doc'
  ELSE 'note'
END
WHERE source_type IS NULL;

CREATE INDEX IF NOT EXISTS idx_signals_source_type ON signals(project_id, source_type);

-- =========================
-- 5. Add PRD mode tracking to projects
-- =========================
ALTER TABLE projects
ADD COLUMN IF NOT EXISTS prd_mode TEXT DEFAULT 'initial'
  CHECK (prd_mode IN ('initial', 'maintenance')),
ADD COLUMN IF NOT EXISTS baseline_finalized_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS baseline_finalized_by UUID,
ADD COLUMN IF NOT EXISTS baseline_completeness_score NUMERIC
  CHECK (baseline_completeness_score >= 0 AND baseline_completeness_score <= 1);

CREATE INDEX IF NOT EXISTS idx_projects_prd_mode ON projects(prd_mode);

UPDATE projects SET prd_mode = 'initial' WHERE prd_mode IS NULL;

-- =========================
-- Helper function
-- =========================
CREATE OR REPLACE FUNCTION is_baseline_ready(project_uuid UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
AS $$
  SELECT COALESCE(baseline_completeness_score, 0) >= 0.75
  FROM projects
  WHERE id = project_uuid;
$$;
