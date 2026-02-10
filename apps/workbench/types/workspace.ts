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

// ============================================
// BRD Canvas Types
// ============================================

export interface BRDEvidence {
  chunk_id?: string | null
  excerpt: string
  source_type: 'signal' | 'research' | 'inferred'
  rationale: string
}

export interface BusinessDriver {
  id: string
  description: string
  driver_type: 'kpi' | 'pain' | 'goal'
  severity?: string | null
  confirmation_status?: string | null
  evidence?: BRDEvidence[]
  associated_persona_names?: string[]
  version?: number | null
  // Pain-specific
  business_impact?: string | null
  affected_users?: string | null
  current_workaround?: string | null
  frequency?: string | null
  // Goal-specific
  success_criteria?: string | null
  owner?: string | null
  goal_timeframe?: string | null
  dependencies?: string | null
  // KPI-specific
  baseline_value?: string | null
  target_value?: string | null
  measurement_method?: string | null
  tracking_frequency?: string | null
  data_source?: string | null
  responsible_team?: string | null
  missing_field_count?: number
}

export interface ConstraintItem {
  id: string
  title: string
  constraint_type: string
  description?: string | null
  severity: string
  confirmation_status?: string | null
  evidence?: BRDEvidence[]
}

export interface PersonaBRDSummary {
  id: string
  name: string
  role?: string | null
  description?: string | null
  persona_type?: string | null
  goals?: string[]
  pain_points?: string[]
  confirmation_status?: string | null
}

export interface VpStepBRDSummary {
  id: string
  step_index: number
  title: string
  description?: string | null
  actor_persona_id?: string | null
  actor_persona_name?: string | null
  confirmation_status?: string | null
  feature_ids?: string[]
  feature_names?: string[]
}

export interface FeatureBRDSummary {
  id: string
  name: string
  description?: string | null
  category?: string | null
  is_mvp: boolean
  priority_group?: string | null
  confirmation_status?: string | null
  vp_step_id?: string | null
  evidence?: BRDEvidence[]
}

export type MoSCoWGroup = 'must_have' | 'should_have' | 'could_have' | 'out_of_scope'

export interface BRDWorkspaceData {
  business_context: {
    background?: string | null
    company_name?: string | null
    industry?: string | null
    pain_points: BusinessDriver[]
    goals: BusinessDriver[]
    vision?: string | null
    success_metrics: BusinessDriver[]
  }
  actors: PersonaBRDSummary[]
  workflows: VpStepBRDSummary[]
  requirements: {
    must_have: FeatureBRDSummary[]
    should_have: FeatureBRDSummary[]
    could_have: FeatureBRDSummary[]
    out_of_scope: FeatureBRDSummary[]
  }
  constraints: ConstraintItem[]
  readiness_score: number
  pending_count: number
}

// ============================================
// Driver Detail Types (for detail drawer)
// ============================================

export interface AssociatedPersona {
  id: string
  name: string
  role?: string | null
  association_reason: string
}

export interface AssociatedFeature {
  id: string
  name: string
  category?: string | null
  confirmation_status?: string | null
  association_reason: string
}

export interface RelatedDriver {
  id: string
  description: string
  driver_type: string
  relationship: string
}

export interface RevisionEntry {
  revision_number: number
  revision_type: string
  diff_summary: string
  changes?: Record<string, unknown> | null
  created_at: string
  created_by?: string | null
}

export interface BusinessDriverDetail {
  id: string
  description: string
  driver_type: string
  severity?: string | null
  confirmation_status?: string | null
  version?: number | null
  evidence: BRDEvidence[]
  // Pain-specific
  business_impact?: string | null
  affected_users?: string | null
  current_workaround?: string | null
  frequency?: string | null
  // Goal-specific
  success_criteria?: string | null
  owner?: string | null
  goal_timeframe?: string | null
  dependencies?: string | null
  // KPI-specific
  baseline_value?: string | null
  target_value?: string | null
  measurement_method?: string | null
  tracking_frequency?: string | null
  data_source?: string | null
  responsible_team?: string | null
  missing_field_count: number
  // Associations
  associated_personas: AssociatedPersona[]
  associated_features: AssociatedFeature[]
  related_drivers: RelatedDriver[]
  // History
  revision_count: number
  revisions: RevisionEntry[]
}

