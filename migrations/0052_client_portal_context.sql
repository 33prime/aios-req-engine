-- Migration: 0052_client_portal_context.sql
-- Description: Project context - living knowledge base for client portal
-- Date: 2026-01-12

-- Project context (living knowledge base - one per project)
CREATE TABLE IF NOT EXISTS project_context (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL UNIQUE REFERENCES projects(id) ON DELETE CASCADE,

  -- The Problem section
  problem_main TEXT,
  problem_main_source TEXT CHECK (problem_main_source IN ('call', 'dashboard', 'chat', 'manual')),
  problem_main_locked BOOLEAN DEFAULT FALSE,

  problem_why_now TEXT,
  problem_why_now_source TEXT CHECK (problem_why_now_source IN ('call', 'dashboard', 'chat', 'manual')),
  problem_why_now_locked BOOLEAN DEFAULT FALSE,

  -- Metrics: [{metric, current, goal, source, locked}]
  metrics JSONB DEFAULT '[]',

  -- Success section
  success_future TEXT,
  success_future_source TEXT CHECK (success_future_source IN ('call', 'dashboard', 'chat', 'manual')),
  success_future_locked BOOLEAN DEFAULT FALSE,

  success_wow TEXT,
  success_wow_source TEXT CHECK (success_wow_source IN ('call', 'dashboard', 'chat', 'manual')),
  success_wow_locked BOOLEAN DEFAULT FALSE,

  -- Key Users: [{name, role, frustrations[], helps[], source, locked}]
  key_users JSONB DEFAULT '[]',

  -- Design section
  -- design_love: [{name, url, what_like, source}]
  design_love JSONB DEFAULT '[]',
  design_avoid TEXT,
  design_avoid_source TEXT CHECK (design_avoid_source IN ('call', 'dashboard', 'chat', 'manual')),
  design_avoid_locked BOOLEAN DEFAULT FALSE,

  -- Competitors: [{name, worked, didnt_work, why_left, source, locked}]
  competitors JSONB DEFAULT '[]',

  -- Tribal Knowledge
  tribal_knowledge TEXT[] DEFAULT '{}',
  tribal_source TEXT CHECK (tribal_source IN ('call', 'dashboard', 'chat', 'manual')),
  tribal_locked BOOLEAN DEFAULT FALSE,

  -- Computed completion scores (updated on read or via trigger)
  -- {problem: 90, success: 60, users: 70, design: 0, competitors: 100, tribal: 85, files: 60}
  completion_scores JSONB DEFAULT '{}',
  overall_completion INT DEFAULT 0,

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for project_context
CREATE INDEX IF NOT EXISTS idx_project_context_project ON project_context(project_id);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_project_context_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER project_context_updated_at
  BEFORE UPDATE ON project_context
  FOR EACH ROW
  EXECUTE FUNCTION update_project_context_updated_at();
