'use client'

import { useState, useEffect } from 'react'
import {
  Activity, X, ArrowRight, AlertTriangle, CheckCircle2,
  TrendingUp, Shield, Zap, Target,
} from 'lucide-react'
import { getPulseSnapshot } from '@/lib/api'
import type { PulseSnapshot } from '@/types/api'

interface ProjectHealthOverlayProps {
  projectId: string
  completeness?: unknown
  onDismiss: () => void
}

const STAGE_LABELS: Record<string, string> = {
  discovery: 'Discovery',
  validation: 'Validation',
  prototype: 'Prototype',
  specification: 'Specification',
  handoff: 'Handoff',
}

const DIRECTIVE_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  stable: { bg: 'bg-[#3FAF7A]/12', text: 'text-[#25785A]', label: 'Healthy' },
  grow: { bg: 'bg-[#3B82F6]/12', text: 'text-[#1D4ED8]', label: 'Needs more' },
  enrich: { bg: 'bg-[#F59E0B]/12', text: 'text-[#92400E]', label: 'Enrich' },
  confirm: { bg: 'bg-[#F97316]/12', text: 'text-[#9A3412]', label: 'Confirm' },
  merge_only: { bg: 'bg-[#6366F1]/12', text: 'text-[#4338CA]', label: 'Saturated' },
}

const ENTITY_LABELS: Record<string, string> = {
  feature: 'Features',
  persona: 'Personas',
  workflow: 'Workflows',
  workflow_step: 'Workflow Steps',
  business_driver: 'Business Drivers',
  stakeholder: 'Stakeholders',
  data_entity: 'Data Entities',
  constraint: 'Constraints',
  competitor: 'Competitors',
}

function ScoreRing({ score, size = 96 }: { score: number; size?: number }) {
  const radius = (size - 12) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (score / 100) * circumference
  const color = score >= 70 ? '#3FAF7A' : score >= 40 ? '#F59E0B' : '#EF4444'

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg className="-rotate-90" width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#E5E5E5" strokeWidth="6" />
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke={color} strokeWidth="6" strokeLinecap="round"
          strokeDasharray={circumference} strokeDashoffset={offset}
          className="transition-all duration-1000 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-[22px] font-bold text-[#333333]">{Math.round(score)}</span>
        <span className="text-[9px] text-[#999999] uppercase tracking-wide">/ 100</span>
      </div>
    </div>
  )
}

function EntityRow({ entityType, health }: {
  entityType: string
  health: PulseSnapshot['health'][string]
}) {
  const dir = DIRECTIVE_STYLES[health.directive] || DIRECTIVE_STYLES.stable
  const pct = health.target > 0 ? Math.min(100, Math.round((health.count / health.target) * 100)) : 100
  const barColor = health.health_score >= 70 ? '#3FAF7A' : health.health_score >= 40 ? '#F59E0B' : '#EF4444'

  return (
    <div className="flex items-center gap-2.5 py-1.5">
      <span className="text-[12px] text-[#333333] w-[110px] truncate font-medium">
        {ENTITY_LABELS[entityType] || entityType}
      </span>
      <div className="flex-1 h-1.5 bg-[#E5E5E5] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, backgroundColor: barColor }}
        />
      </div>
      <span className="text-[11px] font-mono text-[#666666] w-12 text-right">
        {health.count}/{health.target}
      </span>
      <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${dir.bg} ${dir.text} w-[68px] text-center`}>
        {dir.label}
      </span>
    </div>
  )
}

export function ProjectHealthOverlay({ projectId, onDismiss }: ProjectHealthOverlayProps) {
  const [pulse, setPulse] = useState<PulseSnapshot | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    getPulseSnapshot(projectId)
      .then(setPulse)
      .catch(() => setPulse(null))
      .finally(() => setLoading(false))
  }, [projectId])

  // Compute weighted average health
  const healthEntries = Object.entries(pulse?.health || {}).sort(
    ([, a], [, b]) => b.health_score - a.health_score
  )
  const avgHealth = healthEntries.length > 0
    ? healthEntries.reduce((sum, [, h]) => sum + h.health_score, 0) / healthEntries.length
    : 0

  const stageLabel = STAGE_LABELS[pulse?.stage || 'discovery'] || pulse?.stage || 'Discovery'
  const gateProgress = pulse ? `${pulse.gates_met}/${pulse.gates_total}` : '0/0'
  const risk = pulse?.risks
  const forecast = pulse?.forecast

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center">
      <div className="absolute inset-0 bg-white/60 backdrop-blur-sm" onClick={onDismiss} />

      <div className="relative w-full max-w-lg max-h-[85vh] overflow-y-auto bg-white rounded-2xl shadow-2xl border border-[#E5E5E5] p-8">
        <button onClick={onDismiss} className="absolute top-4 right-4 text-[#999999] hover:text-[#333333]">
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-2 mb-5">
          <Activity className="w-5 h-5 text-[#3FAF7A]" />
          <h2 className="text-lg font-semibold text-[#333333]">Project Health</h2>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#3FAF7A]" />
          </div>
        ) : !pulse ? (
          <p className="text-sm text-[#999999] text-center py-8">
            Unable to load project health data.
          </p>
        ) : (
          <>
            {/* Stage + Score row */}
            <div className="flex items-center gap-5 mb-5">
              <ScoreRing score={avgHealth} />
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="text-[13px] font-semibold text-[#333333]">{stageLabel}</span>
                  <span className="text-[11px] text-[#999999]">{gateProgress} gates met</span>
                </div>

                {/* Gate progress bar */}
                <div className="h-2 bg-[#E5E5E5] rounded-full overflow-hidden mb-2.5">
                  <div
                    className="h-full bg-[#3FAF7A] rounded-full transition-all duration-700"
                    style={{ width: `${(pulse.stage_progress ?? 0) * 100}%` }}
                  />
                </div>

                {/* Mini forecast */}
                {forecast && (
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                    {[
                      { label: 'Coverage', value: forecast.coverage_index },
                      { label: 'Confidence', value: forecast.confidence_index },
                      { label: 'Prototype ready', value: forecast.prototype_readiness },
                      { label: 'Spec complete', value: forecast.spec_completeness },
                    ].map((m) => (
                      <div key={m.label} className="flex items-center justify-between">
                        <span className="text-[10px] text-[#999999]">{m.label}</span>
                        <span className="text-[10px] font-medium text-[#333333]">
                          {Math.round(m.value * 100)}%
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Gates checklist (compact) */}
            {pulse.gates && pulse.gates.length > 0 && (
              <div className="mb-5">
                <h4 className="text-[10px] font-semibold text-[#999999] uppercase tracking-wide mb-2">
                  Stage Gates
                </h4>
                <div className="space-y-1">
                  {pulse.gates.map((gate, i) => {
                    const met = gate.startsWith('[x]')
                    return (
                      <div key={i} className="flex items-center gap-2">
                        {met ? (
                          <CheckCircle2 className="w-3.5 h-3.5 text-[#3FAF7A] flex-shrink-0" />
                        ) : (
                          <div className="w-3.5 h-3.5 rounded-full border-2 border-[#E5E5E5] flex-shrink-0" />
                        )}
                        <span className={`text-[11px] ${met ? 'text-[#999999]' : 'text-[#333333] font-medium'}`}>
                          {gate.replace(/^\[.\]\s*/, '')}
                        </span>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Entity health bars */}
            <div className="mb-5">
              <h4 className="text-[10px] font-semibold text-[#999999] uppercase tracking-wide mb-2">
                Entity Health
              </h4>
              <div>
                {healthEntries.map(([entityType, health]) => (
                  <EntityRow key={entityType} entityType={entityType} health={health} />
                ))}
              </div>
            </div>

            {/* Risk + Actions split */}
            <div className="grid grid-cols-5 gap-4 mb-5">
              {/* Risk card */}
              <div className="col-span-2 bg-[#FAFAFA] rounded-xl p-3">
                <div className="flex items-center gap-1.5 mb-2">
                  <Shield className="w-3.5 h-3.5 text-[#999999]" />
                  <span className="text-[10px] font-semibold text-[#999999] uppercase tracking-wide">Risk</span>
                </div>
                {risk && (
                  <div className="space-y-1.5">
                    <div className="flex items-baseline gap-1.5">
                      <span className="text-[20px] font-bold text-[#333333]">
                        {risk.risk_score.toFixed(0)}
                      </span>
                      <span className="text-[10px] text-[#999999]">/ 100</span>
                    </div>
                    <div className="space-y-0.5 text-[10px] text-[#666666]">
                      {risk.stale_clusters > 0 && (
                        <div>{risk.stale_clusters} stale cluster{risk.stale_clusters > 1 ? 's' : ''}</div>
                      )}
                      {risk.critical_questions > 0 && (
                        <div>{risk.critical_questions} critical question{risk.critical_questions > 1 ? 's' : ''}</div>
                      )}
                      {risk.single_source_types > 0 && (
                        <div>{risk.single_source_types} single-source type{risk.single_source_types > 1 ? 's' : ''}</div>
                      )}
                      {risk.risk_score === 0 && (
                        <div className="text-[#3FAF7A]">No risks detected</div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Top actions */}
              <div className="col-span-3">
                <div className="flex items-center gap-1.5 mb-2">
                  <Zap className="w-3.5 h-3.5 text-[#3FAF7A]" />
                  <span className="text-[10px] font-semibold text-[#999999] uppercase tracking-wide">
                    What to Focus On
                  </span>
                </div>
                <div className="space-y-1.5">
                  {(pulse.actions || []).slice(0, 3).map((action, i) => (
                    <div key={i} className="flex items-start gap-2 bg-[#FAFAFA] rounded-lg px-3 py-2">
                      <span className="text-[11px] font-bold text-[#3FAF7A] mt-px">{i + 1}.</span>
                      <div className="flex-1 min-w-0">
                        <p className="text-[11px] text-[#333333] leading-snug">{action.sentence}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <div className="flex-1 h-1 bg-[#E5E5E5] rounded-full overflow-hidden">
                            <div className="h-full bg-[#3FAF7A] rounded-full" style={{ width: `${action.impact_score}%` }} />
                          </div>
                          {action.unblocks_gate && (
                            <span className="text-[8px] font-semibold text-[#9A3412] bg-[#F97316]/12 px-1 py-0.5 rounded whitespace-nowrap">
                              GATE BLOCKER
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                  {(!pulse.actions || pulse.actions.length === 0) && (
                    <p className="text-[11px] text-[#3FAF7A]">No urgent actions needed</p>
                  )}
                </div>
              </div>
            </div>

            {/* Dismiss */}
            <button
              onClick={onDismiss}
              className="w-full flex items-center justify-center gap-2 bg-[#3FAF7A] text-white font-medium py-3 rounded-xl hover:bg-[#25785A] transition-colors"
            >
              Got It <ArrowRight className="w-4 h-4" />
            </button>
          </>
        )}
      </div>
    </div>
  )
}
