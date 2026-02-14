'use client'

import { useState, useEffect, useMemo } from 'react'
import {
  X,
  Clock,
  Users,
  Puzzle,
  Link2,
  Workflow,
  Sparkles,
  CheckCircle2,
  Circle,
  Info,
  AlertTriangle,
  Zap,
  Database,
  Layers,
  Rocket,
  TrendingDown,
  BarChart3,
  Shield,
} from 'lucide-react'
import { BRDStatusBadge } from './StatusBadge'
import { ConfirmActions } from './ConfirmActions'
import { getWorkflowDetail, enrichWorkflow } from '@/lib/api'
import type {
  WorkflowDetail,
  WorkflowInsight,
  StepUnlockSummary,
  WorkflowStepSummary,
  LinkedBusinessDriver,
  LinkedFeature,
  LinkedDataEntity,
  LinkedPersona,
  RevisionEntry,
} from '@/types/workspace'

type TabId = 'overview' | 'connections' | 'insights' | 'history'

interface WorkflowDetailDrawerProps {
  workflowId: string
  projectId: string
  onClose: () => void
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
  onViewStepDetail?: (stepId: string) => void
}

const TABS: { id: TabId; label: string; icon: typeof Clock }[] = [
  { id: 'overview', label: 'Overview', icon: BarChart3 },
  { id: 'connections', label: 'Connections', icon: Link2 },
  { id: 'insights', label: 'Insights', icon: Sparkles },
  { id: 'history', label: 'History', icon: Clock },
]

export function WorkflowDetailDrawer({
  workflowId,
  projectId,
  onClose,
  onConfirm,
  onNeedsReview,
  onViewStepDetail,
}: WorkflowDetailDrawerProps) {
  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [detail, setDetail] = useState<WorkflowDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [enriching, setEnriching] = useState(false)

  const loadDetail = () => {
    setLoading(true)
    return getWorkflowDetail(projectId, workflowId)
      .then((data) => setDetail(data))
      .catch((err) => console.error('Failed to load workflow detail:', err))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getWorkflowDetail(projectId, workflowId)
      .then((data) => {
        if (!cancelled) setDetail(data)
      })
      .catch((err) => {
        console.error('Failed to load workflow detail:', err)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [projectId, workflowId])

  const handleEnrich = async () => {
    setEnriching(true)
    try {
      await enrichWorkflow(projectId, workflowId)
      await loadDetail()
    } catch (err) {
      console.error('Failed to enrich workflow:', err)
    } finally {
      setEnriching(false)
    }
  }

  const connectionCount = useMemo(() => {
    if (!detail) return 0
    return (detail.actor_personas?.length || 0) +
      (detail.business_drivers?.length || 0) +
      (detail.features?.length || 0) +
      (detail.data_entities?.length || 0)
  }, [detail])

  const insightCount = detail?.insights?.length || 0

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-40 transition-opacity"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-[560px] max-w-full bg-white shadow-xl z-50 flex flex-col animate-slide-in-right">
        {/* Header */}
        <div className="flex-shrink-0 border-b border-[#E5E5E5] px-6 py-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3 min-w-0 flex-1">
              {/* Navy circle with workflow icon */}
              <div className="w-8 h-8 rounded-full bg-[#0A1E2F] flex items-center justify-center flex-shrink-0 mt-0.5">
                <Workflow className="w-4 h-4 text-white" />
              </div>
              <div className="min-w-0">
                <p className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-1">
                  Workflow Detail
                </p>
                <h2 className="text-[15px] font-semibold text-[#333333] line-clamp-2 leading-snug">
                  {detail?.name || 'Loading...'}
                </h2>
                {detail && (
                  <div className="flex items-center gap-2 mt-1.5">
                    <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[#F0F0F0] text-[#666666]">
                      {detail.total_step_count} steps
                    </span>
                    {detail.enriched_step_count > 0 && (
                      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[#E8F5E9] text-[#25785A]">
                        {detail.enriched_step_count} enriched
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <BRDStatusBadge status={detail?.confirmation_status} />
              <button
                onClick={onClose}
                className="p-1.5 rounded-md text-[#999999] hover:text-[#666666] hover:bg-[#F0F0F0] transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Confirm/Review actions */}
          {detail && (
            <div className="mt-3">
              <ConfirmActions
                status={detail.confirmation_status}
                onConfirm={() => onConfirm('workflow', workflowId)}
                onNeedsReview={() => onNeedsReview('workflow', workflowId)}
                size="md"
              />
            </div>
          )}

          {/* Tabs */}
          <div className="flex gap-0 mt-4 -mb-4 border-b-0">
            {TABS.map((tab) => {
              const TabIcon = tab.icon
              const isActive = activeTab === tab.id
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-1.5 px-3 py-2 text-[12px] font-medium border-b-2 transition-colors ${
                    isActive
                      ? 'border-[#3FAF7A] text-[#25785A]'
                      : 'border-transparent text-[#999999] hover:text-[#666666]'
                  }`}
                >
                  <TabIcon className="w-3.5 h-3.5" />
                  {tab.label}
                  {tab.id === 'connections' && connectionCount > 0 && (
                    <span className="ml-1 text-[10px] bg-[#F0F0F0] text-[#666666] px-1.5 py-0.5 rounded-full">
                      {connectionCount}
                    </span>
                  )}
                  {tab.id === 'insights' && insightCount > 0 && (
                    <span className="ml-1 text-[10px] bg-[#F0F0F0] text-[#666666] px-1.5 py-0.5 rounded-full">
                      {insightCount}
                    </span>
                  )}
                  {tab.id === 'history' && detail && detail.revision_count > 0 && (
                    <span className="ml-1 text-[10px] bg-[#F0F0F0] text-[#666666] px-1.5 py-0.5 rounded-full">
                      {detail.revision_count}
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {loading && !detail ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#3FAF7A] mx-auto" />
              <p className="text-[12px] text-[#999999] mt-2">Loading workflow details...</p>
            </div>
          ) : detail ? (
            <>
              {activeTab === 'overview' && (
                <OverviewTab detail={detail} onViewStepDetail={onViewStepDetail} onEnrich={handleEnrich} enriching={enriching} />
              )}
              {activeTab === 'connections' && <ConnectionsTab detail={detail} />}
              {activeTab === 'insights' && <InsightsTab insights={detail.insights} />}
              {activeTab === 'history' && <HistoryTab revisions={detail.revisions} />}
            </>
          ) : (
            <div className="text-center py-8">
              <p className="text-[13px] text-[#666666]">Failed to load workflow details.</p>
            </div>
          )}
        </div>
      </div>
    </>
  )
}

// ============================================================================
// Overview Tab
// ============================================================================

function OverviewTab({
  detail,
  onViewStepDetail,
  onEnrich,
  enriching,
}: {
  detail: WorkflowDetail
  onViewStepDetail?: (stepId: string) => void
  onEnrich: () => void
  enriching: boolean
}) {
  const totalSteps = detail.current_steps.length + detail.future_steps.length
  const hasEnrichment = detail.enriched_step_count > 0 || detail.strategic_unlocks.length > 0

  return (
    <div className="space-y-6">
      {/* Description */}
      {detail.description && (
        <div className="bg-[#F4F4F4] border border-[#E5E5E5] rounded-xl px-4 py-3">
          <p className="text-[13px] text-[#333333] leading-relaxed">{detail.description}</p>
        </div>
      )}

      {/* ROI Summary Card */}
      {detail.roi && (
        <ROICard roi={detail.roi} />
      )}

      {/* Health Stats */}
      <HealthStats detail={detail} />

      {/* Step Overview — compact list of both sides */}
      {totalSteps > 0 && (
        <StepOverview
          currentSteps={detail.current_steps}
          futureSteps={detail.future_steps}
          onViewStepDetail={onViewStepDetail}
        />
      )}

      {/* Strategic Unlocks */}
      {detail.strategic_unlocks.length > 0 && (
        <StrategicUnlocksCard unlocks={detail.strategic_unlocks} />
      )}

      {/* Enrich with AI button */}
      {!hasEnrichment && (
        <button
          onClick={onEnrich}
          disabled={enriching}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-[13px] font-medium text-white bg-[#3FAF7A] hover:bg-[#25785A] rounded-xl transition-colors disabled:opacity-50"
        >
          {enriching ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
              Analyzing workflow...
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              Enrich with AI
            </>
          )}
        </button>
      )}
    </div>
  )
}

// ============================================================================
// ROI Card
// ============================================================================

function ROICard({ roi }: { roi: NonNullable<WorkflowDetail['roi']> }) {
  return (
    <div className="border border-[#E5E5E5] rounded-xl overflow-hidden">
      <div className="px-4 py-3 bg-[#0A1E2F]">
        <div className="flex items-center gap-1.5">
          <TrendingDown className="w-3.5 h-3.5 text-[#3FAF7A]" />
          <span className="text-[11px] font-semibold text-white uppercase tracking-wide">
            ROI Summary
          </span>
        </div>
      </div>
      <div className="px-4 py-4">
        {/* Time comparison bars */}
        <div className="space-y-2 mb-4">
          <TimeBar label="Current" minutes={roi.current_total_minutes} max={roi.current_total_minutes} color="bg-[#999999]" />
          <TimeBar label="Future" minutes={roi.future_total_minutes} max={roi.current_total_minutes} color="bg-[#3FAF7A]" />
        </div>

        {/* Savings row */}
        <div className="grid grid-cols-3 gap-3 pt-3 border-t border-[#F0F0F0]">
          <div className="text-center">
            <p className="text-[18px] font-bold text-[#25785A]">{roi.time_saved_percent}%</p>
            <p className="text-[10px] text-[#999999] uppercase">Time Saved</p>
          </div>
          <div className="text-center">
            <p className="text-[18px] font-bold text-[#333333]">{roi.time_saved_minutes}min</p>
            <p className="text-[10px] text-[#999999] uppercase">Per Run</p>
          </div>
          <div className="text-center">
            <p className="text-[18px] font-bold text-[#333333]">
              ${roi.cost_saved_per_year > 0 ? formatCurrency(roi.cost_saved_per_year) : '—'}
            </p>
            <p className="text-[10px] text-[#999999] uppercase">Saved / Year</p>
          </div>
        </div>

        {/* Automation coverage */}
        {roi.steps_total > 0 && (
          <div className="mt-3 pt-3 border-t border-[#F0F0F0]">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[11px] text-[#666666]">Automation Coverage</span>
              <span className="text-[11px] font-medium text-[#333333]">
                {roi.steps_automated}/{roi.steps_total} steps
              </span>
            </div>
            <div className="h-2 bg-[#F0F0F0] rounded-full overflow-hidden">
              <div
                className="h-full bg-[#3FAF7A] rounded-full transition-all"
                style={{ width: `${(roi.steps_automated / roi.steps_total) * 100}%` }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function TimeBar({
  label,
  minutes,
  max,
  color,
}: {
  label: string
  minutes: number
  max: number
  color: string
}) {
  const pct = max > 0 ? (minutes / max) * 100 : 0
  return (
    <div className="flex items-center gap-3">
      <span className="text-[11px] text-[#666666] w-14 shrink-0">{label}</span>
      <div className="flex-1 h-3 bg-[#F0F0F0] rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[12px] font-medium text-[#333333] w-16 text-right">{minutes}min</span>
    </div>
  )
}

// ============================================================================
// Health Stats
// ============================================================================

function HealthStats({ detail }: { detail: WorkflowDetail }) {
  const stats = [
    {
      label: 'No Actor',
      value: detail.steps_without_actor,
      total: detail.total_step_count,
      icon: Users,
    },
    {
      label: 'No Time',
      value: detail.steps_without_time,
      total: detail.total_step_count,
      icon: Clock,
    },
    {
      label: 'No Features',
      value: detail.steps_without_features,
      total: detail.total_step_count,
      icon: Puzzle,
    },
  ]

  const hasIssues = stats.some(s => s.value > 0)
  if (!hasIssues && detail.total_step_count === 0) return null

  return (
    <div>
      <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2 flex items-center gap-1.5">
        <Shield className="w-3.5 h-3.5" />
        Completeness
      </h4>
      <div className="grid grid-cols-3 gap-2">
        {stats.map((stat) => {
          const StatIcon = stat.icon
          const isClean = stat.value === 0
          return (
            <div
              key={stat.label}
              className={`border rounded-xl px-3 py-2.5 text-center ${
                isClean ? 'border-[#E5E5E5] bg-white' : 'border-[#E5E5E5] bg-[#F4F4F4]'
              }`}
            >
              <StatIcon className={`w-4 h-4 mx-auto mb-1 ${isClean ? 'text-[#3FAF7A]' : 'text-[#999999]'}`} />
              <p className={`text-[14px] font-bold ${isClean ? 'text-[#3FAF7A]' : 'text-[#333333]'}`}>
                {isClean ? '✓' : stat.value}
              </p>
              <p className="text-[10px] text-[#999999]">{stat.label}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ============================================================================
// Step Overview — compact list
// ============================================================================

function StepOverview({
  currentSteps,
  futureSteps,
  onViewStepDetail,
}: {
  currentSteps: WorkflowStepSummary[]
  futureSteps: WorkflowStepSummary[]
  onViewStepDetail?: (stepId: string) => void
}) {
  return (
    <div>
      <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2 flex items-center gap-1.5">
        <Layers className="w-3.5 h-3.5" />
        Steps ({currentSteps.length + futureSteps.length})
      </h4>
      <div className="border border-[#E5E5E5] rounded-xl overflow-hidden">
        {currentSteps.length > 0 && (
          <>
            <div className="px-3 py-1.5 bg-[#F4F4F4] border-b border-[#E5E5E5]">
              <span className="text-[10px] font-medium text-[#666666] uppercase">Current State</span>
            </div>
            {currentSteps.map((step) => (
              <StepRow key={step.id} step={step} onClick={onViewStepDetail ? () => onViewStepDetail(step.id) : undefined} />
            ))}
          </>
        )}
        {futureSteps.length > 0 && (
          <>
            <div className="px-3 py-1.5 bg-[#E8F5E9]/50 border-b border-[#E5E5E5] border-t border-t-[#E5E5E5]">
              <span className="text-[10px] font-medium text-[#25785A] uppercase">Future State</span>
            </div>
            {futureSteps.map((step) => (
              <StepRow key={step.id} step={step} onClick={onViewStepDetail ? () => onViewStepDetail(step.id) : undefined} />
            ))}
          </>
        )}
      </div>
    </div>
  )
}

function StepRow({ step, onClick }: { step: WorkflowStepSummary; onClick?: () => void }) {
  const automationConfig: Record<string, { dot: string }> = {
    manual: { dot: 'bg-gray-400' },
    semi_automated: { dot: 'bg-[#999999]' },
    fully_automated: { dot: 'bg-[#3FAF7A]' },
  }
  const c = automationConfig[step.automation_level] || automationConfig.manual

  return (
    <button
      onClick={onClick}
      disabled={!onClick}
      className="w-full flex items-center gap-2.5 px-3 py-2 border-b border-[#F0F0F0] last:border-0 text-left hover:bg-[#F4F4F4]/50 transition-colors disabled:hover:bg-transparent"
    >
      <span className="text-[11px] font-bold text-[#999999] w-5 text-center shrink-0">
        {step.step_index}
      </span>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot} shrink-0`} />
      <span className="text-[12px] text-[#333333] truncate flex-1">{step.label}</span>
      {step.time_minutes != null && (
        <span className="text-[10px] text-[#999999] shrink-0">{step.time_minutes}min</span>
      )}
    </button>
  )
}

// ============================================================================
// Strategic Unlocks Card
// ============================================================================

const UNLOCK_TYPE_CONFIG: Record<string, { icon: typeof Rocket; label: string }> = {
  capability: { icon: Rocket, label: 'New Capability' },
  scale: { icon: Layers, label: 'Scale Unlock' },
  insight: { icon: Sparkles, label: 'New Insight' },
  speed: { icon: Zap, label: 'Speed Unlock' },
}

function StrategicUnlocksCard({ unlocks }: { unlocks: StepUnlockSummary[] }) {
  return (
    <div className="border border-[#3FAF7A]/30 rounded-xl overflow-hidden">
      <div className="px-4 py-3 bg-[#E8F5E9]/50 border-b border-[#3FAF7A]/20">
        <div className="flex items-center gap-1.5">
          <Rocket className="w-3.5 h-3.5 text-[#25785A]" />
          <span className="text-[11px] font-semibold text-[#25785A] uppercase tracking-wide">
            Strategic Unlocks
          </span>
        </div>
        <p className="text-[11px] text-[#666666] mt-0.5">
          What this workflow makes possible beyond time savings
        </p>
      </div>
      <div className="divide-y divide-[#E5E5E5]">
        {unlocks.map((unlock, i) => {
          const config = UNLOCK_TYPE_CONFIG[unlock.unlock_type] || UNLOCK_TYPE_CONFIG.capability
          const TypeIcon = config.icon
          return (
            <div key={i} className="px-4 py-3">
              <div className="flex items-start gap-2.5">
                <TypeIcon className="w-4 h-4 mt-0.5 text-[#3FAF7A] flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-[10px] font-medium uppercase px-1.5 py-0.5 rounded bg-[#E8F5E9] text-[#25785A]">
                      {config.label}
                    </span>
                    {unlock.source_step_label && (
                      <span className="text-[10px] text-[#999999]">
                        from: {unlock.source_step_label}
                      </span>
                    )}
                  </div>
                  <p className="text-[13px] text-[#333333] leading-relaxed font-medium">
                    {unlock.description}
                  </p>
                  <p className="text-[12px] text-[#666666] mt-1 leading-relaxed">
                    {unlock.enabled_by}
                  </p>
                  <p className="text-[11px] text-[#999999] mt-1 italic">
                    {unlock.strategic_value}
                  </p>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ============================================================================
// Connections Tab
// ============================================================================

function ConnectionsTab({ detail }: { detail: WorkflowDetail }) {
  const hasActors = detail.actor_personas.length > 0
  const hasDrivers = detail.business_drivers.length > 0
  const hasFeatures = detail.features.length > 0
  const hasDataEntities = detail.data_entities.length > 0
  const isEmpty = !hasActors && !hasDrivers && !hasFeatures && !hasDataEntities

  if (isEmpty) {
    return (
      <div className="text-center py-8">
        <Link2 className="w-8 h-8 text-[#E5E5E5] mx-auto mb-3" />
        <p className="text-[13px] text-[#666666] mb-1">No connections found</p>
        <p className="text-[12px] text-[#999999]">
          Process more signals or enrich steps to build connections.
        </p>
      </div>
    )
  }

  // Group drivers by type
  const driversByType = detail.business_drivers.reduce<Record<string, LinkedBusinessDriver[]>>((acc, d) => {
    const type = d.driver_type || 'other'
    if (!acc[type]) acc[type] = []
    acc[type].push(d)
    return acc
  }, {})
  const driverTypeOrder = ['pain', 'goal', 'kpi']

  return (
    <div className="space-y-6">
      {/* Actors */}
      {hasActors && (
        <ConnectionGroup icon={Users} title="Actors" count={detail.actor_personas.length}>
          {detail.actor_personas.map((p) => (
            <div key={p.id} className="px-3 py-2.5 border-b border-[#F0F0F0] last:border-0">
              <div className="flex items-center gap-2">
                <span className="text-[13px] text-[#333333] font-medium">{p.name}</span>
                {p.role && (
                  <span className="text-[11px] text-[#999999]">{p.role}</span>
                )}
              </div>
            </div>
          ))}
        </ConnectionGroup>
      )}

      {/* Business Drivers */}
      {hasDrivers && (
        <ConnectionGroup
          icon={AlertTriangle}
          title="Business Drivers"
          count={detail.business_drivers.length}
        >
          {driverTypeOrder.map((type) => {
            const drivers = driversByType[type]
            if (!drivers || drivers.length === 0) return null
            return drivers.map((d) => (
              <div key={d.id} className="px-3 py-2.5 border-b border-[#F0F0F0] last:border-0">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-medium uppercase px-1.5 py-0.5 rounded bg-[#F0F0F0] text-[#666666]">
                    {d.driver_type}
                  </span>
                  <span className="text-[13px] text-[#333333] line-clamp-2 flex-1">{d.description}</span>
                </div>
                <div className="flex items-center gap-2 mt-1">
                  {d.severity && (
                    <span className="text-[10px] text-[#999999]">Severity: {d.severity}</span>
                  )}
                  {d.vision_alignment && (
                    <span className="text-[10px] text-[#999999]">Vision: {d.vision_alignment}</span>
                  )}
                </div>
              </div>
            ))
          })}
        </ConnectionGroup>
      )}

      {/* Features */}
      {hasFeatures && (
        <ConnectionGroup icon={Puzzle} title="Features" count={detail.features.length}>
          {detail.features.map((f) => {
            const isConfirmed = f.confirmation_status === 'confirmed_consultant' || f.confirmation_status === 'confirmed_client'
            return (
              <div key={f.id} className="px-3 py-2.5 border-b border-[#F0F0F0] last:border-0">
                <div className="flex items-center gap-2">
                  {isConfirmed
                    ? <CheckCircle2 className="w-3.5 h-3.5 text-[#3FAF7A] flex-shrink-0" />
                    : <Circle className="w-3.5 h-3.5 text-[#E5E5E5] flex-shrink-0" />
                  }
                  <span className="text-[13px] text-[#333333] font-medium">{f.name}</span>
                  {f.category && (
                    <span className="text-[10px] text-[#999999] bg-[#F0F0F0] px-1.5 py-0.5 rounded">{f.category}</span>
                  )}
                </div>
                {f.priority_group && (
                  <span className="text-[10px] text-[#999999] ml-5.5 mt-0.5 block">
                    {f.priority_group.replace('_', ' ')}
                  </span>
                )}
              </div>
            )
          })}
        </ConnectionGroup>
      )}

      {/* Data Entities */}
      {hasDataEntities && (
        <ConnectionGroup icon={Database} title="Data Entities" count={detail.data_entities.length}>
          {detail.data_entities.map((de) => (
            <div key={de.id} className="px-3 py-2.5 border-b border-[#F0F0F0] last:border-0">
              <div className="flex items-center gap-2">
                <span className="text-[13px] text-[#333333] font-medium">{de.name}</span>
                <span className="text-[10px] text-[#999999] bg-[#F0F0F0] px-1.5 py-0.5 rounded">
                  {de.entity_category}
                </span>
                <OperationBadge type={de.operation_type} />
              </div>
            </div>
          ))}
        </ConnectionGroup>
      )}
    </div>
  )
}

function OperationBadge({ type }: { type: string }) {
  const labels: Record<string, string> = {
    create: 'C', read: 'R', update: 'U', delete: 'D',
  }
  return (
    <span className="text-[10px] font-bold text-[#666666] bg-[#F0F0F0] w-5 h-5 rounded flex items-center justify-center">
      {labels[type] || type[0]?.toUpperCase() || '?'}
    </span>
  )
}

function ConnectionGroup({
  icon: GroupIcon,
  title,
  count,
  children,
}: {
  icon: typeof Users
  title: string
  count: number
  children: React.ReactNode
}) {
  return (
    <div>
      <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2 flex items-center gap-1.5">
        <GroupIcon className="w-3.5 h-3.5" />
        {title}
        <span className="text-[10px] bg-[#F0F0F0] text-[#666666] px-1.5 py-0.5 rounded-full ml-1">
          {count}
        </span>
      </h4>
      <div className="border border-[#E5E5E5] rounded-xl overflow-hidden bg-white">
        {children}
      </div>
    </div>
  )
}

// ============================================================================
// Insights Tab
// ============================================================================

function InsightsTab({ insights }: { insights: WorkflowInsight[] }) {
  if (!insights || insights.length === 0) {
    return (
      <div className="text-center py-8">
        <CheckCircle2 className="w-8 h-8 text-[#3FAF7A] mx-auto mb-3" />
        <p className="text-[13px] text-[#666666] mb-1">No issues detected</p>
        <p className="text-[12px] text-[#999999]">
          This workflow is well-connected and balanced.
        </p>
      </div>
    )
  }

  const typeConfig: Record<string, { icon: typeof Info; borderColor: string; iconColor: string }> = {
    gap: { icon: Info, borderColor: 'border-[#E5E5E5]', iconColor: 'text-[#999999]' },
    warning: { icon: AlertTriangle, borderColor: 'border-[#E5E5E5]', iconColor: 'text-[#999999]' },
    opportunity: { icon: Sparkles, borderColor: 'border-[#3FAF7A]/30', iconColor: 'text-[#3FAF7A]' },
    strength: { icon: CheckCircle2, borderColor: 'border-[#3FAF7A]/30', iconColor: 'text-[#3FAF7A]' },
  }

  return (
    <div className="space-y-3">
      {insights.map((insight, i) => {
        const config = typeConfig[insight.insight_type] || typeConfig.gap
        const Icon = config.icon
        return (
          <div
            key={i}
            className={`border ${config.borderColor} rounded-xl px-4 py-3`}
          >
            <div className="flex items-start gap-2">
              <Icon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${config.iconColor}`} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-[10px] font-medium uppercase px-1.5 py-0.5 rounded bg-[#F0F0F0] text-[#666666]">
                    {insight.insight_type}
                  </span>
                </div>
                <p className="text-[13px] text-[#333333] leading-relaxed">{insight.message}</p>
                {insight.suggestion && (
                  <p className="text-[12px] text-[#999999] mt-1">{insight.suggestion}</p>
                )}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ============================================================================
// History Tab
// ============================================================================

function HistoryTab({ revisions }: { revisions: RevisionEntry[] }) {
  if (!revisions || revisions.length === 0) {
    return (
      <div className="text-center py-8">
        <Clock className="w-8 h-8 text-[#E5E5E5] mx-auto mb-3" />
        <p className="text-[13px] text-[#666666] mb-1">No revision history</p>
        <p className="text-[12px] text-[#999999]">
          Changes will be tracked here as signals are processed.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {revisions.map((rev, i) => {
        const typeColors: Record<string, string> = {
          created: 'bg-[#E8F5E9] text-[#25785A]',
          enriched: 'bg-[#F0F0F0] text-[#666666]',
          updated: 'bg-[#F0F0F0] text-[#666666]',
          merged: 'bg-[#F0F0F0] text-[#666666]',
        }
        return (
          <div key={i} className="border border-[#E5E5E5] rounded-xl px-4 py-3">
            <div className="flex items-center gap-2 mb-1">
              <span className={`text-[10px] font-medium uppercase px-1.5 py-0.5 rounded ${typeColors[rev.revision_type] || typeColors.updated}`}>
                {rev.revision_type}
              </span>
              <span className="text-[10px] text-[#999999]">
                {rev.created_at ? formatRelativeTime(rev.created_at) : ''}
              </span>
              {rev.created_by && (
                <span className="text-[10px] text-[#999999]">by {rev.created_by}</span>
              )}
            </div>
            {rev.diff_summary && (
              <p className="text-[12px] text-[#666666]">{rev.diff_summary}</p>
            )}
          </div>
        )
      })}
    </div>
  )
}

// ============================================================================
// Helpers
// ============================================================================

function formatRelativeTime(dateStr: string): string {
  try {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMin = Math.floor(diffMs / 60000)
    if (diffMin < 1) return 'just now'
    if (diffMin < 60) return `${diffMin}m ago`
    const diffHrs = Math.floor(diffMin / 60)
    if (diffHrs < 24) return `${diffHrs}h ago`
    const diffDays = Math.floor(diffHrs / 24)
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  } catch {
    return ''
  }
}

function formatCurrency(amount: number): string {
  if (amount >= 1000) {
    return `${(amount / 1000).toFixed(1)}k`
  }
  return amount.toFixed(0)
}
