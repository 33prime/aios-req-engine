const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8001'

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
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
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

export const runRedTeam = (projectId: string, includeResearch = false) =>
  apiRequest<{
    run_id: string
    job_id: string
    insights_count: number
    summary: string
  }>('/agents/red-team', {
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

// Insights APIs
export const getInsights = (projectId: string) =>
  apiRequest<any[]>(`/insights?project_id=${projectId}`)

export const applyInsight = (insightId: string) =>
  apiRequest<any>(`/insights/${insightId}/apply`, {
    method: 'PATCH',
  })

export const confirmInsight = (insightId: string) =>
  apiRequest<any>(`/insights/${insightId}/confirm`, {
    method: 'POST',
  })

export const dismissInsight = (insightId: string) =>
  apiRequest<any>(`/insights/${insightId}/dismiss`, {
    method: 'PATCH',
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
