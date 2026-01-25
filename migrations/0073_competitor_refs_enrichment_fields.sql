-- Migration: Competitor References Enrichment Fields
-- Description: Add competitive intelligence fields for market analysis
-- Date: 2026-01-25
-- Part of: Strategic Foundation Entity Enhancement (Phase 1, Task #4)

-- =========================
-- Market analysis fields
-- =========================

ALTER TABLE competitor_references
ADD COLUMN IF NOT EXISTS market_position TEXT
    CHECK (market_position IS NULL OR market_position IN ('market_leader', 'established_player', 'emerging_challenger', 'niche_player', 'declining')),
ADD COLUMN IF NOT EXISTS pricing_model TEXT,
ADD COLUMN IF NOT EXISTS target_audience TEXT,
ADD COLUMN IF NOT EXISTS key_differentiator TEXT;

-- =========================
-- Feature comparison
-- =========================

ALTER TABLE competitor_references
ADD COLUMN IF NOT EXISTS feature_comparison JSONB DEFAULT '{}'::jsonb;

-- =========================
-- Business intelligence
-- =========================

ALTER TABLE competitor_references
ADD COLUMN IF NOT EXISTS funding_stage TEXT
    CHECK (funding_stage IS NULL OR funding_stage IN ('bootstrapped', 'pre_seed', 'seed', 'series_a', 'series_b', 'series_c', 'series_d_plus', 'public', 'acquired', 'unknown')),
ADD COLUMN IF NOT EXISTS estimated_users TEXT,
ADD COLUMN IF NOT EXISTS founded_year INTEGER,
ADD COLUMN IF NOT EXISTS employee_count TEXT;

-- =========================
-- Indexes for competitive analysis queries
-- =========================

-- Query by market position for competitive landscape mapping
CREATE INDEX IF NOT EXISTS idx_competitor_refs_market_position
    ON competitor_references(project_id, market_position)
    WHERE reference_type = 'competitor' AND market_position IS NOT NULL;

-- Query by funding stage for investment context
CREATE INDEX IF NOT EXISTS idx_competitor_refs_funding_stage
    ON competitor_references(project_id, funding_stage)
    WHERE reference_type = 'competitor' AND funding_stage IS NOT NULL;

-- GIN index for feature comparison queries
CREATE INDEX IF NOT EXISTS idx_competitor_refs_feature_comparison
    ON competitor_references USING gin(feature_comparison);

-- =========================
-- Comments
-- =========================

-- Market analysis
COMMENT ON COLUMN competitor_references.market_position IS 'Competitive standing: market_leader, established_player, emerging_challenger, niche_player, declining';
COMMENT ON COLUMN competitor_references.pricing_model IS 'How they charge (e.g., "Freemium with $99/mo Pro", "Enterprise only, custom pricing", "Free forever")';
COMMENT ON COLUMN competitor_references.target_audience IS 'Their primary market segment (e.g., "SMBs in healthcare", "Enterprise retailers", "Individual creators")';
COMMENT ON COLUMN competitor_references.key_differentiator IS 'What makes them unique (e.g., "AI-powered automation", "White-label solution", "Lowest price in market")';

-- Feature comparison
COMMENT ON COLUMN competitor_references.feature_comparison IS 'Structured feature comparison: {"auth": {"us": "pending", "them": "sso_saml"}, "mobile_app": {"us": "yes", "them": "ios_only"}}';

-- Business intelligence
COMMENT ON COLUMN competitor_references.funding_stage IS 'Investment stage: bootstrapped, pre_seed, seed, series_a/b/c/d_plus, public, acquired, unknown';
COMMENT ON COLUMN competitor_references.estimated_users IS 'User base estimate (e.g., "50K+ customers", "1M MAU", "500 enterprise clients")';
COMMENT ON COLUMN competitor_references.founded_year IS 'Year company was founded (e.g., 2018)';
COMMENT ON COLUMN competitor_references.employee_count IS 'Team size estimate (e.g., "11-50", "500+", "10 person team")';

-- =========================
-- Usage notes
-- =========================

-- These enrichment fields apply to reference_type = 'competitor'
-- For design_inspiration and feature_inspiration, use existing fields:
--   - screenshots (visual references)
--   - features_to_study (what to learn from them)
--   - research_notes (general observations)
