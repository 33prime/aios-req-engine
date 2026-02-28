-- Epic confirmation tracking for prototype review tours.
-- Replaces per-feature verdicts with per-epic/card confirmations.

CREATE TABLE prototype_epic_confirmations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES prototype_sessions(id) ON DELETE CASCADE,
    card_type TEXT NOT NULL CHECK (card_type IN ('vision', 'ai_flow', 'horizon', 'discovery')),
    card_index INT NOT NULL,
    verdict TEXT CHECK (verdict IS NULL OR verdict IN ('confirmed', 'refine', 'client_review')),
    notes TEXT,
    answer TEXT,
    source TEXT NOT NULL DEFAULT 'consultant' CHECK (source IN ('consultant', 'client')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(session_id, card_type, card_index, source)
);

CREATE INDEX idx_epic_conf_session ON prototype_epic_confirmations(session_id);
