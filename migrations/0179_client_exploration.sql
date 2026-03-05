-- Client Portal v2: Assumption-based pre-call exploration
-- Adds per-epic config (assumptions, consultant notes, visibility) and
-- client interaction tables for assumption responses, inspirations, and analytics.

-- Per-epic config stored as JSONB on prototype_sessions
ALTER TABLE prototype_sessions
  ADD COLUMN IF NOT EXISTS epic_configs JSONB DEFAULT '[]';

-- Client assumption responses (thumbs up/down per assumption)
CREATE TABLE client_assumption_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES prototype_sessions(id) ON DELETE CASCADE,
    epic_index INT NOT NULL,
    assumption_index INT NOT NULL,
    response TEXT NOT NULL CHECK (response IN ('agree', 'disagree')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(session_id, epic_index, assumption_index)
);

-- Client inspirations ("new ideas" captured during exploration)
CREATE TABLE client_inspirations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES prototype_sessions(id) ON DELETE CASCADE,
    epic_index INT,  -- NULL = general inspiration
    text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Client exploration events (passive analytics: time per epic, navigation)
CREATE TABLE client_exploration_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES prototype_sessions(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,  -- 'epic_view', 'epic_leave', 'prototype_click', 'session_start', 'session_end'
    epic_index INT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_assumption_resp_session ON client_assumption_responses(session_id);
CREATE INDEX idx_inspirations_session ON client_inspirations(session_id);
CREATE INDEX idx_exploration_events_session ON client_exploration_events(session_id);

-- Extend review_state to include client exploration states
ALTER TABLE prototype_sessions
  DROP CONSTRAINT IF EXISTS prototype_sessions_review_state_check;

ALTER TABLE prototype_sessions
  ADD CONSTRAINT prototype_sessions_review_state_check
  CHECK (review_state IN (
    'not_started','in_progress','complete','updating','re_review',
    'ready_for_client','staging','client_exploring','client_complete'
  ));
