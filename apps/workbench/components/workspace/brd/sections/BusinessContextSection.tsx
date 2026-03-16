'use client'

import { useState, useMemo } from 'react'
import { Building2, AlertTriangle, Target, Eye, BarChart3 } from 'lucide-react'
import { BusinessDriverDetailDrawer } from '../components/BusinessDriverDetailDrawer'
import { DriverContainer } from '../components/DriverContainer'
import { DriverItemRow } from '../components/DriverItemRow'
import { NarrativeEditor } from '../components/NarrativeEditor'
import type { BRDWorkspaceData, BusinessDriver, SectionScore, StakeholderBRDSummary } from '@/types/workspace'

interface BusinessContextSectionProps {
  data: BRDWorkspaceData['business_context']
  projectId: string
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
  onConfirmAll: (entityType: string, ids: string[]) => void
  onUpdateVision: (vision: string) => void
  onUpdateBackground: (background: string) => void
  onStatusClick?: (entityType: string, entityId: string, entityName: string, status?: string | null) => void
  sectionScore?: SectionScore | null
  stakeholders?: StakeholderBRDSummary[]
}

const SHOW_MAX_DRIVERS = 6
const SHOW_MAX_METRICS = 8

// ============================================================================
// Main Section
// ============================================================================

export function BusinessContextSection({
  data,
  projectId,
  onConfirm,
  onNeedsReview,
  onConfirmAll,
  onUpdateVision,
  onUpdateBackground,
  onStatusClick,
  sectionScore,
  stakeholders = [],
}: BusinessContextSectionProps) {
  const [showAllGoals, setShowAllGoals] = useState(false)
  const [showAllPains, setShowAllPains] = useState(false)
  const [showAllMetrics, setShowAllMetrics] = useState(false)
  const [selectedDriver, setSelectedDriver] = useState<{ id: string; type: 'pain' | 'goal' | 'kpi'; data: BusinessDriver } | null>(null)

  // Which driver row is expanded inline (only one at a time)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const confirmedPains = data.pain_points.filter(
    (p) => p.confirmation_status === 'confirmed_consultant' || p.confirmation_status === 'confirmed_client'
  ).length
  const confirmedGoals = data.goals.filter(
    (g) => g.confirmation_status === 'confirmed_consultant' || g.confirmation_status === 'confirmed_client'
  ).length
  const confirmedMetrics = data.success_metrics.filter(
    (m) => m.confirmation_status === 'confirmed_consultant' || m.confirmation_status === 'confirmed_client'
  ).length

  // Sort goals + pains by relatability_score descending (built into container)
  const sortedPains = useMemo(
    () => [...data.pain_points].sort((a, b) => (b.relatability_score ?? 0) - (a.relatability_score ?? 0)),
    [data.pain_points]
  )
  const sortedGoals = useMemo(
    () => [...data.goals].sort((a, b) => (b.relatability_score ?? 0) - (a.relatability_score ?? 0)),
    [data.goals]
  )

  const sortedMetrics = useMemo(
    () => [...data.success_metrics].sort((a, b) => (b.relatability_score ?? 0) - (a.relatability_score ?? 0)),
    [data.success_metrics]
  )

  const visibleGoals = showAllGoals ? sortedGoals : sortedGoals.slice(0, SHOW_MAX_DRIVERS)
  const visiblePains = showAllPains ? sortedPains : sortedPains.slice(0, SHOW_MAX_DRIVERS)
  const visibleMetrics = showAllMetrics ? sortedMetrics : sortedMetrics.slice(0, SHOW_MAX_METRICS)

  const companyMeta = data.company_name ? { name: data.company_name, industry: data.industry } : null

  return (
    <section id="brd-section-business-context" className="space-y-8">
      {/* Background — Problem Provenance */}
      <div>
        <h2 className="text-lg font-semibold text-text-body mb-3 flex items-center gap-2">
          <Building2 className="w-5 h-5 text-text-placeholder" />
          What drove the need for this solution
        </h2>
        <div className="bg-white rounded-2xl shadow-md border border-border p-5">
          <NarrativeEditor
            field="background"
            label="Background"
            currentValue={data.background}
            projectId={projectId}
            onSave={onUpdateBackground}
            placeholder="As signals come in — meeting notes, emails, research — this section will tell the story of what led to this initiative and why now is the right time."
            companyMeta={companyMeta}
          />
        </div>
      </div>

      {/* Vision — Future State */}
      <div>
        <h2 className="text-lg font-semibold text-text-body mb-3 flex items-center gap-2">
          <Eye className="w-5 h-5 text-text-placeholder" />
          Vision
        </h2>
        <div className="bg-white rounded-2xl shadow-md border border-border p-5">
          <NarrativeEditor
            field="vision"
            label="Vision"
            currentValue={data.vision}
            projectId={projectId}
            onSave={onUpdateVision}
            placeholder="As goals and pain points take shape, this section will paint the picture of what success looks like once the solution is in place."
          />
        </div>
      </div>

      {/* Business Goals — Action Queue pattern */}
      <DriverContainer
        icon={Target}
        title="BUSINESS GOALS"
        count={data.goals.length}
        confirmedCount={confirmedGoals}
        onConfirmAll={() => onConfirmAll('business_driver', data.goals.map(g => g.id))}
      >
        {data.goals.length === 0 ? (
          <p className="px-5 py-4 text-[13px] text-text-placeholder italic">No business goals identified yet</p>
        ) : (
          <>
            {visibleGoals.map((goal) => (
              <DriverItemRow
                key={goal.id}
                driver={goal}
                driverType="goal"
                isExpanded={expandedId === goal.id}
                onToggle={() => setExpandedId(expandedId === goal.id ? null : goal.id)}
                onDrawerOpen={() => setSelectedDriver({ id: goal.id, type: 'goal', data: goal })}
                onConfirm={() => onConfirm('business_driver', goal.id)}
                onNeedsReview={() => onNeedsReview('business_driver', goal.id)}
                onStatusClick={onStatusClick ? () => onStatusClick('business_driver', goal.id, goal.description.slice(0, 60), goal.confirmation_status) : undefined}
              />
            ))}
            {sortedGoals.length > SHOW_MAX_DRIVERS && (
              <button
                onClick={() => setShowAllGoals(!showAllGoals)}
                className="w-full px-4 py-2.5 text-[12px] font-medium text-brand-primary hover:bg-surface-page transition-colors border-t border-[#F0F0F0]"
              >
                {showAllGoals ? 'Show less' : `Show all ${sortedGoals.length} goals`}
              </button>
            )}
          </>
        )}
      </DriverContainer>

      {/* Business Pain Points — Action Queue pattern */}
      <DriverContainer
        icon={AlertTriangle}
        title="BUSINESS PAIN POINTS"
        count={data.pain_points.length}
        confirmedCount={confirmedPains}
        onConfirmAll={() => onConfirmAll('business_driver', data.pain_points.map(p => p.id))}
      >
        {data.pain_points.length === 0 ? (
          <p className="px-5 py-4 text-[13px] text-text-placeholder italic">No pain points identified yet</p>
        ) : (
          <>
            {visiblePains.map((pain) => (
              <DriverItemRow
                key={pain.id}
                driver={pain}
                driverType="pain"
                isExpanded={expandedId === pain.id}
                onToggle={() => setExpandedId(expandedId === pain.id ? null : pain.id)}
                onDrawerOpen={() => setSelectedDriver({ id: pain.id, type: 'pain', data: pain })}
                onConfirm={() => onConfirm('business_driver', pain.id)}
                onNeedsReview={() => onNeedsReview('business_driver', pain.id)}
                onStatusClick={onStatusClick ? () => onStatusClick('business_driver', pain.id, pain.description.slice(0, 60), pain.confirmation_status) : undefined}
              />
            ))}
            {sortedPains.length > SHOW_MAX_DRIVERS && (
              <button
                onClick={() => setShowAllPains(!showAllPains)}
                className="w-full px-4 py-2.5 text-[12px] font-medium text-brand-primary hover:bg-surface-page transition-colors border-t border-[#F0F0F0]"
              >
                {showAllPains ? 'Show less' : `Show all ${sortedPains.length} pain points`}
              </button>
            )}
          </>
        )}
      </DriverContainer>

      {/* Success Metrics — unified DriverContainer+DriverItemRow pattern */}
      <DriverContainer
        icon={BarChart3}
        title="SUCCESS METRICS"
        count={data.success_metrics.length}
        confirmedCount={confirmedMetrics}
        onConfirmAll={() => onConfirmAll('business_driver', data.success_metrics.map(m => m.id))}
      >
        {data.success_metrics.length === 0 ? (
          <p className="px-5 py-4 text-[13px] text-text-placeholder italic">No success metrics defined yet</p>
        ) : (
          <>
            {visibleMetrics.map((metric) => (
              <DriverItemRow
                key={metric.id}
                driver={metric}
                driverType="kpi"
                isExpanded={expandedId === metric.id}
                onToggle={() => setExpandedId(expandedId === metric.id ? null : metric.id)}
                onDrawerOpen={() => setSelectedDriver({ id: metric.id, type: 'kpi', data: metric })}
                onConfirm={() => onConfirm('business_driver', metric.id)}
                onNeedsReview={() => onNeedsReview('business_driver', metric.id)}
                onStatusClick={onStatusClick ? () => onStatusClick('business_driver', metric.id, metric.description.slice(0, 60), metric.confirmation_status) : undefined}
              />
            ))}
            {sortedMetrics.length > SHOW_MAX_METRICS && (
              <button
                onClick={() => setShowAllMetrics(!showAllMetrics)}
                className="w-full px-4 py-2.5 text-[12px] font-medium text-brand-primary hover:bg-surface-page transition-colors border-t border-[#F0F0F0]"
              >
                {showAllMetrics ? 'Show less' : `Show all ${sortedMetrics.length} metrics`}
              </button>
            )}
          </>
        )}
      </DriverContainer>

      {/* Detail Drawer */}
      {selectedDriver && (
        <BusinessDriverDetailDrawer
          driverId={selectedDriver.id}
          driverType={selectedDriver.type}
          projectId={projectId}
          initialData={selectedDriver.data}
          stakeholders={stakeholders}
          onClose={() => setSelectedDriver(null)}
          onConfirm={onConfirm}
          onNeedsReview={onNeedsReview}
        />
      )}
    </section>
  )
}
