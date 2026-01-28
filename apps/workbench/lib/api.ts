const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'

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
  console.log(`🌐 API Request: ${options?.method || 'GET'} ${url}`)

  const startTime = Date.now()

  try {
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

    const duration = Date.now() - startTime
    console.log(`📡 API Response: ${response.status} ${response.statusText} (${duration}ms)`)

    if (!response.ok) {
      let errorText = 'Unknown error'
      try {
        errorText = await response.text()
      } catch (e) {
        console.warn('Could not read error response body:', e)
      }
      console.error(`❌ API Error: ${response.status} - ${errorText}`)
      throw new ApiError(response.status, errorText)
    }

    const data = await response.json()
    console.log(`✅ API Success:`, data)
    return data
  } catch (error) {
    const duration = Date.now() - startTime
    console.error(`💥 API Request Failed (${duration}ms):`, error)
    throw error
  }
}

// Project APIs
export const getBaselineStatus = (projectId: string) =>
  apiRequest<{ baseline_ready: boolean }>(`/projects/${projectId}/baseline`)

export const updateBaselineStatus = (projectId: string, baselineReady: boolean) =>
  apiRequest<{ baseline_ready: boolean }>(`/projects/${projectId}/baseline`, {
    method: 'PATCH',
    body: JSON.stringify({ baseline_ready: baselineReady }),
  })

// Baseline Completeness APIs (Phase 0 - Surgical Updates)
export const getBaselineCompleteness = (projectId: string) =>
  apiRequest<{
    prd_mode: 'initial' | 'maintenance'
    score: number
    breakdown: {
      features: number
      personas: number
      vp_steps: number
      constraints: number
    }
    counts: {
      features: number
      personas: number
      vp_steps: number
    }
    ready: boolean
    missing: string[]
  }>(`/projects/${projectId}/baseline/completeness`)

export const finalizeBaseline = (projectId: string) =>
  apiRequest<{ success: boolean; message: string }>(`/projects/${projectId}/baseline/finalize`, {
    method: 'POST',
    body: JSON.stringify({ confirmed_by: null }),
  })

// State APIs
export const getFeatures = (projectId: string) =>
  apiRequest<any[]>(`/state/features?project_id=${projectId}`)

// PRD sections removed - use features, personas, VP steps instead

export const getVpSteps = (projectId: string) =>
  apiRequest<any[]>(`/state/vp?project_id=${projectId}`)

export const getPersonas = (projectId: string) =>
  apiRequest<any[]>(`/state/personas?project_id=${projectId}`)


export const updateVpStepStatus = (stepId: string, status: string) =>
  apiRequest<any>(`/state/vp/${stepId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  })

export const updateFeatureStatus = (featureId: string, status: string) =>
  apiRequest<any>(`/state/features/${featureId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  })

// Agent APIs
export const buildState = (projectId: string) =>
  apiRequest<{ run_id: string; job_id: string; changed_counts: any; summary: string }>(
    '/state/build',
    {
      method: 'POST',
      body: JSON.stringify({ project_id: projectId }),
    }
  )

export const reconcileState = (projectId: string, includeResearch = false) =>
  apiRequest<{
    run_id: string
    job_id: string
    changed_counts: any
    confirmations_open_count: number
    summary: string
  }>('/state/reconcile', {
    method: 'POST',
    body: JSON.stringify({
      project_id: projectId,
      include_research: includeResearch,
    }),
  })

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

export const runResearchAgent = (
  projectId: string,
  seedContext: {
    client_name: string
    industry: string
    competitors?: string[]
    focus_areas?: string[]
    custom_questions?: string[]
  },
  maxQueries = 15
) =>
  apiRequest<{
    run_id: string
    job_id: string
    signal_id: string
    chunks_created: number
    queries_executed: number
    findings_summary: {
      competitive_features: number
      market_insights: number
      pain_points: number
      technical_considerations: number
    }
  }>('/agents/research', {
    method: 'POST',
    body: JSON.stringify({
      project_id: projectId,
      seed_context: seedContext,
      max_queries: maxQueries,
    }),
  })

export const runATeam = (projectId: string, autoApply = false) =>
  apiRequest<{
    run_id: string
    job_id: string
    patches_generated: number
    patches_auto_applied: number
    patches_queued: number
    insights_processed: number
  }>('/agents/a-team', {
    method: 'POST',
    body: JSON.stringify({
      project_id: projectId,
      auto_apply: autoApply,
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

export const getStrategicFoundationSummary = (projectId: string) =>
  apiRequest<{
    has_company_info: boolean
    has_business_drivers: boolean
    has_competitor_refs: boolean
    has_strategic_context: boolean
    company_name: string | null
    business_driver_count: number
    competitor_count: number
  }>(`/agents/strategic-foundation/${projectId}/summary`)

export const updateCompanyInfo = (projectId: string, data: {
  name?: string | null
  industry?: string | null
  stage?: string | null
  size?: string | null
  company_type?: string | null
  website?: string | null
  revenue?: string | null
  address?: string | null
  location?: string | null
  description?: string | null
  employee_count?: string | null
}) =>
  apiRequest<{ company_info: any; success: boolean }>('/state/company-info', {
    method: 'PUT',
    body: JSON.stringify({ project_id: projectId, ...data }),
  })

export const getPatches = (projectId: string, status = 'queued') =>
  apiRequest<{ patches: any[]; count: number }>(
    `/projects/${projectId}/patches?status=${status}`
  )

export const applyPatch = (insightId: string) =>
  apiRequest<{
    success: boolean
    entity_type: string
    entity_id: string
    changes_applied: Record<string, any>
  }>(`/insights/${insightId}/apply-patch`, { method: 'POST' })

export const dismissPatch = (insightId: string) =>
  apiRequest<{ success: boolean; insight_id: string }>(
    `/insights/${insightId}/dismiss-patch`,
    { method: 'POST' }
  )

// Job APIs
export const getJobStatus = (jobId: string) =>
  apiRequest<any>(`/jobs/${jobId}`)

export const listProjectJobs = (projectId: string, limit = 10) =>
  apiRequest<{ jobs: any[]; count: number }>(`/jobs?project_id=${projectId}&limit=${limit}`)

export const getResearchJobs = (projectId: string) =>
  apiRequest<any[]>(`/jobs?project_id=${projectId}&job_type=research_query&limit=50`)

// Confirmation APIs
export const listConfirmations = (projectId: string, status?: string) => {
  const params = new URLSearchParams({ project_id: projectId })
  if (status) params.set('status', status)
  return apiRequest<{ confirmations: any[]; total: number }>(`/confirmations?${params}`)
}

export const getConfirmation = (confirmationId: string) =>
  apiRequest<any>(`/confirmations/${confirmationId}`)

export const updateConfirmationStatus = (
  confirmationId: string,
  status: string,
  resolutionEvidence?: any
) =>
  apiRequest<any>(`/confirmations/${confirmationId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({
      status,
      resolution_evidence: resolutionEvidence,
    }),
  })

export const getConfirmationsSummary = (projectId: string) =>
  apiRequest<{
    total: number
    by_method: { email: number; meeting: number }
    by_priority: { high: number; medium: number; low: number }
    by_kind: Record<string, any[]>
    recommendation: string
  }>(`/confirmations/summary?project_id=${projectId}`)

export const generateConfirmationEmail = (
  projectId: string,
  options?: {
    confirmationIds?: string[]
    clientName?: string
    projectName?: string
  }
) =>
  apiRequest<{
    subject: string
    body: string
    confirmation_count: number
    confirmations_included: string[]
  }>('/confirmations/generate-email', {
    method: 'POST',
    body: JSON.stringify({
      project_id: projectId,
      confirmation_ids: options?.confirmationIds || [],
      client_name: options?.clientName || '',
      project_name: options?.projectName || '',
    }),
  })

export const generateMeetingAgenda = (
  projectId: string,
  options?: {
    confirmationIds?: string[]
    clientName?: string
    projectName?: string
    meetingDuration?: number
  }
) =>
  apiRequest<{
    title: string
    duration_estimate: string
    agenda: Array<{
      topic: string
      description: string
      time_minutes: number
      confirmation_ids: string[]
    }>
    pre_read: string
    confirmation_count: number
    confirmations_included: string[]
  }>('/confirmations/generate-meeting-agenda', {
    method: 'POST',
    body: JSON.stringify({
      project_id: projectId,
      confirmation_ids: options?.confirmationIds || [],
      client_name: options?.clientName || '',
      project_name: options?.projectName || '',
      meeting_duration: options?.meetingDuration || 30,
    }),
  })

export interface WhoWouldKnowSuggestion {
  stakeholder_id: string
  stakeholder_name: string
  role?: string
  match_score: number
  reasons: string[]
  is_primary_contact: boolean
  suggestion_text?: string
  topic_matches: string[]
}

export const getWhoWouldKnow = (
  projectId: string,
  entityType: 'feature' | 'persona' | 'vp_step',
  entityId: string,
  gapDescription?: string
) =>
  apiRequest<{
    entity_id: string
    entity_type: string
    entity_name?: string
    topics_extracted: string[]
    suggestions: WhoWouldKnowSuggestion[]
    total_suggestions: number
  }>('/confirmations/who-would-know', {
    method: 'POST',
    body: JSON.stringify({
      project_id: projectId,
      entity_type: entityType,
      entity_id: entityId,
      gap_description: gapDescription,
    }),
  })

// Evidence APIs
export const getSignal = (signalId: string) =>
  apiRequest<any>(`/signals/${signalId}`)

export const getSignalChunks = (signalId: string) =>
  apiRequest<{ signal_id: string; chunks: any[]; count: number }>(`/signals/${signalId}/chunks`)

// Projects CRUD APIs
export const listProjects = (status = 'active', search?: string) => {
  const params = new URLSearchParams({ status })
  if (search) params.append('search', search)
  return apiRequest<{ projects: any[]; total: number }>(`/projects?${params}`)
}

export const createProject = (data: { name: string; description?: string; auto_ingest_description?: boolean }) =>
  apiRequest<any>(`/projects`, {
    method: 'POST',
    body: JSON.stringify(data),
  })

// Enhanced project creation with guided context
export interface CreateProjectContextPayload {
  name: string
  problem: string
  beneficiaries: string
  features: string[]
  company_name?: string
  company_website?: string
}

export const createProjectWithContext = (payload: CreateProjectContextPayload) => {
  // Transform the guided creation data into a rich description for the backend
  const description = `## Problem
${payload.problem}

## Who Benefits
${payload.beneficiaries}

## Core Features
${payload.features.map((f, i) => `${i + 1}. ${f}`).join('\n')}`

  return apiRequest<any>('/projects', {
    method: 'POST',
    body: JSON.stringify({
      name: payload.name,
      description,
      auto_ingest_description: true,
      // Pass additional context metadata
      metadata: {
        problem: payload.problem,
        beneficiaries: payload.beneficiaries,
        features: payload.features,
        company_name: payload.company_name,
        company_website: payload.company_website,
      },
    }),
  })
}

export const getProjectDetails = (projectId: string) =>
  apiRequest<any>(`/projects/${projectId}`)

export const updateProject = (projectId: string, updates: { name?: string; description?: string; status?: string; tags?: string[]; metadata?: any }) =>
  apiRequest<any>(`/projects/${projectId}`, {
    method: 'PATCH',
    body: JSON.stringify(updates),
  })

export const archiveProject = (projectId: string) =>
  apiRequest<any>(`/projects/${projectId}`, {
    method: 'DELETE',
  })

// Signals APIs (extended)
export const listProjectSignals = (projectId: string, filters?: { signal_type?: string; source_type?: string }) => {
  const params = new URLSearchParams()
  if (filters?.signal_type) params.append('signal_type', filters.signal_type)
  if (filters?.source_type) params.append('source_type', filters.source_type)
  const queryString = params.toString()
  return apiRequest<{ signals: any[]; total: number }>(`/projects/${projectId}/signals${queryString ? `?${queryString}` : ''}`)
}

export const getSignalImpact = (signalId: string) =>
  apiRequest<any>(`/signals/${signalId}/impact`)

// Analytics APIs
export const getProjectTimeline = (projectId: string, limit = 500) =>
  apiRequest<{ project_id: string; events: any[]; total: number }>(`/projects/${projectId}/analytics/timeline?limit=${limit}`)

export const getChunkUsageAnalytics = (projectId: string, topK = 20) =>
  apiRequest<any>(`/projects/${projectId}/analytics/chunk-usage?top_k=${topK}`)

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

// Proposals APIs
export const listProposals = (projectId: string, status?: string) => {
  const params = new URLSearchParams({ project_id: projectId })
  if (status) params.set('status', status)
  return apiRequest<{
    proposals: Array<{
      id: string
      title: string
      description?: string
      proposal_type: string
      status: string
      creates_count: number
      updates_count: number
      deletes_count: number
      stale_reason?: string | null
      has_conflicts?: boolean
      conflicting_proposals?: string[]
      created_at: string
    }>
    total: number
  }>(`/proposals?${params}`)
}

export const applyProposal = (proposalId: string) =>
  apiRequest<{ success: boolean }>(`/proposals/${proposalId}/apply`, { method: 'POST' })

export const discardProposal = (proposalId: string) =>
  apiRequest<{ success: boolean }>(`/proposals/${proposalId}/discard`, { method: 'POST' })

export const batchApplyProposals = (proposalIds: string[]) =>
  apiRequest<{ applied: number; failed: number }>('/proposals/batch-apply', {
    method: 'POST',
    body: JSON.stringify({ proposal_ids: proposalIds }),
  })

export const batchDiscardProposals = (proposalIds: string[]) =>
  apiRequest<{ discarded: number }>('/proposals/batch-discard', {
    method: 'POST',
    body: JSON.stringify({ proposal_ids: proposalIds }),
  })

// Cascade APIs
export const listPendingCascades = (projectId: string) =>
  apiRequest<{
    cascades: Array<{
      id: string
      source_entity_type: string
      source_entity_id: string
      source_summary: string
      target_entity_type: string
      target_entity_id: string
      target_summary: string
      cascade_type: 'auto' | 'suggested' | 'logged'
      confidence: number
      changes: Record<string, any>
      rationale?: string
      created_at: string
    }>
    total: number
  }>(`/cascades/pending?project_id=${projectId}`)

export const applyCascade = (cascadeId: string) =>
  apiRequest<{ success: boolean }>(`/cascades/${cascadeId}/apply`, { method: 'POST' })

export const dismissCascade = (cascadeId: string) =>
  apiRequest<{ success: boolean }>(`/cascades/${cascadeId}/dismiss`, { method: 'POST' })

// Persona APIs with scores
export const getPersonasWithScores = (projectId: string) =>
  apiRequest<{
    personas: Array<{
      id: string
      name: string
      role: string
      goals?: string[]
      pain_points?: string[]
      coverage_score?: number
      health_score?: number
      confirmation_status?: string
      created_at: string
      updated_at: string
    }>
  }>(`/personas/with-scores?project_id=${projectId}`)

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

// Persona confirmation status update
export const updatePersonaStatus = (personaId: string, status: string) =>
  apiRequest<any>(`/state/personas/${personaId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
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
  apiRequest<any>(`/admin/projects/${projectId}/portal`, {
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

export const getInfoRequests = (projectId: string, phase?: 'pre_call' | 'post_call') => {
  const params = new URLSearchParams()
  if (phase) params.set('phase', phase)
  const query = params.toString()
  return apiRequest<{ info_requests: InfoRequest[]; total: number }>(
    `/admin/projects/${projectId}/info-requests${query ? `?${query}` : ''}`
  )
}

export const generateInfoRequests = (projectId: string, count = 3) =>
  apiRequest<{
    info_requests: InfoRequest[]
    generated_count: number
  }>(`/admin/projects/${projectId}/info-requests/generate`, {
    method: 'POST',
    body: JSON.stringify({ count }),
  })

export const createInfoRequest = (
  projectId: string,
  data: {
    phase: 'pre_call' | 'post_call'
    title: string
    description?: string
    request_type?: 'question' | 'document' | 'tribal_knowledge'
    input_type?: 'text' | 'file' | 'multi_text' | 'text_and_file'
    priority?: 'high' | 'medium' | 'low' | 'none'
    best_answered_by?: string
    why_asking?: string
    example_answer?: string
  }
) =>
  apiRequest<InfoRequest>(`/admin/projects/${projectId}/info-requests`, {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const updateInfoRequest = (
  requestId: string,
  data: Partial<{
    title: string
    description: string
    priority: 'high' | 'medium' | 'low' | 'none'
    best_answered_by: string
    why_asking: string
    example_answer: string
  }>
) =>
  apiRequest<InfoRequest>(`/admin/info-requests/${requestId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })

export const deleteInfoRequest = (requestId: string) =>
  apiRequest<{ success: boolean }>(`/admin/info-requests/${requestId}`, {
    method: 'DELETE',
  })

// ============================================
// Organization APIs
// ============================================

import type {
  Organization,
  OrganizationWithRole,
  OrganizationSummary,
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

export const getOrganizationSummary = (orgId: string) =>
  apiRequest<OrganizationSummary>(`/organizations/${orgId}/summary`)

export const updateOrganization = (orgId: string, data: OrganizationUpdate) =>
  apiRequest<Organization>(`/organizations/${orgId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })

export const deleteOrganization = (orgId: string) =>
  apiRequest<{ message: string; id: string }>(`/organizations/${orgId}`, {
    method: 'DELETE',
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

export const leaveOrganization = (orgId: string) =>
  apiRequest<{ message: string; organization_id: string }>(
    `/organizations/${orgId}/leave`,
    { method: 'POST' }
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

// Organization Projects
export const listOrganizationProjects = (orgId: string) =>
  apiRequest<any[]>(`/organizations/${orgId}/projects`)

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

import type {
  DiscoveryPrepBundle,
  GeneratePrepResponse,
  SendToPortalResponse,
} from '../types/api'

export const getDiscoveryPrep = (projectId: string) =>
  apiRequest<DiscoveryPrepBundle>(`/discovery-prep/${projectId}`)

export const generateDiscoveryPrep = (projectId: string, forceRegenerate = false) =>
  apiRequest<GeneratePrepResponse>(`/discovery-prep/${projectId}/generate`, {
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
  apiRequest<SendToPortalResponse>(`/discovery-prep/${projectId}/send`, {
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

export const deleteDiscoveryPrep = (projectId: string) =>
  apiRequest<{ message: string }>(`/discovery-prep/${projectId}`, {
    method: 'DELETE',
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

export const listTouchpoints = (projectId: string, status?: string, type?: string) => {
  const params = new URLSearchParams()
  if (status) params.set('status', status)
  if (type) params.set('type', type)
  const query = params.toString()
  return apiRequest<any[]>(`/projects/${projectId}/collaboration/touchpoints${query ? `?${query}` : ''}`)
}

export const getTouchpointDetail = (projectId: string, touchpointId: string) =>
  apiRequest<any>(`/projects/${projectId}/collaboration/touchpoints/${touchpointId}`)

export const completeTouchpoint = (projectId: string, touchpointId: string, outcomes: any) =>
  apiRequest<any>(`/projects/${projectId}/collaboration/touchpoints/${touchpointId}/complete`, {
    method: 'POST',
    body: JSON.stringify(outcomes),
  })

// ============================================
// Client Packages & Phase Progress APIs
// ============================================

import type {
  PhaseProgressResponse,
  PendingItemsQueue,
  PendingItem,
  ClientPackage,
  GeneratePackageRequest,
  GeneratePackageResponse,
} from '../types/api'

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

export const addPendingItem = (projectId: string, item: Partial<PendingItem>) =>
  apiRequest<PendingItem>(`/collaboration/projects/${projectId}/pending-items`, {
    method: 'POST',
    body: JSON.stringify(item),
  })

export const removePendingItem = (itemId: string) =>
  apiRequest<{ message: string }>(`/collaboration/pending-items/${itemId}`, {
    method: 'DELETE',
  })

export const generateClientPackage = (projectId: string, request: GeneratePackageRequest) =>
  apiRequest<GeneratePackageResponse>(`/collaboration/projects/${projectId}/generate-package`, {
    method: 'POST',
    body: JSON.stringify(request),
  })

export const getClientPackage = (packageId: string) =>
  apiRequest<ClientPackage>(`/collaboration/packages/${packageId}`)

export const updateClientPackage = (
  packageId: string,
  updates: { questions?: any[]; action_items?: any[] }
) =>
  apiRequest<{ message: string }>(`/collaboration/packages/${packageId}`, {
    method: 'PATCH',
    body: JSON.stringify(updates),
  })

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
  ProjectTask,
  ProjectTasksResponse,
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
  apiRequest<ProjectTasksResponse>(`/projects/${projectId}/tasks`)

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

export const extractCorePain = (projectId: string) =>
  apiRequest<CorePain>(
    `/projects/${projectId}/foundation/extract-core-pain`,
    { method: 'POST' }
  )

export const extractPrimaryPersona = (projectId: string) =>
  apiRequest<PrimaryPersona>(
    `/projects/${projectId}/foundation/extract-primary-persona`,
    { method: 'POST' }
  )

export const identifyWowMoment = (projectId: string) =>
  apiRequest<WowMoment>(
    `/projects/${projectId}/foundation/identify-wow-moment`,
    { method: 'POST' }
  )

export const extractBusinessCase = (projectId: string) =>
  apiRequest<BusinessCase>(
    `/projects/${projectId}/foundation/extract-business-case`,
    { method: 'POST' }
  )

export const extractBudgetConstraints = (projectId: string) =>
  apiRequest<BudgetConstraints>(
    `/projects/${projectId}/foundation/extract-budget-constraints`,
    { method: 'POST' }
  )

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
  return apiRequest<{ logs: any[]; total: number }>(
    `/projects/${projectId}/di-agent/logs${query ? `?${query}` : ''}`
  )
}

export const invalidateDICache = (projectId: string, reason: string) =>
  apiRequest<{ success: boolean; message: string }>(
    `/projects/${projectId}/di-cache/invalidate?reason=${encodeURIComponent(reason)}`,
    { method: 'POST' }
  )

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

export const recalculateTaskPriorities = (projectId: string) =>
  apiRequest<{ total_checked: number; updated_count: number; updated_tasks: { id: string; title: string; old_priority: number; new_priority: number }[] }>(
    `/projects/${projectId}/tasks/recalculate-priorities`,
    { method: 'POST' }
  )

export const recalculatePrioritiesForEntity = (
  projectId: string,
  entityType: string,
  entityId: string
) =>
  apiRequest<{ total_checked: number; updated_count: number; updated_tasks: { id: string; title: string; old_priority: number; new_priority: number }[] }>(
    `/projects/${projectId}/tasks/recalculate-for-entity?entity_type=${encodeURIComponent(entityType)}&entity_id=${encodeURIComponent(entityId)}`,
    { method: 'POST' }
  )

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
