-- Add critical_requirements JSONB column to call_strategy_briefs
-- Stores top 3 unresolved requirements from 2.5 retrieval pipeline

ALTER TABLE call_strategy_briefs
ADD COLUMN IF NOT EXISTS critical_requirements jsonb DEFAULT '[]'::jsonb;

COMMENT ON COLUMN call_strategy_briefs.critical_requirements IS 'Top 3 critical unresolved requirements from 2.5 retrieval: [{name, entity_type, status, context}]';
