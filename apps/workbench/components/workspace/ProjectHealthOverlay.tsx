'use client'

import { useState, useEffect } from 'react'
import { Activity, X, AlertTriangle, RefreshCw, ArrowRight } from 'lucide-react'
import { getProjectPulse, getBRDHealth } from '@/lib/api'
import type { ProjectPulse } from '@/types/api'
import type { BRDHealthData } from '@/types/workspace'

interface ProjectHealthOverlayProps {
  projectId: string
  onDismiss: () => void
}

function ScoreCircle({ score }: { score: number }) {
  const radius = 42
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (score / 100) * circumference
  const color = score >= 60 ? '#3FAF7A' : '#F59E0B'

  return (
    <div className="relative w-24 h-24">
      <svg className="w-24 h-24 -rotate-90" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r={radius} fill="none" stroke="#E5E5E5" strokeWidth="6" />
        <circle
          cx="50"
          cy="50"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-1000 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-xl font-bold text-[#333333]">{score}</span>
        <span className="text-[10px] text-[#999999]">/100</span>
      </div>
    </div>
  )
}

export function ProjectHealthOverlay({ projectId, onDismiss }: ProjectHealthOverlayProps) {
  const [pulse, setPulse] = useState<ProjectPulse | null>(null)
  const [health, setHealth] = useState<BRDHealthData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      getProjectPulse(projectId).catch(() => null),
      getBRDHealth(projectId).catch(() => null),
    ]).then(([pulseData, healthData]) => {
      setPulse(pulseData)
      setHealth(healthData)
      setLoading(false)
    })
  }, [projectId])

  const totalStale = health?.stale_entities?.total_stale ?? 0
  const scopeAlerts = health?.scope_alerts ?? []
  const hasHealthIssues = totalStale > 0 || scopeAlerts.length > 0

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center">
      <div className="absolute inset-0 bg-white/60 backdrop-blur-sm" onClick={onDismiss} />

      <div className="relative w-full max-w-lg max-h-[85vh] overflow-y-auto bg-white rounded-2xl shadow-2xl border border-[#E5E5E5] p-8">
        <button
          onClick={onDismiss}
          className="absolute top-4 right-4 text-[#999999] hover:text-[#333333]"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-2 mb-6">
          <Activity className="w-5 h-5 text-[#3FAF7A]" />
          <h2 className="text-lg font-semibold text-[#333333]">Project Health</h2>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#3FAF7A]" />
          </div>
        ) : (
          <>
            {/* Score */}
            {pulse && (
              <div className="flex justify-center mb-5">
                <ScoreCircle score={pulse.score} />
              </div>
            )}

            {/* Summary */}
            {pulse?.summary && (
              <p className="text-sm text-[#666666] text-center mb-6">{pulse.summary}</p>
            )}

            {/* Health Issues */}
            {hasHealthIssues && (
              <div className="mb-5">
                <h4 className="text-xs font-semibold text-[#999999] uppercase tracking-wide mb-3">
                  Health Issues
                </h4>

                {/* Stale entities */}
                {totalStale > 0 && (
                  <div className="flex items-start gap-3 bg-[#FFF8F0] rounded-xl px-4 py-3 mb-2">
                    <RefreshCw className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-[#333333]">
                        {totalStale} stale {totalStale === 1 ? 'entity' : 'entities'}
                      </p>
                      <p className="text-xs text-[#999999] mt-0.5">
                        Some entities may need refreshing based on recent changes.
                      </p>
                    </div>
                  </div>
                )}

                {/* Scope alerts */}
                {scopeAlerts.map((alert, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-3 bg-[#FFF8F0] rounded-xl px-4 py-3 mb-2"
                  >
                    <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-[#333333]">{alert.message}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Next actions */}
            {pulse && pulse.next_actions.length > 0 && (
              <div className="mb-5">
                <h4 className="text-xs font-semibold text-[#999999] uppercase tracking-wide mb-3">
                  Recommended Actions
                </h4>
                <div className="space-y-2">
                  {pulse.next_actions.slice(0, 3).map((action, i) => (
                    <div
                      key={i}
                      className="flex items-start gap-3 bg-[#F4F4F4] rounded-xl px-4 py-3"
                    >
                      <span className="text-xs font-bold text-[#3FAF7A] mt-0.5">{i + 1}.</span>
                      <div>
                        <p className="text-sm font-medium text-[#333333]">{action.title}</p>
                        <p className="text-xs text-[#999999] mt-0.5">{action.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Dismiss button */}
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
