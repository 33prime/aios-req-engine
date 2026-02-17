/**
 * WorkspaceLayout - Three-zone layout for project workspace
 *
 * Layout:
 * - Left: AppSidebar (global navigation)
 * - Center: Main workspace (phase-dependent content)
 * - Right: CollaborationPanel (chat, portal, activity)
 */

'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { AppSidebar } from './AppSidebar'
import { PhaseSwitcher, WorkspacePhase } from './PhaseSwitcher'
import { CollaborationPanel, type PanelState } from './CollaborationPanel'
import { CanvasView } from './canvas/CanvasView'
import { BRDCanvas } from './brd/BRDCanvas'
import { BuildPhaseView } from './BuildPhaseView'
import { OverviewPanel } from './OverviewPanel'
import { BottomDock } from './BottomDock'
import { useChat } from '@/lib/useChat'
import { AssistantProvider } from '@/lib/assistant'
import {
  getWorkspaceData,
  updatePitchLine,
  updatePrototypeUrl,
  mapFeatureToStep,
  getReadinessScore,
  getVpSteps,
  getPrototypeForProject,
  getPrototypeOverlays,
  createPrototypeSession,
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
import { useBRDData } from '@/lib/hooks/use-api'
import type { CanvasData } from '@/types/workspace'
import type { ReadinessScore, NextAction } from '@/lib/api'
import type { VpStep } from '@/types/api'
import type { DesignSelection, FeatureOverlay, FeatureVerdict, PrototypeSession, TourStep, SessionContext, RouteFeatureMap } from '@/types/prototype'
import type { PrototypeFrameHandle } from '@/components/prototype/PrototypeFrame'

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
  const { data: brdSwr, mutate: mutateBrd } = useBRDData(projectId, false)
  const brdData = brdSwr ?? null
  const nextActions = brdSwr?.next_actions ?? null
  const [collaborationState, setCollaborationState] = useState<PanelState>('normal')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true)
  const [activeBottomPanel, setActiveBottomPanel] = useState<'context' | 'evidence' | 'history' | null>(null)
  const [discoveryViewMode, setDiscoveryViewMode] = useState<'brd' | 'canvas'>(() => {
    if (typeof window !== 'undefined') {
      return (localStorage.getItem('discovery-view-mode') as 'brd' | 'canvas') || 'brd'
    }
    return 'brd'
  })

  // Pending action from cross-view navigation (e.g., Overview → BRD)
  const [pendingAction, setPendingAction] = useState<NextAction | null>(null)

  // Review mode state
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
  const { messages, isLoading: isChatLoading, sendMessage, sendSignal, addLocalMessage } = useChat({
    projectId,
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
  const handleStartReview = useCallback(async () => {
    try {
      // Load prototype, overlays, and VP steps
      const proto = await getPrototypeForProject(projectId)
      const [ovls, steps] = await Promise.all([
        getPrototypeOverlays(proto.id),
        getVpSteps(projectId),
      ])
      setOverlays(ovls)
      setVpSteps(steps)

      // Use the prototype's deploy_url as the canonical URL
      if (proto.deploy_url) {
        setCanvasData((prev) => prev ? { ...prev, prototype_url: proto.deploy_url } : prev)
      }

      // Create a new session
      const session = await createPrototypeSession(proto.id)
      setReviewSession(session)
      setIsReviewActive(true)
      setPrototypeId(proto.id)
      setReviewPhase('active')
      setClientShareData(null)
      setRouteFeatureMap(new Map())
      setIsFrameReady(false)

      // Auto-expand collaboration panel to show review info
      if (collaborationState === 'collapsed') {
        setCollaborationState('normal')
      }
    } catch (err) {
      console.error('Failed to start review:', err)
    }
  }, [projectId, collaborationState])

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
  const collaborationWidth =
    collaborationState === 'collapsed' ? 48 :
    collaborationState === 'wide' ? 400 : 320

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
                initialTaskStats={taskStats}
                initialHistory={collaborationHistory}
                initialQuestionCounts={questionCounts}
                onNavigateToPhase={(p) => setPhase(p)}
                onActionExecute={handleActionExecuteFromOverview}
              />
            )}

            {phase === 'discovery' && canvasData && (
              <div>
                {/* View mode toggle */}
                <div className="flex items-center justify-end mb-2">
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
                  <BRDCanvas
                    projectId={projectId}
                    initialData={brdData}
                    initialNextActions={nextActions}
                    onRefresh={loadData}
                    onSendToChat={handleSendActionToChat}
                    pendingAction={pendingAction}
                    onPendingActionConsumed={() => setPendingAction(null)}
                  />
                ) : (
                  <CanvasView projectId={projectId} onRefresh={loadData} />
                )}
              </div>
            )}

            {phase === 'build' && canvasData && (
              <div className="h-[calc(100vh-140px)] bg-white rounded-card border border-ui-cardBorder overflow-hidden">
                {reviewPhase === 'awaiting_client' && clientShareData ? (
                  <AwaitingClientPanel
                    overlays={overlays}
                    clientShareData={clientShareData}
                    reviewPhase={reviewPhase}
                    onShareWithClient={() => {
                      const fullUrl = typeof window !== 'undefined'
                        ? `${window.location.origin}${clientShareData.url}`
                        : clientShareData.url
                      navigator.clipboard.writeText(fullUrl)
                    }}
                    onFixFirst={handleRunSynthesis}
                    onKeepWorking={handleKeepWorking}
                  />
                ) : reviewPhase === 'synthesizing' ? (
                  <div className="flex items-center justify-center h-full bg-[#F4F4F4]">
                    <div className="text-center">
                      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-[#3FAF7A] mx-auto mb-4" />
                      <h3 className="text-sm font-semibold text-[#333333]">Synthesizing feedback...</h3>
                      <p className="text-xs text-[#666666] mt-1">Generating code updates from review verdicts</p>
                    </div>
                  </div>
                ) : (
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
                )}
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

        {/* Right Collaboration Panel */}
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
      </div>
    </AssistantProvider>
  )
}

// =============================================================================
// AwaitingClientPanel — shown after consultant ends review
// =============================================================================

function AwaitingClientPanel({
  overlays,
  clientShareData,
  reviewPhase,
  onShareWithClient,
  onFixFirst,
  onKeepWorking,
}: {
  overlays: FeatureOverlay[]
  clientShareData: { token: string; url: string }
  reviewPhase: string
  onShareWithClient: () => void
  onFixFirst: () => void
  onKeepWorking: () => void
}) {
  const fullUrl = typeof window !== 'undefined'
    ? `${window.location.origin}${clientShareData.url}`
    : clientShareData.url

  const verdictCounts = overlays.reduce(
    (acc, o) => {
      const v = o.consultant_verdict
      if (v === 'aligned') acc.aligned++
      else if (v === 'needs_adjustment') acc.needs_adjustment++
      else if (v === 'off_track') acc.off_track++
      return acc
    },
    { aligned: 0, needs_adjustment: 0, off_track: 0 }
  )

  return (
    <div className="flex items-center justify-center h-full bg-[#F4F4F4]">
      <div className="max-w-lg w-full space-y-6 px-6">
        <div className="text-center">
          <h2 className="text-lg font-semibold text-[#333333]">Review Complete</h2>
          <p className="text-sm text-[#666666] mt-1">What would you like to do next?</p>
        </div>

        {/* Verdict summary */}
        <div className="rounded-2xl border border-[#E5E5E5] bg-white p-5 shadow-md">
          <p className="text-xs font-medium text-[#666666] uppercase tracking-wide mb-3">
            Your Verdict Summary
          </p>
          <div className="flex gap-4">
            <div className="flex-1 text-center">
              <div className="text-xl font-bold text-[#25785A]">{verdictCounts.aligned}</div>
              <div className="text-[10px] text-[#666666]">Aligned</div>
            </div>
            <div className="flex-1 text-center">
              <div className="text-xl font-bold text-amber-700">{verdictCounts.needs_adjustment}</div>
              <div className="text-[10px] text-[#666666]">Needs Adj.</div>
            </div>
            <div className="flex-1 text-center">
              <div className="text-xl font-bold text-red-700">{verdictCounts.off_track}</div>
              <div className="text-[10px] text-[#666666]">Off Track</div>
            </div>
          </div>
        </div>

        {/* Share link */}
        <div className="rounded-2xl border border-[#E5E5E5] bg-white p-5 shadow-md">
          <p className="text-xs font-medium text-[#666666] uppercase tracking-wide mb-2">
            Client Review Link
          </p>
          <div className="flex items-center gap-2">
            <input
              readOnly
              value={fullUrl}
              className="flex-1 text-xs px-3 py-2 border border-[#E5E5E5] rounded-lg bg-[#F4F4F4] text-[#333333] truncate"
            />
            <button
              onClick={() => navigator.clipboard.writeText(fullUrl)}
              className="px-3 py-2 text-xs font-medium border border-[#E5E5E5] rounded-lg hover:bg-[#F4F4F4] transition-colors text-[#333333]"
            >
              Copy
            </button>
          </div>
        </div>

        {/* Action buttons */}
        <div className="space-y-3">
          <button
            onClick={onShareWithClient}
            className="w-full px-6 py-3 bg-[#3FAF7A] text-white font-medium rounded-xl hover:bg-[#25785A] transition-all duration-200 shadow-md"
          >
            Share with Client — All Good
          </button>
          <button
            onClick={onFixFirst}
            className="w-full px-6 py-3 bg-white border border-[#E5E5E5] text-[#333333] font-medium rounded-xl hover:bg-[#F4F4F4] transition-all duration-200 shadow-md"
          >
            Fix First, Then Share
          </button>
          <button
            onClick={onKeepWorking}
            className="w-full px-4 py-2 text-sm text-[#666666] hover:text-[#333333] transition-colors"
          >
            Not Ready — Keep Working
          </button>
        </div>

        {/* Polling indicator */}
        <p className="text-center text-[10px] text-[#999999]">
          Listening for client feedback...
        </p>
      </div>
    </div>
  )
}

export default WorkspaceLayout
