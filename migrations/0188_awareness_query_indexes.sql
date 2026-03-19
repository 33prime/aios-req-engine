-- Indexes for awareness queries (entity inventory, recent signals, open questions).
-- These support the 3 new parallel queries added in chat v7 awareness enrichment.

-- Recent signals: ORDER BY created_at DESC LIMIT 3, filtered by project_id
CREATE INDEX IF NOT EXISTS idx_signals_project_created
    ON signals (project_id, created_at DESC);

-- Open questions: filtered by project_id + status='open'
CREATE INDEX IF NOT EXISTS idx_open_questions_project_status
    ON open_questions (project_id, status);

-- Entity inventory queries use the existing FK indexes on project_id.
-- No additional indexes needed for features, personas, workflows, constraints,
-- business_drivers — they already have idx_{table}_project_id from FK constraints.
