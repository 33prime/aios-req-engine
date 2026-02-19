-- Migration: 0142_stakeholder_client_fk.sql
-- Add client_id FK to stakeholders so they link directly to the client org

-- Add column
ALTER TABLE stakeholders
    ADD COLUMN IF NOT EXISTS client_id UUID REFERENCES clients(id) ON DELETE SET NULL;

-- Index for querying stakeholders by client
CREATE INDEX IF NOT EXISTS idx_stakeholders_client_id
    ON stakeholders(client_id)
    WHERE client_id IS NOT NULL;

-- Backfill: set client_id from project.client_id for existing rows
UPDATE stakeholders s
SET client_id = p.client_id
FROM projects p
WHERE s.project_id = p.id
  AND p.client_id IS NOT NULL
  AND s.client_id IS NULL;

-- Extend created_by CHECK to include 'project_launch'
ALTER TABLE stakeholders DROP CONSTRAINT IF EXISTS stakeholders_created_by_check;
ALTER TABLE stakeholders
    ADD CONSTRAINT stakeholders_created_by_check
    CHECK (created_by IN ('system', 'consultant', 'client', 'di_agent', 'si_agent', 'project_launch'));
