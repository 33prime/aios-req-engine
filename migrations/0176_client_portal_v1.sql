-- Client Portal v1: Validation Machine
-- stakeholder_assignments, client_validation_verdicts, role extension, epic confirmation columns

-- 1. Stakeholder assignments (AIOS recommendations → entity assignments)
CREATE TABLE stakeholder_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    stakeholder_id UUID NOT NULL REFERENCES stakeholders(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL CHECK (entity_type IN (
        'workflow', 'business_driver', 'feature', 'persona',
        'vp_step', 'prototype_epic'
    )),
    entity_id TEXT NOT NULL,
    assignment_type TEXT NOT NULL DEFAULT 'validate'
        CHECK (assignment_type IN ('validate', 'knowledge_owner', 'review')),
    source TEXT NOT NULL DEFAULT 'ai'
        CHECK (source IN ('ai', 'consultant', 'client_admin')),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'in_progress', 'completed', 'skipped')),
    priority INT NOT NULL DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
    reason TEXT,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(stakeholder_id, entity_type, entity_id)
);
CREATE INDEX idx_sa_project ON stakeholder_assignments(project_id);
CREATE INDEX idx_sa_stakeholder ON stakeholder_assignments(stakeholder_id);
CREATE INDEX idx_sa_entity ON stakeholder_assignments(entity_type, entity_id);
CREATE INDEX idx_sa_pending ON stakeholder_assignments(project_id, status) WHERE status = 'pending';

-- 2. Client validation verdicts (audit trail)
CREATE TABLE client_validation_verdicts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    assignment_id UUID REFERENCES stakeholder_assignments(id) ON DELETE SET NULL,
    stakeholder_id UUID NOT NULL REFERENCES stakeholders(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    verdict TEXT NOT NULL CHECK (verdict IN ('confirmed', 'refine', 'flag')),
    notes TEXT,
    refinement_details JSONB DEFAULT '{}',
    signal_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_cvv_project ON client_validation_verdicts(project_id);
CREATE INDEX idx_cvv_entity ON client_validation_verdicts(entity_type, entity_id);
CREATE INDEX idx_cvv_stakeholder ON client_validation_verdicts(stakeholder_id);

-- 3. Extend client_role for portal roles
ALTER TABLE project_members
    DROP CONSTRAINT IF EXISTS project_members_client_role_check;
ALTER TABLE project_members
    ADD CONSTRAINT project_members_client_role_check
    CHECK (client_role IS NULL OR client_role IN (
        'decision_maker', 'support', 'client_admin', 'client_user'
    ));

-- 4. Add stakeholder tracking to epic confirmations
ALTER TABLE prototype_epic_confirmations
    ADD COLUMN IF NOT EXISTS stakeholder_id UUID REFERENCES stakeholders(id),
    ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id);
