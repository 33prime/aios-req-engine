-- Universal enrichment_intel JSONB column on all entity tables.
-- Named enrichment_intel (not enrichment) to avoid confusion with
-- existing enrichment_status columns on features/personas/business_drivers.
--
-- Structure:
-- {
--   "canonical_text": "...",
--   "hypothetical_questions": ["...", ...],
--   "expanded_terms": ["...", ...],
--   "before_after": {"before": [...], "after": [...]},
--   "downstream_impacts": ["...", ...],
--   "actors": ["...", ...],
--   "outcome_relevance": ["...", ...],
--   "enrichment_sources": [
--     {"signal_id": "...", "timestamp": "...", "source_authority": "..."}
--   ]
-- }

ALTER TABLE features ADD COLUMN IF NOT EXISTS enrichment_intel JSONB DEFAULT '{}';
ALTER TABLE personas ADD COLUMN IF NOT EXISTS enrichment_intel JSONB DEFAULT '{}';
ALTER TABLE stakeholders ADD COLUMN IF NOT EXISTS enrichment_intel JSONB DEFAULT '{}';
ALTER TABLE workflows ADD COLUMN IF NOT EXISTS enrichment_intel JSONB DEFAULT '{}';
ALTER TABLE vp_steps ADD COLUMN IF NOT EXISTS enrichment_intel JSONB DEFAULT '{}';
ALTER TABLE business_drivers ADD COLUMN IF NOT EXISTS enrichment_intel JSONB DEFAULT '{}';
ALTER TABLE constraints ADD COLUMN IF NOT EXISTS enrichment_intel JSONB DEFAULT '{}';
ALTER TABLE data_entities ADD COLUMN IF NOT EXISTS enrichment_intel JSONB DEFAULT '{}';
ALTER TABLE competitor_references ADD COLUMN IF NOT EXISTS enrichment_intel JSONB DEFAULT '{}';
ALTER TABLE solution_flow_steps ADD COLUMN IF NOT EXISTS enrichment_intel JSONB DEFAULT '{}';
ALTER TABLE unlocks ADD COLUMN IF NOT EXISTS enrichment_intel JSONB DEFAULT '{}';
ALTER TABLE prototype_feedback ADD COLUMN IF NOT EXISTS enrichment_intel JSONB DEFAULT '{}';
