'use client'

import { useState } from 'react'
import { ChevronDown, ChevronRight, AlertTriangle, TrendingUp, Target } from 'lucide-react'
import { useBRDData } from '@/lib/hooks/use-api'
import type { BusinessDriver, NeedNarrative, ROISummary } from '@/types/workspace'

interface PainValueCenterProps {
  projectId: string
}

// ============================================
// Severity config
// ============================================
const SEVERITY_STYLE: Record<string, { bg: string; text: string }> = {
  critical: { bg: 'bg-red-50', text: 'text-red-700' },
  high: { bg: 'bg-amber-50', text: 'text-amber-700' },
  medium: { bg: 'bg-blue-50', text: 'text-blue-700' },
  low: { bg: 'bg-gray-100', text: 'text-gray-600' },
}

const MONETARY_TYPE_LABELS: Record<string, string> = {
  cost_reduction: 'Cost Reduction',
  revenue_increase: 'Revenue Increase',
  revenue_new: 'New Revenue',
  risk_avoidance: 'Risk Avoidance',
  productivity_gain: 'Productivity Gain',
}

// ============================================
// Sub-components
// ============================================

function SectionAccordion({
  title,
  icon,
  defaultOpen = false,
  count,
  children,
}: {
  title: string
  icon: React.ReactNode
  defaultOpen?: boolean
  count?: number
  children: React.ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 py-2 text-left group"
      >
        {open ? (
          <ChevronDown className="w-4 h-4 text-text-placeholder" />
        ) : (
          <ChevronRight className="w-4 h-4 text-text-placeholder" />
        )}
        {icon}
        <span className="text-sm font-semibold text-text-body">{title}</span>
        {count !== undefined && count > 0 && (
          <span className="text-[11px] text-text-placeholder ml-1">({count})</span>
        )}
      </button>
      {open && <div className="pl-6 mt-1">{children}</div>}
    </div>
  )
}

function NeedNarrativeCard({ narrative }: { narrative: NeedNarrative }) {
  return (
    <div className="border-l-3 border-brand-primary bg-brand-primary-light rounded-r-xl px-4 py-3 mb-4">
      <p className="text-sm text-text-body leading-relaxed">{narrative.text}</p>
      {narrative.anchors && narrative.anchors.length > 0 && (
        <p className="text-[11px] text-text-placeholder mt-2">
          Based on {narrative.anchors.length} source{narrative.anchors.length !== 1 ? 's' : ''}
        </p>
      )}
    </div>
  )
}

function PainDriverCard({ driver }: { driver: BusinessDriver }) {
  const sev = driver.severity?.toLowerCase() ?? 'low'
  const style = SEVERITY_STYLE[sev] ?? SEVERITY_STYLE.low
  const statusBadge = driver.confirmation_status === 'confirmed_client'
    ? 'bg-green-50 text-green-700'
    : driver.confirmation_status === 'confirmed_consultant'
      ? 'bg-blue-50 text-blue-700'
      : null

  return (
    <div className="bg-white border border-border rounded-xl p-3.5 space-y-1.5">
      <div className="flex items-start gap-2">
        <p className="text-sm text-text-body flex-1">{driver.description}</p>
        <span className={`shrink-0 px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${style.bg} ${style.text}`}>
          {sev}
        </span>
        {statusBadge && (
          <span className={`shrink-0 px-1.5 py-0.5 rounded-full text-[9px] font-semibold uppercase ${statusBadge}`}>
            Confirmed
          </span>
        )}
      </div>
      {driver.business_impact && (
        <p className="text-[12px] text-text-secondary">{driver.business_impact}</p>
      )}
      <div className="flex flex-wrap gap-2">
        {driver.affected_users && (
          <span className="text-[11px] text-text-placeholder">Affects: {driver.affected_users}</span>
        )}
        {driver.frequency && (
          <span className="px-1.5 py-0.5 bg-surface-subtle rounded text-[10px] text-text-secondary">
            {driver.frequency}
          </span>
        )}
      </div>
      {driver.current_workaround && (
        <p className="text-[11px] text-text-placeholder italic">
          Current workaround: {driver.current_workaround}
        </p>
      )}
    </div>
  )
}

function FinancialImpactCard({
  metrics,
  roiSummary,
}: {
  metrics: BusinessDriver[]
  roiSummary: ROISummary[]
}) {
  // Aggregate annual monetary values
  const annualMetrics = metrics.filter(
    m => m.monetary_timeframe === 'annual' || !m.monetary_timeframe
  )
  const totalLow = annualMetrics.reduce((sum, m) => sum + (m.monetary_value_low ?? 0), 0)
  const totalHigh = annualMetrics.reduce((sum, m) => sum + (m.monetary_value_high ?? 0), 0)

  // Group by monetary_type
  const byType = metrics.reduce<Record<string, number>>((acc, m) => {
    if (m.monetary_type) {
      acc[m.monetary_type] = (acc[m.monetary_type] ?? 0) + (m.monetary_value_high ?? m.monetary_value_low ?? 0)
    }
    return acc
  }, {})

  const hasMonetary = totalLow > 0 || totalHigh > 0
  const hasROI = roiSummary.length > 0

  if (!hasMonetary && !hasROI) return null

  const formatCurrency = (n: number) => {
    if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
    if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`
    return `$${n.toFixed(0)}`
  }

  return (
    <div className="bg-white border border-border rounded-xl p-3.5 space-y-2">
      {hasMonetary && (
        <div>
          <p className="text-lg font-semibold text-text-body">
            {formatCurrency(totalLow)}
            {totalHigh > totalLow && <span> – {formatCurrency(totalHigh)}</span>}
            <span className="text-sm font-normal text-text-placeholder ml-1">/ year</span>
          </p>
          <div className="flex flex-wrap gap-1.5 mt-1.5">
            {Object.entries(byType).map(([type, value]) => (
              <span
                key={type}
                className="px-2 py-0.5 bg-surface-subtle rounded-full text-[10px] font-medium text-text-secondary"
              >
                {MONETARY_TYPE_LABELS[type] || type}: {formatCurrency(value)}
              </span>
            ))}
          </div>
        </div>
      )}
      {hasROI &&
        roiSummary.slice(0, 3).map((roi, i) => (
          <p key={i} className="text-[12px] text-text-secondary">
            Save {roi.time_saved_minutes}min/run across {roi.workflow_name}
            {roi.cost_saved_per_year > 0 && (
              <span className="font-medium"> = {formatCurrency(roi.cost_saved_per_year)}/yr</span>
            )}
          </p>
        ))}
    </div>
  )
}

function GoalCard({ driver }: { driver: BusinessDriver }) {
  return (
    <div className="flex items-start gap-2 py-1.5">
      <Target className="w-3.5 h-3.5 text-text-placeholder mt-0.5 shrink-0" />
      <div className="min-w-0">
        <p className="text-sm text-text-body">{driver.description}</p>
        {driver.success_criteria && (
          <p className="text-[11px] text-text-placeholder mt-0.5">{driver.success_criteria}</p>
        )}
        {driver.goal_timeframe && (
          <span className="text-[10px] px-1.5 py-0.5 bg-surface-subtle rounded text-text-secondary">
            {driver.goal_timeframe}
          </span>
        )}
      </div>
    </div>
  )
}

// ============================================
// Main component
// ============================================

export function PainValueCenter({ projectId }: PainValueCenterProps) {
  const { data: brd } = useBRDData(projectId)
  const [showAllPains, setShowAllPains] = useState(false)

  const painPoints = brd?.business_context?.pain_points ?? []
  const goals = brd?.business_context?.goals ?? []
  const successMetrics = brd?.business_context?.success_metrics ?? []
  const roiSummary = brd?.roi_summary ?? []
  const needNarrative = brd?.need_narrative

  // Sort pains by severity
  const severityOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 }
  const sortedPains = [...painPoints].sort(
    (a, b) => (severityOrder[a.severity?.toLowerCase() ?? 'low'] ?? 3) - (severityOrder[b.severity?.toLowerCase() ?? 'low'] ?? 3)
  )

  const visiblePains = showAllPains ? sortedPains : sortedPains.slice(0, 5)
  const hasMonetary = successMetrics.some(m => m.monetary_value_low || m.monetary_value_high)

  // Empty state
  if (!needNarrative && painPoints.length === 0 && goals.length === 0 && successMetrics.length === 0) {
    return (
      <div className="bg-white rounded-2xl border border-border shadow-sm p-5">
        <h3 className="text-sm font-semibold text-text-body flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-text-placeholder" />
          Pain & Value Center
        </h3>
        <p className="text-sm text-text-placeholder mt-3">
          Feed signals to surface client pain points, goals, and financial impact.
        </p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-2xl border border-border shadow-sm p-5 space-y-3">
      <h3 className="text-sm font-semibold text-text-body flex items-center gap-2">
        <AlertTriangle className="w-4 h-4 text-text-placeholder" />
        Pain & Value Center
      </h3>

      {/* Need Narrative */}
      {needNarrative && <NeedNarrativeCard narrative={needNarrative} />}

      {/* Pain Drivers */}
      {painPoints.length > 0 && (
        <SectionAccordion
          title="Pain Drivers"
          icon={<AlertTriangle className="w-3.5 h-3.5 text-red-500" />}
          defaultOpen
          count={painPoints.length}
        >
          <div className="space-y-2">
            {visiblePains.map((p) => (
              <PainDriverCard key={p.id} driver={p} />
            ))}
            {sortedPains.length > 5 && !showAllPains && (
              <button
                onClick={() => setShowAllPains(true)}
                className="text-[12px] text-brand-primary hover:underline font-medium"
              >
                Show all {sortedPains.length} pain drivers
              </button>
            )}
          </div>
        </SectionAccordion>
      )}

      {/* Financial Impact */}
      {(hasMonetary || roiSummary.length > 0) && (
        <SectionAccordion
          title="Financial Impact"
          icon={<TrendingUp className="w-3.5 h-3.5 text-brand-primary" />}
          defaultOpen={hasMonetary}
        >
          <FinancialImpactCard metrics={successMetrics} roiSummary={roiSummary} />
        </SectionAccordion>
      )}

      {/* Goals */}
      {goals.length > 0 && (
        <SectionAccordion
          title="Goals"
          icon={<Target className="w-3.5 h-3.5 text-text-secondary" />}
          count={goals.length}
        >
          <div className="space-y-0.5">
            {goals.map((g) => (
              <GoalCard key={g.id} driver={g} />
            ))}
          </div>
        </SectionAccordion>
      )}
    </div>
  )
}
