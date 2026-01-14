-- Business drivers entity
-- Stores KPIs, pains, and goals for the project

CREATE TABLE IF NOT EXISTS business_drivers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) NOT NULL,
    driver_type TEXT NOT NULL CHECK (driver_type IN ('kpi', 'pain', 'goal')),
    description TEXT NOT NULL,
    measurement TEXT,     -- For KPIs: "From 2 weeks to 3 days"
    timeframe TEXT,       -- "Within 6 months"
    stakeholder_id UUID REFERENCES stakeholders(id),
    priority INTEGER DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
    source_signal_id UUID REFERENCES signals(id),
    revision_id UUID,  -- For future revision tracking
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_business_drivers_project ON business_drivers(project_id);
CREATE INDEX IF NOT EXISTS idx_business_drivers_type ON business_drivers(driver_type);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_business_drivers_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS business_drivers_updated_at ON business_drivers;
CREATE TRIGGER business_drivers_updated_at
    BEFORE UPDATE ON business_drivers
    FOR EACH ROW
    EXECUTE FUNCTION update_business_drivers_updated_at();
