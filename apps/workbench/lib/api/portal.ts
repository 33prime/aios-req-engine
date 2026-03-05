import { apiRequest } from './core'
import type {
  PortalDashboard,
  ValidationQueueResponse,
  ValidationItem,
  SubmitVerdictRequest,
  VerdictResponse,
  TeamMember,
  TeamInviteRequest,
  TeamProgress,
  StakeholderReviewData,
  EpicConfig,
  ClientExplorationData,
  ClientExplorationResults,
} from '@/types/portal'

// ============================================================================
// Dashboard
// ============================================================================

export const getPortalDashboard = (projectId: string) =>
  apiRequest<PortalDashboard>(
    `/portal/projects/${projectId}/dashboard/v2`
  )

// ============================================================================
// Validation Queue
// ============================================================================

export const getValidationQueue = (projectId: string, entityType?: string) => {
  const qp = new URLSearchParams()
  if (entityType) qp.set('entity_type', entityType)
  const query = qp.toString()
  return apiRequest<ValidationQueueResponse>(
    `/portal/projects/${projectId}/validation/queue${query ? `?${query}` : ''}`
  )
}

export const getValidationItems = (projectId: string, entityType: string) =>
  apiRequest<ValidationItem[]>(
    `/portal/projects/${projectId}/validation/queue/${entityType}`
  )

export const submitVerdict = (projectId: string, data: SubmitVerdictRequest) =>
  apiRequest<VerdictResponse>(
    `/portal/projects/${projectId}/validation/verdict`,
    {
      method: 'POST',
      body: JSON.stringify(data),
    }
  )

export const submitBatchVerdicts = (projectId: string, verdicts: SubmitVerdictRequest[]) =>
  apiRequest<VerdictResponse[]>(
    `/portal/projects/${projectId}/validation/verdict/batch`,
    {
      method: 'POST',
      body: JSON.stringify({ verdicts }),
    }
  )

// ============================================================================
// Team Management
// ============================================================================

export const getTeamMembers = (projectId: string) =>
  apiRequest<TeamMember[]>(
    `/portal/projects/${projectId}/team/members`
  )

export const inviteTeamMember = (projectId: string, data: TeamInviteRequest) =>
  apiRequest<{
    user_id: string
    email: string
    magic_link_sent: boolean
    magic_link_error?: string
    portal_role: string
  }>(
    `/portal/projects/${projectId}/team/invite`,
    {
      method: 'POST',
      body: JSON.stringify(data),
    }
  )

export const updatePortalMemberRole = (projectId: string, userId: string, role: string) =>
  apiRequest<{ user_id: string; portal_role: string }>(
    `/portal/projects/${projectId}/team/members/${userId}/role?role=${role}`,
    { method: 'PATCH' }
  )

export const getTeamProgress = (projectId: string) =>
  apiRequest<TeamProgress>(
    `/portal/projects/${projectId}/team/progress`
  )

// ============================================================================
// Stakeholder Prototype Review
// ============================================================================

export const getStakeholderReview = (sessionId: string, userId?: string) => {
  const qp = new URLSearchParams()
  if (userId) qp.set('user_id', userId)
  const query = qp.toString()
  return apiRequest<StakeholderReviewData>(
    `/prototype-sessions/${sessionId}/stakeholder-review${query ? `?${query}` : ''}`
  )
}

export const submitStakeholderEpicVerdict = (
  sessionId: string,
  data: {
    card_type?: string
    card_index: number
    verdict: string
    notes?: string
    stakeholder_id?: string
    user_id?: string
  }
) =>
  apiRequest<Record<string, unknown>>(
    `/prototype-sessions/${sessionId}/stakeholder-epic-verdict`,
    {
      method: 'PUT',
      body: JSON.stringify(data),
    }
  )

// ============================================================================
// Client Exploration (Portal v2)
// ============================================================================

// Consultant: generate assumptions and create epic configs
export const prepareForClient = (sessionId: string) =>
  apiRequest<{ session_id: string; epics_configured: number; review_state: string }>(
    `/prototype-sessions/${sessionId}/prepare-for-client`,
    { method: 'POST' }
  )

// Consultant: get staging configs
export const getEpicConfigs = (sessionId: string) =>
  apiRequest<{ session_id: string; configs: EpicConfig[] }>(
    `/prototype-sessions/${sessionId}/epic-configs`
  )

// Consultant: update staging configs
export const updateEpicConfigs = (sessionId: string, configs: EpicConfig[]) =>
  apiRequest<{ session_id: string; updated: number }>(
    `/prototype-sessions/${sessionId}/epic-configs`,
    {
      method: 'PUT',
      body: JSON.stringify({ configs }),
    }
  )

// Consultant: share with client
export const shareWithClient = (sessionId: string) =>
  apiRequest<{ session_id: string; review_state: string }>(
    `/prototype-sessions/${sessionId}/share-with-client`,
    { method: 'POST' }
  )

// Client: get exploration data
export const getClientExploration = (sessionId: string) =>
  apiRequest<ClientExplorationData>(
    `/prototype-sessions/${sessionId}/client-exploration`
  )

// Client: submit assumption response
export const submitAssumptionResponse = (
  sessionId: string,
  data: { epic_index: number; assumption_index: number; response: 'agree' | 'disagree' }
) =>
  apiRequest<Record<string, unknown>>(
    `/prototype-sessions/${sessionId}/assumption-response`,
    {
      method: 'POST',
      body: JSON.stringify(data),
    }
  )

// Client: submit inspiration
export const submitInspiration = (
  sessionId: string,
  data: { epic_index?: number | null; text: string }
) =>
  apiRequest<Record<string, unknown>>(
    `/prototype-sessions/${sessionId}/inspiration`,
    {
      method: 'POST',
      body: JSON.stringify(data),
    }
  )

// Client: log exploration event
export const submitExplorationEvent = (
  sessionId: string,
  data: { event_type: string; epic_index?: number | null; metadata?: Record<string, unknown> }
) =>
  apiRequest<{ ok: boolean }>(
    `/prototype-sessions/${sessionId}/exploration-event`,
    {
      method: 'POST',
      body: JSON.stringify(data),
    }
  )

// Client: complete exploration
export const completeExploration = (sessionId: string) =>
  apiRequest<{ session_id: string; review_state: string }>(
    `/prototype-sessions/${sessionId}/complete-exploration`,
    { method: 'POST' }
  )

// Consultant: get results
export const getExplorationResults = (sessionId: string) =>
  apiRequest<ClientExplorationResults>(
    `/prototype-sessions/${sessionId}/exploration-results`
  )

// Consultant: feed inspirations into discovery
export const feedInspirations = (sessionId: string) =>
  apiRequest<{ session_id: string; signals_created: number }>(
    `/prototype-sessions/${sessionId}/feed-inspirations`,
    { method: 'POST' }
  )
