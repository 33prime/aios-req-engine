/**
 * BuildPhaseView - Prototype embed + epic tour
 *
 * Two modes:
 * 1. Normal: prototype iframe with URL controls + "Review with Overlays" button
 * 2. Review: EpicTourController navigates iframe by changing src URL
 *
 * Navigation uses iframe src swapping + postMessage for feature highlighting.
 * When the tour moves to a new epic, the iframe loads that page and highlights
 * relevant features via the injected AIOS bridge script.
 */

'use client'

import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import {
  Layers,
  RefreshCw,
  Maximize2,
  Minimize2,
  Check,
  X,
  Sparkles,
  Loader2,
} from 'lucide-react'
import EpicTourController from '@/components/prototype/EpicTourController'
import { DesignSelectionChat } from '@/components/prototype/DesignSelectionChat'
import type {
  PrototypeSession,
  DesignSelection,
} from '@/types/prototype'
import type { EpicOverlayPlan, EpicTourPhase, ReviewSummary } from '@/types/epic-overlay'
import ReviewSummaryOverlay from '@/components/prototype/ReviewSummaryOverlay'

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
  // Epic overlay plan
  epicPlan?: EpicOverlayPlan | null
  onEpicPhaseChange?: (phase: EpicTourPhase) => void
  onEpicIndexChange?: (epicIndex: number | null) => void
  onEpicCardChange?: (cardIndex: number | null) => void
  // Confirmed set for progress dots
  confirmedSet?: Set<string>
  // Layout
  collaborationWidth?: number
  // Review state machine
  reviewState?: string
  reviewSummary?: ReviewSummary | null
  isUpdating?: boolean
  onReviewComplete?: () => void
  onConfirmAndUpdate?: () => void
  onBackToReview?: () => void
}

export function BuildPhaseView({
  projectId,
  prototypeUrl,
  readinessScore,
  onUpdatePrototypeUrl,
  onGeneratePrototype,
  isReviewActive,
  onStartReview,
  onEndReview,
  session,
  epicPlan,
  onEpicPhaseChange,
  onEpicIndexChange,
  onEpicCardChange,
  confirmedSet,
  collaborationWidth = 0,
  reviewState,
  reviewSummary,
  isUpdating = false,
  onReviewComplete,
  onConfirmAndUpdate,
  onBackToReview,
}: BuildPhaseViewProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [urlValue, setUrlValue] = useState(prototypeUrl || '')
  const [isSaving, setIsSaving] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [iframeKey, setIframeKey] = useState(0)
  const [showDesignModal, setShowDesignModal] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [isEndingReview, setIsEndingReview] = useState(false)
  // Current iframe URL — base URL + tour route
  const [activeIframeSrc, setActiveIframeSrc] = useState(prototypeUrl || '')
  const [activeCardIndex, setActiveCardIndex] = useState<number | null>(null)
  // Loading overlay while iframe src-swaps without bridge
  const [iframeLoading, setIframeLoading] = useState(false)
  // Bridge detection — true when prototype has AiosBridge component
  const [bridgeReady, setBridgeReady] = useState(false)
  // Route manifest from prototype — maps epic indices to prototype routes
  const [routeManifest, setRouteManifest] = useState<{
    epic_routes?: Record<string, string>
    feature_routes?: Record<string, string>
  } | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const iframeRef = useRef<HTMLIFrameElement>(null)

  useEffect(() => {
    setUrlValue(prototypeUrl || '')
    setActiveIframeSrc(prototypeUrl || '')
  }, [prototypeUrl])

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [isEditing])

  // Bridge detection — listens for first aios:page-change from prototype iframe
  useEffect(() => {
    const handler = (e: MessageEvent) => {
      if (e.data?.type === 'aios:page-change') {
        setBridgeReady(true)
      }
    }
    window.addEventListener('message', handler)
    return () => window.removeEventListener('message', handler)
  }, [])

  // Reset bridge state when prototype URL changes (new deploy)
  useEffect(() => {
    setBridgeReady(false)
    setRouteManifest(null)
  }, [prototypeUrl])

  // Fetch route manifest from prototype (static JSON file)
  useEffect(() => {
    if (!prototypeUrl) return
    const url = prototypeUrl.replace(/\/$/, '') + '/route-manifest.json'
    fetch(url)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => { if (data) setRouteManifest(data) })
      .catch(() => {})
  }, [prototypeUrl])

  // Map epic plan routes through route manifest so EpicTourController
  // navigates to the correct prototype routes (not the epic plan's conceptual routes)
  const mappedEpicPlan = useMemo(() => {
    if (!epicPlan || !routeManifest?.epic_routes) return epicPlan
    // Remap config-only pages to dashboard to avoid blank iframe screens
    const fallback = '/dashboard'
    const routeRemaps: Record<string, string> = {
      '/settings': fallback,
      '/admin': fallback,
      '/profile': fallback,
    }
    return {
      ...epicPlan,
      vision_epics: epicPlan.vision_epics.map((epic, i) => {
        const manifestRoute = routeManifest.epic_routes![String(i)] || epic.primary_route || '/dashboard'
        const safeRoute = routeRemaps[manifestRoute] ?? manifestRoute
        return { ...epic, primary_route: safeRoute }
      }),
    }
  }, [epicPlan, routeManifest])

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

  // Get features for a given card from epic plan
  const getCardFeatures = useCallback(
    (cardIndex: number | null) => {
      if (cardIndex === null || !epicPlan) return []
      const allCards = [
        ...(epicPlan.vision_epics || []).map((e) => ({ ...e, _type: 'vision' as const })),
        ...(epicPlan.ai_flow_cards || []).map((c) => ({ ...c, _type: 'ai' as const })),
      ]
      const card = allCards[cardIndex]
      if (!card) return []
      return (card as any).features || []
    },
    [epicPlan]
  )

  // When card changes during tour, highlight features in iframe
  useEffect(() => {
    if (!bridgeReady || !isReviewActive || activeCardIndex === null || !iframeRef.current?.contentWindow) return
    const features = getCardFeatures(activeCardIndex)
    if (!features.length) return

    // Delay highlight to allow route change to complete
    const timer = setTimeout(() => {
      const win = iframeRef.current?.contentWindow
      if (!win) return

      if (features.length === 1) {
        // Single feature — spotlight highlight
        const f = features[0]
        win.postMessage(
          {
            type: 'aios:highlight-feature',
            featureId: f.feature_id,
            featureName: f.name,
            description: '',
            stepLabel: '',
            componentName: f.component_name || '',
            keywords: (f.name || '').split(/\s+/),
          },
          '*'
        )
      } else {
        // Multiple features — radar dots
        win.postMessage(
          {
            type: 'aios:show-radar',
            features: features.map((f: any) => ({
              featureId: f.feature_id,
              featureName: f.name,
              componentName: f.component_name || '',
              keywords: (f.name || '').split(/\s+/),
            })),
          },
          '*'
        )
      }
    }, 800)

    return () => clearTimeout(timer)
  }, [bridgeReady, activeCardIndex, isReviewActive, getCardFeatures])

  // Track card changes from tour controller
  const handleCardChange = useCallback(
    (cardIndex: number | null) => {
      setActiveCardIndex(cardIndex)
      onEpicCardChange?.(cardIndex)
    },
    [onEpicCardChange]
  )

  // Tour route change — postMessage if bridge ready, else src-swap with loading overlay
  const handleRouteChange = useCallback(
    (route: string | null) => {
      if (!prototypeUrl || !route) return

      if (bridgeReady && iframeRef.current?.contentWindow) {
        // SPA navigation via bridge — no page reload
        iframeRef.current.contentWindow.postMessage(
          { type: 'aios:navigate', path: route },
          '*'
        )
      } else {
        // No bridge — fall back to src swap with loading overlay
        const newSrc = prototypeUrl.replace(/\/$/, '') + route
        setIframeLoading(true)
        setActiveIframeSrc(newSrc)
      }
    },
    [prototypeUrl, bridgeReady]
  )

  return (
    <div
      className={`h-full flex flex-col ${isFullscreen ? 'fixed top-0 left-0 bottom-0 z-[100] bg-white' : ''}`}
      style={isFullscreen ? { right: collaborationWidth } : undefined}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-white">
        <div className="flex items-center gap-4">
          {isReviewActive && session ? (
            <>
              <h2 className="text-sm font-semibold text-[#37352f]">
                Session {session.session_number}
              </h2>
              <span className="text-xs text-text-placeholder">Reviewing</span>
            </>
          ) : (
            <>
              <h2 className="text-sm font-semibold text-[#37352f]">Prototype</h2>
              <div className="flex items-center gap-2">
                <div className="w-20 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                  <div className="h-full bg-brand-primary rounded-full transition-all" style={{ width: `${readinessScore}%` }} />
                </div>
                <span className="text-xs font-medium text-[#37352f]">{Math.round(readinessScore)}% ready</span>
              </div>
            </>
          )}
        </div>

        <div className="flex items-center gap-2">
          {prototypeUrl && (
            <>
              <button
                onClick={refreshIframe}
                className="p-1.5 text-text-placeholder hover:text-text-body hover:bg-surface-muted rounded-lg transition-colors"
                title="Refresh preview"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setIsFullscreen(!isFullscreen)}
                className="p-1.5 text-text-placeholder hover:text-text-body hover:bg-surface-muted rounded-lg transition-colors"
                title={isFullscreen ? 'Exit fullscreen (Esc)' : 'Fullscreen'}
              >
                {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
              </button>

              {/* Review toggle */}
              {!isReviewActive && (
                <button
                  onClick={onStartReview}
                  className="flex items-center gap-1.5 px-3 py-1 text-xs font-medium text-brand-primary bg-brand-primary-light hover:bg-brand-primary-light rounded-lg transition-colors"
                >
                  <Layers className="w-3.5 h-3.5" />
                  Review Epics
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {/* Inline URL input */}
      {!isReviewActive && isEditing && (
        <div className="px-4 py-2 bg-surface-muted border-b border-border">
          <div className="flex items-center gap-2">
            <input
              ref={inputRef}
              type="url"
              value={urlValue}
              onChange={(e) => setUrlValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="https://your-prototype.netlify.app"
              className="flex-1 px-3 py-1.5 text-sm bg-white border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary"
              disabled={isSaving}
            />
            <button onClick={handleCancel} className="p-1.5 text-text-placeholder hover:text-text-body rounded transition-colors" disabled={isSaving}>
              <X className="w-4 h-4" />
            </button>
            <button onClick={handleSave} className="p-1.5 text-brand-primary hover:bg-brand-primary-light rounded transition-colors" disabled={isSaving}>
              <Check className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Epic Tour Controller — only during review */}
      {isReviewActive && session && mappedEpicPlan && mappedEpicPlan.vision_epics.length > 0 && (
        <EpicTourController
          epicPlan={mappedEpicPlan}
          onPhaseChange={onEpicPhaseChange ?? (() => {})}
          onEpicChange={onEpicIndexChange ?? (() => {})}
          onCardChange={handleCardChange}
          onRouteChange={handleRouteChange}
          autoStart
          confirmedSet={confirmedSet}
          onReviewComplete={onReviewComplete}
          reviewState={reviewState}
        />
      )}

      {/* Prototype preview — single iframe, src changes when tour navigates */}
      <div className="flex-1 bg-gray-100 relative min-h-0">
        {/* Review Summary Overlay */}
        {reviewState === 'complete' && reviewSummary && (
          <ReviewSummaryOverlay
            summary={reviewSummary}
            isUpdating={isUpdating}
            onConfirmAndUpdate={onConfirmAndUpdate ?? (() => {})}
            onBackToReview={onBackToReview ?? (() => {})}
          />
        )}
        {prototypeUrl ? (
          <>
            {iframeLoading && (
              <div className="absolute inset-0 z-10 flex items-center justify-center bg-white/60 backdrop-blur-sm">
                <Loader2 className="w-6 h-6 text-brand-primary animate-spin" />
              </div>
            )}
            <iframe
              ref={iframeRef}
              key={iframeKey}
              src={isReviewActive ? activeIframeSrc : prototypeUrl}
              className="w-full h-full border-0"
              title="Prototype Preview"
              sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
              onLoad={() => setIframeLoading(false)}
            />
          </>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-brand-primary-light flex items-center justify-center">
                <Sparkles className="w-8 h-8 text-brand-primary" />
              </div>
              <h3 className="text-base font-semibold text-[#37352f] mb-2">Add a Prototype</h3>
              <p className="text-sm text-text-placeholder mb-5">
                Paste your prototype URL to start reviewing epics.
              </p>
              {onGeneratePrototype ? (
                <button
                  onClick={() => setShowDesignModal(true)}
                  className="px-5 py-2.5 bg-brand-primary text-white text-sm font-medium rounded-lg hover:bg-[#25785A] transition-colors inline-flex items-center gap-2"
                >
                  <Sparkles className="w-4 h-4" />
                  Generate Prototype
                </button>
              ) : (
                <button
                  onClick={() => setIsEditing(true)}
                  className="px-5 py-2.5 bg-brand-primary text-white text-sm font-medium rounded-lg hover:bg-[#25785A] transition-colors"
                >
                  Add Prototype URL
                </button>
              )}
              <div className="mt-3">
                <button
                  onClick={() => setIsEditing(true)}
                  className="text-sm text-text-placeholder hover:text-text-body transition-colors underline underline-offset-2"
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
