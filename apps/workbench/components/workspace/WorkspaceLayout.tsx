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
import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import { AppSidebar } from './AppSidebar'
import { PhaseSwitcher, WorkspacePhase } from './PhaseSwitcher'
import { CollaborationPanel, type PanelState } from './CollaborationPanel'
import { RequirementsCanvas } from './canvas/RequirementsCanvas'
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
  getStatusNarrative,
  getVpSteps,
  getPrototypeForProject,
  getPrototypeOverlays,
  createPrototypeSession,
} from '@/lib/api'
import type { CanvasData } from '@/types/workspace'
import type { ReadinessScore } from '@/lib/api'
import type { StatusNarrative, VpStep } from '@/types/api'
import type { FeatureOverlay, PrototypeSession, TourStep, SessionContext, RouteFeatureMap } from '@/types/prototype'
import type { PrototypeFrameHandle } from '@/components/prototype/PrototypeFrame'

interface WorkspaceLayoutProps {
  projectId: string
  children?: React.ReactNode
}

export function WorkspaceLayout({ projectId, children }: WorkspaceLayoutProps) {
  const [phase, setPhase] = useState<WorkspacePhase>('overview')
  const [canvasData, setCanvasData] = useState<CanvasData | null>(null)
  const [readinessData, setReadinessData] = useState<ReadinessScore | null>(null)
  const [narrativeData, setNarrativeData] = useState<StatusNarrative | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [collaborationState, setCollaborationState] = useState<PanelState>('normal')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true)
  const [activeBottomPanel, setActiveBottomPanel] = useState<'context' | 'evidence' | 'history' | null>(null)

  // Review mode state
  const [isReviewActive, setIsReviewActive] = useState(false)
  const [reviewSession, setReviewSession] = useState<PrototypeSession | null>(null)
  const [overlays, setOverlays] = useState<FeatureOverlay[]>([])
  const [vpSteps, setVpSteps] = useState<VpStep[]>([])
  const [currentTourStep, setCurrentTourStep] = useState<TourStep | null>(null)
  const [answeredQuestionIds, setAnsweredQuestionIds] = useState<Set<string>>(new Set())
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

  // Load workspace data
  const loadData = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)

      const [data, readiness, narrative] = await Promise.all([
        getWorkspaceData(projectId),
        getReadinessScore(projectId).catch(() => null),
        getStatusNarrative(projectId).catch(() => null),
      ])

      // If there's an active prototype with a deploy_url, prefer it over the
      // manually-entered projects.prototype_url
      const proto = await getPrototypeForProject(projectId).catch(() => null)
      if (proto?.deploy_url) {
        data.prototype_url = proto.deploy_url
      }

      setCanvasData(data)
      setReadinessData(readiness)
      setNarrativeData(narrative)

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
  }, [projectId])

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
      setAnsweredQuestionIds(new Set())
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

  const handleEndReview = useCallback(() => {
    setIsReviewActive(false)
    setReviewSession(null)
    setCurrentTourStep(null)
    setSessionContext((prev) => ({
      ...prev,
      active_feature_id: null,
      active_feature_name: null,
      active_component: null,
    }))
    frameRef.current?.sendMessage({ type: 'aios:clear-highlights' })
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

  const handleQuestionAnswered = useCallback((questionId: string) => {
    setAnsweredQuestionIds((prev) => new Set(prev).add(questionId))
  }, [])

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
                <Link
                  href={`/projects/${projectId}`}
                  className="flex items-center gap-1.5 text-sm text-ui-supportText hover:text-ui-headingDark transition-colors"
                  title="Back to classic view"
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span className="hidden sm:inline">Classic</span>
                </Link>
                <div className="h-5 w-px bg-ui-cardBorder" />
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
                narrativeData={narrativeData}
                onNavigateToPhase={(p) => setPhase(p)}
              />
            )}

            {phase === 'discovery' && canvasData && (
              <RequirementsCanvas
                data={canvasData}
                projectId={projectId}
                readinessScore={readinessData?.score}
                onUpdatePitchLine={handleUpdatePitchLine}
                onMapFeatureToStep={handleMapFeatureToStep}
                onRefresh={loadData}
              />
            )}

            {phase === 'build' && canvasData && (
              <div className="h-[calc(100vh-140px)] bg-white rounded-card border border-ui-cardBorder overflow-hidden">
                <BuildPhaseView
                  projectId={projectId}
                  prototypeUrl={canvasData.prototype_url}
                  prototypeUpdatedAt={canvasData.prototype_updated_at}
                  readinessScore={readinessData?.score ?? canvasData.readiness_score}
                  onUpdatePrototypeUrl={handleUpdatePrototypeUrl}
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
          answeredQuestionIds={answeredQuestionIds}
          onQuestionAnswered={handleQuestionAnswered}
        />
      </div>
    </AssistantProvider>
  )
}

export default WorkspaceLayout
