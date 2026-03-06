'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { useParams, useSearchParams } from 'next/navigation'
import { usePortal } from '../PortalShell'
import PrototypeFrame from '@/components/prototype/PrototypeFrame'
import { Spinner } from '@/components/ui/Spinner'
import { getPrototypeClientData, submitFeatureVerdict, completeClientReview, getPrototypeForProject, listPrototypeSessions } from '@/lib/api'
import {
  getStakeholderReview,
  submitStakeholderEpicVerdict,
  getClientExploration,
  submitAssumptionResponse,
  submitExplorationEvent,
  completeExploration,
} from '@/lib/api/portal'
import { ExplorationWelcome } from '@/components/portal/ExplorationWelcome'
import { ExplorationSummary } from '@/components/portal/ExplorationSummary'
import { StationChat } from '@/components/portal/StationChat'
import { ExplorationNav } from '@/components/portal/ExplorationNav'
import { StakeholderInviteModal } from '@/components/portal/StakeholderInviteModal'
import { X, CheckCircle, Pencil, HelpCircle, Share2 } from 'lucide-react'
import type { FeatureVerdict } from '@/types/prototype'
import type { PrototypeFrameHandle } from '@/components/prototype/PrototypeFrame'
import type { StakeholderReviewData, VerdictType, ClientExplorationData, AssumptionResponseType } from '@/types/portal'

interface FeatureReview {
  feature_name: string
  overlay_id: string
  consultant_verdict: FeatureVerdict | null
  consultant_notes: string | null
  suggested_verdict: FeatureVerdict | null
  validation_question: string | null
  validation_why: string | null
  validation_area: string | null
  spec_summary: string | null
  implementation_status: string | null
  confidence: number
  status: string
}

const VERDICT_OPTIONS: { value: FeatureVerdict; label: string; icon: string }[] = [
  { value: 'aligned', label: 'Aligned', icon: '\u2713' },
  { value: 'needs_adjustment', label: 'Needs Adjustment', icon: '\u26A0' },
  { value: 'off_track', label: 'Off Track', icon: '\u2717' },
]

const VERDICT_STYLES: Record<FeatureVerdict, { button: string; active: string }> = {
  aligned: {
    button: 'border-border hover:border-brand-primary hover:bg-[#E8F5E9]',
    active: 'border-brand-primary bg-[#E8F5E9] text-[#25785A]',
  },
  needs_adjustment: {
    button: 'border-border hover:border-amber-400 hover:bg-amber-50',
    active: 'border-amber-400 bg-amber-50 text-amber-800',
  },
  off_track: {
    button: 'border-border hover:border-red-400 hover:bg-red-50',
    active: 'border-red-400 bg-red-50 text-red-800',
  },
}

const EPIC_VERDICT_STYLES: Record<VerdictType, { button: string; active: string }> = {
  confirmed: {
    button: 'border-border hover:border-green-400 hover:bg-green-50',
    active: 'border-green-400 bg-green-50 text-green-800',
  },
  refine: {
    button: 'border-border hover:border-amber-400 hover:bg-amber-50',
    active: 'border-amber-400 bg-amber-50 text-amber-800',
  },
  flag: {
    button: 'border-border hover:border-red-400 hover:bg-red-50',
    active: 'border-red-400 bg-red-50 text-red-800',
  },
}

/**
 * Client prototype review page.
 *
 * Three modes:
 * 1. Token-based (legacy) — feature-level verdicts via magic link
 * 2. Stakeholder-aware — epic-level verdicts from portal nav, with assignment highlighting
 * 3. Exploration mode — assumption-based pre-call exploration (Portal v2)
 */
export default function PortalPrototypePage() {
  const params = useParams()
  const searchParams = useSearchParams()
  const { setChatConfig, chatOpen, setChatOpen } = usePortal()
  const projectId = params.projectId as string
  const token = searchParams.get('token') || ''
  const sessionId = searchParams.get('session') || ''
  const mode = searchParams.get('mode') || ''

  // Legacy feature mode
  const [deployUrl, setDeployUrl] = useState<string | null>(null)
  const [prototypeId, setPrototypeId] = useState<string | null>(null)
  const [featureReviews, setFeatureReviews] = useState<FeatureReview[]>([])
  const [clientVerdicts, setClientVerdicts] = useState<Record<string, FeatureVerdict>>({})
  const [clientNotes, setClientNotes] = useState<Record<string, string>>({})

  // Stakeholder epic mode
  const [stakeholderData, setStakeholderData] = useState<StakeholderReviewData | null>(null)
  const [epicVerdicts, setEpicVerdicts] = useState<Record<number, VerdictType>>({})
  const [epicNotes, setEpicNotes] = useState<Record<number, string>>({})

  // Exploration mode (Portal v2)
  const [explorationData, setExplorationData] = useState<ClientExplorationData | null>(null)
  const [explorationPhase, setExplorationPhase] = useState<'welcome' | 'tour' | 'summary' | 'done'>('welcome')
  const [currentEpicIndex, setCurrentEpicIndex] = useState(0)
  const [assumptionResponses, setAssumptionResponses] = useState<Record<string, AssumptionResponseType>>({})
  const [inspirationCount, setInspirationCount] = useState(0)
  const [activeTab, setActiveTab] = useState<'overview' | 'discuss'>('overview')
  const [contextCard, setContextCard] = useState<{ type: 'refine' | 'question'; assumptionText: string } | null>(null)
  const [showShareModal, setShowShareModal] = useState(false)
  const protoFrameRef = useRef<PrototypeFrameHandle>(null)
  const [bridgeReady, setBridgeReady] = useState(false)
  const explorationStarted = useRef(false)

  const [submitted, setSubmitted] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const isTokenMode = !!token && !!sessionId
  const isExplorationMode = mode === 'explore' || (!!explorationData && !isTokenMode && !stakeholderData)
  // Resolve session ID: URL param or from loaded exploration data
  const resolvedSessionId = sessionId || explorationData?.session_id || ''

  // No longer hiding sidebar — it stays visible and is user-collapsible

  // Register prototype-aware chat config — knows which epic is active
  const currentEpic = explorationData?.epics?.[currentEpicIndex]
  useEffect(() => {
    setChatConfig({
      station: 'epic',
      title: currentEpic?.title ? `Discussing: ${currentEpic.title}` : 'Prototype Review',
      greeting: currentEpic?.title
        ? `Let's talk about the "${currentEpic.title}" experience. What do you think of what you see? Anything surprising or missing?`
        : "I can help you explore your prototype. Click through the app and let me know what you think!",
      customPanel: true,
    })
    return () => setChatConfig(null)
  }, [setChatConfig, currentEpic?.title])

  useEffect(() => {
    async function load() {
      try {
        if (isTokenMode) {
          console.log('[proto-debug] Loading: token mode', { sessionId })
          const data = await getPrototypeClientData(sessionId, token)
          console.log('[proto-debug] Token mode response:', { deploy_url: data.deploy_url, features: data.feature_reviews?.length })
          setPrototypeId(data.prototype_id)
          setDeployUrl(data.deploy_url)
          setFeatureReviews(data.feature_reviews || [])
        } else if (sessionId && mode === 'explore') {
          console.log('[proto-debug] Loading: explore mode', { sessionId })
          const data = await getClientExploration(sessionId)
          console.log('[proto-debug] Explore response:', { deploy_url: data.deploy_url, epics: data.epics?.length })
          setExplorationData(data)
          setDeployUrl(data.deploy_url || null)
        } else if (sessionId) {
          console.log('[proto-debug] Loading: session mode (try explore, fallback stakeholder)', { sessionId })
          try {
            const data = await getClientExploration(sessionId)
            console.log('[proto-debug] Exploration response:', { deploy_url: data.deploy_url, epics: data.epics?.length })
            if (data.epics?.length > 0) {
              setExplorationData(data)
              setDeployUrl(data.deploy_url || null)
            } else {
              throw new Error('No exploration epics')
            }
          } catch {
            console.log('[proto-debug] Falling back to stakeholder review')
            const data = await getStakeholderReview(sessionId)
            console.log('[proto-debug] Stakeholder response:', { deploy_url: data.deploy_url, epics: data.epics?.length })
            setStakeholderData(data)
            setDeployUrl(data.deploy_url || null)
            const existing: Record<number, VerdictType> = {}
            for (const e of data.epics) {
              if (e.verdict) existing[e.index] = e.verdict as VerdictType
            }
            setEpicVerdicts(existing)
          }
        } else {
          console.log('[proto-debug] Loading: auto-discover mode', { projectId })
          try {
            const proto = await getPrototypeForProject(projectId)
            console.log('[proto-debug] Prototype lookup:', { id: proto?.id })
            if (proto?.id) {
              const sessions = await listPrototypeSessions(proto.id)
              console.log('[proto-debug] Sessions:', sessions?.map((s: { id: string; review_state: string | null }) => ({ id: s.id, state: s.review_state })))
              const exploring = sessions?.find(
                (s: { review_state: string | null }) =>
                  s.review_state === 'client_exploring' || s.review_state === 'client_complete'
              )
              if (exploring) {
                console.log('[proto-debug] Found session:', exploring.id)
                const data = await getClientExploration(exploring.id)
                console.log('[proto-debug] Exploration response:', { deploy_url: data.deploy_url, epics: data.epics?.length })
                if (data.epics?.length > 0) {
                  setExplorationData(data)
                  setDeployUrl(data.deploy_url || null)
                } else {
                  setError('No prototype session available. Check back when your consultant shares one.')
                }
              } else {
                console.log('[proto-debug] No exploring/complete session found')
                setError('No prototype session available. Check back when your consultant shares one.')
              }
            } else {
              console.log('[proto-debug] No prototype found for project')
              setError('No prototype session available. Check back when your consultant shares one.')
            }
          } catch (err) {
            console.log('[proto-debug] Auto-discover error:', err)
            setError('No prototype session available. Check back when your consultant shares one.')
          }
        }
      } catch (err) {
        console.log('[proto-debug] Top-level load error:', err)
        setError('Unable to load prototype review.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [sessionId, token, isTokenMode, mode])

  // Legacy feature handlers
  const handleVerdictClick = useCallback(async (overlayId: string, verdict: FeatureVerdict) => {
    setClientVerdicts((prev) => ({ ...prev, [overlayId]: verdict }))
    if (prototypeId) {
      try {
        await submitFeatureVerdict(prototypeId, overlayId, verdict, 'client', clientNotes[overlayId] || undefined)
      } catch (err) {
        console.error('Failed to save client verdict:', err)
      }
    }
  }, [prototypeId, clientNotes])

  const handleNotesBlur = useCallback(async (overlayId: string) => {
    const verdict = clientVerdicts[overlayId]
    if (!verdict || !prototypeId) return
    try {
      await submitFeatureVerdict(prototypeId, overlayId, verdict, 'client', clientNotes[overlayId] || undefined)
    } catch (err) {
      console.error('Failed to save client notes:', err)
    }
  }, [prototypeId, clientVerdicts, clientNotes])

  // Stakeholder epic handlers
  const handleEpicVerdict = useCallback(async (epicIndex: number, verdict: VerdictType) => {
    setEpicVerdicts((prev) => ({ ...prev, [epicIndex]: verdict }))
    if (sessionId) {
      try {
        await submitStakeholderEpicVerdict(sessionId, {
          card_type: 'vision',
          card_index: epicIndex,
          verdict,
          notes: epicNotes[epicIndex],
        })
      } catch (err) {
        console.error('Failed to save epic verdict:', err)
      }
    }
  }, [sessionId, epicNotes])

  const handleEpicNotesBlur = useCallback(async (epicIndex: number) => {
    const verdict = epicVerdicts[epicIndex]
    if (!verdict || !sessionId) return
    try {
      await submitStakeholderEpicVerdict(sessionId, {
        card_type: 'vision',
        card_index: epicIndex,
        verdict,
        notes: epicNotes[epicIndex],
      })
    } catch (err) {
      console.error('Failed to save epic notes:', err)
    }
  }, [sessionId, epicVerdicts, epicNotes])

  // Exploration mode handlers
  const handleExplorationStart = useCallback(() => {
    setExplorationPhase('tour')
    setCurrentEpicIndex(0)
    if (resolvedSessionId && !explorationStarted.current) {
      explorationStarted.current = true
      submitExplorationEvent(resolvedSessionId, { event_type: 'session_start' }).catch(console.error)
    }
  }, [resolvedSessionId])

  const handleAssumptionResponse = useCallback(async (assumptionIndex: number, response: AssumptionResponseType) => {
    if (!explorationData) return
    const epic = explorationData.epics[currentEpicIndex]
    if (!epic) return

    const key = `${epic.index}-${assumptionIndex}`
    setAssumptionResponses(prev => ({ ...prev, [key]: response }))

    if (resolvedSessionId) {
      submitAssumptionResponse(resolvedSessionId, {
        epic_index: epic.index,
        assumption_index: assumptionIndex,
        response,
      }).catch(console.error)
    }

    // Open chat panel with context for refine/question
    if (response === 'refine' || response === 'question') {
      const assumption = epic.assumptions[assumptionIndex]
      if (assumption) {
        setContextCard({ type: response, assumptionText: assumption.text })
        setActiveTab('discuss')
        setChatOpen(true)
      }
    }
  }, [explorationData, currentEpicIndex, resolvedSessionId, setChatOpen])

  const handleEpicNavigate = useCallback((newIndex: number) => {
    if (!explorationData) return
    const oldEpic = explorationData.epics[currentEpicIndex]
    const newEpic = explorationData.epics[newIndex]
    if (oldEpic && resolvedSessionId) {
      submitExplorationEvent(resolvedSessionId, { event_type: 'epic_leave', epic_index: oldEpic.index }).catch(console.error)
    }
    setCurrentEpicIndex(newIndex)
    setContextCard(null)
    if (newEpic && resolvedSessionId) {
      submitExplorationEvent(resolvedSessionId, { event_type: 'epic_view', epic_index: newEpic.index }).catch(console.error)
    }
  }, [explorationData, currentEpicIndex, resolvedSessionId])

  const handleExplorationNext = useCallback(() => {
    if (!explorationData) return
    if (currentEpicIndex < explorationData.epics.length - 1) {
      handleEpicNavigate(currentEpicIndex + 1)
    } else {
      // Last epic — go to summary
      const oldEpic = explorationData.epics[currentEpicIndex]
      if (oldEpic && resolvedSessionId) {
        submitExplorationEvent(resolvedSessionId, { event_type: 'epic_leave', epic_index: oldEpic.index }).catch(console.error)
      }
      setExplorationPhase('summary')
    }
  }, [explorationData, currentEpicIndex, handleEpicNavigate, resolvedSessionId])

  const handleExplorationPrev = useCallback(() => {
    if (currentEpicIndex > 0) {
      handleEpicNavigate(currentEpicIndex - 1)
    }
  }, [currentEpicIndex, handleEpicNavigate])

  // Navigate prototype SPA via postMessage when epic changes (same pattern as BuildPhaseView)
  useEffect(() => {
    if (!explorationData || !deployUrl) return
    const epic = explorationData.epics[currentEpicIndex]
    const route = epic?.primary_route
    if (!route) return

    if (bridgeReady && protoFrameRef.current) {
      // SPA navigation via bridge — no page reload
      protoFrameRef.current.sendMessage({ type: 'aios:navigate', path: route })
    }
  }, [currentEpicIndex, explorationData, deployUrl, bridgeReady])

  const handleExplorationComplete = useCallback(async () => {
    if (!resolvedSessionId) return
    setSubmitting(true)
    try {
      await completeExploration(resolvedSessionId)
      setExplorationPhase('done')
      setSubmitted(true)
    } catch (err) {
      console.error('Failed to complete exploration:', err)
    } finally {
      setSubmitting(false)
    }
  }, [resolvedSessionId])

  const handleCompleteReview = async () => {
    setSubmitting(true)
    try {
      if (isTokenMode) {
        await completeClientReview(sessionId, token)
      }
    } catch (err) {
      console.error('Failed to complete review:', err)
    }
    setSubmitted(true)
    setSubmitting(false)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Spinner size="lg" label="Loading prototype review..." />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center max-w-md">
          <h2 className="text-lg font-semibold text-text-primary mb-2">Review Unavailable</h2>
          <p className="text-sm text-text-muted">{error}</p>
        </div>
      </div>
    )
  }

  if (submitted) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-green-50 flex items-center justify-center">
            <span className="text-2xl text-green-600">{'\u2713'}</span>
          </div>
          <h2 className="text-lg font-semibold text-text-primary mb-2">Thank You!</h2>
          <p className="text-sm text-text-muted">
            Your review has been submitted. The team will incorporate your feedback.
          </p>
        </div>
      </div>
    )
  }

  // ── Exploration Mode (Portal v2) ──────────────────────────────────
  if (isExplorationMode && explorationData) {
    const epics = explorationData.epics
    const currentEpic = epics[currentEpicIndex]

    // Compute assumption counts for summary
    let totalAssumptions = 0
    let greatCount = 0
    let refineCount = 0
    let questionCount = 0
    for (const epic of epics) {
      for (let i = 0; i < epic.assumptions.length; i++) {
        totalAssumptions++
        const key = `${epic.index}-${i}`
        const r = assumptionResponses[key]
        if (r === 'great' || r === 'agree') greatCount++
        else if (r === 'refine') refineCount++
        else if (r === 'question' || r === 'disagree') questionCount++
      }
    }

    if (explorationPhase === 'summary' || explorationPhase === 'done') {
      if (submitted) {
        return (
          <div className="flex items-center justify-center min-h-[calc(100vh-80px)] bg-gradient-to-b from-[#0A1E2F] to-[#15314A]">
            <div className="text-center max-w-md px-6">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-brand-primary/20 flex items-center justify-center">
                <span className="text-2xl text-brand-primary">{'\u2713'}</span>
              </div>
              <h2 className="text-xl font-semibold text-white mb-2">Thank You!</h2>
              <p className="text-sm text-white/60">
                Your exploration is complete. Your consultant will review your feedback before the call.
              </p>
            </div>
          </div>
        )
      }

      return (
        <ExplorationSummary
          epics={epics.map(epic => ({
            index: epic.index,
            title: epic.title,
            assumptions: epic.assumptions.map((a, i) => ({
              text: a.text,
              response: assumptionResponses[`${epic.index}-${i}`] || null,
            })),
          }))}
          consultantName={explorationData.consultant_name || undefined}
          bookingUrl={explorationData.booking_url || undefined}
          onComplete={handleExplorationComplete}
          isSubmitting={submitting}
        />
      )
    }

    // Tour phase — epic by epic
    const currentResponses: Record<number, AssumptionResponseType> = {}
    if (currentEpic) {
      for (let i = 0; i < currentEpic.assumptions.length; i++) {
        const key = `${currentEpic.index}-${i}`
        if (assumptionResponses[key]) {
          currentResponses[i] = assumptionResponses[key]
        }
      }
    }

    return (
      <div className="flex flex-col h-full bg-surface-page">
        {/* Nav bar — full width */}
        <div className="bg-accent px-4 py-2 flex-shrink-0">
          <ExplorationNav
            currentIndex={currentEpicIndex}
            totalEpics={epics.length}
            epicTitles={epics.map(e => e.title)}
            onPrevious={handleExplorationPrev}
            onNext={handleExplorationNext}
            onNavigate={handleEpicNavigate}
            onShare={() => setShowShareModal(true)}
          />
        </div>

        {/* Content — iframe + optional panel */}
        <div className="flex flex-1 min-h-0">
          {/* Iframe — fills remaining space */}
          <div className="flex-1 min-h-0 h-full relative">
            {deployUrl ? (
              <PrototypeFrame
                ref={protoFrameRef}
                deployUrl={deployUrl}
                onFeatureClick={() => {}}
                onPageChange={() => {}}
                onIframeReady={() => setBridgeReady(true)}
              />
            ) : (
              <div className="flex items-center justify-center h-full text-text-placeholder">
                Prototype preview unavailable
              </div>
            )}
          </div>

          {/* Right panel — toggled by chat bubble */}
          {chatOpen && (
            <div className="w-[400px] flex-shrink-0 border-l border-border flex flex-col bg-white">
              {/* Panel header with close */}
              <div className="flex items-center justify-between px-4 py-2 border-b border-border">
                <span className="text-sm font-medium text-text-primary">
                  {currentEpic?.title || 'Prototype Review'}
                </span>
                <button
                  onClick={() => setChatOpen(false)}
                  className="p-1 rounded hover:bg-surface-subtle transition-colors text-text-muted hover:text-text-primary"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Tab bar */}
              <div className="flex border-b border-border">
                <button
                  onClick={() => setActiveTab('overview')}
                  className={`flex-1 px-4 py-2.5 text-sm font-medium transition-colors ${
                    activeTab === 'overview'
                      ? 'text-brand-primary border-b-2 border-brand-primary'
                      : 'text-text-muted hover:text-text-primary'
                  }`}
                >
                  Overview
                </button>
                <button
                  onClick={() => setActiveTab('discuss')}
                  className={`flex-1 px-4 py-2.5 text-sm font-medium transition-colors ${
                    activeTab === 'discuss'
                      ? 'text-brand-primary border-b-2 border-brand-primary'
                      : 'text-text-muted hover:text-text-primary'
                  }`}
                >
                  Discuss
                </button>
              </div>

              {/* Tab content */}
              {activeTab === 'overview' ? (
                <>
                  {/* Overview — scrollable */}
                  <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
                    {currentEpic && (
                      <>
                        <h3 className="text-base font-semibold text-text-primary">{currentEpic.title}</h3>

                        {currentEpic.consultant_note && (
                          <div className="bg-brand-primary-light rounded-lg px-3 py-2 border border-brand-primary/20">
                            <p className="text-[10px] uppercase tracking-wide text-brand-primary font-medium mb-0.5">From your consultant</p>
                            <p className="text-xs text-text-body">{currentEpic.consultant_note}</p>
                          </div>
                        )}

                        {currentEpic.features.length > 0 && (
                          <div className="flex flex-wrap gap-1.5">
                            {currentEpic.features.map((f, i) => (
                              <span key={i} className="text-[11px] bg-surface-subtle text-text-muted px-2.5 py-1 rounded-full">{f.name}</span>
                            ))}
                          </div>
                        )}

                        {currentEpic.assumptions.length > 0 && (
                          <div className="space-y-2.5 pt-1">
                            <p className="text-[10px] uppercase tracking-wide text-text-placeholder font-medium">Assumptions</p>
                            {currentEpic.assumptions.map((a, i) => {
                              const response = currentResponses[i]
                              return (
                                <div key={i} className="space-y-1.5">
                                  <p className="text-xs text-text-secondary leading-relaxed">{a.text}</p>
                                  <div className="flex gap-1.5">
                                    <button
                                      onClick={() => handleAssumptionResponse(i, 'great')}
                                      className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all border ${
                                        response === 'great' || response === 'agree'
                                          ? 'bg-brand-primary-light text-brand-primary border-brand-primary/30'
                                          : 'text-text-muted border-border hover:bg-brand-primary-light hover:text-brand-primary hover:border-brand-primary/20'
                                      }`}
                                    >
                                      <CheckCircle className="w-3 h-3" />
                                      Great
                                    </button>
                                    <button
                                      onClick={() => handleAssumptionResponse(i, 'refine')}
                                      className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all border ${
                                        response === 'refine'
                                          ? 'bg-surface-subtle text-text-primary border-text-muted/30'
                                          : 'text-text-muted border-border hover:bg-surface-subtle hover:text-text-primary hover:border-text-muted/20'
                                      }`}
                                    >
                                      <Pencil className="w-3 h-3" />
                                      Refine
                                    </button>
                                    <button
                                      onClick={() => handleAssumptionResponse(i, 'question')}
                                      className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all border ${
                                        response === 'question' || response === 'disagree'
                                          ? 'bg-accent/10 text-accent border-accent/30'
                                          : 'text-text-muted border-border hover:bg-accent/5 hover:text-accent hover:border-accent/20'
                                      }`}
                                    >
                                      <HelpCircle className="w-3 h-3" />
                                      Question
                                    </button>
                                  </div>
                                </div>
                              )
                            })}
                          </div>
                        )}
                      </>
                    )}
                  </div>

                  {/* Next button — pinned bottom */}
                  <div className="flex-shrink-0 px-4 py-3 border-t border-border bg-white">
                    <button
                      onClick={handleExplorationNext}
                      className="w-full px-4 py-2.5 bg-brand-primary text-white text-sm font-medium rounded-xl hover:bg-brand-primary-hover transition-all"
                    >
                      {currentEpicIndex < epics.length - 1 ? 'Next Area' : 'Review Summary'}
                    </button>
                  </div>
                </>
              ) : (
                /* Discuss tab — StationChat fills remaining space */
                <StationChat
                  projectId={projectId}
                  station="epic"
                  greeting={
                    contextCard
                      ? contextCard.type === 'refine'
                        ? `You\u2019d like to refine: \u201C${contextCard.assumptionText}\u201D \u2014 what would you adjust?`
                        : `You have a question about: \u201C${contextCard.assumptionText}\u201D \u2014 ask away!`
                      : currentEpic?.title
                        ? `Let\u2019s talk about the \u201C${currentEpic.title}\u201D experience. What do you think of what you see?`
                        : 'What do you think of the prototype so far?'
                  }
                  epicTitle={currentEpic?.title}
                  epicNarrative={currentEpic?.narrative}
                  assumptionText={contextCard?.assumptionText}
                  consultantName={explorationData.consultant_name || undefined}
                />
              )}
            </div>
          )}
        </div>

        {/* Welcome modal overlay — prototype loads behind */}
        {explorationPhase === 'welcome' && (
          <ExplorationWelcome
            isModal
            projectName={explorationData.project_name}
            consultantName={explorationData.consultant_name}
            epicCount={epics.length}
            onStart={handleExplorationStart}
          />
        )}

        {/* Stakeholder invite modal */}
        {showShareModal && (
          <StakeholderInviteModal
            projectId={projectId}
            sessionId={explorationData.session_id}
            onClose={() => setShowShareModal(false)}
          />
        )}
      </div>
    )
  }

  // ── Stakeholder Epic Review Mode ─────────────────────────────────
  if (stakeholderData && !isTokenMode) {
    return (
      <div className="flex flex-col h-full">
        {/* Prototype iframe — top 55% */}
        <div className="flex-[55] min-h-0">
          {deployUrl ? (
            <PrototypeFrame
              deployUrl={deployUrl}
              onFeatureClick={() => {}}
              onPageChange={() => {}}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-text-placeholder">
              Prototype preview unavailable
            </div>
          )}
        </div>

        {/* Epic review cards — bottom 45% */}
        <div className="flex-[45] border-t border-border bg-surface-page overflow-y-auto">
          <div className="max-w-3xl mx-auto p-6 space-y-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-text-muted">
                {Object.keys(epicVerdicts).length}/{stakeholderData.total_epics} epics reviewed
              </span>
            </div>

            {stakeholderData.epics.map((epic) => {
              const selectedVerdict = epicVerdicts[epic.index] || null
              const notes = epicNotes[epic.index] || ''

              return (
                <div
                  key={epic.index}
                  className={`
                    rounded-lg border bg-surface-card shadow-sm
                    ${epic.is_assigned_to_me && !selectedVerdict
                      ? 'border-brand-primary/40 ring-1 ring-brand-primary/20'
                      : 'border-border'}
                  `}
                >
                  {/* Epic header */}
                  <div className="px-5 py-4 border-b border-border/50">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="text-sm font-semibold text-text-primary">{epic.title}</h3>
                        {epic.theme && (
                          <p className="text-xs text-text-muted mt-0.5">{epic.theme}</p>
                        )}
                      </div>
                      {epic.is_assigned_to_me && !selectedVerdict && (
                        <span className="text-[10px] bg-brand-primary-light text-brand-primary px-2 py-0.5 rounded-full font-medium">
                          Your review
                        </span>
                      )}
                    </div>
                    {epic.features.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {epic.features.map((f, i) => (
                          <span key={i} className="text-[10px] bg-surface-subtle text-text-muted px-1.5 py-0.5 rounded">
                            {f.name}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Narrative */}
                  {epic.narrative && (
                    <div className="px-5 py-3 border-b border-border/50">
                      <p className="text-xs text-text-secondary leading-relaxed line-clamp-3">
                        {epic.narrative}
                      </p>
                    </div>
                  )}

                  {/* Verdict buttons */}
                  <div className="px-5 py-3 border-b border-border/50">
                    <div className="flex gap-2">
                      {(['confirmed', 'refine', 'flag'] as VerdictType[]).map(v => {
                        const isActive = selectedVerdict === v
                        const styles = EPIC_VERDICT_STYLES[v]
                        const labels = { confirmed: 'Confirm', refine: 'Refine', flag: 'Flag' }
                        const icons = { confirmed: '\u2713', refine: '\u270E', flag: '\u26A0' }
                        return (
                          <button
                            key={v}
                            onClick={() => handleEpicVerdict(epic.index, v)}
                            className={`flex-1 px-3 py-2 rounded-lg border text-xs font-medium transition-all ${
                              isActive ? styles.active : styles.button
                            }`}
                          >
                            <span className="mr-1">{icons[v]}</span>
                            {labels[v]}
                          </button>
                        )
                      })}
                    </div>
                  </div>

                  {/* Notes */}
                  <div className="px-5 py-3">
                    <textarea
                      value={notes}
                      onChange={(e) => setEpicNotes((prev) => ({ ...prev, [epic.index]: e.target.value }))}
                      onBlur={() => handleEpicNotesBlur(epic.index)}
                      rows={2}
                      placeholder="Feedback (optional)..."
                      className="w-full px-3 py-2 text-sm border border-border rounded-lg focus:ring-2 focus:ring-brand-primary-ring focus:border-brand-primary resize-none"
                    />
                  </div>
                </div>
              )
            })}

            <div className="pt-4 pb-8">
              <button
                onClick={handleCompleteReview}
                disabled={submitting}
                className="w-full px-6 py-3 bg-brand-primary text-white font-medium rounded-xl hover:bg-brand-primary-hover transition-all shadow-md disabled:opacity-50"
              >
                {submitting ? 'Submitting...' : 'Complete Review'}
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // ── Legacy Feature Review Mode (token-based) ─────────────────────
  const sortedReviews = [...featureReviews].sort((a, b) => {
    const order: Record<string, number> = { off_track: 0, needs_adjustment: 1, aligned: 2 }
    const aScore = a.consultant_verdict ? (order[a.consultant_verdict] ?? 3) : 3
    const bScore = b.consultant_verdict ? (order[b.consultant_verdict] ?? 3) : 3
    return aScore - bScore
  })

  const reviewedCount = Object.keys(clientVerdicts).length

  return (
    <div className="flex flex-col h-full bg-surface-page">
      <div className="bg-accent px-6 py-4">
        <h1 className="text-lg font-semibold text-white">Prototype Review</h1>
        <p className="text-sm text-white/60 mt-0.5">
          Review each feature below and share your verdict.
        </p>
      </div>

      <div className="flex-[55] min-h-0">
        {deployUrl ? (
          <PrototypeFrame
            deployUrl={deployUrl}
            onFeatureClick={() => {}}
            onPageChange={() => {}}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-text-placeholder">
            Prototype preview unavailable
          </div>
        )}
      </div>

      <div className="flex-[45] border-t border-border bg-surface-page overflow-y-auto">
        <div className="max-w-3xl mx-auto p-6 space-y-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-text-muted">
              {reviewedCount}/{featureReviews.length} features reviewed
            </span>
          </div>

          {sortedReviews.map((review) => {
            const selectedVerdict = clientVerdicts[review.overlay_id] || null
            const notes = clientNotes[review.overlay_id] || ''

            return (
              <div key={review.overlay_id} className="rounded-lg border border-border bg-surface-card shadow-sm">
                <div className="px-5 py-4 border-b border-border/50">
                  <div className="flex items-start justify-between">
                    <h3 className="text-sm font-semibold text-text-primary">{review.feature_name}</h3>
                    <span className="text-[10px] text-text-placeholder">
                      {Math.round(review.confidence * 100)}% confidence
                    </span>
                  </div>
                </div>

                {review.consultant_verdict && (
                  <div className="px-5 py-3 border-b border-border/50 bg-surface-subtle">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[11px] font-medium text-text-muted uppercase tracking-wide">
                        Consultant says:
                      </span>
                      <span className={`text-[11px] font-semibold ${
                        review.consultant_verdict === 'aligned' ? 'text-green-700' :
                        review.consultant_verdict === 'needs_adjustment' ? 'text-amber-700' :
                        'text-red-700'
                      }`}>
                        {review.consultant_verdict === 'aligned' ? '\u2713 Aligned' :
                         review.consultant_verdict === 'needs_adjustment' ? '\u26A0 Needs Adjustment' :
                         '\u2717 Off Track'}
                      </span>
                    </div>
                    {review.consultant_notes && (
                      <p className="text-xs text-text-muted">&ldquo;{review.consultant_notes}&rdquo;</p>
                    )}
                  </div>
                )}

                {review.validation_question && (
                  <div className="px-5 py-3 border-b border-border/50">
                    <p className="text-[11px] font-medium text-text-muted uppercase tracking-wide mb-1">Key Question</p>
                    <p className="text-sm text-text-primary">&ldquo;{review.validation_question}&rdquo;</p>
                    {review.validation_area && (
                      <span className="text-[10px] mt-1 inline-block px-1.5 py-0.5 rounded bg-surface-subtle text-text-muted">
                        {review.validation_area.replace('_', ' ')}
                      </span>
                    )}
                  </div>
                )}

                <div className="px-5 py-3 border-b border-border/50">
                  <p className="text-[11px] font-medium text-text-muted uppercase tracking-wide mb-2">Your Verdict</p>
                  <div className="flex gap-2">
                    {VERDICT_OPTIONS.map(({ value, label, icon }) => {
                      const isActive = selectedVerdict === value
                      const styles = VERDICT_STYLES[value]
                      return (
                        <button
                          key={value}
                          onClick={() => handleVerdictClick(review.overlay_id, value)}
                          className={`flex-1 px-3 py-2 rounded-lg border text-xs font-medium transition-all ${
                            isActive ? styles.active : styles.button
                          }`}
                        >
                          <span className="mr-1">{icon}</span>
                          {label}
                        </button>
                      )
                    })}
                  </div>
                </div>

                <div className="px-5 py-3">
                  <textarea
                    value={notes}
                    onChange={(e) => setClientNotes((prev) => ({ ...prev, [review.overlay_id]: e.target.value }))}
                    onBlur={() => handleNotesBlur(review.overlay_id)}
                    rows={2}
                    placeholder="Your feedback (optional)..."
                    className="w-full px-3 py-2 text-sm border border-border rounded-lg focus:ring-2 focus:ring-brand-primary-ring focus:border-brand-primary resize-none"
                  />
                </div>
              </div>
            )
          })}

          <div className="pt-4 pb-8">
            <button
              onClick={handleCompleteReview}
              disabled={submitting}
              className="w-full px-6 py-3 bg-brand-primary text-white font-medium rounded-xl hover:bg-brand-primary-hover transition-all shadow-md disabled:opacity-50"
            >
              {submitting ? 'Submitting...' : 'Complete Review'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
