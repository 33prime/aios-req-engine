import { apiRequest } from './core'

// ============================================
// Open Questions APIs
// ============================================

export const listOpenQuestions = (
  projectId: string,
  params?: { status?: string; priority?: string; category?: string; limit?: number }
) => {
  const qp = new URLSearchParams()
  if (params?.status) qp.set('status', params.status)
  if (params?.priority) qp.set('priority', params.priority)
  if (params?.category) qp.set('category', params.category)
  if (params?.limit) qp.set('limit', String(params.limit))
  const query = qp.toString()
  return apiRequest<import('@/types/workspace').OpenQuestion[]>(
    `/projects/${projectId}/questions${query ? `?${query}` : ''}`
  )
}

export const getQuestionCounts = (projectId: string) =>
  apiRequest<import('@/types/workspace').QuestionCounts>(
    `/projects/${projectId}/questions/counts`
  )

export const createOpenQuestion = (
  projectId: string,
  data: { question: string; why_it_matters?: string; priority?: string; category?: string }
) =>
  apiRequest<import('@/types/workspace').OpenQuestion>(
    `/projects/${projectId}/questions`,
    { method: 'POST', body: JSON.stringify(data) }
  )

export const answerQuestion = (projectId: string, questionId: string, answer: string) =>
  apiRequest<import('@/types/workspace').OpenQuestion>(
    `/projects/${projectId}/questions/${questionId}/answer`,
    { method: 'POST', body: JSON.stringify({ answer }) }
  )

export const dismissQuestion = (projectId: string, questionId: string, reason?: string) =>
  apiRequest<import('@/types/workspace').OpenQuestion>(
    `/projects/${projectId}/questions/${questionId}/dismiss`,
    { method: 'POST', body: JSON.stringify({ reason }) }
  )

// =============================================================================
// Project Launch
// =============================================================================

export const launchProject = (data: {
  project_name: string
  problem_description?: string
  chat_transcript?: string
  client_id?: string
  client_name?: string
  client_website?: string
  client_industry?: string
  stakeholders?: import('@/types/workspace').StakeholderLaunchInput[]
  auto_discovery?: boolean
}) =>
  apiRequest<import('@/types/workspace').ProjectLaunchResponse>('/projects/launch', {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const getLaunchProgress = (projectId: string, launchId: string) =>
  apiRequest<import('@/types/workspace').LaunchProgressResponse>(
    `/projects/${projectId}/launch/${launchId}/progress`
  )

// ============================================================================
// Consultant Enrichment
// ============================================================================

export const enrichConsultantProfile = (data: import('@/types/api').ConsultantEnrichRequest) =>
  apiRequest<import('@/types/api').ConsultantEnrichResponse>(
    '/consultant-enrichment/enrich',
    { method: 'POST', body: JSON.stringify(data) }
  )

export const getConsultantEnrichmentStatus = () =>
  apiRequest<import('@/types/api').ConsultantEnrichmentStatus>(
    '/consultant-enrichment/status'
  )

// =============================================================================
// Super Admin
// =============================================================================

export const getAdminDashboard = () =>
  apiRequest<import('@/types/api').AdminDashboardStats>('/super-admin/dashboard')

export const listAdminUsers = (params?: { search?: string; role?: string }) => {
  const qs = new URLSearchParams()
  if (params?.search) qs.set('search', params.search)
  if (params?.role) qs.set('role', params.role)
  const query = qs.toString()
  return apiRequest<import('@/types/api').AdminUserSummary[]>(`/super-admin/users${query ? `?${query}` : ''}`)
}

export const getAdminUserDetail = (userId: string) =>
  apiRequest<import('@/types/api').AdminUserDetail>(`/super-admin/users/${userId}`)

export const updateUserRole = (userId: string, role: string) =>
  apiRequest<{ status: string }>(`/super-admin/users/${userId}/role`, {
    method: 'PATCH',
    body: JSON.stringify({ platform_role: role }),
  })

export const listAdminProjects = (params?: { search?: string; stage?: string }) => {
  const qs = new URLSearchParams()
  if (params?.search) qs.set('search', params.search)
  if (params?.stage) qs.set('stage', params.stage)
  const query = qs.toString()
  return apiRequest<import('@/types/api').AdminProjectSummary[]>(`/super-admin/projects${query ? `?${query}` : ''}`)
}

export const getAdminCostAnalytics = () =>
  apiRequest<import('@/types/api').AdminCostAnalytics>('/super-admin/cost')

export const getICPLeaderboard = (profileId: string) =>
  apiRequest<import('@/types/api').LeaderboardEntry[]>(`/super-admin/icp/leaderboard?profile_id=${profileId}`)

export const getUserICPSignals = (userId: string) =>
  apiRequest<any[]>(`/super-admin/users/${userId}/icp-signals`)

// =============================================================================
// Eval Pipeline
// =============================================================================

export const getEvalDashboard = () =>
  apiRequest<import('@/types/api').EvalDashboardStats>('/super-admin/eval/dashboard')

export const listEvalRuns = (prototypeId?: string) => {
  const qs = prototypeId ? `?prototype_id=${prototypeId}` : ''
  return apiRequest<import('@/types/api').EvalRunListItem[]>(`/super-admin/eval/runs${qs}`)
}

export const getEvalRunDetail = (runId: string) =>
  apiRequest<import('@/types/api').EvalRunDetail>(`/super-admin/eval/runs/${runId}`)

export const listEvalPromptVersions = (prototypeId: string) =>
  apiRequest<import('@/types/api').EvalPromptVersion[]>(`/super-admin/eval/versions?prototype_id=${prototypeId}`)

export const getEvalPromptDiff = (versionId: string) =>
  apiRequest<import('@/types/api').EvalPromptDiff>(`/super-admin/eval/versions/${versionId}/diff`)

export const listEvalLearnings = (params?: { dimension?: string; active_only?: boolean }) => {
  const qs = new URLSearchParams()
  if (params?.dimension) qs.set('dimension', params.dimension)
  if (params?.active_only) qs.set('active_only', 'true')
  const query = qs.toString()
  return apiRequest<import('@/types/api').EvalLearning[]>(`/super-admin/eval/learnings${query ? `?${query}` : ''}`)
}

export const createEvalLearning = (body: { category: string; learning: string; dimension?: string; gap_pattern?: string }) =>
  apiRequest<import('@/types/api').EvalLearning>('/super-admin/eval/learnings', {
    method: 'POST',
    body: JSON.stringify(body),
  })

export const toggleEvalLearning = (learningId: string, active: boolean) =>
  apiRequest<import('@/types/api').EvalLearning>(`/super-admin/eval/learnings/${learningId}`, {
    method: 'PATCH',
    body: JSON.stringify({ active }),
  })

export const triggerEvalPipeline = (prototypeId: string) =>
  apiRequest<{ prototype_id: string; overall_score: number; action: string; iterations: number }>(`/super-admin/eval/trigger/${prototypeId}`, {
    method: 'POST',
  })

// =============================================================================
// Notifications
// =============================================================================

export const listNotifications = (unreadOnly = false, limit = 20) =>
  apiRequest<import('@/types/api').Notification[]>(
    `/notifications?unread_only=${unreadOnly}&limit=${limit}`
  )

export const getUnreadNotificationCount = () =>
  apiRequest<{ count: number }>('/notifications/unread-count')

export const markNotificationRead = (id: string) =>
  apiRequest<{ ok: boolean }>(`/notifications/${id}/read`, { method: 'PATCH' })

export const markAllNotificationsRead = () =>
  apiRequest<{ ok: boolean }>('/notifications/read-all', { method: 'POST' })

// =============================================================================
// Project Pulse
// =============================================================================

export const getProjectPulse = (projectId: string) =>
  apiRequest<import('@/types/api').ProjectPulse>(
    `/projects/${projectId}/workspace/pulse`
  )

export const dismissProjectPulse = (projectId: string) =>
  apiRequest<{ ok: boolean }>(
    `/projects/${projectId}/workspace/pulse/dismiss`,
    { method: 'POST' }
  )

// ============================================================================
// Unlocks
// ============================================================================

export const listUnlocks = (projectId: string, filters?: { status?: string; tier?: string }) => {
  const params = new URLSearchParams()
  if (filters?.status) params.set('status', filters.status)
  if (filters?.tier) params.set('tier', filters.tier)
  const query = params.toString()
  return apiRequest<import('@/types/workspace').UnlockSummary[]>(
    `/projects/${projectId}/workspace/unlocks${query ? `?${query}` : ''}`
  )
}

export const generateUnlocks = (projectId: string) =>
  apiRequest<{ batch_id: string; status: string }>(
    `/projects/${projectId}/workspace/unlocks/generate`,
    { method: 'POST' }
  )

export const updateUnlock = (projectId: string, unlockId: string, updates: Record<string, unknown>) =>
  apiRequest<import('@/types/workspace').UnlockSummary>(
    `/projects/${projectId}/workspace/unlocks/${unlockId}`,
    { method: 'PATCH', body: JSON.stringify(updates) }
  )

export const promoteUnlock = (projectId: string, unlockId: string, priorityGroup?: string) =>
  apiRequest<{ unlock: import('@/types/workspace').UnlockSummary; feature: Record<string, unknown> }>(
    `/projects/${projectId}/workspace/unlocks/${unlockId}/promote`,
    { method: 'POST', body: JSON.stringify({ target_priority_group: priorityGroup || 'could_have' }) }
  )

export const dismissUnlock = (projectId: string, unlockId: string) =>
  apiRequest<import('@/types/workspace').UnlockSummary>(
    `/projects/${projectId}/workspace/unlocks/${unlockId}/dismiss`,
    { method: 'POST' }
  )

// ============================================
// Solution Flow
// ============================================

export const getSolutionFlow = (projectId: string) =>
  apiRequest<import('@/types/workspace').SolutionFlowOverview>(
    `/projects/${projectId}/workspace/solution-flow`
  )

export const checkSolutionFlowReadiness = (projectId: string) =>
  apiRequest<import('@/types/workspace').SolutionFlowReadiness>(
    `/projects/${projectId}/workspace/solution-flow/readiness`
  )

export const generateSolutionFlow = (projectId: string, force?: boolean) =>
  apiRequest<{ flow_id: string; summary: string; steps_generated: number; steps_preserved?: number; steps: Record<string, unknown>[] }>(
    `/projects/${projectId}/workspace/solution-flow/generate${force ? '?force=true' : ''}`,
    { method: 'POST' }
  )

export const updateSolutionFlow = (projectId: string, data: Record<string, unknown>) =>
  apiRequest<Record<string, unknown>>(
    `/projects/${projectId}/workspace/solution-flow`,
    { method: 'PATCH', body: JSON.stringify(data) }
  )

export const createSolutionFlowStep = (projectId: string, data: Record<string, unknown>) =>
  apiRequest<import('@/types/workspace').SolutionFlowStepDetail>(
    `/projects/${projectId}/workspace/solution-flow/steps`,
    { method: 'POST', body: JSON.stringify(data) }
  )

export const getSolutionFlowStep = (projectId: string, stepId: string) =>
  apiRequest<import('@/types/workspace').SolutionFlowStepDetail>(
    `/projects/${projectId}/workspace/solution-flow/steps/${stepId}`
  )

export const getSolutionFlowStepRevisions = (projectId: string, stepId: string) =>
  apiRequest<{ revisions: import('@/types/workspace').RevisionEntry[] }>(
    `/projects/${projectId}/workspace/solution-flow/steps/${stepId}/revisions`
  )

export const updateSolutionFlowStep = (projectId: string, stepId: string, data: Record<string, unknown>) =>
  apiRequest<import('@/types/workspace').SolutionFlowStepDetail>(
    `/projects/${projectId}/workspace/solution-flow/steps/${stepId}`,
    { method: 'PATCH', body: JSON.stringify(data) }
  )

export const deleteSolutionFlowStep = (projectId: string, stepId: string) =>
  apiRequest<{ deleted: boolean }>(
    `/projects/${projectId}/workspace/solution-flow/steps/${stepId}`,
    { method: 'DELETE' }
  )

export const reorderSolutionFlowSteps = (projectId: string, stepIds: string[]) =>
  apiRequest<Record<string, unknown>[]>(
    `/projects/${projectId}/workspace/solution-flow/steps/reorder`,
    { method: 'POST', body: JSON.stringify({ step_ids: stepIds }) }
  )

// =============================================================================
// Signal Processing Results
// =============================================================================

export const getProcessingResults = (signalId: string) =>
  apiRequest<import('@/types/api').ProcessingResultsResponse>(
    `/signals/${signalId}/processing-results`
  )

export const batchConfirmFromSignal = (
  projectId: string,
  body: import('@/types/api').BatchConfirmRequest,
) =>
  apiRequest<import('@/types/api').BatchConfirmResponse>(
    `/projects/${projectId}/workspace/batch-confirm`,
    { method: 'POST', body: JSON.stringify(body) }
  )

// =============================================================================
// Project Settings
// =============================================================================

export const getProjectSettings = (projectId: string) =>
  apiRequest<{ auto_confirm_extractions: boolean }>(
    `/projects/${projectId}/workspace/settings`
  )

export const updateProjectSettings = (
  projectId: string,
  settings: { auto_confirm_extractions?: boolean },
) =>
  apiRequest<{ auto_confirm_extractions: boolean }>(
    `/projects/${projectId}/workspace/settings`,
    { method: 'PATCH', body: JSON.stringify(settings) }
  )

// =============================================================================
// Confirmation Clustering
// =============================================================================

export const getConfirmationClusters = (projectId: string) =>
  apiRequest<{ clusters: import('@/types/workspace').ConfirmationCluster[]; total: number }>(
    `/projects/${projectId}/workspace/confirmation-clusters`
  )

export const confirmCluster = (
  projectId: string,
  entities: { entity_id: string; entity_type: string }[],
  confirmationStatus = 'confirmed_consultant',
) =>
  apiRequest<{ updated_count: number; confirmation_status: string }>(
    `/projects/${projectId}/workspace/confirmation-clusters/confirm`,
    {
      method: 'POST',
      body: JSON.stringify({ entities, confirmation_status: confirmationStatus }),
    }
  )

// =============================================================================
// Pulse Engine v2 (deterministic health snapshots)
// =============================================================================

export const getPulseSnapshot = (projectId: string) =>
  apiRequest<import('@/types/api').PulseSnapshot>(
    `/projects/${projectId}/pulse`
  )

export const getPulseHistory = (projectId: string, limit = 20) =>
  apiRequest<import('@/types/api').PulseSnapshot[]>(
    `/projects/${projectId}/pulse/history?limit=${limit}`
  )

// =============================================================================
// Pulse Admin
// =============================================================================

export const getAdminPulseConfigs = () =>
  apiRequest<import('@/types/api').AdminPulseConfigSummary[]>(
    '/super-admin/pulse/configs'
  )

export const getAdminProjectPulses = () =>
  apiRequest<import('@/types/api').AdminProjectPulse[]>(
    '/super-admin/pulse/projects'
  )

export const getAdminProjectPulseDetail = (projectId: string) =>
  apiRequest<{
    latest: import('@/types/api').PulseSnapshot
    history: import('@/types/api').PulseSnapshot[]
    project_name: string
  }>(`/super-admin/pulse/projects/${projectId}`)
