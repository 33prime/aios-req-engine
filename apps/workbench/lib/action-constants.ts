/**
 * Shared action constants — single source of truth for action icons,
 * urgency colors, execution types, and CTA labels.
 *
 * Used by: NextActionsBar, OverviewPanel, WorkspaceChat, ProjectsCards, BRDCanvas
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
} from 'lucide-react'

export const ACTION_ICONS: Record<string, typeof Target> = {
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
}

export const URGENCY_COLORS: Record<string, string> = {
  critical: '#EF4444',
  high: '#F97316',
  normal: '#3FAF7A',
  low: '#999999',
}

export type ActionExecutionType = 'drawer' | 'navigate' | 'inline' | 'chat'

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
}

export const ACTION_CTA_LABELS: Record<ActionExecutionType, string> = {
  inline: 'Confirm All',
  drawer: 'Open',
  navigate: 'Go to Section',
  chat: 'Ask AI',
}

/** Get the CTA label for a given action_type */
export function getActionCTALabel(actionType: string): string {
  const execType = ACTION_EXECUTION_MAP[actionType]
  if (!execType) return 'View'
  return ACTION_CTA_LABELS[execType]
}
