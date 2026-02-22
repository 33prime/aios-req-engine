import { apiRequest } from './core'
import type { ClientSummary, ClientDetail, ClientCreatePayload } from '@/types/workspace'
import type {
  ClientSignalSummary,
  ClientIntelligenceLog,
  ClientKnowledgeBase,
  KnowledgeItem,
  CompetitorDeepAnalysis,
  CompetitorSynthesis,
  ProcessDocumentSummary,
  ProcessDocument,
} from '@/types/workspace'

// ============================================================================
// Client Organizations
// ============================================================================

export const listClients = (params?: {
  search?: string
  organization_id?: string
  limit?: number
  offset?: number
}) => {
  const qp = new URLSearchParams()
  if (params?.search) qp.set('search', params.search)
  if (params?.organization_id) qp.set('organization_id', params.organization_id)
  if (params?.limit) qp.set('limit', params.limit.toString())
  if (params?.offset) qp.set('offset', params.offset.toString())
  const query = qp.toString()
  return apiRequest<{ clients: ClientSummary[]; total: number }>(
    `/clients${query ? `?${query}` : ''}`
  )
}

export const getClient = (clientId: string) =>
  apiRequest<ClientDetail>(`/clients/${clientId}`)

export const createClient = (data: ClientCreatePayload) =>
  apiRequest<ClientSummary>(`/clients`, {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const updateClient = (clientId: string, data: Partial<ClientCreatePayload>) =>
  apiRequest<ClientSummary>(`/clients/${clientId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })

export const deleteClient = (clientId: string) =>
  apiRequest<{ success: boolean; message: string }>(`/clients/${clientId}`, {
    method: 'DELETE',
  })

export const enrichClient = (clientId: string) =>
  apiRequest<{ success: boolean; message: string; client_id: string }>(
    `/clients/${clientId}/enrich`,
    { method: 'POST' }
  )

export const linkProjectToClient = (clientId: string, projectId: string) =>
  apiRequest<{ success: boolean; message: string }>(
    `/clients/${clientId}/projects/${projectId}/link`,
    { method: 'POST' }
  )

export const unlinkProjectFromClient = (clientId: string, projectId: string) =>
  apiRequest<{ success: boolean; message: string }>(
    `/clients/${clientId}/projects/${projectId}/link`,
    { method: 'DELETE' }
  )

// =============================================================================
// Discovery Pipeline
// =============================================================================

export const runDiscovery = (
  projectId: string,
  options?: {
    company_name?: string
    company_website?: string
    industry?: string
    focus_areas?: string[]
  }
) =>
  apiRequest<{ job_id: string; status: string; message: string }>(
    `/projects/${projectId}/discover`,
    {
      method: 'POST',
      body: JSON.stringify(options || {}),
    }
  )

export const getDiscoveryProgress = (projectId: string, jobId: string) =>
  apiRequest<{
    job_id: string
    status: string
    phases: Array<{
      phase: string
      status: string
      duration_seconds?: number
      summary?: string
    }>
    current_phase?: string
    cost_so_far_usd: number
    elapsed_seconds: number
    signal_id?: string
    entities_stored?: Record<string, number>
    total_cost_usd?: number
    drivers_count?: number
    competitors_count?: number
  }>(`/projects/${projectId}/discover/progress/${jobId}`)

export interface DiscoveryReadinessReport {
  score: number
  effectiveness_label: string
  have: Array<{ item: string; value: string; weight: number }>
  missing: Array<{ item: string; impact: string; reason: string; weight: number }>
  actions: Array<{ action: string; impact: string; how: string; priority: number }>
  category_scores: Record<string, { score: number; max: number }>
  cost_estimate: number
  potential_savings: number
}

export const getDiscoveryReadiness = (projectId: string) =>
  apiRequest<DiscoveryReadinessReport>(`/projects/${projectId}/discover/readiness`)

// =============================================================================
// Client Intelligence
// =============================================================================

export interface ClientIntelligenceProfile {
  client_id: string
  name: string
  profile_completeness: number
  last_analyzed_at: string | null
  sections: {
    firmographics: {
      company_summary: string | null
      market_position: string | null
      technology_maturity: string | null
      digital_readiness: string | null
      revenue_range: string | null
      employee_count: number | null
      headquarters: string | null
      tech_stack: string[]
    }
    constraints: Array<{
      title: string
      description: string
      category: string
      severity: string
      source: string
      source_detail?: string
      impacts?: string[]
    }>
    role_gaps: Array<{
      role: string
      why_needed: string
      urgency: string
      which_areas?: string[]
    }>
    vision: string | null
    organizational_context: Record<string, unknown>
    competitors: Array<{ name: string; relationship?: string }>
    growth_signals: Array<{ signal: string; type: string }>
  }
  enrichment_status: string
}

export const analyzeClient = (clientId: string) =>
  apiRequest<{ success: boolean; message: string }>(`/clients/${clientId}/analyze`, {
    method: 'POST',
  })

export const getClientIntelligence = (clientId: string) =>
  apiRequest<ClientIntelligenceProfile>(`/clients/${clientId}/intelligence`)

export const getClientStakeholders = (
  clientId: string,
  params?: { stakeholder_type?: string; limit?: number; offset?: number }
) => {
  const qp = new URLSearchParams()
  if (params?.stakeholder_type) qp.set('stakeholder_type', params.stakeholder_type)
  if (params?.limit) qp.set('limit', params.limit.toString())
  if (params?.offset) qp.set('offset', params.offset.toString())
  const query = qp.toString()
  return apiRequest<{ stakeholders: Array<Record<string, unknown>>; total: number }>(
    `/clients/${clientId}/stakeholders${query ? `?${query}` : ''}`
  )
}

export const getClientSignals = (
  clientId: string,
  params?: { signal_type?: string; limit?: number; offset?: number }
) => {
  const qp = new URLSearchParams()
  if (params?.signal_type) qp.set('signal_type', params.signal_type)
  if (params?.limit) qp.set('limit', params.limit.toString())
  if (params?.offset) qp.set('offset', params.offset.toString())
  const query = qp.toString()
  return apiRequest<{ signals: ClientSignalSummary[]; total: number }>(
    `/clients/${clientId}/signals${query ? `?${query}` : ''}`
  )
}

export const getClientIntelligenceLogs = (
  clientId: string,
  params?: { limit?: number; offset?: number }
) => {
  const qp = new URLSearchParams()
  if (params?.limit) qp.set('limit', params.limit.toString())
  if (params?.offset) qp.set('offset', params.offset.toString())
  const query = qp.toString()
  return apiRequest<{ logs: ClientIntelligenceLog[]; total: number }>(
    `/clients/${clientId}/intelligence-logs${query ? `?${query}` : ''}`
  )
}

// ============================================================================
// Client Knowledge Base
// ============================================================================

export const getClientKnowledgeBase = (clientId: string) =>
  apiRequest<ClientKnowledgeBase>(
    `/clients/${clientId}/knowledge-base`
  )

export const addKnowledgeItem = (
  clientId: string,
  category: 'business_processes' | 'sops' | 'tribal_knowledge',
  data: {
    text: string
    source?: 'signal' | 'stakeholder' | 'ai_inferred' | 'manual'
    source_detail?: string
    confidence?: 'high' | 'medium' | 'low'
  }
) =>
  apiRequest<KnowledgeItem>(
    `/clients/${clientId}/knowledge-base/${category}`,
    { method: 'POST', body: JSON.stringify(data) }
  )

export const deleteKnowledgeItem = (
  clientId: string,
  category: 'business_processes' | 'sops' | 'tribal_knowledge',
  itemId: string
) =>
  apiRequest<{ success: boolean }>(
    `/clients/${clientId}/knowledge-base/${category}/${itemId}`,
    { method: 'DELETE' }
  )

// ============================================================================
// Competitor Intelligence
// ============================================================================

export const analyzeCompetitor = (projectId: string, refId: string) =>
  apiRequest<{ status: string; competitor_id: string }>(`/projects/${projectId}/competitors/${refId}/analyze`, {
    method: 'POST',
  })

export const getCompetitorAnalysis = (projectId: string, refId: string) =>
  apiRequest<{
    status: string
    deep_analysis: CompetitorDeepAnalysis | null
    deep_analysis_at?: string
    scraped_pages?: { url: string; title: string; scraped_at: string }[]
  }>(`/projects/${projectId}/competitors/${refId}/analysis`)

export const synthesizeCompetitors = (projectId: string) =>
  apiRequest<CompetitorSynthesis>(`/projects/${projectId}/competitors/synthesize`, {
    method: 'POST',
  })

export const getCompetitorSynthesis = (projectId: string) =>
  apiRequest<{
    raw_text: string
    created_at: string
    competitor_count: number
    competitor_names: string[]
  }>(`/projects/${projectId}/competitors/synthesis`)

export const toggleDesignReference = (projectId: string, refId: string, isDesignRef: boolean) =>
  apiRequest<{ success: boolean; is_design_reference: boolean }>(`/projects/${projectId}/competitors/${refId}/design-reference`, {
    method: 'PATCH',
    body: JSON.stringify({ is_design_reference: isDesignRef }),
  })

// ============================================================================
// Process Documents
// ============================================================================

export const listClientProcessDocuments = (clientId: string) =>
  apiRequest<ProcessDocumentSummary[]>(
    `/process-documents/client/${clientId}`
  )

export const getProcessDocument = (docId: string) =>
  apiRequest<ProcessDocument>(
    `/process-documents/${docId}`
  )

export const generateProcessDocument = (data: {
  project_id: string
  client_id?: string
  source_kb_category: string
  source_kb_item_id: string
}) =>
  apiRequest<ProcessDocument>(
    '/process-documents/generate',
    { method: 'POST', body: JSON.stringify(data) }
  )

export const deleteProcessDocument = (docId: string) =>
  apiRequest<{ success: boolean }>(
    `/process-documents/${docId}`,
    { method: 'DELETE' }
  )
