/**
 * EvolutionTab - Belief history timeline
 *
 * Lists all beliefs sorted by most recently changed.
 * Click to expand: lazy-loads belief history, shows CSS sparkline and
 * a vertical timeline of confidence changes.
 */

'use client'

import { useState } from 'react'
import { ChevronDown, ChevronUp, ArrowUp, ArrowDown, Minus } from 'lucide-react'
import { getBeliefHistory } from '@/lib/api'
import type { MemoryVisualizationResponse, MemoryNodeViz, BeliefHistoryEntry } from '@/lib/api'

interface EvolutionTabProps {
  projectId: string
  data: MemoryVisualizationResponse | null
}

export function EvolutionTab({ projectId, data }: EvolutionTabProps) {
  const [domainFilter, setDomainFilter] = useState<string | null>(null)

  if (!data || data.nodes.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-sm text-ui-supportText">No beliefs to track yet.</p>
      </div>
    )
  }

  let beliefs = data.nodes
    .filter((n) => n.node_type === 'belief')
    .sort((a, b) => b.created_at.localeCompare(a.created_at))

  // Collect unique domains for filter
  const domains = Array.from(new Set(beliefs.map((b) => b.belief_domain).filter(Boolean))) as string[]

  if (domainFilter) {
    beliefs = beliefs.filter((b) => b.belief_domain === domainFilter)
  }

  if (beliefs.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-sm text-ui-supportText">No beliefs formed yet.</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Domain filter */}
      {domains.length > 1 && (
        <div className="flex items-center gap-2 mb-2">
          <span className="text-[11px] text-ui-supportText">Filter:</span>
          <button
            onClick={() => setDomainFilter(null)}
            className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-colors ${
              !domainFilter ? 'bg-brand-teal/10 text-brand-teal' : 'text-ui-supportText hover:text-ui-headingDark'
            }`}
          >
            All
          </button>
          {domains.map((domain) => (
            <button
              key={domain}
              onClick={() => setDomainFilter(domainFilter === domain ? null : domain)}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-colors ${
                domainFilter === domain ? 'bg-brand-teal/10 text-brand-teal' : 'text-ui-supportText hover:text-ui-headingDark'
              }`}
            >
              {domain.replace('_', ' ')}
            </button>
          ))}
        </div>
      )}

      {beliefs.map((belief) => (
        <BeliefEvolutionCard
          key={belief.id}
          belief={belief}
          projectId={projectId}
          allNodes={data.nodes}
        />
      ))}
    </div>
  )
}

function BeliefEvolutionCard({ belief, projectId, allNodes }: {
  belief: MemoryNodeViz
  projectId: string
  allNodes: MemoryNodeViz[]
}) {
  const [expanded, setExpanded] = useState(false)
  const [history, setHistory] = useState<BeliefHistoryEntry[] | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const pct = Math.round(belief.confidence * 100)

  const handleExpand = async () => {
    if (expanded) {
      setExpanded(false)
      return
    }
    setExpanded(true)
    if (!history) {
      setIsLoading(true)
      try {
        const result = await getBeliefHistory(projectId, belief.id)
        setHistory(result.history)
      } catch {
        setHistory([])
      } finally {
        setIsLoading(false)
      }
    }
  }

  return (
    <div className="bg-ui-background rounded-lg overflow-hidden">
      <button
        onClick={handleExpand}
        className="w-full text-left px-4 py-3 flex items-center gap-3"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-0.5">
            <p className="text-sm text-ui-bodyText">{belief.summary}</p>
            <div className="flex items-center gap-2 flex-shrink-0 ml-3">
              <div className="w-16 h-1.5 rounded-full bg-gray-200 overflow-hidden">
                <div
                  className="h-full rounded-full bg-emerald-500"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-[11px] font-medium text-emerald-700">
                {pct}%
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            {belief.belief_domain && (
              <span className="inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium bg-teal-50 text-teal-700">
                {belief.belief_domain.replace('_', ' ')}
              </span>
            )}
          </div>
        </div>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-ui-supportText flex-shrink-0" />
        ) : (
          <ChevronDown className="w-4 h-4 text-ui-supportText flex-shrink-0" />
        )}
      </button>

      {expanded && (
        <div className="px-4 pb-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-4">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-brand-teal" />
            </div>
          ) : history && history.length > 0 ? (
            <>
              {/* CSS Sparkline */}
              <ConfidenceSparkline history={history} currentConfidence={belief.confidence} />

              {/* Timeline entries */}
              <div className="mt-3 space-y-0">
                {history.map((entry) => (
                  <HistoryEntryRow
                    key={entry.id}
                    entry={entry}
                    allNodes={allNodes}
                  />
                ))}
              </div>
            </>
          ) : (
            <p className="text-[11px] text-ui-supportText py-2">
              No history recorded for this belief yet.
            </p>
          )}
        </div>
      )}
    </div>
  )
}

function ConfidenceSparkline({ history, currentConfidence }: {
  history: BeliefHistoryEntry[]
  currentConfidence: number
}) {
  // Build data points: oldest first, then current value
  const reversed = [...history].reverse()
  const points = reversed.map((h) => h.new_confidence)
  points.push(currentConfidence)

  if (points.length < 2) return null

  const width = 200
  const height = 30
  const padding = 4
  const maxY = 1
  const minY = 0

  const xStep = (width - padding * 2) / (points.length - 1)
  const yScale = (height - padding * 2) / (maxY - minY)

  const pointCoords = points.map((p, i) => ({
    x: padding + i * xStep,
    y: height - padding - (p - minY) * yScale,
  }))

  const polylinePoints = pointCoords.map((c) => `${c.x},${c.y}`).join(' ')

  return (
    <div className="mb-2">
      <svg width={width} height={height} className="overflow-visible">
        <polyline
          points={polylinePoints}
          fill="none"
          stroke="#10b981"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
        {pointCoords.map((c, i) => (
          <circle
            key={i}
            cx={c.x}
            cy={c.y}
            r="2.5"
            fill="#10b981"
            stroke="white"
            strokeWidth="1"
          />
        ))}
      </svg>
    </div>
  )
}

const CHANGE_TYPE_BADGES: Record<string, { label: string; className: string }> = {
  confidence_increase: { label: '\u2191 Increased', className: 'bg-emerald-50 text-emerald-700' },
  confidence_decrease: { label: '\u2193 Decreased', className: 'bg-gray-100 text-gray-600' },
  content_refined: { label: 'Refined', className: 'bg-teal-50 text-teal-700' },
  content_changed: { label: 'Changed', className: 'bg-teal-50 text-teal-700' },
  superseded: { label: 'Superseded', className: 'bg-gray-100 text-gray-500' },
  archived: { label: 'Archived', className: 'bg-gray-100 text-gray-400' },
}

function HistoryEntryRow({ entry, allNodes }: {
  entry: BeliefHistoryEntry
  allNodes: MemoryNodeViz[]
}) {
  const badge = CHANGE_TYPE_BADGES[entry.change_type] || {
    label: entry.change_type,
    className: 'bg-gray-100 text-gray-600',
  }

  const prevPct = Math.round(entry.previous_confidence * 100)
  const newPct = Math.round(entry.new_confidence * 100)
  const isIncrease = entry.new_confidence > entry.previous_confidence
  const isDecrease = entry.new_confidence < entry.previous_confidence

  // Resolve triggered_by node summary
  const triggeredByNode = entry.triggered_by_node_id
    ? allNodes.find((n) => n.id === entry.triggered_by_node_id)
    : null

  const dateStr = new Date(entry.created_at).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  })

  return (
    <div className="flex items-start gap-3 py-2.5 border-b border-gray-100 last:border-0">
      {/* Date pill */}
      <span className="text-[10px] text-ui-supportText bg-white px-2 py-0.5 rounded-full flex-shrink-0 mt-0.5">
        {dateStr}
      </span>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          {/* Change type badge */}
          <span className={`inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium ${badge.className}`}>
            {badge.label}
          </span>

          {/* Confidence delta */}
          <span className="flex items-center gap-0.5 text-[11px]">
            <span className="text-ui-supportText">{prevPct}%</span>
            <span className="text-ui-supportText">&rarr;</span>
            <span className={isIncrease ? 'text-emerald-600 font-medium' : isDecrease ? 'text-gray-500 font-medium' : 'text-ui-supportText'}>
              {newPct}%
            </span>
            {isIncrease && <ArrowUp className="w-3 h-3 text-emerald-500" />}
            {isDecrease && <ArrowDown className="w-3 h-3 text-gray-400" />}
            {!isIncrease && !isDecrease && <Minus className="w-3 h-3 text-gray-300" />}
          </span>
        </div>

        {/* Reason */}
        <p className="text-[11px] text-ui-bodyText">{entry.change_reason}</p>

        {/* Triggered by */}
        {triggeredByNode && (
          <p className="text-[10px] text-ui-supportText mt-0.5">
            Triggered by: {triggeredByNode.summary}
          </p>
        )}
      </div>
    </div>
  )
}
