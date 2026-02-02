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
  ExternalLink,
  Layers,
  RefreshCw,
  Maximize2,
  Minimize2,
  Edit3,
  Check,
  X,
  Link as LinkIcon,
  AlertCircle,
  Square,
} from 'lucide-react'
import PrototypeFrame from '@/components/prototype/PrototypeFrame'
import type { PrototypeFrameHandle } from '@/components/prototype/PrototypeFrame'
import TourController from '@/components/prototype/TourController'
import type {
  FeatureOverlay,
  PrototypeSession,
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
  // Review mode props
  isReviewActive: boolean
  onStartReview: () => void
  onEndReview: () => void
  session: PrototypeSession | null
  overlays: FeatureOverlay[]
  vpSteps: VpStep[]
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
  isReviewActive,
  onStartReview,
  onEndReview,
  session,
  overlays,
  vpSteps,
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

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return null
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
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
              <a
                href={prototypeUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 text-ui-supportText hover:text-ui-headingDark hover:bg-ui-background rounded-lg transition-colors"
                title="Open in new tab"
              >
                <ExternalLink className="w-4 h-4" />
              </a>
              <button
                onClick={() => setIsFullscreen(!isFullscreen)}
                className="p-2 text-ui-supportText hover:text-ui-headingDark hover:bg-ui-background rounded-lg transition-colors"
                title={isFullscreen ? 'Exit fullscreen (Esc)' : 'Fullscreen'}
              >
                {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
              </button>

              {/* Review toggle button */}
              {isReviewActive ? (
                <button
                  onClick={onEndReview}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-red-600 bg-red-50 hover:bg-red-100 rounded-lg transition-colors"
                >
                  <Square className="w-3.5 h-3.5" />
                  End Review
                </button>
              ) : (
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

      {/* URL Bar — hidden during review */}
      {!isReviewActive && (
        <div className="px-4 py-2 bg-ui-background border-b border-ui-cardBorder">
          {isEditing ? (
            <div className="flex items-center gap-2">
              <LinkIcon className="w-4 h-4 text-ui-supportText flex-shrink-0" />
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
          ) : (
            <div onClick={() => setIsEditing(true)} className="flex items-center gap-2 cursor-pointer group">
              <LinkIcon className="w-4 h-4 text-ui-supportText flex-shrink-0" />
              {prototypeUrl ? (
                <span className="text-sm text-ui-bodyText truncate flex-1">{prototypeUrl}</span>
              ) : (
                <span className="text-sm text-ui-supportText italic">Click to add prototype URL...</span>
              )}
              <Edit3 className="w-3.5 h-3.5 text-ui-supportText opacity-0 group-hover:opacity-100 transition-opacity" />
              {prototypeUpdatedAt && (
                <span className="text-support text-ui-supportText ml-auto">Updated {formatDate(prototypeUpdatedAt)}</span>
              )}
            </div>
          )}
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
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-ui-background flex items-center justify-center">
                <LinkIcon className="w-8 h-8 text-ui-supportText" />
              </div>
              <h3 className="text-section text-ui-headingDark mb-2">Add Your Prototype URL</h3>
              <p className="text-sm text-ui-supportText mb-4">
                Paste the URL of your deployed prototype (Vercel, Replit, etc.) to preview it directly in the workspace.
              </p>
              <button
                onClick={() => setIsEditing(true)}
                className="px-4 py-2 bg-brand-teal text-white text-sm font-medium rounded-lg hover:bg-brand-tealDark transition-colors"
              >
                Add Prototype URL
              </button>
            </div>
          </div>
        )}

        {/* X-Frame-Options Warning — only in normal mode */}
        {!isReviewActive && prototypeUrl && (
          <div className="absolute bottom-4 left-4 right-4">
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-start gap-3 shadow-sm">
              <AlertCircle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm text-amber-800">
                  Some sites block embedding. If the preview doesn't load,{' '}
                  <a href={prototypeUrl} target="_blank" rel="noopener noreferrer" className="underline hover:text-amber-900">
                    open in a new tab
                  </a>.
                </p>
              </div>
              <button
                onClick={(e) => { const p = e.currentTarget.parentElement; if (p) p.style.display = 'none' }}
                className="text-amber-500 hover:text-amber-700"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default BuildPhaseView
