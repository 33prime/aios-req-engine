'use client'

import { useState, useEffect } from 'react'
import {
  X,
  Puzzle,
  FileText,
  Clock,
  ChevronDown,
  ChevronRight,
  Sparkles,
  Star,
} from 'lucide-react'
import { BRDStatusBadge } from './StatusBadge'
import { ConfirmActions } from './ConfirmActions'
import { EvidenceBlock } from './EvidenceBlock'
import { listEntityRevisions } from '@/lib/api'
import type { FeatureBRDSummary } from '@/types/workspace'

type TabId = 'overview' | 'history'

interface FeatureDrawerProps {
  feature: FeatureBRDSummary
  projectId: string
  onClose: () => void
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
}

const TABS: { id: TabId; label: string; icon: typeof FileText }[] = [
  { id: 'overview', label: 'Overview', icon: FileText },
  { id: 'history', label: 'History', icon: Clock },
]

const PRIORITY_COLORS: Record<string, string> = {
  must_have: 'bg-[#0A1E2F] text-white',
  should_have: 'bg-[#E8F5E9] text-[#25785A]',
  could_have: 'bg-[#F0F0F0] text-[#666666]',
  out_of_scope: 'bg-[#F0F0F0] text-[#999999]',
}

function formatRelativeTime(dateStr: string): string {
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
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  } catch {
    return ''
  }
}

export function FeatureDrawer({
  feature,
  projectId,
  onClose,
  onConfirm,
  onNeedsReview,
}: FeatureDrawerProps) {
  const [activeTab, setActiveTab] = useState<TabId>('overview')

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
              {/* Navy circle with feature icon */}
              <div className="w-8 h-8 rounded-full bg-[#0A1E2F] flex items-center justify-center flex-shrink-0 mt-0.5">
                <Puzzle className="w-4 h-4 text-white" />
              </div>
              <div className="min-w-0">
                {/* Priority group badge */}
                <div className="flex items-center gap-2 mb-1">
                  {feature.priority_group && (
                    <span
                      className={`text-[10px] font-medium uppercase px-1.5 py-0.5 rounded ${
                        PRIORITY_COLORS[feature.priority_group] || PRIORITY_COLORS.could_have
                      }`}
                    >
                      {feature.priority_group.replace('_', ' ')}
                    </span>
                  )}
                  {feature.is_mvp && (
                    <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[#E8F5E9] text-[#25785A] inline-flex items-center gap-0.5">
                      <Star className="w-3 h-3" />
                      MVP
                    </span>
                  )}
                </div>
                <h2 className="text-[15px] font-semibold text-[#333333] line-clamp-2 leading-snug">
                  {feature.name}
                </h2>
              </div>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <BRDStatusBadge status={feature.confirmation_status} />
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
              status={feature.confirmation_status}
              onConfirm={() => onConfirm('feature', feature.id)}
              onNeedsReview={() => onNeedsReview('feature', feature.id)}
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
                </button>
              )
            })}
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {activeTab === 'overview' && <OverviewTab feature={feature} />}
          {activeTab === 'history' && <HistoryTab featureId={feature.id} />}
        </div>
      </div>
    </>
  )
}

// ============================================================================
// Overview Tab
// ============================================================================

function OverviewTab({ feature }: { feature: FeatureBRDSummary }) {
  return (
    <div className="space-y-5">
      {/* Description */}
      {feature.description && (
        <div className="bg-[#F4F4F4] border border-[#E5E5E5] rounded-xl px-4 py-3">
          <p className="text-[13px] text-[#333333] leading-relaxed">{feature.description}</p>
        </div>
      )}

      {/* Category + MVP row */}
      {(feature.category || feature.is_mvp) && (
        <div className="flex items-center gap-2 flex-wrap">
          {feature.category && (
            <span className="text-[11px] font-medium px-2 py-1 rounded-lg bg-[#F0F0F0] text-[#666666]">
              {feature.category}
            </span>
          )}
          {feature.is_mvp && (
            <span className="text-[11px] font-medium px-2 py-1 rounded-lg bg-[#E8F5E9] text-[#25785A] inline-flex items-center gap-1">
              <Star className="w-3 h-3" />
              MVP Feature
            </span>
          )}
        </div>
      )}

      {/* Stale indicator */}
      {feature.is_stale && (
        <div className="bg-orange-50 border-l-2 border-orange-300 px-3 py-2 rounded-r-sm">
          <div className="flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-orange-500 flex-shrink-0" />
            <span className="text-[12px] text-orange-700">
              {feature.stale_reason || 'This feature may be outdated due to upstream changes'}
            </span>
          </div>
        </div>
      )}

      {/* Evidence */}
      {feature.evidence && feature.evidence.length > 0 && (
        <EvidenceBlock evidence={feature.evidence} maxItems={3} />
      )}

      {/* Empty state when no description and no evidence */}
      {!feature.description && (!feature.evidence || feature.evidence.length === 0) && (
        <div className="text-center py-8">
          <Puzzle className="w-8 h-8 text-[#E5E5E5] mx-auto mb-3" />
          <p className="text-[13px] text-[#666666] mb-1">No details yet</p>
          <p className="text-[12px] text-[#999999]">
            Process more signals to enrich this feature with details and evidence.
          </p>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// History Tab
// ============================================================================

interface RevisionItem {
  id: string
  revision_number: number
  change_type: string
  changes: Record<string, unknown>
  diff_summary: string
  created_at: string
  created_by?: string
}

function HistoryTab({ featureId }: { featureId: string }) {
  const [revisions, setRevisions] = useState<RevisionItem[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    listEntityRevisions('feature', featureId)
      .then((data) => {
        if (!cancelled) setRevisions(data.revisions)
      })
      .catch((err) => {
        console.error('Failed to load feature revisions:', err)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [featureId])

  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#3FAF7A] mx-auto" />
        <p className="text-[12px] text-[#999999] mt-2">Loading revision history...</p>
      </div>
    )
  }

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

  const typeColors: Record<string, string> = {
    created: 'bg-[#E8F5E9] text-[#25785A]',
    enriched: 'bg-[#F0F0F0] text-[#666666]',
    updated: 'bg-[#F0F0F0] text-[#666666]',
    merged: 'bg-[#F0F0F0] text-[#666666]',
  }

  return (
    <div className="space-y-3">
      {revisions.map((rev, i) => {
        const isExpanded = expandedIdx === i
        const hasChanges = rev.changes && Object.keys(rev.changes).length > 0

        return (
          <div key={i} className="border border-[#E5E5E5] rounded-xl px-4 py-3">
            <div className="flex items-center gap-2 mb-1">
              <span
                className={`text-[10px] font-medium uppercase px-1.5 py-0.5 rounded ${
                  typeColors[rev.change_type] || typeColors.updated
                }`}
              >
                {rev.change_type}
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
            {hasChanges && (
              <button
                onClick={() => setExpandedIdx(isExpanded ? null : i)}
                className="flex items-center gap-1 mt-2 text-[11px] font-medium text-[#999999] hover:text-[#666666] transition-colors"
              >
                {isExpanded ? (
                  <ChevronDown className="w-3 h-3" />
                ) : (
                  <ChevronRight className="w-3 h-3" />
                )}
                {isExpanded ? 'Hide changes' : 'View changes'}
              </button>
            )}
            {isExpanded && hasChanges && (
              <div className="mt-2 bg-[#F4F4F4] border border-[#E5E5E5] rounded-lg px-3 py-2">
                <pre className="text-[11px] text-[#666666] whitespace-pre-wrap break-words font-mono leading-relaxed">
                  {JSON.stringify(rev.changes, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
