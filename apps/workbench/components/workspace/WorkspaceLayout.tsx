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
import { CollaborationPanel, type PanelState } from './CollaborationPanel'
import { CanvasView } from './canvas/CanvasView'
import { BRDCanvas } from './brd/BRDCanvas'
import { BuildPhaseView } from './BuildPhaseView'
import { OverviewPanel } from './OverviewPanel'
import { BottomDock } from './BottomDock'
import { BrainBubble, BRAIN_PANEL_WIDTH } from './BrainBubble'
import { useChat } from '@/lib/useChat'
import { AssistantProvider } from '@/lib/assistant'
import {
  getWorkspaceData,
  updatePitchLine,
  updatePrototypeUrl,
  mapFeatureToStep,
  getReadinessScore,
  getPrototypeForProject,
  generatePrototype,
  getTaskStats,
  getCollaborationHistory,
  getQuestionCounts,
  endConsultantReview,
  synthesizePrototypeFeedback,
  triggerPrototypeCodeUpdate,
  getPrototypeSession,
} from '@/lib/api'
import type { TaskStatsResponse, CollaborationHistoryResponse } from '@/lib/api'
import type { QuestionCounts } from '@/types/workspace'
import { useBRDData, useContextFrame } from '@/lib/hooks/use-api'
import { useRealtimeBRD } from '@/lib/realtime'
import type { CanvasData } from '@/types/workspace'
import type { ReadinessScore, NextAction } from '@/lib/api'
import type { VpStep } from '@/types/api'
import type { DesignSelection, FeatureOverlay, FeatureVerdict, PrototypeSession, TourStep, SessionContext, RouteFeatureMap } from '@/types/prototype'
import type { PrototypeFrameHandle } from '@/components/prototype/PrototypeFrame'
import ReviewStartModal from '@/components/prototype/ReviewStartModal'
import ReviewEndModal from '@/components/prototype/ReviewEndModal'
import { ProjectHealthOverlay } from './ProjectHealthOverlay'
import { Activity, Settings, Loader2, CheckCircle2, XCircle, Clock, ArrowLeft } from 'lucide-react'
import { getProjectDetails, getLaunchProgress } from '@/lib/api'
import type { LaunchProgressResponse } from '@/types/workspace'

interface WorkspaceLayoutProps {
  projectId: string
  children?: React.ReactNode
}

export function WorkspaceLayout({ projectId, children }: WorkspaceLayoutProps) {
  const [phase, setPhase] = useState<WorkspacePhase>('overview')
  const [canvasData, setCanvasData] = useState<CanvasData | null>(null)
  const [readinessData, setReadinessData] = useState<ReadinessScore | null>(null)
  const [taskStats, setTaskStats] = useState<TaskStatsResponse | null>(null)
  const [collaborationHistory, setCollaborationHistory] = useState<CollaborationHistoryResponse | null>(null)
  const [questionCounts, setQuestionCounts] = useState<QuestionCounts | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // SWR hook for read-only BRD data (cached across page navigations)
  // next_actions are included in the BRD response to avoid a separate API call
  const { data: brdSwr, mutate: mutateBrd } = useBRDData(projectId)
  const brdData = brdSwr ?? null
  const nextActions = brdSwr?.next_actions ?? null
  const { data: contextFrame, mutate: mutateContextFrame } = useContextFrame(projectId)
  useRealtimeBRD(projectId)
  const [collaborationState, setCollaborationState] = useState<PanelState>('normal')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true)
  const [activeBottomPanel, setActiveBottomPanel] = useState<'context' | 'evidence' | 'history' | null>(null)
  const [discoveryViewMode, setDiscoveryViewMode] = useState<'brd' | 'canvas'>(() => {
    if (typeof window !== 'undefined') {
      return (localStorage.getItem('discovery-view-mode') as 'brd' | 'canvas') || 'brd'
    }
    return 'brd'
  })

  // Brain panel open state — controls BRD compression
  const [brainPanelOpen, setBrainPanelOpen] = useState(false)

  // BRD scroll tracking — active section for page_context
  const [activeBrdSection, setActiveBrdSection] = useState<string | null>(null)

  // Dynamic page context for chat — tells the LLM what the user is looking at
  const pageContext = useMemo(() => {
    if (phase === 'overview') return 'overview'
    if (phase === 'build') return 'prototype'
    if (phase === 'discovery') {
      if (discoveryViewMode === 'canvas') return 'canvas'
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
  const [reviewTourMode, setReviewTourMode] = useState<'tour' | 'explore'>('tour')
  const [isReviewActive, setIsReviewActive] = useState(false)
  const [reviewSession, setReviewSession] = useState<PrototypeSession | null>(null)
  const [overlays, setOverlays] = useState<FeatureOverlay[]>([])
  const [vpSteps, setVpSteps] = useState<VpStep[]>([])
  const [currentTourStep, setCurrentTourStep] = useState<TourStep | null>(null)
  const [prototypeId, setPrototypeId] = useState<string | null>(null)
  const [reviewPhase, setReviewPhase] = useState<'active' | 'awaiting_client' | 'synthesizing'>('active')
  const [clientShareData, setClientShareData] = useState<{ token: string; url: string } | null>(null)
  const [routeFeatureMap, setRouteFeatureMap] = useState<RouteFeatureMap>(new Map())
  const [isFrameReady, setIsFrameReady] = useState(false)
  const [sessionContext, setSessionContext] = useState<SessionContext>({
    current_page: '/',
    current_route: '/',
    active_feature_id: null,
    active_feature_name: null,
    active_component: null,
    visible_features: [],
    page_history: [],
    features_reviewed: [],
  })
  const frameRef = useRef<PrototypeFrameHandle>(null)
  const [selectedOverlayId, setSelectedOverlayId] = useState<string | null>(null)

  const isTourActive = currentTourStep !== null

  // Derive current overlay: tour step overlay takes priority, then radar-click selection
  const currentOverlay = currentTourStep
    ? overlays.find((o) => o.id === currentTourStep.overlayId) ?? null
    : selectedOverlayId
      ? overlays.find((o) => o.id === selectedOverlayId || o.feature_id === selectedOverlayId) ?? null
      : null

  // Chat integration
  const {
    messages, isLoading: isChatLoading, sendMessage, sendSignal, addLocalMessage,
    entityDetection, isSavingAsSignal, saveAsSignal, dismissDetection,
    startNewChat, setConversationContext,
  } = useChat({
    projectId,
    pageContext,
    onError: (error) => {
      console.error('Chat error:', error)
    },
  })

  // Load workspace data (canvas + readiness are stateful; BRD + next-actions are SWR-managed)
  const loadData = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)

      const [data, readiness, proto, stats, history, qCounts] = await Promise.all([
        getWorkspaceData(projectId),
        getReadinessScore(projectId).catch(() => null),
        getPrototypeForProject(projectId).catch(() => null),
        getTaskStats(projectId).catch(() => null),
        getCollaborationHistory(projectId).catch(() => null),
        getQuestionCounts(projectId).catch(() => null),
      ])
      if (proto?.deploy_url) {
        data.prototype_url = proto.deploy_url
      }

      setCanvasData(data)
      setReadinessData(readiness)
      setTaskStats(stats)
      setCollaborationHistory(history)
      setQuestionCounts(qCounts)

      // Revalidate SWR-managed BRD data (includes next_actions)
      mutateBrd()

      // Auto-detect phase based on project state
      if (data.prototype_url) {
        setPhase('build')
      }
    } catch (err) {
      console.error('Failed to load workspace data:', err)
      setError('Failed to load workspace data')
    } finally {
      setIsLoading(false)
    }
  }, [projectId, mutateBrd])

  useEffect(() => {
    loadData()
  }, [loadData])

  // Handlers
  const handleUpdatePitchLine = async (pitchLine: string) => {
    await updatePitchLine(projectId, pitchLine)
    setCanvasData((prev) =>
      prev ? { ...prev, pitch_line: pitchLine } : prev
    )
  }

  const handleUpdatePrototypeUrl = async (url: string) => {
    await updatePrototypeUrl(projectId, url)
    setCanvasData((prev) =>
      prev ? { ...prev, prototype_url: url, prototype_updated_at: new Date().toISOString() } : prev
    )
  }

  const handleMapFeatureToStep = async (featureId: string, stepId: string | null) => {
    await mapFeatureToStep(projectId, featureId, stepId)
    // Reload data to get updated state
    await loadData()
  }

  const handleGeneratePrototype = async (selection: DesignSelection) => {
    await generatePrototype(projectId, selection)
    // Refresh workspace to pick up any changes (prompt stored on prototype)
    await loadData()
  }

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
      mode: 'tour' | 'explore'
    ) => {
      setShowReviewModal(false)
      setOverlays(ovls)
      setVpSteps(steps)
      setReviewSession(session)
      setIsReviewActive(true)
      setPrototypeId(protoId)
      setReviewPhase('active')
      setClientShareData(null)
      setRouteFeatureMap(new Map())
      setIsFrameReady(false)
      setReviewTourMode(mode)

      // Use the prototype's deploy_url as the canonical URL
      if (deployUrlFromModal) {
        setCanvasData((prev) => prev ? { ...prev, prototype_url: deployUrlFromModal } : prev)
      }

      // Auto-expand collaboration panel
      if (collaborationState === 'collapsed') {
        setCollaborationState('normal')
      }
    },
    [collaborationState]
  )

  const handleVerdictSubmit = useCallback((overlayId: string, verdict: FeatureVerdict) => {
    setOverlays(prev => prev.map(o =>
      o.id === overlayId ? { ...o, consultant_verdict: verdict } : o
    ))
  }, [])

  const handleEndReview = useCallback(async () => {
    if (!reviewSession) return
    try {
      setCurrentTourStep(null)
      frameRef.current?.sendMessage({ type: 'aios:clear-highlights' })
      const result = await endConsultantReview(reviewSession.id)
      setClientShareData({ token: result.client_review_token, url: result.client_review_url })
      setReviewPhase('awaiting_client')
    } catch (err) {
      console.error('Failed to end review:', err)
      setIsReviewActive(false)
      setReviewSession(null)
    }
  }, [reviewSession])

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

  const handleFeatureClick = useCallback((featureId: string, componentName: string | null) => {
    setSessionContext((prev) => ({
      ...prev,
      active_feature_id: featureId,
      active_component: componentName,
      features_reviewed: prev.features_reviewed.includes(featureId)
        ? prev.features_reviewed
        : [...prev.features_reviewed, featureId],
    }))
    // When radar dot clicked (tour not active), select that overlay in the sidebar
    setSelectedOverlayId(featureId)
    // Expand collaboration panel if collapsed
    if (collaborationState === 'collapsed') {
      setCollaborationState('normal')
    }
  }, [collaborationState])

  const handlePageChange = useCallback((path: string, visibleFeatures: string[]) => {
    setSessionContext((prev) => ({
      ...prev,
      current_page: path,
      current_route: path,
      visible_features: visibleFeatures,
      page_history: [...prev.page_history, { path, timestamp: new Date().toISOString(), features_visible: visibleFeatures }],
    }))
    // Build route-feature map
    setRouteFeatureMap((prev) => new Map(prev).set(path, visibleFeatures))
  }, [])

  const handleTourStepChange = useCallback((step: TourStep | null) => {
    setCurrentTourStep(step)
    if (step) {
      const ov = overlays.find((o) => o.id === step.overlayId)
      setSessionContext((prev) => ({
        ...prev,
        active_feature_id: step.featureId,
        active_feature_name: step.featureName,
        active_component: ov?.component_name ?? null,
      }))
    }
  }, [overlays])

  const handleTourEnd = useCallback(() => {
    setCurrentTourStep(null)
  }, [])

  const handleFrameReady = useCallback(() => {
    setIsFrameReady(true)
  }, [])

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

  // Send radar dots when review active, tour idle, frame ready
  useEffect(() => {
    if (!isReviewActive || isTourActive || !isFrameReady) return
    const frame = frameRef.current
    if (!frame) return

    const features = overlays
      .filter((o) => o.overlay_content)
      .map((o) => ({
        featureId: o.feature_id || o.id,
        featureName: o.overlay_content!.feature_name,
        componentName: o.component_name || undefined,
        keywords: o.overlay_content!.feature_name
          .toLowerCase()
          .replace(/[^a-z0-9\s-]/g, '')
          .split(/[\s-]+/)
          .filter((w: string) => w.length > 2),
      }))

    frame.sendMessage({ type: 'aios:show-radar', features })

    return () => {
      frame.sendMessage({ type: 'aios:clear-radar' })
    }
  }, [isReviewActive, isTourActive, isFrameReady, overlays, sessionContext.current_page])

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

  // Calculate sidebar widths
  const sidebarWidth = sidebarCollapsed ? 64 : 224
  // BrainBubble only in BRD/Canvas views (discovery phase with brd or canvas mode)
  const useBrainBubble = (phase === 'discovery' || phase === 'overview') && (discoveryViewMode === 'brd' || discoveryViewMode === 'canvas')
  // When brain panel is open, BRD compresses to make room
  const collaborationWidth = useBrainBubble
    ? (brainPanelOpen ? BRAIN_PANEL_WIDTH : 0)
    : collaborationState === 'collapsed' ? 48
    : collaborationState === 'wide' ? 400 : 320

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
          <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl border border-[#E5E5E5] p-8 text-center">
            <Settings className="w-12 h-12 text-[#3FAF7A] animate-spin mx-auto mb-4" style={{ animationDuration: '3s' }} />
            <h2 className="text-lg font-semibold text-[#333333] mb-2">Building Your Project</h2>
            <a
              href="/projects"
              className="inline-flex items-center gap-1.5 text-sm text-[#3FAF7A] hover:text-[#25785A] transition-colors mb-4"
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
                  className="h-full bg-[#3FAF7A] rounded-full transition-all duration-500 ease-out"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
              <p className="text-xs text-[#999999] mt-1.5 text-right">{progressPct}%</p>
            </div>

            {/* Steps */}
            {steps.length > 0 && (
              <div className="space-y-2 text-left">
                {steps.map((step) => {
                  const StepIcon = step.status === 'completed' ? CheckCircle2
                    : step.status === 'running' ? Loader2
                    : step.status === 'failed' ? XCircle
                    : Clock
                  const iconClass = step.status === 'completed' ? 'text-[#3FAF7A]'
                    : step.status === 'running' ? 'text-[#3FAF7A] animate-spin'
                    : step.status === 'failed' ? 'text-red-500'
                    : 'text-[#999999]'

                  return (
                    <div key={step.step_key} className="flex items-center gap-3">
                      <StepIcon className={`w-4 h-4 flex-shrink-0 ${iconClass}`} />
                      <span className={`text-sm ${
                        step.status === 'completed' || step.status === 'running'
                          ? 'text-[#333333]'
                          : 'text-[#999999]'
                      }`}>
                        {step.step_label}
                      </span>
                    </div>
                  )
                })}
              </div>
            )}

            <p className="text-xs text-[#999999] mt-6">
              We&apos;ll notify you when it&apos;s ready.
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-ui-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-teal mx-auto mb-4" />
          <p className="text-support text-ui-supportText">Loading workspace...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-ui-background flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error}</p>
          <button
            onClick={loadData}
            className="px-4 py-2 bg-brand-teal text-white rounded-lg hover:bg-brand-tealDark transition-colors"
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
          <header className="sticky top-0 z-20 bg-white border-b border-ui-cardBorder">
            <div className="flex items-center justify-between px-6 py-4">
              <div className="flex items-center gap-4">
                <div>
                  <h1 className="text-h2 text-ui-headingDark">
                    {canvasData?.project_name}
                  </h1>
                  {canvasData?.pitch_line && (
                    <p className="text-support text-ui-supportText mt-0.5 truncate max-w-xl">
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
                  <Activity className="w-4 h-4 text-[#3FAF7A] group-hover:text-[#25785A]" />
                </button>
              </div>

              <PhaseSwitcher
                currentPhase={phase}
                onPhaseChange={setPhase}
              />
            </div>
          </header>

          {/* Phase Content */}
          <main className="p-6">
            {phase === 'overview' && canvasData && (
              <OverviewPanel
                projectId={projectId}
                canvasData={canvasData}
                readinessData={readinessData}
                brdData={brdData}
                nextActions={nextActions}
                contextActions={contextFrame?.actions}
                initialTaskStats={taskStats}
                initialHistory={collaborationHistory}
                initialQuestionCounts={questionCounts}
                onNavigateToPhase={(p) => setPhase(p)}
                onActionExecute={handleActionExecuteFromOverview}
                onOpenHealth={() => setShowHealthOverlay(true)}
              />
            )}

            {phase === 'discovery' && canvasData && (
              <div className="flex flex-col h-[calc(100vh-140px)]">
                {/* View mode toggle */}
                <div className="flex items-center justify-end mb-2 flex-shrink-0">
                  <div className="inline-flex items-center bg-gray-100 rounded-md p-0.5 text-[12px]">
                    <button
                      onClick={() => { setDiscoveryViewMode('brd'); localStorage.setItem('discovery-view-mode', 'brd') }}
                      className={`px-3 py-1 rounded-[5px] font-medium transition-colors ${
                        discoveryViewMode === 'brd'
                          ? 'bg-white text-[#37352f] shadow-sm'
                          : 'text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      BRD View
                    </button>
                    <button
                      onClick={() => { setDiscoveryViewMode('canvas'); localStorage.setItem('discovery-view-mode', 'canvas') }}
                      className={`px-3 py-1 rounded-[5px] font-medium transition-colors ${
                        discoveryViewMode === 'canvas'
                          ? 'bg-white text-[#37352f] shadow-sm'
                          : 'text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      Canvas View
                    </button>
                  </div>
                </div>

                {discoveryViewMode === 'brd' ? (
                  <div className="flex-1 min-h-0 rounded-2xl border border-[#E5E5E5] bg-white shadow-md overflow-hidden">
                    <BRDCanvas
                      projectId={projectId}
                      initialData={brdData}
                      initialNextActions={nextActions}
                      onRefresh={loadData}
                      onSendToChat={handleSendActionToChat}
                      pendingAction={pendingAction}
                      onPendingActionConsumed={() => setPendingAction(null)}
                      onActiveSectionChange={setActiveBrdSection}
                    />
                  </div>
                ) : (
                  <CanvasView projectId={projectId} onRefresh={loadData} />
                )}
              </div>
            )}

            {phase === 'build' && canvasData && (
              <div className="h-[calc(100vh-140px)] bg-white rounded-card border border-ui-cardBorder overflow-hidden relative">
                {/* Synthesizing banner — floats over prototype */}
                {reviewPhase === 'synthesizing' && (
                  <div className="absolute top-0 left-0 right-0 z-10 flex items-center justify-center gap-2 px-4 py-2 bg-[#3FAF7A]/10 border-b border-[#3FAF7A]/20 text-sm text-[#25785A]">
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-[#3FAF7A] border-t-transparent" />
                    <span className="font-medium">Synthesizing feedback...</span>
                    <span className="text-xs text-[#666666]">Generating code updates from review verdicts</span>
                  </div>
                )}

                <BuildPhaseView
                  projectId={projectId}
                  prototypeUrl={canvasData.prototype_url}
                  prototypeUpdatedAt={canvasData.prototype_updated_at}
                  readinessScore={brdData?.completeness?.overall_score ?? readinessData?.score ?? canvasData.readiness_score}
                  onUpdatePrototypeUrl={handleUpdatePrototypeUrl}
                  onGeneratePrototype={handleGeneratePrototype}
                  isReviewActive={isReviewActive}
                  onStartReview={handleStartReview}
                  onEndReview={handleEndReview}
                  session={reviewSession}
                  overlays={overlays}
                  vpSteps={vpSteps}
                  reviewTourMode={reviewTourMode}
                  onFeatureClick={handleFeatureClick}
                  onPageChange={handlePageChange}
                  onTourStepChange={handleTourStepChange}
                  onTourEnd={handleTourEnd}
                  onFrameReady={handleFrameReady}
                  routeFeatureMap={routeFeatureMap}
                  isFrameReady={isFrameReady}
                  frameRef={frameRef}
                  collaborationWidth={collaborationWidth}
                />
              </div>
            )}

            {phase === 'live' && (
              <div className="flex items-center justify-center h-[calc(100vh-200px)]">
                <div className="text-center">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-ui-background flex items-center justify-center">
                    <span className="text-2xl">🚀</span>
                  </div>
                  <h3 className="text-section text-ui-headingDark mb-2">
                    Live Product View
                  </h3>
                  <p className="text-support text-ui-supportText">
                    Coming soon - track your product post-launch
                  </p>
                </div>
              </div>
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

        {/* Right Panel — BrainBubble for Discovery/Overview, CollaborationPanel for Build/Review */}
        {useBrainBubble ? (
          <BrainBubble
            projectId={projectId}
            actionCount={contextFrame?.actions?.length ?? 0}
            messages={messages}
            isChatLoading={isChatLoading}
            onSendMessage={sendMessage}
            onSendSignal={sendSignal}
            onAddLocalMessage={addLocalMessage}
            onCascade={() => { mutateBrd(); mutateContextFrame() }}
            entityDetection={entityDetection}
            isSavingAsSignal={isSavingAsSignal}
            onSaveAsSignal={async () => { await saveAsSignal(); mutateBrd(); mutateContextFrame() }}
            onDismissDetection={dismissDetection}
            onOpenChange={setBrainPanelOpen}
            contextActions={contextFrame?.actions}
            onNewChat={startNewChat}
            onSetConversationContext={setConversationContext}
          />
        ) : (
          <CollaborationPanel
            projectId={projectId}
            projectName={canvasData?.project_name || 'Project'}
            pendingCount={canvasData?.pending_count}
            messages={messages}
            isChatLoading={isChatLoading}
            onSendMessage={sendMessage}
            onSendSignal={sendSignal}
            onAddLocalMessage={addLocalMessage}
            panelState={collaborationState}
            onPanelStateChange={setCollaborationState}
            isReviewActive={isReviewActive}
            isTourActive={isTourActive}
            currentOverlay={currentOverlay}
            currentTourStep={currentTourStep}
            allOverlays={overlays}
            visibleFeatureIds={sessionContext.visible_features}
            session={reviewSession}
            sessionContext={sessionContext}
            prototypeId={prototypeId}
            onVerdictSubmit={handleVerdictSubmit}
          />
        )}
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
