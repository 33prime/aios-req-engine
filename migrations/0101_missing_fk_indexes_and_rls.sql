-- Migration: 0101_missing_fk_indexes_and_rls.sql
-- Description: Add missing indexes on FK columns and enable RLS on 3 missed tables
-- Date: 2026-02-06
--
-- FK columns without indexes hurt join performance and cascade delete speed.
-- All indexes use IF NOT EXISTS for idempotency.

-- ============================================================================
-- Part 1: Missing FK indexes (27 columns)
-- ============================================================================

-- job_id references across 4 tables
CREATE INDEX IF NOT EXISTS idx_extracted_facts_job_id ON extracted_facts(job_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_job_id ON agent_runs(job_id);
CREATE INDEX IF NOT EXISTS idx_insights_job_id ON insights(job_id);
CREATE INDEX IF NOT EXISTS idx_state_revisions_job_id ON state_revisions(job_id);

-- requirement_links.chunk_id
CREATE INDEX IF NOT EXISTS idx_requirement_links_chunk_id ON requirement_links(chunk_id);

-- creative_briefs.last_extracted_from
CREATE INDEX IF NOT EXISTS idx_creative_briefs_last_extracted_from ON creative_briefs(last_extracted_from);

-- constraints.extracted_from_signal_id
CREATE INDEX IF NOT EXISTS idx_constraints_extracted_from_signal ON constraints(extracted_from_signal_id);

-- company_info.source_signal_id
CREATE INDEX IF NOT EXISTS idx_company_info_source_signal ON company_info(source_signal_id);

-- business_drivers FK columns
CREATE INDEX IF NOT EXISTS idx_business_drivers_stakeholder ON business_drivers(stakeholder_id);
CREATE INDEX IF NOT EXISTS idx_business_drivers_source_signal ON business_drivers(source_signal_id);

-- competitor_references.source_signal_id
CREATE INDEX IF NOT EXISTS idx_competitor_refs_source_signal ON competitor_references(source_signal_id);

-- project_members.invited_by
CREATE INDEX IF NOT EXISTS idx_project_members_invited_by ON project_members(invited_by);

-- info_requests.completed_by
CREATE INDEX IF NOT EXISTS idx_info_requests_completed_by ON info_requests(completed_by);

-- client_documents.signal_id
CREATE INDEX IF NOT EXISTS idx_client_documents_signal ON client_documents(signal_id);

-- organizations.deleted_by_user_id
CREATE INDEX IF NOT EXISTS idx_organizations_deleted_by ON organizations(deleted_by_user_id);

-- organization_members.invited_by_user_id
CREATE INDEX IF NOT EXISTS idx_org_members_invited_by ON organization_members(invited_by_user_id);

-- solution_architect_assignments.assigned_by
CREATE INDEX IF NOT EXISTS idx_sa_assignments_assigned_by ON solution_architect_assignments(assigned_by);

-- consultant_invites.organization_id
CREATE INDEX IF NOT EXISTS idx_consultant_invites_org ON consultant_invites(organization_id);

-- di_agent_logs.project_id (project_foundation & di_analysis_cache have UNIQUE which auto-indexes)
CREATE INDEX IF NOT EXISTS idx_di_agent_logs_project ON di_agent_logs(project_id);

-- tasks FK columns
CREATE INDEX IF NOT EXISTS idx_tasks_completed_by ON tasks(completed_by);
CREATE INDEX IF NOT EXISTS idx_tasks_info_request ON tasks(info_request_id);

-- collaboration_touchpoints.meeting_id
CREATE INDEX IF NOT EXISTS idx_collab_touchpoints_meeting ON collaboration_touchpoints(meeting_id);

-- project_decisions.superseded_by
CREATE INDEX IF NOT EXISTS idx_project_decisions_superseded_by ON project_decisions(superseded_by);

-- document_uploads.signal_id
CREATE INDEX IF NOT EXISTS idx_document_uploads_signal ON document_uploads(signal_id);

-- belief_history.triggered_by_node_id
CREATE INDEX IF NOT EXISTS idx_belief_history_triggered_by ON belief_history(triggered_by_node_id);

-- prompt_template_learnings.source_prototype_id
CREATE INDEX IF NOT EXISTS idx_prompt_learnings_source_prototype ON prompt_template_learnings(source_prototype_id);

-- meeting_bots.signal_id
CREATE INDEX IF NOT EXISTS idx_meeting_bots_signal ON meeting_bots(signal_id);

-- ============================================================================
-- Part 2: Enable RLS on 3 tables that have policies but RLS not enabled
-- (Policies were added in 0099 but ENABLE ROW LEVEL SECURITY was missed)
-- ============================================================================

ALTER TABLE client_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE info_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_context ENABLE ROW LEVEL SECURITY;
