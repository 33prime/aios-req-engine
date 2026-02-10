'use client'

import { useState, useEffect } from 'react'
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
  AlertCircle,
  ChevronDown,
  ChevronRight,
} from 'lucide-react'
import { BRDStatusBadge } from './StatusBadge'
import { ConfirmActions } from './ConfirmActions'
import { EvidenceBlock } from './EvidenceBlock'
import { getBRDDriverDetail } from '@/lib/api'
import type {
  BusinessDriver,
  BusinessDriverDetail,
  RevisionEntry,
} from '@/types/workspace'

type DriverType = 'pain' | 'goal' | 'kpi'
type TabId = 'details' | 'evidence' | 'history'

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
  goal: { icon: Target, color: 'text-blue-400', label: 'Business Goal' },
  kpi: { icon: BarChart3, color: 'text-purple-400', label: 'Success Metric' },
}

const TABS: { id: TabId; label: string; icon: typeof FileText }[] = [
  { id: 'details', label: 'Details', icon: FileText },
  { id: 'evidence', label: 'Evidence', icon: FileText },
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
  const [activeTab, setActiveTab] = useState<TabId>('details')
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
        <div className="flex-shrink-0 border-b border-gray-100 px-6 py-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3 min-w-0 flex-1">
              <Icon className={`w-5 h-5 mt-0.5 flex-shrink-0 ${config.color}`} />
              <div className="min-w-0">
                <p className="text-[11px] font-medium text-gray-400 uppercase tracking-wide mb-1">
                  {config.label}
                </p>
                <h2 className="text-[15px] font-semibold text-[#37352f] line-clamp-2 leading-snug">
                  {initialData.description}
                </h2>
              </div>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <BRDStatusBadge status={initialData.confirmation_status} />
              <button
                onClick={onClose}
                className="p-1.5 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
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
                      ? 'border-[#009b87] text-[#009b87]'
                      : 'border-transparent text-gray-400 hover:text-gray-600'
                  }`}
                >
                  <TabIcon className="w-3.5 h-3.5" />
                  {tab.label}
                  {tab.id === 'history' && detail && detail.revision_count > 0 && (
                    <span className="ml-1 text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded-full">
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
          {activeTab === 'details' && (
            <DetailsTab
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
// Details Tab
// ============================================================================

function DetailsTab({
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

  return (
    <div className="space-y-6">
      {/* Type-specific fields */}
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
          {(d.missing_field_count ?? 0) > 0 && (
            <div className="flex items-center gap-1.5 text-[12px] text-amber-600 bg-amber-50 border border-amber-200 rounded-md px-3 py-2">
              <AlertCircle className="w-3.5 h-3.5" />
              {d.missing_field_count} field(s) need data
            </div>
          )}
        </div>
      )}

      {/* Associated Personas */}
      {detail && detail.associated_personas.length > 0 && (
        <div>
          <h4 className="text-[12px] font-medium text-gray-400 uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <Users className="w-3.5 h-3.5" />
            Linked Personas
          </h4>
          <div className="flex flex-wrap gap-1.5">
            {detail.associated_personas.map((p) => (
              <span
                key={p.id}
                className="px-2.5 py-1 text-[11px] font-medium bg-indigo-50 text-indigo-700 rounded-full"
                title={p.association_reason || p.role || undefined}
              >
                {p.name}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Associated Features */}
      {detail && detail.associated_features.length > 0 && (
        <div>
          <h4 className="text-[12px] font-medium text-gray-400 uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <Puzzle className="w-3.5 h-3.5" />
            Linked Features
          </h4>
          <div className="flex flex-wrap gap-1.5">
            {detail.associated_features.map((f) => (
              <span
                key={f.id}
                className="px-2.5 py-1 text-[11px] font-medium bg-teal-50 text-teal-700 rounded-full"
                title={f.association_reason || f.category || undefined}
              >
                {f.name}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Related Drivers */}
      {detail && detail.related_drivers.length > 0 && (
        <div>
          <h4 className="text-[12px] font-medium text-gray-400 uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <Link2 className="w-3.5 h-3.5" />
            Related Drivers
          </h4>
          <div className="space-y-1.5">
            {detail.related_drivers.map((r) => (
              <div
                key={r.id}
                className="bg-gray-50 border border-gray-100 rounded-md px-3 py-2"
              >
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-medium uppercase px-1.5 py-0.5 rounded bg-gray-200 text-gray-500">
                    {r.driver_type}
                  </span>
                  <span className="text-[13px] text-[#37352f] line-clamp-1">
                    {r.description}
                  </span>
                </div>
                {r.relationship && (
                  <p className="text-[11px] text-gray-400 mt-1">{r.relationship}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {loading && !detail && (
        <div className="text-center py-4">
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-[#009b87] mx-auto" />
          <p className="text-[12px] text-gray-400 mt-2">Loading details...</p>
        </div>
      )}
    </div>
  )
}

function FieldRow({ label, value, badge }: { label: string; value?: string | null; badge?: boolean }) {
  if (!value) return null
  return (
    <div className="flex items-start gap-3">
      <span className="text-[12px] font-medium text-gray-400 min-w-[120px] pt-0.5">{label}</span>
      {badge ? (
        <SeverityBadge value={value} />
      ) : (
        <span className="text-[13px] text-[#37352f] leading-relaxed">{value}</span>
      )}
    </div>
  )
}

function KPIField({ label, value }: { label: string; value?: string | null }) {
  const isMissing = !value
  return (
    <div className={`flex items-start gap-3 ${isMissing ? 'rounded-md border border-dashed border-amber-300 bg-amber-50/50 px-3 py-2 -mx-3' : ''}`}>
      <span className="text-[12px] font-medium text-gray-400 min-w-[140px] pt-0.5">{label}</span>
      {isMissing ? (
        <span className="text-[12px] text-amber-500 italic">Data needed</span>
      ) : (
        <span className="text-[13px] text-[#37352f] leading-relaxed">{value}</span>
      )}
    </div>
  )
}

function SeverityBadge({ value }: { value: string }) {
  const colors: Record<string, string> = {
    critical: 'bg-red-100 text-red-700',
    high: 'bg-orange-100 text-orange-700',
    medium: 'bg-yellow-100 text-yellow-700',
    low: 'bg-gray-100 text-gray-600',
  }
  const cls = colors[value.toLowerCase()] || 'bg-gray-100 text-gray-600'
  return (
    <span className={`inline-flex px-2 py-0.5 text-[11px] font-medium rounded-full ${cls}`}>
      {value}
    </span>
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
        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-[#009b87] mx-auto" />
        <p className="text-[12px] text-gray-400 mt-2">Loading evidence...</p>
      </div>
    )
  }

  if (evidence.length === 0) {
    return (
      <p className="text-[13px] text-gray-400 italic py-4">No evidence sources linked to this item.</p>
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
        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-[#009b87] mx-auto" />
        <p className="text-[12px] text-gray-400 mt-2">Loading history...</p>
      </div>
    )
  }

  if (revisions.length === 0) {
    return (
      <p className="text-[13px] text-gray-400 italic py-4">No revision history available.</p>
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
    created: 'bg-green-100 text-green-700',
    enriched: 'bg-blue-100 text-blue-700',
    updated: 'bg-amber-100 text-amber-700',
    merged: 'bg-purple-100 text-purple-700',
  }
  const typeCls = typeColors[revision.revision_type] || 'bg-gray-100 text-gray-600'

  const timeAgo = formatRelativeTime(revision.created_at)

  return (
    <div className="bg-gray-50 border border-gray-100 rounded-md px-3 py-2.5">
      <div className="flex items-center gap-2 mb-1">
        <span className={`inline-flex px-1.5 py-0.5 text-[10px] font-medium rounded ${typeCls}`}>
          {revision.revision_type}
        </span>
        <span className="text-[11px] text-gray-400">{timeAgo}</span>
        {revision.created_by && (
          <span className="text-[11px] text-gray-400">by {revision.created_by}</span>
        )}
      </div>
      {revision.diff_summary && (
        <p className="text-[12px] text-[rgba(55,53,47,0.65)] leading-relaxed">
          {revision.diff_summary}
        </p>
      )}
      {hasChanges && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-1.5 flex items-center gap-1 text-[11px] text-gray-400 hover:text-gray-600 transition-colors"
        >
          {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
          Field changes
        </button>
      )}
      {expanded && revision.changes && (
        <div className="mt-2 space-y-1 pl-2 border-l-2 border-gray-200">
          {Object.entries(revision.changes).map(([field, change]) => (
            <div key={field} className="text-[11px]">
              <span className="font-medium text-gray-500">{field}:</span>{' '}
              {typeof change === 'object' && change !== null && 'old' in change && 'new' in change ? (
                <>
                  <span className="text-red-400 line-through">{String((change as { old: unknown }).old || '—')}</span>
                  {' → '}
                  <span className="text-green-600">{String((change as { new: unknown }).new || '—')}</span>
                </>
              ) : (
                <span className="text-gray-600">{String(change)}</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
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
