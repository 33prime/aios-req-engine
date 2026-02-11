'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  X,
  CheckCircle2,
  Circle,
  FileText,
  Clock,
  Link2,
  ChevronDown,
  ChevronRight,
  Shield,
  BarChart3,
} from 'lucide-react'
import { getEntityConfidence } from '@/lib/api'
import { BRDStatusBadge } from './StatusBadge'
import { ConfirmActions } from './ConfirmActions'
import { StaleIndicator } from './StaleIndicator'
import type { EntityConfidenceData, ConfidenceGap, ConfidenceCategory } from '@/types/workspace'

interface ConfidenceDrawerProps {
  entityType: string
  entityId: string
  entityName: string
  projectId: string
  initialStatus?: string | null
  onClose: () => void
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
}

type TabId = 'overview' | 'evidence' | 'gaps' | 'history'

// All categories use the same neutral styling — no colored badges
const CATEGORY_LABELS: Record<ConfidenceCategory, string> = {
  identity: 'Identity',
  detail: 'Detail',
  relationships: 'Relationships',
  provenance: 'Provenance',
  confirmation: 'Confirmation',
}

function formatRelativeTime(dateStr: string | null | undefined): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr}h ago`
  const diffDay = Math.floor(diffHr / 24)
  if (diffDay < 30) return `${diffDay}d ago`
  return date.toLocaleDateString()
}

export function ConfidenceDrawer({
  entityType,
  entityId,
  entityName,
  projectId,
  initialStatus,
  onClose,
  onConfirm,
  onNeedsReview,
}: ConfidenceDrawerProps) {
  const [data, setData] = useState<EntityConfidenceData | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<TabId>('overview')

  const loadData = useCallback(() => {
    setLoading(true)
    getEntityConfidence(projectId, entityType, entityId)
      .then((result) => setData(result))
      .catch((err) => console.error('Failed to load confidence data:', err))
      .finally(() => setLoading(false))
  }, [projectId, entityType, entityId])

  useEffect(() => {
    loadData()
  }, [loadData])

  const tabs: { id: TabId; label: string; icon: React.ReactNode }[] = [
    { id: 'overview', label: 'Overview', icon: <BarChart3 className="w-3.5 h-3.5" /> },
    { id: 'evidence', label: 'Evidence', icon: <FileText className="w-3.5 h-3.5" /> },
    { id: 'gaps', label: 'Gaps', icon: <Shield className="w-3.5 h-3.5" /> },
    { id: 'history', label: 'History', icon: <Clock className="w-3.5 h-3.5" /> },
  ]

  const gapCount = data?.gaps?.length ?? 0

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-screen w-[560px] max-w-[90vw] bg-white shadow-xl z-50 flex flex-col animate-slide-in-right">
        {/* Header — navy accent bar */}
        <div className="bg-[#0A1E2F] px-6 py-4">
          <div className="flex items-start justify-between">
            <div className="min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <Shield className="w-4 h-4 text-[#3FAF7A] flex-shrink-0" />
                <h2 className="text-[16px] font-semibold text-white truncate">{entityName}</h2>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[12px] text-white/50 capitalize">{entityType.replace('_', ' ')}</span>
                <BRDStatusBadge status={data?.confirmation_status ?? initialStatus} />
              </div>
            </div>
            <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/10 transition-colors flex-shrink-0">
              <X className="w-4 h-4 text-white/60" />
            </button>
          </div>
        </div>

        {/* Confirmation actions */}
        <div className="px-6 py-2.5 border-b border-[#E5E5E5]">
          <ConfirmActions
            status={data?.confirmation_status ?? initialStatus ?? 'ai_generated'}
            onConfirm={() => onConfirm(entityType, entityId)}
            onNeedsReview={() => onNeedsReview(entityType, entityId)}
          />
        </div>

        {/* Tabs */}
        <div className="flex gap-0 border-b border-[#E5E5E5] px-6">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-2.5 text-[12px] font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'text-[#333333] border-[#3FAF7A]'
                  : 'text-[#999999] border-transparent hover:text-[#666666]'
              }`}
            >
              {tab.icon}
              {tab.label}
              {tab.id === 'gaps' && gapCount > 0 && (
                <span className="ml-0.5 w-5 h-5 rounded-full text-[10px] font-bold bg-[#0A1E2F] text-white inline-flex items-center justify-center">
                  {gapCount}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4 bg-[#F4F4F4]">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#3FAF7A]" />
            </div>
          ) : !data ? (
            <p className="text-[13px] text-[#999999] text-center py-8">Failed to load confidence data</p>
          ) : activeTab === 'overview' ? (
            <OverviewTab data={data} />
          ) : activeTab === 'evidence' ? (
            <EvidenceTab data={data} />
          ) : activeTab === 'gaps' ? (
            <GapsTab gaps={data.gaps} />
          ) : (
            <HistoryTab data={data} />
          )}
        </div>
      </div>
    </>
  )
}

// ============================================================================
// Overview Tab
// ============================================================================

function OverviewTab({ data }: { data: EntityConfidenceData }) {
  const pct = data.completeness_total > 0
    ? Math.round((data.completeness_met / data.completeness_total) * 100)
    : 0

  // Group checks by category
  const grouped = new Map<string, ConfidenceGap[]>()
  for (const item of data.completeness_items) {
    const list = grouped.get(item.category) || []
    list.push(item)
    grouped.set(item.category, list)
  }

  const dependsOnCount = data.dependencies.filter(d => d.direction === 'depends_on').length
  const dependedByCount = data.dependencies.filter(d => d.direction === 'depended_by').length

  return (
    <div className="space-y-4">
      {/* Stale indicator */}
      {data.is_stale && (
        <StaleIndicator reason={data.stale_reason} />
      )}

      {/* Completeness progress — card style */}
      <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-5">
        <div className="flex items-center justify-between mb-3">
          <span className="text-[13px] font-semibold text-[#333333]">Confidence Score</span>
          <span className="text-[13px] font-bold text-[#333333]">{data.completeness_met}/{data.completeness_total}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-[#666666] w-16 shrink-0">Progress</span>
          <div className="flex-1 h-2 bg-[#F0F0F0] rounded-full overflow-hidden">
            <div
              className="h-full bg-[#3FAF7A] rounded-full transition-all duration-300"
              style={{ width: `${pct}%` }}
            />
          </div>
          <span className="text-[11px] font-medium text-[#333333] w-10 text-right">{pct}%</span>
        </div>
      </div>

      {/* Grouped checklist — each category in its own card */}
      {Array.from(grouped.entries()).map(([category, items]) => {
        const label = CATEGORY_LABELS[category as ConfidenceCategory] || category
        return (
          <div key={category} className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] overflow-hidden">
            {/* Category header — like workflow column headers */}
            <div className="px-4 py-2 bg-[#F0F0F0]">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-[#666666]">
                {label}
              </span>
            </div>
            <div className="px-4 py-3 space-y-2">
              {items.map((item, i) => (
                <div key={i} className="flex items-center gap-2.5">
                  {item.is_met ? (
                    <CheckCircle2 className="w-4 h-4 text-[#3FAF7A] flex-shrink-0" />
                  ) : (
                    <Circle className="w-4 h-4 text-[#E5E5E5] flex-shrink-0" />
                  )}
                  <span className={`text-[13px] ${item.is_met ? 'text-[#666666]' : 'text-[#333333] font-medium'}`}>
                    {item.label}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )
      })}

      {/* Dependencies summary */}
      {(dependsOnCount > 0 || dependedByCount > 0) && (
        <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-4">
          <div className="flex items-center gap-2 mb-2">
            <Link2 className="w-3.5 h-3.5 text-[#999999]" />
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[#666666]">Dependencies</span>
          </div>
          <div className="flex gap-4 text-[13px] text-[#666666]">
            {dependsOnCount > 0 && (
              <span>Depends on <strong className="text-[#333333]">{dependsOnCount}</strong> {dependsOnCount === 1 ? 'entity' : 'entities'}</span>
            )}
            {dependedByCount > 0 && (
              <span><strong className="text-[#333333]">{dependedByCount}</strong> {dependedByCount === 1 ? 'entity depends' : 'entities depend'} on this</span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Evidence Tab
// ============================================================================

function EvidenceTab({ data }: { data: EntityConfidenceData }) {
  const hasEvidence = data.evidence.length > 0
  const hasAttributions = data.field_attributions.length > 0

  if (!hasEvidence && !hasAttributions) {
    return (
      <div className="text-center py-10">
        <FileText className="w-8 h-8 text-[#E5E5E5] mx-auto mb-2" />
        <p className="text-[13px] text-[#999999]">No evidence tracked yet</p>
        <p className="text-[12px] text-[#999999]/70 mt-1">Process a signal to establish provenance</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Evidence items */}
      {hasEvidence && (
        <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] overflow-hidden">
          <div className="px-4 py-2 bg-[#F0F0F0]">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[#666666]">
              Evidence ({data.evidence.length})
            </span>
          </div>
          <div className="divide-y divide-[#E5E5E5]">
            {data.evidence.map((ev, i) => (
              <div key={i} className="px-4 py-3">
                {ev.excerpt && (
                  <blockquote className="text-[13px] text-[#666666] italic border-l-2 border-[#3FAF7A] pl-3 mb-2">
                    {ev.excerpt}
                  </blockquote>
                )}
                {ev.rationale && (
                  <p className="text-[12px] text-[#999999] mb-2">{ev.rationale}</p>
                )}
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-[#E8F5E9] text-[#25785A]">
                    {ev.source_type || 'Signal'}
                  </span>
                  {ev.signal_label && (
                    <span className="text-[11px] text-[#999999]">{ev.signal_label}</span>
                  )}
                  {ev.signal_created_at && (
                    <span className="text-[11px] text-[#999999]/70">{formatRelativeTime(ev.signal_created_at)}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Field attributions */}
      {hasAttributions && (
        <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] overflow-hidden">
          <div className="px-4 py-2 bg-[#F0F0F0]">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[#666666]">
              Field Attributions ({data.field_attributions.length})
            </span>
          </div>
          <table className="w-full text-[12px]">
            <thead>
              <tr className="border-b border-[#E5E5E5]">
                <th className="text-left px-4 py-2 font-medium text-[#999999]">Field</th>
                <th className="text-left px-4 py-2 font-medium text-[#999999]">Source</th>
                <th className="text-left px-4 py-2 font-medium text-[#999999]">Date</th>
              </tr>
            </thead>
            <tbody>
              {data.field_attributions.map((attr, i) => (
                <tr key={i} className="border-t border-[#E5E5E5]/50">
                  <td className="px-4 py-2 text-[#333333] font-mono text-[11px]">{attr.field_path}</td>
                  <td className="px-4 py-2 text-[#666666]">{attr.signal_label || '—'}</td>
                  <td className="px-4 py-2 text-[#999999]">{formatRelativeTime(attr.contributed_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Gaps Tab
// ============================================================================

function GapsTab({ gaps }: { gaps: ConfidenceGap[] }) {
  if (gaps.length === 0) {
    return (
      <div className="text-center py-10">
        <CheckCircle2 className="w-8 h-8 text-[#3FAF7A] mx-auto mb-2" />
        <p className="text-[14px] font-medium text-[#333333]">All confidence criteria met</p>
        <p className="text-[12px] text-[#999999] mt-1">This entity has full evidence and confirmation coverage</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <p className="text-[12px] text-[#999999] mb-1">
        {gaps.length} {gaps.length === 1 ? 'gap' : 'gaps'} to address for full confidence
      </p>
      {gaps.map((gap, i) => {
        const label = CATEGORY_LABELS[gap.category as ConfidenceCategory] || gap.category
        return (
          <div key={i} className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] px-4 py-3">
            <div className="flex items-start gap-2.5">
              <div className="w-7 h-7 rounded-full bg-[#0A1E2F] flex items-center justify-center shrink-0 mt-0.5">
                <span className="text-[11px] font-bold text-white">{i + 1}</span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-[13px] font-medium text-[#333333]">{gap.label}</span>
                  <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-[#F0F0F0] text-[#666666]">
                    {label}
                  </span>
                </div>
                {gap.suggestion && (
                  <p className="text-[12px] text-[#999999]">{gap.suggestion}</p>
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

function HistoryTab({ data }: { data: EntityConfidenceData }) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null)

  if (data.revisions.length === 0) {
    return (
      <div className="text-center py-10">
        <Clock className="w-8 h-8 text-[#E5E5E5] mx-auto mb-2" />
        <p className="text-[13px] text-[#999999]">No revision history available</p>
      </div>
    )
  }

  return (
    <div className="space-y-0">
      {/* Timeline */}
      <div className="relative">
        {data.revisions.map((rev, i) => {
          const isLast = i === data.revisions.length - 1
          const isExpanded = expandedIdx === i
          const hasChanges = rev.changes && Object.keys(rev.changes).length > 0

          return (
            <div key={i} className="relative flex gap-3">
              {/* Timeline line + dot */}
              <div className="flex flex-col items-center flex-shrink-0">
                <div className="w-7 h-7 rounded-full bg-[#0A1E2F] flex items-center justify-center shrink-0">
                  <span className="text-[11px] font-bold text-white">{i + 1}</span>
                </div>
                {!isLast && <div className="w-0 flex-1 border-l-2 border-dashed border-[#E5E5E5] min-h-[16px]" />}
              </div>

              {/* Content */}
              <div className={`flex-1 min-w-0 ${isLast ? 'pb-0' : 'pb-4'}`}>
                <div className="bg-white rounded-xl border border-[#E5E5E5] px-3.5 py-2.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[12px] text-[#999999]">
                      {formatRelativeTime(rev.created_at)}
                    </span>
                    {rev.revision_type && (
                      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-[#E8F5E9] text-[#25785A]">
                        {rev.revision_type}
                      </span>
                    )}
                    {rev.created_by && (
                      <span className="text-[11px] text-[#999999]">by {rev.created_by}</span>
                    )}
                  </div>
                  {rev.diff_summary && (
                    <p className="text-[13px] text-[#666666] mt-1">{rev.diff_summary}</p>
                  )}
                  {hasChanges && (
                    <button
                      onClick={() => setExpandedIdx(isExpanded ? null : i)}
                      className="flex items-center gap-1 mt-1.5 text-[11px] text-[#3FAF7A] hover:text-[#25785A] transition-colors"
                    >
                      {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                      {isExpanded ? 'Hide changes' : 'Show changes'}
                    </button>
                  )}
                  {isExpanded && rev.changes && (
                    <div className="mt-2 p-2 bg-[#F4F4F4] rounded-lg text-[11px] font-mono text-[#666666] overflow-x-auto">
                      <pre className="whitespace-pre-wrap">{JSON.stringify(rev.changes, null, 2)}</pre>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Entity timestamps */}
      <div className="mt-4 pt-3 border-t border-[#E5E5E5] space-y-1">
        {data.created_at && (
          <p className="text-[11px] text-[#999999]">
            Created {new Date(data.created_at).toLocaleDateString()} at {new Date(data.created_at).toLocaleTimeString()}
          </p>
        )}
        {data.updated_at && (
          <p className="text-[11px] text-[#999999]">
            Last updated {formatRelativeTime(data.updated_at)}
          </p>
        )}
      </div>
    </div>
  )
}
