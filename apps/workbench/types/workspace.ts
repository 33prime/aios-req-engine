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
  is_stale?: boolean
  stale_reason?: string | null
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
  is_stale?: boolean
  stale_reason?: string | null
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
  is_stale?: boolean
  stale_reason?: string | null
}

export type MoSCoWGroup = 'must_have' | 'should_have' | 'could_have' | 'out_of_scope'

// ============================================
// Workflow Current/Future State Types
// ============================================

export type AutomationLevel = 'manual' | 'semi_automated' | 'fully_automated'

export interface WorkflowStepSummary {
  id: string
  step_index: number
  label: string
  description?: string | null
  actor_persona_id?: string | null
  actor_persona_name?: string | null
  time_minutes?: number | null
  pain_description?: string | null
  benefit_description?: string | null
  automation_level: AutomationLevel
  operation_type?: string | null
  confirmation_status?: string | null
  feature_ids?: string[]
  feature_names?: string[]
}

export interface ROISummary {
  workflow_name: string
  current_total_minutes: number
  future_total_minutes: number
  time_saved_minutes: number
  time_saved_percent: number
  cost_saved_per_week: number
  cost_saved_per_year: number
  steps_automated: number
  steps_total: number
}

export interface WorkflowPair {
  id: string
  name: string
  description?: string
  owner?: string | null
  confirmation_status?: string | null
  current_workflow_id?: string | null
  future_workflow_id?: string | null
  current_steps: WorkflowStepSummary[]
  future_steps: WorkflowStepSummary[]
  roi?: ROISummary | null
  is_stale?: boolean
  stale_reason?: string | null
}

// ============================================
// Data Entity Types
// ============================================

export interface DataEntityFieldDef {
  name: string
  type: string
  required: boolean
  description?: string
  constraints?: string | null
}

export interface DataEntityBRDSummary {
  id: string
  name: string
  description?: string | null
  entity_category: 'domain' | 'reference' | 'transactional' | 'system'
  field_count: number
  workflow_step_count: number
  confirmation_status?: string | null
  evidence?: BRDEvidence[]
  is_stale?: boolean
  stale_reason?: string | null
}

export interface DataEntityWorkflowLink {
  id: string
  vp_step_id: string
  vp_step_label?: string | null
  operation_type: string
  description?: string
}

// ============================================
// Stakeholder Types
// ============================================

export type StakeholderType = 'champion' | 'sponsor' | 'blocker' | 'influencer' | 'end_user'
export type InfluenceLevel = 'high' | 'medium' | 'low'

export interface StakeholderBRDSummary {
  id: string
  name: string
  first_name?: string | null
  last_name?: string | null
  role?: string | null
  email?: string | null
  organization?: string | null
  stakeholder_type?: StakeholderType | null
  influence_level?: InfluenceLevel | null
  is_primary_contact?: boolean
  domain_expertise?: string[]
  confirmation_status?: string | null
  evidence?: BRDEvidence[]
}

export interface StakeholderDetail extends StakeholderBRDSummary {
  project_id: string
  phone?: string | null
  topic_mentions?: Record<string, number> | null
  priorities?: string[] | null
  concerns?: string[] | null
  notes?: string | null
  source_type?: string | null
  engagement_level?: string | null
  decision_authority?: string | null
  engagement_strategy?: string | null
  risk_if_disengaged?: string | null
  win_conditions?: string[] | null
  key_concerns?: string[] | null
  project_name?: string | null
  created_at: string
  updated_at?: string | null
}

export interface StakeholderCreatePayload {
  name: string
  role?: string
  email?: string
  phone?: string
  organization?: string
  stakeholder_type?: StakeholderType
  influence_level?: InfluenceLevel
  domain_expertise?: string[]
  priorities?: string[]
  concerns?: string[]
  notes?: string
}

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
  data_entities: DataEntityBRDSummary[]
  stakeholders: StakeholderBRDSummary[]
  readiness_score: number
  pending_count: number
  workflow_pairs: WorkflowPair[]
  roi_summary: ROISummary[]
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

// ============================================
// Cascading Intelligence Types
// ============================================

export interface ScopeAlert {
  alert_type: string
  severity: 'warning' | 'info'
  message: string
}

export interface BRDHealthData {
  stale_entities: {
    features: { id: string; name: string; stale_reason?: string | null }[]
    personas: { id: string; name: string; stale_reason?: string | null }[]
    vp_steps: { id: string; label?: string; stale_reason?: string | null }[]
    data_entities: { id: string; name: string; stale_reason?: string | null }[]
    strategic_context: { id: string; stale_reason?: string | null }[]
    total_stale: number
  }
  scope_alerts: ScopeAlert[]
  dependency_count: number
  pending_cascade_count: number
}

export interface ImpactAnalysis {
  entity: { type: string; id: string }
  direct_impacts: { type: string; id: string; dependency_type: string; strength: number }[]
  indirect_impacts: { type: string; id: string; dependency_type: string; strength: number; path: string[] }[]
  total_affected: number
  recommendation: 'auto' | 'review_suggested' | 'high_impact_warning'
}

