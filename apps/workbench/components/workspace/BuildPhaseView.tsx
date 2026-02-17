/**
 * BuildPhaseView - Prototype embed, build tracking, and review mode
 *
 * Two modes:
 * 1. Normal: prototype iframe with URL controls + "Review with Overlays" button
 * 2. Review: bridge-connected PrototypeFrame with TourController, session management
 *
 * Review mode is controlled by the parent via reviewMode prop.
 */

'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import {
  Layers,
  RefreshCw,
  Maximize2,
  Minimize2,
  Check,
  X,
  Square,
  CheckCircle2,
  Sparkles,
  Loader2,
} from 'lucide-react'
import PrototypeFrame from '@/components/prototype/PrototypeFrame'
import type { PrototypeFrameHandle } from '@/components/prototype/PrototypeFrame'
import TourController from '@/components/prototype/TourController'
import { DesignSelectionChat } from '@/components/prototype/DesignSelectionChat'
import type {
  FeatureOverlay,
  PrototypeSession,
  DesignSelection,
  SessionContext,
  TourStep,
  RouteFeatureMap,
} from '@/types/prototype'
import type { VpStep } from '@/types/api'

interface BuildPhaseViewProps {
  projectId: string
  prototypeUrl?: string | null
  prototypeUpdatedAt?: string | null
  readinessScore: number
  onUpdatePrototypeUrl: (url: string) => Promise<void>
  onGeneratePrototype?: (selection: DesignSelection) => Promise<void>
  // Review mode props
  isReviewActive: boolean
  onStartReview: () => void
  onEndReview: () => Promise<void>
  session: PrototypeSession | null
  overlays: FeatureOverlay[]
  vpSteps: VpStep[]
  /** When set to 'tour', auto-starts the guided tour once frame is ready */
  reviewTourMode?: 'tour' | 'explore'
  // Bridge callbacks — lifted to parent so it can update shared state
  onFeatureClick: (featureId: string, componentName: string | null) => void
  onPageChange: (path: string, visibleFeatures: string[]) => void
  onTourStepChange: (step: TourStep | null) => void
  onTourEnd: () => void
  onFrameReady: () => void
  routeFeatureMap: RouteFeatureMap
  isFrameReady: boolean
  frameRef: React.RefObject<PrototypeFrameHandle | null>
  // Layout — so fullscreen leaves room for the collaboration panel
  collaborationWidth?: number
}

export function BuildPhaseView({
  projectId,
  prototypeUrl,
  prototypeUpdatedAt,
  readinessScore,
  onUpdatePrototypeUrl,
  onGeneratePrototype,
  isReviewActive,
  onStartReview,
  onEndReview,
  session,
  overlays,
  vpSteps,
  reviewTourMode,
  onFeatureClick,
  onPageChange,
  onTourStepChange,
  onTourEnd,
  onFrameReady,
  routeFeatureMap,
  isFrameReady,
  frameRef,
  collaborationWidth = 320,
}: BuildPhaseViewProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [urlValue, setUrlValue] = useState(prototypeUrl || '')
  const [isSaving, setIsSaving] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [iframeKey, setIframeKey] = useState(0)
  const [showDesignModal, setShowDesignModal] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [isEndingReview, setIsEndingReview] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    setUrlValue(prototypeUrl || '')
  }, [prototypeUrl])

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [isEditing])

  // Escape key exits fullscreen
  useEffect(() => {
    if (!isFullscreen) return
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsFullscreen(false)
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [isFullscreen])

  const handleSave = async () => {
    if (!urlValue.trim()) {
      setIsEditing(false)
      return
    }

    let normalizedUrl = urlValue.trim()
    if (!/^https?:\/\//i.test(normalizedUrl)) {
      normalizedUrl = `https://${normalizedUrl}`
      setUrlValue(normalizedUrl)
    }

    setIsSaving(true)
    try {
      await onUpdatePrototypeUrl(normalizedUrl)
      setIsEditing(false)
    } catch (error) {
      console.error('Failed to save prototype URL:', error)
    } finally {
      setIsSaving(false)
    }
  }

  const handleCancel = () => {
    setUrlValue(prototypeUrl || '')
    setIsEditing(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSave()
    else if (e.key === 'Escape') handleCancel()
  }

  const refreshIframe = () => setIframeKey((k) => k + 1)

  const handleGeneratePrototype = async (selection: DesignSelection) => {
    if (!onGeneratePrototype) return
    setIsGenerating(true)
    try {
      await onGeneratePrototype(selection)
      setShowDesignModal(false)
    } catch (error) {
      console.error('Failed to generate prototype:', error)
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <div
      className={`h-full flex flex-col ${isFullscreen ? 'fixed top-0 left-0 bottom-0 z-[100] bg-white' : ''}`}
      style={isFullscreen ? { right: collaborationWidth } : undefined}
    >
      {/* Header — adapts to review mode */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-ui-cardBorder bg-white">
        <div className="flex items-center gap-4">
          {isReviewActive && session ? (
            <>
              <h2 className="text-section text-ui-headingDark">
                Session {session.session_number}
              </h2>
              <span className="text-xs text-ui-supportText">Reviewing</span>
            </>
          ) : (
            <>
              <h2 className="text-section text-ui-headingDark">Prototype</h2>
              <div className="flex items-center gap-2">
                <div className="w-20 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                  <div className="h-full bg-brand-teal rounded-full transition-all" style={{ width: `${readinessScore}%` }} />
                </div>
                <span className="text-sm font-medium text-ui-bodyText">{Math.round(readinessScore)}% ready</span>
              </div>
            </>
          )}
        </div>

        <div className="flex items-center gap-2">
          {prototypeUrl && (
            <>
              {!isReviewActive && (
                <button
                  onClick={refreshIframe}
                  className="p-2 text-ui-supportText hover:text-ui-headingDark hover:bg-ui-background rounded-lg transition-colors"
                  title="Refresh preview"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
              )}
              <button
                onClick={() => setIsFullscreen(!isFullscreen)}
                className="p-2 text-ui-supportText hover:text-ui-headingDark hover:bg-ui-background rounded-lg transition-colors"
                title={isFullscreen ? 'Exit fullscreen (Esc)' : 'Fullscreen'}
              >
                {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
              </button>

              {/* Review toggle button */}
              {isReviewActive ? (() => {
                const reviewedCount = overlays.filter(o => o.consultant_verdict).length
                const totalCount = overlays.length
                const allReviewed = totalCount > 0 && reviewedCount === totalCount

                return allReviewed ? (
                  <button
                    onClick={async () => {
                      setIsEndingReview(true)
                      try {
                        await onEndReview()
                      } finally {
                        setIsEndingReview(false)
                      }
                    }}
                    disabled={isEndingReview}
                    className="flex items-center gap-1.5 px-4 py-1.5 text-sm font-medium text-white bg-[#3FAF7A] hover:bg-[#25785A] rounded-xl transition-colors shadow-sm disabled:opacity-60"
                  >
                    {isEndingReview ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <CheckCircle2 className="w-3.5 h-3.5" />
                    )}
                    {isEndingReview ? 'Ending...' : 'End Review'}
                  </button>
                ) : (
                  <button
                    disabled
                    className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-[#999999] bg-[#F0F0F0] rounded-xl cursor-not-allowed"
                    title={`Review all features before ending (${reviewedCount}/${totalCount})`}
                  >
                    <Square className="w-3.5 h-3.5" />
                    End Review ({reviewedCount}/{totalCount})
                  </button>
                )
              })() : (
                <button
                  onClick={onStartReview}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-brand-primary bg-brand-primary/5 hover:bg-brand-primary/10 rounded-lg transition-colors"
                >
                  <Layers className="w-4 h-4" />
                  Review with Overlays
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {/* Inline URL input — only visible when actively editing (e.g. from empty state "paste URL" button) */}
      {!isReviewActive && isEditing && (
        <div className="px-4 py-2 bg-ui-background border-b border-ui-cardBorder">
          <div className="flex items-center gap-2">
            <input
              ref={inputRef}
              type="url"
              value={urlValue}
              onChange={(e) => setUrlValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="https://your-prototype.vercel.app"
              className="flex-1 px-3 py-1.5 text-sm bg-white border border-ui-cardBorder rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-teal/20 focus:border-brand-teal"
              disabled={isSaving}
            />
            <button onClick={handleCancel} className="p-1.5 text-ui-supportText hover:text-ui-bodyText rounded transition-colors" disabled={isSaving}>
              <X className="w-4 h-4" />
            </button>
            <button onClick={handleSave} className="p-1.5 text-brand-teal hover:bg-brand-teal/10 rounded transition-colors" disabled={isSaving}>
              <Check className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Tour controller bar — only during review */}
      {isReviewActive && session && (
        <TourController
          overlays={overlays}
          vpSteps={vpSteps}
          routeFeatureMap={routeFeatureMap}
          frameRef={frameRef}
          isFrameReady={isFrameReady}
          onStepChange={onTourStepChange}
          onTourEnd={onTourEnd}
          autoStart={reviewTourMode === 'tour'}
        />
      )}

      {/* Prototype preview */}
      <div className="flex-1 bg-gray-100 relative min-h-0">
        {isReviewActive && prototypeUrl ? (
          /* Bridge-connected frame during review */
          <PrototypeFrame
            ref={frameRef as React.Ref<PrototypeFrameHandle>}
            deployUrl={prototypeUrl}
            onFeatureClick={onFeatureClick}
            onPageChange={onPageChange}
            onIframeReady={onFrameReady}
          />
        ) : prototypeUrl ? (
          /* Normal dumb iframe */
          <iframe
            key={iframeKey}
            src={prototypeUrl}
            className="w-full h-full border-0"
            title="Prototype Preview"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
          />
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-brand-teal/10 flex items-center justify-center">
                <Sparkles className="w-8 h-8 text-brand-teal" />
              </div>
              <h3 className="text-section text-ui-headingDark mb-2">Generate a Prototype</h3>
              <p className="text-sm text-ui-supportText mb-5">
                Turn your discovery data into a v0.dev prompt with your chosen design direction.
              </p>
              {onGeneratePrototype ? (
                <button
                  onClick={() => setShowDesignModal(true)}
                  className="px-5 py-2.5 bg-brand-teal text-white text-sm font-medium rounded-lg hover:bg-brand-tealDark transition-colors inline-flex items-center gap-2"
                >
                  <Sparkles className="w-4 h-4" />
                  Generate Prototype
                </button>
              ) : (
                <button
                  onClick={() => setIsEditing(true)}
                  className="px-5 py-2.5 bg-brand-teal text-white text-sm font-medium rounded-lg hover:bg-brand-tealDark transition-colors"
                >
                  Add Prototype URL
                </button>
              )}
              <div className="mt-3">
                <button
                  onClick={() => setIsEditing(true)}
                  className="text-sm text-ui-supportText hover:text-ui-bodyText transition-colors underline underline-offset-2"
                >
                  Or paste a prototype URL
                </button>
              </div>
            </div>
          </div>
        )}

      </div>

      {/* Design Selection Chat */}
      <DesignSelectionChat
        isOpen={showDesignModal}
        onClose={() => setShowDesignModal(false)}
        onGenerate={handleGeneratePrototype}
        projectId={projectId}
        isGenerating={isGenerating}
      />
    </div>
  )
}

export default BuildPhaseView
