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

import { useState, useRef, useEffect, useCallback } from 'react'
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
import type { EpicOverlayPlan, EpicTourPhase } from '@/types/epic-overlay'

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
    if (!isReviewActive || activeCardIndex === null || !iframeRef.current?.contentWindow) return
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
  }, [activeCardIndex, isReviewActive, getCardFeatures])

  // Track card changes from tour controller
  const handleCardChange = useCallback(
    (cardIndex: number | null) => {
      setActiveCardIndex(cardIndex)
      onEpicCardChange?.(cardIndex)
    },
    [onEpicCardChange]
  )

  // Tour route change — navigate iframe by swapping src
  const handleRouteChange = useCallback(
    (route: string | null) => {
      if (!prototypeUrl) return
      if (!route) {
        // No route — stay on current page
        return
      }
      // Build full URL: base + route
      try {
        const base = new URL(prototypeUrl)
        base.pathname = route
        const newSrc = base.toString()
        if (newSrc !== activeIframeSrc) {
          setActiveIframeSrc(newSrc)
        }
      } catch {
        // Invalid URL — ignore
      }
    },
    [prototypeUrl, activeIframeSrc]
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
              {isReviewActive ? (
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
                  className="flex items-center gap-1.5 px-3 py-1 text-xs font-medium text-[#666666] bg-[#F4F4F4] hover:bg-[#EBEBEB] rounded-lg transition-colors disabled:opacity-60"
                >
                  {isEndingReview ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : null}
                  {isEndingReview ? 'Ending...' : 'Prepare for Client'}
                </button>
              ) : (
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
      {isReviewActive && session && epicPlan && epicPlan.vision_epics.length > 0 && (
        <EpicTourController
          epicPlan={epicPlan}
          onPhaseChange={onEpicPhaseChange ?? (() => {})}
          onEpicChange={onEpicIndexChange ?? (() => {})}
          onCardChange={handleCardChange}
          onRouteChange={handleRouteChange}
          autoStart
          confirmedSet={confirmedSet}
        />
      )}

      {/* Prototype preview — single iframe, src changes when tour navigates */}
      <div className="flex-1 bg-gray-100 relative min-h-0">
        {prototypeUrl ? (
          <iframe
            ref={iframeRef}
            key={iframeKey}
            src={isReviewActive ? activeIframeSrc : prototypeUrl}
            className="w-full h-full border-0"
            title="Prototype Preview"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
          />
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
