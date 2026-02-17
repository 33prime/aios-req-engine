-- Migration: 0132_icp_signal_extraction
-- ICP (Ideal Customer Profile) signal extraction system
-- Routes behavioral events against ICP profiles, clusters outliers, scores consultants

-- ============================================================================
-- ICP Profiles — define target consultant segments
-- ============================================================================

CREATE TABLE IF NOT EXISTS icp_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  description TEXT,
  is_active BOOLEAN DEFAULT true,
  signal_patterns JSONB DEFAULT '[]',
  scoring_criteria JSONB DEFAULT '{}',
  target_segments TEXT[] DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================
-- ICP Signals — behavioral events routed against profiles
-- ============================================================================

CREATE TABLE IF NOT EXISTS icp_signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  event_name TEXT NOT NULL,
  event_properties JSONB DEFAULT '{}',
  source TEXT NOT NULL DEFAULT 'posthog'
    CHECK (source IN ('posthog', 'backend', 'manual')),
  routing_status TEXT NOT NULL DEFAULT 'pending'
    CHECK (routing_status IN ('pending', 'auto_routed', 'review', 'outlier', 'dismissed')),
  matched_profile_id UUID REFERENCES icp_profiles(id) ON DELETE SET NULL,
  confidence_score FLOAT DEFAULT 0,
  routed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_icp_signals_user_id ON icp_signals(user_id);
CREATE INDEX IF NOT EXISTS idx_icp_signals_routing_status ON icp_signals(routing_status);
CREATE INDEX IF NOT EXISTS idx_icp_signals_event_name ON icp_signals(event_name);
CREATE INDEX IF NOT EXISTS idx_icp_signals_matched_profile ON icp_signals(matched_profile_id);
CREATE INDEX IF NOT EXISTS idx_icp_signals_created_at ON icp_signals(created_at DESC);

-- ============================================================================
-- ICP Signal Clusters — DBSCAN clusters from outlier signals
-- ============================================================================

CREATE TABLE IF NOT EXISTS icp_signal_clusters (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT,
  description TEXT,
  signal_count INT DEFAULT 0,
  centroid JSONB DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'emerging'
    CHECK (status IN ('emerging', 'validated', 'promoted', 'dismissed')),
  promoted_to_profile_id UUID REFERENCES icp_profiles(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================
-- ICP Signal Cluster Members — junction: signals <-> clusters
-- ============================================================================

CREATE TABLE IF NOT EXISTS icp_signal_cluster_members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cluster_id UUID NOT NULL REFERENCES icp_signal_clusters(id) ON DELETE CASCADE,
  signal_id UUID NOT NULL REFERENCES icp_signals(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(cluster_id, signal_id)
);

-- ============================================================================
-- ICP Consultant Scores — periodic scoring snapshots
-- ============================================================================

CREATE TABLE IF NOT EXISTS icp_consultant_scores (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  profile_id UUID NOT NULL REFERENCES icp_profiles(id) ON DELETE CASCADE,
  score FLOAT NOT NULL DEFAULT 0,
  signal_count INT DEFAULT 0,
  scoring_breakdown JSONB DEFAULT '{}',
  computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(user_id, profile_id)
);

CREATE INDEX IF NOT EXISTS idx_icp_consultant_scores_user_id ON icp_consultant_scores(user_id);
CREATE INDEX IF NOT EXISTS idx_icp_consultant_scores_profile_id ON icp_consultant_scores(profile_id);

-- ============================================================================
-- RLS Policies
-- ============================================================================

ALTER TABLE icp_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE icp_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE icp_signal_clusters ENABLE ROW LEVEL SECURITY;
ALTER TABLE icp_signal_cluster_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE icp_consultant_scores ENABLE ROW LEVEL SECURITY;

-- Service role has full access to all ICP tables
CREATE POLICY icp_profiles_service_all ON icp_profiles
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY icp_signals_service_all ON icp_signals
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY icp_signal_clusters_service_all ON icp_signal_clusters
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY icp_signal_cluster_members_service_all ON icp_signal_cluster_members
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY icp_consultant_scores_service_all ON icp_consultant_scores
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Authenticated users can read ICP profiles (public reference data)
CREATE POLICY icp_profiles_read_auth ON icp_profiles
  FOR SELECT TO authenticated USING (true);

-- Authenticated users can read their own signals and scores
CREATE POLICY icp_signals_read_own ON icp_signals
  FOR SELECT TO authenticated USING (user_id = auth.uid());
CREATE POLICY icp_consultant_scores_read_own ON icp_consultant_scores
  FOR SELECT TO authenticated USING (user_id = auth.uid());
