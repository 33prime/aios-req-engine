/**
 * OverviewTab - Executive summary of memory state
 *
 * Shows: health bar, stats, high-confidence beliefs, working hypotheses,
 * strategic insights, evidence base tree, and recent DI Agent activity.
 */

'use client'

import { useState, useEffect } from 'react'
import {
  FileText,
  Brain,
  Lightbulb,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  Eye,
  AlertTriangle,
  TrendingUp,
  Shield,
  Sparkles,
  Zap,
} from 'lucide-react'
import { getDIAgentLogs } from '@/lib/api'
import type { MemoryVisualizationResponse, MemoryNodeViz } from '@/lib/api'

interface OverviewTabProps {
  projectId: string
  data: MemoryVisualizationResponse | null
}

export function OverviewTab({ projectId, data }: OverviewTabProps) {
  const [activityLogs, setActivityLogs] = useState<any[]>([])

  useEffect(() => {
    getDIAgentLogs(projectId, { limit: 5 })
      .then((res) => setActivityLogs(res.logs || []))
      .catch(() => setActivityLogs([]))
  }, [projectId])

  if (!data) {
    return (
      <div className="text-center py-8">
        <Brain className="w-8 h-8 text-gray-300 mx-auto mb-2" />
        <p className="text-sm text-ui-supportText">No memory data yet.</p>
      </div>
    )
  }

  const { stats, nodes, decisions, learnings } = data

  const beliefs = nodes.filter((n) => n.node_type === 'belief')
  const insights = nodes.filter((n) => n.node_type === 'insight')
  const highConfBeliefs = beliefs.filter((b) => b.confidence >= 0.7)
  const workingHypotheses = beliefs.filter((b) => b.confidence >= 0.4 && b.confidence < 0.7)
  const healthPercent = beliefs.length > 0
    ? Math.round((highConfBeliefs.length / beliefs.length) * 100)
    : 0

  // Find newest node timestamp
  const newestNode = nodes.length > 0
    ? nodes.reduce((a, b) => (a.created_at > b.created_at ? a : b))
    : null
  const lastUpdated = newestNode ? formatRelativeTime(newestNode.created_at) : null

  return (
    <div className="space-y-5">
      {/* 1. Memory Health Bar */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs font-semibold text-ui-headingDark">
            Memory Health: {healthPercent}%
          </span>
          {lastUpdated && (
            <span className="text-[11px] text-ui-supportText">Last updated: {lastUpdated}</span>
          )}
        </div>
        <div className="h-2 rounded-full bg-gray-100 overflow-hidden">
          <div
            className="h-full rounded-full bg-brand-teal transition-all duration-500"
            style={{ width: `${healthPercent}%` }}
          />
        </div>
      </div>

      {/* 2. Stats Row */}
      <div className="grid grid-cols-4 gap-3">
        <StatCard icon={FileText} label="Facts" value={stats.facts_count} color="text-emerald-500" bgColor="bg-emerald-50" />
        <StatCard icon={Brain} label="Beliefs" value={stats.beliefs_count} color="text-teal-500" bgColor="bg-teal-50" />
        <StatCard icon={Lightbulb} label="Insights" value={stats.insights_count} color="text-emerald-500" bgColor="bg-emerald-50" />
        <StatCard icon={CheckCircle} label="Decisions" value={decisions.length} color="text-teal-500" bgColor="bg-teal-50" />
      </div>

      {/* 3. High-Confidence Beliefs */}
      {highConfBeliefs.length > 0 && (
        <BeliefSection
          title="Current Understanding"
          beliefs={highConfBeliefs}
        />
      )}

      {/* 4. Working Hypotheses */}
      {workingHypotheses.length > 0 && (
        <BeliefSection
          title="Working Hypotheses — Need More Evidence"
          beliefs={workingHypotheses}
          muted
        />
      )}

      {/* 5. Strategic Insights */}
      {insights.length > 0 && (
        <InsightsSection insights={insights} />
      )}

      {/* 6. Evidence Base */}
      <EvidenceBaseTree stats={stats} decisionsCount={decisions.length} />

      {/* 7. Recent Activity */}
      {activityLogs.length > 0 && (
        <RecentActivity logs={activityLogs} />
      )}
    </div>
  )
}

// --- Sub-components ---

function StatCard({ icon: Icon, label, value, color, bgColor }: {
  icon: typeof FileText
  label: string
  value: number
  color: string
  bgColor: string
}) {
  return (
    <div className="bg-ui-background rounded-lg px-3 py-2.5 flex items-center gap-2.5">
      <div className={`w-7 h-7 rounded-lg ${bgColor} flex items-center justify-center`}>
        <Icon className={`w-3.5 h-3.5 ${color}`} />
      </div>
      <div>
        <p className="text-lg font-semibold text-ui-headingDark leading-tight">{value}</p>
        <p className="text-[11px] text-ui-supportText">{label}</p>
      </div>
    </div>
  )
}

function BeliefSection({ title, beliefs, muted }: {
  title: string
  beliefs: MemoryNodeViz[]
  muted?: boolean
}) {
  return (
    <div>
      <h5 className="text-xs font-semibold text-ui-headingDark uppercase tracking-wide mb-2">
        {title}
      </h5>
      <div className="space-y-2">
        {beliefs.map((belief) => (
          <BeliefCard key={belief.id} belief={belief} muted={muted} />
        ))}
      </div>
    </div>
  )
}

function BeliefCard({ belief, muted }: { belief: MemoryNodeViz; muted?: boolean }) {
  const [expanded, setExpanded] = useState(false)
  const pct = Math.round(belief.confidence * 100)

  return (
    <div className="bg-ui-background rounded-lg px-3 py-2.5">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left flex items-start gap-2"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-0.5">
            <p className="text-sm text-ui-bodyText">{belief.summary}</p>
            <div className="flex items-center gap-2 flex-shrink-0 ml-3">
              <div className="w-16 h-1.5 rounded-full bg-gray-200 overflow-hidden">
                <div
                  className="h-full rounded-full bg-emerald-500 transition-all"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className={`text-[11px] font-medium ${muted ? 'text-ui-supportText' : 'text-emerald-700'}`}>
                {pct}%
              </span>
            </div>
          </div>
          <p className="text-[11px] text-ui-supportText mt-0.5">
            +{belief.support_count} supported
            {belief.contradict_count > 0 && (
              <span className="text-gray-400"> · {belief.contradict_count} contradicted</span>
            )}
          </p>
        </div>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-ui-supportText flex-shrink-0 mt-0.5" />
        ) : (
          <ChevronDown className="w-4 h-4 text-ui-supportText flex-shrink-0 mt-0.5" />
        )}
      </button>
      {expanded && (
        <div className="mt-2 pt-2 border-t border-gray-100">
          <p className="text-sm text-ui-bodyText whitespace-pre-wrap">{belief.content}</p>
          <div className="flex items-center gap-2 mt-2">
            {belief.belief_domain && (
              <span className="inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium bg-teal-50 text-teal-700">
                {belief.belief_domain.replace('_', ' ')}
              </span>
            )}
            {belief.source_type && (
              <span className="text-[10px] text-ui-supportText">
                Source: {belief.source_type}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

const INSIGHT_TYPE_ICONS: Record<string, typeof Eye> = {
  behavioral: Eye,
  contradiction: AlertTriangle,
  evolution: TrendingUp,
  risk: Shield,
  opportunity: Sparkles,
}

function InsightsSection({ insights }: { insights: MemoryNodeViz[] }) {
  // Group by insight_type
  const grouped: Record<string, MemoryNodeViz[]> = {}
  for (const insight of insights) {
    const type = insight.insight_type || 'other'
    if (!grouped[type]) grouped[type] = []
    grouped[type].push(insight)
  }

  return (
    <div>
      <h5 className="text-xs font-semibold text-ui-headingDark uppercase tracking-wide mb-2">
        Strategic Insights
      </h5>
      {Object.entries(grouped).map(([type, items]) => {
        const Icon = INSIGHT_TYPE_ICONS[type] || Lightbulb
        return (
          <div key={type} className="mb-3">
            <div className="flex items-center gap-1.5 mb-1.5">
              <Icon className="w-3.5 h-3.5 text-gray-400" />
              <span className="text-[11px] font-medium text-ui-supportText capitalize">
                {type}
              </span>
            </div>
            <div className="space-y-1.5 pl-5">
              {items.map((insight) => (
                <div key={insight.id} className="bg-gray-50 rounded-lg px-3 py-2">
                  <p className="text-sm text-ui-bodyText">{insight.summary}</p>
                  <span className="text-[11px] text-ui-supportText">
                    {Math.round(insight.confidence * 100)}% confidence
                  </span>
                </div>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}

function EvidenceBaseTree({ stats, decisionsCount }: {
  stats: MemoryVisualizationResponse['stats']
  decisionsCount: number
}) {
  const lines = [
    { prefix: '\u251C\u2500', text: `${stats.facts_count} facts extracted` },
    { prefix: '\u251C\u2500', text: `${stats.beliefs_count} beliefs formed` },
    { prefix: '\u251C\u2500', text: `${decisionsCount} decisions logged` },
    { prefix: '\u2514\u2500', text: `${stats.sources_count || 0} signal sources` },
  ]

  return (
    <div>
      <h5 className="text-xs font-semibold text-ui-headingDark uppercase tracking-wide mb-2">
        Evidence Base
      </h5>
      <div className="bg-ui-background rounded-lg px-3 py-2.5 font-mono text-sm text-ui-bodyText space-y-0.5">
        {lines.map((line, i) => (
          <div key={i}>
            <span className="text-ui-supportText">{line.prefix}</span> {line.text}
          </div>
        ))}
      </div>
    </div>
  )
}

const ACTION_BADGES: Record<string, { label: string; color: string }> = {
  extract: { label: 'Extract', color: 'bg-teal-100 text-teal-700' },
  enrich: { label: 'Enrich', color: 'bg-teal-100 text-teal-700' },
  validate: { label: 'Validate', color: 'bg-emerald-100 text-emerald-700' },
  warn: { label: 'Warning', color: 'bg-gray-100 text-gray-600' },
  observe: { label: 'Observe', color: 'bg-gray-100 text-gray-600' },
}

function RecentActivity({ logs }: { logs: any[] }) {
  return (
    <div>
      <h5 className="text-xs font-semibold text-ui-headingDark uppercase tracking-wide mb-2">
        Recent Activity
      </h5>
      <div className="space-y-0">
        {logs.map((log, idx) => {
          const actionType = log.action_type || 'observe'
          const badge = ACTION_BADGES[actionType] || ACTION_BADGES.observe
          return (
            <div key={log.id || idx} className="flex items-start gap-3 py-2.5 border-b border-gray-100 last:border-0">
              <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium flex-shrink-0 ${badge.color}`}>
                {badge.label}
              </span>
              <p className="text-sm text-ui-bodyText line-clamp-2 flex-1 min-w-0">
                {log.observation || log.decision || 'Agent action completed'}
              </p>
              <span className="text-[11px] text-ui-supportText flex-shrink-0">
                {log.created_at ? formatRelativeTime(log.created_at) : ''}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  const diffHrs = Math.floor(diffMins / 60)
  if (diffHrs < 24) return `${diffHrs}h ago`
  const diffDays = Math.floor(diffHrs / 24)
  return `${diffDays}d ago`
}
