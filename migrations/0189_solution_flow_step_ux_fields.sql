-- Add UX redesign fields to solution_flow_steps
-- story_headline: one punchy sentence — the key moment
-- user_actions: 3-5 things the user can DO on this screen
-- human_value_statement: what this saves the human

ALTER TABLE solution_flow_steps
  ADD COLUMN IF NOT EXISTS story_headline TEXT DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS user_actions JSONB DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS human_value_statement TEXT DEFAULT NULL;
