/**
 * BuildPhaseView - Prototype embed + epic tour
 *
 * Three modes:
 * 1. Empty: No prototype → "Generate Prototype" button (opens design selection)
 * 2. Building: Build in progress → live progress indicator
 * 3. Normal: Prototype deployed → iframe with URL controls + review
 * 4. Review: EpicTourController navigates iframe by changing src URL
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
  XCircle,
} from 'lucide-react'
import EpicTourController from '@/components/prototype/EpicTourController'
import BuildCinematicView from '@/components/prototype/BuildCinematicView'
import { DesignSelectionChat } from '@/components/prototype/DesignSelectionChat'
import { startBuild, getBuildStatus, cancelBuild } from '@/lib/api'
import type {
  PrototypeSession,
  DesignSelection,
  BuildStatus,
} from '@/types/prototype'
import type { EpicOverlayPlan, EpicTourPhase, ReviewSummary } from '@/types/epic-overlay'
import ReviewSummaryOverlay from '@/components/prototype/ReviewSummaryOverlay'

interface BuildPhaseViewProps {
  projectId: string
  prototypeUrl?: string | null
  prototypeUpdatedAt?: string | null
  readinessScore: number
  onUpdatePrototypeUrl: (url: string) => Promise<void>
  onPrototypeBuilt?: (deployUrl: string) => void
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
  onFeatureClick?: (featureSlug: string) => void
  onIframeRouteChange?: (route: string) => void
  /** Feature navigation requested from side panel */
  pendingFeatureNav?: { slug: string; route: string } | null
  onFeatureNavConsumed?: () => void
  // Verdict map for progress dots: "vision:0" → "confirmed" | "refine" | "flag_for_client"
  verdictMap?: Map<string, string>
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
  onPrototypeBuilt,
  isReviewActive,
  onStartReview,
  onEndReview,
  session,
  epicPlan,
  onEpicPhaseChange,
  onEpicIndexChange,
  onEpicCardChange,
  onFeatureClick,
  onIframeRouteChange,
  pendingFeatureNav,
  onFeatureNavConsumed,
  verdictMap,
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

  // Build pipeline state
  const [activeBuildId, setActiveBuildId] = useState<string | null>(null)
  const [buildStatus, setBuildStatus] = useState<BuildStatus | null>(null)
  const [buildError, setBuildError] = useState<string | null>(null)
  const buildPollRef = useRef<NodeJS.Timeout | null>(null)

  const inputRef = useRef<HTMLInputElement>(null)
  const iframeRef = useRef<HTMLIFrameElement>(null)

  const isBuilding = activeBuildId !== null && buildStatus?.status !== 'completed' && buildStatus?.status !== 'failed'

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

  // Bridge detection + feature click + route tracking
  useEffect(() => {
    const handler = (e: MessageEvent) => {
      if (!e.data?.type) return
      if (e.data.type === 'aios:page-change') {
        setBridgeReady(true)
        if (e.data.path) onIframeRouteChange?.(e.data.path)
      }
      if (e.data.type === 'aios:feature-click' && e.data.featureId) {
        onFeatureClick?.(e.data.featureId)
      }
    }
    window.addEventListener('message', handler)
    return () => window.removeEventListener('message', handler)
  }, [onFeatureClick, onIframeRouteChange])

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
  // Smart routing: pick the page where most of the epic's features live.
  const mappedEpicPlan = useMemo(() => {
    if (!epicPlan) return epicPlan
    const featureRoutes = routeManifest?.feature_routes || {}
    const fallback = '/dashboard'
    const routeRemaps: Record<string, string> = {
      '/admin': fallback,
      '/profile': fallback,
    }

    // Build set of known valid routes from the route manifest
    const validRoutes = new Set<string>()
    if (routeManifest) {
      for (const r of Object.values(routeManifest.epic_routes || {})) validRoutes.add(r as string)
      for (const r of Object.values(routeManifest.feature_routes || {})) validRoutes.add(r as string)
    }

    return {
      ...epicPlan,
      vision_epics: epicPlan.vision_epics.map((epic, i) => {
        // Count features per route to find the best page
        const routeCounts: Record<string, number> = {}
        for (const f of epic.features) {
          const slug = f.slug || f.feature_id
          const route = featureRoutes[slug] || f.route || fallback
          routeCounts[route] = (routeCounts[route] || 0) + 1
        }
        // Pick route with most features, fallback to manifest or epic plan
        let bestRoute = epic.primary_route || fallback
        let bestCount = 0
        for (const [route, count] of Object.entries(routeCounts)) {
          if (count > bestCount) {
            bestCount = count
            bestRoute = route
          }
        }
        // If no features resolved, use manifest route
        if (bestCount === 0 && routeManifest?.epic_routes) {
          bestRoute = routeManifest.epic_routes[String(i)] || bestRoute
        }
        let safeRoute = routeRemaps[bestRoute] ?? bestRoute
        // Validate route exists in prototype — fall back to /dashboard if not
        if (validRoutes.size > 0 && !validRoutes.has(safeRoute)) {
          safeRoute = fallback
        }
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

  // Build pipeline: start build → poll for status → surface deploy URL
  const handleStartBuild = async (selection: DesignSelection) => {
    setBuildError(null)
    try {
      const result = await startBuild(projectId, { designSelection: selection })
      setActiveBuildId(result.build_id)
      setBuildStatus({ build_id: result.build_id, status: 'pending', streams_total: 0, streams_completed: 0, tasks_total: 0, tasks_completed: 0, total_tokens_used: 0, total_cost_usd: 0, deploy_url: null, github_repo_url: null, errors: [], build_log: [] })
      setShowDesignModal(false)
    } catch (error) {
      console.error('Failed to start build:', error)
      setBuildError(error instanceof Error ? error.message : 'Failed to start build')
    }
  }

  // Poll build status
  useEffect(() => {
    if (!activeBuildId) return
    const terminal = ['completed', 'failed']
    if (buildStatus && terminal.includes(buildStatus.status)) return

    const poll = async () => {
      try {
        const status = await getBuildStatus(projectId, activeBuildId)
        setBuildStatus(status)

        if (status.status === 'completed' && status.deploy_url) {
          onPrototypeBuilt?.(status.deploy_url)
          setActiveBuildId(null)
        } else if (status.status === 'failed') {
          setBuildError(status.errors?.[0] || 'Build failed')
        }
      } catch {
        // Non-fatal polling error
      }
    }

    poll()
    buildPollRef.current = setInterval(poll, 3000)
    return () => {
      if (buildPollRef.current) clearInterval(buildPollRef.current)
    }
  }, [activeBuildId, buildStatus?.status, projectId, onPrototypeBuilt])

  const handleCancelBuild = async () => {
    if (!activeBuildId) return
    try {
      await cancelBuild(projectId, activeBuildId)
      setBuildStatus((prev) => prev ? { ...prev, status: 'failed' } : prev)
      setBuildError('Build cancelled')
    } catch {
      // Non-fatal
    }
  }

  const handleRetryBuild = () => {
    setActiveBuildId(null)
    setBuildStatus(null)
    setBuildError(null)
    setShowDesignModal(true)
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
        // Use slug (kebab-case) as the bridge ID — matches data-aios-feature in DOM
        const f = features[0]
        const bridgeId = f.slug || f.feature_id
        win.postMessage(
          {
            type: 'aios:highlight-feature',
            featureId: bridgeId,
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
        // Use slug (kebab-case) as the bridge ID — matches data-aios-feature in DOM
        win.postMessage(
          {
            type: 'aios:show-radar',
            features: features.map((f: any) => ({
              featureId: f.slug || f.feature_id,
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
  }, [bridgeReady, activeCardIndex, isReviewActive, getCardFeatures, collaborationWidth])

  // Handle feature navigation from side panel → navigate iframe + highlight
  useEffect(() => {
    if (!pendingFeatureNav || !bridgeReady || !iframeRef.current?.contentWindow) return
    const win = iframeRef.current.contentWindow
    const { slug, route } = pendingFeatureNav

    // Validate route exists in prototype — fall back to current page if not
    const knownRoutes = new Set<string>()
    if (routeManifest) {
      for (const r of Object.values(routeManifest.epic_routes || {})) knownRoutes.add(r as string)
      for (const r of Object.values(routeManifest.feature_routes || {})) knownRoutes.add(r as string)
    }
    const safeRoute = route && (knownRoutes.size === 0 || knownRoutes.has(route)) ? route : null

    // Navigate to the feature's route if different from current
    if (safeRoute) {
      win.postMessage({ type: 'aios:navigate', path: safeRoute }, '*')
    }

    // After navigation settles, highlight the specific feature
    const timer = setTimeout(() => {
      win.postMessage({
        type: 'aios:highlight-feature',
        featureId: slug,
      }, '*')
    }, safeRoute ? 600 : 100)

    onFeatureNavConsumed?.()
    return () => clearTimeout(timer)
  }, [pendingFeatureNav, bridgeReady, onFeatureNavConsumed, routeManifest])

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
                Internal Review
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

              {/* Review toggle — Start or Resume */}
              {!isReviewActive && (
                <button
                  onClick={onStartReview}
                  className="flex items-center gap-1.5 px-3 py-1 text-xs font-medium text-brand-primary bg-brand-primary-light hover:bg-brand-primary-light rounded-lg transition-colors"
                >
                  <Layers className="w-3.5 h-3.5" />
                  {verdictMap && verdictMap.size > 0 ? 'Resume Review' : 'Start Review'}
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
          verdictMap={verdictMap}
          onReviewComplete={onReviewComplete}
          reviewState={reviewState}
          initialIndex={
            verdictMap && verdictMap.size > 0
              ? Math.max(0, mappedEpicPlan.vision_epics.findIndex(
                  (_, i) => !verdictMap.has(`vision:${i}`)
                ))
              : undefined
          }
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
        {prototypeUrl && !isBuilding ? (
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
        ) : isBuilding && buildStatus ? (
          /* ── Cinematic Build Experience ── */
          <BuildCinematicView
            status={buildStatus.status}
            buildLog={buildStatus.build_log ?? []}
            onCancel={handleCancelBuild}
          />
        ) : buildError ? (
          /* ── Build Failed View ── */
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md px-6">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-50 flex items-center justify-center">
                <XCircle className="w-8 h-8 text-red-400" />
              </div>
              <h3 className="text-base font-semibold text-[#37352f] mb-2">Build Failed</h3>
              <p className="text-sm text-text-placeholder mb-5 break-words">
                {buildError}
              </p>
              <button
                onClick={handleRetryBuild}
                className="px-5 py-2.5 bg-brand-primary text-white text-sm font-medium rounded-lg hover:bg-[#25785A] transition-colors inline-flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                Try Again
              </button>
            </div>
          </div>
        ) : (
          /* ── Empty State ── */
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-brand-primary-light flex items-center justify-center">
                <Sparkles className="w-8 h-8 text-brand-primary" />
              </div>
              <h3 className="text-base font-semibold text-[#37352f] mb-2">Build a Prototype</h3>
              <p className="text-sm text-text-placeholder mb-5">
                Generate a live, interactive prototype from your discovery data — deployed in under a minute.
              </p>
              <button
                onClick={() => setShowDesignModal(true)}
                className="px-5 py-2.5 bg-brand-primary text-white text-sm font-medium rounded-lg hover:bg-[#25785A] transition-colors inline-flex items-center gap-2"
              >
                <Sparkles className="w-4 h-4" />
                Generate Prototype
              </button>
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
        onGenerate={handleStartBuild}
        projectId={projectId}
        isGenerating={isBuilding}
      />
    </div>
  )
}

export default BuildPhaseView
