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
