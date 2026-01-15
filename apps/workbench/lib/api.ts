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
      prd_sections: number
      features: number
      personas: number
      vp_steps: number
      constraints: number
    }
    counts: {
      prd_sections: number
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

export const getPrdSections = (projectId: string) =>
  apiRequest<any[]>(`/state/prd?project_id=${projectId}`)

export const getVpSteps = (projectId: string) =>
  apiRequest<any[]>(`/state/vp?project_id=${projectId}`)

export const getPersonas = (projectId: string) =>
  apiRequest<any[]>(`/state/personas?project_id=${projectId}`)

export const updatePrdSectionStatus = (sectionId: string, status: string) =>
  apiRequest<any>(`/state/prd/${sectionId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  })

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

export const enrichPrd = (projectId: string, includeResearch = false) =>
  apiRequest<{
    run_id: string
    job_id: string
    sections_processed: number
    sections_updated: number
    summary: string
  }>('/agents/enrich-prd', {
    method: 'POST',
    body: JSON.stringify({
      project_id: projectId,
      include_research: includeResearch,
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
}

export const getReadinessScore = (projectId: string) =>
  apiRequest<ReadinessScore>(`/projects/${projectId}/readiness`)
