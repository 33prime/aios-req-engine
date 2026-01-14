-- Migration: Field Attribution Tracking
-- Description: Track which signals contributed to which entity fields
-- Date: 2025-01-06

-- ============================================================================
-- Field Attributions Table
-- Tracks source attribution: which signals contributed to which fields
-- ============================================================================

CREATE TABLE IF NOT EXISTS field_attributions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Entity reference
    entity_type TEXT NOT NULL,
    entity_id UUID NOT NULL,

    -- Field that was influenced
    field_path TEXT NOT NULL,  -- e.g., 'name', 'acceptance_criteria[0]', 'goals'

    -- Signal that contributed
    signal_id UUID NOT NULL REFERENCES signals(id) ON DELETE CASCADE,

    -- Version context
    version_number INT DEFAULT 1,

    -- Timestamps
    contributed_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT field_attributions_entity_type_check
    CHECK (entity_type IN ('feature', 'persona', 'vp_step', 'prd_section'))
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_field_attributions_entity
ON field_attributions(entity_type, entity_id);

CREATE INDEX IF NOT EXISTS idx_field_attributions_signal
ON field_attributions(signal_id);

CREATE INDEX IF NOT EXISTS idx_field_attributions_field
ON field_attributions(entity_type, entity_id, field_path);

-- Composite index for version-specific lookups
CREATE INDEX IF NOT EXISTS idx_field_attributions_version
ON field_attributions(entity_type, entity_id, version_number);

-- Comments
COMMENT ON TABLE field_attributions IS 'Tracks which signals contributed to which entity fields for source attribution';
COMMENT ON COLUMN field_attributions.field_path IS 'Path to field, e.g., name, acceptance_criteria[0], goals';
COMMENT ON COLUMN field_attributions.version_number IS 'Version of entity when this attribution was recorded';
COMMENT ON COLUMN field_attributions.contributed_at IS 'When this attribution was recorded';

-- ============================================================================
-- Add helper function for getting field attributions with signal details
-- ============================================================================

CREATE OR REPLACE FUNCTION get_field_attributions(
    p_entity_type TEXT,
    p_entity_id UUID,
    p_field_path TEXT DEFAULT NULL
)
RETURNS TABLE (
    field_path TEXT,
    signal_id UUID,
    signal_source TEXT,
    signal_label TEXT,
    contributed_at TIMESTAMPTZ,
    version_number INT
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        fa.field_path,
        fa.signal_id,
        s.source,
        s.source_label,
        fa.contributed_at,
        fa.version_number
    FROM field_attributions fa
    JOIN signals s ON s.id = fa.signal_id
    WHERE fa.entity_type = p_entity_type
      AND fa.entity_id = p_entity_id
      AND (p_field_path IS NULL OR fa.field_path = p_field_path)
    ORDER BY fa.contributed_at DESC;
$$;

COMMENT ON FUNCTION get_field_attributions IS 'Get field attributions with signal details for an entity';

-- ============================================================================
-- Add trigger to auto-record attributions from enrichment_revisions
-- When a revision is created with source_signal_id, auto-attribute changed fields
-- ============================================================================

CREATE OR REPLACE FUNCTION auto_attribute_changes()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    field_name TEXT;
BEGIN
    -- Only process if there's a source signal and changes
    IF NEW.source_signal_id IS NOT NULL AND NEW.changes IS NOT NULL AND NEW.changes != '{}'::jsonb THEN
        -- Loop through each changed field
        FOR field_name IN SELECT jsonb_object_keys(NEW.changes)
        LOOP
            -- Insert attribution for this field
            INSERT INTO field_attributions (
                entity_type,
                entity_id,
                field_path,
                signal_id,
                version_number
            ) VALUES (
                NEW.entity_type,
                NEW.entity_id,
                field_name,
                NEW.source_signal_id,
                NEW.revision_number
            )
            ON CONFLICT DO NOTHING;
        END LOOP;
    END IF;

    RETURN NEW;
END;
$$;

-- Create trigger on enrichment_revisions
DROP TRIGGER IF EXISTS trg_auto_attribute_changes ON enrichment_revisions;
CREATE TRIGGER trg_auto_attribute_changes
    AFTER INSERT ON enrichment_revisions
    FOR EACH ROW
    EXECUTE FUNCTION auto_attribute_changes();

COMMENT ON FUNCTION auto_attribute_changes IS 'Automatically create field attributions when revisions are created with source_signal_id';
