-- Migration 0030: Proposal Expiration and Cascade Support
-- Purpose: Add expiration tracking, staleness detection, and cascade events

-- ============================================================================
-- 1. BATCH PROPOSALS: Add expiration and staleness columns
-- ============================================================================

-- Add expiration and staleness columns
ALTER TABLE batch_proposals
ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS stale_reason TEXT,
ADD COLUMN IF NOT EXISTS affected_entities JSONB DEFAULT '[]'::jsonb;

-- Update status constraint to include 'archived'
ALTER TABLE batch_proposals
DROP CONSTRAINT IF EXISTS batch_proposals_status_check;

ALTER TABLE batch_proposals
ADD CONSTRAINT batch_proposals_status_check
CHECK (status IN ('pending', 'previewed', 'applied', 'discarded', 'archived'));

-- Index for finding proposals that need expiration check
CREATE INDEX IF NOT EXISTS idx_batch_proposals_expires_at
ON batch_proposals(project_id, expires_at)
WHERE status IN ('pending', 'previewed');

-- Index for finding stale proposals
CREATE INDEX IF NOT EXISTS idx_batch_proposals_stale
ON batch_proposals(project_id, stale_reason)
WHERE stale_reason IS NOT NULL AND status IN ('pending', 'previewed');

COMMENT ON COLUMN batch_proposals.expires_at IS 'When proposal automatically expires (soft archive)';
COMMENT ON COLUMN batch_proposals.stale_reason IS 'Why proposal is stale (e.g., "VP Step 3 modified after proposal created")';
COMMENT ON COLUMN batch_proposals.affected_entities IS 'Array of {entity_type, entity_id, updated_at} for staleness checks';

-- ============================================================================
-- 2. PERSONAS: Add health and coverage scores
-- ============================================================================

ALTER TABLE personas
ADD COLUMN IF NOT EXISTS health_score FLOAT DEFAULT 100.0
  CHECK (health_score >= 0.0 AND health_score <= 100.0),
ADD COLUMN IF NOT EXISTS coverage_score FLOAT DEFAULT 0.0
  CHECK (coverage_score >= 0.0 AND coverage_score <= 100.0);

-- Index for finding unhealthy personas
CREATE INDEX IF NOT EXISTS idx_personas_health
ON personas(project_id, health_score)
WHERE health_score < 50.0;

COMMENT ON COLUMN personas.health_score IS 'Persona freshness score (100=fresh, degrades 10%/week after 7 days, min 20)';
COMMENT ON COLUMN personas.coverage_score IS 'Percentage of persona goals addressed by features (0-100)';

-- ============================================================================
-- 3. CASCADE EVENTS: Track entity-to-entity cascades
-- ============================================================================

CREATE TABLE IF NOT EXISTS cascade_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Source entity that triggered the cascade
    source_entity_type TEXT NOT NULL,
    source_entity_id UUID NOT NULL,
    source_summary TEXT,  -- Human-readable summary like "Feature: Voice Dictation"

    -- Target entity to be updated
    target_entity_type TEXT NOT NULL,
    target_entity_id UUID NOT NULL,
    target_summary TEXT,  -- Human-readable summary like "VP Step 3: Survey Input"

    -- Cascade details
    cascade_type TEXT NOT NULL CHECK (cascade_type IN ('auto', 'suggested', 'logged')),
    confidence FLOAT NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    changes JSONB NOT NULL,  -- The proposed changes to apply
    rationale TEXT,  -- Why this cascade was suggested

    -- Status
    applied BOOLEAN DEFAULT FALSE,
    applied_at TIMESTAMPTZ,
    applied_by TEXT,
    dismissed BOOLEAN DEFAULT FALSE,
    dismissed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for finding pending cascades
CREATE INDEX IF NOT EXISTS idx_cascade_events_pending
ON cascade_events(project_id, cascade_type)
WHERE applied = FALSE AND dismissed = FALSE;

-- Index for source entity lookups
CREATE INDEX IF NOT EXISTS idx_cascade_events_source
ON cascade_events(source_entity_type, source_entity_id);

-- Index for target entity lookups
CREATE INDEX IF NOT EXISTS idx_cascade_events_target
ON cascade_events(target_entity_type, target_entity_id);

COMMENT ON TABLE cascade_events IS 'Tracks state cascades between entities with confidence-based routing';
COMMENT ON COLUMN cascade_events.cascade_type IS 'auto (>0.8 confidence, applied immediately), suggested (0.5-0.8, shown in sidebar), logged (<0.5, for review)';
COMMENT ON COLUMN cascade_events.changes IS 'JSON object with proposed changes, e.g., {"add_to_needed": "Voice Dictation"}';

-- ============================================================================
-- 4. RLS POLICIES (if RLS is enabled)
-- ============================================================================

-- Cascade events RLS
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'projects' AND policyname LIKE '%rls%'
    ) THEN
        -- Enable RLS on cascade_events
        ALTER TABLE cascade_events ENABLE ROW LEVEL SECURITY;

        -- Policy for service role
        CREATE POLICY cascade_events_service_policy ON cascade_events
            FOR ALL
            TO service_role
            USING (true)
            WITH CHECK (true);
    END IF;
END $$;
