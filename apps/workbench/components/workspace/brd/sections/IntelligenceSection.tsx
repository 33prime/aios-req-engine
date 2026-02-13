'use client'

import { useMemo, useState } from 'react'
import { Brain, ChevronRight, AlertTriangle, RefreshCw, Loader2 } from 'lucide-react'
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
        : 'text-[#333333]'

  return (
    <div className="bg-white rounded-xl border border-[#E5E5E5] p-4 flex-1 min-w-0">
      <div className={`text-[24px] font-bold ${valueColor} leading-tight`}>{value}</div>
      <div className="text-[11px] text-[#999999] mt-0.5">{label}</div>
      <div className="text-[11px] text-[#666666]">{detail}</div>
    </div>
  )
}

// ============================================================================
// Gap item
// ============================================================================

function GapItem({ message, count }: { message: string; count: number }) {
  if (count === 0) return null
  return (
    <div className="flex items-center gap-2 py-1.5">
      <span className="w-1.5 h-1.5 rounded-full bg-[#999999] shrink-0" />
      <span className="text-[12px] text-[#666666]">{message}</span>
      <span className="ml-auto text-[11px] font-medium text-[#999999] bg-[#F0F0F0] px-1.5 py-0.5 rounded">
        {count}
      </span>
    </div>
  )
}

// ============================================================================
// Alert pill (restyled from HealthPanel)
// ============================================================================

function AlertPill({ alert }: { alert: ScopeAlert }) {
  return (
    <div className="flex items-start gap-2 px-3 py-2 rounded-lg bg-[#F0F0F0] text-[12px] text-[#666666]">
      <AlertTriangle className="w-3.5 h-3.5 text-[#999999] shrink-0 mt-0.5" />
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
  const [gapsExpanded, setGapsExpanded] = useState(false)

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

  // Compute gaps from BRD data
  const gaps = useMemo(() => {
    const allFeatures = [
      ...data.requirements.must_have,
      ...data.requirements.should_have,
      ...data.requirements.could_have,
    ]

    // Features without VP step mapping
    const featuresWithoutVpStep = allFeatures.filter((f) => !f.vp_step_id).length

    // VP steps without actor
    const stepsWithoutActor = data.workflows.filter((s) => !s.actor_persona_id).length

    // Personas without features (not referenced in any feature or VP step)
    const referencedPersonaIds = new Set<string>()
    data.workflows.forEach((s) => {
      if (s.actor_persona_id) referencedPersonaIds.add(s.actor_persona_id)
    })
    const orphanedPersonas = data.actors.filter((p) => !referencedPersonaIds.has(p.id)).length

    // Data entities without workflow links
    const unlinkedDataEntities = data.data_entities.filter((e) => e.workflow_step_count === 0).length

    // Unconfirmed by type
    const unconfirmedFeatures = allFeatures.filter(
      (f) => f.confirmation_status === 'ai_generated' || !f.confirmation_status
    ).length
    const unconfirmedPersonas = data.actors.filter(
      (a) => a.confirmation_status === 'ai_generated' || !a.confirmation_status
    ).length

    const hasGaps =
      featuresWithoutVpStep > 0 ||
      stepsWithoutActor > 0 ||
      orphanedPersonas > 0 ||
      unlinkedDataEntities > 0 ||
      unconfirmedFeatures > 0 ||
      unconfirmedPersonas > 0

    return {
      featuresWithoutVpStep,
      stepsWithoutActor,
      orphanedPersonas,
      unlinkedDataEntities,
      unconfirmedFeatures,
      unconfirmedPersonas,
      hasGaps,
    }
  }, [data])

  return (
    <section className="mb-8">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-[#3FAF7A]" />
          <h2 className="text-lg font-semibold text-[#37352f]">Project Intelligence</h2>
        </div>
        {onRefreshAll && (
          <button
            onClick={onRefreshAll}
            disabled={isRefreshing}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-[#666666] bg-white border border-[#E5E5E5] rounded-xl hover:bg-gray-50 transition-colors disabled:opacity-50"
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

      {/* Gaps section (collapsible) */}
      {gaps.hasGaps && (
        <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] overflow-hidden mb-4">
          <button
            onClick={() => setGapsExpanded(!gapsExpanded)}
            className="w-full flex items-center gap-2 px-5 py-3 hover:bg-gray-50/50 transition-colors"
          >
            <ChevronRight
              className={`w-4 h-4 text-[#999999] transition-transform ${gapsExpanded ? 'rotate-90' : ''}`}
            />
            <span className="text-[13px] font-semibold text-[#333333]">Coverage Gaps</span>
            <span className="text-[11px] text-[#999999]">
              Areas that need attention
            </span>
          </button>

          {gapsExpanded && (
            <div className="px-5 pb-4 pt-0 border-t border-[#E5E5E5]">
              <div className="py-1">
                <GapItem
                  message="Features without workflow step mapping"
                  count={gaps.featuresWithoutVpStep}
                />
                <GapItem
                  message="Workflow steps without actor persona"
                  count={gaps.stepsWithoutActor}
                />
                <GapItem
                  message="Personas not referenced in any workflow"
                  count={gaps.orphanedPersonas}
                />
                <GapItem
                  message="Data entities without workflow links"
                  count={gaps.unlinkedDataEntities}
                />
                <GapItem
                  message="Features pending confirmation"
                  count={gaps.unconfirmedFeatures}
                />
                <GapItem
                  message="Personas pending confirmation"
                  count={gaps.unconfirmedPersonas}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Scope alerts */}
      {health && health.scope_alerts.length > 0 && (
        <div className="space-y-2">
          {health.scope_alerts.map((alert, i) => (
            <AlertPill key={i} alert={alert} />
          ))}
        </div>
      )}

      {healthLoading && !health && (
        <div className="text-[12px] text-[#999999] py-2">Loading health data...</div>
      )}
    </section>
  )
}
