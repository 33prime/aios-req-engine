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
// Gap item
// ============================================================================
// Alert pill (restyled from HealthPanel)
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
  // Compute metrics from BRD data
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
      ...data.data_entities,
      ...data.stakeholders,
    ]

    const isConfirmed = (s?: string | null) =>
      s === 'confirmed_consultant' || s === 'confirmed_client'

    const confirmed = allEntities.filter((e) => isConfirmed(e.confirmation_status)).length
    const total = allEntities.length
    const confirmedPct = total > 0 ? Math.round((confirmed / total) * 100) : 0

    // Enrichment: features with details, personas with enrichment
    const enrichedFeatures = allFeatures.filter((f) => f.description).length
    const enrichedPersonas = data.actors.filter((a) => a.goals && a.goals.length > 0).length
    const enrichable = allFeatures.length + data.actors.length
    const enriched = enrichedFeatures + enrichedPersonas
    const enrichedPct = enrichable > 0 ? Math.round((enriched / enrichable) * 100) : 0

    // Staleness
    const staleCount =
      data.actors.filter((a) => a.is_stale).length +
      data.workflows.filter((w) => w.is_stale).length +
      allFeatures.filter((f) => f.is_stale).length +
      data.data_entities.filter((d) => d.is_stale).length

    // Risk score from health alerts
    const alertCount = health?.scope_alerts.length || 0
    const warningCount = health?.scope_alerts.filter((a) => a.severity === 'warning').length || 0
    const riskScore = warningCount > 0 ? 'High' : alertCount > 0 ? 'Medium' : 'Low'

    return {
      confirmed,
      total,
      confirmedPct,
      enriched,
      enrichable,
      enrichedPct,
      staleCount,
      riskScore,
      alertCount,
    }
  }, [data, health])

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

      {/* Metrics row */}
      <div className="flex gap-3 mb-4">
        <MetricCard
          value={`${metrics.confirmedPct}%`}
          label="Confirmed"
          detail={`${metrics.confirmed} / ${metrics.total} entities`}
          accent={metrics.confirmedPct >= 75 ? 'green' : 'default'}
        />
        <MetricCard
          value={`${metrics.enrichedPct}%`}
          label="Enriched"
          detail={`${metrics.enriched} / ${metrics.enrichable} entities`}
          accent={metrics.enrichedPct >= 75 ? 'green' : 'default'}
        />
        <MetricCard
          value={String(metrics.staleCount)}
          label="Stale"
          detail={metrics.staleCount === 0 ? 'All up to date' : 'May be outdated'}
          accent={metrics.staleCount > 0 ? 'orange' : 'default'}
        />
        <MetricCard
          value={metrics.riskScore}
          label="Risk"
          detail={`${metrics.alertCount} scope ${metrics.alertCount === 1 ? 'alert' : 'alerts'}`}
          accent={metrics.riskScore === 'High' ? 'orange' : 'default'}
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
