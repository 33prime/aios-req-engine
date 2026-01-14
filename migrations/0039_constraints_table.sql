-- Migration: Create constraints table for storing extracted constraints, requirements, KPIs, risks
-- This separates non-feature entities from the features table for cleaner data architecture

-- Constraints table
CREATE TABLE IF NOT EXISTS constraints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Core fields
    title TEXT NOT NULL,
    description TEXT,
    constraint_type TEXT NOT NULL CHECK (constraint_type IN (
        'technical',      -- "Must support 10k users"
        'compliance',     -- "HIPAA compliance required"
        'integration',    -- "Must sync with Salesforce"
        'business',       -- "Budget under $50k"
        'timeline',       -- "Must launch by Q3"
        'risk',           -- "Risk of scope creep"
        'kpi',            -- "Reduce churn by 20%"
        'assumption'      -- "Users have modern browsers"
    )),

    -- Severity/priority
    severity TEXT DEFAULT 'should_have' CHECK (severity IN (
        'must_have',      -- Non-negotiable
        'should_have',    -- Important but flexible
        'nice_to_have'    -- Optional
    )),

    -- Evidence and provenance
    evidence JSONB DEFAULT '[]',
    extracted_from_signal_id UUID REFERENCES signals(id),

    -- Linked entities
    linked_feature_ids UUID[] DEFAULT '{}',
    linked_vp_step_ids UUID[] DEFAULT '{}',

    -- Confirmation workflow
    confirmation_status TEXT DEFAULT 'ai_generated' CHECK (confirmation_status IN (
        'ai_generated',
        'confirmed_consultant',
        'needs_client',
        'confirmed_client'
    )),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_constraints_project ON constraints(project_id);
CREATE INDEX IF NOT EXISTS idx_constraints_type ON constraints(constraint_type);
CREATE INDEX IF NOT EXISTS idx_constraints_status ON constraints(confirmation_status);
CREATE INDEX IF NOT EXISTS idx_constraints_severity ON constraints(severity);

-- Trigger for updated_at
DROP TRIGGER IF EXISTS update_constraints_timestamp ON constraints;
CREATE TRIGGER update_constraints_timestamp
    BEFORE UPDATE ON constraints
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add comment for documentation
COMMENT ON TABLE constraints IS 'Stores constraints, requirements, risks, KPIs, and assumptions extracted from signals. Separated from features table for cleaner entity architecture.';
