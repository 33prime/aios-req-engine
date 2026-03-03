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
