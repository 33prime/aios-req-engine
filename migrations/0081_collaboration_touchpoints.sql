-- migrations/0081_collaboration_touchpoints.sql
-- Description: Create collaboration touchpoints table for tracking client interaction events
-- Date: 2026-01-26

-- ============================================================================
-- Collaboration Touchpoints
-- Tracks discrete client collaboration events (discovery calls, validation rounds, etc.)
-- ============================================================================

-- Enum for touchpoint types
CREATE TYPE touchpoint_type AS ENUM (
    'discovery_call',
    'validation_round',
    'follow_up_call',
    'prototype_review',
    'feedback_session'
);

-- Enum for touchpoint status
CREATE TYPE touchpoint_status AS ENUM (
    'preparing',    -- Consultant preparing (generating questions, etc.)
    'ready',        -- Ready to send/share with client
    'sent',         -- Sent to client portal
    'in_progress',  -- Client is actively engaged
    'completed',    -- Touchpoint completed
    'cancelled'     -- Cancelled/skipped
);

-- Main touchpoints table
CREATE TABLE collaboration_touchpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Identity
    type touchpoint_type NOT NULL,
    title TEXT NOT NULL,
    description TEXT,

    -- Status tracking
    status touchpoint_status NOT NULL DEFAULT 'preparing',

    -- Related entities (nullable - not all touchpoints have all)
    meeting_id UUID REFERENCES meetings(id) ON DELETE SET NULL,
    discovery_prep_bundle_id UUID,  -- Links to discovery_prep_bundles

    -- Ordering within project (for multiple validation rounds, etc.)
    sequence_number INT NOT NULL DEFAULT 1,

    -- Outcomes summary (populated when completed)
    -- Structure: {
    --   questions_sent: 5,
    --   questions_answered: 4,
    --   documents_requested: 3,
    --   documents_received: 2,
    --   features_extracted: 12,
    --   personas_identified: 3,
    --   items_confirmed: 8,
    --   items_rejected: 2,
    --   feedback_items: 5
    -- }
    outcomes JSONB DEFAULT '{}',

    -- Portal sync tracking
    portal_items_count INT DEFAULT 0,
    portal_items_completed INT DEFAULT 0,

    -- Timestamps
    prepared_at TIMESTAMPTZ,      -- When consultant finished prep
    sent_at TIMESTAMPTZ,          -- When sent to client portal
    started_at TIMESTAMPTZ,       -- When client started engaging
    completed_at TIMESTAMPTZ,     -- When touchpoint completed
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for efficient project lookups
CREATE INDEX idx_touchpoints_project_id ON collaboration_touchpoints(project_id);

-- Index for ordering touchpoints
CREATE INDEX idx_touchpoints_project_sequence ON collaboration_touchpoints(project_id, sequence_number);

-- Index for status filtering
CREATE INDEX idx_touchpoints_status ON collaboration_touchpoints(status);

-- Trigger to update updated_at
CREATE TRIGGER update_touchpoints_updated_at
    BEFORE UPDATE ON collaboration_touchpoints
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Extend projects table with collaboration tracking fields
-- ============================================================================

-- Add collaboration_phase to track where we are in the collaboration lifecycle
-- This is separate from portal_phase - collaboration_phase is consultant-centric
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'projects' AND column_name = 'collaboration_phase'
    ) THEN
        ALTER TABLE projects ADD COLUMN collaboration_phase TEXT DEFAULT 'pre_discovery';
    END IF;
END $$;

-- Comment on the phase values
COMMENT ON COLUMN projects.collaboration_phase IS
'Consultant-centric collaboration phase: pre_discovery, discovery, validation, prototype, iteration';

-- ============================================================================
-- RLS Policies
-- ============================================================================

ALTER TABLE collaboration_touchpoints ENABLE ROW LEVEL SECURITY;

-- Consultants can manage touchpoints for their projects
CREATE POLICY "Consultants can manage touchpoints"
ON collaboration_touchpoints
FOR ALL
TO authenticated
USING (
    project_id IN (
        SELECT project_id FROM project_members
        WHERE user_id = auth.uid() AND role IN ('owner', 'consultant', 'admin')
    )
);

-- Clients can view touchpoints for their projects (read-only)
CREATE POLICY "Clients can view touchpoints"
ON collaboration_touchpoints
FOR SELECT
TO authenticated
USING (
    project_id IN (
        SELECT project_id FROM project_members
        WHERE user_id = auth.uid() AND role = 'client'
    )
);

-- ============================================================================
-- Helper function to get current active touchpoint
-- ============================================================================

CREATE OR REPLACE FUNCTION get_active_touchpoint(p_project_id UUID)
RETURNS UUID AS $$
DECLARE
    touchpoint_id UUID;
BEGIN
    -- Get the most recent non-completed touchpoint
    SELECT id INTO touchpoint_id
    FROM collaboration_touchpoints
    WHERE project_id = p_project_id
      AND status NOT IN ('completed', 'cancelled')
    ORDER BY sequence_number DESC
    LIMIT 1;

    RETURN touchpoint_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- Helper function to auto-create touchpoint on discovery prep generation
-- ============================================================================

CREATE OR REPLACE FUNCTION auto_create_discovery_touchpoint()
RETURNS TRIGGER AS $$
BEGIN
    -- When a discovery prep bundle is created, auto-create a touchpoint
    INSERT INTO collaboration_touchpoints (
        project_id,
        type,
        title,
        status,
        discovery_prep_bundle_id,
        sequence_number
    )
    SELECT
        NEW.project_id,
        'discovery_call'::touchpoint_type,
        'Discovery Call',
        'preparing'::touchpoint_status,
        NEW.id,
        COALESCE(
            (SELECT MAX(sequence_number) + 1
             FROM collaboration_touchpoints
             WHERE project_id = NEW.project_id AND type = 'discovery_call'),
            1
        )
    WHERE NOT EXISTS (
        -- Don't create if there's already a preparing/ready discovery touchpoint
        SELECT 1 FROM collaboration_touchpoints
        WHERE project_id = NEW.project_id
          AND type = 'discovery_call'
          AND status IN ('preparing', 'ready', 'sent', 'in_progress')
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to discovery_prep_bundles
DROP TRIGGER IF EXISTS trigger_auto_create_discovery_touchpoint ON discovery_prep_bundles;
CREATE TRIGGER trigger_auto_create_discovery_touchpoint
    AFTER INSERT ON discovery_prep_bundles
    FOR EACH ROW
    EXECUTE FUNCTION auto_create_discovery_touchpoint();
