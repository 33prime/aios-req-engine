-- Migration: Add metadata column to projects table
-- Description: Add JSONB metadata column for storing project-specific metadata
-- Date: 2025-12-26
-- Phase: 0 - Foundation

-- =========================
-- Add metadata column to projects table
-- =========================
ALTER TABLE projects
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

-- Add comment for documentation
COMMENT ON COLUMN projects.metadata IS 'Project-specific metadata (flexible JSONB field for future extensions)';

-- Optional: Create index for metadata queries (if needed in future)
-- CREATE INDEX IF NOT EXISTS idx_projects_metadata ON projects USING gin(metadata);



