'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useParams } from 'next/navigation'
import PrototypeFrame from '@/components/prototype/PrototypeFrame'
import type { PrototypeFrameHandle } from '@/components/prototype/PrototypeFrame'
import FeatureOverlayPanel from '@/components/prototype/FeatureOverlayPanel'
import TourController from '@/components/prototype/TourController'
import ContextualSidebar from '@/components/prototype/ContextualSidebar'
import SessionChat from '@/components/prototype/SessionChat'
import {
  createPrototypeSession,
  endConsultantReview,
  getPrototypeForProject,
  getPrototypeOverlays,
  getVpSteps,
  prototypeSessionChat,
  submitPrototypeFeedback,
  synthesizePrototypeFeedback,
  triggerPrototypeCodeUpdate,
} from '@/lib/api'
import type { FeatureOverlay, PrototypeSession, SessionContext, TourStep, RouteFeatureMap } from '@/types/prototype'
import type { VpStep } from '@/types/api'

type SessionStatus = 'loading' | 'no_prototype' | 'ready' | 'reviewing' | 'synthesizing' | 'updating'

/**
 * Consultant prototype review session page.
 *
 * Three-zone layout:
 * - Left: PrototypeFrame (iframe)
 * - Right: FeatureOverlayPanel or ContextualSidebar (380px)
 * - Bottom: SessionChat (collapsible, 240px)
 *
 * When reviewing, a TourController bar appears between the header and content.
 */
export default function PrototypeSessionPage() {
  const params = useParams()
  const projectId = params.projectId as string

  // State
  const [status, setStatus] = useState<SessionStatus>('loading')
  const [prototypeId, setPrototypeId] = useState<string | null>(null)
  const [deployUrl, setDeployUrl] = useState<string | null>(null)
  const [overlays, setOverlays] = useState<FeatureOverlay[]>([])
  const [vpSteps, setVpSteps] = useState<VpStep[]>([])
  const [session, setSession] = useState<PrototypeSession | null>(null)
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

  // Tour state
  const [isTourActive, setIsTourActive] = useState(false)
  const [currentTourStep, setCurrentTourStep] = useState<TourStep | null>(null)
  const [answeredQuestionIds, setAnsweredQuestionIds] = useState<Set<string>>(new Set())
  const [routeFeatureMap, setRouteFeatureMap] = useState<RouteFeatureMap>(new Map())
  const [isFrameReady, setIsFrameReady] = useState(false)
  const frameRef = useRef<PrototypeFrameHandle>(null)

  // Load prototype data + VP steps
  useEffect(() => {
    async function load() {
      try {
        const data = await getPrototypeForProject(projectId)
        setPrototypeId(data.id)
        setDeployUrl(data.deploy_url)

        const overlayData = await getPrototypeOverlays(data.id)
        setOverlays(overlayData)

        // Load VP steps for tour planning
        try {
          const steps = await getVpSteps(projectId)
          setVpSteps(steps)
        } catch {
          // VP steps may not exist yet — tour will work without them
        }

        setStatus('ready')
      } catch {
        setStatus('no_prototype')
      }
    }
    load()
  }, [projectId])

  // Start session
  const startSession = async () => {
    if (!prototypeId) return
    try {
      const sess = await createPrototypeSession(prototypeId)
      setSession(sess)
      setStatus('reviewing')
    } catch (e) {
      console.error('Failed to start session:', e)
    }
  }

  // Handle feature click from iframe
  const handleFeatureClick = useCallback(
    (featureId: string, componentName: string | null) => {
      const overlay = overlays.find((o) => o.feature_id === featureId)
      setSessionContext((prev) => ({
        ...prev,
        active_feature_id: featureId,
        active_feature_name: overlay?.overlay_content?.feature_name || null,
        active_component: componentName,
        features_reviewed: prev.features_reviewed.includes(featureId)
          ? prev.features_reviewed
          : [...prev.features_reviewed, featureId],
      }))
    },
    [overlays]
  )

  // Handle page change from iframe — also builds route-feature map
  const handlePageChange = useCallback((path: string, visibleFeatures: string[]) => {
    setSessionContext((prev) => ({
      ...prev,
      current_page: path,
      current_route: path,
      visible_features: visibleFeatures,
      active_feature_id: null,
      active_feature_name: null,
      active_component: null,
      page_history: [
        ...prev.page_history,
        { path, timestamp: new Date().toISOString(), features_visible: visibleFeatures },
      ],
    }))

    // Accumulate route-feature mapping for tour navigation
    if (visibleFeatures.length > 0) {
      setRouteFeatureMap((prev) => {
        const next = new Map(prev)
        next.set(path, visibleFeatures)
        return next
      })
    }
  }, [])

  // Handle feature selection from overlay panel
  const handleFeatureSelect = (featureId: string | null) => {
    if (!featureId) {
      setSessionContext((prev) => ({
        ...prev,
        active_feature_id: null,
        active_feature_name: null,
        active_component: null,
      }))
      return
    }
    const overlay = overlays.find((o) => o.feature_id === featureId)
    setSessionContext((prev) => ({
      ...prev,
      active_feature_id: featureId,
      active_feature_name: overlay?.overlay_content?.feature_name || null,
    }))
  }

  // Tour step change handler
  const handleTourStepChange = useCallback((step: TourStep | null) => {
    setCurrentTourStep(step)
    if (step) {
      setIsTourActive(true)
    }
  }, [])

  // Tour end handler
  const handleTourEnd = useCallback(() => {
    setIsTourActive(false)
    setCurrentTourStep(null)
  }, [])

  // Answer submission handler
  const handleAnswerSubmit = useCallback(
    async (questionId: string, answer: string) => {
      if (!session) return
      try {
        await submitPrototypeFeedback(session.id, {
          content: answer,
          feedback_type: 'answer',
          answers_question_id: questionId,
          feature_id: currentTourStep?.featureId,
          page_path: sessionContext.current_page,
          context: sessionContext,
        })
        setAnsweredQuestionIds((prev) => new Set(prev).add(questionId))
      } catch (e) {
        console.error('Failed to submit answer:', e)
      }
    },
    [session, currentTourStep, sessionContext]
  )

  // Chat handler
  const handleChatMessage = async (message: string): Promise<string> => {
    if (!session) return 'No active session.'
    const result = await prototypeSessionChat(session.id, message, sessionContext)
    return result.response
  }

  // End review
  const handleEndReview = async () => {
    if (!session) return
    try {
      // End tour if active
      if (isTourActive) {
        frameRef.current?.sendMessage({ type: 'aios:clear-highlights' })
        setIsTourActive(false)
        setCurrentTourStep(null)
      }

      await endConsultantReview(session.id)
      setStatus('synthesizing')

      // Auto-trigger synthesis
      await synthesizePrototypeFeedback(session.id)
      setStatus('updating')

      // Auto-trigger code update
      await triggerPrototypeCodeUpdate(session.id)
      setStatus('ready')
    } catch (e) {
      console.error('Failed to end review:', e)
      setStatus('ready')
    }
  }

  // Loading state
  if (status === 'loading') {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-ui-supportText">Loading prototype...</p>
      </div>
    )
  }

  // No prototype
  if (status === 'no_prototype') {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center space-y-4">
          <h2 className="text-h2 text-ui-headingDark">No Prototype Yet</h2>
          <p className="text-body text-ui-bodyText max-w-md">
            Generate a prototype from your discovery data to begin the refinement process.
          </p>
        </div>
      </div>
    )
  }

  // Ready — start session prompt
  if (status === 'ready' && !session) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center space-y-4">
          <h2 className="text-h2 text-ui-headingDark">Prototype Ready for Review</h2>
          <p className="text-body text-ui-bodyText max-w-md">
            {overlays.length} features analyzed. Start a session to review the prototype
            and capture requirements.
          </p>
          <button
            onClick={startSession}
            className="px-6 py-2.5 bg-brand-primary text-white font-medium rounded-lg hover:bg-[#033344] transition-all duration-200"
          >
            Start Review Session
          </button>
        </div>
      </div>
    )
  }

  // Active session
  return (
    <div className="flex flex-col h-full bg-ui-background">
      {/* Header */}
      <div className="bg-white border-b border-ui-cardBorder px-6 py-3 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-6">
          <h2 className="text-sm font-semibold text-ui-headingDark">
            Session {session?.session_number || 1}
          </h2>
          <span className="text-support text-ui-supportText">
            Coverage: {sessionContext.features_reviewed.length}/{overlays.length}
          </span>
        </div>
        <div className="flex items-center gap-3">
          {status === 'synthesizing' && (
            <span className="text-support text-brand-primary">Synthesizing feedback...</span>
          )}
          {status === 'updating' && (
            <span className="text-support text-brand-primary">Updating code...</span>
          )}
          {status === 'reviewing' && (
            <button
              onClick={handleEndReview}
              className="px-4 py-2 bg-brand-primary text-white text-sm font-medium rounded-lg hover:bg-[#033344] transition-all duration-200"
            >
              End Review
            </button>
          )}
        </div>
      </div>

      {/* Tour controller bar — only during active review */}
      {session && status === 'reviewing' && (
        <TourController
          overlays={overlays}
          vpSteps={vpSteps}
          routeFeatureMap={routeFeatureMap}
          frameRef={frameRef}
          isFrameReady={isFrameReady}
          onStepChange={handleTourStepChange}
          onTourEnd={handleTourEnd}
        />
      )}

      {/* Main content: iframe + sidebar */}
      <div className="flex flex-1 min-h-0">
        {/* Prototype iframe */}
        {deployUrl ? (
          <PrototypeFrame
            ref={frameRef}
            deployUrl={deployUrl}
            onFeatureClick={handleFeatureClick}
            onPageChange={handlePageChange}
            onIframeReady={() => setIsFrameReady(true)}
          />
        ) : (
          <div className="flex-1 flex items-center justify-center text-ui-supportText">
            No deploy URL available
          </div>
        )}

        {/* Conditional sidebar: tour sidebar or standard overlay panel */}
        {isTourActive && session ? (
          <ContextualSidebar
            overlays={overlays}
            currentStep={currentTourStep}
            visibleFeatures={sessionContext.visible_features}
            sessionId={session.id}
            prototypeId={prototypeId || ''}
            onAnswerSubmit={handleAnswerSubmit}
            answeredQuestionIds={answeredQuestionIds}
          />
        ) : (
          <FeatureOverlayPanel
            overlays={overlays}
            activeFeatureId={sessionContext.active_feature_id}
            onFeatureSelect={handleFeatureSelect}
          />
        )}
      </div>

      {/* Session chat */}
      {session && (
        <SessionChat
          sessionId={session.id}
          context={sessionContext}
          onSendMessage={handleChatMessage}
        />
      )}
    </div>
  )
}
