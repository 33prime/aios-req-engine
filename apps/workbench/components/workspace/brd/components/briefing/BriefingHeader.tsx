'use client'

import { Sparkles, Loader2 } from 'lucide-react'
import { PHASE_LABELS } from '@/lib/action-constants'

interface BriefingHeaderProps {
  phase: string | null
  progress: number
  narrativeCached?: boolean
  onRefresh?: () => void
  loading?: boolean
}

export function BriefingHeader({
  phase,
  progress,
  narrativeCached,
  onRefresh,
  loading,
}: BriefingHeaderProps) {
  const phaseLabel = phase ? PHASE_LABELS[phase] || phase : '...'
  const progressPct = Math.round(progress * 100)
  const radius = 14
  const circumference = 2 * Math.PI * radius
  const strokeDashoffset = circumference - (progress * circumference)

  return (
    <div className="px-4 py-3 border-b border-border bg-[#0A1E2F] flex-shrink-0">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Circular progress arc */}
          <div className="relative w-9 h-9 flex-shrink-0">
            <svg className="w-9 h-9 -rotate-90" viewBox="0 0 36 36">
              <circle
                cx="18" cy="18" r={radius}
                fill="none"
                stroke="rgba(255,255,255,0.1)"
                strokeWidth="2.5"
              />
              <circle
                cx="18" cy="18" r={radius}
                fill="none"
                stroke="#3FAF7A"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                className="transition-all duration-700"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-[9px] font-bold text-white">{progressPct}%</span>
            </div>
          </div>

          <div>
            <div className="flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5 text-brand-primary" />
              <h2 className="text-[13px] font-semibold text-white">Briefing</h2>
            </div>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-[10px] text-white/50">{phaseLabel}</span>
              {narrativeCached && (
                <span className="text-[9px] text-white/30">cached</span>
              )}
            </div>
          </div>
        </div>

        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={loading}
            className="p-1 rounded-md hover:bg-white/10 transition-colors disabled:opacity-40"
            title="Refresh briefing"
          >
            <Loader2
              className={`w-3.5 h-3.5 text-white/60 ${loading ? 'animate-spin' : ''}`}
            />
          </button>
        )}
      </div>
    </div>
  )
}
