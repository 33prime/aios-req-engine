// Types for the prototype refinement subsystem

// === Design profile & selection types ===

export interface DesignTokens {
  primary_color: string
  secondary_color: string
  accent_color: string
  font_heading: string
  font_body: string
  spacing: string
  corners: string
  style_direction: string
  logo_url?: string
}

export interface GenericStyle {
  id: string
  label: string
  description: string
  preview_colors: string[]
  tokens: DesignTokens
}

export interface BrandData {
  logo_url: string | null
  brand_colors: string[]
  typography: { heading_font: string; body_font: string } | null
  design_characteristics: {
    overall_feel: string
    spacing: string
    corners: string
    visual_weight: string
  } | null
}

export interface DesignInspiration {
  id: string
  name: string
  url: string | null
  description: string
  source: string
}

export interface DesignProfile {
  brand_available: boolean
  brand: BrandData | null
  design_inspirations: DesignInspiration[]
  suggested_style: string | null
  style_source: string | null
  generic_styles: GenericStyle[]
}

export interface DesignSelection {
  option_id: string
  tokens: DesignTokens
  source: string
}


export interface Prototype {
  id: string
  project_id: string
  repo_url: string | null
  deploy_url: string | null
  status: 'pending' | 'generating' | 'ingested' | 'analyzed' | 'active' | 'archived'
  prompt_audit: PromptAuditResult | null
  prompt_version: number
  session_count: number
  created_at: string
  updated_at: string
}

export interface PromptAuditResult {
  feature_coverage_score: number
  structure_score: number
  mock_data_score: number
  flow_score: number
  feature_id_score: number
  overall_score: number
  gaps: PromptGap[]
  recommendations: string[]
}

export interface PromptGap {
  dimension: string
  description: string
  severity: 'high' | 'medium' | 'low'
  feature_ids: string[]
}

export interface FeatureOverlay {
  id: string
  prototype_id: string
  feature_id: string | null
  code_file_path: string | null
  component_name: string | null
  handoff_feature_name: string | null
  status: 'understood' | 'partial' | 'unknown'
  confidence: number
  gaps_count: number
  overlay_content: OverlayContent | null
  created_at: string
}

export interface OverlayContent {
  feature_id: string | null
  feature_name: string
  status: 'understood' | 'partial' | 'unknown'
  confidence: number
  gaps_count: number
  triggers: string[]
  actions: string[]
  data_requirements: string[]
  personas: PersonaRef[]
  flow_position: { vp_step_index: number; vp_step_label: string } | null
  dependencies: Dependency[]
  questions: OverlayQuestion[]
  business_rules: BusinessRule[]
  implementation_notes: string
  upload_suggestions: UploadSuggestion[]
}

export interface PersonaRef {
  persona_id: string
  persona_name: string
  role: string
}

export interface Dependency {
  feature_id: string
  feature_name: string
  direction: 'upstream' | 'downstream'
  relationship: string
}

export interface OverlayQuestion {
  id: string
  question: string
  category: string
  priority: 'high' | 'medium' | 'low'
  answer: string | null
  answered_in_session: number | null
}

export interface BusinessRule {
  rule: string
  source: 'aios' | 'inferred' | 'confirmed'
  confidence: number
}

export interface UploadSuggestion {
  title: string
  description: string
  priority: 'high' | 'medium' | 'low'
}

export interface PageVisit {
  path: string
  timestamp: string
  features_visible: string[]
}

export interface SessionContext {
  current_page: string
  current_route: string
  active_feature_id: string | null
  active_feature_name: string | null
  active_component: string | null
  visible_features: string[]
  page_history: PageVisit[]
  features_reviewed: string[]
}

export interface PrototypeSession {
  id: string
  prototype_id: string
  session_number: number
  status: string
  readiness_before: number | null
  readiness_after: number | null
  synthesis: Record<string, unknown> | null
  code_update_plan: Record<string, unknown> | null
  code_update_result: Record<string, unknown> | null
  started_at: string | null
  completed_at: string | null
  created_at: string
}

export interface PrototypeFeedback {
  id: string
  session_id: string
  source: 'consultant' | 'client'
  feature_id: string | null
  page_path: string | null
  component_name: string | null
  feedback_type: string | null
  content: string
  context: SessionContext | null
  priority: string
  created_at: string
}

export interface SubmitFeedbackRequest {
  content: string
  feedback_type: 'observation' | 'requirement' | 'concern' | 'question' | 'answer'
  context?: SessionContext
  feature_id?: string
  page_path?: string
  component_name?: string
  answers_question_id?: string
  priority?: 'high' | 'medium' | 'low'
}

// PostMessage event types from the bridge script
export interface AiosFeatureClickEvent {
  type: 'aios:feature-click'
  featureId: string
  componentName: string | null
  elementTag: string
  textContent: string
}

export interface AiosPageChangeEvent {
  type: 'aios:page-change'
  path: string
  visibleFeatures: string[]
}

export interface AiosHighlightReadyEvent {
  type: 'aios:highlight-ready'
  featureId: string
  rect: { top: number; left: number; width: number; height: number }
}

export interface AiosHighlightNotFoundEvent {
  type: 'aios:highlight-not-found'
  featureId: string
}

export interface AiosTourStepCompleteEvent {
  type: 'aios:tour-step-complete'
  featureId: string
}

export type AiosBridgeEvent =
  | AiosFeatureClickEvent
  | AiosPageChangeEvent
  | AiosHighlightReadyEvent
  | AiosHighlightNotFoundEvent
  | AiosTourStepCompleteEvent

// Bridge commands (parent → iframe)
export interface RadarFeature {
  featureId: string
  featureName: string
  componentName?: string
  keywords?: string[]
}

export type AiosBridgeCommand =
  | { type: 'aios:highlight-feature'; featureId: string; featureName: string; description: string; stepLabel: string; componentName?: string; keywords?: string[] }
  | { type: 'aios:clear-highlights' }
  | { type: 'aios:navigate'; path: string }
  | { type: 'aios:show-radar'; features: RadarFeature[] }
  | { type: 'aios:clear-radar' }
  | { type: 'aios:start-tour'; steps: Array<{ featureId: string; featureName: string; description: string; stepLabel: string; route: string | null }> }
  | { type: 'aios:next-step' }
  | { type: 'aios:prev-step' }

// Tour types
export interface TourStep {
  featureId: string
  featureName: string
  description: string
  route: string | null
  vpStepIndex: number | null
  vpStepLabel: string | null
  overlayId: string
  featureRole: 'core' | 'supporting' | 'unmapped'
  questions: OverlayQuestion[]
}

export interface TourStepGroup {
  vpStepIndex: number
  vpStepLabel: string
  steps: TourStep[]
}

export type TourPhase = 'primary_flow' | 'secondary_flow' | 'deep_dive'

export interface TourPlan {
  phases: Record<TourPhase, TourStepGroup[]>
  flatSteps: TourStep[]
  totalSteps: number
  totalQuestions: number
}

export type RouteFeatureMap = Map<string, string[]>

// Review mode state (shared between BuildPhaseView and CollaborationPanel)
export interface ReviewMode {
  session: PrototypeSession
  overlays: FeatureOverlay[]
  prototypeId: string
  isTourActive: boolean
  currentTourStep: TourStep | null
  sessionContext: SessionContext
  answeredQuestionIds: Set<string>
  routeFeatureMap: RouteFeatureMap
  isFrameReady: boolean
}
