-- Add stage and status_narrative fields to projects
-- Used for dashboard display and AI-generated status summaries

-- Add stage column
ALTER TABLE projects ADD COLUMN IF NOT EXISTS stage text DEFAULT 'discovery';
-- Values: 'discovery', 'prototype_refinement', 'proposal'

-- Add status_narrative column for AI-generated summaries
ALTER TABLE projects ADD COLUMN IF NOT EXISTS status_narrative jsonb;
-- Structure: {
--   "where_today": "Currently at the Discovery stage...",
--   "where_going": "The immediate goal is to...",
--   "updated_at": "2024-01-15T10:00:00Z"
-- }

-- Add client_name for display (separate from company info)
ALTER TABLE projects ADD COLUMN IF NOT EXISTS client_name text;

-- Create index for stage filtering
CREATE INDEX IF NOT EXISTS idx_projects_stage ON projects(stage);

-- Comment on columns
COMMENT ON COLUMN projects.stage IS 'Project stage: discovery, prototype_refinement, proposal';
COMMENT ON COLUMN projects.status_narrative IS 'AI-generated status summary with where_today and where_going';
COMMENT ON COLUMN projects.client_name IS 'Display name for the client/company';
