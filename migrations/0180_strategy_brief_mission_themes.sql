-- Mission Themes: replace call_goals + mission_critical_questions + focus_areas
-- with rich, evidence-backed mission themes powered by full 2.5 retrieval.

ALTER TABLE call_strategy_briefs
ADD COLUMN IF NOT EXISTS mission_themes jsonb DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS meeting_frame jsonb DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS retrieval_metadata jsonb DEFAULT '{}'::jsonb;

COMMENT ON COLUMN call_strategy_briefs.mission_themes IS 'Array of MissionTheme objects replacing call_goals + mission_critical_questions + focus_areas';
COMMENT ON COLUMN call_strategy_briefs.meeting_frame IS 'Stage-aware framing: phase, question_goal, retrieval params used';
COMMENT ON COLUMN call_strategy_briefs.retrieval_metadata IS 'Debug: queries, chunk count, rerank scores, graph depth';
