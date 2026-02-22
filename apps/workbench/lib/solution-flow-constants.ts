/**
 * Shared constants for solution flow components.
 * Single source of truth for phase config, ordering, and status colors.
 */

export const PHASE_ORDER = ['entry', 'core_experience', 'output', 'admin'] as const

export type FlowPhase = (typeof PHASE_ORDER)[number]

export const SOLUTION_FLOW_PHASES: Record<string, { label: string; fullLabel: string; color: string }> = {
  entry: { label: 'Entry', fullLabel: 'Entry', color: 'bg-[#0A1E2F]/10 text-[#0A1E2F]' },
  core_experience: { label: 'Core', fullLabel: 'Core Experience', color: 'bg-[#3FAF7A]/10 text-[#25785A]' },
  output: { label: 'Output', fullLabel: 'Output', color: 'bg-[#0D2A35]/10 text-[#0D2A35]' },
  admin: { label: 'Admin', fullLabel: 'Admin', color: 'bg-[#F4F4F4] text-[#666666]' },
}

export const STATUS_BORDER: Record<string, string> = {
  confirmed_client: 'border-l-[#3FAF7A]',
  confirmed_consultant: 'border-l-[#0A1E2F]',
  needs_client: 'border-l-[#C4A97D]',
  ai_generated: 'border-l-[#E5E5E5]',
}

export const CONFIDENCE_DOT_COLOR: Record<string, string> = {
  known: 'bg-[#3FAF7A]',
  inferred: 'bg-[#0A1E2F]/40',
  guess: 'bg-[#BBBBBB]',
  unknown: 'bg-[#E5E5E5]',
}
