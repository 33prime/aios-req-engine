'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  Sparkles,
  Eye,
  EyeOff,
  GripVertical,
  Send,
  Clock,
  Loader2,
  Trash2,
  Plus,
  Pencil,
  CheckCircle,
} from 'lucide-react'
import {
  prepareForClient,
  getEpicConfigs,
  updateEpicConfigs,
  shareWithClient,
} from '@/lib/api/portal'
import { getPrototypeForProject, listPrototypeSessions, getPrototypeSession } from '@/lib/api'
import type { EpicConfig } from '@/types/portal'

interface ClientStagingSectionProps {
  projectId: string
  onStateChange?: (state: { sessionId: string | null; reviewState: string | null }) => void
}

type StagingState = 'loading' | 'no_session' | 'not_ready' | 'prepare' | 'staging' | 'shared'

export function ClientStagingSection({ projectId, onStateChange }: ClientStagingSectionProps) {
  const [state, setState] = useState<StagingState>('loading')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [configs, setConfigs] = useState<EpicConfig[]>([])
  const [isProcessing, setIsProcessing] = useState(false)

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

        const session = await getPrototypeSession(latest.id)
        const reviewState = session.review_state || 'not_started'

        // Notify parent of exploration states
        if (reviewState === 'client_complete') {
          onStateChange?.({ sessionId: latest.id, reviewState: 'results' })
          setState('shared')
        } else if (reviewState === 'client_exploring') {
          onStateChange?.({ sessionId: latest.id, reviewState: 'exploring' })
          setState('shared')
        } else if (reviewState === 'staging') {
          const data = await getEpicConfigs(latest.id)
          setConfigs(data.configs || [])
          setState('staging')
          onStateChange?.({ sessionId: latest.id, reviewState: null })
        } else if (reviewState === 'complete' || reviewState === 'ready_for_client') {
          setState('prepare')
          onStateChange?.({ sessionId: latest.id, reviewState: null })
        } else {
          setState('not_ready')
          onStateChange?.({ sessionId: null, reviewState: null })
        }
      } catch {
        setState('no_session')
      }
    }
    load()
  }, [projectId, onStateChange])

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

  const handleUpdateAssumption = useCallback(async (epicIndex: number, assumptionIndex: number, text: string) => {
    const updated = configs.map(c => {
      if (c.epic_index !== epicIndex) return c
      const assumptions = [...(c.assumptions || [])]
      assumptions[assumptionIndex] = { ...assumptions[assumptionIndex], text }
      return { ...c, assumptions }
    })
    setConfigs(updated)
    if (sessionId) {
      await updateEpicConfigs(sessionId, updated).catch(console.error)
    }
  }, [configs, sessionId])

  const handleDeleteAssumption = useCallback(async (epicIndex: number, assumptionIndex: number) => {
    const updated = configs.map(c => {
      if (c.epic_index !== epicIndex) return c
      const assumptions = (c.assumptions || []).filter((_, i) => i !== assumptionIndex)
      return { ...c, assumptions }
    })
    setConfigs(updated)
    if (sessionId) {
      await updateEpicConfigs(sessionId, updated).catch(console.error)
    }
  }, [configs, sessionId])

  const handleAddAssumption = useCallback(async (epicIndex: number) => {
    const updated = configs.map(c => {
      if (c.epic_index !== epicIndex) return c
      const assumptions = [...(c.assumptions || []), { text: '', source_type: 'inferred' }]
      return { ...c, assumptions }
    })
    setConfigs(updated)
  }, [configs])

  const handleShare = useCallback(async () => {
    if (!sessionId) return
    setIsProcessing(true)
    try {
      await shareWithClient(sessionId)
      setState('shared')
      onStateChange?.({ sessionId, reviewState: 'exploring' })
    } catch (err) {
      console.error('Failed to share with client:', err)
    } finally {
      setIsProcessing(false)
    }
  }, [sessionId, onStateChange])

  const enabledCount = configs.filter(c => c.enabled).length
  const totalAssumptions = configs.reduce((sum, c) => sum + (c.assumptions?.length || 0), 0)

  // Don't render at all for states that don't belong in Outbox
  if (state === 'loading') {
    return (
      <div className="bg-white rounded-2xl border border-border shadow-sm p-5 flex justify-center">
        <Loader2 className="w-5 h-5 animate-spin text-text-placeholder" />
      </div>
    )
  }

  if (state === 'no_session' || state === 'not_ready') {
    return null
  }

  return (
    <div className="bg-white rounded-2xl border border-border shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-border/50">
        <div className="flex items-center gap-2.5">
          <Sparkles className="w-4 h-4 text-[#0A1E2F]" />
          <span className="text-[13px] font-semibold text-text-body">
            Client Exploration
          </span>
          {state === 'shared' && (
            <span className="flex items-center gap-1 px-2 py-0.5 bg-green-50 text-green-700 text-[10px] font-medium rounded-full">
              <CheckCircle className="w-3 h-3" /> Shared
            </span>
          )}
        </div>
      </div>

      <div className="px-5 py-4 space-y-4">
        {/* Prepare button */}
        {state === 'prepare' && (
          <div className="text-center py-2">
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

        {/* Staging: edit configs */}
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

                      {/* Assumptions — editable */}
                      <div className="mt-2 space-y-1.5">
                        {(config.assumptions || []).map((a, i) => (
                          <div key={i} className="flex items-center gap-1.5 group">
                            <Pencil className="w-3 h-3 text-text-placeholder shrink-0" />
                            <input
                              type="text"
                              value={a.text}
                              onChange={(e) => {
                                const updated = configs.map(c => {
                                  if (c.epic_index !== config.epic_index) return c
                                  const assumptions = [...(c.assumptions || [])]
                                  assumptions[i] = { ...assumptions[i], text: e.target.value }
                                  return { ...c, assumptions }
                                })
                                setConfigs(updated)
                              }}
                              onBlur={() => handleUpdateAssumption(config.epic_index, i, a.text)}
                              placeholder="Type an assumption..."
                              className="flex-1 text-[11px] px-2 py-1 border border-border/50 rounded-lg focus:ring-1 focus:ring-brand-primary/20 focus:border-brand-primary placeholder:text-text-placeholder"
                            />
                            <button
                              onClick={() => handleDeleteAssumption(config.epic_index, i)}
                              className="opacity-0 group-hover:opacity-100 transition-opacity"
                              title="Remove assumption"
                            >
                              <Trash2 className="w-3.5 h-3.5 text-text-placeholder hover:text-red-500" />
                            </button>
                          </div>
                        ))}
                        {(config.assumptions?.length || 0) < 3 && (
                          <button
                            onClick={() => handleAddAssumption(config.epic_index)}
                            className="flex items-center gap-1 text-[10px] text-text-placeholder hover:text-brand-primary transition-colors"
                          >
                            <Plus className="w-3 h-3" /> Add assumption
                          </button>
                        )}
                      </div>

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

        {/* Shared confirmation */}
        {state === 'shared' && (
          <div className="flex items-center gap-2 text-[12px] text-green-700 bg-green-50/50 rounded-lg px-3 py-2">
            <CheckCircle className="w-4 h-4 flex-shrink-0" />
            Shared with client. Check Inbox for exploration progress and results.
          </div>
        )}
      </div>
    </div>
  )
}
