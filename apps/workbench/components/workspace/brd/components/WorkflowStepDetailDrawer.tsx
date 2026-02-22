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
  ArrowRight,
  Layers,
  FileText,
} from 'lucide-react'
import { DrawerShell, type DrawerTab } from '@/components/ui/DrawerShell'
import { Spinner } from '@/components/ui/Spinner'
import { BRDStatusBadge } from './StatusBadge'
import { ConfirmActions } from './ConfirmActions'
import { Markdown } from '@/components/ui/Markdown'
import { ConnectionGroup } from '@/components/ui/ConnectionGroup'
import { formatRelativeTime, formatRevisionAuthor, REVISION_TYPE_COLORS } from '@/lib/date-utils'
import { getWorkflowStepDetail } from '@/lib/api'
import type {
  WorkflowStepDetail,
  WorkflowStepSummary,
  StepInsight,
  LinkedBusinessDriver,
  LinkedFeature,
  LinkedDataEntity,
  RevisionEntry,
  BRDEvidence,
} from '@/types/workspace'

type TabId = 'overview' | 'evidence' | 'connections' | 'insights' | 'history'

interface WorkflowStepDetailDrawerProps {
  stepId: string
  projectId: string
  onClose: () => void
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
}

const AUTOMATION_LABELS: Record<string, string> = {
  manual: 'Manual',
  semi_automated: 'Semi-automated',
  fully_automated: 'Fully automated',
}

export function WorkflowStepDetailDrawer({
  stepId,
  projectId,
  onClose,
  onConfirm,
  onNeedsReview,
}: WorkflowStepDetailDrawerProps) {
  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [detail, setDetail] = useState<WorkflowStepDetail | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getWorkflowStepDetail(projectId, stepId)
      .then((data) => {
        if (!cancelled) setDetail(data)
      })
      .catch((err) => {
        console.error('Failed to load step detail:', err)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [projectId, stepId])

  const connectionCount = useMemo(() => {
    if (!detail) return 0
    return (detail.business_drivers?.length || 0) +
      (detail.features?.length || 0) +
      (detail.data_entities?.length || 0) +
      (detail.actor ? 1 : 0)
  }, [detail])

  const evidenceCount = detail?.evidence?.length || 0
  const insightCount = detail?.insights?.length || 0

  const tabs: DrawerTab[] = [
    { id: 'overview', label: 'Overview', icon: Layers },
    {
      id: 'evidence',
      label: 'Evidence',
      icon: FileText,
      badge: evidenceCount > 0 ? (
        <span className="ml-1 text-[10px] bg-[#F0F0F0] text-[#666666] px-1.5 py-0.5 rounded-full">
          {evidenceCount}
        </span>
      ) : undefined,
    },
    {
      id: 'connections',
      label: 'Connections',
      icon: Link2,
      badge: connectionCount > 0 ? (
        <span className="ml-1 text-[10px] bg-[#F0F0F0] text-[#666666] px-1.5 py-0.5 rounded-full">
          {connectionCount}
        </span>
      ) : undefined,
    },
    {
      id: 'insights',
      label: 'Insights',
      icon: Sparkles,
      badge: insightCount > 0 ? (
        <span className="ml-1 text-[10px] bg-[#F0F0F0] text-[#666666] px-1.5 py-0.5 rounded-full">
          {insightCount}
        </span>
      ) : undefined,
    },
    {
      id: 'history',
      label: 'History',
      icon: Clock,
      badge: detail && detail.revision_count > 0 ? (
        <span className="ml-1 text-[10px] bg-[#F0F0F0] text-[#666666] px-1.5 py-0.5 rounded-full">
          {detail.revision_count}
        </span>
      ) : undefined,
    },
  ]

  return (
    <DrawerShell
      onClose={onClose}
      icon={Layers}
      entityLabel={detail?.workflow_name ? `Step ${detail.step_index} of ${detail.workflow_name}` : 'Workflow Step'}
      title={detail?.label || 'Loading...'}
      headerExtra={
        detail ? (
          <div className="flex items-center gap-2 mt-1.5">
            <AutomationBadge level={detail.automation_level} />
            {detail.state_type && (
              <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${
                detail.state_type === 'current'
                  ? 'bg-[#F0F0F0] text-[#666666]'
                  : 'bg-[#E8F5E9] text-[#25785A]'
              }`}>
                {detail.state_type === 'current' ? 'Current' : 'Future'}
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
            onConfirm={() => onConfirm('vp_step', stepId)}
            onNeedsReview={() => onNeedsReview('vp_step', stepId)}
            size="md"
          />
        ) : undefined
      }
      tabs={tabs}
      activeTab={activeTab}
      onTabChange={(id) => setActiveTab(id as TabId)}
    >
      {loading && !detail ? (
        <Spinner label="Loading step details..." />
      ) : detail ? (
        <>
          {activeTab === 'overview' && (
            <OverviewTab detail={detail} />
          )}
          {activeTab === 'evidence' && <EvidenceTab evidence={detail.evidence} />}
          {activeTab === 'connections' && <ConnectionsTab detail={detail} />}
          {activeTab === 'insights' && <InsightsTab insights={detail.insights} />}
          {activeTab === 'history' && <HistoryTab revisions={detail.revisions} />}
        </>
      ) : (
        <div className="text-center py-8">
          <p className="text-[13px] text-[#666666]">Failed to load step details.</p>
        </div>
      )}
    </DrawerShell>
  )
}

// ============================================================================
// Automation Badge
// ============================================================================

function AutomationBadge({ level }: { level: string }) {
  const config: Record<string, { dot: string; label: string; bg: string; text: string }> = {
    manual: { dot: 'bg-gray-400', label: 'Manual', bg: 'bg-gray-100', text: 'text-gray-600' },
    semi_automated: { dot: 'bg-[#999999]', label: 'Semi-auto', bg: 'bg-[#F0F0F0]', text: 'text-[#666666]' },
    fully_automated: { dot: 'bg-[#3FAF7A]', label: 'Automated', bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
  }
  const c = config[level] || config.manual
  return (
    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium ${c.bg} ${c.text} rounded`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      {c.label}
    </span>
  )
}

// ============================================================================
// Overview Tab
// ============================================================================

function OverviewTab({
  detail,
}: {
  detail: WorkflowStepDetail
}) {
  // Build narrative
  const narrative = useMemo(() => {
    const parts: string[] = []
    if (detail.workflow_name) {
      parts.push(`Step ${detail.step_index} of ${detail.workflow_name}: ${detail.label}.`)
    } else {
      parts.push(`${detail.label}.`)
    }
    if (detail.actor) {
      parts.push(`${detail.actor.name} performs this ${AUTOMATION_LABELS[detail.automation_level]?.toLowerCase() || detail.automation_level} step`)
      if (detail.time_minutes != null) {
        parts.push(`taking ${detail.time_minutes}min.`)
      } else {
        parts.push('.')
      }
    } else if (detail.time_minutes != null) {
      parts.push(`This ${AUTOMATION_LABELS[detail.automation_level]?.toLowerCase() || detail.automation_level} step takes ${detail.time_minutes}min.`)
    }
    if (detail.state_type === 'current' && detail.pain_description) {
      parts.push(detail.pain_description)
    } else if (detail.state_type === 'future' && detail.benefit_description) {
      parts.push(detail.benefit_description)
    }
    return parts.join(' ')
  }, [detail])

  const enrichment = detail.enrichment_data
  const hasEnrichment = detail.enrichment_status === 'enriched' && enrichment

  return (
    <div className="space-y-6">
      {/* Narrative */}
      <div className="bg-[#F4F4F4] border border-[#E5E5E5] rounded-xl px-4 py-3">
        <p className="text-[13px] text-[#333333] leading-relaxed">{narrative}</p>
      </div>

      {/* Time Comparison (if counterpart exists) */}
      {detail.counterpart_step && detail.time_delta_minutes != null && (
        <TimeComparison
          step={detail}
          counterpart={detail.counterpart_step}
          counterpartStateType={detail.counterpart_state_type}
          timeDelta={detail.time_delta_minutes}
        />
      )}

      {/* Automation Progression (if counterpart) */}
      {detail.automation_delta && (
        <div className="bg-white border border-[#E5E5E5] rounded-xl px-4 py-3">
          <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2">
            Automation Progression
          </h4>
          <div className="flex items-center gap-3">
            <AutomationBadge level={detail.automation_delta.split(' → ')[0] || 'manual'} />
            <ArrowRight className="w-4 h-4 text-[#999999]" />
            <AutomationBadge level={detail.automation_delta.split(' → ')[1] || 'manual'} />
          </div>
        </div>
      )}

      {/* Key Metrics */}
      <div className="flex flex-wrap gap-2">
        {detail.time_minutes != null && (
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium bg-[#F4F4F4] text-[#333333] rounded-lg border border-[#E5E5E5]">
            <Clock className="w-3.5 h-3.5 text-[#999999]" />
            {detail.time_minutes}min
          </span>
        )}
        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium bg-[#F4F4F4] text-[#333333] rounded-lg border border-[#E5E5E5]">
          <Zap className="w-3.5 h-3.5 text-[#999999]" />
          {AUTOMATION_LABELS[detail.automation_level] || detail.automation_level}
        </span>
        {detail.operation_type && (
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium bg-[#F4F4F4] text-[#333333] rounded-lg border border-[#E5E5E5]">
            <Database className="w-3.5 h-3.5 text-[#999999]" />
            {detail.operation_type}
          </span>
        )}
      </div>

      {/* Pain / Benefit Card */}
      {(detail.pain_description || detail.benefit_description) && (
        <div className="border border-[#E5E5E5] rounded-xl overflow-hidden">
          {detail.pain_description && (
            <div className="px-4 py-3 border-b border-[#E5E5E5] last:border-b-0">
              <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-1">Pain</h4>
              <p className="text-[13px] text-[#333333] leading-relaxed">{detail.pain_description}</p>
            </div>
          )}
          {detail.benefit_description && (
            <div className="px-4 py-3">
              <h4 className="text-[11px] font-medium text-[#25785A] uppercase tracking-wide mb-1">Benefit</h4>
              <p className="text-[13px] text-[#333333] leading-relaxed">{detail.benefit_description}</p>
            </div>
          )}
        </div>
      )}

      {/* Enrichment Section */}
      {hasEnrichment && (
        <div className="border border-[#E5E5E5] rounded-xl overflow-hidden">
          <div className="px-4 py-3 bg-[#E8F5E9] border-b border-[#E5E5E5]">
            <div className="flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-[#25785A]" />
              <span className="text-[11px] font-semibold text-[#25785A] uppercase tracking-wide">AI Analysis</span>
            </div>
          </div>
          <div className="px-4 py-3 space-y-3">
            {enrichment.narrative && (
              <p className="text-[13px] text-[#333333] leading-relaxed">{enrichment.narrative}</p>
            )}
            {enrichment.optimization_suggestions && enrichment.optimization_suggestions.length > 0 && (
              <div>
                <h5 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-1.5">
                  Optimization Suggestions
                </h5>
                <ul className="space-y-1">
                  {enrichment.optimization_suggestions.map((s, i) => (
                    <li key={i} className="text-[12px] text-[#666666] flex items-start gap-1.5">
                      <span className="text-[#3FAF7A] mt-0.5">-</span>
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {enrichment.automation_opportunity_score != null && enrichment.automation_opportunity_score > 0 && (
              <div>
                <h5 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-1.5">
                  Automation Score
                </h5>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-2 bg-[#F0F0F0] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#3FAF7A] rounded-full transition-all"
                      style={{ width: `${Math.min(enrichment.automation_opportunity_score * 100, 100)}%` }}
                    />
                  </div>
                  <span className="text-[12px] font-medium text-[#333333]">
                    {(enrichment.automation_opportunity_score * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

    </div>
  )
}

// ============================================================================
// Time Comparison
// ============================================================================

function TimeComparison({
  step,
  counterpart,
  counterpartStateType,
  timeDelta,
}: {
  step: WorkflowStepDetail
  counterpart: WorkflowStepSummary
  counterpartStateType?: string | null
  timeDelta: number
}) {
  const isCurrent = step.state_type === 'current'
  const currentTime = isCurrent ? step.time_minutes : counterpart.time_minutes
  const futureTime = isCurrent ? counterpart.time_minutes : step.time_minutes
  const maxTime = Math.max(currentTime || 0, futureTime || 0)
  const pctSaved = currentTime && currentTime > 0 ? Math.round((timeDelta / currentTime) * 100) : 0

  return (
    <div className="bg-white border border-[#E5E5E5] rounded-xl px-4 py-3">
      <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-3">
        Time Comparison
      </h4>
      <div className="space-y-2">
        {/* Current bar */}
        <div className="flex items-center gap-3">
          <span className="text-[11px] text-[#666666] w-14 shrink-0">Current</span>
          <div className="flex-1 h-3 bg-[#F0F0F0] rounded-full overflow-hidden">
            <div
              className="h-full bg-[#999999] rounded-full transition-all"
              style={{ width: maxTime > 0 ? `${((currentTime || 0) / maxTime) * 100}%` : '0%' }}
            />
          </div>
          <span className="text-[12px] font-medium text-[#333333] w-14 text-right">
            {currentTime ?? '?'}min
          </span>
        </div>
        {/* Future bar */}
        <div className="flex items-center gap-3">
          <span className="text-[11px] text-[#25785A] w-14 shrink-0">Future</span>
          <div className="flex-1 h-3 bg-[#F0F0F0] rounded-full overflow-hidden">
            <div
              className="h-full bg-[#3FAF7A] rounded-full transition-all"
              style={{ width: maxTime > 0 ? `${((futureTime || 0) / maxTime) * 100}%` : '0%' }}
            />
          </div>
          <span className="text-[12px] font-medium text-[#25785A] w-14 text-right">
            {futureTime ?? '?'}min
          </span>
        </div>
      </div>
      {timeDelta > 0 && (
        <div className="mt-2 pt-2 border-t border-[#F0F0F0]">
          <span className="text-[12px] font-medium text-[#25785A]">
            Saves {timeDelta}min ({pctSaved}%)
          </span>
        </div>
      )}
    </div>
  )
}

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
        <FileText className="w-8 h-8 text-[#E5E5E5] mx-auto mb-3" />
        <p className="text-[13px] text-[#666666] mb-1">No evidence sources</p>
        <p className="text-[12px] text-[#999999]">
          Process more signals to build evidence for this step.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <p className="text-[11px] font-medium text-[#999999] uppercase tracking-wide">
        {evidence.length} source{evidence.length !== 1 ? 's' : ''}
      </p>
      {evidence.map((item, idx) => {
        const excerpt = (item.excerpt as string) || ''
        const sourceType = (item.source_type as string) || 'inferred'
        const rationale = (item.rationale as string) || ''
        return (
          <div
            key={idx}
            className="border border-[#E5E5E5] rounded-xl px-4 py-3"
          >
            <div className="text-[13px] text-[#333333] leading-relaxed italic [&_p]:mb-1 [&_p:last-child]:mb-0 [&_ul]:my-1 [&_ol]:my-1 [&_li]:ml-2 [&_strong]:font-semibold [&_strong]:not-italic">
              <Markdown content={`\u201C${excerpt}\u201D`} />
            </div>
            <div className="flex items-center gap-2 mt-2">
              <span className="text-[10px] font-medium uppercase px-1.5 py-0.5 rounded bg-[#F0F0F0] text-[#666666]">
                {SOURCE_LABELS[sourceType] || sourceType}
              </span>
              {rationale && (
                <span className="text-[11px] text-[#999999]">{rationale}</span>
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

function ConnectionsTab({ detail }: { detail: WorkflowStepDetail }) {
  const hasActor = !!detail.actor
  const hasDrivers = detail.business_drivers.length > 0
  const hasFeatures = detail.features.length > 0
  const hasDataEntities = detail.data_entities.length > 0
  const isEmpty = !hasActor && !hasDrivers && !hasFeatures && !hasDataEntities

  if (isEmpty) {
    return (
      <div className="text-center py-8">
        <Link2 className="w-8 h-8 text-[#E5E5E5] mx-auto mb-3" />
        <p className="text-[13px] text-[#666666] mb-1">No connections found</p>
        <p className="text-[12px] text-[#999999]">
          Run enrichment or process more signals to build connections.
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
      {/* Actor */}
      {hasActor && detail.actor && (
        <ConnectionGroup icon={Users} title="Actor" count={1}>
          <div className="px-3 py-2.5">
            <div className="flex items-center gap-2">
              <span className="text-[13px] text-[#333333] font-medium">{detail.actor.name}</span>
              {detail.actor.role && (
                <span className="text-[11px] text-[#999999]">{detail.actor.role}</span>
              )}
            </div>
          </div>
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
      {!hasFeatures && detail.state_type === 'future' && (
        <div className="flex items-start gap-2 text-[12px] text-[#666666] bg-[#F4F4F4] border border-[#E5E5E5] rounded-lg px-3 py-2">
          <Info className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 text-[#999999]" />
          No features linked — how will this step be implemented?
        </div>
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

// ============================================================================
// Insights Tab
// ============================================================================

function InsightsTab({ insights }: { insights: StepInsight[] }) {
  if (!insights || insights.length === 0) {
    return (
      <div className="text-center py-8">
        <CheckCircle2 className="w-8 h-8 text-[#3FAF7A] mx-auto mb-3" />
        <p className="text-[13px] text-[#666666] mb-1">No issues detected</p>
        <p className="text-[12px] text-[#999999]">
          This step is well-connected.
        </p>
      </div>
    )
  }

  const typeConfig: Record<string, { icon: typeof Info; borderColor: string; iconColor: string }> = {
    gap: { icon: Info, borderColor: 'border-[#E5E5E5]', iconColor: 'text-[#999999]' },
    warning: { icon: AlertTriangle, borderColor: 'border-[#E5E5E5]', iconColor: 'text-[#999999]' },
    opportunity: { icon: Sparkles, borderColor: 'border-[#3FAF7A]/30', iconColor: 'text-[#3FAF7A]' },
    overlap: { icon: Layers, borderColor: 'border-[#E5E5E5]', iconColor: 'text-[#999999]' },
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
        return (
          <div key={i} className="border border-[#E5E5E5] rounded-xl px-4 py-3">
            <div className="flex items-center gap-2 mb-1">
              <span className={`text-[10px] font-medium uppercase px-1.5 py-0.5 rounded ${REVISION_TYPE_COLORS[rev.revision_type] || REVISION_TYPE_COLORS.updated}`}>
                {rev.revision_type}
              </span>
              <span className="text-[10px] text-[#999999]">
                {rev.created_at ? formatRelativeTime(rev.created_at) : ''}
              </span>
              <span className="text-[10px] text-[#999999]">
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
