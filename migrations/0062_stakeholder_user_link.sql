-- Migration: Stakeholder User Link
-- Description: Link stakeholders to users and project members
-- Date: 2025-01-14

-- =========================
-- Add user/member linking columns to stakeholders
-- =========================

ALTER TABLE stakeholders
ADD COLUMN IF NOT EXISTS linked_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS linked_project_member_id UUID REFERENCES project_members(id) ON DELETE SET NULL;

-- Indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_stakeholders_user
    ON stakeholders(linked_user_id) WHERE linked_user_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_stakeholders_member
    ON stakeholders(linked_project_member_id) WHERE linked_project_member_id IS NOT NULL;

-- =========================
-- Auto-link function: Match stakeholder email to user
-- =========================

CREATE OR REPLACE FUNCTION auto_link_stakeholder_to_user()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- If stakeholder has email and no linked_user_id, try to find matching user
    IF NEW.email IS NOT NULL AND NEW.linked_user_id IS NULL THEN
        SELECT id INTO NEW.linked_user_id
        FROM users
        WHERE LOWER(email) = LOWER(NEW.email)
        LIMIT 1;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_auto_link_stakeholder ON stakeholders;
CREATE TRIGGER trg_auto_link_stakeholder
    BEFORE INSERT OR UPDATE OF email ON stakeholders
    FOR EACH ROW
    EXECUTE FUNCTION auto_link_stakeholder_to_user();

-- =========================
-- Comments
-- =========================

COMMENT ON COLUMN stakeholders.linked_user_id IS 'Link to users table if stakeholder has a system account';
COMMENT ON COLUMN stakeholders.linked_project_member_id IS 'Link to project_members table if stakeholder is on project team';

COMMENT ON FUNCTION auto_link_stakeholder_to_user IS 'Auto-links stakeholder to user by email match';
