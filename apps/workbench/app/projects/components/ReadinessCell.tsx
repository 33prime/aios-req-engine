/**
 * ReadinessCell - Compact readiness display for table/card views
 *
 * Shows:
 * - Colored dot + progress bar showing readiness progress
 * - Percentage displayed as XX%
 * - Em-dash when score is null (readiness not yet computed)
 *
 * Uses dimensional weighted score (actual work done) rather than
 * gate-capped score, so projects with real progress show > 0%.
 */

import React from 'react'
import type { ProjectDetailWithDashboard } from '@/types/api'

interface ReadinessCellProps {
  project: ProjectDetailWithDashboard
}

function computeDimensionalScore(
  cached: ProjectDetailWithDashboard['cached_readiness_data']
): number | null {
  if (!cached?.dimensions) return null
  const dims = cached.dimensions
  let total = 0
  for (const key of Object.keys(dims)) {
    const d = dims[key]
    if (d && typeof d.score === 'number' && typeof d.weight === 'number') {
      total += d.score * d.weight
    }
  }
  return total
}

export function ReadinessCell({ project }: ReadinessCellProps) {
  const cached = project.cached_readiness_data

  // Prefer dimensional score (actual progress), then gate_score, then readiness_score
  const dimensionalScore = computeDimensionalScore(cached)
  const rawScore = dimensionalScore ?? cached?.gate_score ?? project.readiness_score ?? null

  const hasScore = rawScore !== null
  const score = rawScore ?? 0
  const roundedScore = Math.round(score)

  // Color based on score
  const getColor = () => {
    if (roundedScore >= 80) return {
      bar: 'bg-[#3FAF7A]',
      text: 'text-[#3FAF7A]',
      dot: 'bg-[#3FAF7A]',
    }
    if (roundedScore >= 50) return {
      bar: 'bg-[#4CC08C]',
      text: 'text-[#25785A]',
      dot: 'bg-[#4CC08C]',
    }
    if (roundedScore >= 20) return {
      bar: 'bg-emerald-300',
      text: 'text-emerald-600',
      dot: 'bg-emerald-300',
    }
    return {
      bar: 'bg-gray-300',
      text: 'text-[#999]',
      dot: 'bg-gray-300',
    }
  }

  const colors = getColor()

  if (!hasScore) {
    return (
      <span className="text-sm text-[#999]">&mdash;</span>
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
