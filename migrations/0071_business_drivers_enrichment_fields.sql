-- Migration: Business Drivers Enrichment Fields
-- Description: Add type-specific enrichment fields for KPIs, Pain Points, and Goals
-- Date: 2026-01-25
-- Part of: Strategic Foundation Entity Enhancement (Phase 1, Task #2)

-- =========================
-- KPI-specific enrichment fields
-- =========================

ALTER TABLE business_drivers
ADD COLUMN IF NOT EXISTS baseline_value TEXT,
ADD COLUMN IF NOT EXISTS target_value TEXT,
ADD COLUMN IF NOT EXISTS measurement_method TEXT,
ADD COLUMN IF NOT EXISTS tracking_frequency TEXT,
ADD COLUMN IF NOT EXISTS data_source TEXT,
ADD COLUMN IF NOT EXISTS responsible_team TEXT;

-- =========================
-- Pain Point-specific enrichment fields
-- =========================

ALTER TABLE business_drivers
ADD COLUMN IF NOT EXISTS severity TEXT
    CHECK (severity IS NULL OR severity IN ('critical', 'high', 'medium', 'low')),
ADD COLUMN IF NOT EXISTS frequency TEXT
    CHECK (frequency IS NULL OR frequency IN ('constant', 'daily', 'weekly', 'monthly', 'rare')),
ADD COLUMN IF NOT EXISTS affected_users TEXT,
ADD COLUMN IF NOT EXISTS business_impact TEXT,
ADD COLUMN IF NOT EXISTS current_workaround TEXT;

-- =========================
-- Goal-specific enrichment fields
-- =========================

ALTER TABLE business_drivers
ADD COLUMN IF NOT EXISTS goal_timeframe TEXT,
ADD COLUMN IF NOT EXISTS success_criteria TEXT,
ADD COLUMN IF NOT EXISTS dependencies TEXT,
ADD COLUMN IF NOT EXISTS owner TEXT;

-- =========================
-- Indexes for enrichment queries
-- =========================

-- Query KPIs by measurement readiness (has baseline and target)
CREATE INDEX IF NOT EXISTS idx_business_drivers_kpi_enriched
    ON business_drivers(project_id, driver_type)
    WHERE driver_type = 'kpi' AND baseline_value IS NOT NULL AND target_value IS NOT NULL;

-- Query pains by severity for prioritization
CREATE INDEX IF NOT EXISTS idx_business_drivers_pain_severity
    ON business_drivers(project_id, severity)
    WHERE driver_type = 'pain' AND severity IS NOT NULL;

-- Query goals by timeframe for roadmapping
CREATE INDEX IF NOT EXISTS idx_business_drivers_goal_timeframe
    ON business_drivers(project_id, goal_timeframe)
    WHERE driver_type = 'goal' AND goal_timeframe IS NOT NULL;

-- =========================
-- Comments
-- =========================

-- KPI fields
COMMENT ON COLUMN business_drivers.baseline_value IS 'Current state of the KPI (e.g., "5 seconds average load time")';
COMMENT ON COLUMN business_drivers.target_value IS 'Desired state of the KPI (e.g., "2 seconds average load time")';
COMMENT ON COLUMN business_drivers.measurement_method IS 'How this KPI is measured (e.g., "Google Analytics Core Web Vitals")';
COMMENT ON COLUMN business_drivers.tracking_frequency IS 'How often to measure (e.g., "daily", "weekly", "monthly")';
COMMENT ON COLUMN business_drivers.data_source IS 'Where the data comes from (e.g., "Mixpanel dashboard", "SQL query on orders table")';
COMMENT ON COLUMN business_drivers.responsible_team IS 'Team or person responsible for this KPI (e.g., "Growth team", "Sarah (Product Manager)")';

-- Pain Point fields
COMMENT ON COLUMN business_drivers.severity IS 'Impact severity: critical (blocking), high (major friction), medium (inconvenience), low (minor)';
COMMENT ON COLUMN business_drivers.frequency IS 'How often this pain occurs: constant, daily, weekly, monthly, rare';
COMMENT ON COLUMN business_drivers.affected_users IS 'Who experiences this pain (e.g., "All warehouse staff", "10% of customers in checkout")';
COMMENT ON COLUMN business_drivers.business_impact IS 'Quantified impact (e.g., "~$50K/month in lost sales", "2 hours/day of manual work")';
COMMENT ON COLUMN business_drivers.current_workaround IS 'How users currently work around this pain (e.g., "Manual Excel exports and email")';

-- Goal fields
COMMENT ON COLUMN business_drivers.goal_timeframe IS 'When this goal should be achieved (e.g., "Q2 2024", "6 months from launch")';
COMMENT ON COLUMN business_drivers.success_criteria IS 'Concrete criteria for goal achievement (e.g., "50+ paying customers", "NPS score > 40")';
COMMENT ON COLUMN business_drivers.dependencies IS 'What must happen first (e.g., "Requires payment processor integration", "Depends on hiring DevOps lead")';
COMMENT ON COLUMN business_drivers.owner IS 'Who owns delivery of this goal (e.g., "VP Sales", "Engineering team")';

-- =========================
-- Validation notes
-- =========================

-- Type-specific field usage:
-- - KPI records should use: baseline_value, target_value, measurement_method, tracking_frequency, data_source, responsible_team
-- - Pain records should use: severity, frequency, affected_users, business_impact, current_workaround
-- - Goal records should use: goal_timeframe, success_criteria, dependencies, owner
--
-- Fields from other types should remain NULL (enforced at application layer)
