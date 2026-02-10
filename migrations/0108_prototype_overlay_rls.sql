-- Migration 0108: Add RLS policies for prototype_feature_overlays and prototype_questions
--
-- Same issue as migration 0107: these tables had RLS enabled (0099) but NO policies,
-- so authenticated-role queries return empty results. The can_access_prototype() helper
-- from 0107 chains through prototypes.project_id → can_access_project().

-- ============================================================================
-- prototype_feature_overlays policies
-- ============================================================================

CREATE POLICY prototype_feature_overlays_select ON prototype_feature_overlays
  FOR SELECT TO authenticated
  USING (can_access_prototype(prototype_id));

CREATE POLICY prototype_feature_overlays_insert ON prototype_feature_overlays
  FOR INSERT TO authenticated
  WITH CHECK (can_access_prototype(prototype_id));

CREATE POLICY prototype_feature_overlays_update ON prototype_feature_overlays
  FOR UPDATE TO authenticated
  USING (can_access_prototype(prototype_id));

CREATE POLICY prototype_feature_overlays_delete ON prototype_feature_overlays
  FOR DELETE TO authenticated
  USING (can_access_prototype(prototype_id));

-- ============================================================================
-- prototype_questions policies
-- (chains through overlay_id → prototype_feature_overlays.prototype_id)
-- ============================================================================

CREATE POLICY prototype_questions_select ON prototype_questions
  FOR SELECT TO authenticated
  USING (can_access_prototype(
    (SELECT prototype_id FROM prototype_feature_overlays WHERE id = overlay_id)
  ));

CREATE POLICY prototype_questions_insert ON prototype_questions
  FOR INSERT TO authenticated
  WITH CHECK (can_access_prototype(
    (SELECT prototype_id FROM prototype_feature_overlays WHERE id = overlay_id)
  ));

CREATE POLICY prototype_questions_update ON prototype_questions
  FOR UPDATE TO authenticated
  USING (can_access_prototype(
    (SELECT prototype_id FROM prototype_feature_overlays WHERE id = overlay_id)
  ));

CREATE POLICY prototype_questions_delete ON prototype_questions
  FOR DELETE TO authenticated
  USING (can_access_prototype(
    (SELECT prototype_id FROM prototype_feature_overlays WHERE id = overlay_id)
  ));
