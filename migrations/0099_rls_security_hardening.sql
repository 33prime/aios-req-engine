-- 0099_rls_security_hardening.sql
-- Security hardening: P0 + P1 from RLS audit
--
-- P0: Enable RLS on 50 unprotected tables
--     Fix SET search_path = '' on all security definer functions
-- P1: Add TO authenticated on all policies (was TO public)
--     Wrap auth.uid() in (select auth.uid()) for InitPlan caching

-- ================================================================
-- PART 1: Fix security definer helper functions
-- Add SET search_path = '', fully-qualify table refs,
-- wrap auth.uid() in (select auth.uid())
-- ================================================================

-- 1a. get_my_platform_role (no deps)
CREATE OR REPLACE FUNCTION public.get_my_platform_role()
RETURNS text
LANGUAGE sql
STABLE SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT COALESCE(
    (SELECT platform_role FROM public.profiles WHERE user_id = (select auth.uid())),
    'sales_consultant'
  );
$$;

-- 1b. is_super_admin (depends on get_my_platform_role)
CREATE OR REPLACE FUNCTION public.is_super_admin()
RETURNS boolean
LANGUAGE sql
STABLE SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT public.get_my_platform_role() = 'super_admin';
$$;

-- 1c. get_my_org_role (no deps)
CREATE OR REPLACE FUNCTION public.get_my_org_role(org_id uuid)
RETURNS text
LANGUAGE sql
STABLE SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT organization_role
  FROM public.organization_members
  WHERE user_id = (select auth.uid()) AND organization_id = org_id;
$$;

-- 1d. is_org_admin_or_owner (depends on is_super_admin, get_my_org_role)
CREATE OR REPLACE FUNCTION public.is_org_admin_or_owner(org_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT public.is_super_admin() OR public.get_my_org_role(org_id) IN ('Owner', 'Admin');
$$;

-- 1e. get_my_organizations (depends on get_my_platform_role)
CREATE OR REPLACE FUNCTION public.get_my_organizations()
RETURNS uuid[]
LANGUAGE plpgsql
STABLE SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
  platform_role TEXT;
  org_ids UUID[];
BEGIN
  SELECT public.get_my_platform_role() INTO platform_role;

  IF platform_role = 'super_admin' THEN
    SELECT ARRAY_AGG(id) INTO org_ids
    FROM public.organizations
    WHERE deleted_at IS NULL;
    RETURN COALESCE(org_ids, '{}');
  END IF;

  IF platform_role = 'solution_architect' THEN
    SELECT ARRAY_AGG(DISTINCT org_id) INTO org_ids
    FROM (
      SELECT organization_id AS org_id
      FROM public.organization_members
      WHERE user_id = (select auth.uid())
      UNION
      SELECT organization_id AS org_id
      FROM public.solution_architect_assignments
      WHERE user_id = (select auth.uid())
    ) combined;
    RETURN COALESCE(org_ids, '{}');
  END IF;

  SELECT ARRAY_AGG(organization_id) INTO org_ids
  FROM public.organization_members
  WHERE user_id = (select auth.uid());

  RETURN COALESCE(org_ids, '{}');
END;
$$;

-- 1f. can_access_organization (depends on is_super_admin, get_my_organizations)
CREATE OR REPLACE FUNCTION public.can_access_organization(org_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT public.is_super_admin() OR org_id = ANY(public.get_my_organizations());
$$;

-- 1g. can_access_project (depends on is_super_admin, get_my_organizations)
CREATE OR REPLACE FUNCTION public.can_access_project(proj_id uuid)
RETURNS boolean
LANGUAGE plpgsql
STABLE SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
  proj_org_id UUID;
BEGIN
  IF public.is_super_admin() THEN
    RETURN TRUE;
  END IF;

  SELECT organization_id INTO proj_org_id
  FROM public.projects
  WHERE id = proj_id;

  IF proj_org_id IS NOT NULL AND proj_org_id = ANY(public.get_my_organizations()) THEN
    RETURN TRUE;
  END IF;

  RETURN EXISTS (
    SELECT 1
    FROM public.project_members
    WHERE project_id = proj_id AND user_id = (select auth.uid())
  );
END;
$$;

-- 1h. is_project_consultant (no deps)
CREATE OR REPLACE FUNCTION public.is_project_consultant(proj_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.project_members
    WHERE project_id = proj_id
      AND user_id = (select auth.uid())
      AND role = 'consultant'
  );
$$;

-- 1i. get_my_project_role (no deps)
CREATE OR REPLACE FUNCTION public.get_my_project_role(proj_id uuid)
RETURNS text
LANGUAGE sql
STABLE SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT role
  FROM public.project_members
  WHERE project_id = proj_id AND user_id = (select auth.uid());
$$;

-- 1j. get_my_client_role (no deps)
CREATE OR REPLACE FUNCTION public.get_my_client_role(proj_id uuid)
RETURNS text
LANGUAGE sql
STABLE SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT client_role
  FROM public.project_members
  WHERE project_id = proj_id AND user_id = (select auth.uid()) AND role = 'client';
$$;

-- 1k. get_user_role (depends on get_my_platform_role)
CREATE OR REPLACE FUNCTION public.get_user_role()
RETURNS text
LANGUAGE sql
STABLE SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT CASE
    WHEN public.get_my_platform_role() = 'super_admin' THEN 'admin'
    ELSE 'user'
  END;
$$;

-- 1l. handle_new_auth_user (trigger, no STABLE)
CREATE OR REPLACE FUNCTION public.handle_new_auth_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
  user_first_name TEXT;
  user_last_name TEXT;
  user_email TEXT;
  org_name TEXT;
  new_org_id UUID;
  is_consultant BOOLEAN := FALSE;
  invite_record RECORD;
BEGIN
  user_email := LOWER(NEW.email);
  user_first_name := COALESCE(
    NEW.raw_user_meta_data->>'first_name',
    split_part(NEW.email, '@', 1)
  );
  user_last_name := COALESCE(
    NEW.raw_user_meta_data->>'last_name',
    ''
  );

  SELECT * INTO invite_record
  FROM public.consultant_invites
  WHERE LOWER(email) = user_email
    AND status = 'pending'
  LIMIT 1;

  IF invite_record.id IS NOT NULL THEN
    is_consultant := TRUE;
    UPDATE public.consultant_invites
    SET status = 'accepted', accepted_at = NOW()
    WHERE id = invite_record.id;
  END IF;

  IF is_consultant THEN
    INSERT INTO public.users (id, email, user_type, first_name, last_name, created_at, updated_at)
    VALUES (NEW.id, user_email, 'consultant', user_first_name, user_last_name, NOW(), NOW())
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO public.profiles (user_id, email, first_name, last_name, platform_role, created_at, updated_at)
    VALUES (NEW.id, user_email, user_first_name, user_last_name, COALESCE(invite_record.platform_role, 'sales_consultant'), NOW(), NOW())
    ON CONFLICT (user_id) DO NOTHING;

    org_name := user_first_name || '''s Organization';
    INSERT INTO public.organizations (name, created_by_user_id, created_at, updated_at)
    VALUES (org_name, NEW.id, NOW(), NOW())
    RETURNING id INTO new_org_id;

    INSERT INTO public.organization_members (organization_id, user_id, organization_role, invited_by_user_id, created_at, updated_at)
    VALUES (new_org_id, NEW.id, 'Owner', NEW.id, NOW(), NOW());

    IF invite_record.organization_id IS NOT NULL THEN
      INSERT INTO public.organization_members (organization_id, user_id, organization_role, invited_by_user_id, created_at, updated_at)
      VALUES (invite_record.organization_id, NEW.id, 'Member', invite_record.invited_by, NOW(), NOW())
      ON CONFLICT (organization_id, user_id) DO NOTHING;
    END IF;
  ELSE
    INSERT INTO public.users (id, email, user_type, first_name, last_name, created_at, updated_at)
    VALUES (NEW.id, user_email, 'client', user_first_name, user_last_name, NOW(), NOW())
    ON CONFLICT (id) DO NOTHING;
  END IF;

  RETURN NEW;
END;
$$;

-- 1m. get_active_touchpoint (no deps)
CREATE OR REPLACE FUNCTION public.get_active_touchpoint(p_project_id uuid)
RETURNS uuid
LANGUAGE plpgsql
STABLE SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    touchpoint_id UUID;
BEGIN
    SELECT id INTO touchpoint_id
    FROM public.collaboration_touchpoints
    WHERE project_id = p_project_id
      AND status NOT IN ('completed', 'cancelled')
    ORDER BY sequence_number DESC
    LIMIT 1;

    RETURN touchpoint_id;
END;
$$;


-- ================================================================
-- PART 2: Enable RLS on all unprotected public tables
-- ================================================================

-- Tables with project_id (will get policies in Part 3)
ALTER TABLE batch_proposals ENABLE ROW LEVEL SECURITY;
ALTER TABLE belief_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE cascade_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE competitor_references ENABLE ROW LEVEL SECURITY;
ALTER TABLE confirmation_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE creative_briefs ENABLE ROW LEVEL SECURITY;
ALTER TABLE di_agent_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE di_analysis_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE discovery_prep_bundles ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_routing_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE enrichment_revisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE entity_dependencies ENABLE ROW LEVEL SECURITY;
ALTER TABLE extracted_facts ENABLE ROW LEVEL SECURITY;
ALTER TABLE feature_intelligence ENABLE ROW LEVEL SECURITY;
ALTER TABLE insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE market_gaps ENABLE ROW LEVEL SECURITY;
ALTER TABLE meeting_agendas ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_access_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_synthesis_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_foundation ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_learnings ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE prototypes ENABLE ROW LEVEL SECURITY;
ALTER TABLE requirements ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE risks ENABLE ROW LEVEL SECURITY;
ALTER TABLE signal_impact ENABLE ROW LEVEL SECURITY;
ALTER TABLE state_revisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE state_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE synthesized_memory_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_voices ENABLE ROW LEVEL SECURITY;
ALTER TABLE vp_change_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE vp_generation_log ENABLE ROW LEVEL SECURITY;

-- Tables without project_id (backend-only via service_role)
ALTER TABLE communication_integrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE field_attributions ENABLE ROW LEVEL SECURITY;
ALTER TABLE meeting_bots ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE prompt_template_learnings ENABLE ROW LEVEL SECURITY;
ALTER TABLE prototype_feature_overlays ENABLE ROW LEVEL SECURITY;
ALTER TABLE prototype_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE prototype_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE prototype_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE requirement_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE vertical_knowledge ENABLE ROW LEVEL SECURITY;


-- ================================================================
-- PART 3: Add policies for newly protected tables
-- ================================================================

-- 3a. Tables with project_id — standard CRUD pattern
-- SELECT/INSERT/UPDATE: can_access_project(project_id)
-- DELETE: is_super_admin() OR is_project_consultant(project_id)

-- batch_proposals
CREATE POLICY "batch_proposals_select" ON batch_proposals FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "batch_proposals_insert" ON batch_proposals FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "batch_proposals_update" ON batch_proposals FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "batch_proposals_delete" ON batch_proposals FOR DELETE TO authenticated USING (is_super_admin() OR is_project_consultant(project_id));

-- belief_history
CREATE POLICY "belief_history_select" ON belief_history FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "belief_history_insert" ON belief_history FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "belief_history_update" ON belief_history FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "belief_history_delete" ON belief_history FOR DELETE TO authenticated USING (is_super_admin() OR is_project_consultant(project_id));

-- cascade_events
CREATE POLICY "cascade_events_select" ON cascade_events FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "cascade_events_insert" ON cascade_events FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "cascade_events_update" ON cascade_events FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "cascade_events_delete" ON cascade_events FOR DELETE TO authenticated USING (is_super_admin() OR is_project_consultant(project_id));

-- competitor_references
CREATE POLICY "competitor_references_select" ON competitor_references FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "competitor_references_insert" ON competitor_references FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "competitor_references_update" ON competitor_references FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "competitor_references_delete" ON competitor_references FOR DELETE TO authenticated USING (is_super_admin() OR is_project_consultant(project_id));

-- confirmation_items
CREATE POLICY "confirmation_items_select" ON confirmation_items FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "confirmation_items_insert" ON confirmation_items FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "confirmation_items_update" ON confirmation_items FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "confirmation_items_delete" ON confirmation_items FOR DELETE TO authenticated USING (is_super_admin() OR is_project_consultant(project_id));

-- conversations
CREATE POLICY "conversations_select" ON conversations FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "conversations_insert" ON conversations FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "conversations_update" ON conversations FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "conversations_delete" ON conversations FOR DELETE TO authenticated USING (is_super_admin() OR is_project_consultant(project_id));

-- creative_briefs
CREATE POLICY "creative_briefs_select" ON creative_briefs FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "creative_briefs_insert" ON creative_briefs FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "creative_briefs_update" ON creative_briefs FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "creative_briefs_delete" ON creative_briefs FOR DELETE TO authenticated USING (is_super_admin() OR is_project_consultant(project_id));

-- di_agent_logs
CREATE POLICY "di_agent_logs_select" ON di_agent_logs FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "di_agent_logs_insert" ON di_agent_logs FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "di_agent_logs_update" ON di_agent_logs FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "di_agent_logs_delete" ON di_agent_logs FOR DELETE TO authenticated USING (is_super_admin());

-- di_analysis_cache
CREATE POLICY "di_analysis_cache_select" ON di_analysis_cache FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "di_analysis_cache_insert" ON di_analysis_cache FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "di_analysis_cache_update" ON di_analysis_cache FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "di_analysis_cache_delete" ON di_analysis_cache FOR DELETE TO authenticated USING (is_super_admin());

-- discovery_prep_bundles
CREATE POLICY "discovery_prep_bundles_select" ON discovery_prep_bundles FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "discovery_prep_bundles_insert" ON discovery_prep_bundles FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "discovery_prep_bundles_update" ON discovery_prep_bundles FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "discovery_prep_bundles_delete" ON discovery_prep_bundles FOR DELETE TO authenticated USING (is_super_admin() OR is_project_consultant(project_id));

-- email_routing_tokens
CREATE POLICY "email_routing_tokens_select" ON email_routing_tokens FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "email_routing_tokens_insert" ON email_routing_tokens FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "email_routing_tokens_update" ON email_routing_tokens FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "email_routing_tokens_delete" ON email_routing_tokens FOR DELETE TO authenticated USING (is_super_admin() OR is_project_consultant(project_id));

-- enrichment_revisions
CREATE POLICY "enrichment_revisions_select" ON enrichment_revisions FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "enrichment_revisions_insert" ON enrichment_revisions FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "enrichment_revisions_update" ON enrichment_revisions FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "enrichment_revisions_delete" ON enrichment_revisions FOR DELETE TO authenticated USING (is_super_admin());

-- entity_dependencies
CREATE POLICY "entity_dependencies_select" ON entity_dependencies FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "entity_dependencies_insert" ON entity_dependencies FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "entity_dependencies_update" ON entity_dependencies FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "entity_dependencies_delete" ON entity_dependencies FOR DELETE TO authenticated USING (is_super_admin() OR is_project_consultant(project_id));

-- extracted_facts
CREATE POLICY "extracted_facts_select" ON extracted_facts FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "extracted_facts_insert" ON extracted_facts FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "extracted_facts_update" ON extracted_facts FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "extracted_facts_delete" ON extracted_facts FOR DELETE TO authenticated USING (is_super_admin());

-- feature_intelligence
CREATE POLICY "feature_intelligence_select" ON feature_intelligence FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "feature_intelligence_insert" ON feature_intelligence FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "feature_intelligence_update" ON feature_intelligence FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "feature_intelligence_delete" ON feature_intelligence FOR DELETE TO authenticated USING (is_super_admin());

-- insights
CREATE POLICY "insights_select" ON insights FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "insights_insert" ON insights FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "insights_update" ON insights FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "insights_delete" ON insights FOR DELETE TO authenticated USING (is_super_admin());

-- jobs
CREATE POLICY "jobs_select" ON jobs FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "jobs_insert" ON jobs FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "jobs_update" ON jobs FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "jobs_delete" ON jobs FOR DELETE TO authenticated USING (is_super_admin());

-- market_gaps
CREATE POLICY "market_gaps_select" ON market_gaps FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "market_gaps_insert" ON market_gaps FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "market_gaps_update" ON market_gaps FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "market_gaps_delete" ON market_gaps FOR DELETE TO authenticated USING (is_super_admin() OR is_project_consultant(project_id));

-- meeting_agendas
CREATE POLICY "meeting_agendas_select" ON meeting_agendas FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "meeting_agendas_insert" ON meeting_agendas FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "meeting_agendas_update" ON meeting_agendas FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "meeting_agendas_delete" ON meeting_agendas FOR DELETE TO authenticated USING (is_super_admin() OR is_project_consultant(project_id));

-- memory_access_log
CREATE POLICY "memory_access_log_select" ON memory_access_log FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "memory_access_log_insert" ON memory_access_log FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "memory_access_log_update" ON memory_access_log FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "memory_access_log_delete" ON memory_access_log FOR DELETE TO authenticated USING (is_super_admin());

-- memory_edges
CREATE POLICY "memory_edges_select" ON memory_edges FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "memory_edges_insert" ON memory_edges FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "memory_edges_update" ON memory_edges FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "memory_edges_delete" ON memory_edges FOR DELETE TO authenticated USING (is_super_admin());

-- memory_nodes
CREATE POLICY "memory_nodes_select" ON memory_nodes FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "memory_nodes_insert" ON memory_nodes FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "memory_nodes_update" ON memory_nodes FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "memory_nodes_delete" ON memory_nodes FOR DELETE TO authenticated USING (is_super_admin());

-- memory_synthesis_log
CREATE POLICY "memory_synthesis_log_select" ON memory_synthesis_log FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "memory_synthesis_log_insert" ON memory_synthesis_log FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "memory_synthesis_log_update" ON memory_synthesis_log FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "memory_synthesis_log_delete" ON memory_synthesis_log FOR DELETE TO authenticated USING (is_super_admin());

-- project_decisions
CREATE POLICY "project_decisions_select" ON project_decisions FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "project_decisions_insert" ON project_decisions FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "project_decisions_update" ON project_decisions FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "project_decisions_delete" ON project_decisions FOR DELETE TO authenticated USING (is_super_admin() OR is_project_consultant(project_id));

-- project_foundation
CREATE POLICY "project_foundation_select" ON project_foundation FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "project_foundation_insert" ON project_foundation FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "project_foundation_update" ON project_foundation FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "project_foundation_delete" ON project_foundation FOR DELETE TO authenticated USING (is_super_admin() OR is_project_consultant(project_id));

-- project_learnings
CREATE POLICY "project_learnings_select" ON project_learnings FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "project_learnings_insert" ON project_learnings FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "project_learnings_update" ON project_learnings FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "project_learnings_delete" ON project_learnings FOR DELETE TO authenticated USING (is_super_admin());

-- project_memory
CREATE POLICY "project_memory_select" ON project_memory FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "project_memory_insert" ON project_memory FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "project_memory_update" ON project_memory FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "project_memory_delete" ON project_memory FOR DELETE TO authenticated USING (is_super_admin());

-- project_state
CREATE POLICY "project_state_select" ON project_state FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "project_state_insert" ON project_state FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "project_state_update" ON project_state FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "project_state_delete" ON project_state FOR DELETE TO authenticated USING (is_super_admin());

-- prototypes
CREATE POLICY "prototypes_select" ON prototypes FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "prototypes_insert" ON prototypes FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "prototypes_update" ON prototypes FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "prototypes_delete" ON prototypes FOR DELETE TO authenticated USING (is_super_admin() OR is_project_consultant(project_id));

-- requirements
CREATE POLICY "requirements_select" ON requirements FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "requirements_insert" ON requirements FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "requirements_update" ON requirements FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "requirements_delete" ON requirements FOR DELETE TO authenticated USING (is_super_admin() OR is_project_consultant(project_id));

-- research_runs
CREATE POLICY "research_runs_select" ON research_runs FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "research_runs_insert" ON research_runs FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "research_runs_update" ON research_runs FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "research_runs_delete" ON research_runs FOR DELETE TO authenticated USING (is_super_admin());

-- risks
CREATE POLICY "risks_select" ON risks FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "risks_insert" ON risks FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "risks_update" ON risks FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "risks_delete" ON risks FOR DELETE TO authenticated USING (is_super_admin() OR is_project_consultant(project_id));

-- signal_impact
CREATE POLICY "signal_impact_select" ON signal_impact FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "signal_impact_insert" ON signal_impact FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "signal_impact_update" ON signal_impact FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "signal_impact_delete" ON signal_impact FOR DELETE TO authenticated USING (is_super_admin());

-- state_revisions
CREATE POLICY "state_revisions_select" ON state_revisions FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "state_revisions_insert" ON state_revisions FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "state_revisions_update" ON state_revisions FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "state_revisions_delete" ON state_revisions FOR DELETE TO authenticated USING (is_super_admin());

-- state_snapshots
CREATE POLICY "state_snapshots_select" ON state_snapshots FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "state_snapshots_insert" ON state_snapshots FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "state_snapshots_update" ON state_snapshots FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "state_snapshots_delete" ON state_snapshots FOR DELETE TO authenticated USING (is_super_admin());

-- synthesized_memory_cache
CREATE POLICY "synthesized_memory_cache_select" ON synthesized_memory_cache FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "synthesized_memory_cache_insert" ON synthesized_memory_cache FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "synthesized_memory_cache_update" ON synthesized_memory_cache FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "synthesized_memory_cache_delete" ON synthesized_memory_cache FOR DELETE TO authenticated USING (is_super_admin());

-- user_voices
CREATE POLICY "user_voices_select" ON user_voices FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "user_voices_insert" ON user_voices FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "user_voices_update" ON user_voices FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "user_voices_delete" ON user_voices FOR DELETE TO authenticated USING (is_super_admin() OR is_project_consultant(project_id));

-- vp_change_queue
CREATE POLICY "vp_change_queue_select" ON vp_change_queue FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "vp_change_queue_insert" ON vp_change_queue FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "vp_change_queue_update" ON vp_change_queue FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "vp_change_queue_delete" ON vp_change_queue FOR DELETE TO authenticated USING (is_super_admin());

-- vp_generation_log
CREATE POLICY "vp_generation_log_select" ON vp_generation_log FOR SELECT TO authenticated USING (can_access_project(project_id));
CREATE POLICY "vp_generation_log_insert" ON vp_generation_log FOR INSERT TO authenticated WITH CHECK (can_access_project(project_id));
CREATE POLICY "vp_generation_log_update" ON vp_generation_log FOR UPDATE TO authenticated USING (can_access_project(project_id));
CREATE POLICY "vp_generation_log_delete" ON vp_generation_log FOR DELETE TO authenticated USING (is_super_admin());

-- 3b. Tables without project_id — RLS enabled, backend-only (service_role bypasses)
-- No policies added; these tables are accessed exclusively through the FastAPI backend
-- which uses the service_role key. If frontend access is needed later, add policies.
-- Affected: communication_integrations, field_attributions, meeting_bots, messages,
--           prompt_template_learnings, prototype_feature_overlays, prototype_feedback,
--           prototype_questions, prototype_sessions, requirement_links, vertical_knowledge


-- ================================================================
-- PART 4: Fix existing policies
-- Change TO public → TO authenticated
-- Wrap inline auth.uid() in (select auth.uid())
-- ================================================================

-- 4a. Policies using only helper functions — just change TO clause
-- activity_feed
ALTER POLICY "activity_feed_select" ON activity_feed TO authenticated;
ALTER POLICY "activity_feed_insert" ON activity_feed TO authenticated;
ALTER POLICY "activity_feed_update" ON activity_feed TO authenticated;
ALTER POLICY "activity_feed_delete" ON activity_feed TO authenticated;

-- agent_runs
ALTER POLICY "agent_runs_select" ON agent_runs TO authenticated;
ALTER POLICY "agent_runs_insert" ON agent_runs TO authenticated;
ALTER POLICY "agent_runs_update" ON agent_runs TO authenticated;
ALTER POLICY "agent_runs_delete" ON agent_runs TO authenticated;

-- business_drivers
ALTER POLICY "business_drivers_select" ON business_drivers TO authenticated;
ALTER POLICY "business_drivers_insert" ON business_drivers TO authenticated;
ALTER POLICY "business_drivers_update" ON business_drivers TO authenticated;
ALTER POLICY "business_drivers_delete" ON business_drivers TO authenticated;

-- client_documents
ALTER POLICY "client_documents_select" ON client_documents TO authenticated;
ALTER POLICY "client_documents_insert" ON client_documents TO authenticated;
ALTER POLICY "client_documents_update" ON client_documents TO authenticated;
ALTER POLICY "client_documents_delete" ON client_documents TO authenticated;

-- company_info
ALTER POLICY "company_info_select" ON company_info TO authenticated;
ALTER POLICY "company_info_insert" ON company_info TO authenticated;
ALTER POLICY "company_info_update" ON company_info TO authenticated;
ALTER POLICY "company_info_delete" ON company_info TO authenticated;

-- constraints
ALTER POLICY "constraints_select" ON constraints TO authenticated;
ALTER POLICY "constraints_insert" ON constraints TO authenticated;
ALTER POLICY "constraints_update" ON constraints TO authenticated;
ALTER POLICY "constraints_delete" ON constraints TO authenticated;

-- consultant_invites
ALTER POLICY "consultant_invites_all" ON consultant_invites TO authenticated;

-- features
ALTER POLICY "features_select" ON features TO authenticated;
ALTER POLICY "features_insert" ON features TO authenticated;
ALTER POLICY "features_update" ON features TO authenticated;
ALTER POLICY "features_delete" ON features TO authenticated;

-- info_requests
ALTER POLICY "info_requests_select" ON info_requests TO authenticated;
ALTER POLICY "info_requests_insert" ON info_requests TO authenticated;
ALTER POLICY "info_requests_update" ON info_requests TO authenticated;
ALTER POLICY "info_requests_delete" ON info_requests TO authenticated;

-- meetings
ALTER POLICY "meetings_select" ON meetings TO authenticated;
ALTER POLICY "meetings_insert" ON meetings TO authenticated;
ALTER POLICY "meetings_update" ON meetings TO authenticated;
ALTER POLICY "meetings_delete" ON meetings TO authenticated;

-- organization_invitations
ALTER POLICY "organization_invitations_select" ON organization_invitations TO authenticated;
ALTER POLICY "organization_invitations_insert" ON organization_invitations TO authenticated;
ALTER POLICY "organization_invitations_update" ON organization_invitations TO authenticated;
ALTER POLICY "organization_invitations_delete" ON organization_invitations TO authenticated;

-- organization_members
ALTER POLICY "organization_members_select" ON organization_members TO authenticated;
ALTER POLICY "organization_members_insert" ON organization_members TO authenticated;
ALTER POLICY "organization_members_update" ON organization_members TO authenticated;
ALTER POLICY "organization_members_delete" ON organization_members TO authenticated;

-- organizations
ALTER POLICY "organizations_select" ON organizations TO authenticated;
ALTER POLICY "organizations_update" ON organizations TO authenticated;
ALTER POLICY "organizations_delete" ON organizations TO authenticated;

-- personas
ALTER POLICY "personas_select" ON personas TO authenticated;
ALTER POLICY "personas_insert" ON personas TO authenticated;
ALTER POLICY "personas_update" ON personas TO authenticated;
ALTER POLICY "personas_delete" ON personas TO authenticated;

-- project_context
ALTER POLICY "project_context_select" ON project_context TO authenticated;
ALTER POLICY "project_context_insert" ON project_context TO authenticated;
ALTER POLICY "project_context_update" ON project_context TO authenticated;
ALTER POLICY "project_context_delete" ON project_context TO authenticated;

-- project_gates
ALTER POLICY "project_gates_select" ON project_gates TO authenticated;
ALTER POLICY "project_gates_insert" ON project_gates TO authenticated;
ALTER POLICY "project_gates_update" ON project_gates TO authenticated;
ALTER POLICY "project_gates_delete" ON project_gates TO authenticated;

-- project_members
ALTER POLICY "project_members_select" ON project_members TO authenticated;
ALTER POLICY "project_members_insert" ON project_members TO authenticated;
ALTER POLICY "project_members_update" ON project_members TO authenticated;
ALTER POLICY "project_members_delete" ON project_members TO authenticated;

-- projects
ALTER POLICY "projects_select" ON projects TO authenticated;
ALTER POLICY "projects_insert" ON projects TO authenticated;
ALTER POLICY "projects_update" ON projects TO authenticated;
ALTER POLICY "projects_delete" ON projects TO authenticated;

-- signal_chunks
ALTER POLICY "signal_chunks_select" ON signal_chunks TO authenticated;
ALTER POLICY "signal_chunks_insert" ON signal_chunks TO authenticated;
ALTER POLICY "signal_chunks_update" ON signal_chunks TO authenticated;
ALTER POLICY "signal_chunks_delete" ON signal_chunks TO authenticated;

-- signals
ALTER POLICY "signals_select" ON signals TO authenticated;
ALTER POLICY "signals_insert" ON signals TO authenticated;
ALTER POLICY "signals_update" ON signals TO authenticated;
ALTER POLICY "signals_delete" ON signals TO authenticated;

-- stakeholders
ALTER POLICY "stakeholders_select" ON stakeholders TO authenticated;
ALTER POLICY "stakeholders_insert" ON stakeholders TO authenticated;
ALTER POLICY "stakeholders_update" ON stakeholders TO authenticated;
ALTER POLICY "stakeholders_delete" ON stakeholders TO authenticated;

-- strategic_context
ALTER POLICY "strategic_context_select" ON strategic_context TO authenticated;
ALTER POLICY "strategic_context_insert" ON strategic_context TO authenticated;
ALTER POLICY "strategic_context_update" ON strategic_context TO authenticated;
ALTER POLICY "strategic_context_delete" ON strategic_context TO authenticated;

-- vp_steps
ALTER POLICY "vp_steps_select" ON vp_steps TO authenticated;
ALTER POLICY "vp_steps_insert" ON vp_steps TO authenticated;
ALTER POLICY "vp_steps_update" ON vp_steps TO authenticated;
ALTER POLICY "vp_steps_delete" ON vp_steps TO authenticated;


-- 4b. Policies with inline auth.uid() — change TO + wrap expressions

-- profiles (TO public → TO authenticated + wrap auth.uid())
ALTER POLICY "profiles_delete" ON profiles TO authenticated;
ALTER POLICY "profiles_insert" ON profiles TO authenticated
  WITH CHECK (is_super_admin() OR (user_id = (select auth.uid())));
ALTER POLICY "profiles_select" ON profiles TO authenticated
  USING (is_super_admin() OR (user_id = (select auth.uid())));
ALTER POLICY "profiles_update" ON profiles TO authenticated
  USING (is_super_admin() OR (user_id = (select auth.uid())));

-- users (TO public → TO authenticated + wrap auth.uid())
ALTER POLICY "users_delete" ON users TO authenticated;
ALTER POLICY "users_insert" ON users TO authenticated
  WITH CHECK (is_super_admin() OR (id = (select auth.uid())));
ALTER POLICY "users_select" ON users TO authenticated
  USING (
    is_super_admin()
    OR (id = (select auth.uid()))
    OR (EXISTS (
      SELECT 1
      FROM organization_members om
      WHERE om.user_id = users.id
        AND om.organization_id = ANY (get_my_organizations())
    ))
  );
ALTER POLICY "users_update" ON users TO authenticated
  USING (is_super_admin() OR (id = (select auth.uid())));

-- organizations_insert (TO public → TO authenticated + wrap auth.uid())
ALTER POLICY "organizations_insert" ON organizations TO authenticated
  WITH CHECK (is_super_admin() OR ((select auth.uid()) = created_by_user_id));

-- solution_architect_assignments (TO public → TO authenticated + wrap auth.uid())
ALTER POLICY "sa_assignments_delete" ON solution_architect_assignments TO authenticated;
ALTER POLICY "sa_assignments_insert" ON solution_architect_assignments TO authenticated;
ALTER POLICY "sa_assignments_update" ON solution_architect_assignments TO authenticated;
ALTER POLICY "sa_assignments_select" ON solution_architect_assignments TO authenticated
  USING (is_super_admin() OR (user_id = (select auth.uid())));

-- document_uploads (TO public → TO authenticated + wrap auth.uid())
-- Note: "Service role can manage all document uploads" is left as-is (uses auth.role(), redundant — P2)
ALTER POLICY "Users can view document uploads for their projects" ON document_uploads TO authenticated
  USING (project_id IN (
    SELECT pm.project_id FROM project_members pm WHERE pm.user_id = (select auth.uid())
  ));
ALTER POLICY "Users can insert document uploads for their projects" ON document_uploads TO authenticated
  WITH CHECK (project_id IN (
    SELECT pm.project_id FROM project_members pm WHERE pm.user_id = (select auth.uid())
  ));
ALTER POLICY "Users can update document uploads for their projects" ON document_uploads TO authenticated
  USING (project_id IN (
    SELECT pm.project_id FROM project_members pm WHERE pm.user_id = (select auth.uid())
  ));

-- tasks (TO public → TO authenticated + wrap auth.uid())
ALTER POLICY "tasks_select_policy" ON tasks TO authenticated
  USING (
    (project_id IN (
      SELECT project_members.project_id FROM project_members
      WHERE project_members.user_id = (select auth.uid())
    ))
    OR (get_my_platform_role() = ANY (ARRAY['super_admin', 'solution_architect']))
  );
ALTER POLICY "tasks_insert_policy" ON tasks TO authenticated
  WITH CHECK (
    (project_id IN (
      SELECT project_members.project_id FROM project_members
      WHERE project_members.user_id = (select auth.uid()) AND project_members.role = 'consultant'
    ))
    OR (get_my_platform_role() = ANY (ARRAY['super_admin', 'solution_architect']))
  );
ALTER POLICY "tasks_update_policy" ON tasks TO authenticated
  USING (
    (project_id IN (
      SELECT project_members.project_id FROM project_members
      WHERE project_members.user_id = (select auth.uid()) AND project_members.role = 'consultant'
    ))
    OR (get_my_platform_role() = ANY (ARRAY['super_admin', 'solution_architect']))
  );
ALTER POLICY "tasks_delete_policy" ON tasks TO authenticated
  USING (
    (project_id IN (
      SELECT project_members.project_id FROM project_members
      WHERE project_members.user_id = (select auth.uid()) AND project_members.role = 'consultant'
    ))
    OR (get_my_platform_role() = ANY (ARRAY['super_admin', 'solution_architect']))
  );

-- task_activity_log (TO public → TO authenticated + wrap auth.uid())
ALTER POLICY "task_activity_select_policy" ON task_activity_log TO authenticated
  USING (
    (project_id IN (
      SELECT project_members.project_id FROM project_members
      WHERE project_members.user_id = (select auth.uid())
    ))
    OR (get_my_platform_role() = ANY (ARRAY['super_admin', 'solution_architect']))
  );
ALTER POLICY "task_activity_insert_policy" ON task_activity_log TO authenticated
  WITH CHECK (
    (project_id IN (
      SELECT project_members.project_id FROM project_members
      WHERE project_members.user_id = (select auth.uid()) AND project_members.role = 'consultant'
    ))
    OR (get_my_platform_role() = ANY (ARRAY['super_admin', 'solution_architect']))
  );


-- 4c. Already TO authenticated — just wrap auth.uid()

-- client_packages
ALTER POLICY "Consultants can manage client_packages" ON client_packages
  USING (project_id IN (
    SELECT project_members.project_id FROM project_members
    WHERE project_members.user_id = (select auth.uid())
      AND project_members.role = ANY (ARRAY['owner', 'consultant', 'admin'])
  ))
  WITH CHECK (project_id IN (
    SELECT project_members.project_id FROM project_members
    WHERE project_members.user_id = (select auth.uid())
      AND project_members.role = ANY (ARRAY['owner', 'consultant', 'admin'])
  ));
ALTER POLICY "Clients can view sent packages" ON client_packages
  USING (
    status = ANY (ARRAY['sent'::package_status, 'partial_response'::package_status, 'complete'::package_status])
    AND project_id IN (
      SELECT project_members.project_id FROM project_members
      WHERE project_members.user_id = (select auth.uid()) AND project_members.role = 'client'
    )
  );

-- collaboration_touchpoints
ALTER POLICY "Consultants can manage touchpoints" ON collaboration_touchpoints
  USING (project_id IN (
    SELECT project_members.project_id FROM project_members
    WHERE project_members.user_id = (select auth.uid())
      AND project_members.role = ANY (ARRAY['owner', 'consultant', 'admin'])
  ))
  WITH CHECK (project_id IN (
    SELECT project_members.project_id FROM project_members
    WHERE project_members.user_id = (select auth.uid())
      AND project_members.role = ANY (ARRAY['owner', 'consultant', 'admin'])
  ));
ALTER POLICY "Clients can view touchpoints" ON collaboration_touchpoints
  USING (project_id IN (
    SELECT project_members.project_id FROM project_members
    WHERE project_members.user_id = (select auth.uid()) AND project_members.role = 'client'
  ));

-- pending_items
ALTER POLICY "Consultants can manage pending_items" ON pending_items
  USING (project_id IN (
    SELECT project_members.project_id FROM project_members
    WHERE project_members.user_id = (select auth.uid())
      AND project_members.role = ANY (ARRAY['owner', 'consultant', 'admin'])
  ))
  WITH CHECK (project_id IN (
    SELECT project_members.project_id FROM project_members
    WHERE project_members.user_id = (select auth.uid())
      AND project_members.role = ANY (ARRAY['owner', 'consultant', 'admin'])
  ));

-- package_action_items
ALTER POLICY "Consultants can manage package_action_items" ON package_action_items
  USING (package_id IN (
    SELECT cp.id FROM client_packages cp
    JOIN project_members pm ON pm.project_id = cp.project_id
    WHERE pm.user_id = (select auth.uid())
      AND pm.role = ANY (ARRAY['owner', 'consultant', 'admin'])
  ))
  WITH CHECK (package_id IN (
    SELECT cp.id FROM client_packages cp
    JOIN project_members pm ON pm.project_id = cp.project_id
    WHERE pm.user_id = (select auth.uid())
      AND pm.role = ANY (ARRAY['owner', 'consultant', 'admin'])
  ));
ALTER POLICY "Clients can view action items in sent packages" ON package_action_items
  USING (package_id IN (
    SELECT cp.id FROM client_packages cp
    JOIN project_members pm ON pm.project_id = cp.project_id
    WHERE pm.user_id = (select auth.uid())
      AND pm.role = 'client'
      AND cp.status = ANY (ARRAY['sent'::package_status, 'partial_response'::package_status, 'complete'::package_status])
  ));
ALTER POLICY "Clients can complete action items" ON package_action_items
  USING (package_id IN (
    SELECT cp.id FROM client_packages cp
    JOIN project_members pm ON pm.project_id = cp.project_id
    WHERE pm.user_id = (select auth.uid())
      AND pm.role = 'client'
      AND cp.status = ANY (ARRAY['sent'::package_status, 'partial_response'::package_status])
  ));

-- package_asset_suggestions
ALTER POLICY "Consultants can manage package_asset_suggestions" ON package_asset_suggestions
  USING (package_id IN (
    SELECT cp.id FROM client_packages cp
    JOIN project_members pm ON pm.project_id = cp.project_id
    WHERE pm.user_id = (select auth.uid())
      AND pm.role = ANY (ARRAY['owner', 'consultant', 'admin'])
  ))
  WITH CHECK (package_id IN (
    SELECT cp.id FROM client_packages cp
    JOIN project_members pm ON pm.project_id = cp.project_id
    WHERE pm.user_id = (select auth.uid())
      AND pm.role = ANY (ARRAY['owner', 'consultant', 'admin'])
  ));
ALTER POLICY "Clients can view asset suggestions" ON package_asset_suggestions
  USING (package_id IN (
    SELECT cp.id FROM client_packages cp
    JOIN project_members pm ON pm.project_id = cp.project_id
    WHERE pm.user_id = (select auth.uid())
      AND pm.role = 'client'
      AND cp.status = ANY (ARRAY['sent'::package_status, 'partial_response'::package_status, 'complete'::package_status])
  ));

-- package_questions
ALTER POLICY "Consultants can manage package_questions" ON package_questions
  USING (package_id IN (
    SELECT cp.id FROM client_packages cp
    JOIN project_members pm ON pm.project_id = cp.project_id
    WHERE pm.user_id = (select auth.uid())
      AND pm.role = ANY (ARRAY['owner', 'consultant', 'admin'])
  ))
  WITH CHECK (package_id IN (
    SELECT cp.id FROM client_packages cp
    JOIN project_members pm ON pm.project_id = cp.project_id
    WHERE pm.user_id = (select auth.uid())
      AND pm.role = ANY (ARRAY['owner', 'consultant', 'admin'])
  ));
ALTER POLICY "Clients can view questions in sent packages" ON package_questions
  USING (package_id IN (
    SELECT cp.id FROM client_packages cp
    JOIN project_members pm ON pm.project_id = cp.project_id
    WHERE pm.user_id = (select auth.uid())
      AND pm.role = 'client'
      AND cp.status = ANY (ARRAY['sent'::package_status, 'partial_response'::package_status, 'complete'::package_status])
  ));
ALTER POLICY "Clients can answer questions" ON package_questions
  USING (package_id IN (
    SELECT cp.id FROM client_packages cp
    JOIN project_members pm ON pm.project_id = cp.project_id
    WHERE pm.user_id = (select auth.uid())
      AND pm.role = 'client'
      AND cp.status = ANY (ARRAY['sent'::package_status, 'partial_response'::package_status])
  ));

-- package_uploaded_files
ALTER POLICY "Consultants can manage package_uploaded_files" ON package_uploaded_files
  USING (package_id IN (
    SELECT cp.id FROM client_packages cp
    JOIN project_members pm ON pm.project_id = cp.project_id
    WHERE pm.user_id = (select auth.uid())
      AND pm.role = ANY (ARRAY['owner', 'consultant', 'admin'])
  ))
  WITH CHECK (package_id IN (
    SELECT cp.id FROM client_packages cp
    JOIN project_members pm ON pm.project_id = cp.project_id
    WHERE pm.user_id = (select auth.uid())
      AND pm.role = ANY (ARRAY['owner', 'consultant', 'admin'])
  ));
ALTER POLICY "Clients can upload files" ON package_uploaded_files
  WITH CHECK (package_id IN (
    SELECT cp.id FROM client_packages cp
    JOIN project_members pm ON pm.project_id = cp.project_id
    WHERE pm.user_id = (select auth.uid())
      AND pm.role = 'client'
      AND cp.status = ANY (ARRAY['sent'::package_status, 'partial_response'::package_status])
  ));
