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
  needs_client: 'border-l-[#0A1E2F]/40',
  ai_generated: 'border-l-[#E5E5E5]',
}

export const CONFIDENCE_DOT_COLOR: Record<string, string> = {
  known: 'bg-[#3FAF7A]',
  inferred: 'bg-[#0A1E2F]/40',
  guess: 'bg-[#BBBBBB]',
  unknown: 'bg-[#E5E5E5]',
}

/** Phase lane config for the v3e canvas layout */
export const LANE_CONFIG: Record<string, { label: string; subtitle: string; flex: number }> = {
  entry: { label: 'Getting Started', subtitle: 'Setup & onboarding', flex: 1 },
  core_experience: { label: 'The Core Experience', subtitle: 'Where the value lives', flex: 1.8 },
  output: { label: 'What You Get', subtitle: 'Reports & deliverables', flex: 1 },
  admin: { label: 'Keeping It Sharp', subtitle: 'Configuration & tuning', flex: 1 },
}

/** Phase-specific card styles for gradient backgrounds, borders, and index badges */
export const PHASE_CARD_STYLE: Record<string, {
  bg: string
  border: string
  hoverBorder: string
  hoverShadow: string
  idxBg: string
  idxColor: string
  laneWash: string
  labelColor: string
  sublabelColor: string
}> = {
  entry: {
    bg: 'linear-gradient(135deg, #fff 0%, rgba(4,65,89,0.04) 100%)',
    border: 'rgba(4,65,89,0.12)',
    hoverBorder: '#044159',
    hoverShadow: '0 4px 16px rgba(4,65,89,0.08)',
    idxBg: 'rgba(4,65,89,0.08)',
    idxColor: '#044159',
    laneWash: 'rgba(4,65,89,0.018)',
    labelColor: '#044159',
    sublabelColor: 'rgba(4,65,89,0.5)',
  },
  core_experience: {
    bg: 'linear-gradient(135deg, #fff 0%, rgba(63,175,122,0.05) 100%)',
    border: 'rgba(63,175,122,0.20)',
    hoverBorder: '#3FAF7A',
    hoverShadow: '0 6px 20px rgba(63,175,122,0.12)',
    idxBg: 'rgba(63,175,122,0.08)',
    idxColor: '#2A8F5F',
    laneWash: 'linear-gradient(180deg, rgba(63,175,122,0.025) 0%, rgba(63,175,122,0.06) 100%)',
    labelColor: '#2A8F5F',
    sublabelColor: 'rgba(63,175,122,0.6)',
  },
  output: {
    bg: 'linear-gradient(135deg, #fff 0%, rgba(10,30,47,0.03) 100%)',
    border: 'rgba(10,30,47,0.10)',
    hoverBorder: '#0A1E2F',
    hoverShadow: '0 4px 16px rgba(10,30,47,0.08)',
    idxBg: 'rgba(10,30,47,0.06)',
    idxColor: '#0A1E2F',
    laneWash: 'rgba(10,30,47,0.015)',
    labelColor: '#0A1E2F',
    sublabelColor: 'rgba(10,30,47,0.4)',
  },
  admin: {
    bg: 'linear-gradient(135deg, #fff 0%, rgba(0,0,0,0.02) 100%)',
    border: 'rgba(0,0,0,0.08)',
    hoverBorder: '#718096',
    hoverShadow: '0 4px 16px rgba(0,0,0,0.06)',
    idxBg: 'rgba(0,0,0,0.04)',
    idxColor: '#718096',
    laneWash: 'rgba(0,0,0,0.01)',
    labelColor: '#718096',
    sublabelColor: '#A0AEC0',
  },
}

/** Maps implied_pattern to a human-readable display label */
export const PATTERN_LABELS: Record<string, string> = {
  dashboard: 'Dashboard',
  table: 'Data Table',
  wizard: 'Setup Wizard',
  card: 'Card View',
  form: 'Form / Input',
  timeline: 'Activity Feed',
  kanban: 'Pipeline Board',
  map: 'Geographic View',
  comparison: 'Comparison View',
  report: 'Report Output',
  chat: 'AI Conversation',
  calendar: 'Schedule Planner',
  gallery: 'Media Gallery',
  tree: 'Hierarchy Navigator',
  metrics: 'KPI Dashboard',
  inbox: 'Message Queue',
  splitview: 'Master-Detail',
}
