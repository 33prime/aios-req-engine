-- Migration: 0102_fk_on_delete_and_triggers.sql
-- Description: Add ON DELETE behavior to FK constraints defaulting to NO ACTION,
--              and add missing updated_at trigger for requirements table.
-- Date: 2026-02-06
--
-- FK constraints without ON DELETE default to NO ACTION, which silently blocks
-- parent row deletes if children exist. This migration adds explicit behavior:
-- - CASCADE for project-owned NOT NULL references (delete parent = delete children)
-- - SET NULL for optional/nullable references (delete parent = null out the FK)
--
-- Constraint names follow Postgres auto-naming: <table>_<column>_fkey

-- ============================================================================
-- Part 1: ON DELETE CASCADE for project-owned NOT NULL FK columns
-- ============================================================================

-- company_info.project_id (singleton per project, UNIQUE NOT NULL)
ALTER TABLE company_info DROP CONSTRAINT company_info_project_id_fkey;
ALTER TABLE company_info ADD CONSTRAINT company_info_project_id_fkey
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE;

-- business_drivers.project_id (NOT NULL, owned by project)
ALTER TABLE business_drivers DROP CONSTRAINT business_drivers_project_id_fkey;
ALTER TABLE business_drivers ADD CONSTRAINT business_drivers_project_id_fkey
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE;

-- competitor_references.project_id (NOT NULL, owned by project)
ALTER TABLE competitor_references DROP CONSTRAINT competitor_references_project_id_fkey;
ALTER TABLE competitor_references ADD CONSTRAINT competitor_references_project_id_fkey
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE;

-- ============================================================================
-- Part 2: ON DELETE SET NULL for nullable FK columns
-- ============================================================================

-- constraints.extracted_from_signal_id → preserve constraint, null source
ALTER TABLE constraints DROP CONSTRAINT constraints_extracted_from_signal_id_fkey;
ALTER TABLE constraints ADD CONSTRAINT constraints_extracted_from_signal_id_fkey
  FOREIGN KEY (extracted_from_signal_id) REFERENCES signals(id) ON DELETE SET NULL;

-- company_info.source_signal_id → preserve company info, null source
ALTER TABLE company_info DROP CONSTRAINT company_info_source_signal_id_fkey;
ALTER TABLE company_info ADD CONSTRAINT company_info_source_signal_id_fkey
  FOREIGN KEY (source_signal_id) REFERENCES signals(id) ON DELETE SET NULL;

-- business_drivers.stakeholder_id → preserve driver, null stakeholder link
ALTER TABLE business_drivers DROP CONSTRAINT business_drivers_stakeholder_id_fkey;
ALTER TABLE business_drivers ADD CONSTRAINT business_drivers_stakeholder_id_fkey
  FOREIGN KEY (stakeholder_id) REFERENCES stakeholders(id) ON DELETE SET NULL;

-- business_drivers.source_signal_id → preserve driver, null source
ALTER TABLE business_drivers DROP CONSTRAINT business_drivers_source_signal_id_fkey;
ALTER TABLE business_drivers ADD CONSTRAINT business_drivers_source_signal_id_fkey
  FOREIGN KEY (source_signal_id) REFERENCES signals(id) ON DELETE SET NULL;

-- competitor_references.source_signal_id → preserve ref, null source
ALTER TABLE competitor_references DROP CONSTRAINT competitor_references_source_signal_id_fkey;
ALTER TABLE competitor_references ADD CONSTRAINT competitor_references_source_signal_id_fkey
  FOREIGN KEY (source_signal_id) REFERENCES signals(id) ON DELETE SET NULL;

-- vp_steps.actor_persona_id → preserve step, null persona link
ALTER TABLE vp_steps DROP CONSTRAINT vp_steps_actor_persona_id_fkey;
ALTER TABLE vp_steps ADD CONSTRAINT vp_steps_actor_persona_id_fkey
  FOREIGN KEY (actor_persona_id) REFERENCES personas(id) ON DELETE SET NULL;

-- feature_intelligence.our_feature_id → preserve intel, null feature link
ALTER TABLE feature_intelligence DROP CONSTRAINT feature_intelligence_our_feature_id_fkey;
ALTER TABLE feature_intelligence ADD CONSTRAINT feature_intelligence_our_feature_id_fkey
  FOREIGN KEY (our_feature_id) REFERENCES features(id) ON DELETE SET NULL;

-- project_members.invited_by → preserve membership, null inviter
ALTER TABLE project_members DROP CONSTRAINT project_members_invited_by_fkey;
ALTER TABLE project_members ADD CONSTRAINT project_members_invited_by_fkey
  FOREIGN KEY (invited_by) REFERENCES users(id) ON DELETE SET NULL;

-- info_requests.completed_by → preserve request, null completer
ALTER TABLE info_requests DROP CONSTRAINT info_requests_completed_by_fkey;
ALTER TABLE info_requests ADD CONSTRAINT info_requests_completed_by_fkey
  FOREIGN KEY (completed_by) REFERENCES users(id) ON DELETE SET NULL;

-- client_documents.signal_id → preserve document, null signal link
ALTER TABLE client_documents DROP CONSTRAINT client_documents_signal_id_fkey;
ALTER TABLE client_documents ADD CONSTRAINT client_documents_signal_id_fkey
  FOREIGN KEY (signal_id) REFERENCES signals(id) ON DELETE SET NULL;

-- tasks.completed_by → preserve task, null completer
ALTER TABLE tasks DROP CONSTRAINT tasks_completed_by_fkey;
ALTER TABLE tasks ADD CONSTRAINT tasks_completed_by_fkey
  FOREIGN KEY (completed_by) REFERENCES users(id) ON DELETE SET NULL;

-- tasks.info_request_id → preserve task, null info request link
ALTER TABLE tasks DROP CONSTRAINT tasks_info_request_id_fkey;
ALTER TABLE tasks ADD CONSTRAINT tasks_info_request_id_fkey
  FOREIGN KEY (info_request_id) REFERENCES info_requests(id) ON DELETE SET NULL;

-- project_decisions.superseded_by → preserve decision, null superseder (self-ref)
ALTER TABLE project_decisions DROP CONSTRAINT project_decisions_superseded_by_fkey;
ALTER TABLE project_decisions ADD CONSTRAINT project_decisions_superseded_by_fkey
  FOREIGN KEY (superseded_by) REFERENCES project_decisions(id) ON DELETE SET NULL;

-- document_uploads.signal_id → preserve upload, null signal link
ALTER TABLE document_uploads DROP CONSTRAINT document_uploads_signal_id_fkey;
ALTER TABLE document_uploads ADD CONSTRAINT document_uploads_signal_id_fkey
  FOREIGN KEY (signal_id) REFERENCES signals(id) ON DELETE SET NULL;

-- signal_chunks.document_upload_id → preserve chunk, null upload link
ALTER TABLE signal_chunks DROP CONSTRAINT signal_chunks_document_upload_id_fkey;
ALTER TABLE signal_chunks ADD CONSTRAINT signal_chunks_document_upload_id_fkey
  FOREIGN KEY (document_upload_id) REFERENCES document_uploads(id) ON DELETE SET NULL;

-- belief_history.triggered_by_node_id → preserve history, null trigger source
ALTER TABLE belief_history DROP CONSTRAINT belief_history_triggered_by_node_id_fkey;
ALTER TABLE belief_history ADD CONSTRAINT belief_history_triggered_by_node_id_fkey
  FOREIGN KEY (triggered_by_node_id) REFERENCES memory_nodes(id) ON DELETE SET NULL;

-- prompt_template_learnings.source_prototype_id → preserve learning, null source
ALTER TABLE prompt_template_learnings DROP CONSTRAINT prompt_template_learnings_source_prototype_id_fkey;
ALTER TABLE prompt_template_learnings ADD CONSTRAINT prompt_template_learnings_source_prototype_id_fkey
  FOREIGN KEY (source_prototype_id) REFERENCES prototypes(id) ON DELETE SET NULL;

-- ============================================================================
-- Part 3: Missing updated_at trigger (requirements table)
-- ============================================================================

-- requirements table from 0001_phase0.sql has updated_at but no trigger
CREATE TRIGGER set_requirements_updated_at
  BEFORE UPDATE ON requirements
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();
