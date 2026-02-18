-- Migration: 0133_llm_usage_log.sql
-- Description: Centralized LLM token/cost tracking table
-- Date: 2026-02-17

CREATE TABLE IF NOT EXISTS public.llm_usage_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  job_id UUID REFERENCES jobs(id),

  -- What ran
  workflow TEXT NOT NULL,
  chain TEXT,
  model TEXT NOT NULL,
  provider TEXT NOT NULL,

  -- Token counts
  tokens_input INT DEFAULT 0,
  tokens_output INT DEFAULT 0,
  tokens_cache_read INT DEFAULT 0,
  tokens_cache_create INT DEFAULT 0,

  -- Cost
  estimated_cost_usd FLOAT DEFAULT 0,

  -- Timing
  duration_ms INT DEFAULT 0,

  created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for admin queries
CREATE INDEX idx_llm_usage_user ON llm_usage_log(user_id);
CREATE INDEX idx_llm_usage_project ON llm_usage_log(project_id);
CREATE INDEX idx_llm_usage_workflow ON llm_usage_log(workflow);
CREATE INDEX idx_llm_usage_created ON llm_usage_log(created_at);

-- RLS
ALTER TABLE llm_usage_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_all" ON llm_usage_log FOR ALL TO service_role USING (true);
CREATE POLICY "authenticated_read_own" ON llm_usage_log FOR SELECT TO authenticated
  USING (user_id = auth.uid());
