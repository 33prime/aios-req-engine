import { API_BASE } from './config'
import type {
  Feature,
  VpStep,
  Persona,
  Job,
  Signal,
  Project,
  ProjectDetailWithDashboard,
  StageStatusResponse,
  AdvanceStageRequest,
  AdvanceStageResponse,
  DiscoveryPrepBundle,
  PhaseProgressResponse,
  PendingItem,
  ClientPackage,
} from '../types/api'

// API key fallback disabled - auth is required
// Set NEXT_PUBLIC_BYPASS_AUTH=true to enable API key fallback for testing
const ADMIN_API_KEY = process.env.NEXT_PUBLIC_BYPASS_AUTH === 'true'
  ? process.env.NEXT_PUBLIC_ADMIN_API_KEY
  : undefined

// Module-level access token for authenticated requests
let accessToken: string | null = null

export const setAccessToken = (token: string | null) => {
  accessToken = token
  // Persist to localStorage for page reloads
  if (typeof window !== 'undefined') {
    if (token) {
      localStorage.setItem('access_token', token)
    } else {
      localStorage.removeItem('access_token')
    }
  }
}

export const getAccessToken = () => {
  // Restore from localStorage if not set
  if (!accessToken && typeof window !== 'undefined') {
    accessToken = localStorage.getItem('access_token')
  }
  return accessToken
}

export const clearAuth = () => {
  accessToken = null
  if (typeof window !== 'undefined') {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    // Clear Supabase session storage
    const keysToRemove = Object.keys(localStorage).filter(key =>
      key.startsWith('sb-') || key.includes('supabase')
    )
    keysToRemove.forEach(key => localStorage.removeItem(key))
  }
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

async function apiRequest<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}/v1${endpoint}`

  // Build auth headers - prefer Bearer token, fallback to API key
  const authHeaders: Record<string, string> = {}
  if (accessToken) {
    authHeaders['Authorization'] = `Bearer ${accessToken}`
  } else if (ADMIN_API_KEY) {
    authHeaders['X-API-Key'] = ADMIN_API_KEY
  }

  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders,
      ...options?.headers,
    },
    ...options,
  })

  if (!response.ok) {
    const errorText = await response.text().catch(() => 'Unknown error')
    throw new ApiError(response.status, errorText)
  }

  return response.json()
}

// State APIs
export const getFeatures = (projectId: string) =>
  apiRequest<Feature[]>(`/state/features?project_id=${projectId}`)

// PRD sections removed - use features, personas, VP steps instead

export const getVpSteps = (projectId: string) =>
  apiRequest<VpStep[]>(`/state/vp?project_id=${projectId}`)

export const getPersonas = (projectId: string) =>
  apiRequest<Persona[]>(`/state/personas?project_id=${projectId}`)

// Agent APIs
export const buildState = (projectId: string) =>
  apiRequest<{ run_id: string; job_id: string; changed_counts: Record<string, number>; summary: string }>(
    '/state/build',
    {
      method: 'POST',
      body: JSON.stringify({ project_id: projectId }),
    }
  )

export const enrichFeatures = (
  projectId: string,
  options: {
    onlyMvp?: boolean
    includeResearch?: boolean
  } = {}
) =>
  apiRequest<{
    run_id: string
    job_id: string
    features_processed: number
    features_updated: number
    summary: string
  }>('/agents/enrich-features', {
    method: 'POST',
    body: JSON.stringify({
      project_id: projectId,
      only_mvp: options.onlyMvp,
      include_research: options.includeResearch,
    }),
  })

export const enrichVp = (projectId: string, includeResearch = false) =>
  apiRequest<{
    run_id: string
    job_id: string
    steps_processed: number
    steps_updated: number
    summary: string
  }>('/agents/enrich-vp', {
    method: 'POST',
    body: JSON.stringify({
      project_id: projectId,
      include_research: includeResearch,
    }),
  })

export const enrichPersonas = (
  projectId: string,
  options: {
    personaIds?: string[]
    includeResearch?: boolean
    topKContext?: number
  } = {}
) =>
  apiRequest<{
    run_id: string
    job_id: string
    personas_processed: number
    personas_updated: number
    summary: string
  }>('/agents/enrich-personas', {
    method: 'POST',
    body: JSON.stringify({
      project_id: projectId,
      persona_ids: options.personaIds,
      include_research: options.includeResearch,
      top_k_context: options.topKContext,
    }),
  })

// n8n Research Integration (external research workflow)
export const triggerN8nResearch = (
  projectId: string,
  focusAreas?: string[]
) =>
  apiRequest<{
    job_id: string
    status: string
    message: string
  }>(`/projects/${projectId}/trigger-research`, {
    method: 'POST',
    body: JSON.stringify({
      focus_areas: focusAreas || [],
    }),
  })

// Strategic Foundation APIs
export const runStrategicFoundation = (projectId: string) =>
  apiRequest<{
    job_id: string
    status: string
    message: string
  }>('/agents/strategic-foundation', {
    method: 'POST',
    body: JSON.stringify({ project_id: projectId }),
  })

// Job APIs
export const getJobStatus = (jobId: string) =>
  apiRequest<Job>(`/jobs/${jobId}`)

// Evidence APIs
export const getSignal = (signalId: string) =>
  apiRequest<Signal>(`/signals/${signalId}`)

// Projects CRUD APIs
export const listProjects = (status = 'active', search?: string) => {
  const params = new URLSearchParams({ status })
  if (search) params.append('search', search)
  return apiRequest<{
    projects: ProjectDetailWithDashboard[]
    total: number
    owner_profiles: Record<string, {
      first_name?: string
      last_name?: string
      photo_url?: string
    }>
  }>(`/projects?${params}`)
}

export const createProject = (data: { name: string; description?: string; auto_ingest_description?: boolean }) =>
  apiRequest<Project>(`/projects`, {
    method: 'POST',
    body: JSON.stringify(data),
  })

// Enhanced project creation with guided context
export interface CreateProjectContextPayload {
  name: string
  brief: string
  company_name?: string
  company_website?: string
}

export const createProjectWithContext = (payload: CreateProjectContextPayload) => {
  // Use the brief directly as the description - no transformation needed
  return apiRequest<Project>('/projects', {
    method: 'POST',
    body: JSON.stringify({
      name: payload.name,
      description: payload.brief,
      auto_ingest_description: true,
      // Pass additional context metadata
      metadata: {
        company_name: payload.company_name,
        company_website: payload.company_website,
      },
    }),
  })
}

export const getProjectDetails = (projectId: string) =>
  apiRequest<ProjectDetailWithDashboard>(`/projects/${projectId}`)

// Stage Progression APIs
export const getStageStatus = (projectId: string) =>
  apiRequest<StageStatusResponse>(`/projects/${projectId}/stage-status`)

export const advanceStage = (projectId: string, request: AdvanceStageRequest) =>
  apiRequest<AdvanceStageResponse>(`/projects/${projectId}/stage`, {
    method: 'PATCH',
    body: JSON.stringify(request),
  })

export const updateProject = (projectId: string, updates: { name?: string; description?: string; status?: string; tags?: string[]; metadata?: Record<string, unknown> }) =>
  apiRequest<Project>(`/projects/${projectId}`, {
    method: 'PATCH',
    body: JSON.stringify(updates),
  })

// Revisions APIs
export const listEntityRevisions = (entityType: string, entityId: string, limit = 20) =>
  apiRequest<{
    entity_type: string
    entity_id: string
    revisions: Array<{
      id: string
      entity_type: string
      entity_id: string
      revision_number: number
      change_type: string
      changes: Record<string, any>
      diff_summary: string
      created_at: string
      created_by?: string
      source_signal_id?: string
    }>
    total: number
  }>(`/state/${entityType}/${entityId}/revisions?limit=${limit}`)

// Persona feature coverage (for Gaps tab)
export interface PersonaFeatureCoverage {
  addressed_goals: string[]
  unaddressed_goals: string[]
  feature_matches: Array<{
    goal: string
    features: Array<{ id: string; name: string; match_type: string }>
  }>
  coverage_score: number
}

export const getPersonaCoverage = (personaId: string) =>
  apiRequest<PersonaFeatureCoverage>(`/personas/${personaId}/coverage`)

// Delete Cascade APIs
export interface FeatureCascadeImpact {
  feature: {
    id: string
    name: string
    category?: string
    is_mvp?: boolean
  }
  affected_vp_steps: Array<{ id: string; step_index: number; label: string }>
  affected_personas: Array<{ id: string; name: string; slug?: string }>
  total_vp_steps: number
  total_personas: number
  affected_vp_count: number
  affected_persona_count: number
  impact_percentage: number
  suggest_bulk_rebuild: boolean
}

export interface PersonaCascadeImpact {
  persona: {
    id: string
    name: string
    slug?: string
    role?: string
  }
  affected_features: Array<{ id: string; name: string; category?: string }>
  affected_vp_steps: Array<{ id: string; step_index: number; label: string }>
  total_features: number
  total_vp_steps: number
  total_personas: number
  affected_feature_count: number
  affected_vp_count: number
  impact_percentage: number
  suggest_bulk_rebuild: boolean
}

export interface DeleteFeatureResult {
  deleted: boolean
  feature_id: string
  feature_name: string
  cleaned_personas: Array<{ id: string; name: string }>
  cleaned_persona_count: number
}

export interface DeletePersonaResult {
  deleted: boolean
  persona_id: string
  persona_name: string
  cleaned_features: Array<{ id: string; name: string }>
  cleaned_feature_count: number
}

export const getFeatureCascadeImpact = (featureId: string) =>
  apiRequest<FeatureCascadeImpact>(`/features/${featureId}/impact`)

export const deleteFeature = (featureId: string, cleanupReferences = true) =>
  apiRequest<DeleteFeatureResult>(`/features/${featureId}?cleanup_references=${cleanupReferences}`, {
    method: 'DELETE',
  })

export const getPersonaCascadeImpact = (personaId: string) =>
  apiRequest<PersonaCascadeImpact>(`/personas/${personaId}/impact`)

export const deletePersona = (personaId: string, cleanupReferences = true) =>
  apiRequest<DeletePersonaResult>(`/personas/${personaId}?cleanup_references=${cleanupReferences}`, {
    method: 'DELETE',
  })

// ============================================
// Client Portal Admin APIs
// ============================================

// Portal Configuration
export interface PortalConfig {
  portal_enabled: boolean
  portal_phase?: 'pre_call' | 'post_call' | 'building' | 'testing'
  discovery_call_date?: string
  client_display_name?: string
}

export const getPortalConfig = (projectId: string) =>
  apiRequest<{
    portal_enabled: boolean
    portal_phase: string
    discovery_call_date: string | null
    call_completed_at: string | null
    client_display_name: string | null
  }>(`/projects/${projectId}`)

export const updatePortalConfig = (projectId: string, config: Partial<PortalConfig>) =>
  apiRequest<{ success: boolean }>(`/admin/projects/${projectId}/portal`, {
    method: 'PATCH',
    body: JSON.stringify(config),
  })

// Project Members (Clients)
export interface ProjectMember {
  id: string
  user_id: string
  role: 'consultant' | 'client'
  invited_at: string
  accepted_at: string | null
  user?: {
    id: string
    email: string
    first_name: string | null
    last_name: string | null
    company_name: string | null
  }
}

export const getProjectMembers = async (projectId: string) => {
  const members = await apiRequest<ProjectMember[]>(
    `/admin/projects/${projectId}/members`
  )
  return { members, total: members.length }
}

export const inviteClient = (
  projectId: string,
  data: {
    email: string
    first_name?: string
    last_name?: string
    company_name?: string
    send_email?: boolean
  }
) =>
  apiRequest<{
    user: { id: string; email: string; first_name?: string; last_name?: string }
    project_member: { id: string; role: string }
    magic_link_sent: boolean
    magic_link_error?: string
  }>(`/admin/projects/${projectId}/invite`, {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const removeProjectMember = (projectId: string, userId: string) =>
  apiRequest<{ success: boolean }>(`/admin/projects/${projectId}/members/${userId}`, {
    method: 'DELETE',
  })

export const resendInvite = (projectId: string, userId: string) =>
  apiRequest<{ success: boolean; magic_link_sent: boolean }>(
    `/admin/projects/${projectId}/members/${userId}/resend`,
    { method: 'POST' }
  )

// Info Requests (Pre-call questions, Post-call actions)
export interface InfoRequest {
  id: string
  project_id: string
  phase: 'pre_call' | 'post_call'
  created_by: 'ai' | 'consultant'
  display_order: number
  title: string
  description: string | null
  request_type: 'question' | 'document' | 'tribal_knowledge'
  input_type: 'text' | 'file' | 'multi_text' | 'text_and_file'
  priority: 'high' | 'medium' | 'low' | 'none' | null
  best_answered_by: string | null
  status: 'not_started' | 'in_progress' | 'complete' | 'skipped'
  answer_data: Record<string, any> | null
  why_asking: string | null
  example_answer: string | null
  created_at: string
}

// ============================================
// Organization APIs
// ============================================

import type {
  Organization,
  OrganizationWithRole,
  OrganizationCreate,
  OrganizationUpdate,
  OrganizationMember,
  OrganizationMemberPublic,
  Invitation,
  InvitationWithOrg,
  InvitationCreate,
  Profile,
  ProfileUpdate,
  OrganizationRole,
} from '../types/api'

// Current organization ID (set by org switcher)
let currentOrganizationId: string | null = null

export const setCurrentOrganization = (orgId: string | null) => {
  currentOrganizationId = orgId
}

export const getCurrentOrganization = () => currentOrganizationId

// Helper for org-scoped requests
async function orgApiRequest<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const headers: Record<string, string> = {
    ...(options?.headers as Record<string, string>),
  }

  if (currentOrganizationId) {
    headers['X-Organization-Id'] = currentOrganizationId
  }

  return apiRequest<T>(endpoint, {
    ...options,
    headers,
  })
}

// Organization CRUD
export const listOrganizations = () =>
  apiRequest<OrganizationWithRole[]>('/organizations')

export const createOrganization = (data: OrganizationCreate) =>
  apiRequest<Organization>('/organizations', {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const getOrganization = (orgId: string) =>
  apiRequest<Organization>(`/organizations/${orgId}`)

export const updateOrganization = (orgId: string, data: OrganizationUpdate) =>
  apiRequest<Organization>(`/organizations/${orgId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })

// Organization Members
export const listOrganizationMembers = (orgId: string) =>
  apiRequest<OrganizationMemberPublic[]>(`/organizations/${orgId}/members`)

export const updateMemberRole = (
  orgId: string,
  userId: string,
  role: OrganizationRole
) =>
  apiRequest<OrganizationMember>(`/organizations/${orgId}/members/${userId}`, {
    method: 'PATCH',
    body: JSON.stringify({ organization_role: role }),
  })

export const removeOrganizationMember = (orgId: string, userId: string) =>
  apiRequest<{ message: string; user_id: string }>(
    `/organizations/${orgId}/members/${userId}`,
    { method: 'DELETE' }
  )

// Organization Invitations
export const sendInvitation = (orgId: string, data: InvitationCreate) =>
  apiRequest<Invitation>(`/organizations/${orgId}/invitations`, {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const listInvitations = (orgId: string) =>
  apiRequest<Invitation[]>(`/organizations/${orgId}/invitations`)

export const cancelInvitation = (orgId: string, invitationId: string) =>
  apiRequest<{ message: string; id: string }>(
    `/organizations/${orgId}/invitations/${invitationId}`,
    { method: 'DELETE' }
  )

export const getInvitationByToken = (token: string) =>
  apiRequest<InvitationWithOrg>(`/organizations/invitations/${token}`)

export const acceptInvitation = (token: string) =>
  apiRequest<{
    organization: Organization
    member: OrganizationMember
    message: string
  }>('/organizations/invitations/accept', {
    method: 'POST',
    body: JSON.stringify({ invite_token: token }),
  })

// Profile
export const getMyProfile = () => apiRequest<Profile>('/organizations/profile/me')

export const updateMyProfile = (data: ProfileUpdate) =>
  apiRequest<Profile>('/organizations/profile/me', {
    method: 'PATCH',
    body: JSON.stringify(data),
  })

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
    discovery_prep?: any
    validation?: any
    prototype_feedback?: any
  }
  active_touchpoint: any | null
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
// Meetings APIs
// ============================================

import type {
  Meeting,
  StatusNarrative,
} from '../types/api'

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
// Tasks APIs
// ============================================

export const getProjectTasks = (projectId: string) =>
  apiRequest<{ project_id: string; tasks: Array<{ id: string; title: string; description?: string; priority: 'high' | 'medium' | 'low'; category: string; action_url?: string; action_type?: string; entity_id?: string; entity_type?: string }>; total: number }>(`/projects/${projectId}/tasks`)

// ============================================
// Status Narrative APIs
// ============================================

export const getStatusNarrative = (projectId: string, regenerate = false) =>
  apiRequest<StatusNarrative>(`/projects/${projectId}/status-narrative?regenerate=${regenerate}`)

// ============================================
// Project Status API (for AI Assistant)
// ============================================

export interface ProjectStatusResponse {
  project: {
    id: string
    name: string
    description: string | null
  }
  company: {
    name: string | null
    industry: string | null
    stage: string | null
    location: string | null
    website: string | null
    unique_selling_point: string | null
  } | null
  strategic: {
    pains: Array<{ description: string; status: string | null }>
    goals: Array<{ description: string; status: string | null }>
    kpis: Array<{ description: string; measurement: string | null; status: string | null }>
    total_drivers: number
    confirmed_drivers: number
  }
  market: {
    competitors: Array<{ name: string; notes: string }>
    design_refs: string[]
    constraints: Array<{ name: string; type: string | null }>
  }
  product: {
    features: {
      total: number
      mvp: number
      confirmed: number
      items: Array<{ name: string; is_mvp: boolean; status: string | null }>
    }
    personas: {
      total: number
      primary: number
      confirmed: number
      items: Array<{ name: string; role: string | null; is_primary: boolean }>
    }
    vp_steps: {
      total: number
      items: Array<{ name: string; order: number }>
    }
  }
  stakeholders: {
    total: number
    items: Array<{ name: string; role: string | null; type: string | null }>
  }
  signals: {
    total: number
  }
  readiness: {
    score: number
    blockers: string[]
    suggestions: string[]
  }
}

export const getProjectStatus = (projectId: string) =>
  apiRequest<ProjectStatusResponse>(`/state/project-status?project_id=${projectId}`)

// ============================================
// Readiness Score API
// ============================================

export interface ReadinessFactorScore {
  score: number
  max_score: number
  details: string | null
}

export interface ReadinessRecommendation {
  action: string
  impact: string
  effort: 'low' | 'medium' | 'high'
  priority: number
  dimension: string | null
}

export interface ReadinessDimensionScore {
  score: number
  weight: number
  weighted_score: number
  factors: Record<string, ReadinessFactorScore>
  blockers: string[]
  recommendations: ReadinessRecommendation[]
  summary: string | null
}

export interface ReadinessCapApplied {
  cap_id: string
  limit: number
  reason: string
}

export interface GateAssessment {
  gate_name: string
  is_satisfied: boolean
  confidence: number
  completeness: number
  status: string
  reason_not_satisfied?: string
  how_to_acquire?: string
}

export interface ReadinessScore {
  score: number
  ready: boolean
  threshold: number
  dimensions: Record<string, ReadinessDimensionScore>
  caps_applied: ReadinessCapApplied[]
  top_recommendations: ReadinessRecommendation[]
  computed_at: string
  confirmed_entities: number
  total_entities: number
  client_signals_count: number
  meetings_completed: number
  // Gate-based readiness fields
  phase?: string
  gates?: GateAssessment[]
  gate_score?: number
  total_readiness?: number
  prototype_gates_satisfied?: number
  prototype_gates_total?: number
  build_gates_satisfied?: number
  build_gates_total?: number
}

export const getReadinessScore = (projectId: string) =>
  apiRequest<ReadinessScore>(`/projects/${projectId}/readiness`)

// =============================================================================
// DI Agent - Design Intelligence Agent
// =============================================================================

export interface DIAgentInvokeRequest {
  trigger: string
  trigger_context?: string
  specific_request?: string
}

export interface DIAgentLog {
  id: string
  project_id: string
  trigger: string
  action_type: string
  observation: string
  decision: string
  success: boolean
  created_at: string
}

export interface DIAgentResponse {
  observation: string
  thinking: string
  decision: string
  action_type: string
  tools_called?: Array<{
    tool_name: string
    tool_args: Record<string, any>
    result?: Record<string, any>
    success: boolean
    error?: string | null
  }>
  tool_results?: Array<{ success: boolean; data: any; error?: string }>  // Deprecated - results in tools_called
  guidance?: {
    summary: string
    questions_to_ask?: Array<{
      question: string
      why_ask: string
      listen_for?: string[]
    }>
    signals_to_watch?: string[]
    what_this_unlocks?: string
  }
  readiness_before?: number
  readiness_after?: number
  gates_affected?: string[]
}

export interface CorePain {
  statement: string
  confidence: number
  trigger?: string
  stakes?: string
  who_feels_it?: string
  confirmed_by?: string
}

export interface PrimaryPersona {
  name: string
  role: string
  confidence: number
  context?: string
  pain_experienced?: string
  current_behavior?: string
  desired_outcome?: string
  confirmed_by?: string
}

export interface WowMoment {
  description: string
  confidence: number
  trigger_event?: string
  emotional_response?: string
  level_1_core?: string
  level_2_adjacent?: string
  level_3_unstated?: string
  confirmed_by?: string
}

export interface BusinessCase {
  value_to_business: string
  roi_framing: string
  why_priority: string
  confidence: number
  success_kpis: Array<{
    metric: string
    current_state: string
    target_state: string
    measurement_method: string
    timeframe: string
  }>
  confirmed_by?: string
}

export interface BudgetConstraints {
  budget_range: string
  budget_flexibility: string
  timeline: string
  confidence: number
  hard_deadline?: string
  deadline_driver?: string
  technical_constraints: string[]
  organizational_constraints: string[]
  confirmed_by?: string
}

export interface ProjectFoundation {
  project_id: string
  core_pain?: CorePain
  primary_persona?: PrimaryPersona
  wow_moment?: WowMoment
  design_preferences?: any
  business_case?: BusinessCase
  budget_constraints?: BudgetConstraints
  confirmed_scope?: any
  created_at: string
  updated_at: string
}

export const invokeDIAgent = (
  projectId: string,
  request: DIAgentInvokeRequest
) =>
  apiRequest<DIAgentResponse>(`/projects/${projectId}/di-agent/invoke`, {
    method: 'POST',
    body: JSON.stringify(request),
  })

export const getProjectFoundation = (projectId: string) =>
  apiRequest<ProjectFoundation>(`/projects/${projectId}/foundation`)

export const getDIAgentLogs = (
  projectId: string,
  params?: {
    limit?: number
    offset?: number
    trigger?: string
    action_type?: string
    success_only?: boolean
  }
) => {
  const queryParams = new URLSearchParams()
  if (params?.limit) queryParams.set('limit', params.limit.toString())
  if (params?.offset) queryParams.set('offset', params.offset.toString())
  if (params?.trigger) queryParams.set('trigger', params.trigger)
  if (params?.action_type) queryParams.set('action_type', params.action_type)
  if (params?.success_only) queryParams.set('success_only', 'true')

  const query = queryParams.toString()
  return apiRequest<{ logs: DIAgentLog[]; total: number }>(
    `/projects/${projectId}/di-agent/logs${query ? `?${query}` : ''}`
  )
}

export const invalidateDICache = (projectId: string, reason: string) =>
  apiRequest<{ success: boolean; message: string }>(
    `/projects/${projectId}/di-cache/invalidate?reason=${encodeURIComponent(reason)}`,
    { method: 'POST' }
  )

// ============================================
// Gap Analysis APIs
// ============================================

export interface GapAnalysisResponse {
  foundation: Record<string, any>
  evidence: Record<string, any>
  solution: Record<string, any>
  stakeholders: Record<string, any>
  summary: string
  priority_gaps: Array<{
    type: string
    severity: string
    gate?: string
    description: string
    suggestion?: string
  }>
  phase: string
  total_readiness: number
  counts: {
    total_gaps?: number
    critical_gaps?: number
    high_gaps?: number
    medium_gaps?: number
    low_gaps?: number
  }
}

export interface RequirementsGapsResponse {
  success: boolean
  gaps: Array<{
    gap_type: string
    severity: string
    entity_type?: string
    entity_id?: string
    description: string
    suggestion?: string
  }>
  summary: {
    total_gaps: number
    high_severity: number
    medium_severity: number
    low_severity: number
    most_critical_area?: string
    overall_completeness?: number
  }
  recommendations: string[]
  entities_analyzed: {
    features?: number
    personas?: number
    vp_steps?: number
  }
}

export interface GapFixSuggestionsResponse {
  success: boolean
  suggestions: Array<{
    entity_type: string
    action: string
    title: string
    description: string
    severity?: string
    risk_level?: string
    auto_applicable?: boolean
  }>
  summary: string
  auto_applicable: number
}

export const analyzeGaps = (projectId: string) =>
  apiRequest<GapAnalysisResponse>(`/projects/${projectId}/gaps/analyze`)

export const analyzeRequirementsGaps = (projectId: string, focusAreas?: string[]) => {
  const params = focusAreas?.length ? `?focus_areas=${focusAreas.join(',')}` : ''
  return apiRequest<RequirementsGapsResponse>(`/projects/${projectId}/gaps/requirements${params}`)
}

export const suggestGapFixes = (
  projectId: string,
  maxSuggestions = 5,
  autoApply = false
) => {
  const params = new URLSearchParams()
  params.set('max_suggestions', maxSuggestions.toString())
  if (autoApply) params.set('auto_apply', 'true')
  return apiRequest<GapFixSuggestionsResponse>(
    `/projects/${projectId}/gaps/suggest-fixes?${params.toString()}`,
    { method: 'POST' }
  )
}

// ============================================
// Task APIs
// ============================================

export interface Task {
  id: string
  project_id: string
  title: string
  description?: string
  task_type: 'proposal' | 'gap' | 'manual' | 'enrichment' | 'validation' | 'research' | 'collaboration'
  anchored_entity_type?: string
  anchored_entity_id?: string
  gate_stage?: string
  priority_score: number
  status: 'pending' | 'in_progress' | 'completed' | 'dismissed'
  requires_client_input: boolean
  source_type: string
  source_id?: string
  source_context?: Record<string, unknown>
  completed_at?: string
  completed_by?: string
  completion_method?: string
  completion_notes?: string
  created_at: string
  updated_at: string
}

export interface TaskListResponse {
  tasks: Task[]
  total: number
  has_more: boolean
}

export interface TaskStatsResponse {
  total: number
  by_status: Record<string, number>
  by_type: Record<string, number>
  client_relevant: number
  avg_priority: number
}

export const listTasks = (
  projectId: string,
  params?: {
    status?: string
    task_type?: string
    requires_client_input?: boolean
    limit?: number
    offset?: number
    sort_by?: string
    sort_order?: 'asc' | 'desc'
  }
) => {
  const queryParams = new URLSearchParams()
  if (params?.status) queryParams.set('status', params.status)
  if (params?.task_type) queryParams.set('task_type', params.task_type)
  if (params?.requires_client_input !== undefined) {
    queryParams.set('requires_client_input', params.requires_client_input.toString())
  }
  if (params?.limit) queryParams.set('limit', params.limit.toString())
  if (params?.offset) queryParams.set('offset', params.offset.toString())
  if (params?.sort_by) queryParams.set('sort_by', params.sort_by)
  if (params?.sort_order) queryParams.set('sort_order', params.sort_order)

  const query = queryParams.toString()
  return apiRequest<TaskListResponse>(
    `/projects/${projectId}/tasks${query ? `?${query}` : ''}`
  )
}

export const getTask = (projectId: string, taskId: string) =>
  apiRequest<Task>(`/projects/${projectId}/tasks/${taskId}`)

export const getTaskStats = (projectId: string) =>
  apiRequest<TaskStatsResponse>(`/projects/${projectId}/tasks/stats`)

export const createTask = (
  projectId: string,
  data: {
    title: string
    description?: string
    task_type?: string
    anchored_entity_type?: string
    anchored_entity_id?: string
    gate_stage?: string
    requires_client_input?: boolean
    metadata?: Record<string, unknown>
  }
) =>
  apiRequest<Task>(`/projects/${projectId}/tasks`, {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const updateTask = (
  projectId: string,
  taskId: string,
  data: {
    title?: string
    description?: string
    status?: string
    requires_client_input?: boolean
    priority_score?: number
  }
) =>
  apiRequest<Task>(`/projects/${projectId}/tasks/${taskId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })

export const completeTask = (
  projectId: string,
  taskId: string,
  data?: {
    completion_method?: string
    completion_notes?: string
  }
) =>
  apiRequest<Task>(`/projects/${projectId}/tasks/${taskId}/complete`, {
    method: 'POST',
    body: JSON.stringify(data || {}),
  })

export const dismissTask = (
  projectId: string,
  taskId: string,
  reason?: string
) =>
  apiRequest<Task>(`/projects/${projectId}/tasks/${taskId}/dismiss`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  })

export const bulkCompleteTasks = (
  projectId: string,
  taskIds: string[],
  completionMethod?: string
) =>
  apiRequest<{ processed: number; tasks: Task[] }>(
    `/projects/${projectId}/tasks/bulk/complete`,
    {
      method: 'POST',
      body: JSON.stringify({
        task_ids: taskIds,
        completion_method: completionMethod || 'chat_approval',
      }),
    }
  )

export const bulkDismissTasks = (
  projectId: string,
  taskIds: string[],
  reason?: string
) =>
  apiRequest<{ processed: number; tasks: Task[] }>(
    `/projects/${projectId}/tasks/bulk/dismiss`,
    {
      method: 'POST',
      body: JSON.stringify({ task_ids: taskIds, reason }),
    }
  )

export const syncGapTasks = (projectId: string) =>
  apiRequest<{ synced: boolean; tasks_created: number; task_ids: string[] }>(
    `/projects/${projectId}/tasks/sync/gaps`,
    { method: 'POST' }
  )

export const syncEnrichmentTasks = (projectId: string) =>
  apiRequest<{ synced: boolean; tasks_created: number; task_ids: string[] }>(
    `/projects/${projectId}/tasks/sync/enrichment`,
    { method: 'POST' }
  )

export interface TaskActivity {
  id: string
  task_id: string
  action: 'created' | 'updated' | 'completed' | 'dismissed' | 'reopened'
  actor_id?: string
  actor_type: 'user' | 'system' | 'ai'
  changes?: Record<string, unknown>
  note?: string
  created_at: string
}

export interface TaskActivityListResponse {
  activities: TaskActivity[]
  total: number
}

export const getProjectTaskActivity = (
  projectId: string,
  params?: { limit?: number; offset?: number }
) => {
  const queryParams = new URLSearchParams()
  if (params?.limit) queryParams.set('limit', params.limit.toString())
  if (params?.offset) queryParams.set('offset', params.offset.toString())
  const query = queryParams.toString()
  return apiRequest<TaskActivityListResponse>(
    `/projects/${projectId}/tasks/activity${query ? `?${query}` : ''}`
  )
}

// ============================================
// Project Memory APIs
// ============================================

export interface ProjectMemory {
  decisions: Array<{
    id: string
    content: string
    rationale?: string
    created_at: string
  }>
  learnings: Array<{
    id: string
    content: string
    created_at: string
  }>
  questions: Array<{
    id: string
    content: string
    resolved: boolean
    created_at: string
  }>
}

export const getProjectMemory = (projectId: string) =>
  apiRequest<ProjectMemory>(`/projects/${projectId}/memory`)

export const addToMemory = (
  projectId: string,
  type: string,
  content: string,
  rationale?: string
) =>
  apiRequest<{ id: string; type: string; content: string }>(
    `/projects/${projectId}/memory/${type}`,
    {
      method: 'POST',
      body: JSON.stringify({ content, rationale }),
    }
  )

export const getMemoryContent = (projectId: string) =>
  apiRequest<{
    content: string | null
    last_updated_by: string | null
    tokens_estimate: number | null
    message?: string
  }>(`/projects/${projectId}/memory/content`)

export const synthesizeMemory = (projectId: string) =>
  apiRequest<{
    success: boolean
    message: string
    content_preview: string | null
  }>(`/projects/${projectId}/memory/synthesize`, { method: 'POST' })

export const compactMemory = (projectId: string, force = false) =>
  apiRequest<{
    compacted: boolean
    reason?: string
    method?: string
    before_tokens?: number
    after_tokens?: number
    reduction_percent?: number
    landmarks_preserved?: number
    landmarks?: string[]
  }>(`/projects/${projectId}/memory/compact?force=${force}`, { method: 'POST' })

// ============================================
// Unified Memory APIs
// ============================================

export interface UnifiedMemoryFreshness {
  age_seconds: number
  age_human: string
}

export interface UnifiedMemoryResponse {
  content: string
  synthesized_at: string
  is_stale: boolean
  stale_reason: string | null
  freshness: UnifiedMemoryFreshness
}

/**
 * Get the unified synthesized memory document.
 * Returns cached content if fresh, otherwise generates new synthesis.
 */
export const getUnifiedMemory = (projectId: string) =>
  apiRequest<UnifiedMemoryResponse>(`/projects/${projectId}/memory/unified`)

/**
 * Force re-synthesis of the unified memory document.
 */
export const refreshUnifiedMemory = (projectId: string) =>
  apiRequest<UnifiedMemoryResponse>(
    `/projects/${projectId}/memory/unified/refresh`,
    { method: 'POST' }
  )

// =============================================================================
// Memory Visualization
// =============================================================================

export interface MemoryNodeViz {
  id: string
  node_type: 'fact' | 'belief' | 'insight'
  summary: string
  content: string
  confidence: number
  belief_domain: string | null
  insight_type: string | null
  source_type: string | null
  linked_entity_type: string | null
  created_at: string
  support_count: number
  contradict_count: number
}

export interface MemoryEdgeViz {
  id: string
  from_node_id: string
  to_node_id: string
  edge_type: string
  strength: number
  rationale: string | null
}

export interface MemoryDecisionViz {
  id: string
  title: string
  decision: string
  rationale: string
  confidence: number
  decision_type: string
  is_landmark: boolean
  created_at: string
}

export interface MemoryLearningViz {
  id: string
  title: string
  learning: string
  learning_type: string
  domain: string | null
  times_applied: number
  created_at: string
}

export interface MemoryGraphStats {
  total_nodes: number
  facts_count: number
  beliefs_count: number
  insights_count: number
  total_edges: number
  edges_by_type: Record<string, number>
  average_belief_confidence: number
  decisions_count?: number
  learnings_count?: number
  sources_count?: number
}

export interface MemoryVisualizationResponse {
  stats: MemoryGraphStats
  nodes: MemoryNodeViz[]
  edges: MemoryEdgeViz[]
  decisions: MemoryDecisionViz[]
  learnings: MemoryLearningViz[]
}

export interface BeliefHistoryEntry {
  id: string
  node_id: string
  previous_content: string
  new_content: string
  previous_confidence: number
  new_confidence: number
  change_type: string
  change_reason: string
  triggered_by_node_id: string | null
  created_at: string
}

export const getMemoryVisualization = (projectId: string) =>
  apiRequest<MemoryVisualizationResponse>(`/projects/${projectId}/memory/visualize`)

export const getBeliefHistory = (projectId: string, beliefId: string) =>
  apiRequest<{ history: BeliefHistoryEntry[] }>(
    `/projects/${projectId}/memory/belief-history?belief_id=${beliefId}`
  )

// =============================================================================
// Requirements Intelligence
// =============================================================================

export interface InformationGap {
  id: string
  gap_type: string
  severity: string
  title: string
  description: string
  how_to_fix: string
}

export interface SuggestedSource {
  source_type: string
  title: string
  description: string
  why_valuable: string
  likely_owner_role: string
  priority: string
  related_gaps: string[]
}

export interface StakeholderIntel {
  stakeholder_id: string | null
  name: string | null
  role: string
  organization: string | null
  stakeholder_type: string | null
  influence_level: string | null
  is_known: boolean
  is_primary_contact: boolean
  likely_knowledge: string[]
  domain_expertise: string[]
  concerns: string[]
  priorities: string[]
  engagement_tip: string | null
}

export interface TribalKnowledge {
  title: string
  description: string
  why_undocumented: string
  best_asked_of: string
  conversation_starters: string[]
  related_gaps: string[]
}

export interface RequirementsIntelligenceResponse {
  summary: string
  phase: string
  total_readiness: number
  information_gaps: InformationGap[]
  suggested_sources: SuggestedSource[]
  stakeholder_intelligence: StakeholderIntel[]
  tribal_knowledge: TribalKnowledge[]
  counts: {
    gaps: number
    sources: number
    stakeholders_known: number
    stakeholders_suggested: number
    tribal: number
  }
}

export const getRequirementsIntelligence = (projectId: string) =>
  apiRequest<RequirementsIntelligenceResponse>(
    `/projects/${projectId}/evidence/intelligence`
  )

// =============================================================================
// Document Upload
// =============================================================================

export interface DocumentUploadResponse {
  id: string
  project_id: string
  original_filename: string
  file_type: string
  file_size_bytes: number
  processing_status: string
  is_duplicate: boolean
  duplicate_of?: string
}

export interface DocumentStatusResponse {
  id: string
  processing_status: 'pending' | 'processing' | 'completed' | 'failed'
  original_filename: string
  message?: string
  started_at?: string
  completed_at?: string
  duration_ms?: number
  document_class?: string
  page_count?: number
  word_count?: number
  total_chunks?: number
  signal_id?: string
  error?: string
}

/**
 * Upload a document for processing.
 * Uses FormData for multipart upload.
 */
export const uploadDocument = async (
  projectId: string,
  file: File,
  uploadSource: string = 'workbench',
  authority: string = 'consultant'
): Promise<DocumentUploadResponse> => {
  const url = `${API_BASE}/v1/projects/${projectId}/documents`

  const formData = new FormData()
  formData.append('file', file)
  formData.append('upload_source', uploadSource)
  formData.append('authority', authority)

  const token = getAccessToken()
  const headers: HeadersInit = {}

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  } else if (ADMIN_API_KEY) {
    headers['X-API-Key'] = ADMIN_API_KEY
  }

  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: formData,
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Upload failed' }))
    throw new ApiError(response.status, errorData.detail || 'Upload failed')
  }

  return response.json()
}

/**
 * Get document processing status.
 */
export const getDocumentStatus = (documentId: string) =>
  apiRequest<DocumentStatusResponse>(`/documents/${documentId}/status`)

/**
 * Trigger immediate processing of a document.
 */
export const processDocument = (documentId: string) =>
  apiRequest<{ success: boolean }>(`/documents/${documentId}/process`, { method: 'POST' })

// ============================================================================
// Sources Tab Redesign API Functions
// ============================================================================

/**
 * Document summary with usage stats
 */
export interface DocumentContributedTo {
  features: number
  personas: number
  vp_steps: number
  other: number
}

export interface DocumentSummaryItem {
  id: string
  original_filename: string
  file_type: string
  file_size_bytes: number
  page_count: number | null
  created_at: string
  content_summary: string | null
  usage_count: number
  contributed_to: DocumentContributedTo
  confidence_level: string
  processing_status: string
  // Analysis fields from document classification
  quality_score?: number
  relevance_score?: number
  information_density?: number
  keyword_tags?: string[]
  key_topics?: string[]
}

export interface DocumentSummaryResponse {
  documents: DocumentSummaryItem[]
  total: number
}

/**
 * Get documents with AI summaries and usage statistics.
 */
export const getDocumentsSummary = (projectId: string) =>
  apiRequest<DocumentSummaryResponse>(`/projects/${projectId}/documents/summary`)

/**
 * Get a signed download URL for a document.
 */
export interface DocumentDownloadResponse {
  download_url: string
  filename: string
  mime_type: string
}

export const getDocumentDownloadUrl = (documentId: string) =>
  apiRequest<DocumentDownloadResponse>(`/documents/${documentId}/download`)

/**
 * Withdraw a document (soft delete).
 * Removes from retrieval but preserves data for audit.
 */
export const withdrawDocument = (documentId: string) =>
  apiRequest<{ status: string; document_id: string }>(
    `/documents/${documentId}/withdraw`,
    { method: 'POST' }
  )

/**
 * Hard delete a document (only for failed/pending documents).
 */
export const deleteDocument = (documentId: string, force = false) =>
  apiRequest<{ success: boolean; message: string }>(
    `/documents/${documentId}${force ? '?force=true' : ''}`,
    { method: 'DELETE' }
  )

/**
 * Source usage aggregation
 */
export interface SourceUsageByEntity {
  feature: number
  persona: number
  vp_step: number
  business_driver: number
}

export interface SourceUsageItem {
  source_id: string
  source_type: string
  source_name: string
  signal_type: string | null
  total_uses: number
  uses_by_entity: SourceUsageByEntity
  last_used: string | null
  entities_contributed: string[]
  content?: string | null  // Full content for research signals
}

export interface SourceUsageResponse {
  sources: SourceUsageItem[]
}

/**
 * Get usage statistics for all sources in a project.
 */
export const getSourceUsage = (projectId: string) =>
  apiRequest<SourceUsageResponse>(`/projects/${projectId}/sources/usage`)

/**
 * Evidence quality breakdown
 */
export interface ConfirmationStatusCount {
  count: number
  percentage: number
}

export interface EvidenceBreakdown {
  confirmed_client: ConfirmationStatusCount
  confirmed_consultant: ConfirmationStatusCount
  needs_client: ConfirmationStatusCount
  ai_generated: ConfirmationStatusCount
}

export interface EntityTypeBreakdown {
  confirmed_client: number
  confirmed_consultant: number
  needs_client: number
  ai_generated: number
}

export interface EvidenceQualityResponse {
  breakdown: EvidenceBreakdown
  by_entity_type: Record<string, EntityTypeBreakdown>
  total_entities: number
  strong_evidence_percentage: number
  summary: string
}

/**
 * Get evidence quality breakdown for a project.
 */
export const getEvidenceQuality = (projectId: string) =>
  apiRequest<EvidenceQualityResponse>(`/projects/${projectId}/evidence/quality`)

// ============================================
// Workspace Canvas APIs
// ============================================

import type { CanvasData } from '@/types/workspace'
import type {
  Prototype,
  FeatureOverlay,
  PrototypeSession,
  PrototypeFeedback,
  SubmitFeedbackRequest,
  SessionContext,
  PromptAuditResult,
} from '../types/prototype'

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
// Prototype Refinement APIs
// ============================================

export const generatePrototype = (projectId: string) =>
  apiRequest<{ prototype_id: string; prompt_length: number; features_included: number; flows_included: number }>('/prototypes/generate', {
    method: 'POST',
    body: JSON.stringify({ project_id: projectId }),
  })

export const ingestPrototype = (projectId: string, repoUrl: string, deployUrl?: string) =>
  apiRequest<{ prototype_id: string; local_path: string; handoff_found: boolean; status: string }>('/prototypes/ingest', {
    method: 'POST',
    body: JSON.stringify({ project_id: projectId, repo_url: repoUrl, deploy_url: deployUrl }),
  })

export const getPrototype = (prototypeId: string) =>
  apiRequest<Prototype>(`/prototypes/${prototypeId}`)

export const getPrototypeForProject = (projectId: string) =>
  apiRequest<Prototype>(`/prototypes/by-project/${projectId}`)

export const getPrototypeOverlays = (prototypeId: string) =>
  apiRequest<FeatureOverlay[]>(`/prototypes/${prototypeId}/overlays`)

export const getPrototypeAudit = (prototypeId: string) =>
  apiRequest<PromptAuditResult | { message: string }>(`/prototypes/${prototypeId}/audit`)

export const triggerPrototypeAnalysis = (prototypeId: string) =>
  apiRequest<{ prototype_id: string; run_id: string; features_analyzed: number; errors: number; status: string }>(
    `/prototypes/${prototypeId}/analyze`,
    { method: 'POST' }
  )

export const retryPrototype = (prototypeId: string) =>
  apiRequest<{ prototype_id: string; prompt_version: number; prompt_length: number }>(
    `/prototypes/${prototypeId}/retry`,
    { method: 'POST' }
  )

// Prototype Sessions
export const createPrototypeSession = (prototypeId: string) =>
  apiRequest<PrototypeSession>('/prototype-sessions', {
    method: 'POST',
    body: JSON.stringify({ prototype_id: prototypeId }),
  })

export const getPrototypeSession = (sessionId: string) =>
  apiRequest<PrototypeSession>(`/prototype-sessions/${sessionId}`)

export const submitPrototypeFeedback = (sessionId: string, data: SubmitFeedbackRequest) =>
  apiRequest<PrototypeFeedback>(`/prototype-sessions/${sessionId}/feedback`, {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const prototypeSessionChat = (sessionId: string, message: string, context?: SessionContext) =>
  apiRequest<{ response: string; extracted_feedback: Record<string, unknown>[] }>(
    `/prototype-sessions/${sessionId}/chat`,
    {
      method: 'POST',
      body: JSON.stringify({ message, context }),
    }
  )

export const endConsultantReview = (sessionId: string) =>
  apiRequest<{ session_id: string; client_review_token: string; client_review_url: string }>(
    `/prototype-sessions/${sessionId}/end-review`,
    { method: 'POST' }
  )

export const synthesizePrototypeFeedback = (sessionId: string) =>
  apiRequest<{
    session_id: string
    features_with_feedback: number
    new_features_discovered: number
    high_priority_changes: number
    session_summary: string
  }>(`/prototype-sessions/${sessionId}/synthesize`, { method: 'POST' })

export const triggerPrototypeCodeUpdate = (sessionId: string) =>
  apiRequest<{
    session_id: string
    files_changed: number
    build_passed: boolean
    commit_sha: string | null
    summary: string
  }>(`/prototype-sessions/${sessionId}/update-code`, { method: 'POST' })

export const getPrototypeClientData = (sessionId: string, token: string) =>
  apiRequest<{
    deploy_url: string | null
    session_number: number
    features_analyzed: number
    questions: Array<{ id: string; question: string; category: string; priority: string }>
  }>(`/prototype-sessions/${sessionId}/client-data?token=${token}`)

/**
 * Map a feature to a value path step (or unmap if stepId is null).
 */
export const mapFeatureToStep = (
  projectId: string,
  featureId: string,
  vpStepId: string | null
) =>
  apiRequest<{ success: boolean; feature_id: string; vp_step_id: string | null }>(
    `/projects/${projectId}/workspace/features/${featureId}/map-to-step`,
    {
      method: 'PATCH',
      body: JSON.stringify({ vp_step_id: vpStepId }),
    }
  )
