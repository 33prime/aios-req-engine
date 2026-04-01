'use client'

import { Loader2 } from 'lucide-react'
import { useIntelligence } from '@/lib/hooks/use-api'
import { Markdown } from '@/components/ui/Markdown'
import type { SynthesizedAction } from '@/lib/api/workspace'
import type { BRDWorkspaceData } from '@/types/workspace'

interface IntelligenceSectionProps {
  data?: BRDWorkspaceData
  health?: unknown
  healthLoading?: boolean
  onRefreshAll?: () => void
  isRefreshing?: boolean
  projectId?: string
  onActionClick?: (action: SynthesizedAction) => void
}

// ============================================================================
// Score Ring — matches ProjectHealthOverlay exactly
// ============================================================================

function ScoreRing({ score, size = 60 }: { score: number; size?: number }) {
  const r = (size / 2) - 6
  const circumference = 2 * Math.PI * r
  const offset = circumference - (score / 100) * circumference
  const color = score >= 70 ? '#3FAF7A' : score >= 40 ? '#044159' : '#D4D4D4'

  return (
    <div className="relative flex-shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#F0F0F0" strokeWidth={4} />
        <circle
          cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={4}
          strokeDasharray={circumference} strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 0.8s ease-out' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-[16px] font-bold leading-none" style={{ color }}>{Math.round(score)}</span>
        <span className="text-[8px] text-text-placeholder mt-0.5">%</span>
      </div>
    </div>
  )
}

// ============================================================================
// Stage Journey — matches ProjectHealthOverlay exactly
// ============================================================================

const STAGES = ['discovery', 'validation', 'prototype', 'build'] as const
const STAGE_LABELS: Record<string, string> = {
  discovery: 'Discovery', validation: 'Validation', prototype: 'Prototype', build: 'Build',
}

function StageJourney({ currentStage }: { currentStage: string }) {
  const idx = STAGES.indexOf(currentStage as typeof STAGES[number])

  return (
    <div className="flex items-center gap-1">
      {STAGES.map((s, i) => {
        const cls = i < idx ? 'text-brand-primary font-medium'
          : i === idx ? 'bg-brand-primary text-white font-semibold px-2 py-0.5 rounded-full'
          : 'text-[#D4D4D4]'
        const connector = i > 0
          ? <div className={`w-3 h-px ${i <= idx ? 'bg-brand-primary' : 'bg-[#D4D4D4]'}`} />
          : null
        return (
          <div key={s} className="flex items-center gap-1">
            {connector}
            <span className={`text-[11px] whitespace-nowrap ${cls}`}>{STAGE_LABELS[s]}</span>
          </div>
        )
      })}
    </div>
  )
}

// ============================================================================
// Action Card — 3-col grid with click→chat
// ============================================================================

const ACTION_BADGE_STYLES: Record<string, { label: string; bg: string; text: string }> = {
  interview: { label: 'Interview', bg: 'rgba(4,65,89,0.06)', text: '#044159' },
  research: { label: 'Research', bg: '#D1FAE5', text: '#047857' },
  review: { label: 'Review', bg: 'rgba(4,65,89,0.08)', text: '#044159' },
  signal: { label: 'Signal', bg: 'rgba(63,175,122,0.08)', text: '#2a8f5f' },
  confirm: { label: 'Confirm', bg: 'rgba(63,175,122,0.12)', text: '#2a8f5f' },
}

function NextActions({
  actions,
  onActionClick,
}: {
  actions: SynthesizedAction[]
  onActionClick?: (action: SynthesizedAction) => void
}) {
  const items = actions.slice(0, 3)
  if (items.length === 0) {
    return <p className="text-[12px] text-brand-primary">No urgent actions right now</p>
  }

  return (
    <div className="grid grid-cols-3 gap-3">
      {items.map((action, i) => {
        const badge = ACTION_BADGE_STYLES[action.action_type] || ACTION_BADGE_STYLES.signal
        return (
          <div
            key={i}
            className="flex flex-col gap-2 p-3 bg-[#F5F5F5] rounded-lg border border-transparent hover:border-brand-primary hover:bg-white cursor-pointer transition-all"
            onClick={() => onActionClick?.(action)}
          >
            <div className="flex items-center gap-2">
              <span className="w-[20px] h-[20px] rounded-full bg-brand-primary text-white text-[10px] font-bold flex items-center justify-center flex-shrink-0">
                {i + 1}
              </span>
              <span
                className="text-[9px] uppercase font-bold tracking-wide px-1.5 py-0.5 rounded"
                style={{ backgroundColor: badge.bg, color: badge.text }}
              >
                {badge.label}
              </span>
            </div>
            <p className="text-[12px] text-[#4B4B4B] leading-snug flex-1">{action.sentence}</p>
            <span className="text-[#D4D4D4] text-sm self-end hover:text-brand-primary transition-colors">→</span>
          </div>
        )
      })}
    </div>
  )
}

// ============================================================================
// Main — Deal Pulse Strip
// ============================================================================

export function IntelligenceSection({
  data,
  health,
  healthLoading,
  onRefreshAll,
  isRefreshing,
  projectId: projectIdProp,
  onActionClick,
}: IntelligenceSectionProps) {
  const projectId = projectIdProp || ''

  const { data: intelligence, isLoading: loading } = useIntelligence(projectId || undefined)

  // Compute health score from unified response
  const avgHealth = intelligence?.pulse?.health_score ?? 0
  const stage = intelligence?.pulse?.stage || 'discovery'
  const forecast = intelligence?.pulse?.forecast
  const pulseText = intelligence?.deal_pulse_text
  const actions = intelligence?.actions || []

  const subMetrics = forecast
    ? [
        { label: 'Coverage', value: Math.round(forecast.coverage_index * 100) },
        { label: 'Confidence', value: Math.round(forecast.confidence_index * 100) },
        { label: 'Readiness', value: Math.round(forecast.prototype_readiness * 100) },
      ]
    : []

  return (
    <section className="mb-8">
      <div className="bg-white rounded-2xl shadow-md border border-border overflow-hidden">
        {/* Header: Score ring + stage journey + sub-metrics */}
        <div className="px-5 pt-5 pb-3 flex items-center gap-4">
          <ScoreRing score={avgHealth} />
          <div className="flex flex-col gap-1.5">
            <StageJourney currentStage={stage} />
            {subMetrics.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {subMetrics.map((m) => (
                  <span key={m.label} className="bg-[#F5F5F5] text-[#7B7B7B] text-[10px] px-2 py-0.5 rounded-full">
                    {m.label} {m.value}%
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Pulse narrative */}
        <div className="px-5 pb-4">
          {loading && !pulseText ? (
            <div className="flex items-center gap-2 text-[12px] text-text-placeholder py-2">
              <Loader2 className="w-3 h-3 animate-spin" />
              Generating project summary...
            </div>
          ) : pulseText ? (
            <Markdown
              content={pulseText}
              className="text-[14px] text-[#444444] leading-[1.75] [&_p]:mb-1.5 [&_p:last-child]:mb-0 [&_strong]:text-text-body [&_strong]:font-semibold [&_em]:text-[#555555]"
            />
          ) : (
            <p className="text-[13px] text-text-placeholder italic">
              Add more signals and entities to generate a project summary.
            </p>
          )}
        </div>

        {/* Next actions — 3-column grid with click→chat */}
        {actions.length > 0 && (
          <div className="border-t border-[#F0F0F0] px-5 py-4">
            <p className="text-[11px] font-semibold text-text-placeholder uppercase tracking-wide mb-2.5">
              Next Actions
            </p>
            <NextActions actions={actions} onActionClick={onActionClick} />
          </div>
        )}
      </div>
    </section>
  )
}
