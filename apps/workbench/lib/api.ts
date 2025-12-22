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

// State APIs
export const getFeatures = (projectId: string) =>
  apiRequest<any[]>(`/state/features?project_id=${projectId}`)

export const getPrdSections = (projectId: string) =>
  apiRequest<any[]>(`/state/prd?project_id=${projectId}`)

export const getVpSteps = (projectId: string) =>
  apiRequest<any[]>(`/state/vp?project_id=${projectId}`)

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

// Job APIs
export const getJobStatus = (jobId: string) =>
  apiRequest<any>(`/jobs/${jobId}`)

export const listProjectJobs = (projectId: string, limit = 10) =>
  apiRequest<{ jobs: any[]; count: number }>(`/jobs?project_id=${projectId}&limit=${limit}`)

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

// Evidence APIs
export const getSignal = (signalId: string) =>
  apiRequest<any>(`/signals/${signalId}`)

export const getSignalChunks = (signalId: string) =>
  apiRequest<{ signal_id: string; chunks: any[]; count: number }>(`/signals/${signalId}/chunks`)
