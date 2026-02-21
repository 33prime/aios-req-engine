/**
 * TypeScript types for the workspace canvas UI
 */

import type { TerseAction } from '@/lib/api'

export interface PersonaSummary {
  id: string
  name: string
  role?: string | null
  description?: string | null
  persona_type?: string | null
  confirmation_status?: string | null
  confidence_score?: number | null
  created_at?: string | null
  version?: number | null
}

export interface FeatureSummary {
  id: string
  name: string
  description?: string | null
  is_mvp: boolean
  confirmation_status?: string | null
  vp_step_id?: string | null
  created_at?: string | null
  version?: number | null
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
  created_at?: string | null
  version?: number | null
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
  created_at?: string | null
  version?: number | null
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
  created_at?: string | null
  version?: number | null
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
  created_at?: string | null
  version?: number | null
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
  evidence: Array<Record<string, unknown>>
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
  created_at?: string | null
  version?: number | null
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

// ============================================
// Solution Flow Types
// ============================================

export interface InformationField {
  name: string
  type: 'captured' | 'displayed' | 'computed'
  mock_value: string
  confidence: 'known' | 'inferred' | 'guess' | 'unknown'
}

export interface FlowOpenQuestion {
  question: string
  context?: string
  status: 'open' | 'resolved' | 'escalated'
  resolved_answer?: string
  escalated_to?: string
}

export interface SolutionFlowStepSummary {
  id: string
  step_index: number
  phase: string
  title: string
  goal: string
  actors: string[]
  confirmation_status?: string | null
  has_pending_updates?: boolean
  open_question_count: number
  info_field_count: number
  confidence_breakdown: Record<string, number>
  confidence_impact?: number | null
}

export interface SolutionFlowStepDetail extends SolutionFlowStepSummary {
  information_fields: InformationField[]
  mock_data_narrative: string
  open_questions: FlowOpenQuestion[]
  implied_pattern: string
  linked_workflow_ids: string[]
  linked_feature_ids: string[]
  linked_data_entity_ids: string[]
  evidence_ids: string[]
  version: number
  success_criteria: string[] | null
  pain_points_addressed: Array<{ text: string; persona?: string } | string> | null
  goals_addressed: string[] | null
  ai_config: {
    role?: string
    ai_role?: string  // legacy field name from v3 generation
    behaviors?: string[]
    guardrails?: string[]
    confidence_display?: string
    fallback?: string
  } | null
  background_narrative?: string | null
  generation_version?: number
  preserved_from_version?: number | null
}

export interface SolutionFlowReadiness {
  ready: boolean
  met: Record<string, number>
  required: Record<string, number>
  missing: string[]
}

export interface ConfirmationClusterEntity {
  entity_id: string
  entity_type: string
  name: string
  confirmation_status: string
}

export interface ConfirmationCluster {
  cluster_id: string
  theme: string
  topics: string[]
  entities: ConfirmationClusterEntity[]
  entity_type_counts: Record<string, number>
  total: number
}

export interface SolutionFlowOverview {
  id: string | null
  title: string
  summary?: string | null
  generated_at?: string | null
  confirmation_status?: string | null
  steps: SolutionFlowStepSummary[]
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
  next_actions?: import('@/lib/api').NextAction[]
  solution_flow?: SolutionFlowOverview | null
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
    industry?: string | null
    stage?: string | null
    size?: string | null
    description?: string | null
    website?: string | null
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
  profile_completeness?: number | null
  constraint_summary?: Array<{ title: string; description: string; category: string; severity: string; source: string; impacts?: string[] }> | null
  role_gaps?: Array<{ role: string; why_needed: string; urgency: string; which_areas?: string[] }> | null
  vision_synthesis?: string | null
  organizational_context?: Record<string, unknown> | null
  last_analyzed_at?: string | null
}

export interface ClientDetailProject {
  id: string
  name: string
  description?: string | null
  stage?: string | null
  status?: string | null
  client_name?: string | null
  cached_readiness_score?: number | null
  cached_readiness_data?: {
    score: number
    dimensions?: Record<string, { score: number; weight: number; weighted_score: number }>
    confirmed_entities?: number
    total_entities?: number
  } | null
  counts?: { signals: number; features: number; personas: number; vp_steps: number; business_drivers: number } | null
  created_at?: string | null
  updated_at?: string | null
}

export interface ClientDetail extends ClientSummary {
  projects: ClientDetailProject[]
}

export interface ClientSignalSummary {
  id: string
  project_id: string
  project_name: string
  source: string
  signal_type: string
  raw_text?: string | null
  created_at: string
}

export interface ClientIntelligenceLog {
  id: string
  client_id: string
  trigger: string
  action_type?: string | null
  status?: string | null
  profile_completeness_before?: number | null
  profile_completeness_after?: number | null
  tools_called?: Array<{
    tool_name: string
    tool_args: Record<string, unknown>
    result?: Record<string, unknown> | null
    success: boolean
    error?: string | null
  }> | null
  observation?: string | null
  thinking?: string | null
  decision?: string | null
  action_summary?: string | null
  sections_affected?: string[] | null
  trigger_context?: string | null
  guidance?: Record<string, unknown> | null
  execution_time_ms?: number | null
  error_message?: string | null
  created_at: string
}

// =============================================================================
// Knowledge Base Types
// =============================================================================

export interface KnowledgeItem {
  id: string
  text: string
  category?: string | null
  source: 'signal' | 'stakeholder' | 'ai_inferred' | 'manual'
  source_detail?: string | null
  source_signal_id?: string | null
  stakeholder_name?: string | null
  confidence: 'high' | 'medium' | 'low'
  captured_at: string
  related_entity_ids?: string[] | null
}

export interface ClientKnowledgeBase {
  business_processes: KnowledgeItem[]
  sops: KnowledgeItem[]
  tribal_knowledge: KnowledgeItem[]
}

// =============================================================================
// Process Document Types
// =============================================================================

export interface ProcessDocumentStep {
  step_index: number
  label: string
  description?: string | null
  actor_persona_id?: string | null
  actor_persona_name?: string | null
  vp_step_id?: string | null
  time_minutes?: number | null
  decision_points?: string[]
  exceptions?: string[]
  evidence?: Array<{ signal_id?: string; excerpt?: string }>
}

export interface ProcessDocumentRole {
  persona_id?: string | null
  persona_name: string
  responsibilities?: string[]
  authority_level?: string | null
  evidence?: Array<{ signal_id?: string; excerpt?: string }>
}

export interface ProcessDocumentDataFlow {
  data_entity_id?: string | null
  data_entity_name: string
  operation: string
  step_indices?: number[]
  description?: string | null
  evidence?: Array<{ signal_id?: string; excerpt?: string }>
}

export interface ProcessDocumentDecisionPoint {
  label: string
  description?: string | null
  criteria?: string[]
  outcomes?: string[]
  owner_persona_id?: string | null
  step_index?: number | null
  evidence?: Array<{ signal_id?: string; excerpt?: string }>
}

export interface ProcessDocumentException {
  label: string
  description?: string | null
  handling_procedure?: string | null
  escalation_path?: string | null
  frequency?: string | null
  evidence?: Array<{ signal_id?: string; excerpt?: string }>
}

export interface ProcessDocumentTribalCallout {
  text: string
  stakeholder_name?: string | null
  context?: string | null
  importance?: 'critical' | 'important' | 'nice_to_know'
  evidence?: Array<{ signal_id?: string; excerpt?: string }>
}

export interface ProcessDocumentSummary {
  id: string
  title: string
  status: 'draft' | 'review' | 'confirmed' | 'archived'
  confirmation_status?: string | null
  generation_scenario?: 'reconstruct' | 'generate' | 'tribal_capture' | null
  step_count: number
  role_count: number
  source_kb_category?: string | null
  source_kb_item_id?: string | null
  project_id?: string | null
  created_at?: string | null
}

export interface ProcessDocument extends ProcessDocumentSummary {
  client_id?: string | null
  purpose?: string | null
  trigger_event?: string | null
  frequency?: string | null
  steps: ProcessDocumentStep[]
  roles: ProcessDocumentRole[]
  data_flow: ProcessDocumentDataFlow[]
  decision_points: ProcessDocumentDecisionPoint[]
  exceptions: ProcessDocumentException[]
  tribal_knowledge_callouts: ProcessDocumentTribalCallout[]
  evidence: Array<{ signal_id?: string; excerpt?: string; section?: string }>
  generation_model?: string | null
  generation_duration_ms?: number | null
  updated_at?: string | null
}

// ============================================
// Stakeholder Intelligence Types
// ============================================

export interface StakeholderIntelligenceSectionScore {
  section: string
  score: number
  max_score: number
}

export interface StakeholderIntelligenceProfile {
  stakeholder_id: string
  name: string
  role: string | null
  profile_completeness: number
  completeness_label: string
  intelligence_version: number
  last_intelligence_at: string | null
  sections: StakeholderIntelligenceSectionScore[]
  enrichment_fields: Record<string, unknown>
}

export interface StakeholderIntelligenceLog {
  id: string
  trigger: string
  action_type: string
  action_summary: string | null
  profile_completeness_before: number | null
  profile_completeness_after: number | null
  fields_affected: string[]
  stop_reason: string | null
  execution_time_ms: number | null
  success: boolean
  created_at: string
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

// ============================================================================
// Open Questions
// ============================================================================

export type QuestionPriority = 'critical' | 'high' | 'medium' | 'low'
export type QuestionStatus = 'open' | 'answered' | 'dismissed' | 'converted'
export type QuestionCategory = 'requirements' | 'stakeholder' | 'technical' | 'process' | 'scope' | 'validation' | 'general'

export interface OpenQuestion {
  id: string
  project_id: string
  question: string
  why_it_matters?: string | null
  context?: string | null
  priority: QuestionPriority
  category?: QuestionCategory | null
  status: QuestionStatus
  answer?: string | null
  answered_by?: string | null
  answered_at?: string | null
  converted_to_type?: string | null
  converted_to_id?: string | null
  source_type: string
  source_id?: string | null
  source_signal_id?: string | null
  target_entity_type?: string | null
  target_entity_id?: string | null
  suggested_owner?: string | null
  created_at: string
  updated_at: string
}

export interface QuestionCounts {
  total: number
  open: number
  answered: number
  dismissed: number
  converted: number
  critical_open: number
  high_open: number
}

// Project Launch Types
export interface LaunchStepStatus {
  step_key: string
  step_label: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  started_at?: string
  completed_at?: string
  result_summary?: string
  error_message?: string
}

export interface ProjectLaunchResponse {
  launch_id: string
  project_id: string
  client_id?: string
  stakeholder_ids: string[]
  status: string
  steps: LaunchStepStatus[]
}

export interface LaunchProgressResponse {
  launch_id: string
  project_id: string
  status: string
  steps: LaunchStepStatus[]
  progress_pct: number
  can_navigate: boolean
}

export interface StakeholderLaunchInput {
  first_name: string
  last_name: string
  email?: string
  linkedin_url?: string
  role?: string
  stakeholder_type?: string
}

// ============================================================================
// Intelligence Briefing
// ============================================================================

export type ChangeType =
  | 'belief_strengthened'
  | 'belief_weakened'
  | 'belief_created'
  | 'entity_created'
  | 'entity_updated'
  | 'signal_processed'
  | 'fact_added'
  | 'insight_added'

export type HypothesisStatus = 'proposed' | 'testing' | 'graduated' | 'rejected'

export interface TemporalChange {
  change_type: ChangeType
  summary: string
  entity_type?: string | null
  entity_id?: string | null
  entity_name?: string | null
  confidence_delta?: number | null
  timestamp?: string | null
}

export interface TemporalDiff {
  since_timestamp?: string | null
  since_label: string
  changes: TemporalChange[]
  change_summary: string
  counts: Record<string, number>
}

export interface Tension {
  tension_id: string
  summary: string
  side_a: string
  side_b: string
  involved_entities: Array<{ type: string; id: string; name: string }>
  confidence: number
}

export interface Hypothesis {
  hypothesis_id: string
  statement: string
  status: HypothesisStatus
  confidence: number
  evidence_for: number
  evidence_against: number
  test_suggestion?: string | null
  domain?: string | null
}

export interface ProjectHeartbeat {
  completeness_pct: number
  confirmation_pct: number
  days_since_last_signal?: number | null
  memory_depth: number
  stale_entity_count: number
  scope_alerts: string[]
  entity_counts: Record<string, number>
}

export interface BriefingSituation {
  narrative: string
  project_name: string
  phase: string
  phase_progress: number
  key_stakeholders: string[]
  entity_summary: Record<string, number>
}

export interface WhatYouShouldKnow {
  narrative: string
  bullets: string[]
}

export interface EvidenceAnchor {
  excerpt: string
  signal_label: string
  signal_type: string
  entity_name?: string | null
}

export type StarterActionType = 'deep_dive' | 'meeting_prep' | 'map_workflow' | 'batch_review' | 'quick_answers'

export interface ConversationStarter {
  starter_id: string
  hook: string
  question: string
  action_type: StarterActionType
  anchors: EvidenceAnchor[]
  chat_context: string
  topic_domain: string
  is_fallback: boolean
  generated_at?: string | null
}

export interface IntelligenceBriefing {
  situation: BriefingSituation
  what_changed: TemporalDiff
  what_you_should_know: WhatYouShouldKnow
  tensions: Tension[]
  hypotheses: Hypothesis[]
  heartbeat: ProjectHeartbeat
  actions: TerseAction[]
  conversation_starters?: ConversationStarter[]
  computed_at: string
  narrative_cached: boolean
  phase: string
}

// =============================================================================
// Intelligence Module Types
// =============================================================================

export interface IntelPulseStats {
  total_nodes: number
  total_edges: number
  avg_confidence: number
  hypotheses_count: number
  tensions_count: number
  confirmed_count: number
  disputed_count: number
  days_since_signal: number | null
}

export interface IntelRecentActivity {
  event_type: string
  summary: string
  confidence_delta: number | null
  timestamp: string
}

export interface IntelOverviewResponse {
  narrative: string
  what_you_should_know: Record<string, unknown>
  tensions: Tension[]
  hypotheses: Hypothesis[]
  what_changed: Record<string, unknown>
  pulse: IntelPulseStats
  recent_activity: IntelRecentActivity[]
}

export interface IntelGraphNode {
  id: string
  node_type: string
  summary: string
  content: string
  confidence: number
  belief_domain: string | null
  insight_type: string | null
  source_type: string | null
  linked_entity_type: string | null
  linked_entity_id: string | null
  is_active: boolean
  consultant_status: string | null
  consultant_note: string | null
  consultant_status_at: string | null
  hypothesis_status: string | null
  created_at: string
  support_count: number
  contradict_count: number
}

export interface IntelGraphEdge {
  id: string
  from_node_id: string
  to_node_id: string
  edge_type: string
  strength: number
  rationale: string | null
}

export interface IntelGraphResponse {
  nodes: IntelGraphNode[]
  edges: IntelGraphEdge[]
  stats: Record<string, number>
}

export interface IntelBeliefHistoryItem {
  id: string
  previous_confidence: number
  new_confidence: number
  change_type: string
  change_reason: string
  triggered_by_node_id: string | null
  created_at: string
}

export interface IntelNodeDetail {
  node: IntelGraphNode
  edges_from: IntelGraphEdge[]
  edges_to: IntelGraphEdge[]
  supporting_facts: IntelGraphNode[]
  contradicting_facts: IntelGraphNode[]
  history: IntelBeliefHistoryItem[]
}

export interface IntelEvolutionEvent {
  event_type: string
  summary: string
  entity_type: string | null
  entity_id: string | null
  entity_name: string | null
  confidence_before: number | null
  confidence_after: number | null
  confidence_delta: number | null
  change_reason: string | null
  timestamp: string
}

export interface IntelEvolutionResponse {
  events: IntelEvolutionEvent[]
  total_count: number
}

export interface IntelConfidenceCurvePoint {
  confidence: number
  timestamp: string
  change_reason: string | null
}

export interface IntelConfidenceCurve {
  node_id: string
  summary: string
  points: IntelConfidenceCurvePoint[]
}

export interface IntelLinkedMemory {
  id: string
  node_type: string
  summary: string
  confidence: number
  consultant_status: string | null
}

export interface IntelEntityRevision {
  id: string
  field_name: string | null
  old_value: unknown
  new_value: unknown
  source_signal_id: string | null
  created_at: string
}

export interface IntelSourceSignal {
  id: string
  signal_type: string | null
  title: string | null
  created_at: string
}

export interface IntelEvidenceResponse {
  entity_type: string
  entity_id: string
  entity_name: string
  linked_memory: IntelLinkedMemory[]
  revisions: IntelEntityRevision[]
  source_signals: IntelSourceSignal[]
}

export interface IntelDealReadinessComponent {
  name: string
  score: number
  weight: number
  details: string
}

export interface IntelStakeholderMapEntry {
  id: string
  name: string
  stakeholder_type: string | null
  influence_level: string | null
  role: string | null
  is_addressed: boolean
}

export interface IntelGapOrRisk {
  severity: string
  message: string
}

export interface IntelSalesResponse {
  has_client: boolean
  deal_readiness_score: number
  components: IntelDealReadinessComponent[]
  client_name: string | null
  client_industry: string | null
  client_size: string | null
  profile_completeness: number | null
  vision: string | null
  constraints_summary: string | null
  stakeholder_map: IntelStakeholderMapEntry[]
  gaps_and_risks: IntelGapOrRisk[]
}

// ============================================
// Unlocks Module
// ============================================

export type ImpactType = 'operational_scale' | 'talent_leverage' | 'risk_elimination' |
    'revenue_expansion' | 'data_intelligence' | 'compliance' | 'speed_to_change'
export type UnlockTier = 'implement_now' | 'after_feedback' | 'if_this_works'
export type UnlockKind = 'new_capability' | 'feature_upgrade'
export type UnlockStatus = 'generated' | 'curated' | 'promoted' | 'dismissed'

export interface ProvenanceLink {
    entity_type: string
    entity_id: string
    entity_name: string
    relationship: 'enables' | 'solves' | 'serves' | 'validated_by'
}

export interface UnlockSummary {
    id: string
    title: string
    narrative: string
    feature_sketch: string | null
    impact_type: ImpactType
    unlock_kind: UnlockKind
    tier: UnlockTier
    status: UnlockStatus
    magnitude: string | null
    why_now: string | null
    non_obvious: string | null
    provenance: ProvenanceLink[]
    promoted_feature_id: string | null
    confirmation_status: string
    created_at: string
}

