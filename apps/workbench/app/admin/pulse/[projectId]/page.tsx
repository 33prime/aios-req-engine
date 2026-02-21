'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, AlertTriangle, CheckCircle2, Clock, Zap } from 'lucide-react'
import { getAdminProjectPulseDetail } from '@/lib/api'
import type { PulseSnapshot } from '@/types/api'

const DIRECTIVE_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  stable: { bg: 'bg-[#3FAF7A]/15', text: 'text-[#25785A]', label: 'Stable' },
  grow: { bg: 'bg-[#3B82F6]/15', text: 'text-[#1D4ED8]', label: 'Grow' },
  enrich: { bg: 'bg-[#F59E0B]/15', text: 'text-[#92400E]', label: 'Enrich' },
  confirm: { bg: 'bg-[#F97316]/15', text: 'text-[#9A3412]', label: 'Confirm' },
  merge_only: { bg: 'bg-[#EF4444]/15', text: 'text-[#991B1B]', label: 'Merge Only' },
}

const COVERAGE_COLORS: Record<string, string> = {
  missing: 'text-[#991B1B]',
  thin: 'text-[#9A3412]',
  growing: 'text-[#92400E]',
  adequate: 'text-[#25785A]',
  saturated: 'text-[#1D4ED8]',
}

const STAGE_COLORS: Record<string, string> = {
  discovery: 'bg-[#3FAF7A]/15 text-[#25785A]',
  validation: 'bg-[#3FAF7A]/15 text-[#25785A]',
  prototype: 'bg-[#3FAF7A]/20 text-[#25785A]',
  specification: 'bg-[#0A1E2F]/10 text-[#0A1E2F]',
  handoff: 'bg-[#0A1E2F]/15 text-[#0A1E2F]',
}

const TRIGGER_LABELS: Record<string, string> = {
  api: 'API request',
  signal_processed: 'Signal processed',
  confirmation: 'Batch confirm',
  manual: 'Manual',
}

export default function AdminPulseDetailPage() {
  const params = useParams()
  const projectId = params.projectId as string

  const [projectName, setProjectName] = useState('')
  const [latest, setLatest] = useState<PulseSnapshot | null>(null)
  const [history, setHistory] = useState<PulseSnapshot[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!projectId) return
    getAdminProjectPulseDetail(projectId)
      .then((data) => {
        setProjectName(data.project_name)
        setLatest(data.latest)
        setHistory(data.history || [])
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [projectId])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-5 h-5 border-2 border-[#3FAF7A] border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!latest) {
    return (
      <div className="space-y-4">
        <Link href="/admin/pulse" className="flex items-center gap-1.5 text-[13px] text-[#3FAF7A] hover:text-[#25785A]">
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Pulse
        </Link>
        <p className="text-[13px] text-[#999999]">No pulse data for this project yet.</p>
      </div>
    )
  }

  const healthEntries = Object.entries(latest.health || {}).sort(
    ([, a], [, b]) => (b.health_score ?? 0) - (a.health_score ?? 0)
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link href="/admin/pulse" className="flex items-center gap-1.5 text-[13px] text-[#3FAF7A] hover:text-[#25785A] mb-3">
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Pulse
        </Link>
        <div className="flex items-center gap-3">
          <h1 className="text-[22px] font-bold text-[#333333]">{projectName || projectId.slice(0, 8)}</h1>
          <span className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-medium ${STAGE_COLORS[latest.stage] || 'bg-[#E5E5E5] text-[#666666]'}`}>
            {latest.stage}
          </span>
        </div>

        {/* Progress bar */}
        <div className="mt-3 flex items-center gap-3">
          <div className="flex-1 h-2 bg-[#E5E5E5] rounded-full overflow-hidden">
            <div
              className="h-full bg-[#3FAF7A] rounded-full transition-all"
              style={{ width: `${(latest.stage_progress ?? 0) * 100}%` }}
            />
          </div>
          <span className="text-[12px] text-[#999999] font-mono">
            {latest.gates_met ?? 0}/{latest.gates_total ?? 0} gates
          </span>
        </div>

        {/* Gates checklist */}
        {latest.gates && latest.gates.length > 0 && (
          <div className="mt-3 space-y-1">
            {latest.gates.map((gate, i) => {
              const met = gate.startsWith('[x]')
              return (
                <div key={i} className="flex items-center gap-2 text-[12px]">
                  {met ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-[#3FAF7A] flex-shrink-0" />
                  ) : (
                    <div className="w-3.5 h-3.5 rounded-full border-2 border-[#E5E5E5] flex-shrink-0" />
                  )}
                  <span className={met ? 'text-[#666666]' : 'text-[#333333] font-medium'}>
                    {gate.replace(/^\[.\]\s*/, '')}
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Entity health cards */}
      <div>
        <h2 className="text-[15px] font-semibold text-[#333333] mb-3">Entity Health</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {healthEntries.map(([entityType, health]) => {
            const dir = DIRECTIVE_COLORS[health.directive] || DIRECTIVE_COLORS.stable
            const covColor = COVERAGE_COLORS[health.coverage] || 'text-[#666666]'
            return (
              <div key={entityType} className="bg-white rounded-xl border border-[#E5E5E5] p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[13px] font-medium text-[#333333]">
                    {entityType.replace('_', ' ')}
                  </span>
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${dir.bg} ${dir.text}`}>
                    {dir.label}
                  </span>
                </div>

                <div className="flex items-baseline gap-1 mb-2">
                  <span className="text-[20px] font-bold text-[#333333]">{health.count}</span>
                  <span className="text-[12px] text-[#999999]">/ {health.target}</span>
                </div>

                {/* Health score bar */}
                <div className="h-1.5 bg-[#E5E5E5] rounded-full overflow-hidden mb-2">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${Math.min(100, health.health_score ?? 0)}%`,
                      backgroundColor: (health.health_score ?? 0) >= 70 ? '#3FAF7A' : (health.health_score ?? 0) >= 40 ? '#F59E0B' : '#EF4444',
                    }}
                  />
                </div>

                <div className="flex items-center justify-between text-[11px]">
                  <span className={covColor}>{health.coverage}</span>
                  <span className="text-[#999999]">
                    {health.confirmed} conf / {health.stale} stale
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Actions + Risk + Forecast row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Actions */}
        <div className="bg-white rounded-xl border border-[#E5E5E5] p-4">
          <h3 className="text-[13px] font-semibold text-[#333333] mb-3 flex items-center gap-1.5">
            <Zap className="w-3.5 h-3.5 text-[#3FAF7A]" /> Actions
          </h3>
          <div className="space-y-2.5">
            {(latest.actions || []).map((action, i) => (
              <div key={i} className="flex items-start gap-2">
                <div className="flex-1">
                  <p className="text-[12px] text-[#333333]">{action.sentence}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="flex-1 h-1 bg-[#E5E5E5] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-[#3FAF7A] rounded-full"
                        style={{ width: `${action.impact_score}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-[#999999] font-mono">{action.impact_score.toFixed(0)}</span>
                    {action.unblocks_gate && (
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-medium bg-[#F97316]/15 text-[#9A3412]">
                        gate blocker
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {(!latest.actions || latest.actions.length === 0) && (
              <p className="text-[12px] text-[#999999]">No actions needed</p>
            )}
          </div>
        </div>

        {/* Risk */}
        <div className="bg-white rounded-xl border border-[#E5E5E5] p-4">
          <h3 className="text-[13px] font-semibold text-[#333333] mb-3 flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5 text-[#F59E0B]" /> Risk
          </h3>
          {latest.risks && (
            <div className="space-y-3">
              <div className="flex items-baseline gap-2">
                <span className="text-[24px] font-bold text-[#333333]">
                  {latest.risks.risk_score.toFixed(0)}
                </span>
                <span className="text-[12px] text-[#999999]">/ 100</span>
              </div>
              <div className="space-y-1.5 text-[12px]">
                <div className="flex justify-between">
                  <span className="text-[#666666]">Stale clusters</span>
                  <span className="font-medium text-[#333333]">{latest.risks.stale_clusters}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#666666]">Critical questions</span>
                  <span className="font-medium text-[#333333]">{latest.risks.critical_questions}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#666666]">Single-source types</span>
                  <span className="font-medium text-[#333333]">{latest.risks.single_source_types}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#666666]">Contradictions</span>
                  <span className="font-medium text-[#333333]">{latest.risks.contradiction_count}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Forecast */}
        <div className="bg-white rounded-xl border border-[#E5E5E5] p-4">
          <h3 className="text-[13px] font-semibold text-[#333333] mb-3">Forecast</h3>
          {latest.forecast && (
            <div className="space-y-3">
              {[
                { label: 'Prototype Readiness', value: latest.forecast.prototype_readiness },
                { label: 'Spec Completeness', value: latest.forecast.spec_completeness },
                { label: 'Confidence Index', value: latest.forecast.confidence_index },
                { label: 'Coverage Index', value: latest.forecast.coverage_index },
              ].map((metric) => (
                <div key={metric.label}>
                  <div className="flex justify-between text-[12px] mb-1">
                    <span className="text-[#666666]">{metric.label}</span>
                    <span className="font-medium text-[#333333]">{(metric.value * 100).toFixed(0)}%</span>
                  </div>
                  <div className="h-1.5 bg-[#E5E5E5] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#3FAF7A] rounded-full transition-all"
                      style={{ width: `${metric.value * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Snapshot timeline */}
      <div className="bg-white rounded-xl border border-[#E5E5E5] p-4">
        <h3 className="text-[13px] font-semibold text-[#333333] mb-3 flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5 text-[#999999]" /> Snapshot Timeline
        </h3>

        {history.length === 0 ? (
          <p className="text-[12px] text-[#999999]">No snapshots recorded yet.</p>
        ) : (
          <div className="space-y-0">
            {history.slice(0, 10).map((snap, i) => {
              const prevSnap = history[i + 1]
              const stageChanged = prevSnap && prevSnap.stage !== snap.stage
              return (
                <div key={snap.id || i} className="flex items-start gap-3 py-2 border-b border-[#F4F4F4] last:border-0">
                  {/* Timeline dot */}
                  <div className="flex flex-col items-center pt-1">
                    <div className={`w-2.5 h-2.5 rounded-full ${stageChanged ? 'bg-[#3FAF7A]' : 'bg-[#E5E5E5]'}`} />
                    {i < Math.min(history.length - 1, 9) && (
                      <div className="w-px h-full bg-[#E5E5E5] min-h-[16px]" />
                    )}
                  </div>

                  <div className="flex-1 flex items-center gap-3 text-[12px]">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${STAGE_COLORS[snap.stage] || 'bg-[#E5E5E5] text-[#666666]'}`}>
                      {snap.stage}
                    </span>
                    <span className="text-[#666666]">
                      {TRIGGER_LABELS[snap.trigger] || snap.trigger}
                    </span>
                    {stageChanged && (
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-medium bg-[#3FAF7A]/15 text-[#25785A]">
                        stage change
                      </span>
                    )}
                    <span className="text-[#999999] ml-auto">
                      {snap.created_at ? new Date(snap.created_at).toLocaleString() : '—'}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
