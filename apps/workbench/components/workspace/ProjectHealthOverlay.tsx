'use client'

import { useState, useEffect } from 'react'
import { ArrowRight, X } from 'lucide-react'
import { getPulseSnapshot } from '@/lib/api'
import { useIntelligenceBriefing } from '@/lib/hooks/use-api'
import type { PulseSnapshot } from '@/types/api'

interface ProjectHealthOverlayProps {
  projectId: string
  completeness?: unknown
  onDismiss: () => void
}

const STAGE_STEPS = [
  { key: 'discovery', label: 'Discovery' },
  { key: 'validation', label: 'Validation' },
  { key: 'prototype', label: 'Prototype' },
  { key: 'specification', label: 'Build' },
]

const ENTITY_LABELS: Record<string, string> = {
  feature: 'Features',
  persona: 'Personas',
  workflow: 'Workflows',
  workflow_step: 'Workflow Steps',
  business_driver: 'Drivers',
  stakeholder: 'Stakeholders',
  data_entity: 'Data Entities',
  constraint: 'Constraints',
  competitor: 'Competitors',
}

const HEALTH_CLUSTERS: Array<{ label: string; types: string[] }> = [
  { label: 'People', types: ['persona', 'stakeholder'] },
  { label: 'Solution', types: ['feature', 'workflow', 'workflow_step'] },
  { label: 'Context', types: ['business_driver', 'constraint', 'competitor'] },
]

/** Render inline markdown: **bold** and *italic* */
function InlineMarkdown({ text }: { text: string }) {
  const parts: Array<{ content: string; style: 'normal' | 'bold' | 'italic' }> = []
  let remaining = text

  while (remaining.length > 0) {
    const boldMatch = remaining.match(/\*\*(.+?)\*\*/)
    const italicMatch = remaining.match(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/)
    const boldIdx = boldMatch?.index ?? Infinity
    const italicIdx = italicMatch?.index ?? Infinity

    if (boldIdx === Infinity && italicIdx === Infinity) {
      parts.push({ content: remaining, style: 'normal' })
      break
    }

    if (boldIdx <= italicIdx) {
      if (boldIdx > 0) parts.push({ content: remaining.slice(0, boldIdx), style: 'normal' })
      parts.push({ content: boldMatch![1], style: 'bold' })
      remaining = remaining.slice(boldIdx + boldMatch![0].length)
    } else {
      if (italicIdx > 0) parts.push({ content: remaining.slice(0, italicIdx), style: 'normal' })
      parts.push({ content: italicMatch![1], style: 'italic' })
      remaining = remaining.slice(italicIdx + italicMatch![0].length)
    }
  }

  return (
    <>
      {parts.map((p, i) => {
        if (p.style === 'bold') return <strong key={i} className="font-semibold">{p.content}</strong>
        if (p.style === 'italic') return <em key={i} className="italic">{p.content}</em>
        return <span key={i}>{p.content}</span>
      })}
    </>
  )
}

function ScoreRing({ score, stage, gateProgress }: { score: number; stage: string; gateProgress: string }) {
  const size = 80
  const radius = (size - 8) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (score / 100) * circumference
  const color = score >= 70 ? '#3FAF7A' : score >= 40 ? '#044159' : '#D4D4D4'

  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="relative" style={{ width: size, height: size }}>
        <svg className="-rotate-90" width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#E5E5E5" strokeWidth="5" />
          <circle
            cx={size / 2} cy={size / 2} r={radius}
            fill="none" stroke={color} strokeWidth="5" strokeLinecap="round"
            strokeDasharray={circumference} strokeDashoffset={offset}
            className="transition-all duration-1000 ease-out"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-[20px] font-bold text-text-body">{Math.round(score)}</span>
        </div>
      </div>
      <span className="text-[11px] font-medium text-text-body capitalize">{stage}</span>
      <span className="text-[10px] text-text-placeholder bg-[#F5F5F5] px-2 py-0.5 rounded-full">
        {gateProgress} met
      </span>
    </div>
  )
}

function StageJourney({ currentStage }: { currentStage: string }) {
  const currentIdx = STAGE_STEPS.findIndex((s) => s.key === currentStage)

  return (
    <div className="flex items-center">
      {STAGE_STEPS.map((step, i) => {
        const isCurrent = i === currentIdx
        const isPast = i < currentIdx
        return (
          <div key={step.key} className="flex items-center">
            {i > 0 && (
              <div
                className="w-6 h-[2px] mx-0.5"
                style={{ backgroundColor: isPast || isCurrent ? '#3FAF7A' : '#E5E5E5' }}
              />
            )}
            {isCurrent ? (
              <span className="text-[10px] font-semibold text-white bg-[#3FAF7A] px-2.5 py-1 rounded-full whitespace-nowrap">
                {step.label}
              </span>
            ) : (
              <span
                className="text-[10px] font-medium px-1.5 py-1 whitespace-nowrap"
                style={{ color: isPast ? '#3FAF7A' : '#999999' }}
              >
                {step.label}
              </span>
            )}
          </div>
        )
      })}
    </div>
  )
}

function HealthDot({ directive }: { directive: string }) {
  const color =
    directive === 'stable' || directive === 'merge_only'
      ? '#3FAF7A'
      : directive === 'grow' || directive === 'enrich' || directive === 'confirm'
        ? '#044159'
        : '#D4D4D4'
  const filled = color !== '#D4D4D4'

  return (
    <span
      className="inline-block w-2 h-2 rounded-full flex-shrink-0"
      style={filled ? { backgroundColor: color } : { border: '1.5px solid #D4D4D4' }}
    />
  )
}

function HealthClusters({ health }: { health: PulseSnapshot['health'] }) {
  return (
    <div className="space-y-4">
      {HEALTH_CLUSTERS.map((cluster) => {
        const entities = cluster.types
          .filter((t) => health[t])
          .map((t) => ({ type: t, ...health[t] }))
        if (entities.length === 0) return null

        return (
          <div key={cluster.label}>
            <h4 className="text-[10px] font-semibold text-text-placeholder uppercase tracking-wide mb-1.5">
              {cluster.label}
            </h4>
            <div className="space-y-1">
              {entities.map((e) => (
                <div key={e.type} className="flex items-center gap-2">
                  <HealthDot directive={e.directive} />
                  <span className="text-[11px] text-text-body flex-1 truncate">
                    {ENTITY_LABELS[e.type] || e.type}
                  </span>
                  <span className="text-[10px] font-mono text-[#999999]">
                    {e.count}/{e.target}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}

const ACTION_BADGE_STYLES: Record<string, { label: string; bg: string; text: string }> = {
  interview: { label: 'Interview', bg: 'rgba(4,65,89,0.06)', text: '#044159' },
  research: { label: 'Research', bg: '#D1FAE5', text: '#047857' },
  review: { label: 'Review', bg: 'rgba(4,65,89,0.08)', text: '#044159' },
  signal: { label: 'Signal', bg: 'rgba(63,175,122,0.08)', text: '#2a8f5f' },
}

function actionBadgeFor(action: PulseSnapshot['actions'][number]) {
  if (action.unblocks_gate) return ACTION_BADGE_STYLES.review
  // Map from entity type heuristics
  const s = action.sentence.toLowerCase()
  if (s.includes('interview') || s.includes('stakeholder') || s.includes('call'))
    return ACTION_BADGE_STYLES.interview
  if (s.includes('upload') || s.includes('compet') || s.includes('research'))
    return ACTION_BADGE_STYLES.research
  return ACTION_BADGE_STYLES.signal
}

function NextActions({ actions }: { actions: PulseSnapshot['actions'] }) {
  const items = actions.slice(0, 3)
  if (items.length === 0) {
    return <p className="text-[12px] text-[#3FAF7A]">No urgent actions right now</p>
  }

  return (
    <div className="grid grid-cols-3 gap-3">
      {items.map((action, i) => {
        const badge = actionBadgeFor(action)
        return (
          <div
            key={i}
            className="flex flex-col gap-2 p-3 bg-[#F5F5F5] rounded-lg border border-transparent hover:border-[#3FAF7A] hover:bg-white cursor-pointer transition-all"
          >
            <div className="flex items-center gap-2">
              <span className="w-[20px] h-[20px] rounded-full bg-[#3FAF7A] text-white text-[10px] font-bold flex items-center justify-center flex-shrink-0">
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
            <span className="text-[#D4D4D4] text-sm self-end hover:text-[#3FAF7A] transition-colors">→</span>
          </div>
        )
      })}
    </div>
  )
}

export function ProjectHealthOverlay({ projectId, onDismiss }: ProjectHealthOverlayProps) {
  const [pulse, setPulse] = useState<PulseSnapshot | null>(null)
  const [loading, setLoading] = useState(true)
  const { data: briefing } = useIntelligenceBriefing(projectId)

  useEffect(() => {
    setLoading(true)
    getPulseSnapshot(projectId)
      .then(setPulse)
      .catch(() => setPulse(null))
      .finally(() => setLoading(false))
  }, [projectId])

  // Compute weighted average health
  const healthEntries = Object.entries(pulse?.health || {})
  const avgHealth = healthEntries.length > 0
    ? healthEntries.reduce((sum, [, h]) => sum + h.health_score, 0) / healthEntries.length
    : 0

  const stage = pulse?.stage || 'discovery'
  const gateProgress = pulse ? `${pulse.gates_met}/${pulse.gates_total}` : '0/0'
  const briefingNarrative = briefing?.situation?.narrative ?? ''

  // Use the first paragraph of the briefing narrative, or a warm fallback
  const narrative = (() => {
    if (briefingNarrative) {
      // Take just the first paragraph (split on double newline or period-space after 80+ chars)
      const firstPara = briefingNarrative.split(/\n\n/)[0]
      return firstPara.length > 600 ? firstPara.slice(0, 597) + '...' : firstPara
    }
    if (!pulse) return ''
    const stageLabel = STAGE_STEPS.find((s) => s.key === stage)?.label || stage
    return (
      `Your project is moving through **${stageLabel}**. `
      + 'Open the briefing panel for a full intelligence summary.'
    )
  })()

  // Sub-metrics from forecast
  const forecast = pulse?.forecast
  const subMetrics = forecast
    ? [
        { label: 'Coverage', value: Math.round(forecast.coverage_index * 100) },
        { label: 'Confidence', value: Math.round(forecast.confidence_index * 100) },
        { label: 'Readiness', value: Math.round(forecast.prototype_readiness * 100) },
      ]
    : []

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center">
      <div className="absolute inset-0 bg-white/60 backdrop-blur-sm" onClick={onDismiss} />

      <div className="relative w-full max-w-[860px] max-h-[85vh] overflow-y-auto bg-white rounded-2xl shadow-2xl border border-border">
        <button
          onClick={onDismiss}
          className="absolute top-4 right-4 z-10 text-text-placeholder hover:text-text-body transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-primary" />
          </div>
        ) : !pulse ? (
          <div className="py-16 text-center">
            <p className="text-sm text-text-placeholder">Unable to load project health data.</p>
          </div>
        ) : (
          <>
            {/* 2-column layout */}
            <div className="flex">
              {/* Left column — ~55% */}
              <div className="flex-[55] p-8 pr-6 border-r border-border flex flex-col">
                {/* Score header — ring left, meta right */}
                <div className="flex items-start gap-5 mb-5">
                  <ScoreRing score={avgHealth} stage={stage} gateProgress={gateProgress} />
                  <div className="flex-1 pt-1">
                    <StageJourney currentStage={stage} />
                    {subMetrics.length > 0 && (
                      <div className="flex flex-wrap gap-2 mt-3">
                        {subMetrics.map((m) => (
                          <span
                            key={m.label}
                            className="bg-[#F5F5F5] text-[#7B7B7B] text-[10px] px-2 py-0.5 rounded-full"
                          >
                            {m.label} {m.value}%
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Narrative text — fills remaining space */}
                <div className="flex-1">
                  {narrative ? (
                    <p className="text-[13px] text-text-body leading-[1.7]">
                      <InlineMarkdown text={narrative} />
                    </p>
                  ) : (
                    <p className="text-[13px] text-text-placeholder leading-[1.7]">
                      Process signals to generate a project narrative.
                    </p>
                  )}
                </div>
              </div>

              {/* Right column — ~45% */}
              <div className="flex-[45] p-8 pl-6">
                <h3 className="text-[11px] font-semibold text-text-placeholder uppercase tracking-wide mb-3">
                  Entity Health
                </h3>
                <HealthClusters health={pulse.health} />
              </div>
            </div>

            {/* Next Actions — full-width 3-column row */}
            <div className="px-8 pb-2">
              <h3 className="text-[11px] font-semibold text-text-placeholder uppercase tracking-wide mb-2">
                Next Actions
              </h3>
              <NextActions actions={pulse.actions || []} />
            </div>

            {/* Footer */}
            <div className="px-8 pb-5 flex justify-end">
              <button
                onClick={onDismiss}
                className="flex items-center gap-1.5 bg-[#3FAF7A] text-white text-[12px] font-semibold px-4 py-2 rounded-lg hover:bg-[#25785A] transition-colors"
              >
                Got it <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
