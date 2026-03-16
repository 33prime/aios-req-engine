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
  critical: '#0A1E2F',
  high: '#044159',
  normal: '#666666',
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

// =============================================================================
// v3 gap source constants
// =============================================================================

import { Upload, MessageSquare, type LucideIcon as LIcon } from 'lucide-react'

/** Icons by gap source type (v3 terse actions) */
export const GAP_SOURCE_ICONS: Record<string, LIcon> = {
  structural: HelpCircle,
  signal: Upload,
  knowledge: MessageSquare,
  // Also support specific gap_types
  signal_gap: Upload,
  knowledge_gap: MessageSquare,
  ...GAP_TYPE_ICONS,
}

/** Colors by gap source (v3) */
export const GAP_SOURCE_COLORS: Record<string, string> = {
  structural: '#3FAF7A',  // brand green — answerable inline
  signal: '#0A1E2F',      // navy — needs document
  knowledge: '#666666',   // secondary — needs discussion
}

/** Phase display labels */
export const PHASE_LABELS: Record<string, string> = {
  empty: 'Getting Started',
  seeding: 'Seeding',
  building: 'Building',
  refining: 'Refining',
}

/** Phase descriptions for empty states */
export const PHASE_DESCRIPTIONS: Record<string, string> = {
  empty: 'Tell us about the project to get started',
  seeding: 'Upload documents or describe the current process',
  building: 'Fill in the details to strengthen the BRD',
  refining: 'Almost there — confirm and polish',
}

// =============================================================================
// Conversation Starter action types
// =============================================================================

import type { StarterActionType } from '@/types/workspace'

/** Display labels for starter action types */
export const STARTER_ACTION_LABELS: Record<StarterActionType, string> = {
  deep_dive: 'Explore',
  meeting_prep: 'Meeting',
  map_workflow: 'Build',
  batch_review: 'Review',
  quick_answers: 'Quick fill',
}

// =============================================================================
// Intelligence Briefing constants
// =============================================================================

import {
  ArrowUpRight,
  ArrowDownRight,
  FileInput,
  Brain,
  Zap,
  Activity,
  FlaskConical,
  Swords,
  Search,
  CalendarDays,
  Route,
  ListChecks,
} from 'lucide-react'

/** Icons for starter action types */
export const STARTER_ACTION_ICONS: Record<StarterActionType, LucideIcon> = {
  deep_dive: Search,
  meeting_prep: CalendarDays,
  map_workflow: Route,
  batch_review: ListChecks,
  quick_answers: Zap,
}

/** Icons for temporal change types */
export const CHANGE_TYPE_ICONS: Record<string, LucideIcon> = {
  belief_strengthened: ArrowUpRight,
  belief_weakened: ArrowDownRight,
  belief_created: Brain,
  entity_created: FileText,
  entity_updated: RefreshCw,
  signal_processed: FileInput,
  fact_added: Zap,
  insight_added: Lightbulb,
}

/** Colors for temporal change types */
export const CHANGE_TYPE_COLORS: Record<string, string> = {
  belief_strengthened: '#3FAF7A',
  belief_weakened: '#999999',
  belief_created: '#0A1E2F',
  entity_created: '#3FAF7A',
  entity_updated: '#666666',
  signal_processed: '#0A1E2F',
  fact_added: '#3FAF7A',
  insight_added: '#25785A',
}

/** Icons for briefing sections */
export const BRIEFING_SECTION_ICONS: Record<string, LucideIcon> = {
  situation: Activity,
  what_changed: Clock,
  tensions: Swords,
  hypotheses: FlaskConical,
  heartbeat: Activity,
  actions: Target,
}

/** Hypothesis status display */
export const HYPOTHESIS_STATUS_LABELS: Record<string, string> = {
  proposed: 'Proposed',
  testing: 'Testing',
  graduated: 'Confirmed',
  rejected: 'Rejected',
}

export const HYPOTHESIS_STATUS_COLORS: Record<string, string> = {
  proposed: '#666666',
  testing: '#0A1E2F',
  graduated: '#3FAF7A',
  rejected: '#999999',
}

// =============================================================================
// Action Chat Context Builder
// =============================================================================

import type { TerseAction } from '@/lib/api/workspace'

const GAP_CHAT_INSTRUCTIONS: Record<string, (a: TerseAction) => string> = {
  step_no_actor: (a) => `This workflow step needs a persona assigned. Help identify who performs "${a.entity_name}" and why.`,
  step_no_pain: (a) => `This workflow step lacks a pain description. Help articulate the current friction in "${a.entity_name}".`,
  step_no_time: (a) => `This workflow step has no time estimate. Help estimate how long "${a.entity_name}" takes today.`,
  step_no_benefit: (a) => `This workflow step needs a benefit. Help describe the value the solution brings to "${a.entity_name}".`,
  workflow_no_future_state: (a) => `This workflow has no future-state vision. Help envision what "${a.entity_name}" looks like after the solution.`,
  workflow_no_drivers: (a) => `This workflow isn't linked to business drivers. Help connect "${a.entity_name}" to business value.`,
  pain_no_workflow: (a) => `This pain point isn't connected to a workflow. Help map "${a.entity_name}" to the affected process.`,
  goal_no_feature: (a) => `This goal has no features mapped. Help identify capabilities that address "${a.entity_name}".`,
  kpi_no_numbers: (a) => `This KPI needs concrete targets. Help define measurable thresholds for "${a.entity_name}".`,
  driver_single_source: (a) => `This driver only has one evidence source. Help identify additional validation for "${a.entity_name}".`,
  persona_no_workflow: (a) => `This persona isn't linked to any workflows. Help identify what processes "${a.entity_name}" participates in.`,
  persona_pains_not_drivers: (a) => `This persona's pains aren't connected to business drivers. Help link "${a.entity_name}" to business impact.`,
  open_question: (a) => `There are open questions blocking progress. Help answer: "${a.sentence}"`,
  critical_questions: (a) => `Critical questions are blocking progress. Help address: "${a.sentence}"`,
}

/** Build rich conversation context for a Next Action click — primes the LLM with gap-specific instructions and card usage directives. */
export function buildActionChatContext(action: TerseAction): string {
  const parts: string[] = []

  // Gap-type-specific instruction
  const gapFn = GAP_CHAT_INSTRUCTIONS[action.gap_type]
  if (gapFn) {
    parts.push(gapFn(action))
  } else {
    parts.push(`The consultant clicked a Next Action card: "${action.sentence}".`)
  }

  // Entity context
  if (action.entity_type && action.entity_name) {
    parts.push(`Entity: ${action.entity_type} "${action.entity_name}"${action.entity_id ? ` (ID: ${action.entity_id})` : ''}.`)
  }

  // Behavioral directive — use cards, don't narrate
  parts.push(
    'Search silently for relevant context, then present findings as structured cards (gap_closer, choice, or smart_summary). ' +
    'Your text should be 1-2 sentences of insight max. Do NOT narrate your search process. ' +
    'Be warm — this is a teammate asking for help knocking out a priority.'
  )

  return parts.join(' ')
}
