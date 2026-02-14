'use client'

import { useState, useEffect, useMemo } from 'react'
import {
  X,
  AlertTriangle,
  Target,
  BarChart3,
  FileText,
  Clock,
  Users,
  Puzzle,
  Link2,
  ChevronDown,
  ChevronRight,
  Workflow,
  Sparkles,
  CheckCircle2,
  Circle,
  Info,
} from 'lucide-react'
import { BRDStatusBadge } from './StatusBadge'
import { ConfirmActions } from './ConfirmActions'
import { EvidenceBlock } from './EvidenceBlock'
import { getBRDDriverDetail } from '@/lib/api'
import type {
  BusinessDriver,
  BusinessDriverDetail,
  RevisionEntry,
  AssociatedPersona,
  VisionAlignment,
} from '@/types/workspace'

type DriverType = 'pain' | 'goal' | 'kpi'
type TabId = 'intelligence' | 'evidence' | 'connections' | 'history'

interface BusinessDriverDetailDrawerProps {
  driverId: string
  driverType: DriverType
  projectId: string
  initialData: BusinessDriver
  onClose: () => void
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
}

const TYPE_CONFIG: Record<DriverType, { icon: typeof AlertTriangle; color: string; label: string }> = {
  pain: { icon: AlertTriangle, color: 'text-red-400', label: 'Pain Point' },
  goal: { icon: Target, color: '#3FAF7A', label: 'Business Goal' },
  kpi: { icon: BarChart3, color: 'text-gray-500', label: 'Success Metric' },
}

const TABS: { id: TabId; label: string; icon: typeof FileText }[] = [
  { id: 'intelligence', label: 'Intelligence', icon: Sparkles },
  { id: 'evidence', label: 'Evidence', icon: FileText },
  { id: 'connections', label: 'Connections', icon: Link2 },
  { id: 'history', label: 'History', icon: Clock },
]

export function BusinessDriverDetailDrawer({
  driverId,
  driverType,
  projectId,
  initialData,
  onClose,
  onConfirm,
  onNeedsReview,
}: BusinessDriverDetailDrawerProps) {
  const [activeTab, setActiveTab] = useState<TabId>('intelligence')
  const [detail, setDetail] = useState<BusinessDriverDetail | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getBRDDriverDetail(projectId, driverId)
      .then((data) => {
        if (!cancelled) setDetail(data)
      })
      .catch((err) => {
        console.error('Failed to load driver detail:', err)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [projectId, driverId])

  const config = TYPE_CONFIG[driverType]
  const Icon = config.icon

  const connectionCount = useMemo(() => {
    if (detail) {
      return (detail.associated_personas?.length || 0) +
        (detail.associated_features?.length || 0) +
        (detail.related_drivers?.length || 0)
    }
    return (initialData.linked_persona_count ?? 0) +
      (initialData.linked_feature_count ?? 0) +
      (initialData.linked_workflow_count ?? 0)
  }, [detail, initialData])

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
              <Icon className={`w-5 h-5 mt-0.5 flex-shrink-0 ${config.color}`} />
              <div className="min-w-0">
                <p className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-1">
                  {config.label}
                </p>
                <h2 className="text-[15px] font-semibold text-[#333333] line-clamp-2 leading-snug">
                  {initialData.description}
                </h2>
              </div>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <BRDStatusBadge status={initialData.confirmation_status} />
              <button
                onClick={onClose}
                className="p-1.5 rounded-md text-[#999999] hover:text-[#666666] hover:bg-[#F0F0F0] transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Confirm/Review actions */}
          <div className="mt-3">
            <ConfirmActions
              status={initialData.confirmation_status}
              onConfirm={() => onConfirm('business_driver', driverId)}
              onNeedsReview={() => onNeedsReview('business_driver', driverId)}
              size="md"
            />
          </div>

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
          {activeTab === 'intelligence' && (
            <IntelligenceTab
              driverType={driverType}
              initialData={initialData}
              detail={detail}
              loading={loading}
            />
          )}
          {activeTab === 'evidence' && (
            <EvidenceTab
              evidence={detail?.evidence || initialData.evidence || []}
              loading={loading}
            />
          )}
          {activeTab === 'connections' && (
            <ConnectionsTab
              detail={detail}
              initialData={initialData}
              loading={loading}
            />
          )}
          {activeTab === 'history' && (
            <HistoryTab
              revisions={detail?.revisions || []}
              loading={loading}
            />
          )}
        </div>
      </div>
    </>
  )
}

// ============================================================================
// Intelligence Tab (replaces Details)
// ============================================================================

function IntelligenceTab({
  driverType,
  initialData,
  detail,
  loading,
}: {
  driverType: DriverType
  initialData: BusinessDriver
  detail: BusinessDriverDetail | null
  loading: boolean
}) {
  const d = detail || initialData

  // Build narrative from available data
  const narrative = useMemo(() => buildNarrative(driverType, d), [driverType, d])
  const score = d.relatability_score ?? 0
  const va = d.vision_alignment

  // Detect missing data
  const missingData = useMemo(() => {
    const items: string[] = []
    if (!d.linked_persona_count && !(detail?.associated_personas?.length))
      items.push('Not linked to any persona — consider mapping who experiences this')
    if (!d.linked_workflow_count)
      items.push('Not linked to any workflow — consider mapping where this occurs')
    if (!d.linked_feature_count && !(detail?.associated_features?.length))
      items.push('Not linked to any feature — consider mapping what addresses this')
    if (driverType === 'kpi') {
      if (!d.baseline_value) items.push('Missing baseline value')
      if (!d.target_value) items.push('Missing target value')
      if (!d.measurement_method) items.push('Missing measurement method')
    }
    if (driverType === 'pain' && !d.severity) items.push('Missing severity assessment')
    if (driverType === 'goal' && !d.success_criteria) items.push('Missing success criteria')
    return items
  }, [d, detail, driverType])

  return (
    <div className="space-y-6">
      {/* AI Narrative */}
      {narrative && (
        <div className="bg-[#F4F4F4] border border-[#E5E5E5] rounded-xl px-4 py-3">
          <p className="text-[13px] text-[#333333] leading-relaxed">{narrative}</p>
        </div>
      )}

      {/* Relatability Score + Vision Alignment */}
      <div className="flex items-center gap-4">
        <div className="flex-1">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-medium text-[#999999] uppercase tracking-wide">
              Relevance Score
            </span>
            <span className="text-[12px] font-semibold text-[#333333]">{score.toFixed(1)}</span>
          </div>
          <div className="h-2 bg-[#F0F0F0] rounded-full overflow-hidden">
            <div
              className="h-full bg-[#3FAF7A] rounded-full transition-all duration-500"
              style={{ width: `${Math.min((score / 30) * 100, 100)}%` }}
            />
          </div>
        </div>
        {va && <VisionAlignmentBadge alignment={va} />}
      </div>

      {/* Missing Data Callouts */}
      {missingData.length > 0 && (
        <div className="space-y-1.5">
          {missingData.map((msg, i) => (
            <div
              key={i}
              className="flex items-start gap-2 text-[12px] text-[#666666] bg-[#F4F4F4] border border-[#E5E5E5] rounded-lg px-3 py-2"
            >
              <Info className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 text-[#999999]" />
              {msg}
            </div>
          ))}
        </div>
      )}

      {/* Type-specific fields */}
      <div>
        <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-3">
          {driverType === 'pain' ? 'Pain Details' : driverType === 'goal' ? 'Goal Details' : 'Metric Details'}
        </h4>

        {driverType === 'pain' && (
          <div className="space-y-3">
            <FieldRow label="Severity" value={d.severity} badge />
            <FieldRow label="Business Impact" value={d.business_impact} />
            <FieldRow label="Affected Users" value={d.affected_users} />
            <FieldRow label="Current Workaround" value={d.current_workaround} />
            <FieldRow label="Frequency" value={d.frequency} />
          </div>
        )}

        {driverType === 'goal' && (
          <div className="space-y-3">
            <FieldRow label="Success Criteria" value={d.success_criteria} />
            <FieldRow label="Owner" value={d.owner} />
            <FieldRow label="Timeframe" value={d.goal_timeframe} />
            <FieldRow label="Dependencies" value={d.dependencies} />
          </div>
        )}

        {driverType === 'kpi' && (
          <div className="space-y-3">
            <KPIField label="Baseline" value={d.baseline_value} />
            <KPIField label="Target" value={d.target_value} />
            <KPIField label="Measurement Method" value={d.measurement_method} />
            <KPIField label="Tracking Frequency" value={d.tracking_frequency} />
            <KPIField label="Data Source" value={d.data_source} />
            <KPIField label="Responsible Team" value={d.responsible_team} />
          </div>
        )}
      </div>

      {loading && !detail && (
        <div className="text-center py-4">
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-[#3FAF7A] mx-auto" />
          <p className="text-[12px] text-[#999999] mt-2">Loading details...</p>
        </div>
      )}
    </div>
  )
}

function buildNarrative(driverType: DriverType, d: BusinessDriver | BusinessDriverDetail): string | null {
  const parts: string[] = []
  const desc = d.description

  if (driverType === 'pain') {
    parts.push(`This pain point`)
    if ('associated_personas' in d && (d as BusinessDriverDetail).associated_personas?.length) {
      parts.push(`affects ${(d as BusinessDriverDetail).associated_personas.map((p: AssociatedPersona) => p.name).join(', ')}`)
    } else if ('associated_persona_names' in d && (d as BusinessDriver).associated_persona_names?.length) {
      parts.push(`affects ${(d as BusinessDriver).associated_persona_names!.join(', ')}`)
    }
    if (d.severity) parts.push(`with ${d.severity.toLowerCase()} severity`)
    if (d.business_impact) parts.push(`— ${d.business_impact}`)
    if (d.current_workaround) parts.push(`Current workaround: ${d.current_workaround}`)
  } else if (driverType === 'goal') {
    parts.push(`This business goal`)
    if (d.owner) parts.push(`is owned by ${d.owner}`)
    if (d.goal_timeframe) parts.push(`with a target timeframe of ${d.goal_timeframe}`)
    if (d.success_criteria) parts.push(`Success criteria: ${d.success_criteria}`)
  } else {
    parts.push(`This KPI`)
    if (d.baseline_value && d.target_value) {
      parts.push(`tracks from ${d.baseline_value} to ${d.target_value}`)
    } else if (d.target_value) {
      parts.push(`targets ${d.target_value}`)
    }
    if (d.measurement_method) parts.push(`measured via ${d.measurement_method}`)
    if (d.tracking_frequency) parts.push(`tracked ${d.tracking_frequency}`)
    if (d.responsible_team) parts.push(`by ${d.responsible_team}`)
  }

  if (parts.length <= 1) return null

  const linked = d.linked_feature_count ?? 0
  if (linked > 0) {
    parts.push(`It is addressed by ${linked} feature${linked > 1 ? 's' : ''}.`)
  }

  return parts.join(' ').replace(/\s+/g, ' ').trim() + '.'
}

function VisionAlignmentBadge({ alignment }: { alignment: VisionAlignment }) {
  const config: Record<string, { bg: string; text: string; label: string }> = {
    high: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]', label: 'High alignment' },
    medium: { bg: 'bg-[#F0F0F0]', text: 'text-[#666666]', label: 'Medium alignment' },
    low: { bg: 'bg-[#F0F0F0]', text: 'text-[#999999]', label: 'Low alignment' },
    unrelated: { bg: 'bg-[#F0F0F0]', text: 'text-[#999999]', label: 'Unrelated' },
  }
  const c = config[alignment] || config.low
  return (
    <div className="flex-shrink-0 text-center">
      <span className="text-[10px] font-medium text-[#999999] uppercase tracking-wide block mb-1">Vision</span>
      <span className={`inline-flex px-2.5 py-1 text-[11px] font-medium rounded-full ${c.bg} ${c.text}`}>
        {c.label}
      </span>
    </div>
  )
}

// ============================================================================
// Connections Tab (NEW)
// ============================================================================

function ConnectionsTab({
  detail,
  initialData,
  loading,
}: {
  detail: BusinessDriverDetail | null
  initialData: BusinessDriver
  loading: boolean
}) {
  const personas = detail?.associated_personas || []
  const features = detail?.associated_features || []
  const relatedDrivers = detail?.related_drivers || []
  const workflowCount = (detail || initialData).linked_workflow_count ?? 0

  if (loading && !detail) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-[#3FAF7A] mx-auto" />
        <p className="text-[12px] text-[#999999] mt-2">Loading connections...</p>
      </div>
    )
  }

  const isEmpty = personas.length === 0 && features.length === 0 && relatedDrivers.length === 0 && workflowCount === 0

  if (isEmpty) {
    return (
      <div className="text-center py-8">
        <Link2 className="w-8 h-8 text-[#E5E5E5] mx-auto mb-3" />
        <p className="text-[13px] text-[#666666] mb-1">No connections found</p>
        <p className="text-[12px] text-[#999999]">
          Run enrichment or manually link entities to build the relationship graph.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Actors */}
      {personas.length > 0 && (
        <ConnectionGroup
          icon={Users}
          title="Actors"
          count={personas.length}
        >
          {personas.map((p) => (
            <ConnectionItem
              key={p.id}
              name={p.name}
              subtitle={p.role || undefined}
              reason={p.association_reason}
            />
          ))}
        </ConnectionGroup>
      )}

      {/* Features */}
      {features.length > 0 && (
        <ConnectionGroup
          icon={Puzzle}
          title="Features"
          count={features.length}
        >
          {features.map((f) => (
            <ConnectionItem
              key={f.id}
              name={f.name}
              subtitle={f.category || undefined}
              reason={f.association_reason}
              confirmed={f.confirmation_status === 'confirmed_consultant' || f.confirmation_status === 'confirmed_client'}
            />
          ))}
        </ConnectionGroup>
      )}

      {/* Workflows */}
      {workflowCount > 0 && (
        <ConnectionGroup
          icon={Workflow}
          title="Workflow Steps"
          count={workflowCount}
        >
          <p className="text-[12px] text-[#999999] px-3 py-2">
            {workflowCount} workflow step{workflowCount > 1 ? 's' : ''} linked via enrichment analysis.
          </p>
        </ConnectionGroup>
      )}

      {/* Related Drivers */}
      {relatedDrivers.length > 0 && (
        <ConnectionGroup
          icon={Link2}
          title="Related Drivers"
          count={relatedDrivers.length}
        >
          {relatedDrivers.map((r) => (
            <div key={r.id} className="px-3 py-2 border-b border-[#F0F0F0] last:border-0">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-medium uppercase px-1.5 py-0.5 rounded bg-[#F0F0F0] text-[#666666]">
                  {r.driver_type}
                </span>
                <span className="text-[13px] text-[#333333] line-clamp-1">{r.description}</span>
              </div>
              {r.relationship && (
                <p className="text-[11px] text-[#999999] mt-1 pl-0.5">{r.relationship}</p>
              )}
            </div>
          ))}
        </ConnectionGroup>
      )}
    </div>
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

function ConnectionItem({
  name,
  subtitle,
  reason,
  confirmed,
}: {
  name: string
  subtitle?: string
  reason?: string
  confirmed?: boolean
}) {
  return (
    <div className="px-3 py-2.5 border-b border-[#F0F0F0] last:border-0">
      <div className="flex items-center gap-2">
        {confirmed !== undefined && (
          confirmed
            ? <CheckCircle2 className="w-3.5 h-3.5 text-[#3FAF7A] flex-shrink-0" />
            : <Circle className="w-3.5 h-3.5 text-[#E5E5E5] flex-shrink-0" />
        )}
        <span className="text-[13px] text-[#333333] font-medium">{name}</span>
        {subtitle && (
          <span className="text-[11px] text-[#999999]">{subtitle}</span>
        )}
      </div>
      {reason && (
        <p className="text-[11px] text-[#999999] mt-0.5 pl-5">{reason}</p>
      )}
    </div>
  )
}

// ============================================================================
// Evidence Tab
// ============================================================================

function EvidenceTab({
  evidence,
  loading,
}: {
  evidence: import('@/types/workspace').BRDEvidence[]
  loading: boolean
}) {
  if (loading && evidence.length === 0) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-[#3FAF7A] mx-auto" />
        <p className="text-[12px] text-[#999999] mt-2">Loading evidence...</p>
      </div>
    )
  }

  if (evidence.length === 0) {
    return (
      <p className="text-[13px] text-[#999999] italic py-4">No evidence sources linked to this item.</p>
    )
  }

  return <EvidenceBlock evidence={evidence} maxItems={100} />
}

// ============================================================================
// History Tab
// ============================================================================

function HistoryTab({
  revisions,
  loading,
}: {
  revisions: RevisionEntry[]
  loading: boolean
}) {
  if (loading && revisions.length === 0) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-[#3FAF7A] mx-auto" />
        <p className="text-[12px] text-[#999999] mt-2">Loading history...</p>
      </div>
    )
  }

  if (revisions.length === 0) {
    return (
      <p className="text-[13px] text-[#999999] italic py-4">No revision history available.</p>
    )
  }

  return (
    <div className="space-y-3">
      {revisions.map((rev, idx) => (
        <RevisionCard key={idx} revision={rev} />
      ))}
    </div>
  )
}

function RevisionCard({ revision }: { revision: RevisionEntry }) {
  const [expanded, setExpanded] = useState(false)
  const hasChanges = revision.changes && Object.keys(revision.changes).length > 0

  const typeColors: Record<string, string> = {
    created: 'bg-[#E8F5E9] text-[#25785A]',
    enriched: 'bg-[#F0F0F0] text-[#666666]',
    updated: 'bg-[#F0F0F0] text-[#666666]',
    merged: 'bg-[#F0F0F0] text-[#666666]',
  }
  const typeCls = typeColors[revision.revision_type] || 'bg-[#F0F0F0] text-[#666666]'

  const timeAgo = formatRelativeTime(revision.created_at)

  return (
    <div className="bg-[#F4F4F4] border border-[#E5E5E5] rounded-xl px-3 py-2.5">
      <div className="flex items-center gap-2 mb-1">
        <span className={`inline-flex px-1.5 py-0.5 text-[10px] font-medium rounded ${typeCls}`}>
          {revision.revision_type}
        </span>
        <span className="text-[11px] text-[#999999]">{timeAgo}</span>
        {revision.created_by && (
          <span className="text-[11px] text-[#999999]">by {revision.created_by}</span>
        )}
      </div>
      {revision.diff_summary && (
        <p className="text-[12px] text-[#666666] leading-relaxed">
          {revision.diff_summary}
        </p>
      )}
      {hasChanges && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-1.5 flex items-center gap-1 text-[11px] text-[#999999] hover:text-[#666666] transition-colors"
        >
          {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
          Field changes
        </button>
      )}
      {expanded && revision.changes && (
        <div className="mt-2 space-y-1 pl-2 border-l-2 border-[#E5E5E5]">
          {Object.entries(revision.changes).map(([field, change]) => (
            <div key={field} className="text-[11px]">
              <span className="font-medium text-[#666666]">{field}:</span>{' '}
              {typeof change === 'object' && change !== null && 'old' in change && 'new' in change ? (
                <>
                  <span className="text-red-400 line-through">{String((change as { old: unknown }).old || '—')}</span>
                  {' → '}
                  <span className="text-[#3FAF7A]">{String((change as { new: unknown }).new || '—')}</span>
                </>
              ) : (
                <span className="text-[#666666]">{String(change)}</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Shared helpers
// ============================================================================

function FieldRow({ label, value, badge }: { label: string; value?: string | null; badge?: boolean }) {
  if (!value) return null
  return (
    <div className="flex items-start gap-3">
      <span className="text-[12px] font-medium text-[#999999] min-w-[120px] pt-0.5">{label}</span>
      {badge ? (
        <SeverityBadge value={value} />
      ) : (
        <span className="text-[13px] text-[#333333] leading-relaxed">{value}</span>
      )}
    </div>
  )
}

function KPIField({ label, value }: { label: string; value?: string | null }) {
  const isMissing = !value
  return (
    <div className={`flex items-start gap-3 ${isMissing ? 'rounded-lg border border-dashed border-[#E5E5E5] bg-[#F4F4F4] px-3 py-2 -mx-3' : ''}`}>
      <span className="text-[12px] font-medium text-[#999999] min-w-[140px] pt-0.5">{label}</span>
      {isMissing ? (
        <span className="text-[12px] text-[#999999] italic">Data needed</span>
      ) : (
        <span className="text-[13px] text-[#333333] leading-relaxed">{value}</span>
      )}
    </div>
  )
}

function SeverityBadge({ value }: { value: string }) {
  const isHigh = value.toLowerCase() === 'critical' || value.toLowerCase() === 'high'
  return (
    <span className={`inline-flex px-2 py-0.5 text-[11px] font-medium rounded-full ${
      isHigh ? 'bg-red-100 text-red-700' : 'bg-[#F0F0F0] text-[#666666]'
    }`}>
      {value}
    </span>
  )
}

function formatRelativeTime(dateStr: string): string {
  if (!dateStr) return ''
  try {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    if (diffMins < 1) return 'just now'
    if (diffMins < 60) return `${diffMins}m ago`
    const diffHours = Math.floor(diffMins / 60)
    if (diffHours < 24) return `${diffHours}h ago`
    const diffDays = Math.floor(diffHours / 24)
    if (diffDays < 30) return `${diffDays}d ago`
    return date.toLocaleDateString()
  } catch {
    return dateStr
  }
}
