'use client'

import { useState, useEffect, useMemo } from 'react'
import {
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
  TrendingDown,
  BarChart3,
  Shield,
  FileText,
} from 'lucide-react'
import { DrawerShell, type DrawerTab } from '@/components/ui/DrawerShell'
import { Spinner } from '@/components/ui/Spinner'
import { BRDStatusBadge } from './StatusBadge'
import { ConfirmActions } from './ConfirmActions'
import { Markdown } from '@/components/ui/Markdown'
import { ConnectionGroup } from '@/components/ui/ConnectionGroup'
import { formatRelativeTime, formatRevisionAuthor, REVISION_TYPE_COLORS } from '@/lib/date-utils'
import { getWorkflowDetail, enrichWorkflow } from '@/lib/api'
import type {
  WorkflowDetail,
  WorkflowInsight,
  WorkflowStepSummary,
  LinkedBusinessDriver,
  LinkedFeature,
  LinkedDataEntity,
  LinkedPersona,
  RevisionEntry,
} from '@/types/workspace'
import type { StakeholderBRDSummary } from '@/types/workspace'
import { WhoHasTheData } from './WhoHasTheData'
import { inferTopicsFromText } from '@/lib/topic-role-map'

type TabId = 'overview' | 'evidence' | 'connections' | 'insights' | 'history' | 'who_knows'

interface WorkflowDetailDrawerProps {
  workflowId: string
  projectId: string
  stakeholders?: StakeholderBRDSummary[]
  onClose: () => void
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
  onViewStepDetail?: (stepId: string) => void
}

const TABS: { id: TabId; label: string; icon: typeof Clock }[] = [
  { id: 'overview', label: 'Overview', icon: BarChart3 },
  { id: 'evidence', label: 'Evidence', icon: FileText },
  { id: 'connections', label: 'Connections', icon: Link2 },
  { id: 'insights', label: 'Insights', icon: Sparkles },
  { id: 'history', label: 'History', icon: Clock },
  { id: 'who_knows', label: 'Who Knows', icon: Users },
]

export function WorkflowDetailDrawer({
  workflowId,
  projectId,
  stakeholders = [],
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

  const evidenceCount = detail?.evidence?.length || 0

  const connectionCount = useMemo(() => {
    if (!detail) return 0
    return (detail.actor_personas?.length || 0) +
      (detail.business_drivers?.length || 0) +
      (detail.features?.length || 0) +
      (detail.data_entities?.length || 0)
  }, [detail])

  const insightCount = detail?.insights?.length || 0

  const drawerTabs: DrawerTab[] = TABS.map((tab) => ({
    id: tab.id,
    label: tab.label,
    icon: tab.icon,
    badge: tab.id === 'evidence' && evidenceCount > 0 ? (
      <span className="ml-1 text-[10px] bg-[#F0F0F0] text-[#666666] px-1.5 py-0.5 rounded-full">{evidenceCount}</span>
    ) : tab.id === 'connections' && connectionCount > 0 ? (
      <span className="ml-1 text-[10px] bg-[#F0F0F0] text-[#666666] px-1.5 py-0.5 rounded-full">{connectionCount}</span>
    ) : tab.id === 'insights' && insightCount > 0 ? (
      <span className="ml-1 text-[10px] bg-[#F0F0F0] text-[#666666] px-1.5 py-0.5 rounded-full">{insightCount}</span>
    ) : tab.id === 'history' && detail && detail.revision_count > 0 ? (
      <span className="ml-1 text-[10px] bg-[#F0F0F0] text-[#666666] px-1.5 py-0.5 rounded-full">{detail.revision_count}</span>
    ) : undefined,
  }))

  return (
    <DrawerShell
      onClose={onClose}
      icon={Workflow}
      entityLabel="Workflow Detail"
      title={detail?.name || 'Loading...'}
      headerExtra={
        detail ? (
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
        ) : undefined
      }
      headerRight={<BRDStatusBadge status={detail?.confirmation_status} />}
      headerActions={
        detail ? (
          <ConfirmActions
            status={detail.confirmation_status}
            onConfirm={() => onConfirm('workflow', workflowId)}
            onNeedsReview={() => onNeedsReview('workflow', workflowId)}
            size="md"
          />
        ) : undefined
      }
      tabs={drawerTabs}
      activeTab={activeTab}
      onTabChange={(id) => setActiveTab(id as TabId)}
    >
      {loading && !detail ? (
        <Spinner label="Loading workflow details..." />
      ) : detail ? (
        <>
          {activeTab === 'overview' && (
            <OverviewTab detail={detail} onViewStepDetail={onViewStepDetail} onEnrich={handleEnrich} enriching={enriching} />
          )}
          {activeTab === 'evidence' && <EvidenceTab evidence={detail.evidence} />}
          {activeTab === 'connections' && <ConnectionsTab detail={detail} />}
          {activeTab === 'insights' && <InsightsTab insights={detail.insights} />}
          {activeTab === 'history' && <HistoryTab revisions={detail.revisions} />}
          {activeTab === 'who_knows' && (
            <WhoHasTheData
              topics={[
                'process', 'workflow', 'operations',
                ...inferTopicsFromText(detail.name + ' ' + (detail.description || '')),
              ]}
              stakeholders={stakeholders}
              evidence={[]}
            />
          )}
        </>
      ) : (
        <div className="text-center py-8">
          <p className="text-[13px] text-[#666666]">Failed to load workflow details.</p>
        </div>
      )}
    </DrawerShell>
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
  const hasEnrichment = detail.enriched_step_count > 0

  return (
    <div className="space-y-6">
      {/* Description */}
      {detail.description && (
        <div className="bg-[#F4F4F4] border border-border rounded-xl px-4 py-3">
          <p className="text-[13px] text-text-body leading-relaxed">{detail.description}</p>
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

      {/* Enrich with AI button */}
      {!hasEnrichment && (
        <button
          onClick={onEnrich}
          disabled={enriching}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-[13px] font-medium text-white bg-brand-primary hover:bg-[#25785A] rounded-xl transition-colors disabled:opacity-50"
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
    <div className="border border-border rounded-xl overflow-hidden">
      <div className="px-4 py-3 bg-[#0A1E2F]">
        <div className="flex items-center gap-1.5">
          <TrendingDown className="w-3.5 h-3.5 text-brand-primary" />
          <span className="text-[11px] font-semibold text-white uppercase tracking-wide">
            ROI Summary
          </span>
        </div>
      </div>
      <div className="px-4 py-4">
        {/* Time comparison bars */}
        <div className="space-y-2 mb-4">
          <TimeBar label="Current" minutes={roi.current_total_minutes} max={roi.current_total_minutes} color="bg-text-placeholder" />
          <TimeBar label="Future" minutes={roi.future_total_minutes} max={roi.current_total_minutes} color="bg-brand-primary" />
        </div>

        {/* Savings row */}
        <div className="grid grid-cols-3 gap-3 pt-3 border-t border-[#F0F0F0]">
          <div className="text-center">
            <p className="text-[18px] font-bold text-[#25785A]">{roi.time_saved_percent}%</p>
            <p className="text-[10px] text-text-placeholder uppercase">Time Saved</p>
          </div>
          <div className="text-center">
            <p className="text-[18px] font-bold text-text-body">{roi.time_saved_minutes}min</p>
            <p className="text-[10px] text-text-placeholder uppercase">Per Run</p>
          </div>
          <div className="text-center">
            <p className="text-[18px] font-bold text-text-body">
              ${roi.cost_saved_per_year > 0 ? formatCurrency(roi.cost_saved_per_year) : '—'}
            </p>
            <p className="text-[10px] text-text-placeholder uppercase">Saved / Year</p>
          </div>
        </div>

        {/* Automation coverage */}
        {roi.steps_total > 0 && (
          <div className="mt-3 pt-3 border-t border-[#F0F0F0]">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[11px] text-[#666666]">Automation Coverage</span>
              <span className="text-[11px] font-medium text-text-body">
                {roi.steps_automated}/{roi.steps_total} steps
              </span>
            </div>
            <div className="h-2 bg-[#F0F0F0] rounded-full overflow-hidden">
              <div
                className="h-full bg-brand-primary rounded-full transition-all"
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
      <span className="text-[12px] font-medium text-text-body w-16 text-right">{minutes}min</span>
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
      <h4 className="text-[11px] font-medium text-text-placeholder uppercase tracking-wide mb-2 flex items-center gap-1.5">
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
                isClean ? 'border-border bg-white' : 'border-border bg-[#F4F4F4]'
              }`}
            >
              <StatIcon className={`w-4 h-4 mx-auto mb-1 ${isClean ? 'text-brand-primary' : 'text-text-placeholder'}`} />
              <p className={`text-[14px] font-bold ${isClean ? 'text-brand-primary' : 'text-text-body'}`}>
                {isClean ? '✓' : stat.value}
              </p>
              <p className="text-[10px] text-text-placeholder">{stat.label}</p>
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
      <h4 className="text-[11px] font-medium text-text-placeholder uppercase tracking-wide mb-2 flex items-center gap-1.5">
        <Layers className="w-3.5 h-3.5" />
        Steps ({currentSteps.length + futureSteps.length})
      </h4>
      <div className="border border-border rounded-xl overflow-hidden">
        {currentSteps.length > 0 && (
          <>
            <div className="px-3 py-1.5 bg-[#F4F4F4] border-b border-border">
              <span className="text-[10px] font-medium text-[#666666] uppercase">Current State</span>
            </div>
            {currentSteps.map((step) => (
              <StepRow key={step.id} step={step} onClick={onViewStepDetail ? () => onViewStepDetail(step.id) : undefined} />
            ))}
          </>
        )}
        {futureSteps.length > 0 && (
          <>
            <div className="px-3 py-1.5 bg-[#E8F5E9]/50 border-b border-border border-t border-t-border">
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
    semi_automated: { dot: 'bg-text-placeholder' },
    fully_automated: { dot: 'bg-brand-primary' },
  }
  const c = automationConfig[step.automation_level] || automationConfig.manual

  return (
    <button
      onClick={onClick}
      disabled={!onClick}
      className="w-full flex items-center gap-2.5 px-3 py-2 border-b border-[#F0F0F0] last:border-0 text-left hover:bg-[#F4F4F4]/50 transition-colors disabled:hover:bg-transparent"
    >
      <span className="text-[11px] font-bold text-text-placeholder w-5 text-center shrink-0">
        {step.step_index}
      </span>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot} shrink-0`} />
      <span className="text-[12px] text-text-body truncate flex-1">{step.label}</span>
      {step.time_minutes != null && (
        <span className="text-[10px] text-text-placeholder shrink-0">{step.time_minutes}min</span>
      )}
    </button>
  )
}

// ============================================================================
// Strategic Unlocks Card
// ============================================================================

// ============================================================================
// Evidence Tab
// ============================================================================

const SOURCE_LABELS: Record<string, string> = {
  signal: 'Signal',
  research: 'Research',
  inferred: 'Inferred',
}

function EvidenceTab({ evidence }: { evidence: Array<Record<string, unknown>> }) {
  if (!evidence || evidence.length === 0) {
    return (
      <div className="text-center py-8">
        <FileText className="w-8 h-8 text-border mx-auto mb-3" />
        <p className="text-[13px] text-[#666666] mb-1">No evidence sources</p>
        <p className="text-[12px] text-text-placeholder">
          Process more signals to build evidence for this workflow.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <p className="text-[11px] font-medium text-text-placeholder uppercase tracking-wide">
        {evidence.length} source{evidence.length !== 1 ? 's' : ''}
      </p>
      {evidence.map((item, idx) => {
        const excerpt = (item.excerpt as string) || ''
        const sourceType = (item.source_type as string) || 'inferred'
        const rationale = (item.rationale as string) || ''
        return (
          <div
            key={idx}
            className="border border-border rounded-xl px-4 py-3"
          >
            <div className="text-[13px] text-text-body leading-relaxed italic [&_p]:mb-1 [&_p:last-child]:mb-0 [&_ul]:my-1 [&_ol]:my-1 [&_li]:ml-2 [&_strong]:font-semibold [&_strong]:not-italic">
              <Markdown content={`\u201C${excerpt}\u201D`} />
            </div>
            <div className="flex items-center gap-2 mt-2">
              <span className="text-[10px] font-medium uppercase px-1.5 py-0.5 rounded bg-[#F0F0F0] text-[#666666]">
                {SOURCE_LABELS[sourceType] || sourceType}
              </span>
              {rationale && (
                <span className="text-[11px] text-text-placeholder">{rationale}</span>
              )}
            </div>
          </div>
        )
      })}
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
        <Link2 className="w-8 h-8 text-border mx-auto mb-3" />
        <p className="text-[13px] text-[#666666] mb-1">No connections found</p>
        <p className="text-[12px] text-text-placeholder">
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
                <span className="text-[13px] text-text-body font-medium">{p.name}</span>
                {p.role && (
                  <span className="text-[11px] text-text-placeholder">{p.role}</span>
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
                  <span className="text-[13px] text-text-body line-clamp-2 flex-1">{d.description}</span>
                </div>
                <div className="flex items-center gap-2 mt-1">
                  {d.severity && (
                    <span className="text-[10px] text-text-placeholder">Severity: {d.severity}</span>
                  )}
                  {d.vision_alignment && (
                    <span className="text-[10px] text-text-placeholder">Vision: {d.vision_alignment}</span>
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
                    ? <CheckCircle2 className="w-3.5 h-3.5 text-brand-primary flex-shrink-0" />
                    : <Circle className="w-3.5 h-3.5 text-border flex-shrink-0" />
                  }
                  <span className="text-[13px] text-text-body font-medium">{f.name}</span>
                  {f.category && (
                    <span className="text-[10px] text-text-placeholder bg-[#F0F0F0] px-1.5 py-0.5 rounded">{f.category}</span>
                  )}
                </div>
                {f.priority_group && (
                  <span className="text-[10px] text-text-placeholder ml-5.5 mt-0.5 block">
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
                <span className="text-[13px] text-text-body font-medium">{de.name}</span>
                <span className="text-[10px] text-text-placeholder bg-[#F0F0F0] px-1.5 py-0.5 rounded">
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

// ============================================================================
// Insights Tab
// ============================================================================

function InsightsTab({ insights }: { insights: WorkflowInsight[] }) {
  if (!insights || insights.length === 0) {
    return (
      <div className="text-center py-8">
        <CheckCircle2 className="w-8 h-8 text-brand-primary mx-auto mb-3" />
        <p className="text-[13px] text-[#666666] mb-1">No issues detected</p>
        <p className="text-[12px] text-text-placeholder">
          This workflow is well-connected and balanced.
        </p>
      </div>
    )
  }

  const typeConfig: Record<string, { icon: typeof Info; borderColor: string; iconColor: string }> = {
    gap: { icon: Info, borderColor: 'border-border', iconColor: 'text-text-placeholder' },
    warning: { icon: AlertTriangle, borderColor: 'border-border', iconColor: 'text-text-placeholder' },
    opportunity: { icon: Sparkles, borderColor: 'border-brand-primary/30', iconColor: 'text-brand-primary' },
    strength: { icon: CheckCircle2, borderColor: 'border-brand-primary/30', iconColor: 'text-brand-primary' },
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
                <p className="text-[13px] text-text-body leading-relaxed">{insight.message}</p>
                {insight.suggestion && (
                  <p className="text-[12px] text-text-placeholder mt-1">{insight.suggestion}</p>
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
        <Clock className="w-8 h-8 text-border mx-auto mb-3" />
        <p className="text-[13px] text-[#666666] mb-1">No revision history</p>
        <p className="text-[12px] text-text-placeholder">
          Changes will be tracked here as signals are processed.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {revisions.map((rev, i) => {
        return (
          <div key={i} className="border border-border rounded-xl px-4 py-3">
            <div className="flex items-center gap-2 mb-1">
              <span className={`text-[10px] font-medium uppercase px-1.5 py-0.5 rounded ${REVISION_TYPE_COLORS[rev.revision_type] || REVISION_TYPE_COLORS.updated}`}>
                {rev.revision_type}
              </span>
              <span className="text-[10px] text-text-placeholder">
                {rev.created_at ? formatRelativeTime(rev.created_at) : ''}
              </span>
              <span className="text-[10px] text-text-placeholder">
                by {formatRevisionAuthor(rev.created_by)}
              </span>
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

function formatCurrency(amount: number): string {
  if (amount >= 1000) {
    return `${(amount / 1000).toFixed(1)}k`
  }
  return amount.toFixed(0)
}
