-- Meetings table for tracking project meetings
-- Used in dashboard for upcoming meetings and meeting management

-- Create enum types
DO $$ BEGIN
    CREATE TYPE meeting_type_enum AS ENUM ('discovery', 'validation', 'review', 'other');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE meeting_status_enum AS ENUM ('scheduled', 'completed', 'cancelled');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create meetings table
CREATE TABLE IF NOT EXISTS public.meetings (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Core fields
    title text NOT NULL,
    description text,
    meeting_type meeting_type_enum NOT NULL DEFAULT 'other',
    status meeting_status_enum NOT NULL DEFAULT 'scheduled',

    -- Scheduling
    meeting_date date NOT NULL,
    meeting_time time NOT NULL,
    duration_minutes integer NOT NULL DEFAULT 60,
    timezone text NOT NULL DEFAULT 'UTC',

    -- Participants (references stakeholders table)
    stakeholder_ids uuid[] DEFAULT '{}',

    -- Content (populated after meeting or for agenda)
    agenda jsonb,
    summary text,
    highlights jsonb,

    -- Calendar integration (for later)
    google_calendar_event_id text,
    google_meet_link text,

    -- Metadata
    created_by uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_meetings_project_id ON meetings(project_id);
CREATE INDEX IF NOT EXISTS idx_meetings_date ON meetings(meeting_date);
CREATE INDEX IF NOT EXISTS idx_meetings_status ON meetings(status);
CREATE INDEX IF NOT EXISTS idx_meetings_upcoming ON meetings(meeting_date, meeting_time)
    WHERE status = 'scheduled';

-- Trigger for updated_at
DROP TRIGGER IF EXISTS set_meetings_updated_at ON meetings;
CREATE TRIGGER set_meetings_updated_at
    BEFORE UPDATE ON meetings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
