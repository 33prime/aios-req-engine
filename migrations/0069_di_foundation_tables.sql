-- Design Intelligence (DI) Agent Foundation System
--
-- This migration creates the foundation tables for the DI Agent system:
-- 1. project_foundation - Stores gate data (core pain, persona, wow moment, etc.)
-- 2. di_analysis_cache - Caches expensive analysis results
-- 3. di_agent_logs - Logs agent reasoning traces for debugging
-- 4. vertical_knowledge - Stores reusable industry knowledge

-- ============================================================================
-- 1. PROJECT FOUNDATION TABLE
-- ============================================================================
-- Stores the foundational elements (gates) for each project
-- These elements determine readiness to build prototype vs final product

CREATE TABLE IF NOT EXISTS project_foundation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE UNIQUE NOT NULL,

    -- Phase 1: Prototype Gates (required to build trust-building prototype)
    core_pain JSONB DEFAULT NULL,
    -- {
    --   statement: "THE problem (singular)",
    --   trigger: "Why now? What made them reach out?",
    --   stakes: "What happens if unsolved?",
    --   who_feels_it: "Who experiences this pain most?",
    --   confidence: 0.0-1.0,
    --   confirmed_by: "client" | "consultant" | null,
    --   evidence: ["signal_id_1", "signal_id_2", ...]
    -- }

    primary_persona JSONB DEFAULT NULL,
    -- {
    --   name: "Role name (e.g., Development Director)",
    --   role: "What they do",
    --   goal: "What they're trying to achieve",
    --   pain_connection: "How core pain affects them specifically",
    --   context: "Their daily reality",
    --   confidence: 0.0-1.0,
    --   confirmed_by: "client" | "consultant" | null
    -- }

    wow_moment JSONB DEFAULT NULL,
    -- {
    --   description: "The peak moment where core pain dissolves",
    --   core_pain_inversion: "How this is the opposite of the pain",
    --   emotional_impact: "How they'll feel at this moment",
    --   visual_concept: "What they'll SEE in the prototype",
    --   level_1: "Core pain solved (required)",
    --   level_2: "Adjacent pains addressed (better)",
    --   level_3: "Unstated needs met (holy shit)",
    --   confidence: 0.0-1.0
    -- }

    design_preferences JSONB DEFAULT NULL,
    -- {
    --   visual_style: "clean/minimal" | "playful" | "enterprise" | null,
    --   references: ["Product they love 1", "Product they love 2"],
    --   anti_references: ["Product they hated 1"],
    --   specific_requirements: ["Accessibility", "WCAG AA", etc.]
    -- }

    -- Phase 2: Build Gates (required to build real product)
    business_case JSONB DEFAULT NULL,
    -- {
    --   value_to_business: "How solving this helps the organization",
    --   roi_framing: "Value in dollars, time, or risk",
    --   success_kpis: [
    --     {
    --       metric: "Donor retention rate",
    --       current_state: "~45%",
    --       target_state: "60%+",
    --       measurement_method: "How they'll measure",
    --       timeframe: "When to measure"
    --     }
    --   ],
    --   why_priority: "Why invest in this vs other things",
    --   confidence: 0.0-1.0,
    --   confirmed_by: "client" | "consultant" | null
    -- }

    budget_constraints JSONB DEFAULT NULL,
    -- {
    --   budget_range: "$200-500/month" or "$5K-10K one-time",
    --   budget_flexibility: "firm" | "flexible" | "unknown",
    --   timeline: "When they need it",
    --   hard_deadline: "Immovable date" | null,
    --   deadline_driver: "What's driving the deadline" | null,
    --   technical_constraints: ["Must integrate with X", ...],
    --   organizational_constraints: ["Who approves", "change tolerance", ...],
    --   confidence: 0.0-1.0,
    --   confirmed_by: "client" | "consultant" | null
    -- }

    confirmed_scope JSONB DEFAULT NULL,
    -- {
    --   v1_features: ["feature_id_1", "feature_id_2", ...],
    --   v2_features: ["feature_id_3", ...],
    --   v1_agreed: true | false,
    --   specs_signed_off: true | false,
    --   confirmed_by: "client" | "consultant" | null
    -- }

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_project_foundation_project_id
    ON project_foundation(project_id);

COMMENT ON TABLE project_foundation IS 'Foundation elements (gates) that determine project readiness for prototype vs build phases';
COMMENT ON COLUMN project_foundation.core_pain IS 'THE core pain (singular) - root problem, not symptoms';
COMMENT ON COLUMN project_foundation.primary_persona IS 'Who we are building for FIRST - the primary user persona';
COMMENT ON COLUMN project_foundation.wow_moment IS 'The peak moment where core pain dissolves - with Level 1/2/3 progression';
COMMENT ON COLUMN project_foundation.design_preferences IS 'Visual style, references, anti-references (optional gate)';
COMMENT ON COLUMN project_foundation.business_case IS 'ROI, KPIs, value justification - often unlocked by prototype';
COMMENT ON COLUMN project_foundation.budget_constraints IS 'Budget, timeline, technical and organizational constraints';
COMMENT ON COLUMN project_foundation.confirmed_scope IS 'V1 vs V2 feature split, client agreement';

-- ============================================================================
-- 2. DI ANALYSIS CACHE TABLE
-- ============================================================================
-- Caches expensive analysis results to avoid recomputation
-- Invalidated when new signals arrive or foundation changes

CREATE TABLE IF NOT EXISTS di_analysis_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE UNIQUE NOT NULL,

    -- Cached analysis results (expensive LLM operations)
    org_profile JSONB DEFAULT NULL,
    -- Organization analysis (industry, stage, culture, etc.)

    detected_signals JSONB DEFAULT NULL,
    -- Implicit signals detected (emotional state, org dynamics, etc.)

    inferences JSONB DEFAULT NULL,
    -- Inferences from explicit facts (hidden stakeholders, constraints, needs)

    identified_stakeholders JSONB DEFAULT NULL,
    -- Stakeholders identified from signals and inference

    identified_risks JSONB DEFAULT NULL,
    -- Risk analysis results

    identified_gaps JSONB DEFAULT NULL,
    -- Gap analysis results

    -- Confidence tracking
    overall_confidence FLOAT DEFAULT 0.0,
    confidence_by_area JSONB DEFAULT '{}',
    -- {"core_pain": 0.8, "stakeholders": 0.7, ...}

    -- Cache management
    signals_analyzed UUID[] DEFAULT ARRAY[]::UUID[],
    -- Which signal IDs have been analyzed

    last_signal_analyzed_at TIMESTAMPTZ,
    -- Timestamp of most recent signal analyzed

    last_full_analysis_at TIMESTAMPTZ,
    -- When was full analysis last run

    invalidated_at TIMESTAMPTZ DEFAULT NULL,
    -- When cache was invalidated (null = valid)

    invalidation_reason TEXT,
    -- Why was cache invalidated

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_di_analysis_cache_project_id
    ON di_analysis_cache(project_id);

CREATE INDEX IF NOT EXISTS idx_di_analysis_cache_invalidated
    ON di_analysis_cache(invalidated_at)
    WHERE invalidated_at IS NULL;

COMMENT ON TABLE di_analysis_cache IS 'Cached DI Agent analysis results to avoid expensive recomputation';
COMMENT ON COLUMN di_analysis_cache.signals_analyzed IS 'Array of signal UUIDs that have been analyzed';
COMMENT ON COLUMN di_analysis_cache.invalidated_at IS 'When cache was marked invalid (NULL = valid, non-NULL = stale)';
COMMENT ON COLUMN di_analysis_cache.confidence_by_area IS 'Confidence scores for different analysis areas';

-- ============================================================================
-- 3. DI AGENT LOGS TABLE
-- ============================================================================
-- Logs all DI Agent reasoning traces for debugging and learning

CREATE TABLE IF NOT EXISTS di_agent_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE NOT NULL,

    -- Invocation context
    trigger VARCHAR(50) NOT NULL,
    -- "new_signal" | "user_request" | "scheduled" | "pre_call"

    trigger_context TEXT,
    -- Additional context about the trigger

    -- OBSERVE → THINK → DECIDE → ACT trace
    observation TEXT,
    -- What the agent observed about current state

    thinking TEXT,
    -- The agent's analysis and reasoning

    decision TEXT,
    -- What the agent decided to do and why

    action_type VARCHAR(50),
    -- "tool_call" | "guidance" | "stop" | "confirmation"

    -- Action details
    tools_called JSONB,
    -- [{tool_name: "extract_core_pain", args: {...}, result: {...}}]

    guidance_provided JSONB,
    -- {summary: "...", questions: [...], signals_to_watch: [...]}

    stop_reason TEXT,
    -- Why the agent stopped (if action_type = "stop")

    -- Readiness tracking
    readiness_before INT,
    readiness_after INT,
    gates_affected TEXT[],

    -- Execution metadata
    execution_time_ms INT,
    llm_model VARCHAR(50),
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_di_agent_logs_project_id
    ON di_agent_logs(project_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_di_agent_logs_trigger
    ON di_agent_logs(trigger);

CREATE INDEX IF NOT EXISTS idx_di_agent_logs_action_type
    ON di_agent_logs(action_type);

COMMENT ON TABLE di_agent_logs IS 'DI Agent reasoning traces - full OBSERVE → THINK → DECIDE → ACT logs for debugging';
COMMENT ON COLUMN di_agent_logs.observation IS 'What the agent observed (state snapshot, readiness, gates, cache)';
COMMENT ON COLUMN di_agent_logs.thinking IS 'The agent''s analysis - biggest gap, what''s missing';
COMMENT ON COLUMN di_agent_logs.decision IS 'What the agent decided to do and why';
COMMENT ON COLUMN di_agent_logs.action_type IS 'Type of action taken: tool_call, guidance, stop, or confirmation';

-- ============================================================================
-- 4. VERTICAL KNOWLEDGE TABLE
-- ============================================================================
-- Stores reusable industry/vertical knowledge for context and inference

CREATE TABLE IF NOT EXISTS vertical_knowledge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    vertical VARCHAR(50) NOT NULL,
    -- "SaaS", "nonprofit", "healthcare", "education", etc.

    category VARCHAR(50) NOT NULL,
    -- "common_problems" | "stakeholder_patterns" | "terminology" |
    -- "failure_modes" | "success_metrics"

    content JSONB NOT NULL,
    -- Vertical-specific knowledge content
    -- Structure varies by category:
    -- common_problems: [{problem: "...", frequency: "high", ...}]
    -- stakeholder_patterns: [{role: "...", typical_concerns: [...], ...}]
    -- terminology: {term: "definition", ...}

    metadata JSONB DEFAULT '{}',
    -- Additional metadata (source, confidence, last_updated, etc.)

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(vertical, category)
);

CREATE INDEX IF NOT EXISTS idx_vertical_knowledge_vertical
    ON vertical_knowledge(vertical);

CREATE INDEX IF NOT EXISTS idx_vertical_knowledge_category
    ON vertical_knowledge(category);

COMMENT ON TABLE vertical_knowledge IS 'Reusable industry/vertical knowledge for DI Agent context and inference';
COMMENT ON COLUMN vertical_knowledge.vertical IS 'Industry vertical (SaaS, nonprofit, healthcare, etc.)';
COMMENT ON COLUMN vertical_knowledge.category IS 'Knowledge category (common_problems, stakeholder_patterns, terminology, etc.)';
COMMENT ON COLUMN vertical_knowledge.content IS 'JSONB content - structure varies by category';

-- ============================================================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================================================

-- Trigger function for project_foundation.updated_at
CREATE OR REPLACE FUNCTION update_project_foundation_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS project_foundation_updated_at ON project_foundation;
CREATE TRIGGER project_foundation_updated_at
    BEFORE UPDATE ON project_foundation
    FOR EACH ROW
    EXECUTE FUNCTION update_project_foundation_updated_at();

-- Trigger function for di_analysis_cache.updated_at
CREATE OR REPLACE FUNCTION update_di_analysis_cache_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS di_analysis_cache_updated_at ON di_analysis_cache;
CREATE TRIGGER di_analysis_cache_updated_at
    BEFORE UPDATE ON di_analysis_cache
    FOR EACH ROW
    EXECUTE FUNCTION update_di_analysis_cache_updated_at();

-- Trigger function for vertical_knowledge.updated_at
CREATE OR REPLACE FUNCTION update_vertical_knowledge_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS vertical_knowledge_updated_at ON vertical_knowledge;
CREATE TRIGGER vertical_knowledge_updated_at
    BEFORE UPDATE ON vertical_knowledge
    FOR EACH ROW
    EXECUTE FUNCTION update_vertical_knowledge_updated_at();

-- ============================================================================
-- SEED DATA - Example vertical knowledge
-- ============================================================================

-- SaaS common problems
INSERT INTO vertical_knowledge (vertical, category, content, metadata)
VALUES (
    'SaaS',
    'common_problems',
    '[
        {
            "problem": "Churn prediction and prevention",
            "frequency": "very_high",
            "typical_triggers": ["Lost customers", "Usage drops", "Support tickets increase"],
            "stakeholders": ["Customer Success", "Product", "Sales"]
        },
        {
            "problem": "Onboarding friction",
            "frequency": "high",
            "typical_triggers": ["Low activation rate", "Time to value too long"],
            "stakeholders": ["Product", "Customer Success", "Engineering"]
        },
        {
            "problem": "Feature adoption",
            "frequency": "high",
            "typical_triggers": ["New features unused", "Product-led growth stalls"],
            "stakeholders": ["Product", "Marketing", "Customer Success"]
        }
    ]'::jsonb,
    '{"source": "DI Agent seed data", "confidence": 0.9}'::jsonb
)
ON CONFLICT (vertical, category) DO NOTHING;

-- Nonprofit common problems
INSERT INTO vertical_knowledge (vertical, category, content, metadata)
VALUES (
    'nonprofit',
    'common_problems',
    '[
        {
            "problem": "Donor retention and engagement",
            "frequency": "very_high",
            "typical_triggers": ["Donors lapse", "Giving down", "Lost major donors"],
            "stakeholders": ["Development Director", "Board", "Executive Director"]
        },
        {
            "problem": "Impact measurement and reporting",
            "frequency": "high",
            "typical_triggers": ["Grant reporting burden", "Board wants data", "Funders ask for outcomes"],
            "stakeholders": ["Program Director", "Development", "Executive Director"]
        },
        {
            "problem": "Volunteer coordination",
            "frequency": "medium",
            "typical_triggers": ["Manual spreadsheets", "No-shows", "Communication gaps"],
            "stakeholders": ["Volunteer Coordinator", "Program Staff"]
        }
    ]'::jsonb,
    '{"source": "DI Agent seed data", "confidence": 0.9}'::jsonb
)
ON CONFLICT (vertical, category) DO NOTHING;

-- SaaS stakeholder patterns
INSERT INTO vertical_knowledge (vertical, category, content, metadata)
VALUES (
    'SaaS',
    'stakeholder_patterns',
    '[
        {
            "role": "Customer Success Manager",
            "typical_concerns": ["Churn risk", "Usage metrics", "Customer health scores"],
            "decision_influence": "medium",
            "likely_champion": true
        },
        {
            "role": "VP Product",
            "typical_concerns": ["Feature adoption", "Product-market fit", "Roadmap priorities"],
            "decision_influence": "high",
            "likely_champion": false
        },
        {
            "role": "Head of Sales",
            "typical_concerns": ["Deal velocity", "Win rates", "Sales enablement"],
            "decision_influence": "medium",
            "likely_champion": false
        }
    ]'::jsonb,
    '{"source": "DI Agent seed data", "confidence": 0.85}'::jsonb
)
ON CONFLICT (vertical, category) DO NOTHING;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify tables were created
DO $$
BEGIN
    ASSERT (SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name IN ('project_foundation', 'di_analysis_cache', 'di_agent_logs', 'vertical_knowledge')) = 4,
           'Not all DI foundation tables were created';

    RAISE NOTICE 'DI Foundation tables created successfully';
END $$;
