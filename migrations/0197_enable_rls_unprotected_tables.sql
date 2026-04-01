-- =============================================================================
-- Enable RLS + add policies for 8 unprotected tables
-- 4 project-scoped (via project_id), 4 session-scoped (via session_id → prototype_sessions)
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. call_strategy_briefs (project_id)
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE public.call_strategy_briefs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "call_strategy_briefs_select" ON public.call_strategy_briefs
  FOR SELECT USING (can_access_project(project_id));

CREATE POLICY "call_strategy_briefs_insert" ON public.call_strategy_briefs
  FOR INSERT WITH CHECK (can_access_project(project_id));

CREATE POLICY "call_strategy_briefs_update" ON public.call_strategy_briefs
  FOR UPDATE USING (can_access_project(project_id));

CREATE POLICY "call_strategy_briefs_delete" ON public.call_strategy_briefs
  FOR DELETE USING (is_super_admin() OR is_project_consultant(project_id));

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. forge_module_matches (project_id)
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE public.forge_module_matches ENABLE ROW LEVEL SECURITY;

CREATE POLICY "forge_module_matches_select" ON public.forge_module_matches
  FOR SELECT USING (can_access_project(project_id));

CREATE POLICY "forge_module_matches_insert" ON public.forge_module_matches
  FOR INSERT WITH CHECK (can_access_project(project_id));

CREATE POLICY "forge_module_matches_update" ON public.forge_module_matches
  FOR UPDATE USING (can_access_project(project_id));

CREATE POLICY "forge_module_matches_delete" ON public.forge_module_matches
  FOR DELETE USING (is_super_admin() OR is_project_consultant(project_id));

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. project_briefings (project_id)
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE public.project_briefings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "project_briefings_select" ON public.project_briefings
  FOR SELECT USING (can_access_project(project_id));

CREATE POLICY "project_briefings_insert" ON public.project_briefings
  FOR INSERT WITH CHECK (can_access_project(project_id));

CREATE POLICY "project_briefings_update" ON public.project_briefings
  FOR UPDATE USING (can_access_project(project_id));

CREATE POLICY "project_briefings_delete" ON public.project_briefings
  FOR DELETE USING (is_super_admin() OR is_project_consultant(project_id));

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. prototype_builds (project_id)
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE public.prototype_builds ENABLE ROW LEVEL SECURITY;

CREATE POLICY "prototype_builds_select" ON public.prototype_builds
  FOR SELECT USING (can_access_project(project_id));

CREATE POLICY "prototype_builds_insert" ON public.prototype_builds
  FOR INSERT WITH CHECK (can_access_project(project_id));

CREATE POLICY "prototype_builds_update" ON public.prototype_builds
  FOR UPDATE USING (can_access_project(project_id));

CREATE POLICY "prototype_builds_delete" ON public.prototype_builds
  FOR DELETE USING (is_super_admin() OR is_project_consultant(project_id));

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. client_assumption_responses (session_id → prototype_sessions)
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE public.client_assumption_responses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "client_assumption_responses_select" ON public.client_assumption_responses
  FOR SELECT USING (
    can_access_prototype((
      SELECT ps.prototype_id FROM prototype_sessions ps
      WHERE ps.id = client_assumption_responses.session_id
    ))
  );

CREATE POLICY "client_assumption_responses_insert" ON public.client_assumption_responses
  FOR INSERT WITH CHECK (
    can_access_prototype((
      SELECT ps.prototype_id FROM prototype_sessions ps
      WHERE ps.id = session_id
    ))
  );

CREATE POLICY "client_assumption_responses_update" ON public.client_assumption_responses
  FOR UPDATE USING (
    can_access_prototype((
      SELECT ps.prototype_id FROM prototype_sessions ps
      WHERE ps.id = client_assumption_responses.session_id
    ))
  );

CREATE POLICY "client_assumption_responses_delete" ON public.client_assumption_responses
  FOR DELETE USING (
    can_access_prototype((
      SELECT ps.prototype_id FROM prototype_sessions ps
      WHERE ps.id = client_assumption_responses.session_id
    ))
  );

-- ─────────────────────────────────────────────────────────────────────────────
-- 6. client_exploration_events (session_id → prototype_sessions)
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE public.client_exploration_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "client_exploration_events_select" ON public.client_exploration_events
  FOR SELECT USING (
    can_access_prototype((
      SELECT ps.prototype_id FROM prototype_sessions ps
      WHERE ps.id = client_exploration_events.session_id
    ))
  );

CREATE POLICY "client_exploration_events_insert" ON public.client_exploration_events
  FOR INSERT WITH CHECK (
    can_access_prototype((
      SELECT ps.prototype_id FROM prototype_sessions ps
      WHERE ps.id = session_id
    ))
  );

CREATE POLICY "client_exploration_events_update" ON public.client_exploration_events
  FOR UPDATE USING (
    can_access_prototype((
      SELECT ps.prototype_id FROM prototype_sessions ps
      WHERE ps.id = client_exploration_events.session_id
    ))
  );

CREATE POLICY "client_exploration_events_delete" ON public.client_exploration_events
  FOR DELETE USING (
    can_access_prototype((
      SELECT ps.prototype_id FROM prototype_sessions ps
      WHERE ps.id = client_exploration_events.session_id
    ))
  );

-- ─────────────────────────────────────────────────────────────────────────────
-- 7. client_inspirations (session_id → prototype_sessions)
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE public.client_inspirations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "client_inspirations_select" ON public.client_inspirations
  FOR SELECT USING (
    can_access_prototype((
      SELECT ps.prototype_id FROM prototype_sessions ps
      WHERE ps.id = client_inspirations.session_id
    ))
  );

CREATE POLICY "client_inspirations_insert" ON public.client_inspirations
  FOR INSERT WITH CHECK (
    can_access_prototype((
      SELECT ps.prototype_id FROM prototype_sessions ps
      WHERE ps.id = session_id
    ))
  );

CREATE POLICY "client_inspirations_update" ON public.client_inspirations
  FOR UPDATE USING (
    can_access_prototype((
      SELECT ps.prototype_id FROM prototype_sessions ps
      WHERE ps.id = client_inspirations.session_id
    ))
  );

CREATE POLICY "client_inspirations_delete" ON public.client_inspirations
  FOR DELETE USING (
    can_access_prototype((
      SELECT ps.prototype_id FROM prototype_sessions ps
      WHERE ps.id = client_inspirations.session_id
    ))
  );

-- ─────────────────────────────────────────────────────────────────────────────
-- 8. prototype_epic_confirmations (session_id → prototype_sessions)
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE public.prototype_epic_confirmations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "prototype_epic_confirmations_select" ON public.prototype_epic_confirmations
  FOR SELECT USING (
    can_access_prototype((
      SELECT ps.prototype_id FROM prototype_sessions ps
      WHERE ps.id = prototype_epic_confirmations.session_id
    ))
  );

CREATE POLICY "prototype_epic_confirmations_insert" ON public.prototype_epic_confirmations
  FOR INSERT WITH CHECK (
    can_access_prototype((
      SELECT ps.prototype_id FROM prototype_sessions ps
      WHERE ps.id = session_id
    ))
  );

CREATE POLICY "prototype_epic_confirmations_update" ON public.prototype_epic_confirmations
  FOR UPDATE USING (
    can_access_prototype((
      SELECT ps.prototype_id FROM prototype_sessions ps
      WHERE ps.id = prototype_epic_confirmations.session_id
    ))
  );

CREATE POLICY "prototype_epic_confirmations_delete" ON public.prototype_epic_confirmations
  FOR DELETE USING (
    can_access_prototype((
      SELECT ps.prototype_id FROM prototype_sessions ps
      WHERE ps.id = prototype_epic_confirmations.session_id
    ))
  );
