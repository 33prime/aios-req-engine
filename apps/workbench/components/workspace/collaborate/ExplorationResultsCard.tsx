'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  Sparkles,
  ThumbsUp,
  ThumbsDown,
  Lightbulb,
  Clock,
  ArrowRight,
  Loader2,
} from 'lucide-react'
import { getExplorationResults, feedInspirations } from '@/lib/api/portal'
import type { ClientExplorationResults } from '@/types/portal'

interface ExplorationResultsCardProps {
  projectId: string
  sessionId: string | null
}

export function ExplorationResultsCard({ projectId, sessionId }: ExplorationResultsCardProps) {
  const [results, setResults] = useState<ClientExplorationResults | null>(null)
  const [isExploring, setIsExploring] = useState(true)
  const [feedingInspirations, setFeedingInspirations] = useState(false)

  useEffect(() => {
    if (!sessionId) return
    let cancelled = false

    async function load() {
      try {
        const res = await getExplorationResults(sessionId!)
        if (!cancelled) {
          setResults(res)
          setIsExploring(false)
        }
      } catch {
        // Still exploring — no results yet
        if (!cancelled) setIsExploring(true)
      }
    }

    load()
    // Poll while exploring
    const interval = setInterval(load, 15_000)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [sessionId])

  const handleFeedInspirations = useCallback(async () => {
    if (!sessionId) return
    setFeedingInspirations(true)
    try {
      const res = await feedInspirations(sessionId)
      alert(`${res.signals_created} inspiration(s) fed into discovery`)
    } catch (err) {
      console.error('Failed to feed inspirations:', err)
    } finally {
      setFeedingInspirations(false)
    }
  }, [sessionId])

  if (!sessionId) return null

  // Exploring state — client is actively reviewing
  if (isExploring && !results) {
    return (
      <div className="bg-white rounded-2xl border border-border shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-border/50">
          <div className="flex items-center gap-2.5">
            <Sparkles className="w-4 h-4 text-amber-500" />
            <span className="text-[13px] font-semibold text-text-body">Exploration</span>
            <span className="flex items-center gap-1 px-2 py-0.5 bg-amber-50 text-amber-700 text-[10px] font-medium rounded-full">
              <Clock className="w-3 h-3 animate-pulse" /> Live
            </span>
          </div>
        </div>
        <div className="px-5 py-6 text-center">
          <div className="w-10 h-10 mx-auto mb-2 rounded-full bg-amber-50 flex items-center justify-center">
            <Clock className="w-5 h-5 text-amber-600 animate-pulse" />
          </div>
          <p className="text-[13px] font-medium text-text-body mb-1">Client is exploring the prototype</p>
          <p className="text-[12px] text-text-placeholder">
            Reviewing assumptions and capturing ideas. Results will appear here when done.
          </p>
        </div>
      </div>
    )
  }

  if (!results) return null

  // Count verdicts
  let agrees = 0, disagrees = 0, unanswered = 0
  for (const epic of results.epics) {
    for (const a of epic.assumptions) {
      if (a.response === 'agree' || a.response === 'great') agrees++
      else if (a.response === 'disagree' || a.response === 'refine') disagrees++
      else if (a.response === 'question') unanswered++
      else unanswered++
    }
  }

  return (
    <div className="bg-white rounded-2xl border border-border shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-border/50">
        <div className="flex items-center gap-2.5">
          <Sparkles className="w-4 h-4 text-brand-primary" />
          <span className="text-[13px] font-semibold text-text-body">Exploration Results</span>
          <span className="px-1.5 py-0.5 bg-green-50 text-green-700 text-[10px] font-bold rounded-full">
            Complete
          </span>
        </div>
      </div>

      <div className="px-5 py-4 space-y-4">
        {/* Summary stats */}
        <div className="grid grid-cols-3 gap-2">
          <div className="text-center p-2.5 rounded-xl bg-green-50">
            <ThumbsUp className="w-3.5 h-3.5 mx-auto mb-0.5 text-green-600" />
            <p className="text-base font-semibold text-green-700">{agrees}</p>
            <p className="text-[10px] text-green-600">Agreed</p>
          </div>
          <div className="text-center p-2.5 rounded-xl bg-amber-50">
            <ThumbsDown className="w-3.5 h-3.5 mx-auto mb-0.5 text-amber-600" />
            <p className="text-base font-semibold text-amber-700">{disagrees}</p>
            <p className="text-[10px] text-amber-600">Refined</p>
          </div>
          <div className="text-center p-2.5 rounded-xl bg-gray-50">
            <p className="text-base font-semibold text-gray-500 mt-4">{unanswered}</p>
            <p className="text-[10px] text-gray-400">Skipped</p>
          </div>
        </div>

        {/* Per-epic breakdown */}
        {results.epics.map((epic) => (
          <div key={epic.epic_index} className="rounded-xl border border-border p-3">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-medium text-text-body">{epic.title}</h4>
              {epic.time_spent_seconds != null && (
                <span className="text-[10px] text-text-placeholder flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {Math.round(epic.time_spent_seconds / 60)}m
                </span>
              )}
            </div>
            <div className="space-y-1">
              {epic.assumptions.map((a, i) => (
                <div key={i} className="flex items-start gap-2">
                  {(a.response === 'agree' || a.response === 'great') ? (
                    <ThumbsUp className="w-3.5 h-3.5 text-green-500 mt-0.5 flex-shrink-0" />
                  ) : (a.response === 'disagree' || a.response === 'refine') ? (
                    <ThumbsDown className="w-3.5 h-3.5 text-amber-500 mt-0.5 flex-shrink-0" />
                  ) : (
                    <span className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                  )}
                  <span className={`text-[11px] ${
                    (a.response === 'disagree' || a.response === 'refine') ? 'text-amber-700 font-medium' : 'text-text-body'
                  }`}>
                    {a.text}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}

        {/* Inspirations */}
        {results.inspirations.length > 0 && (
          <div className="rounded-xl border border-border p-3">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-medium text-text-body flex items-center gap-1.5">
                <Lightbulb className="w-4 h-4 text-amber-500" />
                Inspirations ({results.inspirations.length})
              </h4>
              <button
                onClick={handleFeedInspirations}
                disabled={feedingInspirations}
                className="text-[11px] text-brand-primary hover:text-[#25785A] font-medium flex items-center gap-1"
              >
                {feedingInspirations ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <ArrowRight className="w-3 h-3" />
                )}
                Feed into Discovery
              </button>
            </div>
            <div className="space-y-1.5">
              {results.inspirations.map((insp) => (
                <div key={insp.id} className="text-[11px] text-text-body bg-amber-50/50 rounded-lg px-2.5 py-1.5">
                  {insp.text}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Total time */}
        {results.total_time_seconds != null && (
          <p className="text-[11px] text-text-placeholder text-center">
            Total exploration time: {Math.round(results.total_time_seconds / 60)} minutes
          </p>
        )}
      </div>
    </div>
  )
}
