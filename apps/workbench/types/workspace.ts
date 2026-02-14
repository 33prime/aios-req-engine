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

export type VisionAlignment = 'high' | 'medium' | 'low' | 'unrelated'

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
  // Monetary impact (KPI)
  monetary_value_low?: number | null
  monetary_value_high?: number | null
  monetary_type?: 'cost_reduction' | 'revenue_increase' | 'revenue_new' | 'risk_avoidance' | 'productivity_gain' | null
  monetary_timeframe?: 'annual' | 'monthly' | 'quarterly' | 'per_transaction' | 'one_time' | null
  monetary_confidence?: number | null
  monetary_source?: string | null
  // Relatability intelligence
  relatability_score?: number
  linked_feature_count?: number
  linked_persona_count?: number
  linked_workflow_count?: number
  vision_alignment?: VisionAlignment | null
  is_stale?: boolean
  stale_reason?: string | null
}

export interface ConstraintItem {
  id: string
  title: string
  constraint_type: string
  description?: string | null
  severity: string
  confirmation_status?: string | null
  evidence?: BRDEvidence[]
  source?: 'extracted' | 'manual' | 'ai_inferred'
  confidence?: number | null
  linked_feature_ids?: string[]
  linked_vp_step_ids?: string[]
  linked_data_entity_ids?: string[]
  impact_description?: string | null
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
  canvas_role?: 'primary' | 'secondary' | null
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
// Unlock Types (shared between step and workflow level)
// ============================================

export type UnlockType = 'capability' | 'scale' | 'insight' | 'speed'

export interface StepUnlock {
  description: string
  unlock_type: UnlockType
  enabled_by: string
  strategic_value: string
  linked_goal_id?: string | null
}

// ============================================
// Workflow Detail Types (for workflow-level drawer)
// ============================================

export interface StepUnlockSummary {
  description: string
  unlock_type: UnlockType
  enabled_by: string
  strategic_value: string
  linked_goal_id?: string | null
  source_step_id?: string | null
  source_step_label?: string | null
}

export interface WorkflowInsight {
  insight_type: 'gap' | 'warning' | 'opportunity' | 'strength'
  severity: 'info' | 'warning'
  message: string
  suggestion?: string | null
}

export interface WorkflowDetail {
  id: string
  name: string
  description?: string
  owner?: string | null
  state_type?: string | null
  confirmation_status?: string | null

  current_workflow_id?: string | null
  future_workflow_id?: string | null
  current_steps: WorkflowStepSummary[]
  future_steps: WorkflowStepSummary[]

  roi?: ROISummary | null

  actor_personas: LinkedPersona[]
  business_drivers: LinkedBusinessDriver[]
  features: LinkedFeature[]
  data_entities: LinkedDataEntity[]

  strategic_unlocks: StepUnlockSummary[]
  insights: WorkflowInsight[]

  revision_count: number
  revisions: RevisionEntry[]

  steps_without_actor: number
  steps_without_time: number
  steps_without_features: number
  enriched_step_count: number
  total_step_count: number
}

// ============================================
// Workflow Step Detail Types (for detail drawer)
// ============================================

export interface LinkedBusinessDriver {
  id: string
  description: string
  driver_type: string
  severity?: string | null
  vision_alignment?: string | null
}

export interface LinkedFeature {
  id: string
  name: string
  category?: string | null
  priority_group?: string | null
  confirmation_status?: string | null
}

export interface LinkedDataEntity {
  id: string
  name: string
  entity_category: string
  operation_type: string
}

export interface LinkedPersona {
  id: string
  name: string
  role?: string | null
}

export interface StepInsight {
  insight_type: 'gap' | 'warning' | 'opportunity' | 'overlap'
  severity: 'info' | 'warning'
  message: string
  suggestion?: string | null
}

export interface WorkflowStepDetail {
  // Identity
  id: string
  step_index: number
  label: string
  description?: string | null
  workflow_id?: string | null
  workflow_name?: string | null
  state_type?: string | null

  // Step fields
  time_minutes?: number | null
  pain_description?: string | null
  benefit_description?: string | null
  automation_level: string
  operation_type?: string | null
  confirmation_status?: string | null

  // Actor
  actor?: LinkedPersona | null

  // Connections
  business_drivers: LinkedBusinessDriver[]
  features: LinkedFeature[]
  data_entities: LinkedDataEntity[]

  // Counterpart comparison
  counterpart_step?: WorkflowStepSummary | null
  counterpart_state_type?: string | null
  time_delta_minutes?: number | null
  automation_delta?: string | null

  // Evidence
  evidence: Array<Record<string, unknown>>

  // Intelligence
  insights: StepInsight[]

  // History
  revision_count: number
  revisions: RevisionEntry[]

  // Staleness
  is_stale: boolean
  stale_reason?: string | null

  // Enrichment
  enrichment_status?: string | null
  enrichment_data?: {
    narrative?: string | null
    optimization_suggestions?: string[]
    risk_assessment?: string | null
    automation_opportunity_score?: number
    automation_approach?: string | null
    unlocks?: StepUnlock[]
    dependencies?: string[]
    complexity?: string | null
    confidence?: number
  } | null
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

export interface DataEntityField {
  name: string
  type?: string
  required?: boolean
  description?: string
  group?: string
}

export interface DataEntityBRDSummary {
  id: string
  name: string
  description?: string | null
  entity_category: 'domain' | 'reference' | 'transactional' | 'system'
  fields: DataEntityField[]
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

export interface DataEntityRelationshipSuggestion {
  target_entity: string
  relationship_type: string
  rationale: string
}

export interface DataEntityEnrichment {
  sensitivity_level?: string | null
  pii_fields?: string[]
  ai_opportunities?: string[]
  system_design_notes?: string | null
  relationship_suggestions?: DataEntityRelationshipSuggestion[]
  validation_suggestions?: string[]
}

export interface DataEntityDetail {
  id: string
  name: string
  description?: string | null
  entity_category: string
  fields: DataEntityField[]
  field_count: number
  confirmation_status?: string | null
  evidence?: BRDEvidence[]
  is_stale?: boolean
  stale_reason?: string | null
  workflow_links: DataEntityWorkflowLink[]
  enrichment_data?: DataEntityEnrichment | null
  enrichment_status?: string | null
  pii_flags?: string[]
  relationships?: Record<string, unknown>[]
  revisions: RevisionEntry[]
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

  // Extended fields (from enrichment)
  linkedin_profile?: string | null
  communication_preferences?: Record<string, string> | null
  last_interaction_date?: string | null
  preferred_channel?: string | null
  approval_required_for?: string[] | null
  veto_power_over?: string[] | null
  reports_to_id?: string | null
  allies?: string[] | null
  potential_blockers?: string[] | null
  linked_persona_id?: string | null
  source_signal_ids?: string[] | null
  version?: number | null
  enrichment_status?: string | null
  extracted_from_signal_id?: string | null
  mentioned_in_signals?: string[] | null

  // Resolved references (from ?detail=true)
  reports_to?: ResolvedStakeholderRef | null
  allies_resolved?: ResolvedStakeholderRef[]
  potential_blockers_resolved?: ResolvedStakeholderRef[]
  linked_persona?: ResolvedPersonaRef | null
  linked_features?: LinkedFeatureRef[]
  linked_drivers?: LinkedDriverRef[]
}

// ============================================
// Stakeholder Detail Reference Types
// ============================================

export interface ResolvedStakeholderRef {
  id: string
  name: string
  role?: string | null
  stakeholder_type?: string | null
}

export interface ResolvedPersonaRef {
  id: string
  name: string
  role?: string | null
}

export interface LinkedFeatureRef {
  id: string
  name: string
  priority_group?: string | null
  confirmation_status?: string | null
}

export interface LinkedDriverRef {
  id: string
  description: string
  driver_type: string
  severity?: string | null
}

export interface SignalReference {
  id: string
  title?: string | null
  signal_type?: string | null
  source_label?: string | null
  created_at?: string | null
}

export interface FieldAttribution {
  field_path: string
  signal_id?: string | null
  signal_source?: string | null
  signal_label?: string | null
  contributed_at?: string | null
  version_number?: number | null
}

export interface EnrichmentRevisionSummary {
  revision_number?: number | null
  revision_type: string
  diff_summary?: string | null
  changes?: Record<string, unknown> | null
  created_at: string
  created_by?: string | null
  source_signal_id?: string | null
}

export interface StakeholderEvidenceData {
  source_signals: SignalReference[]
  field_attributions: FieldAttribution[]
  enrichment_history: EnrichmentRevisionSummary[]
  evidence_items: Array<Record<string, unknown>>
  topic_mentions: Record<string, number>
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

// ============================================
// BRD Completeness Types
// ============================================

export interface SectionScore {
  section: string
  score: number
  max_score: number
  label: 'Poor' | 'Fair' | 'Good' | 'Excellent'
  gaps: string[]
}

export interface BRDCompleteness {
  overall_score: number
  overall_label: 'Poor' | 'Fair' | 'Good' | 'Excellent'
  sections: SectionScore[]
  top_gaps: string[]
}

export interface BRDWorkspaceData {
  business_context: {
    background?: string | null
    company_name?: string | null
    industry?: string | null
    pain_points: BusinessDriver[]
    goals: BusinessDriver[]
    vision?: string | null
    vision_updated_at?: string | null
    vision_analysis?: Record<string, unknown> | null
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
  competitors: CompetitorBRDSummary[]
  readiness_score: number
  pending_count: number
  workflow_pairs: WorkflowPair[]
  roi_summary: ROISummary[]
  completeness?: BRDCompleteness | null
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
  // Monetary impact (KPI)
  monetary_value_low?: number | null
  monetary_value_high?: number | null
  monetary_type?: 'cost_reduction' | 'revenue_increase' | 'revenue_new' | 'risk_avoidance' | 'productivity_gain' | null
  monetary_timeframe?: 'annual' | 'monthly' | 'quarterly' | 'per_transaction' | 'one_time' | null
  monetary_confidence?: number | null
  monetary_source?: string | null
  // Associations
  associated_personas: AssociatedPersona[]
  associated_features: AssociatedFeature[]
  related_drivers: RelatedDriver[]
  // Relatability intelligence
  relatability_score?: number
  linked_feature_count?: number
  linked_persona_count?: number
  linked_workflow_count?: number
  vision_alignment?: VisionAlignment | null
  is_stale?: boolean
  stale_reason?: string | null
  // History
  revision_count: number
  revisions: RevisionEntry[]
}

// ============================================
// Vision Detail Types
// ============================================

export interface VisionAnalysis {
  conciseness: number
  measurability: number
  completeness: number
  alignment: number
  overall_score: number
  suggestions: string[]
  summary: string
}

export interface VisionDetailData {
  vision: string | null
  vision_analysis: VisionAnalysis | null
  vision_updated_at: string | null
  total_features: number
  revisions: RevisionEntry[]
}

// ============================================
// Client Intelligence Types
// ============================================

export interface ClientIntelligenceData {
  company_profile: {
    name?: string | null
    description?: string | null
    industry?: string | null
    website?: string | null
    stage?: string | null
    size?: string | null
    revenue?: string | null
    employee_count?: string | null
    location?: string | null
    unique_selling_point?: string | null
    company_type?: string | null
    industry_display?: string | null
    enrichment_source?: string | null
    enriched_at?: string | null
  }
  client_data: {
    name?: string | null
    company_summary?: string | null
    market_position?: string | null
    technology_maturity?: string | null
    digital_readiness?: string | null
    tech_stack?: string[] | null
    growth_signals?: string[] | null
    competitors?: string[] | null
    innovation_score?: number | null
    constraint_summary?: Record<string, unknown>[] | null
    role_gaps?: Record<string, unknown>[] | null
    vision_synthesis?: string | null
    organizational_context?: Record<string, unknown> | null
    profile_completeness?: number | null
    last_analyzed_at?: string | null
    enrichment_status?: string | null
    enriched_at?: string | null
  }
  strategic_context: {
    executive_summary?: string | null
    opportunity?: Record<string, unknown> | null
    risks?: Record<string, unknown>[] | null
    investment_case?: Record<string, unknown> | null
    success_metrics?: Record<string, unknown>[] | null
    constraints?: Record<string, unknown> | null
    confirmation_status?: string | null
    enrichment_status?: string | null
  }
  open_questions: Record<string, unknown>[]
  has_client: boolean
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

// ============================================
// Data Entity ERD Types
// ============================================

export interface ERDNode {
  id: string
  name: string
  entity_category: 'domain' | 'reference' | 'transactional' | 'system'
  field_count: number
  fields: { name: string; type?: string; required?: boolean; group?: string }[]
  workflow_step_count: number
}

export interface ERDEdge {
  id: string
  source: string
  target: string
  edge_type: string
  label?: string | null
}

export interface DataEntityGraphData {
  nodes: ERDNode[]
  edges: ERDEdge[]
}

export interface ImpactAnalysis {
  entity: { type: string; id: string }
  direct_impacts: { type: string; id: string; dependency_type: string; strength: number }[]
  indirect_impacts: { type: string; id: string; dependency_type: string; strength: number; path: string[] }[]
  total_affected: number
  recommendation: 'auto' | 'review_suggested' | 'high_impact_warning'
}

// ============================================
// Entity Confidence Types
// ============================================

export type ConfidenceCategory = 'identity' | 'detail' | 'relationships' | 'provenance' | 'confirmation'

export interface ConfidenceGap {
  label: string
  category: ConfidenceCategory
  is_met: boolean
  suggestion?: string | null
}

export interface EvidenceWithSource extends BRDEvidence {
  signal_id?: string | null
  signal_label?: string | null
  signal_type?: string | null
  signal_created_at?: string | null
}

export interface FieldAttributionItem {
  field_path: string
  signal_id?: string | null
  signal_label?: string | null
  contributed_at?: string | null
  version_number?: number | null
}

export interface ConfidenceRevision {
  revision_type: string
  diff_summary?: string | null
  changes?: Record<string, unknown> | null
  created_at: string
  created_by?: string | null
  source_signal_id?: string | null
}

export interface DependencyItem {
  entity_type: string
  entity_id: string
  dependency_type?: string | null
  strength?: number | null
  direction: 'depends_on' | 'depended_by'
}

export interface EntityConfidenceData {
  entity_type: string
  entity_id: string
  entity_name: string
  confirmation_status?: string | null
  is_stale: boolean
  stale_reason?: string | null
  created_at?: string | null
  updated_at?: string | null

  completeness_items: ConfidenceGap[]
  completeness_met: number
  completeness_total: number

  evidence: EvidenceWithSource[]
  field_attributions: FieldAttributionItem[]
  gaps: ConfidenceGap[]
  revisions: ConfidenceRevision[]
  dependencies: DependencyItem[]
}

// ============================================
// Canvas View Synthesis Types
// ============================================

export interface ValuePathUnlock {
  description: string
  unlock_type: UnlockType
  enabled_by: string
  strategic_value: string
  suggested_feature: string
}

export interface ValuePathStep {
  step_index: number
  title: string
  description: string
  actor_persona_id?: string | null
  actor_persona_name?: string | null
  pain_addressed?: string | null
  goal_served?: string | null
  linked_feature_ids: string[]
  linked_feature_names: string[]
  source_workflow_step_id?: string | null
  automation_level: AutomationLevel
  time_minutes?: number | null
  roi_impact: 'high' | 'medium' | 'low'
  unlocks: ValuePathUnlock[]
}

export interface CanvasViewData {
  actors: (PersonaBRDSummary & { canvas_role: 'primary' | 'secondary' })[]
  value_path: ValuePathStep[]
  synthesis_rationale?: string | null
  synthesis_stale: boolean
  mvp_features: FeatureBRDSummary[]
  workflow_pairs: WorkflowPair[]
}

// ============================================
// Project Context — living product specification
// ============================================

export interface ProjectContext {
  product_vision: string
  target_users: string
  core_value_proposition: string
  key_workflows: string
  data_landscape: string
  technical_boundaries: string
  design_principles: string
  assumptions: string[]
  open_questions: string[]
  source_count: number
  version: number
  generated_at?: string | null
  is_stale: boolean
}

// ============================================
// Value Path Step Detail — powers the 4-tab drawer
// ============================================

export interface StepActor {
  persona_id: string
  persona_name: string
  role?: string | null
  pain_at_step?: string | null
  goal_at_step?: string | null
  is_primary: boolean
}

export interface StepDataOperation {
  entity_id: string
  entity_name: string
  entity_category: string
  operation: string
  description?: string | null
}

export interface StepLinkedFeature {
  feature_id: string
  feature_name: string
  category?: string | null
  priority_group?: string | null
  confirmation_status?: string | null
}

export interface RecommendedComponent {
  name: string
  description: string
  priority: string
  rationale: string
}

export interface StepBusinessLogic {
  decision_points: string[]
  validation_rules: string[]
  edge_cases: string[]
  success_criteria: string
  error_states: string[]
}

export interface ValuePathStepDetail {
  step_index: number
  title: string
  description: string
  automation_level: string
  time_minutes?: number | null
  roi_impact: string
  pain_addressed?: string | null
  goal_served?: string | null
  // Tab 1: Actors
  actors: StepActor[]
  combined_value: string
  // Tab 2: System Flow
  data_operations: StepDataOperation[]
  input_dependencies: string[]
  output_effects: string[]
  // Tab 3: Business Logic
  business_logic: StepBusinessLogic
  // Tab 4: Components
  recommended_components: RecommendedComponent[]
  linked_features: StepLinkedFeature[]
  ai_suggestions: string[]
  effort_level: string
  // Tab 5: Unlocks
  unlocks: ValuePathUnlock[]
}

// ============================================
// Client Organization Types
// ============================================

export interface ClientSummary {
  id: string
  name: string
  website?: string | null
  industry?: string | null
  stage?: string | null
  size?: string | null
  description?: string | null
  logo_url?: string | null
  revenue_range?: string | null
  employee_count?: number | null
  founding_year?: number | null
  headquarters?: string | null
  tech_stack: string[]
  growth_signals: { signal: string; type: string }[]
  competitors: { name: string; relationship: string }[]
  innovation_score?: number | null
  company_summary?: string | null
  market_position?: string | null
  technology_maturity?: string | null
  digital_readiness?: string | null
  enrichment_status: string
  enriched_at?: string | null
  enrichment_source?: string | null
  organization_id?: string | null
  created_by?: string | null
  created_at?: string | null
  updated_at?: string | null
  project_count: number
  stakeholder_count: number
}

export interface ClientDetail extends ClientSummary {
  projects: {
    id: string
    name: string
    stage?: string | null
    status?: string | null
    created_at?: string | null
    updated_at?: string | null
  }[]
}

export interface ClientCreatePayload {
  name: string
  website?: string
  industry?: string
  stage?: string
  size?: string
  description?: string
  logo_url?: string
  organization_id?: string
}

// =============================================================================
// Discovery Pipeline Types
// =============================================================================

export interface DiscoveryPhaseStatus {
  phase: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  duration_seconds?: number
  summary?: string
}

export interface DiscoveryProgress {
  job_id: string
  status: string
  phases: DiscoveryPhaseStatus[]
  current_phase?: string
  cost_so_far_usd: number
  elapsed_seconds: number
  // Available when completed
  signal_id?: string
  entities_stored?: Record<string, number>
  total_cost_usd?: number
  drivers_count?: number
  competitors_count?: number
}

// =============================================================================
// Competitor Intelligence Types
// =============================================================================

export interface CompetitorBRDSummary {
  id: string
  name: string
  website?: string | null
  url?: string | null
  category?: string | null
  market_position?: string | null
  key_differentiator?: string | null
  pricing_model?: string | null
  target_audience?: string | null
  confirmation_status?: string | null
  deep_analysis_status?: string | null
  deep_analysis_at?: string | null
  is_design_reference: boolean
  is_stale?: boolean
  stale_reason?: string | null
  evidence?: BRDEvidence[]
}

export interface FeatureComparison {
  feature_name: string
  our_approach?: string | null
  their_approach?: string | null
  advantage: 'us' | 'them' | 'neutral'
}

export interface FeatureNote {
  feature_name: string
  description: string
  strategic_relevance: 'high' | 'medium' | 'low'
}

export interface CompetitorDeepAnalysis {
  feature_overlap: FeatureComparison[]
  unique_to_them: FeatureNote[]
  unique_to_us: FeatureNote[]
  inferred_pains: string[]
  inferred_benefits: string[]
  positioning_summary: string
  threat_level: 'low' | 'medium' | 'high' | 'critical'
  threat_reasoning: string
  differentiation_opportunities: string[]
  gaps_to_address: string[]
}

export interface FeatureHeatmapRow {
  feature_area: string
  competitors: Record<string, string>
  our_status: string
}

export interface CompetitorThreat {
  competitor_name: string
  threat_level: string
  key_risk: string
}

export interface CompetitorSynthesis {
  market_landscape: string
  feature_heatmap: FeatureHeatmapRow[]
  common_themes: string[]
  market_gaps: string[]
  positioning_recommendation: string
  threat_summary: CompetitorThreat[]
}

