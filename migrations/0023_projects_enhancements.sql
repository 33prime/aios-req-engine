-- Migration 0023: Projects Table Enhancements
-- Purpose: Add fields to support project management dashboard (search, filter, soft delete)
-- Enables: Project list page with status filtering, search, and user tracking

-- Add new columns to projects table
ALTER TABLE projects
ADD COLUMN IF NOT EXISTS created_by UUID,
ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT ARRAY[]::TEXT[],
ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active' CHECK (status IN ('active', 'archived', 'completed'));

-- Indexes for efficient querying

-- Filter projects by status and sort by creation date
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status, created_at DESC);

-- Full-text search on project names
CREATE INDEX IF NOT EXISTS idx_projects_name_search ON projects USING gin(to_tsvector('english', name));

-- Optional: Full-text search on descriptions (if description column exists)
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'projects' AND column_name = 'description'
  ) THEN
    CREATE INDEX IF NOT EXISTS idx_projects_description_search ON projects USING gin(to_tsvector('english', description));
  END IF;
END $$;

-- Add comments for documentation
COMMENT ON COLUMN projects.created_by IS 'UUID of user who created the project (optional for future multi-user support)';
COMMENT ON COLUMN projects.tags IS 'Array of tags for categorizing projects';
COMMENT ON COLUMN projects.status IS 'Project lifecycle status: active (working), archived (hidden), completed (done)';
