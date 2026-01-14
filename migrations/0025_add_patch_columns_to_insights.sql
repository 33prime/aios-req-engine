-- Add columns to insights table to support patch storage
-- Patches are a special type of insight that represent actionable surgical updates

ALTER TABLE insights
  ADD COLUMN IF NOT EXISTS insight_type VARCHAR(50) DEFAULT 'general',
  ADD COLUMN IF NOT EXISTS parent_insight_id UUID REFERENCES insights(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS patch_data JSONB,
  ADD COLUMN IF NOT EXISTS auto_apply_ok BOOLEAN DEFAULT false,
  ADD COLUMN IF NOT EXISTS applied_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS applied_by VARCHAR(255);

-- Add indexes for efficient patch queries
CREATE INDEX IF NOT EXISTS idx_insights_parent_insight_id ON insights(parent_insight_id);
CREATE INDEX IF NOT EXISTS idx_insights_patch_status ON insights(insight_type, status) WHERE insight_type = 'patch';
CREATE INDEX IF NOT EXISTS idx_insights_type ON insights(insight_type);

-- Add comments for documentation
COMMENT ON COLUMN insights.parent_insight_id IS 'For patch insights: the original insight this patch addresses';
COMMENT ON COLUMN insights.patch_data IS 'For patch insights: the ScopedPatch JSON with target entity and proposed changes';
COMMENT ON COLUMN insights.auto_apply_ok IS 'For patch insights: whether this patch passed auto-apply safety checks (true if change_type is add/refine AND severity is minor/moderate AND entity not confirmed_client)';
COMMENT ON COLUMN insights.applied_at IS 'For patch insights: timestamp when patch was applied';
COMMENT ON COLUMN insights.applied_by IS 'For patch insights: who applied it (a_team_agent, manual, etc.)';
