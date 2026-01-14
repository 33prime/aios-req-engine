-- Migration: 0064_rls_helper_functions.sql
-- Description: Create RLS helper functions for role-based access control
-- Date: 2026-01-14

-- ============================================================================
-- Helper function: Get current user's platform role
-- Returns the platform_role from profiles table, defaults to 'sales_consultant'
-- ============================================================================
CREATE OR REPLACE FUNCTION get_my_platform_role()
RETURNS TEXT AS $$
  SELECT COALESCE(
    (SELECT platform_role FROM profiles WHERE user_id = auth.uid()),
    'sales_consultant'
  );
$$ LANGUAGE sql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION get_my_platform_role() IS
  'Returns the current user''s platform role (super_admin, solution_architect, or sales_consultant)';

-- ============================================================================
-- Helper function: Check if current user is a super admin
-- ============================================================================
CREATE OR REPLACE FUNCTION is_super_admin()
RETURNS BOOLEAN AS $$
  SELECT get_my_platform_role() = 'super_admin';
$$ LANGUAGE sql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION is_super_admin() IS
  'Returns true if the current user is a super_admin (god mode)';

-- ============================================================================
-- Helper function: Get organizations current user can access
-- Returns array of organization UUIDs based on:
-- - Super admins: all organizations
-- - Solution architects: direct memberships + assigned orgs
-- - Sales consultants: direct memberships only
-- ============================================================================
CREATE OR REPLACE FUNCTION get_my_organizations()
RETURNS UUID[] AS $$
DECLARE
  platform_role TEXT;
  org_ids UUID[];
BEGIN
  -- Get user's platform role
  SELECT get_my_platform_role() INTO platform_role;

  -- Super admins see all non-deleted organizations
  IF platform_role = 'super_admin' THEN
    SELECT ARRAY_AGG(id) INTO org_ids
    FROM organizations
    WHERE deleted_at IS NULL;
    RETURN COALESCE(org_ids, '{}');
  END IF;

  -- For solution architects: get direct memberships + assigned orgs
  IF platform_role = 'solution_architect' THEN
    SELECT ARRAY_AGG(DISTINCT org_id) INTO org_ids
    FROM (
      -- Direct memberships
      SELECT organization_id AS org_id
      FROM organization_members
      WHERE user_id = auth.uid()
      UNION
      -- Solution architect assignments
      SELECT organization_id AS org_id
      FROM solution_architect_assignments
      WHERE user_id = auth.uid()
    ) combined;
    RETURN COALESCE(org_ids, '{}');
  END IF;

  -- For sales consultants (default): only direct memberships
  SELECT ARRAY_AGG(organization_id) INTO org_ids
  FROM organization_members
  WHERE user_id = auth.uid();

  RETURN COALESCE(org_ids, '{}');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION get_my_organizations() IS
  'Returns array of organization UUIDs the current user can access';

-- ============================================================================
-- Helper function: Get user's role in a specific organization
-- Returns the organization_role (Owner, Admin, Member) or NULL if not a member
-- ============================================================================
CREATE OR REPLACE FUNCTION get_my_org_role(org_id UUID)
RETURNS TEXT AS $$
  SELECT organization_role
  FROM organization_members
  WHERE user_id = auth.uid() AND organization_id = org_id;
$$ LANGUAGE sql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION get_my_org_role(UUID) IS
  'Returns the current user''s role in the specified organization';

-- ============================================================================
-- Helper function: Check if user can access a specific organization
-- Returns true if user is super_admin OR has access to the org
-- ============================================================================
CREATE OR REPLACE FUNCTION can_access_organization(org_id UUID)
RETURNS BOOLEAN AS $$
  SELECT is_super_admin() OR org_id = ANY(get_my_organizations());
$$ LANGUAGE sql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION can_access_organization(UUID) IS
  'Returns true if the current user can access the specified organization';

-- ============================================================================
-- Helper function: Check if user can access a specific project
-- Returns true if:
-- - User is super_admin, OR
-- - Project's organization is accessible, OR
-- - User is a direct project member
-- ============================================================================
CREATE OR REPLACE FUNCTION can_access_project(proj_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
  proj_org_id UUID;
BEGIN
  -- Super admins can access everything
  IF is_super_admin() THEN
    RETURN TRUE;
  END IF;

  -- Get the project's organization
  SELECT organization_id INTO proj_org_id
  FROM projects
  WHERE id = proj_id;

  -- Check if user can access the project's organization
  IF proj_org_id IS NOT NULL AND proj_org_id = ANY(get_my_organizations()) THEN
    RETURN TRUE;
  END IF;

  -- Check if user is a direct project member
  RETURN EXISTS (
    SELECT 1
    FROM project_members
    WHERE project_id = proj_id AND user_id = auth.uid()
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION can_access_project(UUID) IS
  'Returns true if the current user can access the specified project';

-- ============================================================================
-- Helper function: Get user's role in a specific project
-- Returns 'consultant' or 'client' based on project_members, or NULL
-- ============================================================================
CREATE OR REPLACE FUNCTION get_my_project_role(proj_id UUID)
RETURNS TEXT AS $$
  SELECT role
  FROM project_members
  WHERE project_id = proj_id AND user_id = auth.uid();
$$ LANGUAGE sql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION get_my_project_role(UUID) IS
  'Returns the current user''s role in the specified project (consultant or client)';

-- ============================================================================
-- Helper function: Get user's client role in a specific project
-- Returns 'decision_maker' or 'support' for clients, NULL for consultants
-- ============================================================================
CREATE OR REPLACE FUNCTION get_my_client_role(proj_id UUID)
RETURNS TEXT AS $$
  SELECT client_role
  FROM project_members
  WHERE project_id = proj_id AND user_id = auth.uid() AND role = 'client';
$$ LANGUAGE sql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION get_my_client_role(UUID) IS
  'Returns the current user''s client role in the specified project (decision_maker or support)';

-- ============================================================================
-- Helper function: Check if user is a consultant on a project
-- ============================================================================
CREATE OR REPLACE FUNCTION is_project_consultant(proj_id UUID)
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1
    FROM project_members
    WHERE project_id = proj_id
      AND user_id = auth.uid()
      AND role = 'consultant'
  );
$$ LANGUAGE sql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION is_project_consultant(UUID) IS
  'Returns true if the current user is a consultant on the specified project';

-- ============================================================================
-- Helper function: Check if user is org owner or admin
-- ============================================================================
CREATE OR REPLACE FUNCTION is_org_admin_or_owner(org_id UUID)
RETURNS BOOLEAN AS $$
  SELECT is_super_admin() OR get_my_org_role(org_id) IN ('Owner', 'Admin');
$$ LANGUAGE sql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION is_org_admin_or_owner(UUID) IS
  'Returns true if the current user is an owner or admin of the specified organization';

-- ============================================================================
-- Legacy compatibility function
-- Returns 'admin' for super_admins, 'user' for everyone else
-- ============================================================================
CREATE OR REPLACE FUNCTION get_user_role()
RETURNS TEXT AS $$
  SELECT CASE
    WHEN get_my_platform_role() = 'super_admin' THEN 'admin'
    ELSE 'user'
  END;
$$ LANGUAGE sql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION get_user_role() IS
  'Legacy: Returns ''admin'' for super_admins, ''user'' for everyone else';
