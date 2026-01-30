/**
 * TypeScript types for the workspace canvas UI
 */

export interface PersonaSummary {
  id: string
  name: string
  role?: string | null
  description?: string | null
  persona_type?: string | null
  confirmation_status?: string | null
  confidence_score?: number | null
}

export interface FeatureSummary {
  id: string
  name: string
  description?: string | null
  is_mvp: boolean
  confirmation_status?: string | null
  vp_step_id?: string | null
}

export interface VpStepSummary {
  id: string
  step_index: number
  title: string
  description?: string | null
  actor_persona_id?: string | null
  actor_persona_name?: string | null
  confirmation_status?: string | null
  features: FeatureSummary[]
}

export interface PortalClientSummary {
  id: string
  email: string
  name?: string | null
  status: 'active' | 'pending' | 'invited'
  last_activity?: string | null
}

export interface CanvasData {
  project_id: string
  project_name: string
  pitch_line?: string | null
  collaboration_phase: string
  portal_phase?: string | null
  prototype_url?: string | null
  prototype_updated_at?: string | null
  readiness_score: number
  personas: PersonaSummary[]
  features: FeatureSummary[]
  vp_steps: VpStepSummary[]
  unmapped_features: FeatureSummary[]
  portal_enabled: boolean
  portal_clients: PortalClientSummary[]
  pending_count: number
}

export interface WorkspaceState {
  phase: 'overview' | 'discovery' | 'build' | 'live'
  canvasData: CanvasData | null
  isLoading: boolean
  error: string | null
}
