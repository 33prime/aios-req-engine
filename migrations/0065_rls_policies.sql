-- Migration: 0065_rls_policies.sql
-- Description: Enable RLS and create access policies for all tables (safe version)
-- Date: 2026-01-14

-- ============================================================================
-- ORGANIZATIONS TABLE
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'organizations' AND table_schema = 'public') THEN
    ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS organizations_select ON organizations;
    DROP POLICY IF EXISTS organizations_insert ON organizations;
    DROP POLICY IF EXISTS organizations_update ON organizations;
    DROP POLICY IF EXISTS organizations_delete ON organizations;

    CREATE POLICY organizations_select ON organizations FOR SELECT
      USING (is_super_admin() OR id = ANY(get_my_organizations()));
    CREATE POLICY organizations_insert ON organizations FOR INSERT
      WITH CHECK (is_super_admin() OR auth.uid() = created_by_user_id);
    CREATE POLICY organizations_update ON organizations FOR UPDATE
      USING (is_org_admin_or_owner(id));
    CREATE POLICY organizations_delete ON organizations FOR DELETE
      USING (is_super_admin() OR get_my_org_role(id) = 'Owner');
  END IF;
END $$;

-- ============================================================================
-- ORGANIZATION_MEMBERS TABLE
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'organization_members' AND table_schema = 'public') THEN
    ALTER TABLE organization_members ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS organization_members_select ON organization_members;
    DROP POLICY IF EXISTS organization_members_insert ON organization_members;
    DROP POLICY IF EXISTS organization_members_update ON organization_members;
    DROP POLICY IF EXISTS organization_members_delete ON organization_members;

    CREATE POLICY organization_members_select ON organization_members FOR SELECT
      USING (can_access_organization(organization_id));
    CREATE POLICY organization_members_insert ON organization_members FOR INSERT
      WITH CHECK (is_org_admin_or_owner(organization_id));
    CREATE POLICY organization_members_update ON organization_members FOR UPDATE
      USING (is_org_admin_or_owner(organization_id));
    CREATE POLICY organization_members_delete ON organization_members FOR DELETE
      USING (is_org_admin_or_owner(organization_id));
  END IF;
END $$;

-- ============================================================================
-- ORGANIZATION_INVITATIONS TABLE
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'organization_invitations' AND table_schema = 'public') THEN
    ALTER TABLE organization_invitations ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS organization_invitations_select ON organization_invitations;
    DROP POLICY IF EXISTS organization_invitations_insert ON organization_invitations;
    DROP POLICY IF EXISTS organization_invitations_update ON organization_invitations;
    DROP POLICY IF EXISTS organization_invitations_delete ON organization_invitations;

    CREATE POLICY organization_invitations_select ON organization_invitations FOR SELECT
      USING (is_org_admin_or_owner(organization_id));
    CREATE POLICY organization_invitations_insert ON organization_invitations FOR INSERT
      WITH CHECK (is_org_admin_or_owner(organization_id));
    CREATE POLICY organization_invitations_update ON organization_invitations FOR UPDATE
      USING (is_org_admin_or_owner(organization_id));
    CREATE POLICY organization_invitations_delete ON organization_invitations FOR DELETE
      USING (is_org_admin_or_owner(organization_id));
  END IF;
END $$;

-- ============================================================================
-- PROFILES TABLE
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'profiles' AND table_schema = 'public') THEN
    ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS profiles_select ON profiles;
    DROP POLICY IF EXISTS profiles_insert ON profiles;
    DROP POLICY IF EXISTS profiles_update ON profiles;
    DROP POLICY IF EXISTS profiles_delete ON profiles;

    CREATE POLICY profiles_select ON profiles FOR SELECT
      USING (is_super_admin() OR user_id = auth.uid());
    CREATE POLICY profiles_insert ON profiles FOR INSERT
      WITH CHECK (is_super_admin() OR user_id = auth.uid());
    CREATE POLICY profiles_update ON profiles FOR UPDATE
      USING (is_super_admin() OR user_id = auth.uid());
    CREATE POLICY profiles_delete ON profiles FOR DELETE
      USING (is_super_admin());
  END IF;
END $$;

-- ============================================================================
-- USERS TABLE
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users' AND table_schema = 'public') THEN
    ALTER TABLE users ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS users_select ON users;
    DROP POLICY IF EXISTS users_insert ON users;
    DROP POLICY IF EXISTS users_update ON users;
    DROP POLICY IF EXISTS users_delete ON users;

    CREATE POLICY users_select ON users FOR SELECT
      USING (
        is_super_admin() OR
        id = auth.uid() OR
        EXISTS (
          SELECT 1 FROM organization_members om
          WHERE om.user_id = users.id
            AND om.organization_id = ANY(get_my_organizations())
        )
      );
    CREATE POLICY users_insert ON users FOR INSERT
      WITH CHECK (is_super_admin() OR id = auth.uid());
    CREATE POLICY users_update ON users FOR UPDATE
      USING (is_super_admin() OR id = auth.uid());
    CREATE POLICY users_delete ON users FOR DELETE
      USING (is_super_admin());
  END IF;
END $$;

-- ============================================================================
-- PROJECTS TABLE
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'projects' AND table_schema = 'public') THEN
    ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS projects_select ON projects;
    DROP POLICY IF EXISTS projects_insert ON projects;
    DROP POLICY IF EXISTS projects_update ON projects;
    DROP POLICY IF EXISTS projects_delete ON projects;

    CREATE POLICY projects_select ON projects FOR SELECT
      USING (can_access_project(id));
    CREATE POLICY projects_insert ON projects FOR INSERT
      WITH CHECK (
        is_super_admin() OR
        organization_id = ANY(get_my_organizations())
      );
    CREATE POLICY projects_update ON projects FOR UPDATE
      USING (
        is_super_admin() OR
        is_org_admin_or_owner(organization_id) OR
        is_project_consultant(id)
      );
    CREATE POLICY projects_delete ON projects FOR DELETE
      USING (
        is_super_admin() OR
        is_org_admin_or_owner(organization_id)
      );
  END IF;
END $$;

-- ============================================================================
-- PROJECT_MEMBERS TABLE
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'project_members' AND table_schema = 'public') THEN
    ALTER TABLE project_members ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS project_members_select ON project_members;
    DROP POLICY IF EXISTS project_members_insert ON project_members;
    DROP POLICY IF EXISTS project_members_update ON project_members;
    DROP POLICY IF EXISTS project_members_delete ON project_members;

    CREATE POLICY project_members_select ON project_members FOR SELECT
      USING (can_access_project(project_id));
    CREATE POLICY project_members_insert ON project_members FOR INSERT
      WITH CHECK (is_super_admin() OR is_project_consultant(project_id));
    CREATE POLICY project_members_update ON project_members FOR UPDATE
      USING (is_super_admin() OR is_project_consultant(project_id));
    CREATE POLICY project_members_delete ON project_members FOR DELETE
      USING (is_super_admin() OR is_project_consultant(project_id));
  END IF;
END $$;

-- ============================================================================
-- CONSULTANT_INVITES TABLE
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'consultant_invites' AND table_schema = 'public') THEN
    ALTER TABLE consultant_invites ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS consultant_invites_all ON consultant_invites;

    CREATE POLICY consultant_invites_all ON consultant_invites FOR ALL
      USING (is_super_admin());
  END IF;
END $$;

-- ============================================================================
-- SOLUTION_ARCHITECT_ASSIGNMENTS TABLE
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'solution_architect_assignments' AND table_schema = 'public') THEN
    ALTER TABLE solution_architect_assignments ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS sa_assignments_select ON solution_architect_assignments;
    DROP POLICY IF EXISTS sa_assignments_insert ON solution_architect_assignments;
    DROP POLICY IF EXISTS sa_assignments_update ON solution_architect_assignments;
    DROP POLICY IF EXISTS sa_assignments_delete ON solution_architect_assignments;

    CREATE POLICY sa_assignments_select ON solution_architect_assignments FOR SELECT
      USING (is_super_admin() OR user_id = auth.uid());
    CREATE POLICY sa_assignments_insert ON solution_architect_assignments FOR INSERT
      WITH CHECK (is_super_admin());
    CREATE POLICY sa_assignments_update ON solution_architect_assignments FOR UPDATE
      USING (is_super_admin());
    CREATE POLICY sa_assignments_delete ON solution_architect_assignments FOR DELETE
      USING (is_super_admin());
  END IF;
END $$;

-- ============================================================================
-- SIGNALS TABLE
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'signals' AND table_schema = 'public') THEN
    ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS signals_select ON signals;
    DROP POLICY IF EXISTS signals_insert ON signals;
    DROP POLICY IF EXISTS signals_update ON signals;
    DROP POLICY IF EXISTS signals_delete ON signals;

    CREATE POLICY signals_select ON signals FOR SELECT
      USING (can_access_project(project_id));
    CREATE POLICY signals_insert ON signals FOR INSERT
      WITH CHECK (can_access_project(project_id));
    CREATE POLICY signals_update ON signals FOR UPDATE
      USING (can_access_project(project_id));
    CREATE POLICY signals_delete ON signals FOR DELETE
      USING (is_super_admin() OR is_project_consultant(project_id));
  END IF;
END $$;

-- ============================================================================
-- SIGNAL_CHUNKS TABLE
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'signal_chunks' AND table_schema = 'public') THEN
    ALTER TABLE signal_chunks ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS signal_chunks_select ON signal_chunks;
    DROP POLICY IF EXISTS signal_chunks_insert ON signal_chunks;
    DROP POLICY IF EXISTS signal_chunks_update ON signal_chunks;
    DROP POLICY IF EXISTS signal_chunks_delete ON signal_chunks;

    CREATE POLICY signal_chunks_select ON signal_chunks FOR SELECT
      USING (
        is_super_admin() OR
        EXISTS (
          SELECT 1 FROM signals s
          WHERE s.id = signal_chunks.signal_id
            AND can_access_project(s.project_id)
        )
      );
    CREATE POLICY signal_chunks_insert ON signal_chunks FOR INSERT
      WITH CHECK (
        is_super_admin() OR
        EXISTS (
          SELECT 1 FROM signals s
          WHERE s.id = signal_chunks.signal_id
            AND can_access_project(s.project_id)
        )
      );
    CREATE POLICY signal_chunks_update ON signal_chunks FOR UPDATE
      USING (
        is_super_admin() OR
        EXISTS (
          SELECT 1 FROM signals s
          WHERE s.id = signal_chunks.signal_id
            AND can_access_project(s.project_id)
        )
      );
    CREATE POLICY signal_chunks_delete ON signal_chunks FOR DELETE
      USING (is_super_admin());
  END IF;
END $$;

-- ============================================================================
-- FEATURES TABLE
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'features' AND table_schema = 'public') THEN
    ALTER TABLE features ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS features_select ON features;
    DROP POLICY IF EXISTS features_insert ON features;
    DROP POLICY IF EXISTS features_update ON features;
    DROP POLICY IF EXISTS features_delete ON features;

    CREATE POLICY features_select ON features FOR SELECT
      USING (can_access_project(project_id));
    CREATE POLICY features_insert ON features FOR INSERT
      WITH CHECK (can_access_project(project_id));
    CREATE POLICY features_update ON features FOR UPDATE
      USING (can_access_project(project_id));
    CREATE POLICY features_delete ON features FOR DELETE
      USING (is_super_admin() OR is_project_consultant(project_id));
  END IF;
END $$;

-- ============================================================================
-- PERSONAS TABLE
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'personas' AND table_schema = 'public') THEN
    ALTER TABLE personas ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS personas_select ON personas;
    DROP POLICY IF EXISTS personas_insert ON personas;
    DROP POLICY IF EXISTS personas_update ON personas;
    DROP POLICY IF EXISTS personas_delete ON personas;

    CREATE POLICY personas_select ON personas FOR SELECT
      USING (can_access_project(project_id));
    CREATE POLICY personas_insert ON personas FOR INSERT
      WITH CHECK (can_access_project(project_id));
    CREATE POLICY personas_update ON personas FOR UPDATE
      USING (can_access_project(project_id));
    CREATE POLICY personas_delete ON personas FOR DELETE
      USING (is_super_admin() OR is_project_consultant(project_id));
  END IF;
END $$;

-- ============================================================================
-- VP_STEPS TABLE
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'vp_steps' AND table_schema = 'public') THEN
    ALTER TABLE vp_steps ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS vp_steps_select ON vp_steps;
    DROP POLICY IF EXISTS vp_steps_insert ON vp_steps;
    DROP POLICY IF EXISTS vp_steps_update ON vp_steps;
    DROP POLICY IF EXISTS vp_steps_delete ON vp_steps;

    CREATE POLICY vp_steps_select ON vp_steps FOR SELECT
      USING (can_access_project(project_id));
    CREATE POLICY vp_steps_insert ON vp_steps FOR INSERT
      WITH CHECK (can_access_project(project_id));
    CREATE POLICY vp_steps_update ON vp_steps FOR UPDATE
      USING (can_access_project(project_id));
    CREATE POLICY vp_steps_delete ON vp_steps FOR DELETE
      USING (is_super_admin() OR is_project_consultant(project_id));
  END IF;
END $$;

-- ============================================================================
-- PRD_SECTIONS TABLE
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'prd_sections' AND table_schema = 'public') THEN
    ALTER TABLE prd_sections ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS prd_sections_select ON prd_sections;
    DROP POLICY IF EXISTS prd_sections_insert ON prd_sections;
    DROP POLICY IF EXISTS prd_sections_update ON prd_sections;
    DROP POLICY IF EXISTS prd_sections_delete ON prd_sections;

    CREATE POLICY prd_sections_select ON prd_sections FOR SELECT
      USING (can_access_project(project_id));
    CREATE POLICY prd_sections_insert ON prd_sections FOR INSERT
      WITH CHECK (can_access_project(project_id));
    CREATE POLICY prd_sections_update ON prd_sections FOR UPDATE
      USING (can_access_project(project_id));
    CREATE POLICY prd_sections_delete ON prd_sections FOR DELETE
      USING (is_super_admin() OR is_project_consultant(project_id));
  END IF;
END $$;

-- ============================================================================
-- STAKEHOLDERS TABLE
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'stakeholders' AND table_schema = 'public') THEN
    ALTER TABLE stakeholders ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS stakeholders_select ON stakeholders;
    DROP POLICY IF EXISTS stakeholders_insert ON stakeholders;
    DROP POLICY IF EXISTS stakeholders_update ON stakeholders;
    DROP POLICY IF EXISTS stakeholders_delete ON stakeholders;

    CREATE POLICY stakeholders_select ON stakeholders FOR SELECT
      USING (can_access_project(project_id));
    CREATE POLICY stakeholders_insert ON stakeholders FOR INSERT
      WITH CHECK (can_access_project(project_id));
    CREATE POLICY stakeholders_update ON stakeholders FOR UPDATE
      USING (can_access_project(project_id));
    CREATE POLICY stakeholders_delete ON stakeholders FOR DELETE
      USING (is_super_admin() OR is_project_consultant(project_id));
  END IF;
END $$;

-- ============================================================================
-- CONFIRMATIONS TABLE
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'confirmations' AND table_schema = 'public') THEN
    ALTER TABLE confirmations ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS confirmations_select ON confirmations;
    DROP POLICY IF EXISTS confirmations_insert ON confirmations;
    DROP POLICY IF EXISTS confirmations_update ON confirmations;
    DROP POLICY IF EXISTS confirmations_delete ON confirmations;

    CREATE POLICY confirmations_select ON confirmations FOR SELECT
      USING (can_access_project(project_id));
    CREATE POLICY confirmations_insert ON confirmations FOR INSERT
      WITH CHECK (can_access_project(project_id));
    CREATE POLICY confirmations_update ON confirmations FOR UPDATE
      USING (can_access_project(project_id));
    CREATE POLICY confirmations_delete ON confirmations FOR DELETE
      USING (is_super_admin() OR is_project_consultant(project_id));
  END IF;
END $$;

-- ============================================================================
-- PROPOSALS TABLE
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'proposals' AND table_schema = 'public') THEN
    ALTER TABLE proposals ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS proposals_select ON proposals;
    DROP POLICY IF EXISTS proposals_insert ON proposals;
    DROP POLICY IF EXISTS proposals_update ON proposals;
    DROP POLICY IF EXISTS proposals_delete ON proposals;

    CREATE POLICY proposals_select ON proposals FOR SELECT
      USING (can_access_project(project_id));
    CREATE POLICY proposals_insert ON proposals FOR INSERT
      WITH CHECK (can_access_project(project_id));
    CREATE POLICY proposals_update ON proposals FOR UPDATE
      USING (can_access_project(project_id));
    CREATE POLICY proposals_delete ON proposals FOR DELETE
      USING (is_super_admin() OR is_project_consultant(project_id));
  END IF;
END $$;

-- ============================================================================
-- AGENT_RUNS TABLE
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'agent_runs' AND table_schema = 'public') THEN
    ALTER TABLE agent_runs ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS agent_runs_select ON agent_runs;
    DROP POLICY IF EXISTS agent_runs_insert ON agent_runs;
    DROP POLICY IF EXISTS agent_runs_update ON agent_runs;
    DROP POLICY IF EXISTS agent_runs_delete ON agent_runs;

    CREATE POLICY agent_runs_select ON agent_runs FOR SELECT
      USING (can_access_project(project_id));
    CREATE POLICY agent_runs_insert ON agent_runs FOR INSERT
      WITH CHECK (can_access_project(project_id));
    CREATE POLICY agent_runs_update ON agent_runs FOR UPDATE
      USING (can_access_project(project_id));
    CREATE POLICY agent_runs_delete ON agent_runs FOR DELETE
      USING (is_super_admin());
  END IF;
END $$;

-- ============================================================================
-- MEETINGS TABLE
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'meetings' AND table_schema = 'public') THEN
    ALTER TABLE meetings ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS meetings_select ON meetings;
    DROP POLICY IF EXISTS meetings_insert ON meetings;
    DROP POLICY IF EXISTS meetings_update ON meetings;
    DROP POLICY IF EXISTS meetings_delete ON meetings;

    CREATE POLICY meetings_select ON meetings FOR SELECT
      USING (can_access_project(project_id));
    CREATE POLICY meetings_insert ON meetings FOR INSERT
      WITH CHECK (can_access_project(project_id));
    CREATE POLICY meetings_update ON meetings FOR UPDATE
      USING (can_access_project(project_id));
    CREATE POLICY meetings_delete ON meetings FOR DELETE
      USING (is_super_admin() OR is_project_consultant(project_id));
  END IF;
END $$;

-- ============================================================================
-- STRATEGIC_CONTEXT TABLE
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'strategic_context' AND table_schema = 'public') THEN
    ALTER TABLE strategic_context ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS strategic_context_select ON strategic_context;
    DROP POLICY IF EXISTS strategic_context_insert ON strategic_context;
    DROP POLICY IF EXISTS strategic_context_update ON strategic_context;
    DROP POLICY IF EXISTS strategic_context_delete ON strategic_context;

    CREATE POLICY strategic_context_select ON strategic_context FOR SELECT
      USING (can_access_project(project_id));
    CREATE POLICY strategic_context_insert ON strategic_context FOR INSERT
      WITH CHECK (can_access_project(project_id));
    CREATE POLICY strategic_context_update ON strategic_context FOR UPDATE
      USING (can_access_project(project_id));
    CREATE POLICY strategic_context_delete ON strategic_context FOR DELETE
      USING (is_super_admin() OR is_project_consultant(project_id));
  END IF;
END $$;

-- ============================================================================
-- COMPANY_INFO TABLE
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'company_info' AND table_schema = 'public') THEN
    ALTER TABLE company_info ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS company_info_select ON company_info;
    DROP POLICY IF EXISTS company_info_insert ON company_info;
    DROP POLICY IF EXISTS company_info_update ON company_info;
    DROP POLICY IF EXISTS company_info_delete ON company_info;

    CREATE POLICY company_info_select ON company_info FOR SELECT
      USING (can_access_project(project_id));
    CREATE POLICY company_info_insert ON company_info FOR INSERT
      WITH CHECK (can_access_project(project_id));
    CREATE POLICY company_info_update ON company_info FOR UPDATE
      USING (can_access_project(project_id));
    CREATE POLICY company_info_delete ON company_info FOR DELETE
      USING (is_super_admin() OR is_project_consultant(project_id));
  END IF;
END $$;

-- ============================================================================
-- BUSINESS_DRIVERS TABLE
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'business_drivers' AND table_schema = 'public') THEN
    ALTER TABLE business_drivers ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS business_drivers_select ON business_drivers;
    DROP POLICY IF EXISTS business_drivers_insert ON business_drivers;
    DROP POLICY IF EXISTS business_drivers_update ON business_drivers;
    DROP POLICY IF EXISTS business_drivers_delete ON business_drivers;

    CREATE POLICY business_drivers_select ON business_drivers FOR SELECT
      USING (can_access_project(project_id));
    CREATE POLICY business_drivers_insert ON business_drivers FOR INSERT
      WITH CHECK (can_access_project(project_id));
    CREATE POLICY business_drivers_update ON business_drivers FOR UPDATE
      USING (can_access_project(project_id));
    CREATE POLICY business_drivers_delete ON business_drivers FOR DELETE
      USING (is_super_admin() OR is_project_consultant(project_id));
  END IF;
END $$;

-- ============================================================================
-- COMPETITOR_REFS TABLE
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'competitor_refs' AND table_schema = 'public') THEN
    ALTER TABLE competitor_refs ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS competitor_refs_select ON competitor_refs;
    DROP POLICY IF EXISTS competitor_refs_insert ON competitor_refs;
    DROP POLICY IF EXISTS competitor_refs_update ON competitor_refs;
    DROP POLICY IF EXISTS competitor_refs_delete ON competitor_refs;

    CREATE POLICY competitor_refs_select ON competitor_refs FOR SELECT
      USING (can_access_project(project_id));
    CREATE POLICY competitor_refs_insert ON competitor_refs FOR INSERT
      WITH CHECK (can_access_project(project_id));
    CREATE POLICY competitor_refs_update ON competitor_refs FOR UPDATE
      USING (can_access_project(project_id));
    CREATE POLICY competitor_refs_delete ON competitor_refs FOR DELETE
      USING (is_super_admin() OR is_project_consultant(project_id));
  END IF;
END $$;

-- ============================================================================
-- CONSTRAINTS TABLE
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'constraints' AND table_schema = 'public') THEN
    ALTER TABLE constraints ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS constraints_select ON constraints;
    DROP POLICY IF EXISTS constraints_insert ON constraints;
    DROP POLICY IF EXISTS constraints_update ON constraints;
    DROP POLICY IF EXISTS constraints_delete ON constraints;

    CREATE POLICY constraints_select ON constraints FOR SELECT
      USING (can_access_project(project_id));
    CREATE POLICY constraints_insert ON constraints FOR INSERT
      WITH CHECK (can_access_project(project_id));
    CREATE POLICY constraints_update ON constraints FOR UPDATE
      USING (can_access_project(project_id));
    CREATE POLICY constraints_delete ON constraints FOR DELETE
      USING (is_super_admin() OR is_project_consultant(project_id));
  END IF;
END $$;

-- ============================================================================
-- PROJECT_GATES TABLE
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'project_gates' AND table_schema = 'public') THEN
    ALTER TABLE project_gates ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS project_gates_select ON project_gates;
    DROP POLICY IF EXISTS project_gates_insert ON project_gates;
    DROP POLICY IF EXISTS project_gates_update ON project_gates;
    DROP POLICY IF EXISTS project_gates_delete ON project_gates;

    CREATE POLICY project_gates_select ON project_gates FOR SELECT
      USING (can_access_project(project_id));
    CREATE POLICY project_gates_insert ON project_gates FOR INSERT
      WITH CHECK (can_access_project(project_id));
    CREATE POLICY project_gates_update ON project_gates FOR UPDATE
      USING (can_access_project(project_id));
    CREATE POLICY project_gates_delete ON project_gates FOR DELETE
      USING (is_super_admin());
  END IF;
END $$;

-- ============================================================================
-- CHAT_CONVERSATIONS TABLE
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'chat_conversations' AND table_schema = 'public') THEN
    ALTER TABLE chat_conversations ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS chat_conversations_select ON chat_conversations;
    DROP POLICY IF EXISTS chat_conversations_insert ON chat_conversations;
    DROP POLICY IF EXISTS chat_conversations_update ON chat_conversations;
    DROP POLICY IF EXISTS chat_conversations_delete ON chat_conversations;

    CREATE POLICY chat_conversations_select ON chat_conversations FOR SELECT
      USING (can_access_project(project_id));
    CREATE POLICY chat_conversations_insert ON chat_conversations FOR INSERT
      WITH CHECK (can_access_project(project_id));
    CREATE POLICY chat_conversations_update ON chat_conversations FOR UPDATE
      USING (can_access_project(project_id));
    CREATE POLICY chat_conversations_delete ON chat_conversations FOR DELETE
      USING (is_super_admin());
  END IF;
END $$;

-- ============================================================================
-- ACTIVITY_FEED TABLE
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'activity_feed' AND table_schema = 'public') THEN
    ALTER TABLE activity_feed ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS activity_feed_select ON activity_feed;
    DROP POLICY IF EXISTS activity_feed_insert ON activity_feed;
    DROP POLICY IF EXISTS activity_feed_update ON activity_feed;
    DROP POLICY IF EXISTS activity_feed_delete ON activity_feed;

    CREATE POLICY activity_feed_select ON activity_feed FOR SELECT
      USING (can_access_project(project_id));
    CREATE POLICY activity_feed_insert ON activity_feed FOR INSERT
      WITH CHECK (can_access_project(project_id));
    CREATE POLICY activity_feed_update ON activity_feed FOR UPDATE
      USING (can_access_project(project_id));
    CREATE POLICY activity_feed_delete ON activity_feed FOR DELETE
      USING (is_super_admin());
  END IF;
END $$;

-- ============================================================================
-- Grant execute permissions on helper functions to authenticated users
-- ============================================================================
GRANT EXECUTE ON FUNCTION get_my_platform_role() TO authenticated;
GRANT EXECUTE ON FUNCTION is_super_admin() TO authenticated;
GRANT EXECUTE ON FUNCTION get_my_organizations() TO authenticated;
GRANT EXECUTE ON FUNCTION get_my_org_role(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION can_access_organization(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION can_access_project(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION get_my_project_role(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION get_my_client_role(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION is_project_consultant(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION is_org_admin_or_owner(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_role() TO authenticated;
