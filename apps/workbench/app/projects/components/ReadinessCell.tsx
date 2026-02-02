/**
 * ReadinessCell - Compact readiness display for table view
 *
 * Shows:
 * - Colored dot + progress bar showing gate score
 * - Percentage displayed as XX%
 * - Em-dash when score is null (readiness not yet computed)
 */

import React from 'react'
import type { ProjectDetailWithDashboard } from '@/types/api'

interface ReadinessCellProps {
  project: ProjectDetailWithDashboard
}

export function ReadinessCell({ project }: ReadinessCellProps) {
  // Use gate_score from cached readiness data, fallback to readiness_score
  const rawScore = project.cached_readiness_data?.gate_score ?? project.readiness_score ?? null
  const hasScore = rawScore !== null
  const score = rawScore ?? 0
  const roundedScore = Math.round(score)

  // Color based on score
  const getColor = () => {
    if (roundedScore >= 80) return {
      bar: 'bg-[#009b87]',
      text: 'text-[#009b87]',
      dot: 'bg-[#009b87]',
    }
    if (roundedScore >= 50) return {
      bar: 'bg-emerald-400',
      text: 'text-emerald-600',
      dot: 'bg-emerald-400',
    }
    return {
      bar: 'bg-emerald-200',
      text: 'text-emerald-500',
      dot: 'bg-emerald-200',
    }
  }

  const colors = getColor()

  if (!hasScore) {
    return (
      <span className="text-sm text-ui-supportText">&mdash;</span>
    )
  }

  return (
    <div className="flex items-center gap-2">
      {/* Colored dot */}
      <span className={`w-2 h-2 rounded-full flex-shrink-0 ${colors.dot}`} />

      {/* Progress bar */}
      <div className="w-20 h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${colors.bar}`}
          style={{ width: `${Math.min(score, 100)}%` }}
        />
      </div>

      {/* Percentage display */}
      <span className={`text-sm font-semibold tabular-nums ${colors.text}`}>
        {roundedScore}%
      </span>
    </div>
  )
}
