-- Migration: Activity Feed & Enhanced Auto-Apply
-- Description: Add activity feed table for curated change notifications and enhance insights for VP impact tracking
-- Date: 2025-01-05

-- =============================================================================
-- 1. Activity Feed Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS activity_feed (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

  -- Activity categorization
  activity_type TEXT NOT NULL CHECK (activity_type IN (
    'auto_applied',      -- Change was auto-applied
    'needs_review',      -- Change requires user review
    'user_applied',      -- User manually applied a change
    'user_dismissed',    -- User dismissed a suggestion
    'entity_refreshed',  -- Stale entity was refreshed
    'cascade_triggered', -- Cascade propagated to dependents
    'research_ingested', -- New research was processed
    'insight_created'    -- Red Team found new insight
  )),

  -- What changed
  entity_type TEXT,  -- feature, persona, vp_step, strategic_context
  entity_id UUID,
  entity_name TEXT,

  -- Change details
  change_summary TEXT NOT NULL,  -- Human-readable: "Updated goals based on research"
  change_details JSONB DEFAULT '{}',  -- Full details for expansion

  -- Source tracking
  source_type TEXT,  -- a_team, cascade, user, research, redteam
  source_id UUID,    -- insight_id, cascade_event_id, etc.

  -- Aggregation support
  aggregation_key TEXT,  -- For grouping: "auto_applied:feature:2024-01-05"

  -- Status
  is_read BOOLEAN DEFAULT FALSE,
  requires_action BOOLEAN DEFAULT FALSE,
  action_taken_at TIMESTAMPTZ,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_activity_feed_project_recent
  ON activity_feed(project_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_activity_feed_unread
  ON activity_feed(project_id, is_read, requires_action)
  WHERE is_read = FALSE;

CREATE INDEX IF NOT EXISTS idx_activity_feed_aggregation
  ON activity_feed(project_id, aggregation_key, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_activity_feed_needs_action
  ON activity_feed(project_id, requires_action, action_taken_at)
  WHERE requires_action = TRUE AND action_taken_at IS NULL;


-- =============================================================================
-- 2. Enhance Insights Table with VP Impact Tracking
-- =============================================================================

-- Track if the patch would make structural VP changes
ALTER TABLE insights
  ADD COLUMN IF NOT EXISTS vp_structural_change BOOLEAN DEFAULT FALSE;

-- Count of VP steps that would be affected
ALTER TABLE insights
  ADD COLUMN IF NOT EXISTS affected_vp_step_count INTEGER DEFAULT 0;

-- Reason for auto-apply decision (for transparency)
ALTER TABLE insights
  ADD COLUMN IF NOT EXISTS auto_apply_reason TEXT;
-- Values: 'high_confidence', 'low_impact', 'review_required:{reason}'


-- =============================================================================
-- 3. Function to Get Aggregated Activity
-- =============================================================================

CREATE OR REPLACE FUNCTION get_aggregated_activity(
  p_project_id UUID,
  p_since TIMESTAMPTZ
) RETURNS TABLE (
  aggregation_key TEXT,
  activity_type TEXT,
  entity_type TEXT,
  count BIGINT,
  entity_names TEXT[],
  entity_ids UUID[],
  latest_summary TEXT,
  latest_created_at TIMESTAMPTZ,
  requires_action BOOLEAN,
  action_pending_count BIGINT
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    af.aggregation_key,
    af.activity_type,
    af.entity_type,
    COUNT(*)::BIGINT as count,
    ARRAY_AGG(DISTINCT af.entity_name) FILTER (WHERE af.entity_name IS NOT NULL) as entity_names,
    ARRAY_AGG(DISTINCT af.entity_id) FILTER (WHERE af.entity_id IS NOT NULL) as entity_ids,
    (ARRAY_AGG(af.change_summary ORDER BY af.created_at DESC))[1] as latest_summary,
    MAX(af.created_at) as latest_created_at,
    BOOL_OR(af.requires_action) as requires_action,
    COUNT(*) FILTER (WHERE af.requires_action = TRUE AND af.action_taken_at IS NULL)::BIGINT as action_pending_count
  FROM activity_feed af
  WHERE af.project_id = p_project_id
    AND af.created_at >= p_since
  GROUP BY af.aggregation_key, af.activity_type, af.entity_type
  ORDER BY latest_created_at DESC;
END;
$$ LANGUAGE plpgsql;


-- =============================================================================
-- 4. Function to Mark Activity Read
-- =============================================================================

CREATE OR REPLACE FUNCTION mark_activity_read(
  p_activity_ids UUID[]
) RETURNS INTEGER AS $$
DECLARE
  updated_count INTEGER;
BEGIN
  UPDATE activity_feed
  SET is_read = TRUE
  WHERE id = ANY(p_activity_ids)
    AND is_read = FALSE;

  GET DIAGNOSTICS updated_count = ROW_COUNT;
  RETURN updated_count;
END;
$$ LANGUAGE plpgsql;


-- =============================================================================
-- 5. Function to Get Pending Action Count (for badges)
-- =============================================================================

CREATE OR REPLACE FUNCTION get_pending_action_count(
  p_project_id UUID
) RETURNS INTEGER AS $$
DECLARE
  pending_count INTEGER;
BEGIN
  SELECT COUNT(*)::INTEGER INTO pending_count
  FROM activity_feed
  WHERE project_id = p_project_id
    AND requires_action = TRUE
    AND action_taken_at IS NULL;

  RETURN pending_count;
END;
$$ LANGUAGE plpgsql;


-- =============================================================================
-- 6. Comments
-- =============================================================================

COMMENT ON TABLE activity_feed IS
  'Curated activity feed showing recent changes with smart aggregation';

COMMENT ON COLUMN activity_feed.activity_type IS
  'Type of activity: auto_applied, needs_review, user_applied, user_dismissed, entity_refreshed, cascade_triggered, research_ingested, insight_created';

COMMENT ON COLUMN activity_feed.aggregation_key IS
  'Key for grouping similar events, format: activity_type:entity_type:YYYY-MM-DD';

COMMENT ON COLUMN activity_feed.requires_action IS
  'TRUE if this item needs user review/action';

COMMENT ON COLUMN insights.vp_structural_change IS
  'TRUE if this patch would add or remove VP steps';

COMMENT ON COLUMN insights.affected_vp_step_count IS
  'Number of VP steps that would be affected by this change';

COMMENT ON COLUMN insights.auto_apply_reason IS
  'Reason for auto-apply decision: high_confidence, low_impact, or review_required:{reason}';

COMMENT ON FUNCTION get_aggregated_activity IS
  'Get activity feed with smart aggregation - groups similar events by aggregation_key';

COMMENT ON FUNCTION get_pending_action_count IS
  'Get count of items needing action for badge display';
