-- Migration: 0063_auth_role_updates.sql
-- Description: Update platform roles, add solution architect assignments, consultant invites, and client roles
-- Date: 2026-01-14

-- ============================================================================
-- 1. Update platform_role enum in profiles table
-- ============================================================================
-- Drop old constraint and add new one with updated roles
ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_platform_role_check;
ALTER TABLE profiles ADD CONSTRAINT profiles_platform_role_check
  CHECK (platform_role IN ('super_admin', 'solution_architect', 'sales_consultant'));

-- ============================================================================
-- 2. Migrate existing data to new role names
-- ============================================================================
-- Map old 'user' role to 'sales_consultant' (default role)
UPDATE profiles SET platform_role = 'sales_consultant' WHERE platform_role = 'user';
-- Map old 'admin' role to 'solution_architect'
UPDATE profiles SET platform_role = 'solution_architect' WHERE platform_role = 'admin';
-- super_admin stays as super_admin (no change needed)

-- ============================================================================
-- 3. Create solution_architect_assignments table
-- Allows solution architects to be assigned to organizations they don't directly belong to
-- ============================================================================
CREATE TABLE IF NOT EXISTS solution_architect_assignments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  assigned_by UUID REFERENCES users(id) ON DELETE SET NULL,
  assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(user_id, organization_id)
);

CREATE INDEX IF NOT EXISTS idx_sa_assignments_user_id ON solution_architect_assignments(user_id);
CREATE INDEX IF NOT EXISTS idx_sa_assignments_org_id ON solution_architect_assignments(organization_id);

-- ============================================================================
-- 4. Add client_role to project_members
-- Allows distinguishing between decision makers and support staff for clients
-- ============================================================================
ALTER TABLE project_members ADD COLUMN IF NOT EXISTS client_role TEXT
  CHECK (client_role IS NULL OR client_role IN ('decision_maker', 'support'));

-- Add index for filtering by client role
CREATE INDEX IF NOT EXISTS idx_project_members_client_role ON project_members(project_id, client_role)
  WHERE client_role IS NOT NULL;

-- ============================================================================
-- 5. Create consultant_invites table
-- Tracks invitations for new consultants (invite-only signup)
-- ============================================================================
CREATE TABLE IF NOT EXISTS consultant_invites (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL,
  platform_role TEXT NOT NULL CHECK (platform_role IN ('solution_architect', 'sales_consultant')),
  organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
  invited_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  invite_token TEXT NOT NULL UNIQUE DEFAULT gen_random_uuid()::TEXT,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'expired', 'cancelled')),
  first_name TEXT,
  last_name TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '7 days'),
  accepted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_consultant_invites_email ON consultant_invites(email);
CREATE INDEX IF NOT EXISTS idx_consultant_invites_token ON consultant_invites(invite_token);
CREATE INDEX IF NOT EXISTS idx_consultant_invites_status ON consultant_invites(status);
CREATE INDEX IF NOT EXISTS idx_consultant_invites_invited_by ON consultant_invites(invited_by);

-- ============================================================================
-- 6. Update users table to distinguish consultant vs client more clearly
-- ============================================================================
-- Add is_consultant column for faster filtering (denormalized for performance)
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_consultant BOOLEAN DEFAULT FALSE;

-- Update existing users based on user_type
UPDATE users SET is_consultant = TRUE WHERE user_type = 'consultant';
UPDATE users SET is_consultant = FALSE WHERE user_type = 'client';

-- Index for consultant filtering
CREATE INDEX IF NOT EXISTS idx_users_is_consultant ON users(is_consultant);

-- ============================================================================
-- Comments for documentation
-- ============================================================================
COMMENT ON TABLE solution_architect_assignments IS 'Tracks which organizations a solution architect is assigned to (beyond their direct memberships)';
COMMENT ON TABLE consultant_invites IS 'Invitation records for new consultants - invite-only signup flow';
COMMENT ON COLUMN project_members.client_role IS 'For clients: decision_maker has full access, support has limited access';
COMMENT ON COLUMN users.is_consultant IS 'Denormalized flag for quick consultant vs client filtering';
