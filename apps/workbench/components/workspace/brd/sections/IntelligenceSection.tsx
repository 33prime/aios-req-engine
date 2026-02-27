'use client'

import { useMemo } from 'react'
import { Brain, AlertTriangle, RefreshCw, Loader2 } from 'lucide-react'
import type { BRDWorkspaceData, ScopeAlert, BRDHealthData } from '@/types/workspace'

interface IntelligenceSectionProps {
  data: BRDWorkspaceData
  health: BRDHealthData | null
  healthLoading: boolean
  onRefreshAll?: () => void
  isRefreshing?: boolean
}

// ============================================================================
// Metric card
// ============================================================================

function MetricCard({
  value,
  label,
  detail,
  accent,
}: {
  value: string
  label: string
  detail: string
  accent?: 'green' | 'orange' | 'default'
}) {
  const valueColor =
    accent === 'green'
      ? 'text-[#25785A]'
      : accent === 'orange'
        ? 'text-orange-600'
        : 'text-text-body'

  return (
    <div className="bg-white rounded-xl border border-border p-4 flex-1 min-w-0">
      <div className={`text-[24px] font-bold ${valueColor} leading-tight`}>{value}</div>
      <div className="text-[11px] text-text-placeholder mt-0.5">{label}</div>
      <div className="text-[11px] text-[#666666]">{detail}</div>
    </div>
  )
}

// ============================================================================
// Alert pill
// ============================================================================

function AlertPill({ alert }: { alert: ScopeAlert }) {
  return (
    <div className="flex items-start gap-2 px-3 py-2 rounded-lg bg-[#F0F0F0] text-[12px] text-[#666666]">
      <AlertTriangle className="w-3.5 h-3.5 text-text-placeholder shrink-0 mt-0.5" />
      <span>{alert.message}</span>
    </div>
  )
}

// ============================================================================
// Main component
// ============================================================================

export function IntelligenceSection({
  data,
  health,
  healthLoading,
  onRefreshAll,
  isRefreshing,
}: IntelligenceSectionProps) {
  const metrics = useMemo(() => {
    const allFeatures = [
      ...data.requirements.must_have,
      ...data.requirements.should_have,
      ...data.requirements.could_have,
      ...data.requirements.out_of_scope,
    ]
    const allEntities = [
      ...data.business_context.pain_points,
      ...data.business_context.goals,
      ...data.business_context.success_metrics,
      ...data.actors,
      ...data.workflows,
      ...allFeatures,
      ...data.constraints,
    ]

    const isConfirmed = (s?: string | null) =>
      s === 'confirmed_consultant' || s === 'confirmed_client'

    const confirmed = allEntities.filter((e) => isConfirmed(e.confirmation_status)).length
    const total = allEntities.length
    const confirmedPct = total > 0 ? Math.round((confirmed / total) * 100) : 0

    // Provenance % from backend
    const provenancePct = Math.round(data.provenance_pct ?? 0)

    // Gap cluster count from backend
    const gapCount = data.gap_cluster_count ?? 0

    return {
      confirmed,
      total,
      confirmedPct,
      provenancePct,
      gapCount,
    }
  }, [data])

  return (
    <section className="mb-8">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-brand-primary" />
          <h2 className="text-lg font-semibold text-[#37352f]">Project Intelligence</h2>
        </div>
        {onRefreshAll && (
          <button
            onClick={onRefreshAll}
            disabled={isRefreshing}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-[#666666] bg-white border border-border rounded-xl hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            {isRefreshing ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <RefreshCw className="w-3.5 h-3.5" />
            )}
            Refresh Health
          </button>
        )}
      </div>

      {/* 3-card metrics row */}
      <div className="flex gap-3 mb-4">
        <MetricCard
          value={`${metrics.confirmedPct}%`}
          label="Confirmed"
          detail={`${metrics.confirmed} / ${metrics.total} entities`}
          accent={metrics.confirmedPct >= 75 ? 'green' : 'default'}
        />
        <MetricCard
          value={`${metrics.provenancePct}%`}
          label="Provenance"
          detail="Entities traced to source signals"
          accent={metrics.provenancePct >= 75 ? 'green' : metrics.provenancePct < 30 ? 'orange' : 'default'}
        />
        <MetricCard
          value={String(metrics.gapCount)}
          label="Gaps Detected"
          detail={metrics.gapCount === 0 ? 'No intelligence gaps' : `${metrics.gapCount} intelligence gap${metrics.gapCount !== 1 ? 's' : ''} found`}
          accent={metrics.gapCount === 0 ? 'green' : metrics.gapCount > 3 ? 'orange' : 'default'}
        />
      </div>

      {/* Scope alerts */}
      {health && health.scope_alerts.length > 0 && (
        <div className="space-y-2">
          {health.scope_alerts.map((alert, i) => (
            <AlertPill key={i} alert={alert} />
          ))}
        </div>
      )}
    </section>
  )
}
