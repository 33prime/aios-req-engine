import { apiRequest } from './core'

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
// Evidence Quality
// =============================================================================

export interface SourceUsageByEntity {
  feature: number
  persona: number
  vp_step: number
  business_driver: number
  stakeholder: number
  workflow: number
  data_entity: number
  constraint: number
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
 * Signal impact — entities influenced by a specific signal
 */
export interface SignalImpactResponse {
  signal_id: string
  total_impacts: number
  by_entity_type: Record<string, number>
  details: Record<string, Array<{ id: string; label?: string; name?: string; slug?: string }>>
}

export const getSignalImpact = (signalId: string) =>
  apiRequest<SignalImpactResponse>(`/signals/${signalId}/impact`)

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

// =============================================================================
// Intelligence Briefing
// =============================================================================

export const getIntelligenceBriefing = (
  projectId: string,
  maxActions = 5,
  forceRefresh = false,
) =>
  apiRequest<import('@/types/workspace').IntelligenceBriefing>(
    `/projects/${projectId}/workspace/briefing?max_actions=${maxActions}&force_refresh=${forceRefresh}`
  )

export const getProjectHeartbeat = (projectId: string) =>
  apiRequest<import('@/types/workspace').ProjectHeartbeat>(
    `/projects/${projectId}/workspace/heartbeat`
  )

export const promoteHypothesis = (projectId: string, nodeId: string) =>
  apiRequest<{ ok: boolean; node: Record<string, unknown> }>(
    `/projects/${projectId}/workspace/hypotheses/${nodeId}/promote`,
    { method: 'POST' }
  )

// =============================================================================
// Intelligence Module
// =============================================================================

export const getIntelligenceOverview = (projectId: string) =>
  apiRequest<import('@/types/workspace').IntelOverviewResponse>(
    `/projects/${projectId}/intelligence/overview`
  )

export const getIntelligenceGraph = (projectId: string) =>
  apiRequest<import('@/types/workspace').IntelGraphResponse>(
    `/projects/${projectId}/intelligence/graph`
  )

export const getIntelligenceNodeDetail = (projectId: string, nodeId: string) =>
  apiRequest<import('@/types/workspace').IntelNodeDetail>(
    `/projects/${projectId}/intelligence/graph/${nodeId}`
  )

export const submitNodeFeedback = (
  projectId: string,
  nodeId: string,
  action: 'confirm' | 'dispute' | 'archive',
  note?: string,
) =>
  apiRequest<import('@/types/workspace').IntelGraphNode>(
    `/projects/${projectId}/intelligence/graph/${nodeId}/feedback`,
    {
      method: 'POST',
      body: JSON.stringify({ action, note: note || null }),
    }
  )

export const updateIntelligenceNode = (
  projectId: string,
  nodeId: string,
  data: { content?: string; summary?: string; confidence?: number },
) =>
  apiRequest<import('@/types/workspace').IntelGraphNode>(
    `/projects/${projectId}/intelligence/graph/${nodeId}`,
    { method: 'PUT', body: JSON.stringify(data) }
  )

export const createBelief = (
  projectId: string,
  data: {
    statement: string
    domain?: string
    confidence?: number
    linked_entity_type?: string
    linked_entity_id?: string
  },
) =>
  apiRequest<import('@/types/workspace').IntelGraphNode>(
    `/projects/${projectId}/intelligence/graph/nodes`,
    { method: 'POST', body: JSON.stringify(data) }
  )

export const generateBeliefs = (projectId: string) =>
  apiRequest<import('@/types/workspace').IntelGraphNode[]>(
    `/projects/${projectId}/intelligence/beliefs/generate`,
    { method: 'POST' }
  )

export const getIntelligenceEvolution = (
  projectId: string,
  params?: { event_type?: string; days?: number; limit?: number },
) => {
  const qp = new URLSearchParams()
  if (params?.event_type) qp.set('event_type', params.event_type)
  if (params?.days) qp.set('days', params.days.toString())
  if (params?.limit) qp.set('limit', params.limit.toString())
  const query = qp.toString()
  return apiRequest<import('@/types/workspace').IntelEvolutionResponse>(
    `/projects/${projectId}/intelligence/evolution${query ? `?${query}` : ''}`
  )
}

export const getConfidenceCurve = (projectId: string, nodeId: string) =>
  apiRequest<import('@/types/workspace').IntelConfidenceCurve>(
    `/projects/${projectId}/intelligence/evolution/${nodeId}/curve`
  )

export const getEntityEvidence = (projectId: string, entityType: string, entityId: string) =>
  apiRequest<import('@/types/workspace').IntelEvidenceResponse>(
    `/projects/${projectId}/intelligence/evidence/${entityType}/${entityId}`
  )

export const getSalesIntelligence = (projectId: string) =>
  apiRequest<import('@/types/workspace').IntelSalesResponse>(
    `/projects/${projectId}/intelligence/sales`
  )
