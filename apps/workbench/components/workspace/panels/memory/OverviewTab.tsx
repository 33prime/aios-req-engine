/**
 * OverviewTab — Intelligence overview with briefing narrative, open threads,
 * hypotheses, pulse stats, and recent activity.
 *
 * Two-column layout: left 60% (narrative + threads + hypotheses + changes),
 * right 40% (pulse stats + recent activity).
 */

'use client'

import { useCallback } from 'react'
import {
  TrendingUp,
  TrendingDown,
  Zap,
  Upload,
  Lightbulb,
  ThumbsUp,
  ThumbsDown,
  GitBranch,
  ArrowLeftRight,
  FlaskConical,
} from 'lucide-react'
import { submitNodeFeedback, getIntelligenceOverview } from '@/lib/api'
import type { MemoryVisualizationResponse } from '@/lib/api'
import type {
  IntelOverviewResponse,
  IntelRecentActivity,
  Tension,
  Hypothesis,
} from '@/types/workspace'
import { useIntelOverview } from '@/lib/hooks/use-api'

interface OverviewTabProps {
  projectId: string
  data: MemoryVisualizationResponse | null
}

export function OverviewTab({ projectId, data: vizData }: OverviewTabProps) {
  const { data: overview, isLoading, mutate } = useIntelOverview(projectId)

  const handleHypothesisFeedback = useCallback(
    async (nodeId: string, action: 'confirm' | 'dispute') => {
      try {
        await submitNodeFeedback(projectId, nodeId, action)
        mutate()
      } catch {
        // Silent fail
      }
    },
    [projectId, mutate],
  )

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#3FAF7A]" />
      </div>
    )
  }

  if (!overview) {
    return <FallbackOverview data={vizData} />
  }

  const pulse = overview.pulse
  const narrative = overview.narrative
  const wysk = overview.what_you_should_know
  const tensions = overview.tensions as Tension[]
  const hypotheses = overview.hypotheses as Hypothesis[]
  const whatChanged = overview.what_changed as Record<string, unknown>
  const changes = (whatChanged?.changes as Array<Record<string, unknown>>) || []

  return (
    <div className="grid grid-cols-5 gap-6">
      {/* Left column — 3/5 */}
      <div className="col-span-3 space-y-6">
        {/* Narrative */}
        {narrative ? (
          <div className="bg-white rounded-2xl border border-[#E5E5E5] p-5 shadow-sm">
            <p className="text-sm text-[#333333] leading-relaxed">{narrative}</p>
          </div>
        ) : null}

        {/* What You Should Know */}
        {wysk?.narrative ? (
          <div className="bg-[#F4F4F4] rounded-2xl p-5">
            <h4 className="text-[12px] font-semibold text-[#333333] uppercase tracking-wide mb-2">
              What You Should Know
            </h4>
            <p className="text-[13px] text-[#666666] leading-relaxed">
              {String(wysk.narrative)}
            </p>
            {Array.isArray(wysk.bullets) && (
              <ul className="mt-2 space-y-1">
                {(wysk.bullets as string[]).map((b: string, i: number) => (
                  <li key={i} className="text-[12px] text-[#666666] flex items-start gap-2">
                    <span className="text-[#3FAF7A] mt-0.5">-</span>
                    {b}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ) : null}

        {/* Open Threads (formerly "Active Tensions") */}
        {tensions.length > 0 && (
          <div>
            <h4 className="text-[12px] font-semibold text-[#333333] uppercase tracking-wide mb-3">
              Open Threads
            </h4>
            <div className="space-y-2">
              {tensions.slice(0, 3).map((t, i) => (
                <div
                  key={t.tension_id || i}
                  className="bg-white rounded-xl border border-[#E5E5E5] px-4 py-3 shadow-sm"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <ArrowLeftRight className="w-3.5 h-3.5 text-[#666666]" />
                    <span className="text-[12px] font-medium text-[#333333]">
                      {t.summary}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-[11px] text-[#999999]">
                    <span>{t.side_a}</span>
                    <span className="text-[#CCCCCC]">&harr;</span>
                    <span>{t.side_b}</span>
                    <span className="ml-auto font-medium text-[#666666]">
                      {Math.round((t.confidence || 0) * 100)}% confidence
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Hypotheses */}
        {hypotheses.length > 0 && (
          <div>
            <h4 className="text-[12px] font-semibold text-[#333333] uppercase tracking-wide mb-3">
              Active Hypotheses
            </h4>
            <div className="space-y-2">
              {hypotheses.slice(0, 5).map((h) => (
                <div
                  key={h.hypothesis_id}
                  className="bg-white rounded-xl border border-[#E5E5E5] px-4 py-3 shadow-sm"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-2 min-w-0">
                      <FlaskConical className="w-3.5 h-3.5 text-[#666666] mt-0.5 shrink-0" />
                      <div className="min-w-0">
                        <p className="text-[12px] font-medium text-[#333333] truncate">
                          {h.statement}
                        </p>
                        <div className="flex items-center gap-2 mt-1 text-[10px] text-[#999999]">
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-[#F0F0F0] text-[#666666]">
                            {h.status}
                          </span>
                          <span>{Math.round((h.confidence || 0) * 100)}%</span>
                          {h.evidence_for > 0 && <span>{h.evidence_for} supporting</span>}
                          {h.evidence_against > 0 && <span>{h.evidence_against} against</span>}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        onClick={() => handleHypothesisFeedback(h.hypothesis_id, 'confirm')}
                        className="p-1 rounded hover:bg-[#E8F5E9] text-[#999999] hover:text-[#25785A] transition-colors"
                        title="Confirm"
                      >
                        <ThumbsUp className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleHypothesisFeedback(h.hypothesis_id, 'dispute')}
                        className="p-1 rounded hover:bg-gray-100 text-[#999999] hover:text-[#666666] transition-colors"
                        title="Dispute"
                      >
                        <ThumbsDown className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                  {h.test_suggestion && (
                    <p className="text-[11px] text-[#3FAF7A] mt-1.5 ml-5">
                      Test: {h.test_suggestion}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* What Changed */}
        {changes.length > 0 && (
          <div>
            <h4 className="text-[12px] font-semibold text-[#333333] uppercase tracking-wide mb-3">
              What Changed
            </h4>
            <p className="text-[12px] text-[#666666]">
              {(whatChanged?.change_summary as string) || `${changes.length} changes since last session`}
            </p>
          </div>
        )}
      </div>

      {/* Right column — 2/5 */}
      <div className="col-span-2 space-y-6">
        {/* Pulse Stats */}
        <div className="bg-white rounded-2xl border border-[#E5E5E5] p-5 shadow-sm">
          <h4 className="text-[12px] font-semibold text-[#333333] uppercase tracking-wide mb-3">
            Pulse
          </h4>
          <div className="grid grid-cols-2 gap-3">
            <StatCell label="Nodes" value={pulse.total_nodes} />
            <StatCell label="Edges" value={pulse.total_edges} />
            <StatCell label="Avg Confidence" value={`${Math.round(pulse.avg_confidence * 100)}%`} />
            <StatCell label="Hypotheses" value={pulse.hypotheses_count} />
            <StatCell label="Open Threads" value={pulse.tensions_count} />
            <StatCell label="Confirmed" value={pulse.confirmed_count} color="green" />
            <StatCell label="Under Review" value={pulse.disputed_count} />
            <StatCell
              label="Last Signal"
              value={pulse.days_since_signal !== null ? `${pulse.days_since_signal}d ago` : 'Never'}
            />
          </div>
        </div>

        {/* Recent Activity */}
        {overview.recent_activity.length > 0 && (
          <div className="bg-white rounded-2xl border border-[#E5E5E5] p-5 shadow-sm">
            <h4 className="text-[12px] font-semibold text-[#333333] uppercase tracking-wide mb-3">
              Recent Activity
            </h4>
            <div className="space-y-2.5">
              {overview.recent_activity.slice(0, 8).map((item, i) => (
                <ActivityRow key={i} item={item} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function StatCell({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="bg-[#F4F4F4] rounded-lg px-3 py-2">
      <p className="text-[10px] text-[#999999] mb-0.5">{label}</p>
      <p className={`text-sm font-semibold ${color === 'green' ? 'text-[#3FAF7A]' : 'text-[#333333]'}`}>
        {value}
      </p>
    </div>
  )
}

function ActivityRow({ item }: { item: IntelRecentActivity }) {
  const icon = getActivityIcon(item.event_type)
  const Icon = icon.component

  return (
    <div className="flex items-start gap-2.5">
      <div className={`p-1 rounded ${icon.bg} shrink-0 mt-0.5`}>
        <Icon className={`w-3 h-3 ${icon.color}`} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-[11px] text-[#333333] truncate">{item.summary}</p>
        <div className="flex items-center gap-2 mt-0.5">
          {item.confidence_delta !== null && item.confidence_delta !== 0 && (
            <span className={`text-[10px] font-medium ${
              item.confidence_delta > 0 ? 'text-[#3FAF7A]' : 'text-[#999999]'
            }`}>
              {item.confidence_delta > 0 ? '+' : ''}{Math.round(item.confidence_delta * 100)}%
            </span>
          )}
          <span className="text-[10px] text-[#999999]">
            {formatTimeAgo(item.timestamp)}
          </span>
        </div>
      </div>
    </div>
  )
}

function getActivityIcon(type: string) {
  switch (type) {
    case 'belief_strengthened':
      return { component: TrendingUp, bg: 'bg-[#E8F5E9]', color: 'text-[#25785A]' }
    case 'belief_weakened':
      return { component: TrendingDown, bg: 'bg-gray-100', color: 'text-[#999999]' }
    case 'signal_processed':
      return { component: Upload, bg: 'bg-gray-100', color: 'text-[#666666]' }
    case 'fact_added':
      return { component: Lightbulb, bg: 'bg-[#E8F5E9]', color: 'text-[#25785A]' }
    default:
      return { component: Zap, bg: 'bg-gray-100', color: 'text-[#666666]' }
  }
}

function formatTimeAgo(ts: string): string {
  if (!ts) return ''
  const diff = Date.now() - new Date(ts).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

// ─── Fallback for when no intelligence data exists ───────────────────────────

function FallbackOverview({ data }: { data: MemoryVisualizationResponse | null }) {
  if (!data) {
    return (
      <div className="text-center py-12">
        <p className="text-sm text-[#666666]">No intelligence data yet.</p>
        <p className="text-xs text-[#999999] mt-1">Process signals to build the knowledge graph.</p>
      </div>
    )
  }

  const stats = data.stats
  return (
    <div className="grid grid-cols-4 gap-4">
      <StatCell label="Facts" value={stats.facts_count} />
      <StatCell label="Beliefs" value={stats.beliefs_count} />
      <StatCell label="Insights" value={stats.insights_count} />
      <StatCell label="Edges" value={stats.total_edges} />
    </div>
  )
}
