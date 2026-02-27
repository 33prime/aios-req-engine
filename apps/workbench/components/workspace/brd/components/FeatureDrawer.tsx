'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  Puzzle,
  FileText,
  Clock,
  ChevronDown,
  ChevronRight,
  Sparkles,
  Star,
  AlertTriangle,
  Target,
  Users,
  Workflow,
} from 'lucide-react'
import { DrawerShell, type DrawerTab } from '@/components/ui/DrawerShell'
import { EmptyState } from '@/components/ui/EmptyState'
import { Spinner } from '@/components/ui/Spinner'
import { BRDStatusBadge } from './StatusBadge'
import { ConfirmActions } from './ConfirmActions'
import { EvidenceBlock } from './EvidenceBlock'
import { getFeatureDetail } from '@/lib/api'
import { formatRelativeTime, formatRevisionAuthor, REVISION_TYPE_COLORS } from '@/lib/date-utils'
import type { FeatureBRDSummary, FeatureDetailResponse, LinkedEntityPill } from '@/types/workspace'

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
  out_of_scope: 'bg-[#F0F0F0] text-text-placeholder',
}

export function FeatureDrawer({
  feature,
  projectId,
  onClose,
  onConfirm,
  onNeedsReview,
}: FeatureDrawerProps) {
  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [detail, setDetail] = useState<FeatureDetailResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getFeatureDetail(projectId, feature.id)
      .then((data) => { if (!cancelled) setDetail(data) })
      .catch((err) => console.error('Failed to load feature detail:', err))
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [projectId, feature.id])

  return (
    <DrawerShell
      onClose={onClose}
      icon={Puzzle}
      title={feature.name}
      headerExtra={
        <>
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
      {activeTab === 'overview' && (
        <OverviewTab feature={feature} detail={detail} loading={loading} />
      )}
      {activeTab === 'history' && (
        <HistoryTab revisions={detail?.revisions || []} loading={loading} />
      )}
    </DrawerShell>
  )
}

// ============================================================================
// LinkedPillGroup — reusable for feature + driver drawers
// ============================================================================

const TYPE_ICONS: Record<string, typeof AlertTriangle> = {
  business_driver: AlertTriangle,
  persona: Users,
  vp_step: Workflow,
  feature: Puzzle,
}

const SUBTITLE_LABELS: Record<string, string> = {
  pain: 'Pain',
  goal: 'Goal',
  kpi: 'Metric',
}

export function LinkedPillGroup({
  icon: Icon,
  title,
  pills,
  emptyText,
}: {
  icon: typeof AlertTriangle
  title: string
  pills: LinkedEntityPill[]
  emptyText: string
}) {
  if (pills.length === 0) {
    return (
      <div>
        <h4 className="text-[11px] font-medium text-text-placeholder uppercase tracking-wide mb-2">
          {title}
        </h4>
        <p className="text-[12px] text-text-placeholder italic">{emptyText}</p>
      </div>
    )
  }

  return (
    <div>
      <h4 className="text-[11px] font-medium text-text-placeholder uppercase tracking-wide mb-2">
        {title} ({pills.length})
      </h4>
      <div className="space-y-1.5">
        {pills.map((pill) => {
          const PillIcon = TYPE_ICONS[pill.entity_type] || Puzzle
          const subtitleText = pill.subtitle
            ? (SUBTITLE_LABELS[pill.subtitle] || pill.subtitle)
            : null
          return (
            <div
              key={pill.id}
              className="flex items-center gap-2.5 px-3 py-2 bg-[#F4F4F4] border border-border rounded-lg"
            >
              <PillIcon className="w-3.5 h-3.5 text-text-placeholder flex-shrink-0" />
              <span className="text-[13px] text-text-body font-medium truncate flex-1 min-w-0">
                {pill.name}
              </span>
              {subtitleText && (
                <span className="text-[10px] text-text-placeholder flex-shrink-0 px-1.5 py-0.5 bg-white rounded">
                  {subtitleText}
                </span>
              )}
              {pill.strength > 0 && (
                <div className="flex-shrink-0 w-8 h-1.5 bg-[#E8E8E8] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-brand-primary rounded-full"
                    style={{ width: `${Math.round(pill.strength * 100)}%` }}
                  />
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ============================================================================
// Overview Tab
// ============================================================================

function OverviewTab({
  feature,
  detail,
  loading,
}: {
  feature: FeatureBRDSummary
  detail: FeatureDetailResponse | null
  loading: boolean
}) {
  const [evidenceExpanded, setEvidenceExpanded] = useState(false)
  const evidence = detail?.evidence || feature.evidence || []

  return (
    <div className="space-y-5">
      {/* Description */}
      {feature.description && (
        <div className="bg-[#F4F4F4] border border-border rounded-xl px-4 py-3">
          <p className="text-[13px] text-text-body leading-relaxed">{feature.description}</p>
        </div>
      )}

      {/* Badges */}
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

      {/* Linked Entities (progressive load) */}
      {loading && !detail ? (
        <Spinner size="sm" label="Loading connections..." />
      ) : detail ? (
        <>
          <LinkedPillGroup
            icon={AlertTriangle}
            title="Why this exists"
            pills={detail.linked_drivers}
            emptyText="No business drivers linked yet"
          />
          <LinkedPillGroup
            icon={Users}
            title="Who needs it"
            pills={detail.linked_personas}
            emptyText="No personas linked yet"
          />
          <LinkedPillGroup
            icon={Workflow}
            title="Where it lives"
            pills={detail.linked_vp_steps}
            emptyText="No workflow steps linked yet"
          />
        </>
      ) : null}

      {/* Evidence strip (collapsed) */}
      {evidence.length > 0 && (
        <div>
          <button
            onClick={() => setEvidenceExpanded(!evidenceExpanded)}
            className="flex items-center gap-1.5 text-[11px] font-medium text-text-placeholder hover:text-[#666666] transition-colors"
          >
            {evidenceExpanded ? (
              <ChevronDown className="w-3 h-3" />
            ) : (
              <ChevronRight className="w-3 h-3" />
            )}
            Evidence ({evidence.length} source{evidence.length !== 1 ? 's' : ''})
          </button>
          {evidenceExpanded && (
            <div className="mt-2">
              <EvidenceBlock evidence={evidence} maxItems={5} />
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!feature.description && evidence.length === 0 && !loading && (
        <EmptyState
          icon={<Puzzle className="w-8 h-8 text-border" />}
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
  revision_number?: number
  revision_type?: string
  change_type?: string
  changes?: Record<string, unknown> | null
  diff_summary?: string
  created_at?: string
  created_by?: string | null
}

function HistoryTab({
  revisions,
  loading,
}: {
  revisions: RevisionItem[]
  loading: boolean
}) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null)

  if (loading && revisions.length === 0) {
    return <Spinner size="sm" label="Loading history..." />
  }

  if (!revisions || revisions.length === 0) {
    return (
      <EmptyState
        icon={<Clock className="w-8 h-8 text-border" />}
        title="No revision history"
        description="Changes will be tracked here as signals are processed."
      />
    )
  }

  return (
    <div className="space-y-3">
      {revisions.map((rev, i) => {
        const isExpanded = expandedIdx === i
        const changeType = rev.revision_type || rev.change_type || 'updated'
        const hasChanges = rev.changes && Object.keys(rev.changes).length > 0

        return (
          <div key={i} className="border border-border rounded-xl px-4 py-3">
            <div className="flex items-center gap-2 mb-1">
              <span
                className={`text-[10px] font-medium uppercase px-1.5 py-0.5 rounded ${
                  REVISION_TYPE_COLORS[changeType] || REVISION_TYPE_COLORS.updated
                }`}
              >
                {changeType}
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
            {hasChanges && (
              <button
                onClick={() => setExpandedIdx(isExpanded ? null : i)}
                className="flex items-center gap-1 mt-2 text-[11px] font-medium text-text-placeholder hover:text-[#666666] transition-colors"
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
              <div className="mt-2 bg-[#F4F4F4] border border-border rounded-lg px-3 py-2">
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
