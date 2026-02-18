/**
 * Shared action constants — single source of truth for action icons,
 * urgency colors, execution types, and CTA labels.
 *
 * Used by: NextActionsBar, IntelligencePanel, OverviewPanel, BRDCanvas,
 *          WorkspaceChat, ProjectsCards
 */

import {
  Target,
  Users,
  FileText,
  Lightbulb,
  MessageCircle,
  RefreshCw,
  GitBranch,
  Link2,
  Clock,
  Workflow,
  TrendingUp,
  BarChart3,
  AlertTriangle,
  HelpCircle,
  Layers,
  type LucideIcon,
} from 'lucide-react'

// =============================================================================
// v2 gap type icons (relationship-aware engine)
// =============================================================================

export const GAP_TYPE_ICONS: Record<string, LucideIcon> = {
  // Workflow domain
  step_no_actor: Users,
  step_no_pain: AlertTriangle,
  step_no_time: Clock,
  step_no_benefit: TrendingUp,
  workflow_no_future_state: Workflow,
  workflow_no_drivers: Link2,
  // Driver domain
  pain_no_workflow: Workflow,
  goal_no_feature: Target,
  kpi_no_numbers: BarChart3,
  driver_single_source: FileText,
  // Persona domain
  persona_no_workflow: Users,
  persona_pains_not_drivers: AlertTriangle,
  // Cross-ref domain
  open_question: HelpCircle,
  critical_questions: HelpCircle,
  // Batch/project-level
  no_workflows: Workflow,
  no_kpis: BarChart3,
  no_vision: Lightbulb,
  project_stale: Clock,
}

// Legacy action type icons (backward compat for dashboard/overview)
export const ACTION_ICONS: Record<string, LucideIcon> = {
  confirm_critical: Target,
  stakeholder_gap: Users,
  section_gap: FileText,
  missing_evidence: FileText,
  validate_pains: Target,
  missing_vision: Lightbulb,
  missing_metrics: Target,
  open_question_critical: MessageCircle,
  open_question_blocking: MessageCircle,
  stale_belief: RefreshCw,
  revisit_decision: RefreshCw,
  contradiction_unresolved: GitBranch,
  cross_entity_gap: Link2,
  temporal_stale: Clock,
  // v2 gap types also accessible via legacy map
  ...GAP_TYPE_ICONS,
}

export const URGENCY_COLORS: Record<string, string> = {
  critical: '#EF4444',
  high: '#F97316',
  normal: '#3FAF7A',
  low: '#999999',
}

// Domain colors for the intelligence panel
export const GAP_DOMAIN_COLORS: Record<string, string> = {
  workflow: '#3FAF7A',   // brand green — workflows are king
  driver: '#0A1E2F',     // navy
  persona: '#666666',    // secondary text
  cross_ref: '#999999',  // muted
}

export const GAP_DOMAIN_LABELS: Record<string, string> = {
  workflow: 'Workflow',
  driver: 'Business Driver',
  persona: 'Persona',
  cross_ref: 'Cross-Reference',
}

export type ActionExecutionType = 'drawer' | 'navigate' | 'inline' | 'chat' | 'answer'

// v2 execution map (gap_type → execution type)
export const GAP_EXECUTION_MAP: Record<string, ActionExecutionType> = {
  // Workflow gaps → inline answer in intelligence panel
  step_no_actor: 'answer',
  step_no_pain: 'answer',
  step_no_time: 'answer',
  step_no_benefit: 'answer',
  workflow_no_future_state: 'answer',
  workflow_no_drivers: 'answer',
  // Driver gaps → inline answer
  pain_no_workflow: 'answer',
  goal_no_feature: 'answer',
  kpi_no_numbers: 'answer',
  driver_single_source: 'answer',
  // Persona gaps → inline answer
  persona_no_workflow: 'answer',
  persona_pains_not_drivers: 'answer',
  // Cross-ref → navigate to questions section
  open_question: 'navigate',
  critical_questions: 'navigate',
  // Project-level
  no_workflows: 'navigate',
  no_kpis: 'navigate',
  no_vision: 'drawer',
  project_stale: 'navigate',
}

// Legacy execution map (backward compat)
export const ACTION_EXECUTION_MAP: Record<string, ActionExecutionType> = {
  confirm_critical: 'inline',
  stakeholder_gap: 'navigate',
  section_gap: 'navigate',
  missing_evidence: 'drawer',
  validate_pains: 'drawer',
  missing_vision: 'drawer',
  missing_metrics: 'navigate',
  open_question_critical: 'navigate',
  open_question_blocking: 'navigate',
  stale_belief: 'chat',
  temporal_stale: 'drawer',
  cross_entity_gap: 'navigate',
  contradiction_unresolved: 'chat',
  revisit_decision: 'chat',
  // v2 gap types
  ...GAP_EXECUTION_MAP,
}

export const ACTION_CTA_LABELS: Record<ActionExecutionType, string> = {
  inline: 'Confirm All',
  drawer: 'Open',
  navigate: 'Go to Section',
  chat: 'Ask AI',
  answer: 'Answer',
}

/** Get the CTA label for a given action/gap type */
export function getActionCTALabel(actionType: string): string {
  const execType = GAP_EXECUTION_MAP[actionType] || ACTION_EXECUTION_MAP[actionType]
  if (!execType) return 'View'
  return ACTION_CTA_LABELS[execType]
}

/** Get the icon for a gap type (v2) or action type (legacy) */
export function getActionIcon(gapType: string): LucideIcon {
  return GAP_TYPE_ICONS[gapType] || ACTION_ICONS[gapType] || Layers
}
