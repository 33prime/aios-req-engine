-- Migration: Add first_name/last_name to stakeholders + search indexes
-- Purpose: Support People page with name splitting and search

ALTER TABLE stakeholders
  ADD COLUMN IF NOT EXISTS first_name TEXT,
  ADD COLUMN IF NOT EXISTS last_name TEXT;

-- Backfill from existing name column
UPDATE stakeholders SET
  first_name = split_part(name, ' ', 1),
  last_name = CASE WHEN name LIKE '% %' THEN substring(name FROM position(' ' IN name) + 1) ELSE NULL END
WHERE first_name IS NULL;

-- Search indexes
CREATE INDEX IF NOT EXISTS idx_stakeholders_name_search ON stakeholders USING gin(to_tsvector('simple', name));
CREATE INDEX IF NOT EXISTS idx_stakeholders_email_lower ON stakeholders(LOWER(email)) WHERE email IS NOT NULL;
