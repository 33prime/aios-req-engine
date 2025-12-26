// API response types matching the backend schemas

export interface Job {
  id: string
  project_id?: string
  job_type: string
  status: 'queued' | 'processing' | 'completed' | 'failed'
  input: any
  output: any
  error?: string
  run_id: string
  created_at: string
  started_at?: string
  completed_at?: string
}

export interface BaselineStatus {
  baseline_ready: boolean
}

export interface Feature {
  id: string
  name: string
  category: string
  is_mvp: boolean
  status: string
  confidence: string
  details?: any
  evidence: any[]
  created_at: string
  updated_at: string
}

export interface PrdSection {
  id: string
  slug: string
  label: string
  required: boolean
  status: string
  fields: any
  enrichment?: any
  evidence?: any[]
  created_at: string
  updated_at: string
}

export interface VpStep {
  id: string
  step_index: number
  label: string
  status: string
  description: string
  enrichment?: any
  created_at: string
  updated_at: string
}

export interface Confirmation {
  id: string
  kind: 'prd' | 'vp' | 'feature' | 'insight' | 'gate'
  title: string
  why: string
  ask: string
  status: 'open' | 'queued' | 'resolved' | 'dismissed'
  priority: 'low' | 'medium' | 'high'
  suggested_method: 'email' | 'meeting'
  evidence: Array<{
    chunk_id: string
    excerpt: string
    rationale: string
  }>
  created_at: string
  updated_at: string
}

export interface Signal {
  id: string
  project_id: string
  source: string
  signal_type: string
  raw_text: string
  metadata: any
  created_at: string
}

export interface SignalChunk {
  chunk_index: number
  content: string
  start_char: number
  end_char: number
  metadata?: any
}

export interface Insight {
  id: string
  project_id: string
  title: string
  severity: 'minor' | 'important' | 'critical'
  gate: 'completeness' | 'validation' | 'assumption' | 'scope' | 'wow'
  finding: string
  why: string
  ask: string
  targets: Array<{
    kind: string
    entity_id: string
    label: string
  }>
  evidence: Array<{
    chunk_id: string
    excerpt: string
    rationale: string
  }>
  status: string
  decision?: string
  created_at: string
  updated_at: string
}

export interface AgentRunResponse {
  run_id: string
  job_id: string
  summary: string
}

export interface EnrichmentResponse extends AgentRunResponse {
  features_processed?: number
  features_updated?: number
  sections_processed?: number
  sections_updated?: number
  steps_processed?: number
  steps_updated?: number
}

// Projects
export interface Project {
  id: string
  name: string
  description?: string
  prd_mode: 'initial' | 'maintenance'
  status: 'active' | 'archived' | 'completed'
  created_at: string
  updated_at?: string
  signal_id?: string // ID of auto-ingested description signal
}

export interface ProjectDetail extends Project {
  counts: {
    signals: number
    prd_sections: number
    vp_steps: number
    features: number
    insights: number
    personas: number
  }
}

// Signals with counts
export interface SignalWithCounts extends Signal {
  chunk_count: number
  impact_count: number
  source_label?: string
  source_type?: string
  source_timestamp?: string
}

// Signal impact
export interface EntityImpactDetail {
  id: string
  label: string
  slug: string
}

export interface SignalImpactResponse {
  signal_id: string
  total_impacts: number
  by_entity_type: Record<string, number>
  details: Record<string, EntityImpactDetail[]>
}

// Timeline
export interface TimelineEvent {
  id: string
  type: 'signal_ingested' | 'prd_section_created' | 'vp_step_created' | 'feature_created' | 'insight_created' | 'baseline_finalized'
  timestamp: string
  description: string
  metadata: any
}

// Analytics
export interface ChunkUsageAnalytics {
  project_id: string
  top_chunks: Array<{
    chunk_id: string
    signal_id: string
    chunk_index: number
    content_preview: string
    citation_count: number
  }>
  total_citations: number
  citations_by_entity_type: Record<string, number>
  unused_signals: SignalWithCounts[]
  unused_signals_count: number
}
