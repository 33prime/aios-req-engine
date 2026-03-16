'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  Layers,
  ExternalLink,
  Loader2,
  Clock,
  ThumbsUp,
  ThumbsDown,
  Lightbulb,
  ArrowRight,
  Monitor,
  Sparkles,
} from 'lucide-react'
import {
  getPrototypeForProject,
  listPrototypeSessions,
  getPrototypeSession,
} from '@/lib/api'
import { getExplorationResults, feedInspirations } from '@/lib/api/portal'
import type { Prototype, PrototypeSession } from '@/types/prototype'
import type { ClientExplorationResults } from '@/types/portal'

interface PrototypeStatusCardProps {
  projectId: string
  onNavigateToBuild?: () => void
}

type ProtoState = 'loading' | 'no_prototype' | 'building' | 'active' | 'client_exploring' | 'complete'

export function PrototypeStatusCard({ projectId, onNavigateToBuild }: PrototypeStatusCardProps) {
  const [state, setState] = useState<ProtoState>('loading')
  const [prototype, setPrototype] = useState<Prototype | null>(null)
  const [sessions, setSessions] = useState<PrototypeSession[]>([])
  const [latestSession, setLatestSession] = useState<PrototypeSession | null>(null)
  const [results, setResults] = useState<ClientExplorationResults | null>(null)
  const [feedingInspirations, setFeedingInspirations] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const proto = await getPrototypeForProject(projectId)
        if (cancelled) return
        if (!proto?.id) {
          setState('no_prototype')
          return
        }
        setPrototype(proto)

        if (proto.status === 'pending' || proto.status === 'generating') {
          setState('building')
          return
        }

        const sessionList = await listPrototypeSessions(proto.id)
        if (cancelled) return
        setSessions(sessionList ?? [])

        if (!sessionList?.length) {
          setState('active')
          return
        }

        const latest = sessionList[sessionList.length - 1]
        const session = await getPrototypeSession(latest.id)
        if (cancelled) return
        setLatestSession(session)

        if (session.review_state === 'client_exploring') {
          setState('client_exploring')
        } else if (session.review_state === 'client_complete') {
          try {
            const res = await getExplorationResults(session.id)
            if (!cancelled) setResults(res)
          } catch { /* no results yet */ }
          setState('complete')
        } else {
          setState('active')
        }
      } catch {
        if (!cancelled) setState('no_prototype')
      }
    }
    load()
    return () => { cancelled = true }
  }, [projectId])

  const handleFeedInspirations = useCallback(async () => {
    if (!latestSession) return
    setFeedingInspirations(true)
    try {
      const res = await feedInspirations(latestSession.id)
      alert(`${res.signals_created} inspiration(s) fed into discovery`)
    } catch (err) {
      console.error('Failed to feed inspirations:', err)
    } finally {
      setFeedingInspirations(false)
    }
  }, [latestSession])

  // Compute verdict counts from results
  const verdictCounts = results ? (() => {
    let agreed = 0, refined = 0, questioned = 0
    for (const epic of results.epics) {
      for (const a of epic.assumptions) {
        if (a.response === 'agree' || a.response === 'great') agreed++
        else if (a.response === 'refine' || a.response === 'disagree') refined++
        else if (a.response === 'question') questioned++
      }
    }
    return { agreed, refined, questioned }
  })() : null

  if (state === 'loading') {
    return (
      <div className="bg-white rounded-2xl border border-border shadow-sm p-5 flex justify-center">
        <Loader2 className="w-5 h-5 animate-spin text-text-placeholder" />
      </div>
    )
  }

  if (state === 'no_prototype') {
    return (
      <div className="bg-white rounded-2xl border border-border shadow-sm p-5">
        <div className="flex items-center gap-2.5 mb-3">
          <Layers className="w-4 h-4 text-text-placeholder" />
          <span className="text-[13px] font-semibold text-text-body">Prototype</span>
        </div>
        <div className="text-center py-3">
          <Monitor className="w-6 h-6 mx-auto mb-2 text-border" />
          <p className="text-[12px] text-text-placeholder mb-3">No prototype yet</p>
          {onNavigateToBuild && (
            <button
              onClick={onNavigateToBuild}
              className="px-4 py-2 bg-brand-primary text-white text-[12px] font-medium rounded-lg hover:bg-[#25785A] transition-colors flex items-center gap-1.5 mx-auto"
            >
              <Sparkles className="w-3.5 h-3.5" />
              Generate Prototype
            </button>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-2xl border border-border shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-border/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Layers className="w-4 h-4 text-[#0A1E2F]" />
            <span className="text-[13px] font-semibold text-text-body">Prototype</span>
            {sessions.length > 0 && (
              <span className="px-1.5 py-0.5 bg-[#0A1E2F]/8 text-[#0A1E2F] text-[10px] font-bold rounded-full">
                Session {sessions.length}
              </span>
            )}
          </div>
          {/* State pill */}
          {state === 'building' && (
            <span className="flex items-center gap-1 px-2 py-0.5 bg-blue-50 text-blue-600 text-[10px] font-medium rounded-full">
              <Loader2 className="w-3 h-3 animate-spin" /> Generating
            </span>
          )}
          {state === 'client_exploring' && (
            <span className="flex items-center gap-1 px-2 py-0.5 bg-amber-50 text-amber-700 text-[10px] font-medium rounded-full">
              <Clock className="w-3 h-3 animate-pulse" /> Client exploring
            </span>
          )}
          {state === 'complete' && (
            <span className="px-2 py-0.5 bg-green-50 text-green-700 text-[10px] font-bold rounded-full">
              Complete
            </span>
          )}
          {state === 'active' && latestSession?.review_state && (
            <span className="px-2 py-0.5 bg-surface-muted text-text-placeholder text-[10px] font-medium rounded-full">
              {latestSession.review_state.replace(/_/g, ' ')}
            </span>
          )}
        </div>
      </div>

      <div className="px-5 py-4 space-y-3">
        {/* Deploy URL — always shown when prototype exists */}
        {prototype?.deploy_url && (
          <a
            href={prototype.deploy_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 text-[13px] text-brand-primary hover:text-[#25785A] font-medium transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            {prototype.deploy_url.replace(/^https?:\/\//, '').slice(0, 40)}
          </a>
        )}

        {/* Building state */}
        {state === 'building' && (
          <p className="text-[12px] text-text-placeholder">
            Prototype is being generated. This may take a few minutes.
          </p>
        )}

        {/* Client exploring */}
        {state === 'client_exploring' && (
          <div className="flex items-center gap-2 text-[12px] text-amber-700 bg-amber-50/50 rounded-lg px-3 py-2">
            <Clock className="w-4 h-4 animate-pulse flex-shrink-0" />
            Client is reviewing assumptions. Results will appear when they finish.
          </div>
        )}

        {/* Complete with verdicts */}
        {state === 'complete' && verdictCounts && (
          <>
            <div className="grid grid-cols-3 gap-2">
              <div className="text-center p-2.5 rounded-xl bg-green-50">
                <ThumbsUp className="w-3.5 h-3.5 mx-auto mb-0.5 text-green-600" />
                <p className="text-base font-semibold text-green-700">{verdictCounts.agreed}</p>
                <p className="text-[10px] text-green-600">Agreed</p>
              </div>
              <div className="text-center p-2.5 rounded-xl bg-amber-50">
                <ThumbsDown className="w-3.5 h-3.5 mx-auto mb-0.5 text-amber-600" />
                <p className="text-base font-semibold text-amber-700">{verdictCounts.refined}</p>
                <p className="text-[10px] text-amber-600">Refined</p>
              </div>
              <div className="text-center p-2.5 rounded-xl bg-purple-50">
                <Lightbulb className="w-3.5 h-3.5 mx-auto mb-0.5 text-purple-600" />
                <p className="text-base font-semibold text-purple-700">{verdictCounts.questioned}</p>
                <p className="text-[10px] text-purple-600">Questioned</p>
              </div>
            </div>

            {/* Inspirations count + feed button */}
            {results && results.inspirations.length > 0 && (
              <div className="flex items-center justify-between">
                <span className="text-[12px] text-text-placeholder">
                  {results.inspirations.length} inspiration{results.inspirations.length !== 1 ? 's' : ''} captured
                </span>
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
            )}

            {/* Total time */}
            {results?.total_time_seconds != null && (
              <p className="text-[11px] text-text-placeholder">
                Total exploration: {Math.round(results.total_time_seconds / 60)} min
              </p>
            )}
          </>
        )}
      </div>
    </div>
  )
}
