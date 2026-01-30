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

export interface Feature {
  id: string
  name: string
  category: string
  is_mvp: boolean
  status: string
  confidence: string
  details?: any
  evidence: any[]
  confirmation_status?: 'ai_generated' | 'confirmed_consultant' | 'confirmed_client' | 'needs_client'
  created_at: string
  updated_at: string

  // V2 enrichment fields
  overview?: string | null
  target_personas?: Array<{
    persona_id?: string | null
    persona_name: string
    role: 'primary' | 'secondary'
    context: string
  }>
  user_actions?: string[]
  system_behaviors?: string[]
  ui_requirements?: string[]
  rules?: string[]
  integrations?: string[]
  enrichment_status?: 'none' | 'enriched' | 'stale' | null
  enriched_at?: string | null
}

// PrdSection removed - PRD is now generated from features, personas, VP steps

export interface Persona {
  id: string
  project_id: string
  slug: string
  name: string
  role: string | null
  demographics: Record<string, any>
  psychographics: Record<string, any>
  goals: string[]
  pain_points: string[]
  description: string | null
  related_features: string[]
  related_vp_steps: string[]
  confirmation_status: 'ai_generated' | 'confirmed_consultant' | 'confirmed_client' | 'needs_client'
  confirmed_by: string | null
  confirmed_at: string | null
  created_at: string
  updated_at: string
  overview: string | null
  key_workflows: Array<{ name: string; description: string; steps: string[]; features_used: string[] }>
  enrichment_status: 'none' | 'enriched' | 'stale' | null
  enriched_at: string | null
  coverage_score?: number
  health_score?: number
}

// V2 evidence item for VP steps
export interface VpEvidence {
  chunk_id?: string | null
  excerpt: string
  source_type: 'signal' | 'research' | 'inferred'
  rationale: string
}

// V2 feature reference in VP step
export interface VpFeatureRef {
  feature_id: string
  feature_name: string
  role: 'core' | 'supporting'
}

export interface VpStep {
  id: string
  step_index: number
  label: string
  status: string
  description: string
  enrichment?: any
  evidence?: VpEvidence[]
  user_benefit_pain?: string
  ui_overview?: string
  value_created?: string
  kpi_impact?: string
  created_at: string
  updated_at: string

  // V2 fields
  actor_persona_id?: string | null
  actor_persona_name?: string | null
  narrative_user?: string | null
  narrative_system?: string | null
  features_used?: VpFeatureRef[]
  rules_applied?: string[]
  integrations_triggered?: string[]
  ui_highlights?: string[]
  confirmation_status?: 'ai_generated' | 'confirmed_consultant' | 'confirmed_client' | 'needs_client'
  has_signal_evidence?: boolean
  generation_status?: 'none' | 'generated' | 'stale'
  generated_at?: string | null
  is_stale?: boolean
  stale_reason?: string | null
  consultant_edited?: boolean
  consultant_edited_at?: string | null
}

export interface Confirmation {
  id: string
  kind: 'vp' | 'feature' | 'insight' | 'gate' | 'persona'
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
  onboarding_job_id?: string // ID of onboarding job (for polling progress)
}

export interface ProjectDetail extends Project {
  counts: {
    signals: number
    vp_steps: number
    features: number
    insights: number
    personas: number
  }
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
  unused_signals: Array<Signal & {
    chunk_count: number
    impact_count: number
    source_label?: string
    source_type?: string
    source_timestamp?: string
  }>
  unused_signals_count: number
}

// ============================================================================
// Organizations
// ============================================================================

export type OrganizationRole = 'Owner' | 'Admin' | 'Member'
export type InvitationStatus = 'pending' | 'accepted' | 'expired' | 'cancelled'
export type AvailabilityStatus = 'Available' | 'Busy' | 'Away'
export type PlatformRole = 'user' | 'admin' | 'super_admin'

export interface Organization {
  id: string
  name: string
  slug?: string
  created_by_user_id?: string
  logo_url?: string
  settings: Record<string, any>
  created_at: string
  updated_at: string
  archived_at?: string
  deleted_at?: string
  deleted_by_user_id?: string
}

export interface OrganizationWithRole extends Organization {
  current_user_role: OrganizationRole
}

export interface OrganizationSummary {
  id: string
  name: string
  slug?: string
  logo_url?: string
  member_count: number
  project_count: number
  created_at: string
}

export interface OrganizationCreate {
  name: string
  slug?: string
  logo_url?: string
  settings?: Record<string, any>
}

export interface OrganizationUpdate {
  name?: string
  slug?: string
  logo_url?: string
  settings?: Record<string, any>
}

export interface OrganizationMember {
  id: string
  organization_id: string
  user_id: string
  organization_role: OrganizationRole
  invited_by_user_id?: string
  joined_at: string
  created_at: string
}

export interface OrganizationMemberPublic {
  id: string
  user_id: string
  email: string
  first_name?: string
  last_name?: string
  photo_url?: string
  organization_role: OrganizationRole
  joined_at: string
}

export interface Invitation {
  id: string
  organization_id: string
  email: string
  organization_role: OrganizationRole
  invited_by_user_id: string
  invite_token: string
  status: InvitationStatus
  created_at: string
  expires_at: string
  accepted_at?: string
}

export interface InvitationWithOrg extends Invitation {
  organization_name: string
  organization_logo_url?: string
  invited_by_name?: string
}

export interface InvitationCreate {
  email: string
  organization_role?: OrganizationRole
}

export interface Profile {
  id: string
  user_id: string
  first_name?: string
  last_name?: string
  email: string
  photo_url?: string
  linkedin?: string
  meeting_link?: string
  phone_number?: string
  city?: string
  state?: string
  country?: string
  platform_role: PlatformRole
  expertise_areas: string[]
  certifications: string[]
  bio?: string
  availability_status: AvailabilityStatus
  capacity: number
  timezone?: string
  preferences: Record<string, any>
  created_at: string
  updated_at: string
}

export interface ProfileUpdate {
  first_name?: string
  last_name?: string
  photo_url?: string
  linkedin?: string
  meeting_link?: string
  phone_number?: string
  city?: string
  state?: string
  country?: string
  bio?: string
  timezone?: string
  expertise_areas?: string[]
  certifications?: string[]
  availability_status?: AvailabilityStatus
  capacity?: number
  preferences?: Record<string, any>
}

// ============================================================================
// Discovery Prep
// ============================================================================

export type PrepStatus = 'draft' | 'confirmed' | 'sent'
export type DocPriority = 'high' | 'medium' | 'low'

export interface PrepQuestion {
  id: string
  question: string
  best_answered_by: string
  why_important: string
  confirmed: boolean
  client_answer?: string
  answered_at?: string
}

export interface DocRecommendation {
  id: string
  document_name: string
  priority: DocPriority
  why_important: string
  confirmed: boolean
  uploaded_file_id?: string
  uploaded_at?: string
}

export interface DiscoveryPrepBundle {
  id: string
  project_id: string
  agenda_summary?: string
  agenda_bullets: string[]
  questions: PrepQuestion[]
  documents: DocRecommendation[]
  status: PrepStatus
  sent_to_portal_at?: string
  generated_at: string
  updated_at: string
}

// ============================================================================
// Meetings
// ============================================================================

export type MeetingType = 'discovery' | 'validation' | 'review' | 'other'
export type MeetingStatus = 'scheduled' | 'completed' | 'cancelled'

export interface Meeting {
  id: string
  project_id: string
  title: string
  description?: string
  meeting_type: MeetingType
  status: MeetingStatus
  meeting_date: string
  meeting_time: string
  duration_minutes: number
  timezone: string
  stakeholder_ids: string[]
  agenda?: Record<string, any>
  summary?: string
  highlights?: Record<string, any>
  google_calendar_event_id?: string
  google_meet_link?: string
  created_by?: string
  created_at: string
  updated_at: string
  // Joined fields
  project_name?: string
}

// ============================================================================
// Status Narrative
// ============================================================================

export interface StatusNarrative {
  where_today: string
  where_going: string
  updated_at?: string
}

// ============================================================================
// Extended Project (with new dashboard fields)
// ============================================================================

export type ProjectStage = 'discovery' | 'validation' | 'prototype' | 'prototype_refinement' | 'proposal' | 'build' | 'live'

export interface ProjectWithDashboard extends Project {
  created_by?: string
  stage: ProjectStage
  client_name?: string
  status_narrative?: StatusNarrative
  portal_enabled?: boolean
  portal_phase?: 'pre_call' | 'post_call' | 'building' | 'testing'
  readiness_score?: number
  stage_eligible?: boolean | null
}

// ============================================================================
// Stage Progression
// ============================================================================

export interface StageGateCriterion {
  gate_name: string
  gate_label: string
  satisfied: boolean
  confidence: number
  required: boolean
  missing: string[]
  how_to_acquire: string[]
}

export interface StageStatusResponse {
  current_stage: string
  next_stage: string | null
  can_advance: boolean
  criteria: StageGateCriterion[]
  criteria_met: number
  criteria_total: number
  progress_pct: number
  transition_description: string
  is_final_stage: boolean
}

export interface AdvanceStageRequest {
  target_stage: string
  force?: boolean
  reason?: string
}

export interface AdvanceStageResponse {
  previous_stage: string
  current_stage: string
  forced: boolean
  message: string
}

export interface ProjectDetailWithDashboard extends ProjectWithDashboard {
  counts: {
    signals: number
    vp_steps: number
    features: number
    insights: number
    personas: number
  }
  /** Full cached readiness data for instant display */
  cached_readiness_data?: {
    score: number
    ready: boolean
    threshold: number
    dimensions: Record<string, { score: number; weight: number; weighted_score: number }>
    caps_applied: Array<{ cap_id: string; limit: number; reason: string }>
    top_recommendations: Array<{ action: string; impact: string; effort: string; priority: number }>
    computed_at: string
    confirmed_entities: number
    total_entities: number
    client_signals_count: number
    meetings_completed: number
    // Gate-based readiness fields (DI Agent integration)
    phase?: string  // "insufficient" | "prototype_ready" | "build_ready"
    prototype_ready?: boolean
    build_ready?: boolean
    gates?: {
      prototype_gates: Record<string, any>
      build_gates: Record<string, any>
    }
    next_milestone?: string  // "prototype" | "build" | "complete"
    blocking_gates?: string[]
    gate_score?: number
  } | null
}

// ============================================================================
// Collaboration System (Linear Phase Workflow)
// ============================================================================

export type CollaborationPhase =
  | 'pre_discovery'
  | 'discovery'
  | 'validation'
  | 'prototype'
  | 'proposal'
  | 'build'
  | 'delivery'

export type PhaseStepStatus = 'locked' | 'available' | 'in_progress' | 'completed'

export type PendingItemType =
  | 'feature'
  | 'persona'
  | 'vp_step'
  | 'question'
  | 'document'
  | 'kpi'
  | 'goal'
  | 'pain_point'
  | 'requirement'
  | 'competitor'
  | 'design_preference'
  | 'stakeholder'

export type PendingItemSource =
  | 'phase_workflow'
  | 'needs_review'
  | 'ai_generated'
  | 'manual'

// Phase Progress

export interface PhaseStep {
  id: string
  label: string
  status: PhaseStepStatus
  progress?: { current: number; total: number }
  unlock_message?: string
}

export interface PhaseGate {
  id: string
  label: string
  condition: string
  met: boolean
  current_value?: string | number
  required_for_completion: boolean
}

export interface PhaseProgressConfig {
  phase: CollaborationPhase
  steps: PhaseStep[]
  gates: PhaseGate[]
  readiness_score: number
}

// Pending Items Queue

export interface PendingItem {
  id: string
  item_type: PendingItemType
  source: PendingItemSource
  entity_id?: string
  title: string
  description?: string
  why_needed?: string
  priority: 'high' | 'medium' | 'low'
  created_at: string
  added_by?: string
}

export interface PendingItemsQueue {
  items: PendingItem[]
  by_type: Record<string, number>
  total_count: number
}

// Client Package (AI-Synthesized)

export interface SynthesizedQuestion {
  id: string
  question_text: string
  hint?: string
  suggested_answerer?: string
  why_asking?: string
  example_answer?: string
  covers_items: string[]
  covers_summary?: string
  sequence_order: number
}

export interface ActionItem {
  id: string
  title: string
  description?: string
  item_type: 'document' | 'task' | 'approval'
  hint?: string
  why_needed?: string
  covers_items: string[]
  sequence_order: number
}

export interface AssetSuggestion {
  id: string
  category: 'sample_data' | 'process' | 'data_systems' | 'integration'
  title: string
  description: string
  why_valuable: string
  examples: string[]
  priority: 'high' | 'medium' | 'low'
  phase_relevant: CollaborationPhase[]
}

export interface ClientPackage {
  id: string
  project_id: string
  status: 'draft' | 'sent' | 'responses_received'
  questions: SynthesizedQuestion[]
  action_items: ActionItem[]
  suggested_assets: AssetSuggestion[]
  source_items: string[]
  source_items_count: number
  questions_count: number
  action_items_count: number
  suggestions_count: number
  created_at: string
  sent_at?: string
  updated_at: string
}

// Main Response

export interface PhaseProgressResponse {
  project_id: string
  current_phase: CollaborationPhase
  phases: Array<{
    phase: CollaborationPhase
    status: 'locked' | 'active' | 'completed'
    completed_at?: string
  }>
  phase_config: PhaseProgressConfig
  readiness_score: number
  readiness_gates: PhaseGate[]
  pending_queue: PendingItemsQueue
  draft_package?: ClientPackage
  sent_package?: ClientPackage
  package_responses?: {
    package_id: string
    question_responses: Array<{
      question_id: string
      answer_text: string
      answered_by?: string
      answered_by_name?: string
      answered_at: string
    }>
    action_item_responses: Array<{
      action_item_id: string
      status: 'complete' | 'skipped' | 'partial'
      files: Array<{ id: string; name: string; url: string }>
      notes?: string
      completed_by?: string
      completed_at: string
    }>
    questions_answered: number
    questions_total: number
    action_items_completed: number
    action_items_total: number
    overall_progress: number
  }
  portal_enabled: boolean
  clients_count: number
  last_client_activity?: string
}
