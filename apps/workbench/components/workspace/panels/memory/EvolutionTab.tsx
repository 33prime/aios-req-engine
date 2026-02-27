/**
 * EvolutionTab — Unified timeline with event type filters + confidence curves header
 *
 * Shows beliefs, signals, entities, facts in a single chronological timeline.
 * Top section: confidence curves for top beliefs.
 * Filter by: All, Beliefs, Signals, Entities + time range (7d, 30d, 90d, All).
 */

'use client'

import { useState, useEffect, useMemo } from 'react'
import {
  TrendingUp,
  TrendingDown,
  Upload,
  Lightbulb,
  Zap,
  RefreshCw,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import { getConfidenceCurve } from '@/lib/api'
import { formatDate } from '@/lib/date-utils'
import type { MemoryVisualizationResponse } from '@/lib/api'
import type {
  IntelEvolutionEvent,
  IntelConfidenceCurve,
} from '@/types/workspace'
import { useIntelEvolution } from '@/lib/hooks/use-api'

interface EvolutionTabProps {
  projectId: string
  data: MemoryVisualizationResponse | null
}

type EventFilter = 'all' | 'beliefs' | 'signals' | 'entities'
type TimeRange = 7 | 30 | 90 | 365

export function EvolutionTab({ projectId }: EvolutionTabProps) {
  const [eventFilter, setEventFilter] = useState<EventFilter>('all')
  const [timeRange, setTimeRange] = useState<TimeRange>(30)
  const [curves, setCurves] = useState<IntelConfidenceCurve[]>([])
  const [showCurves, setShowCurves] = useState(true)

  const filterMap: Record<EventFilter, string | undefined> = {
    all: undefined,
    beliefs: 'beliefs',
    signals: 'signals',
    entities: 'entities',
  }

  const { data: evolutionData, isLoading } = useIntelEvolution(projectId, {
    event_type: filterMap[eventFilter],
    days: timeRange,
    limit: 50,
  })

  const events = evolutionData?.events ?? []

  // Load confidence curves for top beliefs
  useEffect(() => {
    const topBeliefIds = events
      .filter((e) => e.entity_type === 'belief' && e.entity_id)
      .map((e) => e.entity_id!)
      .filter((id, idx, arr) => arr.indexOf(id) === idx)
      .slice(0, 3)

    if (topBeliefIds.length === 0) {
      setCurves([])
      return
    }

    Promise.all(
      topBeliefIds.map((id) =>
        getConfidenceCurve(projectId, id).catch(() => null),
      ),
    ).then((results) => {
      setCurves(results.filter((r): r is IntelConfidenceCurve => r !== null && r.points.length > 1))
    })
  }, [projectId, events])

  return (
    <div className="space-y-4">
      {/* Confidence Curves Header */}
      {curves.length > 0 && (
        <div className="bg-white rounded-2xl border border-border p-4 shadow-sm">
          <button
            onClick={() => setShowCurves(!showCurves)}
            className="flex items-center gap-2 text-[12px] font-semibold text-text-body uppercase tracking-wide mb-2"
          >
            Confidence Curves
            {showCurves ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
          {showCurves && (
            <div className="flex gap-4">
              {curves.map((c) => (
                <div key={c.node_id} className="flex-1 min-w-0">
                  <p className="text-[11px] text-[#666666] truncate mb-1">{c.summary}</p>
                  <svg viewBox="0 0 200 40" className="w-full h-8">
                    <polyline
                      fill="none"
                      stroke="#3FAF7A"
                      strokeWidth="2"
                      points={c.points.map((p, i) => {
                        const x = (i / Math.max(c.points.length - 1, 1)) * 200
                        const y = 40 - p.confidence * 40
                        return `${x},${y}`
                      }).join(' ')}
                    />
                  </svg>
                  <div className="flex justify-between text-[9px] text-text-placeholder">
                    <span>{Math.round(c.points[0].confidence * 100)}%</span>
                    <span>{Math.round(c.points[c.points.length - 1].confidence * 100)}%</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="flex gap-1">
          {(['all', 'beliefs', 'signals', 'entities'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setEventFilter(f)}
              className={`px-3 py-1 rounded-lg text-[11px] font-medium transition-colors ${
                eventFilter === f
                  ? 'bg-[#E8F5E9] text-[#25785A]'
                  : 'text-[#666666] hover:text-text-body hover:bg-[#F4F4F4]'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
        <div className="flex gap-1">
          {([7, 30, 90, 365] as const).map((d) => (
            <button
              key={d}
              onClick={() => setTimeRange(d)}
              className={`px-2 py-1 rounded-lg text-[11px] font-medium transition-colors ${
                timeRange === d
                  ? 'bg-[#E8F5E9] text-[#25785A]'
                  : 'text-[#666666] hover:text-text-body hover:bg-[#F4F4F4]'
              }`}
            >
              {d === 365 ? 'All' : `${d}d`}
            </button>
          ))}
        </div>
      </div>

      {/* Timeline */}
      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-brand-primary" />
        </div>
      ) : events.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-sm text-[#666666]">No events in this time range.</p>
        </div>
      ) : (
        <div className="space-y-1">
          {events.map((event, i) => (
            <EventRow key={`${event.timestamp}-${i}`} event={event} />
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Event Row ───────────────────────────────────────────────────────────────

function EventRow({ event }: { event: IntelEvolutionEvent }) {
  const icon = getEventIcon(event.event_type)
  const Icon = icon.component

  return (
    <div className="flex items-start gap-3 bg-white rounded-xl border border-border px-4 py-3 shadow-sm">
      <div className={`p-1.5 rounded-lg ${icon.bg} shrink-0 mt-0.5`}>
        <Icon className={`w-3.5 h-3.5 ${icon.color}`} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-[11px] font-medium text-text-body">
            {formatEventType(event.event_type)}
          </span>
          <span className="text-[10px] text-text-placeholder">
            {formatDate(event.timestamp)}
          </span>
        </div>
        <p className="text-[12px] text-[#666666] leading-relaxed">{event.summary}</p>
        {event.confidence_delta !== null && event.confidence_delta !== 0 && (
          <div className="flex items-center gap-2 mt-1">
            {event.confidence_before !== null && event.confidence_after !== null && (
              <span className="text-[10px] text-text-placeholder">
                {Math.round(event.confidence_before * 100)}% &rarr; {Math.round(event.confidence_after * 100)}%
              </span>
            )}
            <span
              className={`text-[10px] font-medium ${
                event.confidence_delta > 0 ? 'text-brand-primary' : 'text-text-placeholder'
              }`}
            >
              ({event.confidence_delta > 0 ? '+' : ''}{Math.round(event.confidence_delta * 100)}%)
            </span>
          </div>
        )}
        {event.change_reason && event.change_reason !== event.summary && (
          <p className="text-[11px] text-text-placeholder mt-0.5">
            Reason: {event.change_reason}
          </p>
        )}
      </div>
    </div>
  )
}

function getEventIcon(type: string) {
  switch (type) {
    case 'belief_strengthened':
      return { component: TrendingUp, bg: 'bg-[#E8F5E9]', color: 'text-[#25785A]' }
    case 'belief_weakened':
      return { component: TrendingDown, bg: 'bg-gray-100', color: 'text-text-placeholder' }
    case 'belief_created':
    case 'belief_updated':
      return { component: Lightbulb, bg: 'bg-[#E8F5E9]', color: 'text-[#25785A]' }
    case 'belief_superseded':
      return { component: RefreshCw, bg: 'bg-gray-100', color: 'text-[#666666]' }
    case 'signal_processed':
      return { component: Upload, bg: 'bg-gray-100', color: 'text-[#666666]' }
    case 'fact_added':
      return { component: Zap, bg: 'bg-[#E8F5E9]', color: 'text-[#25785A]' }
    default:
      return { component: Zap, bg: 'bg-gray-100', color: 'text-[#666666]' }
  }
}

function formatEventType(type: string): string {
  return type
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

