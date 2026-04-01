/**
 * ReadinessCell - Compact readiness display for table/card views
 *
 * Shows:
 * - Colored dot + progress bar showing readiness progress
 * - Percentage displayed as XX%
 * - Em-dash when score is null (readiness not yet computed)
 * - Hover tooltip with dimension breakdown (value_path, problem, solution, engagement)
 *
 * Uses dimensional weighted score (actual work done) rather than
 * gate-capped score, so projects with real progress show > 0%.
 */

import React, { useState } from 'react'
import type { ProjectDetailWithDashboard } from '@/types/api'

interface ReadinessCellProps {
  project: ProjectDetailWithDashboard
}

const DIMENSION_LABELS: Record<string, string> = {
  value_path: 'Value Path',
  problem: 'Problem',
  solution: 'Solution',
  engagement: 'Engagement',
}

export function computeDimensionalScore(
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

export function getReadinessScore(project: ProjectDetailWithDashboard): number | null {
  const cached = project.cached_readiness_data
  return computeDimensionalScore(cached) ?? cached?.gate_score ?? project.readiness_score ?? null
}

export function ReadinessCell({ project }: ReadinessCellProps) {
  const [showTooltip, setShowTooltip] = useState(false)
  const cached = project.cached_readiness_data

  const rawScore = getReadinessScore(project)
  const hasScore = rawScore !== null
  const score = rawScore ?? 0
  const roundedScore = Math.round(score)

  // Build dimension breakdown for tooltip
  const dimensions = cached?.dimensions
    ? Object.entries(cached.dimensions)
        .filter(([, d]) => d && typeof d.score === 'number')
        .map(([key, d]) => ({
          label: DIMENSION_LABELS[key] || key,
          score: Math.round(d.score),
          weight: Math.round((d.weight ?? 0) * 100),
        }))
        .sort((a, b) => b.weight - a.weight)
    : []

  // Color based on score
  const getColor = () => {
    if (roundedScore >= 80) return {
      bar: 'bg-brand-primary',
      text: 'text-brand-primary',
      dot: 'bg-brand-primary',
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
    <div
      className="relative flex items-center gap-2"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
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

      {/* Dimension breakdown tooltip */}
      {showTooltip && dimensions.length > 0 && (
        <div className="absolute left-0 top-full mt-2 z-50 bg-white border border-border rounded-lg shadow-lg p-3 min-w-[200px]">
          <p className="text-[11px] font-semibold text-text-primary mb-2">Readiness Breakdown</p>
          <div className="space-y-1.5">
            {dimensions.map((dim) => (
              <div key={dim.label} className="flex items-center gap-2">
                <span className="text-[10px] text-text-secondary w-16 flex-shrink-0">{dim.label}</span>
                <div className="flex-1 h-1 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-brand-primary rounded-full"
                    style={{ width: `${Math.min(dim.score, 100)}%` }}
                  />
                </div>
                <span className="text-[10px] font-medium text-text-body tabular-nums w-7 text-right">
                  {dim.score}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
