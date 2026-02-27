import { apiRequest } from './core'
import type { CanvasData, BRDWorkspaceData, WorkflowPair, StakeholderDetail, StakeholderCreatePayload, StakeholderEvidenceData } from '@/types/workspace'

// ============================================
// Workspace Canvas APIs
// ============================================

/**
 * Get all workspace data for the canvas UI.
 */
export const getWorkspaceData = (projectId: string) =>
  apiRequest<CanvasData>(`/projects/${projectId}/workspace`)

/**
 * Update the project's pitch line.
 */
export const updatePitchLine = (projectId: string, pitchLine: string) =>
  apiRequest<{ success: boolean; pitch_line: string }>(`/projects/${projectId}/workspace/pitch-line`, {
    method: 'PATCH',
    body: JSON.stringify({ pitch_line: pitchLine }),
  })

/**
 * Update the project's prototype URL.
 */
export const updatePrototypeUrl = (projectId: string, prototypeUrl: string) =>
  apiRequest<{ success: boolean; prototype_url: string }>(`/projects/${projectId}/workspace/prototype-url`, {
    method: 'PATCH',
    body: JSON.stringify({ prototype_url: prototypeUrl }),
  })

// ============================================
// BRD Canvas APIs
// ============================================

/**
 * Get aggregated BRD workspace data for the BRD canvas.
 */
export const getBRDWorkspaceData = (projectId: string, includeEvidence = true) =>
  apiRequest<BRDWorkspaceData>(`/projects/${projectId}/workspace/brd?include_evidence=${includeEvidence}`)

/**
 * Get vision detail including analysis scores and revision history.
 */
export const getVisionDetail = (projectId: string) =>
  apiRequest<import('@/types/workspace').VisionDetailData>(
    `/projects/${projectId}/workspace/vision/detail`
  )

/**
 * Get merged client intelligence: company_info + clients + strategic_context + project_memory.
 */
export const getProjectClientIntelligence = (projectId: string) =>
  apiRequest<import('@/types/workspace').ClientIntelligenceData>(
    `/projects/${projectId}/workspace/client-intelligence`
  )

/**
 * Update the project's vision statement.
 */
export const updateProjectVision = (projectId: string, vision: string) =>
  apiRequest<{ success: boolean; vision: string }>(`/projects/${projectId}/workspace/vision`, {
    method: 'PATCH',
    body: JSON.stringify({ vision }),
  })

/**
 * Enhance project vision using AI.
 */
export const enhanceVision = (projectId: string, enhancementType: string) =>
  apiRequest<{ suggestion: string }>(`/projects/${projectId}/workspace/vision/enhance`, {
    method: 'POST',
    body: JSON.stringify({ enhancement_type: enhancementType }),
  })

/**
 * Trigger AI constraint inference for a project.
 */
export const inferConstraints = (projectId: string) =>
  apiRequest<{ suggestions: import('@/types/workspace').ConstraintItem[]; count: number }>(
    `/projects/${projectId}/workspace/constraints/infer`,
    { method: 'POST' }
  )

/**
 * Update a feature's MoSCoW priority group.
 */
export const updateFeaturePriority = (
  projectId: string,
  featureId: string,
  priorityGroup: string
) =>
  apiRequest<{ success: boolean; feature_id: string; priority_group: string }>(
    `/projects/${projectId}/workspace/features/${featureId}/priority`,
    {
      method: 'PATCH',
      body: JSON.stringify({ priority_group: priorityGroup }),
    }
  )

/**
 * Get full feature detail with linked entities (drivers, personas, vp_steps).
 */
export const getFeatureDetail = (projectId: string, featureId: string) =>
  apiRequest<import('@/types/workspace').FeatureDetailResponse>(
    `/projects/${projectId}/workspace/brd/features/${featureId}/detail`
  )

/**
 * Get horizon outcomes linked to a business driver.
 */
export const getDriverHorizons = (projectId: string, driverId: string) =>
  apiRequest<{ horizons: Array<{ horizon_number: number; outcomes: Array<{ id: string; title: string; threshold?: string | null; current_value?: string | null; progress: number; trend?: string | null; horizon_title: string }> }> }>(
    `/projects/${projectId}/workspace/brd/drivers/${driverId}/horizons`
  )

/**
 * Batch confirm multiple entities.
 */
export const batchConfirmEntities = (
  projectId: string,
  entityType: string,
  entityIds: string[],
  confirmationStatus: string = 'confirmed_consultant'
) =>
  apiRequest<{ updated_count: number; entity_type: string; confirmation_status: string }>(
    '/confirmations/batch',
    {
      method: 'POST',
      body: JSON.stringify({
        project_id: projectId,
        entity_type: entityType,
        entity_ids: entityIds,
        confirmation_status: confirmationStatus,
      }),
    }
  )

// Entity Confidence
export const getEntityConfidence = (projectId: string, entityType: string, entityId: string) =>
  apiRequest<import('@/types/workspace').EntityConfidenceData>(
    `/projects/${projectId}/workspace/entity-confidence/${entityType}/${entityId}`
  )

// BRD Driver Detail + Background
export const getBRDDriverDetail = (projectId: string, driverId: string) =>
  apiRequest<import('@/types/workspace').BusinessDriverDetail>(
    `/projects/${projectId}/workspace/brd/drivers/${driverId}/detail`
  )

export const updateDriverFinancials = (
  projectId: string,
  driverId: string,
  data: {
    monetary_value_low?: number | null
    monetary_value_high?: number | null
    monetary_type?: string | null
    monetary_timeframe?: string | null
    monetary_confidence?: number | null
    monetary_source?: string | null
  }
) =>
  apiRequest<Record<string, unknown>>(
    `/projects/${projectId}/workspace/brd/drivers/${driverId}/financials`,
    { method: 'PATCH', body: JSON.stringify(data) }
  )

export const updateBusinessDriver = (
  projectId: string,
  driverId: string,
  data: Record<string, string | null>
) =>
  apiRequest<Record<string, unknown>>(
    `/projects/${projectId}/workspace/brd/drivers/${driverId}`,
    { method: 'PATCH', body: JSON.stringify(data) }
  )

export const enhanceDriverField = (
  projectId: string,
  driverId: string,
  data: { field_name: string; mode: 'rewrite' | 'notes'; user_notes?: string }
) =>
  apiRequest<{ suggestion: string }>(
    `/projects/${projectId}/workspace/brd/drivers/${driverId}/enhance`,
    { method: 'POST', body: JSON.stringify(data) }
  )

export const updateProjectBackground = (projectId: string, background: string) =>
  apiRequest<{ success: boolean; background: string }>(
    `/projects/${projectId}/workspace/brd/background`,
    {
      method: 'PATCH',
      body: JSON.stringify({ background }),
    }
  )

// ============================================
// Workflow CRUD APIs
// ============================================

export const createWorkflow = (
  projectId: string,
  data: {
    name: string
    description?: string
    owner?: string
    state_type?: 'current' | 'future'
    paired_workflow_id?: string
    frequency_per_week?: number
    hourly_rate?: number
  }
) =>
  apiRequest<Record<string, unknown>>(`/projects/${projectId}/workspace/workflows`, {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const updateWorkflow = (
  projectId: string,
  workflowId: string,
  data: {
    name?: string
    description?: string
    owner?: string
    frequency_per_week?: number
    hourly_rate?: number
  }
) =>
  apiRequest<Record<string, unknown>>(`/projects/${projectId}/workspace/workflows/${workflowId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })

export const deleteWorkflow = (projectId: string, workflowId: string) =>
  apiRequest<{ success: boolean; workflow_id: string }>(
    `/projects/${projectId}/workspace/workflows/${workflowId}`,
    { method: 'DELETE' }
  )

export const createWorkflowStep = (
  projectId: string,
  workflowId: string,
  data: {
    step_index: number
    label: string
    description?: string
    actor_persona_id?: string
    time_minutes?: number
    pain_description?: string
    benefit_description?: string
    automation_level?: 'manual' | 'semi_automated' | 'fully_automated'
    operation_type?: string
  }
) =>
  apiRequest<Record<string, unknown>>(
    `/projects/${projectId}/workspace/workflows/${workflowId}/steps`,
    {
      method: 'POST',
      body: JSON.stringify(data),
    }
  )

export const updateWorkflowStep = (
  projectId: string,
  workflowId: string,
  stepId: string,
  data: {
    label?: string
    description?: string
    time_minutes?: number
    pain_description?: string
    benefit_description?: string
    automation_level?: string
    operation_type?: string
  }
) =>
  apiRequest<Record<string, unknown>>(
    `/projects/${projectId}/workspace/workflows/${workflowId}/steps/${stepId}`,
    {
      method: 'PATCH',
      body: JSON.stringify(data),
    }
  )

export const deleteWorkflowStep = (
  projectId: string,
  workflowId: string,
  stepId: string
) =>
  apiRequest<{ success: boolean; step_id: string }>(
    `/projects/${projectId}/workspace/workflows/${workflowId}/steps/${stepId}`,
    { method: 'DELETE' }
  )

export const pairWorkflows = (
  projectId: string,
  workflowId: string,
  pairedWorkflowId: string
) =>
  apiRequest<{ success: boolean; workflow_id: string; paired_workflow_id: string }>(
    `/projects/${projectId}/workspace/workflows/${workflowId}/pair`,
    {
      method: 'POST',
      body: JSON.stringify({ paired_workflow_id: pairedWorkflowId }),
    }
  )

export const getWorkflowPairs = (projectId: string) =>
  apiRequest<WorkflowPair[]>(`/projects/${projectId}/workspace/workflows/pairs`)

// ============================================
// Data Entity APIs
// ============================================

export const createDataEntity = (
  projectId: string,
  data: {
    name: string
    description?: string
    entity_category?: 'domain' | 'reference' | 'transactional' | 'system'
    fields?: Array<{ name: string; type?: string; required?: boolean; description?: string }>
  }
) =>
  apiRequest<Record<string, unknown>>(`/projects/${projectId}/workspace/data-entities`, {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const updateDataEntity = (
  projectId: string,
  entityId: string,
  data: {
    name?: string
    description?: string
    entity_category?: string
    fields?: Array<{ name: string; type?: string; required?: boolean; description?: string }>
  }
) =>
  apiRequest<Record<string, unknown>>(
    `/projects/${projectId}/workspace/data-entities/${entityId}`,
    {
      method: 'PATCH',
      body: JSON.stringify(data),
    }
  )

export const deleteDataEntity = (projectId: string, entityId: string) =>
  apiRequest<{ success: boolean; entity_id: string }>(
    `/projects/${projectId}/workspace/data-entities/${entityId}`,
    { method: 'DELETE' }
  )

export const getDataEntityDetail = (projectId: string, entityId: string) =>
  apiRequest<import('@/types/workspace').DataEntityDetail>(
    `/projects/${projectId}/workspace/data-entities/${entityId}`
  )

export const analyzeDataEntity = (projectId: string, entityId: string) =>
  apiRequest<{ success: boolean; enrichment_data: import('@/types/workspace').DataEntityEnrichment }>(
    `/projects/${projectId}/workspace/data-entities/${entityId}/analyze`,
    { method: 'POST' }
  )

export const updateDataEntityFields = (projectId: string, entityId: string, fields: Record<string, unknown>[]) =>
  apiRequest<{ success: boolean; field_count: number }>(
    `/projects/${projectId}/workspace/data-entities/${entityId}/fields`,
    {
      method: 'PATCH',
      body: JSON.stringify({ fields }),
    }
  )

export const linkDataEntityToStep = (
  projectId: string,
  entityId: string,
  data: { vp_step_id: string; operation_type: string; description?: string }
) =>
  apiRequest<{ id: string; vp_step_id: string; operation_type: string; description: string }>(
    `/projects/${projectId}/workspace/data-entities/${entityId}/workflow-links`,
    {
      method: 'POST',
      body: JSON.stringify(data),
    }
  )

export const unlinkDataEntityFromStep = (
  projectId: string,
  entityId: string,
  linkId: string
) =>
  apiRequest<{ success: boolean; link_id: string }>(
    `/projects/${projectId}/workspace/data-entities/${entityId}/workflow-links/${linkId}`,
    { method: 'DELETE' }
  )

// ============================================
// Stakeholder / People APIs
// ============================================

export const listAllStakeholders = (params?: {
  search?: string
  stakeholder_type?: string
  influence_level?: string
  project_id?: string
  limit?: number
  offset?: number
}) => {
  const qp = new URLSearchParams()
  if (params?.search) qp.set('search', params.search)
  if (params?.stakeholder_type) qp.set('stakeholder_type', params.stakeholder_type)
  if (params?.influence_level) qp.set('influence_level', params.influence_level)
  if (params?.project_id) qp.set('project_id', params.project_id)
  if (params?.limit) qp.set('limit', params.limit.toString())
  if (params?.offset) qp.set('offset', params.offset.toString())
  const query = qp.toString()
  return apiRequest<{ stakeholders: StakeholderDetail[]; total: number }>(
    `/people${query ? `?${query}` : ''}`
  )
}

export const getStakeholder = (projectId: string, stakeholderId: string, detail = false) =>
  apiRequest<StakeholderDetail>(
    `/projects/${projectId}/stakeholders/${stakeholderId}${detail ? '?detail=true' : ''}`
  )

export const getStakeholderEvidence = (projectId: string, stakeholderId: string) =>
  apiRequest<StakeholderEvidenceData>(
    `/projects/${projectId}/stakeholders/${stakeholderId}/evidence`
  )

export const createStakeholder = (projectId: string, data: StakeholderCreatePayload) =>
  apiRequest<StakeholderDetail>(`/projects/${projectId}/stakeholders`, {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const updateStakeholder = (
  projectId: string,
  stakeholderId: string,
  data: Partial<StakeholderCreatePayload>
) =>
  apiRequest<StakeholderDetail>(
    `/projects/${projectId}/stakeholders/${stakeholderId}`,
    {
      method: 'PATCH',
      body: JSON.stringify(data),
    }
  )

export const deleteStakeholder = (projectId: string, stakeholderId: string) =>
  apiRequest<{ success: boolean; message: string }>(
    `/projects/${projectId}/stakeholders/${stakeholderId}`,
    { method: 'DELETE' }
  )

export const listProjectStakeholders = (projectId: string) =>
  apiRequest<{ stakeholders: StakeholderDetail[]; total: number }>(
    `/projects/${projectId}/stakeholders`
  )

// Stakeholder Intelligence
export const analyzeStakeholder = (projectId: string, stakeholderId: string) =>
  apiRequest<{ success: boolean; message: string }>(
    `/projects/${projectId}/stakeholders/${stakeholderId}/analyze`,
    { method: 'POST' }
  )

export const getStakeholderIntelligence = (projectId: string, stakeholderId: string) =>
  apiRequest<import('@/types/workspace').StakeholderIntelligenceProfile>(
    `/projects/${projectId}/stakeholders/${stakeholderId}/intelligence`
  )

export const getStakeholderIntelligenceLogs = (
  projectId: string,
  stakeholderId: string,
  params?: { limit?: number; offset?: number }
) => {
  const qp = new URLSearchParams()
  if (params?.limit) qp.set('limit', params.limit.toString())
  if (params?.offset) qp.set('offset', params.offset.toString())
  const query = qp.toString()
  return apiRequest<{ logs: import('@/types/workspace').StakeholderIntelligenceLog[]; total: number }>(
    `/projects/${projectId}/stakeholders/${stakeholderId}/intelligence-logs${query ? `?${query}` : ''}`
  )
}

// ============================================
// Cascading Intelligence APIs
// ============================================

export const getBRDHealth = (projectId: string) =>
  apiRequest<import('@/types/workspace').BRDHealthData>(
    `/projects/${projectId}/workspace/brd/health`
  )

// ============================================
// Actions / Context Frame APIs
// ============================================

// Legacy action type — used by batch dashboard, overview, projects cards
export interface NextAction {
  action_type: string
  title: string
  description: string
  impact_score: number
  target_entity_type: string
  target_entity_id: string | null
  suggested_stakeholder_role: string | null
  suggested_artifact: string | null
  category?: string
  rationale?: string | null
  tool_hint?: string | null
  related_question_id?: string | null
  urgency?: 'low' | 'normal' | 'high' | 'critical'
  staleness_days?: number | null
}

// =============================================================================
// Action Engine v2 types
// =============================================================================

export type ActionCategory = 'gap' | 'intelligence' | 'opportunity'
export type GapDomain = 'workflow' | 'driver' | 'persona' | 'cross_ref'
export type QuestionTarget = 'consultant' | 'client' | 'either'

export interface ActionQuestion {
  question: string
  target: QuestionTarget
  suggested_contact: string | null
  unlocks: string
}

export interface IntelligenceAction {
  action_id: string
  category: ActionCategory
  gap_domain: GapDomain | null
  narrative: string
  unlocks: string
  questions: ActionQuestion[]
  impact_score: number
  urgency: 'low' | 'normal' | 'high' | 'critical'
  primary_entity_type: string
  primary_entity_id: string
  primary_entity_name: string
  related_entity_ids: string[]
  gates_affected: string[]
  gap_type: string
  known_contacts: string[]
  evidence_count: number
}

export interface IntelligenceActionsResult {
  actions: IntelligenceAction[]
  skeleton_count: number
  open_questions: Array<{
    id: string
    question: string
    priority: string
    category: string
  }>
  phase: string
  phase_progress: number
  computed_at: string
  narrative_cached: boolean
  state_snapshot_tokens: number
}

export interface AnswerActionResponse {
  ok: boolean
  extractions: Array<{
    operation: string
    entity_type: string
    entity_id: string | null
    data: Record<string, unknown>
  }>
  entities_affected: number
  cascade_triggered: boolean
  summary: string
}

// Legacy result type (kept for backward compat)
export interface UnifiedActionsResult {
  actions: NextAction[]
  open_questions: Array<{
    id: string
    question: string
    priority: string
    category: string
  }>
  phase: string
  phase_progress: number
  memory_signals_used: number
  computed_at: string
}

// ===========================================
// v3 Context Frame types
// ===========================================

export type ContextPhase = 'empty' | 'seeding' | 'building' | 'refining'
export type CTAType = 'inline_answer' | 'upload_doc' | 'discuss'

export interface StructuralGap {
  gap_id: string
  gap_type: string
  sentence: string
  entity_type: string
  entity_id: string
  entity_name: string
  workflow_name: string | null
  score: number
  question_placeholder: string | null
}

export interface SignalGap {
  gap_id: string
  sentence: string
  suggested_artifact: string
  reasoning: string
  related_workflow: string | null
  cta_type: CTAType
}

export interface KnowledgeGap {
  gap_id: string
  sentence: string
  reasoning: string
  related_context: string | null
}

export interface TerseAction {
  action_id: string
  sentence: string
  cta_type: CTAType
  cta_label: string
  gap_source: 'structural' | 'signal' | 'knowledge'
  gap_type: string
  entity_type: string | null
  entity_id: string | null
  entity_name: string | null
  question_placeholder: string | null
  priority: number
  impact_score: number
}

export interface ProjectContextFrame {
  phase: ContextPhase
  phase_progress: number
  structural_gaps: StructuralGap[]
  signal_gaps: SignalGap[]
  knowledge_gaps: KnowledgeGap[]
  actions: TerseAction[]
  state_snapshot: string
  workflow_context: string
  memory_hints: string[]
  entity_counts: Record<string, number>
  total_gap_count: number
  computed_at: string
  open_questions: Array<{
    id: string
    question: string
    priority: string
    category: string
  }>
}

export const getNextActions = (projectId: string) =>
  apiRequest<{ actions: NextAction[] }>(
    `/projects/${projectId}/workspace/brd/next-actions`
  )

// v3 context frame (terse actions with structural/signal/knowledge gaps)
export const getContextFrame = (projectId: string, maxActions = 5) =>
  apiRequest<ProjectContextFrame>(
    `/projects/${projectId}/workspace/actions?max_actions=${maxActions}&version=v3`
  )

// v2 intelligence actions (with Haiku narratives + questions)
export const getIntelligenceActions = (projectId: string, maxActions = 5) =>
  apiRequest<IntelligenceActionsResult>(
    `/projects/${projectId}/workspace/actions?max_actions=${maxActions}&version=v2`
  )

// Answer an action question and trigger cascade (v2 compat)
export const answerActionQuestion = (
  projectId: string,
  actionId: string,
  answerText: string,
  questionIndex = 0,
) =>
  apiRequest<AnswerActionResponse>(
    `/projects/${projectId}/workspace/actions/answer`,
    {
      method: 'POST',
      body: JSON.stringify({
        action_id: actionId,
        question_index: questionIndex,
        answer_text: answerText,
      }),
    }
  )

// Answer a terse action (v3 — passes entity info directly)
export const answerTerseAction = (
  projectId: string,
  action: TerseAction,
  answerText: string,
) =>
  apiRequest<AnswerActionResponse>(
    `/projects/${projectId}/workspace/actions/answer`,
    {
      method: 'POST',
      body: JSON.stringify({
        action_id: action.action_id,
        answer_text: answerText,
        gap_type: action.gap_type,
        entity_type: action.entity_type,
        entity_id: action.entity_id,
        entity_name: action.entity_name,
        question_text: action.sentence,
      }),
    }
  )

// Keep legacy alias for existing callers
export const getUnifiedActions = (projectId: string, maxActions = 5) =>
  apiRequest<UnifiedActionsResult>(
    `/projects/${projectId}/workspace/actions?max_actions=${maxActions}`
  )

// =============================================================================
// Chat-as-Signal: Entity Detection + Extraction
// =============================================================================

export interface ChatEntityDetectionResult {
  should_extract: boolean
  entity_count: number
  entity_hints: Array<{ type: string; name: string }>
  reason: string
}

export interface ChatSaveAsSignalResult {
  success: boolean
  signal_id?: string
  facts_extracted?: number
  type_summary?: string
  open_questions?: number
  summary?: string
  error?: string
}

export const detectChatEntities = (
  projectId: string,
  messages: Array<{ role: string; content: string }>,
) =>
  apiRequest<ChatEntityDetectionResult>(
    `/v1/chat/detect-entities?project_id=${projectId}`,
    {
      method: 'POST',
      body: JSON.stringify({ messages }),
    }
  )

export const saveChatAsSignal = (
  projectId: string,
  messages: Array<{ role: string; content: string }>,
) =>
  apiRequest<ChatSaveAsSignalResult>(
    `/v1/chat/save-as-signal?project_id=${projectId}`,
    {
      method: 'POST',
      body: JSON.stringify({ messages }),
    }
  )

export const getConversationMessages = (
  conversationId: string,
  limit = 100,
) =>
  apiRequest<{ messages: Array<{ id: string; role: string; content: string; created_at: string; metadata?: Record<string, unknown> }>; total: number }>(
    `/v1/conversations/${conversationId}/messages?limit=${limit}`,
  )

// =============================================================================
// Batch Dashboard
// =============================================================================

import type { TaskStatsResponse, Task } from './tasks'
import type { ProjectDetailWithDashboard } from '@/types/api'

export interface PortalSyncBatch {
  portal_enabled: boolean
  portal_phase: string
  questions: { sent: number; completed: number; in_progress: number; pending: number }
  documents: { sent: number; completed: number; in_progress: number; pending: number }
  clients_invited: number
  clients_active: number
  last_client_activity: string | null
}

export interface BatchDashboardData {
  task_stats: Record<string, TaskStatsResponse>
  next_actions: Record<string, NextAction[]>
  portal_sync?: Record<string, PortalSyncBatch>
  pending_tasks?: Task[]
}

export const batchGetDashboardData = (
  projectIds: string[],
  opts?: { includePortalSync?: boolean; includePendingTasks?: boolean; pendingTasksLimit?: number },
) =>
  apiRequest<BatchDashboardData>('/projects/batch/dashboard-data', {
    method: 'POST',
    body: JSON.stringify({
      project_ids: projectIds,
      include_portal_sync: opts?.includePortalSync ?? false,
      include_pending_tasks: opts?.includePendingTasks ?? false,
      pending_tasks_limit: opts?.pendingTasksLimit ?? 10,
    }),
  })

// --- Home Dashboard (single-call, no waterfall) ---

export interface HomeDashboardMeeting {
  id: string
  title: string
  meeting_date: string
  meeting_time: string | null
  project_id: string | null
  status: string
  project_name?: string
}

export interface HomeDashboardData {
  projects: ProjectDetailWithDashboard[]
  total: number
  owner_profiles: Record<string, { first_name?: string; last_name?: string; photo_url?: string }>
  next_actions: Record<string, NextAction[]>
  portal_sync: Record<string, PortalSyncBatch>
  pending_tasks: Task[]
  meetings: HomeDashboardMeeting[]
}

export const getHomeDashboard = (status = 'active', pendingTasksLimit = 5) =>
  apiRequest<HomeDashboardData>(
    `/projects/home-dashboard?status=${status}&pending_tasks_limit=${pendingTasksLimit}`
  )

// =============================================================================
// Data Entity Graph / Impact / Refresh / Cascades
// =============================================================================

export const getDataEntityGraph = (projectId: string) =>
  apiRequest<import('@/types/workspace').DataEntityGraphData>(
    `/projects/${projectId}/workspace/data-entity-graph`
  )

export const getImpactAnalysis = (projectId: string, entityType: string, entityId: string) =>
  apiRequest<import('@/types/workspace').ImpactAnalysis>(
    `/projects/${projectId}/impact-analysis`,
    {
      method: 'POST',
      body: JSON.stringify({ entity_type: entityType, entity_id: entityId }),
    }
  )

export const refreshStaleEntity = (projectId: string, entityType: string, entityId: string) =>
  apiRequest<{ entity_type: string; entity_id: string; status: string; message: string }>(
    `/projects/${projectId}/refresh-entity`,
    {
      method: 'POST',
      body: JSON.stringify({ entity_type: entityType, entity_id: entityId }),
    }
  )

export const processCascades = (projectId: string) =>
  apiRequest<{ changes_processed: number; entities_marked_stale: number; errors: string[] }>(
    `/projects/${projectId}/process-cascades`,
    { method: 'POST' }
  )

// ============================================
// Workflow Step Detail APIs
// ============================================

export const getWorkflowStepDetail = (projectId: string, stepId: string) =>
  apiRequest<import('@/types/workspace').WorkflowStepDetail>(
    `/projects/${projectId}/workspace/workflows/steps/${stepId}/detail`
  )

export const enrichWorkflow = (projectId: string, workflowId: string) =>
  apiRequest<{ success: boolean; enriched_step_count: number; unlock_count: number }>(
    `/projects/${projectId}/workspace/workflows/${workflowId}/enrich`,
    { method: 'POST' }
  )

export const getWorkflowDetail = (projectId: string, workflowId: string) =>
  apiRequest<import('@/types/workspace').WorkflowDetail>(
    `/projects/${projectId}/workspace/workflows/${workflowId}/detail`
  )

// ============================================
// Canvas View APIs
// ============================================

export const getCanvasViewData = (projectId: string) =>
  apiRequest<import('@/types/workspace').CanvasViewData>(
    `/projects/${projectId}/workspace/canvas`
  )

export const triggerValuePathSynthesis = (projectId: string) =>
  apiRequest<{
    value_path: import('@/types/workspace').ValuePathStep[]
    synthesis_rationale: string
    excluded_flows: string[]
    step_count: number
    version: number
  }>(
    `/projects/${projectId}/workspace/canvas/synthesize`,
    { method: 'POST' }
  )

export const updateCanvasRole = (projectId: string, personaId: string, canvasRole: string | null) =>
  apiRequest<{ success: boolean; persona_id: string; canvas_role: string | null }>(
    `/projects/${projectId}/workspace/personas/${personaId}/canvas-role`,
    {
      method: 'PATCH',
      body: JSON.stringify({ canvas_role: canvasRole }),
    }
  )

export const getCanvasActors = (projectId: string) =>
  apiRequest<import('@/types/workspace').PersonaBRDSummary[]>(
    `/projects/${projectId}/workspace/canvas-actors`
  )

// Canvas: Project Context
export const getProjectContext = (projectId: string) =>
  apiRequest<import('@/types/workspace').ProjectContext>(
    `/projects/${projectId}/workspace/canvas/project-context`
  )

export const generateProjectContext = (projectId: string) =>
  apiRequest<import('@/types/workspace').ProjectContext>(
    `/projects/${projectId}/workspace/canvas/project-context/generate`,
    { method: 'POST' }
  )

// Canvas: Value Path Step Detail
export const getValuePathStepDetail = (projectId: string, stepIndex: number) =>
  apiRequest<import('@/types/workspace').ValuePathStepDetail>(
    `/projects/${projectId}/workspace/canvas/value-path-steps/${stepIndex}/detail`
  )
