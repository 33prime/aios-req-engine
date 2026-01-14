-- Deep Research Agent tables
-- Tables for storing user voices/reviews and market gaps

-- User voices: Actual quotes and feedback from users
CREATE TABLE IF NOT EXISTS user_voices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Source info
    source_type TEXT NOT NULL CHECK (source_type IN ('g2', 'capterra', 'trustpilot', 'reddit', 'twitter', 'forum', 'other')),
    source_url TEXT,
    competitor_name TEXT,  -- If this review is about a competitor

    -- Review data
    review_date TIMESTAMPTZ,
    rating DECIMAL(2,1) CHECK (rating >= 1 AND rating <= 5),
    reviewer_role TEXT,  -- "Sales Manager", "Sales Rep", etc.
    company_size TEXT,  -- "small", "mid-market", "enterprise"

    -- Content
    quote TEXT NOT NULL,  -- The actual user quote
    sentiment TEXT NOT NULL CHECK (sentiment IN ('positive', 'negative', 'neutral', 'mixed')),
    themes JSONB DEFAULT '[]'::jsonb,  -- ["ease_of_use", "mobile_experience", "integration"]

    -- Relevance
    relevance_to_project TEXT DEFAULT 'medium' CHECK (relevance_to_project IN ('high', 'medium', 'low')),
    feature_mentions JSONB DEFAULT '[]'::jsonb,  -- Features mentioned
    pain_points_mentioned JSONB DEFAULT '[]'::jsonb,

    -- Research metadata
    research_run_id UUID,  -- Which research run found this
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_user_voices_project ON user_voices(project_id);
CREATE INDEX idx_user_voices_competitor ON user_voices(competitor_name);
CREATE INDEX idx_user_voices_sentiment ON user_voices(sentiment);


-- Market gaps: Identified opportunities in the market
CREATE TABLE IF NOT EXISTS market_gaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Gap identification
    gap_type TEXT NOT NULL CHECK (gap_type IN ('feature_gap', 'market_segment', 'integration', 'pricing', 'ux', 'technical')),
    title TEXT NOT NULL,
    description TEXT NOT NULL,

    -- Evidence
    evidence JSONB DEFAULT '[]'::jsonb,  -- Specific data points
    sources JSONB DEFAULT '[]'::jsonb,
    confidence TEXT DEFAULT 'medium' CHECK (confidence IN ('low', 'medium', 'high')),

    -- Opportunity analysis
    opportunity_size TEXT CHECK (opportunity_size IN ('small', 'medium', 'large')),
    implementation_complexity TEXT CHECK (implementation_complexity IN ('low', 'medium', 'high')),
    competitive_advantage_potential TEXT CHECK (competitive_advantage_potential IN ('low', 'medium', 'high')),

    -- Relationship to our product
    related_feature_ids JSONB DEFAULT '[]'::jsonb,
    recommended_action TEXT,
    priority INTEGER DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),  -- 1=highest

    -- Research metadata
    research_run_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_market_gaps_project ON market_gaps(project_id);
CREATE INDEX idx_market_gaps_type ON market_gaps(gap_type);
CREATE INDEX idx_market_gaps_priority ON market_gaps(priority);


-- Feature intelligence: Feature-level competitive analysis
CREATE TABLE IF NOT EXISTS feature_intelligence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Feature identification
    feature_category TEXT NOT NULL,  -- "audio_recording", "ai_analysis", etc.
    our_feature_id UUID REFERENCES features(id),  -- Link to our feature if exists
    our_feature_name TEXT,

    -- Analysis
    market_standard BOOLEAN DEFAULT FALSE,  -- Is this table stakes?
    differentiation_opportunity TEXT DEFAULT 'medium' CHECK (differentiation_opportunity IN ('low', 'medium', 'high')),
    implementation_notes TEXT,

    -- User voice summary
    user_sentiment TEXT CHECK (user_sentiment IN ('positive', 'neutral', 'negative', 'mixed')),
    common_complaints JSONB DEFAULT '[]'::jsonb,
    feature_requests JSONB DEFAULT '[]'::jsonb,

    -- Competitor implementations stored as JSONB array
    competitor_implementations JSONB DEFAULT '[]'::jsonb,
    -- Format: [{"competitor_name": "X", "has_feature": true, "quality": "good", "unique_approach": "..."}, ...]

    -- Sources
    sources JSONB DEFAULT '[]'::jsonb,

    -- Metadata
    research_run_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_feature_intel_project ON feature_intelligence(project_id);
CREATE INDEX idx_feature_intel_feature ON feature_intelligence(our_feature_id);
CREATE INDEX idx_feature_intel_category ON feature_intelligence(feature_category);


-- Research runs: Track each research agent execution
CREATE TABLE IF NOT EXISTS research_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Execution info
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'completed', 'partial', 'failed')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,

    -- Configuration
    focus_areas JSONB DEFAULT '[]'::jsonb,
    max_competitors INTEGER DEFAULT 5,
    include_g2_reviews BOOLEAN DEFAULT TRUE,

    -- Results summary
    competitors_found INTEGER DEFAULT 0,
    competitors_analyzed INTEGER DEFAULT 0,
    reviews_analyzed INTEGER DEFAULT 0,
    market_gaps_identified INTEGER DEFAULT 0,

    -- Phases
    phases_completed JSONB DEFAULT '[]'::jsonb,

    -- Output
    executive_summary TEXT,
    key_insights JSONB DEFAULT '[]'::jsonb,
    recommended_actions JSONB DEFAULT '[]'::jsonb,

    -- Error tracking
    error_message TEXT
);

CREATE INDEX idx_research_runs_project ON research_runs(project_id);
CREATE INDEX idx_research_runs_status ON research_runs(status);
