-- Confirmation history: append-only log of who confirmed what and when.
-- Project type for internal / new_product / hybrid fork.

ALTER TABLE features ADD COLUMN IF NOT EXISTS confirmation_history JSONB DEFAULT '[]';
ALTER TABLE personas ADD COLUMN IF NOT EXISTS confirmation_history JSONB DEFAULT '[]';
ALTER TABLE stakeholders ADD COLUMN IF NOT EXISTS confirmation_history JSONB DEFAULT '[]';
ALTER TABLE workflows ADD COLUMN IF NOT EXISTS confirmation_history JSONB DEFAULT '[]';
ALTER TABLE vp_steps ADD COLUMN IF NOT EXISTS confirmation_history JSONB DEFAULT '[]';
ALTER TABLE business_drivers ADD COLUMN IF NOT EXISTS confirmation_history JSONB DEFAULT '[]';
ALTER TABLE constraints ADD COLUMN IF NOT EXISTS confirmation_history JSONB DEFAULT '[]';
ALTER TABLE data_entities ADD COLUMN IF NOT EXISTS confirmation_history JSONB DEFAULT '[]';
ALTER TABLE competitor_references ADD COLUMN IF NOT EXISTS confirmation_history JSONB DEFAULT '[]';
ALTER TABLE solution_flow_steps ADD COLUMN IF NOT EXISTS confirmation_history JSONB DEFAULT '[]';
ALTER TABLE unlocks ADD COLUMN IF NOT EXISTS confirmation_history JSONB DEFAULT '[]';
ALTER TABLE outcomes ADD COLUMN IF NOT EXISTS confirmation_history JSONB DEFAULT '[]';
ALTER TABLE outcome_actors ADD COLUMN IF NOT EXISTS confirmation_history JSONB DEFAULT '[]';

ALTER TABLE projects ADD COLUMN IF NOT EXISTS project_type TEXT DEFAULT 'new_product'
    CHECK (project_type IN ('internal', 'new_product', 'hybrid'));
