'use client'

import { useState, useEffect } from 'react'
import {
  Puzzle,
  FileText,
  Clock,
  ChevronDown,
  ChevronRight,
  Sparkles,
  Star,
} from 'lucide-react'
import { DrawerShell, type DrawerTab } from '@/components/ui/DrawerShell'
import { EmptyState } from '@/components/ui/EmptyState'
import { Spinner } from '@/components/ui/Spinner'
import { BRDStatusBadge } from './StatusBadge'
import { ConfirmActions } from './ConfirmActions'
import { EvidenceBlock } from './EvidenceBlock'
import { listEntityRevisions } from '@/lib/api'
import { formatRelativeTime, formatRevisionAuthor, REVISION_TYPE_COLORS } from '@/lib/date-utils'
import type { FeatureBRDSummary } from '@/types/workspace'

type TabId = 'overview' | 'history'

interface FeatureDrawerProps {
  feature: FeatureBRDSummary
  projectId: string
  onClose: () => void
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
}

const TABS: DrawerTab[] = [
  { id: 'overview', label: 'Overview', icon: FileText },
  { id: 'history', label: 'History', icon: Clock },
]

const PRIORITY_COLORS: Record<string, string> = {
  must_have: 'bg-[#0A1E2F] text-white',
  should_have: 'bg-[#E8F5E9] text-[#25785A]',
  could_have: 'bg-[#F0F0F0] text-[#666666]',
  out_of_scope: 'bg-[#F0F0F0] text-[#999999]',
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
    <DrawerShell
      onClose={onClose}
      icon={Puzzle}
      title={feature.name}
      headerExtra={
        <>
          {/* Priority group badge */}
          <div className="flex items-center gap-2 mb-1" style={{ order: -1 }}>
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
        </>
      }
      headerRight={<BRDStatusBadge status={feature.confirmation_status} />}
      headerActions={
        <ConfirmActions
          status={feature.confirmation_status}
          onConfirm={() => onConfirm('feature', feature.id)}
          onNeedsReview={() => onNeedsReview('feature', feature.id)}
          size="md"
        />
      }
      tabs={TABS}
      activeTab={activeTab}
      onTabChange={(id) => setActiveTab(id as TabId)}
    >
      {activeTab === 'overview' && <OverviewTab feature={feature} />}
      {activeTab === 'history' && <HistoryTab featureId={feature.id} />}
    </DrawerShell>
  )
}

// ============================================================================
// Overview Tab
// ============================================================================

function OverviewTab({ feature }: { feature: FeatureBRDSummary }) {
  return (
    <div className="space-y-5">
      {feature.description && (
        <div className="bg-[#F4F4F4] border border-[#E5E5E5] rounded-xl px-4 py-3">
          <p className="text-[13px] text-[#333333] leading-relaxed">{feature.description}</p>
        </div>
      )}

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

      {feature.evidence && feature.evidence.length > 0 && (
        <EvidenceBlock evidence={feature.evidence} maxItems={3} />
      )}

      {!feature.description && (!feature.evidence || feature.evidence.length === 0) && (
        <EmptyState
          icon={<Puzzle className="w-8 h-8 text-[#E5E5E5]" />}
          title="No details yet"
          description="Process more signals to enrich this feature with details and evidence."
        />
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
    return <Spinner label="Loading revision history..." />
  }

  if (!revisions || revisions.length === 0) {
    return (
      <EmptyState
        icon={<Clock className="w-8 h-8 text-[#E5E5E5]" />}
        title="No revision history"
        description="Changes will be tracked here as signals are processed."
      />
    )
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
                  REVISION_TYPE_COLORS[rev.change_type] || REVISION_TYPE_COLORS.updated
                }`}
              >
                {rev.change_type}
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
