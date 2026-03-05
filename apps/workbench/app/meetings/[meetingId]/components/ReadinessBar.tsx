'use client'

import type { DealReadinessSnapshot, AmbiguitySnapshot } from '@/types/call-intelligence'

export function ReadinessBar({
  readiness,
  ambiguity,
}: {
  readiness?: DealReadinessSnapshot | null
  ambiguity?: AmbiguitySnapshot | null
}) {
  if (!readiness && !ambiguity) return null

  const readinessScore = readiness?.score ?? 0
  const ambiguityScore = ambiguity?.score ?? 0
  const ambiguityPct = Math.round(ambiguityScore * 100)

  const readinessColor =
    readinessScore < 40 ? 'bg-red-500' : readinessScore < 70 ? 'bg-amber-500' : 'bg-green-500'
  const ambiguityColor =
    ambiguityPct > 60 ? 'bg-red-500' : ambiguityPct > 30 ? 'bg-amber-500' : 'bg-green-500'

  return (
    <div className="mt-7 flex items-center gap-6 px-3 py-3 bg-white rounded-lg border border-border">
      {/* Readiness gauge */}
      {readiness && (
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] font-semibold text-text-muted uppercase tracking-wide">Readiness</span>
            <span className="text-[13px] font-bold text-text-body">{Math.round(readinessScore)}%</span>
          </div>
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${readinessColor}`}
              style={{ width: `${readinessScore}%` }}
            />
          </div>
        </div>
      )}

      {readiness && ambiguity && (
        <div className="w-px h-8 bg-border shrink-0" />
      )}

      {/* Ambiguity gauge */}
      {ambiguity && typeof ambiguity.score === 'number' && (
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] font-semibold text-text-muted uppercase tracking-wide">Ambiguity</span>
            <span className="text-[13px] font-bold text-text-body">{ambiguityPct}%</span>
          </div>
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${ambiguityColor}`}
              style={{ width: `${ambiguityPct}%` }}
            />
          </div>
        </div>
      )}
    </div>
  )
}
