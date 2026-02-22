import { apiRequest } from './core'
import type {
  DiscoveryPrepBundle,
  PhaseProgressResponse,
  PendingItem,
  ClientPackage,
  Meeting,
  StatusNarrative,
  IntegrationSettings,
  GoogleStatusResponse,
  EmailTokenResponse,
  MeetingBot,
  RecordingDefault,
} from '../../types/api'

// ============================================
// Discovery Prep APIs
// ============================================

export const getDiscoveryPrep = (projectId: string) =>
  apiRequest<DiscoveryPrepBundle>(`/discovery-prep/${projectId}`)

export const generateDiscoveryPrep = (projectId: string, forceRegenerate = false) =>
  apiRequest<{ bundle: DiscoveryPrepBundle; message: string }>(`/discovery-prep/${projectId}/generate`, {
    method: 'POST',
    body: JSON.stringify({ force_regenerate: forceRegenerate }),
  })

export const confirmPrepQuestion = (projectId: string, questionId: string, confirmed = true) =>
  apiRequest<DiscoveryPrepBundle>(`/discovery-prep/${projectId}/questions/${questionId}/confirm`, {
    method: 'POST',
    body: JSON.stringify({ confirmed }),
  })

export const confirmPrepDocument = (projectId: string, documentId: string, confirmed = true) =>
  apiRequest<DiscoveryPrepBundle>(`/discovery-prep/${projectId}/documents/${documentId}/confirm`, {
    method: 'POST',
    body: JSON.stringify({ confirmed }),
  })

export const sendDiscoveryPrepToPortal = (projectId: string, inviteEmails?: string[]) =>
  apiRequest<{ success: boolean; questions_sent: number; documents_sent: number; invitations_sent: number; message: string }>(`/discovery-prep/${projectId}/send`, {
    method: 'POST',
    body: JSON.stringify({ invite_emails: inviteEmails }),
  })

export const regeneratePrepQuestions = (projectId: string) =>
  apiRequest<DiscoveryPrepBundle>(`/discovery-prep/${projectId}/regenerate-questions`, {
    method: 'POST',
  })

export const regeneratePrepDocuments = (projectId: string) =>
  apiRequest<DiscoveryPrepBundle>(`/discovery-prep/${projectId}/regenerate-documents`, {
    method: 'POST',
  })

// ============================================
// Collaboration APIs
// ============================================

export interface CollaborationCurrentResponse {
  project_id: string
  collaboration_phase: string
  current_focus: {
    phase: string
    primary_action: string
    discovery_prep?: Record<string, unknown>
    validation?: Record<string, unknown>
    prototype_feedback?: Record<string, unknown>
  }
  active_touchpoint: Record<string, unknown> | null
  portal_sync: {
    portal_enabled: boolean
    portal_phase: string
    questions: { sent: number; completed: number; in_progress: number; pending: number }
    documents: { sent: number; completed: number; in_progress: number; pending: number }
    last_client_activity: string | null
    clients_invited: number
    clients_active: number
  }
  pending_validation_count: number
  pending_proposals_count: number
  pending_review_count: number
  total_touchpoints_completed: number
  last_client_interaction: string | null
}

export interface CollaborationHistoryResponse {
  project_id: string
  touchpoints: Array<{
    id: string
    type: string
    title: string
    status: string
    sequence_number: number
    outcomes_summary: string
    completed_at: string | null
    created_at: string
  }>
  total_questions_answered: number
  total_documents_received: number
  total_features_extracted: number
  total_items_confirmed: number
}

export const getCollaborationCurrent = (projectId: string) =>
  apiRequest<CollaborationCurrentResponse>(`/projects/${projectId}/collaboration/current`)

export const getCollaborationHistory = (projectId: string) =>
  apiRequest<CollaborationHistoryResponse>(`/projects/${projectId}/collaboration/history`)

export const setCollaborationPhase = (projectId: string, phase: string) =>
  apiRequest<{ success: boolean; phase: string }>(`/projects/${projectId}/collaboration/phase/${phase}`, {
    method: 'POST',
  })

// ============================================
// Touchpoints APIs
// ============================================

export type TouchpointType = 'discovery_call' | 'validation_round' | 'follow_up_call' | 'prototype_review' | 'feedback_session'

export interface CreateTouchpointRequest {
  type: TouchpointType
  title: string
  description?: string
  meeting_id?: string
}

export interface Touchpoint {
  id: string
  project_id: string
  type: TouchpointType
  title: string
  description?: string
  status: string
  sequence_number: number
  meeting_id?: string
  discovery_prep_bundle_id?: string
  outcomes: {
    questions_sent: number
    questions_answered: number
    documents_requested: number
    documents_received: number
    features_extracted: number
    personas_identified: number
    items_confirmed: number
    items_rejected: number
    feedback_items: number
  }
  portal_items_count: number
  portal_items_completed: number
  prepared_at?: string
  sent_at?: string
  started_at?: string
  completed_at?: string
  created_at: string
  updated_at: string
}

export const createTouchpoint = (projectId: string, data: CreateTouchpointRequest) =>
  apiRequest<Touchpoint>(`/projects/${projectId}/collaboration/touchpoints`, {
    method: 'POST',
    body: JSON.stringify({ ...data, project_id: projectId }),
  })

export const listTouchpoints = (projectId: string, status?: string, type?: string) => {
  const params = new URLSearchParams()
  if (status) params.set('status', status)
  if (type) params.set('type', type)
  const query = params.toString()
  return apiRequest<Touchpoint[]>(`/projects/${projectId}/collaboration/touchpoints${query ? `?${query}` : ''}`)
}

export const completeTouchpoint = (projectId: string, touchpointId: string, outcomes: Record<string, unknown>) =>
  apiRequest<Touchpoint>(`/projects/${projectId}/collaboration/touchpoints/${touchpointId}/complete`, {
    method: 'POST',
    body: JSON.stringify(outcomes),
  })

// ============================================
// Client Packages & Phase Progress APIs
// ============================================

export const getPhaseProgress = (projectId: string) =>
  apiRequest<PhaseProgressResponse>(`/collaboration/projects/${projectId}/progress`)

export const listPendingItems = (projectId: string, itemType?: string, status = 'pending') => {
  const params = new URLSearchParams()
  if (itemType) params.set('item_type', itemType)
  params.set('status', status)
  const query = params.toString()
  return apiRequest<{ items: PendingItem[]; count: number }>(
    `/collaboration/projects/${projectId}/pending-items?${query}`
  )
}

export const removePendingItem = (itemId: string) =>
  apiRequest<{ message: string }>(`/collaboration/pending-items/${itemId}`, {
    method: 'DELETE',
  })

export const generateClientPackage = (projectId: string, request: { item_ids?: string[]; include_asset_suggestions?: boolean; max_questions?: number }) =>
  apiRequest<{ package: ClientPackage; synthesis_notes?: string }>(`/collaboration/projects/${projectId}/generate-package`, {
    method: 'POST',
    body: JSON.stringify(request),
  })

export const getClientPackage = (packageId: string) =>
  apiRequest<ClientPackage>(`/collaboration/packages/${packageId}`)

export const sendClientPackage = (packageId: string) =>
  apiRequest<{ success: boolean; package_id: string; sent_at: string }>(
    `/collaboration/packages/${packageId}/send`,
    { method: 'POST' }
  )

export const markEntityNeedsReview = (
  projectId: string,
  entityType: string,
  entityId: string,
  reason?: string
) =>
  apiRequest<{ success: boolean; message: string; pending_item_id?: string }>(
    `/collaboration/projects/${projectId}/mark-needs-review`,
    {
      method: 'POST',
      body: JSON.stringify({
        entity_type: entityType,
        entity_id: entityId,
        reason,
      }),
    }
  )

// ============================================
// Client Pulse & Activity APIs
// ============================================

export const getClientPulse = (projectId: string) =>
  apiRequest<import('@/types/api').ClientPulse>(
    `/collaboration/projects/${projectId}/pulse`
  )

export const getClientActivity = (projectId: string, limit = 30) =>
  apiRequest<{ items: import('@/types/api').ClientActivityItem[] }>(
    `/collaboration/projects/${projectId}/client-activity?limit=${limit}`
  )

// ============================================
// Meetings APIs
// ============================================

export const listMeetings = (projectId?: string, status?: string, upcomingOnly = false) => {
  const params = new URLSearchParams()
  if (projectId) params.set('project_id', projectId)
  if (status) params.set('status', status)
  if (upcomingOnly) params.set('upcoming_only', 'true')
  const query = params.toString()
  return apiRequest<Meeting[]>(`/meetings${query ? `?${query}` : ''}`)
}

export const listUpcomingMeetings = (limit = 10) =>
  apiRequest<Meeting[]>(`/meetings/upcoming?limit=${limit}`)

export const getMeeting = (meetingId: string) =>
  apiRequest<Meeting>(`/meetings/${meetingId}`)

export const createMeeting = (data: {
  project_id: string
  title: string
  meeting_date: string
  meeting_time: string
  meeting_type?: 'discovery' | 'validation' | 'review' | 'other'
  description?: string
  duration_minutes?: number
  timezone?: string
  stakeholder_ids?: string[]
  agenda?: Record<string, any>
  create_calendar_event?: boolean
  attendee_emails?: string[]
}) =>
  apiRequest<Meeting>('/meetings', {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const updateMeeting = (meetingId: string, data: Partial<{
  title: string
  description: string
  meeting_type: 'discovery' | 'validation' | 'review' | 'other'
  status: 'scheduled' | 'completed' | 'cancelled'
  meeting_date: string
  meeting_time: string
  duration_minutes: number
  timezone: string
  stakeholder_ids: string[]
  agenda: Record<string, any>
  summary: string
  highlights: Record<string, any>
}>) =>
  apiRequest<Meeting>(`/meetings/${meetingId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })

export const deleteMeeting = (meetingId: string) =>
  apiRequest<{ success: boolean; meeting_id: string }>(`/meetings/${meetingId}`, {
    method: 'DELETE',
  })

// ============================================
// Status Narrative APIs
// ============================================

export const getStatusNarrative = (projectId: string, regenerate = false) =>
  apiRequest<StatusNarrative>(`/projects/${projectId}/status-narrative?regenerate=${regenerate}`)

// ============================================
// Communication Integration APIs
// ============================================

// Google OAuth
export const getGoogleStatus = () =>
  apiRequest<GoogleStatusResponse>('/communications/google/status')

export const connectGoogle = (refreshToken: string, scopes: string[]) =>
  apiRequest<GoogleStatusResponse>('/communications/google/connect', {
    method: 'POST',
    body: JSON.stringify({ refresh_token: refreshToken, scopes }),
  })

export const disconnectGoogle = () =>
  apiRequest<{ success: boolean }>('/communications/google/disconnect', {
    method: 'DELETE',
  })

// Integration Settings
export const getIntegrationSettings = () =>
  apiRequest<IntegrationSettings>('/communications/integrations/me')

export const updateIntegrationSettings = (data: {
  calendar_sync_enabled?: boolean
  recording_default?: RecordingDefault
}) =>
  apiRequest<{ success: boolean }>('/communications/integrations/me', {
    method: 'PATCH',
    body: JSON.stringify(data),
  })

// Email Submission
export const submitEmail = (data: {
  project_id: string
  sender: string
  recipients: string[]
  cc?: string[]
  subject: string
  body: string
}) =>
  apiRequest<{ signal_id: string; job_id?: string }>('/communications/emails/submit', {
    method: 'POST',
    body: JSON.stringify(data),
  })

// Email Routing Tokens
export const createEmailToken = (data: {
  project_id: string
  allowed_sender_domain?: string
  allowed_sender_emails?: string[]
  max_emails?: number
}) =>
  apiRequest<EmailTokenResponse>('/communications/email-tokens', {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const listEmailTokens = (projectId: string) =>
  apiRequest<{ tokens: EmailTokenResponse[]; total: number }>(
    `/communications/email-tokens/${projectId}`
  )

export const deactivateEmailToken = (tokenId: string) =>
  apiRequest<{ success: boolean; token_id: string }>(
    `/communications/email-tokens/${tokenId}`,
    { method: 'DELETE' }
  )

// Meeting Bots
export const deployBot = (meetingId: string) =>
  apiRequest<MeetingBot>('/communications/bots/deploy', {
    method: 'POST',
    body: JSON.stringify({ meeting_id: meetingId }),
  })

export const getBotStatus = (meetingId: string) =>
  apiRequest<MeetingBot>(`/communications/bots/${meetingId}`)

export const cancelBot = (botId: string) =>
  apiRequest<{ success: boolean; bot_id: string }>(
    `/communications/bots/${botId}`,
    { method: 'DELETE' }
  )
