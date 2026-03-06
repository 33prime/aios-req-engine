'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  Sparkles,
  ChevronDown,
  ChevronRight,
  Eye,
  EyeOff,
  GripVertical,
  Send,
  ThumbsUp,
  ThumbsDown,
  Lightbulb,
  Clock,
  Loader2,
  ArrowRight,
} from 'lucide-react'
import {
  prepareForClient,
  getEpicConfigs,
  updateEpicConfigs,
  shareWithClient,
  getExplorationResults,
  feedInspirations,
} from '@/lib/api/portal'
import { getPrototypeForProject, listPrototypeSessions, getPrototypeSession } from '@/lib/api'
import type { EpicConfig, ClientExplorationResults } from '@/types/portal'

interface ClientStagingSectionProps {
  projectId: string
}

type StagingState = 'loading' | 'no_session' | 'not_ready' | 'prepare' | 'staging' | 'exploring' | 'results'

export function ClientStagingSection({ projectId }: ClientStagingSectionProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [state, setState] = useState<StagingState>('loading')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [configs, setConfigs] = useState<EpicConfig[]>([])
  const [results, setResults] = useState<ClientExplorationResults | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [feedingInspirations, setFeedingInspirations] = useState(false)

  // Load session and determine state
  useEffect(() => {
    async function load() {
      try {
        const proto = await getPrototypeForProject(projectId)
        if (!proto?.id) {
          setState('no_session')
          return
        }
        const sessions = await listPrototypeSessions(proto.id)
        if (!sessions?.length) {
          setState('no_session')
          return
        }
        const latest = sessions[sessions.length - 1]
        setSessionId(latest.id)

        // Get fresh session data for review_state
        const session = await getPrototypeSession(latest.id)
        const reviewState = session.review_state || 'not_started'

        if (reviewState === 'client_complete') {
          const res = await getExplorationResults(latest.id)
          setResults(res)
          setState('results')
        } else if (reviewState === 'client_exploring') {
          setState('exploring')
        } else if (reviewState === 'staging') {
          const data = await getEpicConfigs(latest.id)
          setConfigs(data.configs || [])
          setState('staging')
        } else if (reviewState === 'complete' || reviewState === 'ready_for_client') {
          setState('prepare')
        } else {
          setState('not_ready')
        }
      } catch {
        setState('no_session')
      }
    }
    load()
  }, [projectId])

  const handlePrepare = useCallback(async () => {
    if (!sessionId) return
    setIsProcessing(true)
    try {
      await prepareForClient(sessionId)
      const data = await getEpicConfigs(sessionId)
      setConfigs(data.configs || [])
      setState('staging')
    } catch (err) {
      console.error('Failed to prepare for client:', err)
    } finally {
      setIsProcessing(false)
    }
  }, [sessionId])

  const handleToggleEpic = useCallback(async (epicIndex: number) => {
    const updated = configs.map(c =>
      c.epic_index === epicIndex ? { ...c, enabled: !c.enabled } : c
    )
    setConfigs(updated)
    if (sessionId) {
      await updateEpicConfigs(sessionId, updated).catch(console.error)
    }
  }, [configs, sessionId])

  const handleUpdateNote = useCallback(async (epicIndex: number, note: string) => {
    const updated = configs.map(c =>
      c.epic_index === epicIndex ? { ...c, consultant_note: note || null } : c
    )
    setConfigs(updated)
    if (sessionId) {
      await updateEpicConfigs(sessionId, updated).catch(console.error)
    }
  }, [configs, sessionId])

  const handleShare = useCallback(async () => {
    if (!sessionId) return
    setIsProcessing(true)
    try {
      await shareWithClient(sessionId)
      setState('exploring')
    } catch (err) {
      console.error('Failed to share with client:', err)
    } finally {
      setIsProcessing(false)
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

  const enabledCount = configs.filter(c => c.enabled).length
  const totalAssumptions = configs.reduce((sum, c) => sum + (c.assumptions?.length || 0), 0)

  const sectionLabel = state === 'results' ? 'Client Exploration Results'
    : state === 'exploring' ? 'Client Exploring...'
    : 'Client Exploration'

  return (
    <div className="bg-white rounded-2xl border border-border shadow-sm overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-surface-page transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <Sparkles className="w-4 h-4 text-brand-primary" />
          <span className="text-[11px] uppercase tracking-wider text-text-placeholder font-semibold">
            {sectionLabel}
          </span>
          {state === 'exploring' && (
            <span className="flex items-center gap-1 px-2 py-0.5 bg-amber-50 text-amber-700 text-[10px] font-medium rounded-full">
              <Clock className="w-3 h-3" /> Live
            </span>
          )}
          {state === 'results' && (
            <span className="px-1.5 py-0.5 bg-green-50 text-green-700 text-[10px] font-bold rounded-full">
              Complete
            </span>
          )}
        </div>
        {isOpen ? <ChevronDown className="w-4 h-4 text-text-placeholder" /> : <ChevronRight className="w-4 h-4 text-text-placeholder" />}
      </button>

      {isOpen && (
        <div className="px-5 pb-5 space-y-4">
          {/* ── Loading ── */}
          {state === 'loading' && (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="w-5 h-5 animate-spin text-text-placeholder" />
            </div>
          )}

          {/* ── No session or not ready ── */}
          {(state === 'no_session' || state === 'not_ready') && (
            <div className="text-center py-4">
              <Sparkles className="w-8 h-8 mx-auto mb-2 text-border" />
              <p className="text-[12px] text-text-placeholder">
                {state === 'no_session'
                  ? 'No prototype session found'
                  : 'Complete the consultant review first'}
              </p>
            </div>
          )}

          {/* ── Prepare button ── */}
          {state === 'prepare' && (
            <div className="text-center py-4">
              <p className="text-[12px] text-text-body mb-3">
                Review is complete. Generate assumptions for the client to validate before the call.
              </p>
              <button
                onClick={handlePrepare}
                disabled={isProcessing}
                className="px-5 py-2.5 bg-brand-primary text-white text-sm font-medium rounded-xl hover:bg-[#25785A] transition-all disabled:opacity-50"
              >
                {isProcessing ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" /> Generating Assumptions...
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4" /> Prepare for Client
                  </span>
                )}
              </button>
            </div>
          )}

          {/* ── Staging: edit configs ── */}
          {state === 'staging' && (
            <>
              <div className="flex items-center justify-between">
                <p className="text-[12px] text-text-placeholder">
                  {enabledCount} epic{enabledCount !== 1 ? 's' : ''} enabled · {totalAssumptions} assumptions
                </p>
                <button
                  onClick={handleShare}
                  disabled={isProcessing || enabledCount === 0}
                  className="px-4 py-2 bg-brand-primary text-white text-xs font-medium rounded-lg hover:bg-[#25785A] transition-all disabled:opacity-50 flex items-center gap-1.5"
                >
                  {isProcessing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                  Share with Client
                </button>
              </div>

              <div className="space-y-2">
                {configs.map((config) => (
                  <div
                    key={config.epic_index}
                    className={`rounded-xl border p-3 transition-all ${
                      config.enabled ? 'border-border bg-white' : 'border-border/50 bg-gray-50 opacity-60'
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      <GripVertical className="w-4 h-4 text-text-placeholder mt-0.5 flex-shrink-0 cursor-grab" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <h4 className="text-sm font-medium text-text-body truncate">
                            {config.title || `Epic ${config.epic_index + 1}`}
                          </h4>
                          <button
                            onClick={() => handleToggleEpic(config.epic_index)}
                            className="flex-shrink-0 ml-2"
                            title={config.enabled ? 'Hide from client' : 'Show to client'}
                          >
                            {config.enabled ? (
                              <Eye className="w-4 h-4 text-brand-primary" />
                            ) : (
                              <EyeOff className="w-4 h-4 text-text-placeholder" />
                            )}
                          </button>
                        </div>

                        {/* Assumptions preview */}
                        {config.assumptions?.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            {config.assumptions.map((a, i) => (
                              <span
                                key={i}
                                className="text-[10px] px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full"
                                title={a.text}
                              >
                                {a.text.length > 50 ? a.text.slice(0, 50) + '...' : a.text}
                              </span>
                            ))}
                          </div>
                        )}

                        {/* Consultant note */}
                        <input
                          type="text"
                          value={config.consultant_note || ''}
                          onChange={(e) => {
                            const updated = configs.map(c =>
                              c.epic_index === config.epic_index
                                ? { ...c, consultant_note: e.target.value || null }
                                : c
                            )
                            setConfigs(updated)
                          }}
                          onBlur={() => handleUpdateNote(config.epic_index, config.consultant_note || '')}
                          placeholder="Add a note for the client..."
                          className="mt-2 w-full text-[11px] px-2 py-1.5 border border-border/50 rounded-lg focus:ring-1 focus:ring-brand-primary/20 focus:border-brand-primary placeholder:text-text-placeholder"
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          {/* ── Client exploring (live status) ── */}
          {state === 'exploring' && (
            <div className="text-center py-6">
              <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-amber-50 flex items-center justify-center">
                <Clock className="w-6 h-6 text-amber-600 animate-pulse" />
              </div>
              <p className="text-sm font-medium text-text-body mb-1">Client is exploring the prototype</p>
              <p className="text-[12px] text-text-placeholder">
                They&apos;re reviewing assumptions and capturing new ideas. Results will appear here when they&apos;re done.
              </p>
            </div>
          )}

          {/* ── Results ── */}
          {state === 'results' && results && (
            <>
              {/* Summary stats */}
              <div className="grid grid-cols-3 gap-3">
                {(() => {
                  let agrees = 0, disagrees = 0, unanswered = 0
                  for (const epic of results.epics) {
                    for (const a of epic.assumptions) {
                      if (a.response === 'agree') agrees++
                      else if (a.response === 'disagree') disagrees++
                      else unanswered++
                    }
                  }
                  return (
                    <>
                      <div className="text-center p-3 rounded-xl bg-green-50">
                        <ThumbsUp className="w-4 h-4 mx-auto mb-1 text-green-600" />
                        <p className="text-lg font-semibold text-green-700">{agrees}</p>
                        <p className="text-[10px] text-green-600">Agreed</p>
                      </div>
                      <div className="text-center p-3 rounded-xl bg-amber-50">
                        <ThumbsDown className="w-4 h-4 mx-auto mb-1 text-amber-600" />
                        <p className="text-lg font-semibold text-amber-700">{disagrees}</p>
                        <p className="text-[10px] text-amber-600">Disagreed</p>
                      </div>
                      <div className="text-center p-3 rounded-xl bg-gray-50">
                        <p className="text-lg font-semibold text-gray-500 mt-5">{unanswered}</p>
                        <p className="text-[10px] text-gray-400">Skipped</p>
                      </div>
                    </>
                  )
                })()}
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
                        {a.response === 'agree' ? (
                          <ThumbsUp className="w-3.5 h-3.5 text-green-500 mt-0.5 flex-shrink-0" />
                        ) : a.response === 'disagree' ? (
                          <ThumbsDown className="w-3.5 h-3.5 text-amber-500 mt-0.5 flex-shrink-0" />
                        ) : (
                          <span className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                        )}
                        <span className={`text-[11px] ${
                          a.response === 'disagree' ? 'text-amber-700 font-medium' : 'text-text-body'
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
                      Client Inspirations ({results.inspirations.length})
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
            </>
          )}
        </div>
      )}
    </div>
  )
}
