'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  X,
  CheckCircle2,
  Circle,
  FileText,
  AlertTriangle,
  Clock,
  Link2,
  ChevronDown,
  ChevronRight,
  Shield,
  BarChart3,
} from 'lucide-react'
import { getEntityConfidence } from '@/lib/api'
import { formatRelativeTime, formatRevisionAuthor } from '@/lib/date-utils'
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

const CATEGORY_CONFIG: Record<ConfidenceCategory, { bg: string; text: string; label: string }> = {
  identity: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]', label: 'Identity' },
  detail: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]', label: 'Detail' },
  relationships: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]', label: 'Relationships' },
  provenance: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]', label: 'Provenance' },
  confirmation: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]', label: 'Confirmation' },
}

const SOURCE_TYPE_CONFIG: Record<string, { bg: string; text: string; label: string }> = {
  signal: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]', label: 'Signal' },
  research: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]', label: 'Research' },
  inferred: { bg: 'bg-gray-100', text: 'text-gray-600', label: 'Inferred' },
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
    { id: 'gaps', label: 'Gaps', icon: <AlertTriangle className="w-3.5 h-3.5" /> },
    { id: 'history', label: 'History', icon: <Clock className="w-3.5 h-3.5" /> },
  ]

  const gapCount = data?.gaps?.length ?? 0

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-screen w-[560px] max-w-[90vw] bg-white shadow-xl z-50 flex flex-col animate-slide-in-right">
        {/* Header */}
        <div className="flex items-start justify-between px-6 py-4 border-b border-gray-100">
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <Shield className="w-4 h-4 text-[#3FAF7A] flex-shrink-0" />
              <h2 className="text-[16px] font-semibold text-[#37352f] truncate">{entityName}</h2>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[12px] text-[rgba(55,53,47,0.45)] capitalize">{entityType.replace('_', ' ')}</span>
              <BRDStatusBadge status={data?.confirmation_status ?? initialStatus} />
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors flex-shrink-0">
            <X className="w-4 h-4 text-gray-400" />
          </button>
        </div>

        {/* Confirmation actions */}
        <div className="px-6 py-2 border-b border-gray-50">
          <ConfirmActions
            status={data?.confirmation_status ?? initialStatus ?? 'ai_generated'}
            onConfirm={() => onConfirm(entityType, entityId)}
            onNeedsReview={() => onNeedsReview(entityType, entityId)}
          />
        </div>

        {/* Tabs */}
        <div className="flex gap-0 border-b border-gray-100 px-6">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-2.5 text-[12px] font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'text-[#3FAF7A] border-[#3FAF7A]'
                  : 'text-[rgba(55,53,47,0.45)] border-transparent hover:text-[rgba(55,53,47,0.65)]'
              }`}
            >
              {tab.icon}
              {tab.label}
              {tab.id === 'gaps' && gapCount > 0 && (
                <span className="ml-0.5 px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-[#E8F5E9] text-[#25785A]">
                  {gapCount}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#3FAF7A]" />
            </div>
          ) : !data ? (
            <p className="text-[13px] text-gray-400 text-center py-8">Failed to load confidence data</p>
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
    <div className="space-y-5">
      {/* Stale indicator */}
      {data.is_stale && (
        <StaleIndicator reason={data.stale_reason} />
      )}

      {/* Completeness progress */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-[13px] font-medium text-[#37352f]">Confidence Score</span>
          <span className="text-[13px] font-semibold text-[#37352f]">{data.completeness_met}/{data.completeness_total}</span>
        </div>
        <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-[#3FAF7A] rounded-full transition-all duration-300"
            style={{ width: `${pct}%` }}
          />
        </div>
        <p className="text-[11px] text-[rgba(55,53,47,0.45)] mt-1">{pct}% of confidence criteria met</p>
      </div>

      {/* Grouped checklist */}
      {Array.from(grouped.entries()).map(([category, items]) => {
        const catConfig = CATEGORY_CONFIG[category as ConfidenceCategory] || CATEGORY_CONFIG.detail
        return (
          <div key={category}>
            <div className="flex items-center gap-2 mb-2">
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider ${catConfig.bg} ${catConfig.text}`}>
                {catConfig.label}
              </span>
            </div>
            <div className="space-y-1.5">
              {items.map((item, i) => (
                <div key={i} className="flex items-start gap-2">
                  {item.is_met ? (
                    <CheckCircle2 className="w-4 h-4 text-[#3FAF7A] flex-shrink-0 mt-0.5" />
                  ) : (
                    <Circle className="w-4 h-4 text-gray-300 flex-shrink-0 mt-0.5" />
                  )}
                  <span className={`text-[13px] ${item.is_met ? 'text-[rgba(55,53,47,0.65)]' : 'text-[#37352f]'}`}>
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
        <div className="pt-3 border-t border-gray-100">
          <div className="flex items-center gap-2 mb-2">
            <Link2 className="w-3.5 h-3.5 text-gray-400" />
            <span className="text-[12px] font-semibold text-[rgba(55,53,47,0.45)] uppercase tracking-wider">Dependencies</span>
          </div>
          <div className="flex gap-4 text-[13px] text-[rgba(55,53,47,0.65)]">
            {dependsOnCount > 0 && (
              <span>Depends on <strong>{dependsOnCount}</strong> {dependsOnCount === 1 ? 'entity' : 'entities'}</span>
            )}
            {dependedByCount > 0 && (
              <span><strong>{dependedByCount}</strong> {dependedByCount === 1 ? 'entity depends' : 'entities depend'} on this</span>
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
        <FileText className="w-8 h-8 text-gray-300 mx-auto mb-2" />
        <p className="text-[13px] text-[rgba(55,53,47,0.45)]">No evidence tracked yet</p>
        <p className="text-[12px] text-[rgba(55,53,47,0.35)] mt-1">Process a signal to establish provenance</p>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      {/* Evidence items */}
      {hasEvidence && (
        <div>
          <h4 className="text-[12px] font-semibold text-[rgba(55,53,47,0.45)] uppercase tracking-wider mb-3">
            Evidence ({data.evidence.length})
          </h4>
          <div className="space-y-3">
            {data.evidence.map((ev, i) => {
              const srcConfig = SOURCE_TYPE_CONFIG[ev.source_type] || SOURCE_TYPE_CONFIG.inferred
              return (
                <div key={i} className="border border-gray-100 rounded-md p-3">
                  {ev.excerpt && (
                    <blockquote className="text-[13px] text-[rgba(55,53,47,0.65)] italic border-l-2 border-[#3FAF7A] pl-3 mb-2">
                      {ev.excerpt}
                    </blockquote>
                  )}
                  {ev.rationale && (
                    <p className="text-[12px] text-[rgba(55,53,47,0.45)] mb-2">{ev.rationale}</p>
                  )}
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium ${srcConfig.bg} ${srcConfig.text}`}>
                      {srcConfig.label}
                    </span>
                    {ev.signal_label && (
                      <span className="text-[11px] text-[rgba(55,53,47,0.45)]">
                        {ev.signal_label}
                      </span>
                    )}
                    {ev.signal_created_at && (
                      <span className="text-[11px] text-[rgba(55,53,47,0.35)]">
                        {formatRelativeTime(ev.signal_created_at)}
                      </span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Field attributions */}
      {hasAttributions && (
        <div>
          <h4 className="text-[12px] font-semibold text-[rgba(55,53,47,0.45)] uppercase tracking-wider mb-3">
            Field Attributions ({data.field_attributions.length})
          </h4>
          <div className="overflow-hidden rounded-md border border-gray-100">
            <table className="w-full text-[12px]">
              <thead>
                <tr className="bg-gray-50/50">
                  <th className="text-left px-3 py-2 font-medium text-[rgba(55,53,47,0.45)]">Field</th>
                  <th className="text-left px-3 py-2 font-medium text-[rgba(55,53,47,0.45)]">Source</th>
                  <th className="text-left px-3 py-2 font-medium text-[rgba(55,53,47,0.45)]">Date</th>
                </tr>
              </thead>
              <tbody>
                {data.field_attributions.map((attr, i) => (
                  <tr key={i} className="border-t border-gray-50">
                    <td className="px-3 py-2 text-[rgba(55,53,47,0.65)] font-mono text-[11px]">{attr.field_path}</td>
                    <td className="px-3 py-2 text-[rgba(55,53,47,0.65)]">{attr.signal_label || '—'}</td>
                    <td className="px-3 py-2 text-[rgba(55,53,47,0.45)]">{attr.contributed_at ? formatRelativeTime(attr.contributed_at) : ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
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
        <p className="text-[14px] font-medium text-[#37352f]">All confidence criteria met</p>
        <p className="text-[12px] text-[rgba(55,53,47,0.45)] mt-1">This entity has full evidence and confirmation coverage</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <p className="text-[12px] text-[rgba(55,53,47,0.45)] mb-1">
        {gaps.length} {gaps.length === 1 ? 'gap' : 'gaps'} to address for full confidence
      </p>
      {gaps.map((gap, i) => {
        const catConfig = CATEGORY_CONFIG[gap.category as ConfidenceCategory] || CATEGORY_CONFIG.detail
        return (
          <div key={i} className="border border-gray-100 rounded-md p-3">
            <div className="flex items-start gap-2">
              <Circle className="w-4 h-4 text-gray-300 flex-shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[13px] font-medium text-[#37352f]">{gap.label}</span>
                  <span className={`inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-medium ${catConfig.bg} ${catConfig.text}`}>
                    {catConfig.label}
                  </span>
                </div>
                {gap.suggestion && (
                  <p className="text-[12px] text-[rgba(55,53,47,0.45)]">{gap.suggestion}</p>
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
        <Clock className="w-8 h-8 text-gray-300 mx-auto mb-2" />
        <p className="text-[13px] text-[rgba(55,53,47,0.45)]">No revision history available</p>
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
                <div className="w-2.5 h-2.5 rounded-full bg-[#3FAF7A] border-2 border-white shadow-sm mt-1.5" />
                {!isLast && <div className="w-px flex-1 bg-gray-200 mt-1" />}
              </div>

              {/* Content */}
              <div className={`flex-1 min-w-0 ${isLast ? 'pb-0' : 'pb-4'}`}>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[12px] text-[rgba(55,53,47,0.35)]">
                    {formatRelativeTime(rev.created_at)}
                  </span>
                  {rev.revision_type && (
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-600">
                      {rev.revision_type}
                    </span>
                  )}
                  <span className="text-[11px] text-[rgba(55,53,47,0.35)]">
                    by {formatRevisionAuthor(rev.created_by)}
                  </span>
                </div>
                {rev.diff_summary && (
                  <p className="text-[13px] text-[rgba(55,53,47,0.65)] mt-0.5">{rev.diff_summary}</p>
                )}
                {hasChanges && (
                  <button
                    onClick={() => setExpandedIdx(isExpanded ? null : i)}
                    className="flex items-center gap-1 mt-1 text-[11px] text-[#3FAF7A] hover:text-[#25785A] transition-colors"
                  >
                    {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                    {isExpanded ? 'Hide changes' : 'Show changes'}
                  </button>
                )}
                {isExpanded && rev.changes && (
                  <div className="mt-2 p-2 bg-gray-50 rounded text-[11px] font-mono text-[rgba(55,53,47,0.65)] overflow-x-auto">
                    <pre className="whitespace-pre-wrap">{JSON.stringify(rev.changes, null, 2)}</pre>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Entity timestamps */}
      <div className="mt-4 pt-3 border-t border-gray-100 space-y-1">
        {data.created_at && (
          <p className="text-[11px] text-[rgba(55,53,47,0.35)]">
            Created {new Date(data.created_at).toLocaleDateString()} at {new Date(data.created_at).toLocaleTimeString()}
          </p>
        )}
        {data.updated_at && (
          <p className="text-[11px] text-[rgba(55,53,47,0.35)]">
            Last updated {formatRelativeTime(data.updated_at)}
          </p>
        )}
      </div>
    </div>
  )
}
