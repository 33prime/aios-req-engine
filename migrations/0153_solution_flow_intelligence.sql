-- Solution Flow Intelligence: new columns for Success tab, AI tab, and narrative beats
-- success_criteria: ["Candidate completes in under 45 minutes", ...]
-- pain_points_addressed: [{"text": "Manual assessments take 3+ hours", "persona": "Clinical Evaluator"}, ...]
-- goals_addressed: ["Reduce evaluation time by 60%", ...]
-- ai_config: {"role": "...", "behaviors": ["..."], "guardrails": ["..."]}

ALTER TABLE solution_flow_steps
  ADD COLUMN IF NOT EXISTS success_criteria JSONB DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS pain_points_addressed JSONB DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS goals_addressed JSONB DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS ai_config JSONB DEFAULT NULL;
