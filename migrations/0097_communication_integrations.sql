-- Communication integrations: Google OAuth, email routing, meeting recording bots
-- Supports email capture (SendGrid), meeting recording (Recall.ai), calendar sync

-- communication_integrations: OAuth state and preferences per user
CREATE TABLE IF NOT EXISTS public.communication_integrations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider text NOT NULL DEFAULT 'google',

    -- OAuth tokens (encrypted at rest via application layer)
    google_refresh_token_encrypted text,
    scopes_granted text[] DEFAULT '{}',

    -- Calendar sync
    calendar_sync_enabled boolean NOT NULL DEFAULT false,
    calendar_watch_channel_id text,
    calendar_watch_expiration timestamptz,

    -- Recording preferences: 'on' = always record, 'off' = never, 'ask' = prompt per meeting
    recording_default text NOT NULL DEFAULT 'off'
        CHECK (recording_default IN ('on', 'off', 'ask')),

    -- Metadata
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),

    UNIQUE(user_id, provider)
);

CREATE INDEX IF NOT EXISTS idx_comm_integrations_user_id
    ON communication_integrations(user_id);
CREATE INDEX IF NOT EXISTS idx_comm_integrations_calendar_sync
    ON communication_integrations(user_id)
    WHERE calendar_sync_enabled = true;

-- Trigger for updated_at
DROP TRIGGER IF EXISTS set_comm_integrations_updated_at ON communication_integrations;
CREATE TRIGGER set_comm_integrations_updated_at
    BEFORE UPDATE ON communication_integrations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- email_routing_tokens: reply-to address -> project mapping with TTL
CREATE TABLE IF NOT EXISTS public.email_routing_tokens (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Routing token (used as local part of reply-to address)
    token text NOT NULL UNIQUE DEFAULT gen_random_uuid()::text,

    -- Sender restrictions
    allowed_sender_domain text,
    allowed_sender_emails text[] DEFAULT '{}',

    -- TTL and rate limiting
    expires_at timestamptz NOT NULL DEFAULT (now() + interval '7 days'),
    is_active boolean NOT NULL DEFAULT true,
    emails_received integer NOT NULL DEFAULT 0,
    max_emails integer NOT NULL DEFAULT 100,

    -- Metadata
    created_by uuid REFERENCES auth.users(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_email_routing_token ON email_routing_tokens(token)
    WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_email_routing_project ON email_routing_tokens(project_id);

-- Trigger for updated_at
DROP TRIGGER IF EXISTS set_email_routing_tokens_updated_at ON email_routing_tokens;
CREATE TRIGGER set_email_routing_tokens_updated_at
    BEFORE UPDATE ON email_routing_tokens
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- meeting_bots: Recall.ai bot lifecycle tracking
CREATE TABLE IF NOT EXISTS public.meeting_bots (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id uuid NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,

    -- Recall.ai integration
    recall_bot_id text NOT NULL,
    status text NOT NULL DEFAULT 'deploying'
        CHECK (status IN ('deploying', 'joining', 'recording', 'processing', 'done', 'failed', 'cancelled')),

    -- Linked signal (set when transcript is ingested)
    signal_id uuid REFERENCES signals(id) ON DELETE SET NULL,

    -- Artifacts
    transcript_url text,
    recording_url text,

    -- Consent tracking
    consent_status text NOT NULL DEFAULT 'pending'
        CHECK (consent_status IN ('pending', 'all_consented', 'opted_out', 'expired')),
    consent_emails_sent_at timestamptz,
    opt_out_deadline timestamptz,
    participants_notified text[] DEFAULT '{}',
    participants_opted_out text[] DEFAULT '{}',

    -- Error handling
    error_message text,

    -- Metadata
    deployed_by uuid REFERENCES auth.users(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_meeting_bots_meeting ON meeting_bots(meeting_id);
CREATE INDEX IF NOT EXISTS idx_meeting_bots_recall ON meeting_bots(recall_bot_id);
CREATE INDEX IF NOT EXISTS idx_meeting_bots_status ON meeting_bots(status)
    WHERE status NOT IN ('done', 'failed', 'cancelled');

-- Trigger for updated_at
DROP TRIGGER IF EXISTS set_meeting_bots_updated_at ON meeting_bots;
CREATE TRIGGER set_meeting_bots_updated_at
    BEFORE UPDATE ON meeting_bots
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- Extend meetings table with recording columns
ALTER TABLE meetings ADD COLUMN IF NOT EXISTS recall_bot_id text;
ALTER TABLE meetings ADD COLUMN IF NOT EXISTS recording_enabled boolean DEFAULT false;
ALTER TABLE meetings ADD COLUMN IF NOT EXISTS recording_consent_status text DEFAULT 'none';
