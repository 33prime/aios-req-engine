-- Migration 0140: Unlocks table
-- Strategic business outcomes that become possible when software automates work

-- Unlocks table
CREATE TABLE unlocks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Core content
    title TEXT NOT NULL,
    narrative TEXT NOT NULL,
    impact_type TEXT NOT NULL CHECK (impact_type IN (
        'operational_scale', 'talent_leverage', 'risk_elimination',
        'revenue_expansion', 'data_intelligence', 'compliance', 'speed_to_change'
    )),

    -- Classification
    unlock_kind TEXT NOT NULL CHECK (unlock_kind IN ('new_capability', 'feature_upgrade')),
    tier TEXT NOT NULL CHECK (tier IN ('implement_now', 'after_feedback', 'if_this_works')),

    -- Impact analysis
    magnitude TEXT,
    why_now TEXT,
    non_obvious TEXT,

    -- Provenance (typed relationships stored as JSONB array)
    provenance JSONB NOT NULL DEFAULT '[]'::jsonb,

    -- Lifecycle
    status TEXT NOT NULL DEFAULT 'generated' CHECK (status IN (
        'generated', 'curated', 'promoted', 'dismissed'
    )),
    promoted_feature_id UUID REFERENCES features(id) ON DELETE SET NULL,

    -- Generation metadata
    generation_batch_id UUID,
    generation_source TEXT CHECK (generation_source IN (
        'holistic_analysis', 'competitor_synthesis', 'workflow_enrichment', 'manual'
    )),

    -- Standard fields
    evidence JSONB DEFAULT '[]'::jsonb,
    source_signal_ids UUID[] DEFAULT '{}',
    version INTEGER NOT NULL DEFAULT 1,
    confirmation_status TEXT NOT NULL DEFAULT 'ai_generated'
        CHECK (confirmation_status IN ('ai_generated', 'confirmed_consultant', 'confirmed_client', 'needs_client')),
    is_stale BOOLEAN NOT NULL DEFAULT FALSE,
    stale_reason TEXT,
    stale_since TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX idx_unlocks_project ON unlocks(project_id);
CREATE INDEX idx_unlocks_tier ON unlocks(project_id, tier);
CREATE INDEX idx_unlocks_status ON unlocks(project_id, status);
CREATE INDEX idx_unlocks_batch ON unlocks(generation_batch_id);

-- RLS (CRITICAL — must have policies or queries return empty in prod)
ALTER TABLE unlocks ENABLE ROW LEVEL SECURITY;
CREATE POLICY "authenticated_read_unlocks" ON unlocks FOR SELECT TO authenticated USING (true);
CREATE POLICY "authenticated_write_unlocks" ON unlocks FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "authenticated_update_unlocks" ON unlocks FOR UPDATE TO authenticated USING (true);
CREATE POLICY "authenticated_delete_unlocks" ON unlocks FOR DELETE TO authenticated USING (true);
CREATE POLICY "service_role_all_unlocks" ON unlocks FOR ALL TO service_role USING (true);
