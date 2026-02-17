-- Migration: 0131_consultant_enrichment
-- Extends profiles table with consultant enrichment columns
-- Adds consultant_enrichment_logs table for audit trail

-- ============================================================================
-- Extend profiles table with enrichment columns
-- ============================================================================

ALTER TABLE profiles
  ADD COLUMN IF NOT EXISTS enrichment_status TEXT DEFAULT 'pending'
    CHECK (enrichment_status IN ('pending', 'enriching', 'enriched', 'failed')),
  ADD COLUMN IF NOT EXISTS linkedin_raw_text TEXT,
  ADD COLUMN IF NOT EXISTS website_raw_text TEXT,
  ADD COLUMN IF NOT EXISTS enriched_profile JSONB DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS industry_expertise TEXT[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS methodology_expertise TEXT[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS consulting_style JSONB DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS consultant_summary TEXT,
  ADD COLUMN IF NOT EXISTS profile_completeness INT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS enriched_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS enrichment_source TEXT;

-- ============================================================================
-- Consultant enrichment logs table (mirrors client_intelligence_logs)
-- ============================================================================

CREATE TABLE IF NOT EXISTS consultant_enrichment_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  trigger_type TEXT NOT NULL CHECK (trigger_type IN (
    'user_request', 'profile_update', 'scheduled', 'onboarding'
  )),
  input_sources JSONB DEFAULT '{}',
  enriched_profile JSONB DEFAULT '{}',
  profile_completeness INT DEFAULT 0,
  model_used TEXT,
  tokens_used INT DEFAULT 0,
  duration_ms INT DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
    'pending', 'running', 'completed', 'failed'
  )),
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_consultant_enrichment_logs_user_id
  ON consultant_enrichment_logs(user_id);

CREATE INDEX IF NOT EXISTS idx_consultant_enrichment_logs_status
  ON consultant_enrichment_logs(status);

-- ============================================================================
-- RLS Policies
-- ============================================================================

ALTER TABLE consultant_enrichment_logs ENABLE ROW LEVEL SECURITY;

-- Authenticated users can read their own logs
CREATE POLICY consultant_enrichment_logs_select_own
  ON consultant_enrichment_logs
  FOR SELECT TO authenticated
  USING (user_id = auth.uid());

-- Service role has full access
CREATE POLICY consultant_enrichment_logs_service_all
  ON consultant_enrichment_logs
  FOR ALL TO service_role
  USING (true)
  WITH CHECK (true);

-- Authenticated users can insert their own logs
CREATE POLICY consultant_enrichment_logs_insert_own
  ON consultant_enrichment_logs
  FOR INSERT TO authenticated
  WITH CHECK (user_id = auth.uid());
