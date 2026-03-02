-- Call Intelligence: recording pipeline, transcription, analysis, insights
-- Recall.ai (with video) -> Deepgram nova-2 (speaker diarization) -> Claude analysis

-- ============================================================================
-- 1. call_recordings — Recording metadata + 8-state status machine
-- ============================================================================
CREATE TABLE IF NOT EXISTS call_recordings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    meeting_id UUID REFERENCES meetings(id) ON DELETE SET NULL,
    recall_bot_id TEXT,
    meeting_bot_id UUID REFERENCES meeting_bots(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN (
            'pending', 'bot_scheduled', 'recording', 'transcribing',
            'analyzing', 'complete', 'skipped', 'failed'
        )),
    audio_url TEXT,
    video_url TEXT,
    recording_url TEXT,
    duration_seconds INTEGER,
    signal_id UUID,
    error_message TEXT,
    error_step TEXT,
    deployed_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_call_recordings_project ON call_recordings(project_id);
CREATE INDEX idx_call_recordings_meeting ON call_recordings(meeting_id);
CREATE INDEX idx_call_recordings_recall_bot ON call_recordings(recall_bot_id);
CREATE INDEX idx_call_recordings_status ON call_recordings(status);

-- updated_at trigger
CREATE OR REPLACE FUNCTION update_call_recordings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS call_recordings_updated_at ON call_recordings;
CREATE TRIGGER call_recordings_updated_at
    BEFORE UPDATE ON call_recordings
    FOR EACH ROW
    EXECUTE FUNCTION update_call_recordings_updated_at();

-- RLS
ALTER TABLE call_recordings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "call_recordings_authenticated" ON call_recordings
    FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY "call_recordings_service" ON call_recordings
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ============================================================================
-- 2. call_transcripts — Full text + speaker-diarized segments
-- ============================================================================
CREATE TABLE IF NOT EXISTS call_transcripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recording_id UUID NOT NULL UNIQUE REFERENCES call_recordings(id) ON DELETE CASCADE,
    full_text TEXT NOT NULL DEFAULT '',
    segments JSONB NOT NULL DEFAULT '[]',
    speaker_map JSONB NOT NULL DEFAULT '{}',
    word_count INTEGER NOT NULL DEFAULT 0,
    language TEXT DEFAULT 'en',
    provider TEXT DEFAULT 'deepgram',
    model TEXT DEFAULT 'nova-2',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_call_transcripts_recording ON call_transcripts(recording_id);

CREATE OR REPLACE FUNCTION update_call_transcripts_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS call_transcripts_updated_at ON call_transcripts;
CREATE TRIGGER call_transcripts_updated_at
    BEFORE UPDATE ON call_transcripts
    FOR EACH ROW
    EXECUTE FUNCTION update_call_transcripts_updated_at();

ALTER TABLE call_transcripts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "call_transcripts_authenticated" ON call_transcripts
    FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY "call_transcripts_service" ON call_transcripts
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ============================================================================
-- 3. call_analyses — Scores + timeline + summary
-- ============================================================================
CREATE TABLE IF NOT EXISTS call_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recording_id UUID NOT NULL UNIQUE REFERENCES call_recordings(id) ON DELETE CASCADE,
    engagement_score FLOAT,
    talk_ratio JSONB DEFAULT '{}',
    engagement_timeline JSONB DEFAULT '[]',
    executive_summary TEXT,
    custom_dimensions JSONB DEFAULT '{}',
    dimension_packs_used TEXT[] DEFAULT '{}',
    model TEXT,
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_call_analyses_recording ON call_analyses(recording_id);

CREATE OR REPLACE FUNCTION update_call_analyses_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS call_analyses_updated_at ON call_analyses;
CREATE TRIGGER call_analyses_updated_at
    BEFORE UPDATE ON call_analyses
    FOR EACH ROW
    EXECUTE FUNCTION update_call_analyses_updated_at();

ALTER TABLE call_analyses ENABLE ROW LEVEL SECURITY;
CREATE POLICY "call_analyses_authenticated" ON call_analyses
    FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY "call_analyses_service" ON call_analyses
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ============================================================================
-- 4. call_feature_insights — Feature reactions + quotes
-- ============================================================================
CREATE TABLE IF NOT EXISTS call_feature_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recording_id UUID NOT NULL REFERENCES call_recordings(id) ON DELETE CASCADE,
    feature_id UUID REFERENCES features(id) ON DELETE SET NULL,
    feature_name TEXT NOT NULL,
    reaction TEXT NOT NULL DEFAULT 'neutral'
        CHECK (reaction IN ('excited', 'interested', 'neutral', 'confused', 'resistant')),
    quote TEXT,
    context TEXT,
    timestamp_seconds INTEGER,
    is_aha_moment BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_call_feature_insights_recording ON call_feature_insights(recording_id);
CREATE INDEX idx_call_feature_insights_feature ON call_feature_insights(feature_id);

CREATE OR REPLACE FUNCTION update_call_feature_insights_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS call_feature_insights_updated_at ON call_feature_insights;
CREATE TRIGGER call_feature_insights_updated_at
    BEFORE UPDATE ON call_feature_insights
    FOR EACH ROW
    EXECUTE FUNCTION update_call_feature_insights_updated_at();

ALTER TABLE call_feature_insights ENABLE ROW LEVEL SECURITY;
CREATE POLICY "call_feature_insights_authenticated" ON call_feature_insights
    FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY "call_feature_insights_service" ON call_feature_insights
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ============================================================================
-- 5. call_signals — ICP/market signals (distinct from AIOS signals table)
-- ============================================================================
CREATE TABLE IF NOT EXISTS call_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recording_id UUID NOT NULL REFERENCES call_recordings(id) ON DELETE CASCADE,
    signal_type TEXT NOT NULL
        CHECK (signal_type IN (
            'pain_point', 'goal', 'budget_indicator',
            'timeline', 'decision_criteria', 'risk_factor'
        )),
    title TEXT NOT NULL,
    description TEXT,
    intensity FLOAT DEFAULT 0.5,
    quote TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_call_signals_recording ON call_signals(recording_id);
CREATE INDEX idx_call_signals_type ON call_signals(signal_type);

CREATE OR REPLACE FUNCTION update_call_signals_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS call_signals_updated_at ON call_signals;
CREATE TRIGGER call_signals_updated_at
    BEFORE UPDATE ON call_signals
    FOR EACH ROW
    EXECUTE FUNCTION update_call_signals_updated_at();

ALTER TABLE call_signals ENABLE ROW LEVEL SECURITY;
CREATE POLICY "call_signals_authenticated" ON call_signals
    FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY "call_signals_service" ON call_signals
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ============================================================================
-- 6. call_content_nuggets — Reusable content extracts
-- ============================================================================
CREATE TABLE IF NOT EXISTS call_content_nuggets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recording_id UUID NOT NULL REFERENCES call_recordings(id) ON DELETE CASCADE,
    nugget_type TEXT NOT NULL
        CHECK (nugget_type IN (
            'testimonial', 'soundbite', 'statistic',
            'use_case', 'objection', 'vision_statement'
        )),
    content TEXT NOT NULL,
    speaker TEXT,
    reuse_score FLOAT DEFAULT 0.5,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_call_content_nuggets_recording ON call_content_nuggets(recording_id);
CREATE INDEX idx_call_content_nuggets_type ON call_content_nuggets(nugget_type);

CREATE OR REPLACE FUNCTION update_call_content_nuggets_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS call_content_nuggets_updated_at ON call_content_nuggets;
CREATE TRIGGER call_content_nuggets_updated_at
    BEFORE UPDATE ON call_content_nuggets
    FOR EACH ROW
    EXECUTE FUNCTION update_call_content_nuggets_updated_at();

ALTER TABLE call_content_nuggets ENABLE ROW LEVEL SECURITY;
CREATE POLICY "call_content_nuggets_authenticated" ON call_content_nuggets
    FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY "call_content_nuggets_service" ON call_content_nuggets
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ============================================================================
-- 7. call_competitive_mentions — Competitor tracking
-- ============================================================================
CREATE TABLE IF NOT EXISTS call_competitive_mentions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recording_id UUID NOT NULL REFERENCES call_recordings(id) ON DELETE CASCADE,
    competitor_name TEXT NOT NULL,
    sentiment TEXT DEFAULT 'neutral'
        CHECK (sentiment IN ('positive', 'neutral', 'negative')),
    context TEXT,
    quote TEXT,
    feature_comparison TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_call_competitive_mentions_recording ON call_competitive_mentions(recording_id);

CREATE OR REPLACE FUNCTION update_call_competitive_mentions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS call_competitive_mentions_updated_at ON call_competitive_mentions;
CREATE TRIGGER call_competitive_mentions_updated_at
    BEFORE UPDATE ON call_competitive_mentions
    FOR EACH ROW
    EXECUTE FUNCTION update_call_competitive_mentions_updated_at();

ALTER TABLE call_competitive_mentions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "call_competitive_mentions_authenticated" ON call_competitive_mentions
    FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY "call_competitive_mentions_service" ON call_competitive_mentions
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ============================================================================
-- 8. Backlink: meetings -> call_recordings
-- ============================================================================
ALTER TABLE meetings ADD COLUMN IF NOT EXISTS call_recording_id UUID
    REFERENCES call_recordings(id) ON DELETE SET NULL;
