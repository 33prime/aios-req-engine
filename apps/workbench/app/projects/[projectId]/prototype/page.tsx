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
  getPrototypeSession,
  getVpSteps,
  prototypeSessionChat,
  submitPrototypeFeedback,
  synthesizePrototypeFeedback,
  triggerPrototypeCodeUpdate,
} from '@/lib/api'
import type { FeatureOverlay, PrototypeSession, SessionContext, TourStep, RouteFeatureMap } from '@/types/prototype'
import type { VpStep } from '@/types/api'

type SessionStatus = 'loading' | 'no_prototype' | 'ready' | 'reviewing' | 'awaiting_client' | 'synthesizing' | 'updating'

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

  // Client share state
  const [clientShareData, setClientShareData] = useState<{
    token: string; url: string
  } | null>(null)

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

  // End review — stop after generating client link
  const handleEndReview = async () => {
    if (!session) return
    try {
      if (isTourActive) {
        frameRef.current?.sendMessage({ type: 'aios:clear-highlights' })
        setIsTourActive(false)
        setCurrentTourStep(null)
      }

      const result = await endConsultantReview(session.id)
      setClientShareData({ token: result.client_review_token, url: result.client_review_url })
      setStatus('awaiting_client')
    } catch (e) {
      console.error('Failed to end review:', e)
    }
  }

  // Synthesis handler — used by all post-review paths
  const handleRunSynthesis = async () => {
    if (!session) return
    try {
      setStatus('synthesizing')
      await synthesizePrototypeFeedback(session.id)
      setStatus('updating')
      await triggerPrototypeCodeUpdate(session.id)
    } catch (e) {
      console.error('Failed during synthesis/update:', e)
    }
    setStatus('ready')
    setSession(null)
    setClientShareData(null)
  }

  // Poll for client completion while awaiting_client
  useEffect(() => {
    if (status !== 'awaiting_client' || !session) return
    const interval = setInterval(async () => {
      try {
        const fresh = await getPrototypeSession(session.id)
        if (fresh.status === 'client_complete') {
          clearInterval(interval)
          handleRunSynthesis()
        }
      } catch { /* ignore polling errors */ }
    }, 10000)
    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, session])

  // Loading state
  if (status === 'loading') {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-[#999999]">Loading prototype...</p>
      </div>
    )
  }

  // No prototype
  if (status === 'no_prototype') {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center space-y-4">
          <h2 className="text-xl text-[#333333]">No Prototype Yet</h2>
          <p className="text-sm text-[#666666] max-w-md">
            Generate a prototype from your discovery data to begin the refinement process.
          </p>
        </div>
      </div>
    )
  }

  // Awaiting client — show share panel
  if (status === 'awaiting_client' && clientShareData) {
    const fullUrl = typeof window !== 'undefined'
      ? `${window.location.origin}${clientShareData.url}`
      : clientShareData.url

    // Count verdicts from overlays
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
              onClick={() => {
                navigator.clipboard.writeText(fullUrl)
              }}
              className="w-full px-6 py-3 bg-[#3FAF7A] text-white font-medium rounded-xl hover:bg-[#25785A] transition-all duration-200 shadow-md"
            >
              Share with Client — All Good
            </button>
            <button
              onClick={handleRunSynthesis}
              className="w-full px-6 py-3 bg-white border border-[#E5E5E5] text-[#333333] font-medium rounded-xl hover:bg-[#F4F4F4] transition-all duration-200 shadow-md"
            >
              Fix First, Then Share
            </button>
            <button
              onClick={() => {
                setStatus('reviewing')
                setClientShareData(null)
              }}
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

  // Ready — start session prompt
  if (status === 'ready' && !session) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center space-y-4">
          <h2 className="text-xl text-[#333333]">Prototype Ready for Review</h2>
          <p className="text-sm text-[#666666] max-w-md">
            {overlays.length} features analyzed. Start a session to review the prototype
            and capture requirements.
          </p>
          <button
            onClick={startSession}
            className="px-6 py-2.5 bg-[#3FAF7A] text-white font-medium rounded-lg hover:bg-[#033344] transition-all duration-200"
          >
            Start Review Session
          </button>
        </div>
      </div>
    )
  }

  // Active session
  return (
    <div className="flex flex-col h-full bg-[#F9F9F9]">
      {/* Header */}
      <div className="bg-white border-b border-[#E5E5E5] px-6 py-3 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-6">
          <h2 className="text-sm font-semibold text-[#333333]">
            Session {session?.session_number || 1}
          </h2>
          <span className="text-[12px] text-[#999999]">
            Coverage: {sessionContext.features_reviewed.length}/{overlays.length}
          </span>
        </div>
        <div className="flex items-center gap-3">
          {status === 'synthesizing' && (
            <span className="text-[12px] text-[#3FAF7A]">Synthesizing feedback...</span>
          )}
          {status === 'updating' && (
            <span className="text-[12px] text-[#3FAF7A]">Updating code...</span>
          )}
          {status === 'reviewing' && (
            <button
              onClick={handleEndReview}
              className="px-4 py-2 bg-[#3FAF7A] text-white text-sm font-medium rounded-lg hover:bg-[#033344] transition-all duration-200"
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
          <div className="flex-1 flex items-center justify-center text-[#999999]">
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
