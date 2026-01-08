-- Migration: Stakeholders Enhancement
-- Description: Add domain expertise, topic tracking, and signal provenance to stakeholders
-- Date: 2025-01-07

-- ============================================================================
-- Add new columns to existing stakeholders table
-- ============================================================================

-- Domain expertise for "who would know" matching
ALTER TABLE stakeholders
ADD COLUMN IF NOT EXISTS domain_expertise TEXT[] DEFAULT '{}';

-- Topic mention counts for ranking expertise
ALTER TABLE stakeholders
ADD COLUMN IF NOT EXISTS topic_mentions JSONB DEFAULT '{}';

-- Source type: how was this stakeholder identified
ALTER TABLE stakeholders
ADD COLUMN IF NOT EXISTS source_type TEXT CHECK (source_type IN ('direct_participant', 'mentioned', 'manual'));

-- Primary contact flag
ALTER TABLE stakeholders
ADD COLUMN IF NOT EXISTS is_primary_contact BOOLEAN DEFAULT false;

-- Signal provenance
ALTER TABLE stakeholders
ADD COLUMN IF NOT EXISTS extracted_from_signal_id UUID REFERENCES signals(id) ON DELETE SET NULL;

ALTER TABLE stakeholders
ADD COLUMN IF NOT EXISTS mentioned_in_signals UUID[] DEFAULT '{}';

-- Phone number (optional)
ALTER TABLE stakeholders
ADD COLUMN IF NOT EXISTS phone TEXT;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_stakeholders_domain ON stakeholders USING GIN(domain_expertise);
CREATE INDEX IF NOT EXISTS idx_stakeholders_primary ON stakeholders(project_id, is_primary_contact) WHERE is_primary_contact = true;
CREATE INDEX IF NOT EXISTS idx_stakeholders_source_type ON stakeholders(project_id, source_type);

-- Comments
COMMENT ON COLUMN stakeholders.domain_expertise IS 'Areas of expertise: finance, security, ux, etc.';
COMMENT ON COLUMN stakeholders.topic_mentions IS 'Count of times stakeholder discussed each topic {"sso": 3, "budget": 5}';
COMMENT ON COLUMN stakeholders.source_type IS 'How stakeholder was identified: direct_participant (on call/email), mentioned (referenced by others), manual (added by user)';
COMMENT ON COLUMN stakeholders.is_primary_contact IS 'Primary point of contact for the project';
COMMENT ON COLUMN stakeholders.extracted_from_signal_id IS 'Signal that first identified this stakeholder';
COMMENT ON COLUMN stakeholders.mentioned_in_signals IS 'Array of signal IDs where this stakeholder was mentioned';

-- ============================================================================
-- Trigger: Auto-set first stakeholder as primary contact
-- ============================================================================

CREATE OR REPLACE FUNCTION set_first_stakeholder_as_primary()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- If this is the first stakeholder for the project, make them primary
    IF NOT EXISTS (
        SELECT 1 FROM stakeholders
        WHERE project_id = NEW.project_id
        AND id != NEW.id
    ) THEN
        NEW.is_primary_contact := true;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_set_first_stakeholder_primary ON stakeholders;
CREATE TRIGGER trg_set_first_stakeholder_primary
    BEFORE INSERT ON stakeholders
    FOR EACH ROW
    EXECUTE FUNCTION set_first_stakeholder_as_primary();

-- ============================================================================
-- Trigger: Update updated_at timestamp
-- ============================================================================

CREATE OR REPLACE FUNCTION update_stakeholder_timestamp()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_update_stakeholder_timestamp ON stakeholders;
CREATE TRIGGER trg_update_stakeholder_timestamp
    BEFORE UPDATE ON stakeholders
    FOR EACH ROW
    EXECUTE FUNCTION update_stakeholder_timestamp();

-- ============================================================================
-- Helper function: Update topic mentions for a stakeholder
-- ============================================================================

CREATE OR REPLACE FUNCTION update_stakeholder_topics(
    p_stakeholder_id UUID,
    p_topics TEXT[]
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    topic TEXT;
BEGIN
    FOREACH topic IN ARRAY p_topics
    LOOP
        UPDATE stakeholders
        SET topic_mentions = jsonb_set(
            COALESCE(topic_mentions, '{}'::jsonb),
            ARRAY[topic],
            (COALESCE((topic_mentions->topic)::int, 0) + 1)::text::jsonb
        )
        WHERE id = p_stakeholder_id;
    END LOOP;
END;
$$;

COMMENT ON FUNCTION update_stakeholder_topics IS 'Increment topic mention counts for a stakeholder';
