-- Migration: Fix missing columns and migrate existing projects
-- Description: Add applied_at to insights table and migrate existing projects
-- Date: 2025-12-25

-- 1. Add applied_at column to insights table
ALTER TABLE insights
ADD COLUMN IF NOT EXISTS applied_at TIMESTAMPTZ;

-- 2. Insert existing projects into projects table (if they don't exist)
-- This migrates projects that existed before the projects table was created
INSERT INTO projects (id, name, created_at, updated_at, prd_mode)
SELECT DISTINCT
    project_id as id,
    'Project ' || project_id as name,
    MIN(created_at) as created_at,
    now() as updated_at,
    'initial' as prd_mode
FROM signals
WHERE project_id NOT IN (SELECT id FROM projects)
GROUP BY project_id
ON CONFLICT (id) DO NOTHING;

-- 3. Also check prd_sections for any other projects
INSERT INTO projects (id, name, created_at, updated_at, prd_mode)
SELECT DISTINCT
    project_id as id,
    'Project ' || project_id as name,
    MIN(created_at) as created_at,
    now() as updated_at,
    'initial' as prd_mode
FROM prd_sections
WHERE project_id NOT IN (SELECT id FROM projects)
GROUP BY project_id
ON CONFLICT (id) DO NOTHING;

-- 4. Also check features table
INSERT INTO projects (id, name, created_at, updated_at, prd_mode)
SELECT DISTINCT
    project_id as id,
    'Project ' || project_id as name,
    MIN(created_at) as created_at,
    now() as updated_at,
    'initial' as prd_mode
FROM features
WHERE project_id NOT IN (SELECT id FROM projects)
GROUP BY project_id
ON CONFLICT (id) DO NOTHING;

-- Comments
COMMENT ON COLUMN insights.applied_at IS 'Timestamp when the insight was applied to the PRD';
