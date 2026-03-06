'use client'

import { Calendar, TrendingUp } from 'lucide-react'
import { ProgressRing } from '@/components/ui/ProgressRing'
import type { PortalDashboard, ProjectContextData } from '@/types/portal'

interface ConsultantBannerProps {
  dashboard: PortalDashboard
  projectContext: ProjectContextData | null
}

const PHASE_STEPS = ['Discovery', 'Building', 'Review'] as const

function getPhaseIndex(phase: string): number {
  if (phase === 'building' || phase === 'prototype') return 1
  if (phase === 'review' || phase === 'complete') return 2
  return 0
}

function getLowestStation(ctx: ProjectContextData | null): string | null {
  if (!ctx?.completion_scores) return null
  const scores = ctx.completion_scores
  const stations: [string, number][] = [
    ['competitors', scores.competitors],
    ['design', scores.design],
    ['tribal knowledge', scores.tribal],
    ['problem definition', scores.problem],
    ['success criteria', scores.success],
    ['key users', scores.users],
  ]
  const lowest = stations.reduce((min, s) => (s[1] < min[1] ? s : min))
  if (lowest[1] >= 80) return null
  return lowest[0]
}

export function ConsultantBanner({ dashboard, projectContext }: ConsultantBannerProps) {
  const phaseIdx = getPhaseIndex(dashboard.phase)
  const overall = projectContext?.overall_completion ?? 0
  const consultantName = dashboard.call_info?.consultant_name
  const lowestStation = getLowestStation(projectContext)
  const meeting = dashboard.upcoming_meeting

  return (
    <div className="bg-[#0A1E2F] rounded-xl p-5 text-white">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          {consultantName && (
            <p className="text-xs text-white/50 mb-1">Working with {consultantName}</p>
          )}
          <h1 className="text-lg font-semibold truncate">{dashboard.project_name}</h1>

          {/* Phase progress */}
          <div className="flex items-center gap-1 mt-3">
            {PHASE_STEPS.map((step, i) => (
              <div key={step} className="flex items-center gap-1">
                <div
                  className={`h-1.5 rounded-full transition-all ${
                    i <= phaseIdx ? 'bg-brand-primary w-12' : 'bg-white/20 w-8'
                  }`}
                />
                <span className={`text-[10px] ${i <= phaseIdx ? 'text-white/80' : 'text-white/30'}`}>
                  {step}
                </span>
              </div>
            ))}
          </div>

          {/* Nudge */}
          {lowestStation && (
            <p className="text-xs text-white/50 mt-3 flex items-center gap-1">
              <TrendingUp className="w-3 h-3" />
              Tip: Sharing more about <span className="text-brand-primary">{lowestStation}</span> will help the most right now
            </p>
          )}
        </div>

        <div className="flex items-center gap-4 flex-shrink-0">
          {/* Meeting badge */}
          {meeting && (
            <div className="flex items-center gap-2 bg-white/10 rounded-lg px-3 py-2">
              <Calendar className="w-4 h-4 text-white/60" />
              <div>
                <p className="text-xs text-white/80 font-medium">{meeting.title || 'Upcoming Call'}</p>
                <p className="text-[10px] text-white/50">
                  {new Date(meeting.scheduled_at).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    hour: 'numeric',
                    minute: '2-digit',
                  })}
                </p>
              </div>
            </div>
          )}

          {/* Overall readiness */}
          <ProgressRing value={overall} size={48} strokeWidth={4} showLabel className="text-white [&_circle:first-child]:text-white/20" />
        </div>
      </div>
    </div>
  )
}
