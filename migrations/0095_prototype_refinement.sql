-- Prototype Refinement System
-- Adds tables for prototype generation, feature overlay analysis,
-- review sessions, feedback collection, and cross-project prompt learnings.

-- Prototypes
CREATE TABLE prototypes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    repo_url TEXT,
    deploy_url TEXT,
    local_path TEXT,
    handoff_parsed JSONB,
    status TEXT NOT NULL DEFAULT 'pending',
    prompt_text TEXT,
    prompt_audit JSONB,
    prompt_version INT DEFAULT 1,
    session_count INT DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_prototypes_project ON prototypes(project_id);

-- Feature overlay analysis results
CREATE TABLE prototype_feature_overlays (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prototype_id UUID NOT NULL REFERENCES prototypes(id) ON DELETE CASCADE,
    feature_id UUID REFERENCES features(id) ON DELETE SET NULL,
    code_file_path TEXT,
    component_name TEXT,
    handoff_feature_name TEXT,
    analysis JSONB NOT NULL,
    overlay_content JSONB,
    status TEXT NOT NULL DEFAULT 'unknown',
    gaps_count INT DEFAULT 0,
    confidence NUMERIC(3,2) DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_overlays_prototype ON prototype_feature_overlays(prototype_id);
CREATE INDEX idx_overlays_feature ON prototype_feature_overlays(feature_id);

-- Questions generated per overlay feature
CREATE TABLE prototype_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    overlay_id UUID NOT NULL REFERENCES prototype_feature_overlays(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    category TEXT,
    priority TEXT DEFAULT 'medium',
    answer TEXT,
    answered_in_session INT,
    answered_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_questions_overlay ON prototype_questions(overlay_id);

-- Review sessions
CREATE TABLE prototype_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prototype_id UUID NOT NULL REFERENCES prototypes(id) ON DELETE CASCADE,
    session_number INT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    consultant_id UUID,
    client_review_token TEXT UNIQUE,
    readiness_before NUMERIC(5,2),
    readiness_after NUMERIC(5,2),
    synthesis JSONB,
    code_update_plan JSONB,
    code_update_result JSONB,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(prototype_id, session_number)
);
CREATE INDEX idx_sessions_prototype ON prototype_sessions(prototype_id);
CREATE INDEX idx_sessions_token ON prototype_sessions(client_review_token);

-- Feedback from consultant and client
CREATE TABLE prototype_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES prototype_sessions(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    feature_id UUID REFERENCES features(id),
    page_path TEXT,
    component_name TEXT,
    feedback_type TEXT,
    content TEXT NOT NULL,
    context JSONB,
    affects_features TEXT[],
    answers_question_id UUID,
    priority TEXT DEFAULT 'medium',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_feedback_session ON prototype_feedback(session_id);
CREATE INDEX idx_feedback_feature ON prototype_feedback(feature_id);

-- Cross-project prompt learnings
CREATE TABLE prompt_template_learnings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category TEXT NOT NULL,
    learning TEXT NOT NULL,
    source_prototype_id UUID REFERENCES prototypes(id),
    effectiveness_score NUMERIC(3,2),
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
