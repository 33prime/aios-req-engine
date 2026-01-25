-- Migration: Stakeholders Enrichment Fields
-- Description: Add engagement analysis and strategic fields for stakeholder management
-- Date: 2026-01-25
-- Part of: Strategic Foundation Entity Enhancement (Phase 1, Task #6)

-- =========================
-- Engagement analysis fields
-- =========================

ALTER TABLE stakeholders
ADD COLUMN IF NOT EXISTS engagement_level TEXT
    CHECK (engagement_level IS NULL OR engagement_level IN ('highly_engaged', 'moderately_engaged', 'neutral', 'disengaged', 'unknown')),
ADD COLUMN IF NOT EXISTS communication_preferences JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS last_interaction_date DATE,
ADD COLUMN IF NOT EXISTS preferred_channel TEXT;

-- =========================
-- Decision-making fields
-- =========================

ALTER TABLE stakeholders
ADD COLUMN IF NOT EXISTS decision_authority TEXT,
ADD COLUMN IF NOT EXISTS approval_required_for TEXT[],
ADD COLUMN IF NOT EXISTS veto_power_over TEXT[];

-- =========================
-- Strategic engagement
-- =========================

ALTER TABLE stakeholders
ADD COLUMN IF NOT EXISTS engagement_strategy TEXT,
ADD COLUMN IF NOT EXISTS risk_if_disengaged TEXT,
ADD COLUMN IF NOT EXISTS win_conditions TEXT[],
ADD COLUMN IF NOT EXISTS key_concerns TEXT[];

-- =========================
-- Relationship mapping
-- =========================

ALTER TABLE stakeholders
ADD COLUMN IF NOT EXISTS reports_to_id UUID REFERENCES stakeholders(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS allies UUID[],
ADD COLUMN IF NOT EXISTS potential_blockers UUID[];

-- =========================
-- Indexes for stakeholder queries
-- =========================

-- Query by engagement level for stakeholder prioritization
CREATE INDEX IF NOT EXISTS idx_stakeholders_engagement_level
    ON stakeholders(project_id, engagement_level)
    WHERE engagement_level IS NOT NULL;

-- Query by influence and engagement for stakeholder matrix
CREATE INDEX IF NOT EXISTS idx_stakeholders_influence_engagement
    ON stakeholders(project_id, influence_level, engagement_level)
    WHERE influence_level IS NOT NULL AND engagement_level IS NOT NULL;

-- Query organizational hierarchy
CREATE INDEX IF NOT EXISTS idx_stakeholders_reports_to
    ON stakeholders(reports_to_id)
    WHERE reports_to_id IS NOT NULL;

-- GIN index for communication preferences
CREATE INDEX IF NOT EXISTS idx_stakeholders_communication_prefs
    ON stakeholders USING gin(communication_preferences);

-- =========================
-- Comments
-- =========================

-- Engagement analysis
COMMENT ON COLUMN stakeholders.engagement_level IS 'Current engagement: highly_engaged, moderately_engaged, neutral, disengaged, unknown';
COMMENT ON COLUMN stakeholders.communication_preferences IS 'Preferences: {"frequency": "weekly", "channel": "email", "format": "detailed", "time_preference": "morning"}';
COMMENT ON COLUMN stakeholders.last_interaction_date IS 'Last meaningful interaction with this stakeholder';
COMMENT ON COLUMN stakeholders.preferred_channel IS 'Preferred contact method (e.g., "email", "slack", "in-person", "phone")';

-- Decision-making
COMMENT ON COLUMN stakeholders.decision_authority IS 'What they can approve (e.g., "Budget up to $50K", "Technical decisions", "Hiring for team")';
COMMENT ON COLUMN stakeholders.approval_required_for IS 'What requires their sign-off (e.g., ["scope changes", "budget increases", "timeline extensions"])';
COMMENT ON COLUMN stakeholders.veto_power_over IS 'What they can block (e.g., ["vendor selection", "architecture decisions"])';

-- Strategic engagement
COMMENT ON COLUMN stakeholders.engagement_strategy IS 'How to keep them engaged (e.g., "Weekly progress emails + monthly demos", "Involve in design reviews")';
COMMENT ON COLUMN stakeholders.risk_if_disengaged IS 'Impact if they disengage (e.g., "Could block launch approval", "Team loses executive air cover")';
COMMENT ON COLUMN stakeholders.win_conditions IS 'What success looks like for them (e.g., ["reduce costs by 30%", "launch before competitor", "zero downtime migration"])';
COMMENT ON COLUMN stakeholders.key_concerns IS 'Top worries extracted from concerns field (e.g., ["budget overruns", "timeline delays", "user adoption"])';

-- Relationship mapping
COMMENT ON COLUMN stakeholders.reports_to_id IS 'Their manager/superior in org chart (links to another stakeholder)';
COMMENT ON COLUMN stakeholders.allies IS 'Stakeholder IDs who support this person or align with their goals';
COMMENT ON COLUMN stakeholders.potential_blockers IS 'Stakeholder IDs who might oppose this person or create friction';

-- =========================
-- Usage notes
-- =========================

-- Communication preferences structure:
-- {
--   "frequency": "daily" | "weekly" | "biweekly" | "monthly",
--   "channel": "email" | "slack" | "teams" | "phone" | "in-person",
--   "format": "brief" | "detailed" | "executive_summary",
--   "time_preference": "morning" | "afternoon" | "end_of_week"
-- }
