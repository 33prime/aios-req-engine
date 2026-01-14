-- Migration: 0054_projects_portal_fields.sql
-- Description: Add client portal fields to projects table
-- Date: 2026-01-12

-- Add portal fields to projects table
ALTER TABLE projects ADD COLUMN IF NOT EXISTS portal_phase TEXT
  DEFAULT 'pre_call' CHECK (portal_phase IN ('pre_call', 'post_call', 'building', 'testing'));

ALTER TABLE projects ADD COLUMN IF NOT EXISTS discovery_call_date TIMESTAMPTZ;

ALTER TABLE projects ADD COLUMN IF NOT EXISTS call_completed_at TIMESTAMPTZ;

ALTER TABLE projects ADD COLUMN IF NOT EXISTS prototype_expected_date TIMESTAMPTZ;

ALTER TABLE projects ADD COLUMN IF NOT EXISTS portal_enabled BOOLEAN DEFAULT FALSE;

-- Client-facing project name (may differ from internal name)
ALTER TABLE projects ADD COLUMN IF NOT EXISTS client_display_name TEXT;

-- Index for portal-enabled projects
CREATE INDEX IF NOT EXISTS idx_projects_portal_enabled ON projects(portal_enabled) WHERE portal_enabled = TRUE;
