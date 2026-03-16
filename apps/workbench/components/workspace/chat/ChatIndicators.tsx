/**
 * ChatIndicators — Shared activity indicator and tool chip components.
 *
 * ActivityIndicator: Replaces bouncing dots with a spinner + contextual label.
 * ToolChip: Compact pill shown after a tool completes (non-card tools only).
 */

'use client'

import { Search, PenLine, Sparkles, FileText, Zap, type LucideIcon } from 'lucide-react'

// =============================================================================
// Tool Label Config
// =============================================================================

const TOOL_LABELS: Record<string, string> = {
  // Consolidated 6-tool system
  search: 'Searching project...',
  write: 'Updating BRD...',
  process: 'Processing...',
  solution_flow: 'Updating flow...',
  client_portal: 'Portal action...',
  suggest_actions: 'Preparing actions...',
  // Action-qualified labels (tool_name.action)
  'write.create': 'Creating entity...',
  'write.update': 'Updating entity...',
  'write.delete': 'Removing entity...',
  'process.signal': 'Processing signal...',
  'process.belief': 'Recording belief...',
  'process.evidence': 'Attaching evidence...',
  'process.strategic_context': 'Generating context...',
  'process.identify_stakeholders': 'Identifying stakeholders...',
  'solution_flow.update': 'Updating step...',
  'solution_flow.add': 'Adding step...',
  'solution_flow.remove': 'Removing step...',
  'solution_flow.reorder': 'Reordering steps...',
  'solution_flow.resolve_question': 'Resolving question...',
  'solution_flow.refine': 'Refining step...',
}

/** Tools that render their own card — skip chip for these */
const CARD_TOOLS = new Set(['suggest_actions'])

const TOOL_CHIP_CONFIG: Record<string, { label: string; icon: LucideIcon }> = {
  // Consolidated tools — show chip after completion
  write: { label: 'Updated BRD', icon: PenLine },
  process: { label: 'Processed', icon: Sparkles },
  solution_flow: { label: 'Updated flow', icon: PenLine },
  client_portal: { label: 'Portal action', icon: Sparkles },
}

// =============================================================================
// ActivityIndicator
// =============================================================================

export interface ActivityState {
  phase: 'thinking' | 'tool' | 'document'
  toolName?: string
  action?: string
}

interface ActivityIndicatorProps {
  state: ActivityState
}

export function ActivityIndicator({ state }: ActivityIndicatorProps) {
  let label = 'Thinking...'

  if (state.phase === 'document') {
    label = 'Analyzing document...'
  } else if (state.phase === 'tool' && state.toolName) {
    // Try action-qualified key first, then tool name
    const actionKey = state.action ? `${state.toolName}.${state.action}` : ''
    label = (actionKey && TOOL_LABELS[actionKey]) || TOOL_LABELS[state.toolName] || 'Working...'
  }

  return (
    <div className="flex justify-start">
      <div className="flex items-center gap-2.5 px-4 py-3 bg-white border border-border rounded-2xl rounded-bl-md shadow-sm">
        <div className="w-4 h-4 border-2 border-[#E5E5E5] border-t-brand-primary rounded-full animate-spin" />
        <span className="text-[12px] text-[#666]">{label}</span>
      </div>
    </div>
  )
}

// =============================================================================
// ToolChip
// =============================================================================

interface ToolChipProps {
  toolName: string
  result?: Record<string, unknown>
  count?: number
}

export function ToolChip({ toolName, result, count = 1 }: ToolChipProps) {
  // Skip tools that have dedicated card rendering
  if (CARD_TOOLS.has(toolName)) return null

  const config = TOOL_CHIP_CONFIG[toolName]
  if (!config) return null

  const Icon = config.icon
  let label = config.label

  // Enrich label with result count for search
  if (toolName === 'search') {
    if (count > 1) {
      label = `Searched project (${count})`
    } else if (result) {
      const total = (result as Record<string, unknown>).total_results
      if (typeof total === 'number') {
        label = `Searched ${total} results`
      }
    }
  } else if (count > 1) {
    label = `${config.label} (${count})`
  }

  // Enrich with entity type for CRUD tools (only when single)
  if (count === 1 && result && typeof (result as Record<string, unknown>).entity_type === 'string') {
    const entityType = (result as Record<string, unknown>).entity_type as string
    const readable = entityType.replace(/_/g, ' ')
    if (toolName === 'create_entity') label = `Created ${readable}`
    else if (toolName === 'update_entity') label = `Updated ${readable}`
    else if (toolName === 'delete_entity') label = `Removed ${readable}`
  }

  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-[#F0F1F3] rounded-full text-[11px] text-[#666] mr-1 mb-1">
      <Icon className="w-3 h-3" />
      {label}
    </span>
  )
}

/** Group tool calls by name — collapse duplicates with counts */
export function groupToolChips(
  toolCalls: Array<{ tool_name: string; status: string; result?: unknown }>
): Array<{ tool_name: string; result?: Record<string, unknown>; count: number }> {
  const groups: Array<{ tool_name: string; result?: Record<string, unknown>; count: number }> = []
  for (const tc of toolCalls) {
    if (tc.status !== 'complete' || !isChipTool(tc.tool_name)) continue
    const existing = groups.find((g) => g.tool_name === tc.tool_name)
    if (existing) {
      existing.count++
      existing.result = tc.result as Record<string, unknown>
    } else {
      groups.push({ tool_name: tc.tool_name, result: tc.result as Record<string, unknown>, count: 1 })
    }
  }
  return groups
}

/** Check if a tool should render as a chip (not a card) */
export function isChipTool(toolName: string): boolean {
  return !CARD_TOOLS.has(toolName) && toolName in TOOL_CHIP_CONFIG
}
