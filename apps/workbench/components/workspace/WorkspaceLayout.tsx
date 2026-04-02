/**
 * WorkspaceLayout - Three-zone layout for project workspace
 *
 * Layout:
 * - Left: AppSidebar (global navigation)
 * - Center: Main workspace (phase-dependent content)
 * - Right: CollaborationPanel (chat, portal, activity)
 */

'use client'

import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { AppSidebar } from './AppSidebar'
import { PhaseSwitcher, WorkspacePhase } from './PhaseSwitcher'
// CollaborationPanel deprecated — unified into ReviewBubble
import { CanvasView } from './canvas/CanvasView'
import { BRDCanvas } from './brd/BRDCanvas'
import { OutcomesCanvas } from './outcomes/OutcomesCanvas'
import { FlowBlueprintView } from './flow/FlowBlueprintView'
import { IntelligenceWorkbench } from './ai/IntelligenceWorkbench'
import { BuildPhaseView } from './BuildPhaseView'
import { OverviewPanel } from './OverviewPanel'
import { BottomDock } from './BottomDock'
// BrainBubble deprecated — unified into ReviewBubble
import { useChat } from '@/lib/useChat'
import { AssistantProvider } from '@/lib/assistant'
import {
  updatePitchLine,
  updatePrototypeUrl,
  mapFeatureToStep,
  getPrototypeForProject,
  endConsultantReview,
  synthesizePrototypeFeedback,
  triggerPrototypeCodeUpdate,
  getPrototypeSession,
  submitEpicVerdict,
  getReviewSummary,
  updateReviewState,
  triggerEpicUpdate,
  listPrototypeSessions,
  getEpicVerdicts,
} from '@/lib/api'
import { useBRDData, useContextFrame, useWorkspaceData, useEpicPlan, useEpicVerdicts, useIntelligence } from '@/lib/hooks/use-api'
import { useRealtimeBRD } from '@/lib/realtime'
import type { CanvasData } from '@/types/workspace'
import type { NextAction } from '@/lib/api'
import { buildActionChatContext, buildStrategicActionChatContext } from '@/lib/action-constants'
import type { VpStep } from '@/types/api'
import type { FeatureOverlay, PrototypeSession } from '@/types/prototype'
import type { EpicTourPhase, EpicVerdict, ReviewSummary, ReviewState } from '@/types/epic-overlay'
import ReviewStartModal from '@/components/prototype/ReviewStartModal'
import ReviewEndModal from '@/components/prototype/ReviewEndModal'
import { ReviewBubble, SIDE_PANEL_WIDTH } from '@/components/prototype/ReviewBubble'
import { ProjectHealthOverlay } from './ProjectHealthOverlay'
import { Activity, Settings, Loader2, CheckCircle2, XCircle, Clock, ArrowLeft, Users, Target, FileText, GitBranch, Brain } from 'lucide-react'
import { CollaborateView } from './collaborate/CollaborateView'
import { useClientPulse } from '@/lib/hooks/use-api'
import { getProjectDetails, getLaunchProgress } from '@/lib/api'
import type { LaunchProgressResponse } from '@/types/workspace'

interface WorkspaceLayoutProps {
  projectId: string
  children?: React.ReactNode
}

export function WorkspaceLayout({ projectId, children }: WorkspaceLayoutProps) {
  const [phase, setPhase] = useState<WorkspacePhase>(() => {
    if (typeof window !== 'undefined') {
      return (localStorage.getItem(`workspace-phase-${projectId}`) as WorkspacePhase) || 'overview'
    }
    return 'overview'
  })
  const [error, setError] = useState<string | null>(null)

  // State declarations needed before SWR hooks (for conditional fetching)
  const [panelOpen, setPanelOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true)
  const [activeBottomPanel, setActiveBottomPanel] = useState<'context' | 'evidence' | 'history' | 'calls' | null>(null)
  const [discoveryViewMode, setDiscoveryViewMode] = useState<'outcomes' | 'brd' | 'canvas' | 'flow' | 'ai'>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('discovery-view-mode') as 'outcomes' | 'brd' | 'canvas' | 'flow' | 'ai'
      // Canvas tab hidden — fallback to outcomes if stored
      return stored === 'canvas' ? 'outcomes' : (stored || 'outcomes')
    }
    return 'outcomes'
  })

  // SWR hooks — all fire on mount in parallel, cached across navigations
  const { data: canvasData, isLoading: isWorkspaceLoading, mutate: mutateWorkspace } = useWorkspaceData(projectId)
  // Lazy-load BRD data: only fetch when a phase/view actually needs it.
  // overview, discovery (brd/flow/ai), build, and health overlay all consume brdData.
  // Skip for discovery+outcomes, collaborate, and live phases to speed up initial load.
  const shouldLoadBRD =
    phase === 'overview' ||
    phase === 'build' ||
    (phase === 'discovery' && discoveryViewMode !== 'outcomes')
  const { data: brdSwr, isLoading: isBrdLoading, mutate: mutateBrd } = useBRDData(shouldLoadBRD ? projectId : undefined)
  const brdData = brdSwr ?? null
  const nextActions = brdSwr?.next_actions ?? null
  const { data: contextFrame, isLoading: isContextFrameLoading, mutate: mutateContextFrame } = useContextFrame(projectId)
  const { data: intelligenceData, isLoading: isIntelligenceLoading, mutate: mutateIntelligence } = useIntelligence(projectId)
  useRealtimeBRD(projectId)
  // Persist phase to localStorage so refresh restores the current view
  useEffect(() => {
    localStorage.setItem(`workspace-phase-${projectId}`, phase)
  }, [phase, projectId])


  // BRD scroll tracking — active section for page_context
  const [activeBrdSection, setActiveBrdSection] = useState<string | null>(null)
  // Trigger to switch ReviewBubble to chat tab (incremented on action clicks)
  const [chatTabTrigger, setChatTabTrigger] = useState(0)

  // Dynamic page context for chat — tells the LLM what the user is looking at
  const pageContext = useMemo(() => {
    if (phase === 'overview') return 'overview'
    if (phase === 'collaborate') return 'collaborate'
    if (phase === 'build') return 'prototype'
    if (phase === 'discovery') {
      if (discoveryViewMode === 'outcomes') return 'outcomes'
      if (discoveryViewMode === 'canvas') return 'canvas'
      if (discoveryViewMode === 'flow') return 'brd:solution-flow'
      if (discoveryViewMode === 'ai') return 'brd:ai-agent'
      // BRD mode — map section to page_context
      if (activeBrdSection) {
        const sectionMap: Record<string, string> = {
          'business-context': 'brd:business_context',
          'personas': 'brd:personas',
          'workflows': 'brd:workflows',
          'features': 'brd:features',
          'data-entities': 'brd:data_entities',
          'stakeholders': 'brd:stakeholders',
          'constraints': 'brd:constraints',
          'questions': 'brd:questions',
        }
        return sectionMap[activeBrdSection] || 'brd'
      }
      return 'brd'
    }
    return 'brd'
  }, [phase, discoveryViewMode, activeBrdSection])

  // Project building state — blocks workspace until build completes
  const [projectBuildStatus, setProjectBuildStatus] = useState<'loading' | 'building' | 'ready'>('loading')
  const [buildProgress, setBuildProgress] = useState<LaunchProgressResponse | null>(null)
  const buildPollRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    let active = true
    getProjectDetails(projectId)
      .then((project) => {
        if (!active) return
        if (project.launch_status === 'building') {
          setProjectBuildStatus('building')
          // Start polling launch progress
          const launchId = project.active_launch_id
          if (launchId) {
            const poll = async () => {
              try {
                const progress = await getLaunchProgress(projectId, launchId)
                if (!active) return
                setBuildProgress(progress)
                const terminal = ['completed', 'completed_with_errors', 'failed']
                if (terminal.includes(progress.status)) {
                  setProjectBuildStatus('ready')
                  if (buildPollRef.current) clearInterval(buildPollRef.current)
                }
              } catch {
                // Non-fatal
              }
            }
            poll()
            buildPollRef.current = setInterval(poll, 3000)
          }
        } else {
          setProjectBuildStatus('ready')
        }
      })
      .catch(() => {
        if (active) setProjectBuildStatus('ready') // Fail open
      })
    return () => {
      active = false
      if (buildPollRef.current) clearInterval(buildPollRef.current)
    }
  }, [projectId])



  // Project Health overlay
  const [showHealthOverlay, setShowHealthOverlay] = useState(false)

  // Pending action from cross-view navigation (e.g., Overview → BRD)
  const [pendingAction, setPendingAction] = useState<NextAction | null>(null)

  // Review modal + mode state
  const [showReviewModal, setShowReviewModal] = useState(false)
  const [isReviewActive, setIsReviewActive] = useState(false)
  const [reviewSession, setReviewSession] = useState<PrototypeSession | null>(null)
  const [overlays, setOverlays] = useState<FeatureOverlay[]>([])
  const [prototypeId, setPrototypeId] = useState<string | null>(null)
  const [reviewPhase, setReviewPhase] = useState<'active' | 'awaiting_client' | 'synthesizing'>('active')
  const [clientShareData, setClientShareData] = useState<{ token: string; url: string } | null>(null)

  // Epic tour state
  const [epicPhase, setEpicPhase] = useState<EpicTourPhase>('vision_journey')
  const [epicCardIndex, setEpicCardIndex] = useState<number | null>(null)
  const [highlightedFeatureSlug, setHighlightedFeatureSlug] = useState<string | null>(null)
  const [currentIframeRoute, setCurrentIframeRoute] = useState<string | null>(null)
  // Feature navigation request from panel → BuildPhaseView
  const [pendingFeatureNav, setPendingFeatureNav] = useState<{
    slug: string
    route: string
  } | null>(null)
  const { data: epicPlan } = useEpicPlan(prototypeId)
  const { data: epicConfirmations, mutate: mutateEpicVerdicts } = useEpicVerdicts(reviewSession?.id)

  // Review state machine
  const [reviewState, setReviewState] = useState<ReviewState>('not_started')
  const [reviewSummary, setReviewSummary] = useState<ReviewSummary | null>(null)
  const [isUpdating, setIsUpdating] = useState(false)

  // Build a map of card keys → verdict for the progress bar: "vision:0" → "confirmed", etc.
  const verdictMap = useMemo(() => {
    const map = new Map<string, string>()
    if (epicConfirmations) {
      for (const c of epicConfirmations) {
        if (c.verdict) {
          map.set(`${c.card_type}:${c.card_index}`, c.verdict)
        }
      }
    }
    return map
  }, [epicConfirmations])

  // Revalidate BRD + context frame + intelligence when chat tools mutate data
  const handleDataMutated = useCallback(() => {
    mutateBrd()
    mutateContextFrame()
    mutateIntelligence()
  }, [mutateBrd, mutateContextFrame, mutateIntelligence])

  // Chat integration
  const {
    messages, isLoading: isChatLoading, sendMessage, sendSignal, addLocalMessage,
    entityDetection, isSavingAsSignal, saveAsSignal, dismissDetection,
    startNewChat, setConversationContext,
    snapshotConversation, restoreConversation,
  } = useChat({
    projectId,
    pageContext,
    onError: (error) => {
      console.error('Chat error:', error)
    },
    onDataMutated: handleDataMutated,
  })

  // Reset chat when switching phases — each screen gets a clean conversation context.
  // Without this, prototype review chat bleeds into BRD, or BRD context leaks into prototype.
  // Conversations are persisted to DB, so nothing is lost — user just gets a fresh start.
  const prevPhaseRef = useRef(phase)
  useEffect(() => {
    if (prevPhaseRef.current !== phase) {
      // If leaving review mode, restore the snapshot first
      restoreConversation()
      startNewChat()
      prevPhaseRef.current = phase
    }
  }, [phase, startNewChat, restoreConversation])

  // Resolved prototype URL — survives SWR revalidation (which may return null from projects table).
  // Prototype deploy_url lives in the prototypes table; projects.prototype_url may be empty.
  // Deferred: only fetch when build phase is active to avoid blocking initial page load.
  const [resolvedProtoUrl, setResolvedProtoUrl] = useState<string | null>(null)
  const protoSyncedRef = useRef(false)
  useEffect(() => {
    if (protoSyncedRef.current || phase !== 'build') return
    protoSyncedRef.current = true
    // Fire and forget — don't block page load. 404s silently ignored.
    getPrototypeForProject(projectId)
      .then((proto) => {
        if (proto?.deploy_url) {
          setResolvedProtoUrl(proto.deploy_url)
          setPrototypeId(proto.id)
        }
      })
      .catch(() => {})
  }, [projectId, phase])

  // Auto-restore active review session on mount (survives navigation & refresh)
  const sessionRestoredRef = useRef(false)
  useEffect(() => {
    if (sessionRestoredRef.current || !prototypeId || isReviewActive) return
    sessionRestoredRef.current = true
    listPrototypeSessions(prototypeId)
      .then((sessions) => {
        const active = [...sessions].reverse().find((s) => s.status === 'consultant_review')
        if (active) {
          setReviewSession(active)
          setIsReviewActive(true)
          setReviewPhase('active')
          setReviewState('in_progress')
          // Don't setPanelOpen here — ReviewBubble manages its own open state
          // and will auto-open when review mode fully engages (session + epicPlan)
        }
      })
      .catch(() => {})
  }, [prototypeId, isReviewActive])

  // Revalidate all data
  const loadData = useCallback(async () => {
    await Promise.all([mutateWorkspace(), mutateBrd()])
  }, [mutateWorkspace, mutateBrd])

  // Handlers
  const handleUpdatePitchLine = async (pitchLine: string) => {
    await updatePitchLine(projectId, pitchLine)
    mutateWorkspace((prev) =>
      prev ? { ...prev, pitch_line: pitchLine } : prev, false
    )
  }

  const handleUpdatePrototypeUrl = async (url: string) => {
    await updatePrototypeUrl(projectId, url)
    setResolvedProtoUrl(url)
    mutateWorkspace((prev) =>
      prev ? { ...prev, prototype_url: url, prototype_updated_at: new Date().toISOString() } : prev, false
    )
  }

  const handleMapFeatureToStep = async (featureId: string, stepId: string | null) => {
    await mapFeatureToStep(projectId, featureId, stepId)
    // Reload data to get updated state
    await loadData()
  }

  const handlePrototypeBuilt = useCallback(async (deployUrl: string) => {
    setResolvedProtoUrl(deployUrl)
    // Re-fetch prototype record to get the new prototypeId
    try {
      const proto = await getPrototypeForProject(projectId)
      if (proto?.id) setPrototypeId(proto.id)
    } catch {}
    await loadData()
  }, [projectId, loadData])

  // Review mode handlers
  const handleStartReview = useCallback(() => {
    setShowReviewModal(true)
  }, [])

  const handleReviewModalStart = useCallback(
    (
      session: PrototypeSession,
      ovls: FeatureOverlay[],
      steps: VpStep[],
      protoId: string,
      deployUrlFromModal: string,
      _mode: 'tour' | 'explore'
    ) => {
      setShowReviewModal(false)
      setOverlays(ovls)
      setReviewSession(session)
      setIsReviewActive(true)
      setPrototypeId(protoId)
      setReviewPhase('active')
      setClientShareData(null)

      // Use the prototype's deploy_url as the canonical URL
      if (deployUrlFromModal) {
        mutateWorkspace((prev) => prev ? { ...prev, prototype_url: deployUrlFromModal } : prev, false)
      }

      // Freeze BRD chat so review mode starts clean
      snapshotConversation()

      // Open panel by default when review starts
      setPanelOpen(true)

      // Set review state machine to in_progress
      setReviewState('in_progress')
      updateReviewState(session.id, 'in_progress').catch(() => {})
    },
    [snapshotConversation]
  )

  const handleEndReview = useCallback(async () => {
    if (!reviewSession) return
    try {
      const result = await endConsultantReview(reviewSession.id)
      setClientShareData({ token: result.client_review_token, url: result.client_review_url })
      setReviewPhase('awaiting_client')
    } catch (err) {
      console.error('Failed to end review:', err)
      setIsReviewActive(false)
      setReviewSession(null)
    } finally {
      restoreConversation()
    }
  }, [reviewSession, restoreConversation])

  // Advance to next epic card from the ReviewInfoPanel
  const handleEpicAdvance = useCallback(() => {
    mutateEpicVerdicts()
    // The EpicTourController handles navigation; we just trigger a re-render
    // by bumping the card index. The tour controller's handleNext is internal,
    // so we simulate it by dispatching a custom event the controller listens to.
    // For now, the Info panel's onAdvance is a no-op — the user clicks Next in the tour bar.
  }, [mutateEpicVerdicts])

  const handleRunSynthesis = useCallback(async () => {
    if (!reviewSession) return
    setReviewPhase('synthesizing')
    try {
      await synthesizePrototypeFeedback(reviewSession.id)
      await triggerPrototypeCodeUpdate(reviewSession.id)
    } catch (err) {
      console.error('Synthesis failed:', err)
    } finally {
      // Reset all review state
      setIsReviewActive(false)
      setReviewSession(null)
      setReviewPhase('active')
      setClientShareData(null)
      setPrototypeId(null)
      await loadData()
    }
  }, [reviewSession, loadData])

  const handleKeepWorking = useCallback(() => {
    setReviewPhase('active')
    setClientShareData(null)
  }, [])

  // Review state machine handlers
  const handleReviewComplete = useCallback(async () => {
    if (!reviewSession) return
    try {
      const summary = await getReviewSummary(reviewSession.id)
      setReviewSummary(summary)
      setReviewState('complete')
      await updateReviewState(reviewSession.id, 'complete')
    } catch (err) {
      console.error('Failed to compute review summary:', err)
    }
  }, [reviewSession])

  const handleConfirmAndUpdate = useCallback(async () => {
    if (!reviewSession) return
    const hasRefines = reviewSummary?.tallies.refine ?? 0
    if (!hasRefines) {
      // No refinements — go straight to ready_for_client
      setReviewState('ready_for_client')
      await updateReviewState(reviewSession.id, 'ready_for_client')
      return
    }
    setIsUpdating(true)
    try {
      await triggerEpicUpdate(reviewSession.id)
      // Poll for completion
      const pollInterval = setInterval(async () => {
        try {
          const session = await getPrototypeSession(reviewSession.id)
          const state = (session as any).review_state
          if (state === 're_review' || state === 'ready_for_client') {
            clearInterval(pollInterval)
            setReviewState(state)
            setReviewSummary(null)
            setIsUpdating(false)
            await mutateEpicVerdicts()
          }
        } catch {
          // Non-fatal
        }
      }, 3000)
    } catch (err) {
      console.error('Update trigger failed:', err)
      setIsUpdating(false)
      setReviewState('complete')
    }
  }, [reviewSession, reviewSummary, mutateEpicVerdicts])

  const handleBackToReview = useCallback(async () => {
    if (!reviewSession) return
    setReviewState('in_progress')
    setReviewSummary(null)
    await updateReviewState(reviewSession.id, 'in_progress')
  }, [reviewSession])

  // Submit epic verdict handler for ReviewBubble → EpicOverviewPanel
  const handleSubmitVerdict = useCallback(
    async (verdict: EpicVerdict, notes?: string) => {
      if (!reviewSession || epicCardIndex === null) return
      await submitEpicVerdict(reviewSession.id, {
        card_type: 'vision',
        card_index: epicCardIndex,
        verdict,
        notes: notes || null,
        source: 'consultant',
      })
      await mutateEpicVerdicts()
    },
    [reviewSession, epicCardIndex, mutateEpicVerdicts]
  )


  // Poll for client completion when awaiting_client
  useEffect(() => {
    if (reviewPhase !== 'awaiting_client' || !reviewSession) return
    const interval = setInterval(async () => {
      try {
        const session = await getPrototypeSession(reviewSession.id)
        if (session.status === 'client_complete' || session.status === 'synthesized') {
          setReviewPhase('synthesizing')
          clearInterval(interval)
        }
      } catch {
        // Polling failure is non-fatal
      }
    }, 10000)
    return () => clearInterval(interval)
  }, [reviewPhase, reviewSession])

  // Cross-view action execution: Overview → switch to BRD → execute
  const handleActionExecuteFromOverview = useCallback((action: NextAction) => {
    setPendingAction(action)
    setPhase('discovery')
    setDiscoveryViewMode('brd')
    localStorage.setItem('discovery-view-mode', 'brd')
  }, [])

  // Chat fallback for actions that need AI reasoning
  const handleSendActionToChat = useCallback((action: NextAction) => {
    const chatMessages: Record<string, (a: NextAction) => string> = {
      stale_belief: (a) => `Help me verify this assumption: ${a.title}`,
      contradiction_unresolved: () => 'Help me resolve the contradictions in our knowledge graph',
      revisit_decision: (a) => `Help me revisit this decision: ${a.title}`,
    }
    const msgFn = chatMessages[action.action_type]
    const message = msgFn ? msgFn(action) : `Help me with: ${action.title}`
    sendMessage(message)
  }, [sendMessage])

  // Intelligence action click → open chat with context pre-loaded
  const handleIntelligenceAction = useCallback((action: import('@/lib/api/workspace').SynthesizedAction) => {
    setConversationContext(action.chat_context)
    setChatTabTrigger((n) => n + 1)
    sendMessage(action.sentence)
  }, [setConversationContext, sendMessage])

  // Calculate sidebar widths
  const sidebarWidth = sidebarCollapsed ? 64 : 224

  // Client pulse for Collaborate button badge
  const { data: pulseData } = useClientPulse(projectId)
  // When panel is open, content compresses to make room
  const collaborationWidth = panelOpen ? SIDE_PANEL_WIDTH : 0

  // Build assistant project data
  const assistantProjectData = canvasData
    ? {
        readinessScore: canvasData.readiness_score,
        blockers: [],
        warnings: [],
        pendingConfirmations: canvasData.pending_count,
        stats: {
          features: canvasData.features.length,
          personas: canvasData.personas.length,
          vpSteps: canvasData.vp_steps.length,
          signals: 0,
        },
      }
    : undefined

  // Show building overlay ONLY if project is actively being built (not during initial load)
  if (projectBuildStatus === 'building') {
    const steps = buildProgress?.steps || []
    const progressPct = buildProgress?.progress_pct || 0

    return (
      <div className="min-h-screen bg-[#F8F9FB]">
        <AppSidebar
          isCollapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
        <div
          className="transition-all duration-300 flex items-center justify-center min-h-screen"
          style={{ marginLeft: sidebarWidth }}
        >
          <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl border border-border p-8 text-center">
            <Settings className="w-12 h-12 text-brand-primary animate-spin mx-auto mb-4" style={{ animationDuration: '3s' }} />
            <h2 className="text-lg font-semibold text-text-body mb-2">Building Your Project</h2>
            <a
              href="/projects"
              className="inline-flex items-center gap-1.5 text-sm text-brand-primary hover:text-[#25785A] transition-colors mb-4"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Back to Projects
            </a>
            <p className="text-sm text-[#666666] mb-6">
              We&apos;re setting up your project with personas, workflows, and requirements. This usually takes about a minute.
            </p>

            {/* Progress bar */}
            <div className="mb-6">
              <div className="h-2 bg-[#F0F0F0] rounded-full overflow-hidden">
                <div
                  className="h-full bg-brand-primary rounded-full transition-all duration-500 ease-out"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
              <p className="text-xs text-text-placeholder mt-1.5 text-right">{progressPct}%</p>
            </div>

            {/* Steps */}
            {steps.length > 0 && (
              <div className="space-y-2 text-left">
                {steps.map((step) => {
                  const StepIcon = step.status === 'completed' ? CheckCircle2
                    : step.status === 'running' ? Loader2
                    : step.status === 'failed' ? XCircle
                    : Clock
                  const iconClass = step.status === 'completed' ? 'text-brand-primary'
                    : step.status === 'running' ? 'text-brand-primary animate-spin'
                    : step.status === 'failed' ? 'text-red-500'
                    : 'text-text-placeholder'

                  return (
                    <div key={step.step_key} className="flex items-center gap-3">
                      <StepIcon className={`w-4 h-4 flex-shrink-0 ${iconClass}`} />
                      <span className={`text-sm ${
                        step.status === 'completed' || step.status === 'running'
                          ? 'text-text-body'
                          : 'text-text-placeholder'
                      }`}>
                        {step.step_label}
                      </span>
                    </div>
                  )
                })}
              </div>
            )}

            <p className="text-xs text-text-placeholder mt-6">
              We&apos;ll notify you when it&apos;s ready.
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (isWorkspaceLoading && !canvasData) {
    return (
      <div className="min-h-screen bg-surface-muted flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-primary mx-auto mb-4" />
          <p className="text-[12px] text-text-placeholder">Loading workspace...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-surface-muted flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error}</p>
          <button
            onClick={loadData}
            className="px-4 py-2 bg-brand-primary text-white rounded-lg hover:bg-[#25785A] transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <AssistantProvider
      projectId={projectId}
      initialProjectData={assistantProjectData}
      onProjectDataChanged={loadData}
    >
      <div className="min-h-screen bg-[#F8F9FB]">
        {/* Left Sidebar */}
        <AppSidebar
          isCollapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        />

        {/* Main Content Area */}
        <div
          className="transition-all duration-300"
          style={{
            marginLeft: sidebarWidth,
            marginRight: collaborationWidth,
          }}
        >
          {/* Header with Phase Switcher */}
          <header className="sticky top-0 z-20 bg-white border-b border-border">
            <div className="flex items-center justify-between px-6 py-4">
              <div className="flex items-center gap-4">
                <div>
                  <h1 className="text-xl font-medium text-text-body">
                    {canvasData?.project_name}
                  </h1>
                  {canvasData?.pitch_line && (
                    <p className="text-[12px] text-text-placeholder mt-0.5 truncate max-w-xl">
                      {canvasData.pitch_line}
                    </p>
                  )}
                </div>
                {/* Heartbeat icon — opens health modal */}
                <button
                  onClick={() => setShowHealthOverlay(true)}
                  className="p-1.5 rounded-lg hover:bg-[#F4F4F4] transition-colors group"
                  title="Project Health"
                >
                  <Activity className="w-4 h-4 text-brand-primary group-hover:text-[#25785A]" />
                </button>
              </div>

              <div className="flex items-center gap-3">
                <PhaseSwitcher
                  currentPhase={phase}
                  onPhaseChange={setPhase}
                />
                <div className="w-px h-6 bg-border" />
                <button
                  onClick={() => setPhase('collaborate')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-[13px] font-medium transition-all duration-200 ${
                    phase === 'collaborate'
                      ? 'bg-white text-brand-primary shadow-sm border border-border'
                      : 'text-[#666666] hover:text-text-body'
                  }`}
                >
                  <Users className="w-4 h-4" />
                  Collaborate
                  {(pulseData?.unread_count ?? 0) > 0 && (
                    <span className="px-1.5 py-0.5 bg-brand-primary text-white text-[10px] font-bold rounded-full min-w-[18px] text-center">
                      {pulseData!.unread_count}
                    </span>
                  )}
                </button>
              </div>
            </div>
          </header>

          {/* Phase Content */}
          <main className="p-6">
            {phase === 'overview' && canvasData && (
              <OverviewPanel
                projectId={projectId}
                canvasData={canvasData}
                readinessData={null}
                brdData={brdData}
                isBrdLoading={isBrdLoading}
                nextActions={nextActions}
                contextActions={contextFrame?.actions}
                strategicActions={intelligenceData?.actions}
                isLoadingActions={isIntelligenceLoading}
                onNavigateToPhase={(p) => setPhase(p)}
                onActionExecute={handleActionExecuteFromOverview}
                onActionChat={(action) => {
                  setConversationContext(buildActionChatContext(action))
                  setPanelOpen(true)
                  sendMessage(action.sentence)
                }}
                onStrategicActionChat={(action) => {
                  setConversationContext(buildStrategicActionChatContext(action))
                  setPanelOpen(true)
                  sendMessage(action.sentence)
                }}
                onOpenHealth={() => setShowHealthOverlay(true)}
              />
            )}

            {phase === 'discovery' && canvasData && (
              <div className="flex flex-col h-[calc(100vh-140px)]">
                {/* View mode toggle */}
                <div className="flex items-center justify-end mb-2 flex-shrink-0">
                  <div className="inline-flex items-center bg-gray-100 rounded-md p-0.5 text-[12px]">
                    {(['outcomes', 'brd', 'flow', 'ai'] as const).map((mode) => {
                      const tabs = {
                        outcomes: { label: 'Outcomes', icon: Target },
                        brd: { label: 'Requirements', icon: FileText },
                        flow: { label: 'Solution Flow', icon: GitBranch },
                        ai: { label: 'Intelligence', icon: Brain },
                      } as const
                      const tab = tabs[mode]
                      const Icon = tab.icon
                      return (
                        <button
                          key={mode}
                          onClick={() => { setDiscoveryViewMode(mode); localStorage.setItem('discovery-view-mode', mode) }}
                          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-[5px] font-medium transition-colors ${
                            discoveryViewMode === mode
                              ? 'bg-white text-[#37352f] shadow-sm'
                              : 'text-gray-500 hover:text-gray-700'
                          }`}
                        >
                          <Icon className="w-3.5 h-3.5" />
                          {tab.label}
                        </button>
                      )
                    })}
                  </div>
                </div>

                {discoveryViewMode === 'outcomes' && (
                  <div className="flex-1 min-h-0 rounded-2xl border border-border bg-white shadow-md overflow-y-auto">
                    <OutcomesCanvas
                      projectId={projectId}
                      onActionClick={handleIntelligenceAction}
                    />
                  </div>
                )}

                {discoveryViewMode === 'brd' && (
                  <div className="flex-1 min-h-0 rounded-2xl border border-border bg-white shadow-md overflow-hidden">
                    <BRDCanvas
                      projectId={projectId}
                      initialData={brdData}
                      initialNextActions={nextActions}
                      onRefresh={loadData}
                      onSendToChat={handleSendActionToChat}
                      pendingAction={pendingAction}
                      onPendingActionConsumed={() => setPendingAction(null)}
                      onActiveSectionChange={setActiveBrdSection}
                      onNavigateToCollaborate={() => setPhase('collaborate')}
                      onActionClick={handleIntelligenceAction}
                    />
                  </div>
                )}
                {discoveryViewMode === 'canvas' && (
                  <CanvasView projectId={projectId} onRefresh={loadData} />
                )}
                {discoveryViewMode === 'flow' && (
                  <FlowBlueprintView
                    projectId={projectId}
                    flow={brdData?.solution_flow ?? null}
                    personas={canvasData.personas}
                    onGenerateFlow={loadData}
                    projectName={brdData?.business_context?.company_name ?? undefined}
                    brdFeatures={brdData ? [
                      ...(brdData.requirements?.must_have || []),
                      ...(brdData.requirements?.should_have || []),
                      ...(brdData.requirements?.could_have || []),
                    ] : undefined}
                    brdWorkflows={brdData?.workflows}
                    brdDataEntities={brdData?.data_entities}
                  />
                )}
                {discoveryViewMode === 'ai' && (
                  <IntelligenceWorkbench
                    projectId={projectId}
                    flow={brdData?.solution_flow ?? null}
                    personas={canvasData.personas}
                  />
                )}
              </div>
            )}

            {phase === 'build' && canvasData && (
              <div className="h-[calc(100vh-140px)] bg-white rounded-lg border border-border overflow-hidden relative">
                {/* Synthesizing banner — floats over prototype */}
                {reviewPhase === 'synthesizing' && (
                  <div className="absolute top-0 left-0 right-0 z-10 flex items-center justify-center gap-2 px-4 py-2 bg-brand-primary-light border-b border-brand-primary/20 text-sm text-[#25785A]">
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-brand-primary border-t-transparent" />
                    <span className="font-medium">Synthesizing feedback...</span>
                    <span className="text-xs text-[#666666]">Generating code updates from review verdicts</span>
                  </div>
                )}

                <BuildPhaseView
                  projectId={projectId}
                  prototypeUrl={resolvedProtoUrl || canvasData.prototype_url}
                  prototypeUpdatedAt={canvasData.prototype_updated_at}
                  readinessScore={brdData?.completeness?.overall_score ?? canvasData.readiness_score}
                  onUpdatePrototypeUrl={handleUpdatePrototypeUrl}
                  onPrototypeBuilt={handlePrototypeBuilt}
                  isReviewActive={isReviewActive}
                  onStartReview={handleStartReview}
                  onEndReview={handleEndReview}
                  session={reviewSession}
                  epicPlan={epicPlan}
                  onEpicPhaseChange={setEpicPhase}
                  onEpicIndexChange={() => {}}
                  onEpicCardChange={(idx) => {
                    setEpicCardIndex(idx)
                    setHighlightedFeatureSlug(null) // Clear on card change
                  }}
                  onFeatureClick={setHighlightedFeatureSlug}
                  onIframeRouteChange={setCurrentIframeRoute}
                  pendingFeatureNav={pendingFeatureNav}
                  onFeatureNavConsumed={() => setPendingFeatureNav(null)}
                  verdictMap={verdictMap}
                  collaborationWidth={collaborationWidth}
                  reviewState={reviewState}
                  reviewSummary={reviewSummary}
                  isUpdating={isUpdating}
                  onReviewComplete={handleReviewComplete}
                  onConfirmAndUpdate={handleConfirmAndUpdate}
                  onBackToReview={handleBackToReview}
                />
              </div>
            )}

            {phase === 'live' && (
              <div className="flex items-center justify-center h-[calc(100vh-200px)]">
                <div className="text-center">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-surface-muted flex items-center justify-center">
                    <span className="text-2xl">🚀</span>
                  </div>
                  <h3 className="text-base font-semibold text-text-body mb-2">
                    Live Product View
                  </h3>
                  <p className="text-[12px] text-text-placeholder">
                    Coming soon - track your product post-launch
                  </p>
                </div>
              </div>
            )}

            {phase === 'collaborate' && (
              <CollaborateView projectId={projectId} onNavigateToPhase={setPhase} />
            )}

            {/* Optional children for extension */}
            {children}
          </main>

          {/* Bottom Dock */}
          <BottomDock
            projectId={projectId}
            activePanel={activeBottomPanel}
            onPanelChange={setActiveBottomPanel}
          />
        </div>

        {/* Review Start Modal */}
        <ReviewStartModal
          projectId={projectId}
          isOpen={showReviewModal}
          onClose={() => setShowReviewModal(false)}
          onStartReview={handleReviewModalStart}
        />

        {/* Review End Modal — overlay on top of prototype */}
        <ReviewEndModal
          isOpen={reviewPhase === 'awaiting_client' && !!clientShareData}
          overlays={overlays}
          clientShareData={clientShareData ?? { token: '', url: '' }}
          onShareWithClient={() => {
            const fullUrl = typeof window !== 'undefined'
              ? `${window.location.origin}${clientShareData?.url ?? ''}`
              : clientShareData?.url ?? ''
            navigator.clipboard.writeText(fullUrl)
          }}
          onFixFirst={handleRunSynthesis}
          onKeepWorking={handleKeepWorking}
        />

        {/* Right Panel — unified ReviewBubble (Briefing|Chat or Review|Chat) */}
        <ReviewBubble
          projectId={projectId}
          messages={messages}
          isChatLoading={isChatLoading}
          onSendMessage={sendMessage}
          onCardAction={(cmd) => sendMessage(cmd, { silent: true })}
          onSendSignal={sendSignal}
          onAddLocalMessage={addLocalMessage}
          onOpenChange={setPanelOpen}
          // Briefing props
          actionCount={contextFrame?.actions?.length ?? 0}
          onCascade={() => { mutateBrd(); mutateContextFrame() }}
          contextActions={contextFrame?.actions}
          onNewChat={startNewChat}
          onSetConversationContext={setConversationContext}
          onNavigateToCollaborate={() => setPhase('collaborate')}
          hideClientPulse={phase === 'collaborate'}
          chatTabTrigger={chatTabTrigger}
          // Entity detection
          entityDetection={entityDetection}
          isSavingAsSignal={isSavingAsSignal}
          onSaveAsSignal={async () => { await saveAsSignal(); mutateBrd(); mutateContextFrame() }}
          onDismissDetection={dismissDetection}
          // Review props — only on Build phase, otherwise show normal Briefing/Chat
          session={isReviewActive && phase === 'build' ? reviewSession ?? undefined : undefined}
          epicPlan={isReviewActive && phase === 'build' ? epicPlan ?? undefined : undefined}
          epicPhase={epicPhase}
          epicCardIndex={epicCardIndex}
          epicConfirmations={epicConfirmations ?? []}
          onEpicAdvance={handleEpicAdvance}
          onSubmitVerdict={handleSubmitVerdict}
          highlightedFeatureSlug={highlightedFeatureSlug}
          currentIframeRoute={currentIframeRoute}
          onFeatureNavigate={(slug, route) => {
            setPendingFeatureNav({ slug, route })
            setHighlightedFeatureSlug(slug)
          }}
        />
        {/* Project Health Overlay — unified pulse + health modal */}
        {showHealthOverlay && (
          <ProjectHealthOverlay
            projectId={projectId}
            completeness={brdData?.completeness}
            onDismiss={() => setShowHealthOverlay(false)}
          />
        )}
      </div>
    </AssistantProvider>
  )
}

export default WorkspaceLayout
