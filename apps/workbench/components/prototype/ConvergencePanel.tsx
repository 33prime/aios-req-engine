'use client'

import { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, Minus, CheckCircle2, AlertCircle, HelpCircle } from 'lucide-react'
import type { ConvergenceSnapshot, FeatureConvergence } from '@/types/prototype'
import { getPrototypeConvergence } from '@/lib/api'

const TREND_CONFIG = {
  improving: { icon: TrendingUp, label: 'Improving', color: 'text-[#3FAF7A]' },
  declining: { icon: TrendingDown, label: 'Declining', color: 'text-[#E5634E]' },
  stable: { icon: Minus, label: 'Stable', color: 'text-[#666666]' },
  insufficient_data: { icon: HelpCircle, label: 'Not enough data', color: 'text-[#999999]' },
}

const VERDICT_COLORS: Record<string, string> = {
  aligned: 'bg-[#3FAF7A]/10 text-[#25785A]',
  needs_adjustment: 'bg-[#F5A623]/10 text-[#B47B1A]',
  off_track: 'bg-[#E5634E]/10 text-[#C43D2A]',
}

interface ConvergencePanelProps {
  prototypeId: string
}

export function ConvergencePanel({ prototypeId }: ConvergencePanelProps) {
  const [data, setData] = useState<ConvergenceSnapshot | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getPrototypeConvergence(prototypeId)
      .then(result => {
        if (!cancelled) setData(result)
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [prototypeId])

  if (loading) {
    return (
      <div className="p-4 text-sm text-[#999999]">Loading convergence data...</div>
    )
  }

  if (!data || data.total_features === 0) {
    return (
      <div className="p-4 text-sm text-[#999999]">No feature overlays to track yet.</div>
    )
  }

  const trendConfig = TREND_CONFIG[data.trend]
  const TrendIcon = trendConfig.icon

  return (
    <div className="space-y-4">
      {/* Summary row */}
      <div className="grid grid-cols-4 gap-3">
        <MetricCard
          label="Alignment"
          value={`${Math.round(data.alignment_rate * 100)}%`}
          sub={`${data.features_with_verdicts} of ${data.total_features} reviewed`}
        />
        <MetricCard
          label="Question Coverage"
          value={`${Math.round(data.question_coverage * 100)}%`}
          sub={`${data.questions_answered}/${data.questions_total} answered`}
        />
        <MetricCard
          label="Feedback"
          value={`${data.feedback_total}`}
          sub={`${data.feedback_concerns} concerns`}
        />
        <div className="border border-[#E5E5E5] rounded-lg px-3 py-2">
          <p className="text-[10px] text-[#999999] font-medium uppercase tracking-wide mb-1">Trend</p>
          <div className={`flex items-center gap-1.5 ${trendConfig.color}`}>
            <TrendIcon className="w-4 h-4" />
            <span className="text-sm font-semibold">{trendConfig.label}</span>
          </div>
          <p className="text-[10px] text-[#BBBBBB] mt-0.5">{data.sessions_completed} sessions</p>
        </div>
      </div>

      {/* Per-feature breakdown */}
      <div>
        <h4 className="text-xs font-semibold text-[#333333] uppercase tracking-wide mb-2">
          Per-Feature Convergence
        </h4>
        <div className="space-y-1.5">
          {data.per_feature.map((f: FeatureConvergence) => (
            <div
              key={f.feature_id || f.feature_name}
              className="flex items-center gap-2 px-3 py-2 rounded-lg border border-[#E5E5E5] text-xs"
            >
              {/* Alignment indicator */}
              <div className="shrink-0">
                {f.aligned ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#3FAF7A]" />
                ) : f.consultant_verdict && f.client_verdict ? (
                  <AlertCircle className="w-3.5 h-3.5 text-[#F5A623]" />
                ) : (
                  <HelpCircle className="w-3.5 h-3.5 text-[#CCCCCC]" />
                )}
              </div>

              {/* Feature name */}
              <span className="flex-1 min-w-0 truncate text-[#333333] font-medium">
                {f.feature_name}
              </span>

              {/* Verdicts */}
              <div className="flex gap-1.5 shrink-0">
                {f.consultant_verdict ? (
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${VERDICT_COLORS[f.consultant_verdict] || 'bg-gray-100 text-[#666666]'}`}>
                    C: {f.consultant_verdict.replace('_', ' ')}
                  </span>
                ) : (
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-gray-50 text-[#BBBBBB] font-medium">
                    C: pending
                  </span>
                )}
                {f.client_verdict ? (
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${VERDICT_COLORS[f.client_verdict] || 'bg-gray-100 text-[#666666]'}`}>
                    Cl: {f.client_verdict.replace('_', ' ')}
                  </span>
                ) : (
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-gray-50 text-[#BBBBBB] font-medium">
                    Cl: pending
                  </span>
                )}
              </div>

              {/* Questions */}
              {f.questions_total > 0 && (
                <span className="text-[10px] text-[#999999] shrink-0">
                  Q: {f.questions_answered}/{f.questions_total}
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function MetricCard({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="border border-[#E5E5E5] rounded-lg px-3 py-2">
      <p className="text-[10px] text-[#999999] font-medium uppercase tracking-wide mb-1">{label}</p>
      <p className="text-lg font-bold text-[#333333] leading-tight">{value}</p>
      <p className="text-[10px] text-[#BBBBBB] mt-0.5">{sub}</p>
    </div>
  )
}
