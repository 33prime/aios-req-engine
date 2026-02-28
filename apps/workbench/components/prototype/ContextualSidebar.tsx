'use client'

import { useState, useMemo } from 'react'
import type { FeatureOverlay, TourStep, FeatureVerdict } from '@/types/prototype'
import type { EpicOverlayPlan, EpicTourPhase } from '@/types/epic-overlay'
import FeatureVerdictCard from './FeatureVerdictCard'
import EpicCard from './EpicCard'
import AIFlowCardComponent from './AIFlowCardComponent'
import HorizonCardComponent from './HorizonCardComponent'
import DiscoveryThreadCard from './DiscoveryThreadCard'

interface ContextualSidebarProps {
  overlays: FeatureOverlay[]
  currentStep: TourStep | null
  visibleFeatures: string[]
  sessionId: string
  prototypeId: string
  onAnswerSubmit: (questionId: string, answer: string) => void
  answeredQuestionIds: Set<string>
  onVerdictSubmit?: (overlayId: string, verdict: FeatureVerdict) => void
  // Epic tour mode props
  epicPlan?: EpicOverlayPlan | null
  epicPhase?: EpicTourPhase | null
  epicCardIndex?: number | null
}

/**
 * Contextual sidebar shown during guided tour.
 * Displays the current tour step's verdict card, or a review scorecard when no step is active.
 */
export default function ContextualSidebar({
  overlays,
  currentStep,
  visibleFeatures,
  sessionId,
  prototypeId,
  onAnswerSubmit,
  answeredQuestionIds,
  onVerdictSubmit,
  epicPlan,
  epicPhase,
  epicCardIndex,
}: ContextualSidebarProps) {
  const [showScorecard, setShowScorecard] = useState(false)

  // Get the overlay for the current step
  const currentOverlay = currentStep
    ? overlays.find((o) => o.id === currentStep.overlayId)
    : null

  // Get overlays for visible features (fallback when no step active)
  const visibleOverlays = useMemo(() => {
    if (currentStep) return []
    return overlays.filter(
      (o) => o.feature_id && visibleFeatures.includes(o.feature_id)
    )
  }, [currentStep, overlays, visibleFeatures])

  // Verdict counts for progress bar
  const verdictCounts = useMemo(() => {
    let aligned = 0, needsAdj = 0, offTrack = 0, unreviewed = 0
    for (const o of overlays) {
      const v = o.consultant_verdict
      if (v === 'aligned') aligned++
      else if (v === 'needs_adjustment') needsAdj++
      else if (v === 'off_track') offTrack++
      else unreviewed++
    }
    return { aligned, needsAdj, offTrack, unreviewed, total: overlays.length }
  }, [overlays])

  const reviewedCount = verdictCounts.total - verdictCounts.unreviewed

  // Epic tour mode: if we have an epic plan and a card index, show epic content
  const isEpicMode = epicPlan && epicCardIndex != null

  return (
    <div className="w-[380px] flex-shrink-0 bg-white border-l border-border flex flex-col h-full overflow-hidden">
      {/* Epic tour mode — focused on current card only */}
      {isEpicMode && epicPlan && epicPhase && (
        <div className="flex-1 overflow-y-auto p-3 space-y-3 custom-scrollbar">
          {epicPhase === 'vision_journey' && (() => {
            const localIdx = getPhaseLocalIndex(epicPlan, epicPhase, epicCardIndex!)
            const epic = epicPlan.vision_epics[localIdx]
            return epic ? <EpicCard epic={epic} isActive /> : null
          })()}

          {epicPhase === 'ai_deep_dive' && (() => {
            const localIdx = getPhaseLocalIndex(epicPlan, epicPhase, epicCardIndex!)
            const card = epicPlan.ai_flow_cards[localIdx]
            return card ? <AIFlowCardComponent card={card} isActive /> : null
          })()}

          {epicPhase === 'horizons' && (() => {
            const localIdx = getPhaseLocalIndex(epicPlan, epicPhase, epicCardIndex!)
            const card = epicPlan.horizon_cards[localIdx]
            return card ? <HorizonCardComponent card={card} isActive /> : null
          })()}

          {epicPhase === 'discovery' && (() => {
            const localIdx = getPhaseLocalIndex(epicPlan, epicPhase, epicCardIndex!)
            const thread = epicPlan.discovery_threads.slice(0, 3)[localIdx]
            return thread ? <DiscoveryThreadCard thread={thread} isActive /> : null
          })()}
        </div>
      )}

      {/* Current step: verdict card (feature mode) */}
      {!isEpicMode && currentStep && currentOverlay && (
        <div className="flex-1 overflow-y-auto p-3 custom-scrollbar">
          <FeatureVerdictCard
            overlay={currentOverlay}
            prototypeId={prototypeId}
            source="consultant"
            onVerdictSubmit={onVerdictSubmit}
          />

          {/* Spec vs Code context below the card */}
          {currentOverlay.overlay_content && (
            <div className="mt-3 space-y-3">
              {currentOverlay.overlay_content.overview?.spec_summary && (
                <div className="rounded-xl border border-border p-3">
                  <h4 className="text-[11px] font-semibold text-[#666666] uppercase tracking-wide mb-1">
                    What AIOS says
                  </h4>
                  <p className="text-xs text-text-body leading-relaxed">
                    {currentOverlay.overlay_content.overview.spec_summary}
                  </p>
                </div>
              )}
              {currentOverlay.overlay_content.overview?.delta &&
                currentOverlay.overlay_content.overview.delta.length > 0 && (
                <div className="rounded-xl border border-border p-3">
                  <h4 className="text-[11px] font-semibold text-[#666666] uppercase tracking-wide mb-1">
                    Spec vs Code Gaps
                  </h4>
                  <ul className="space-y-0.5">
                    {currentOverlay.overlay_content.overview.delta.map((d, i) => (
                      <li key={i} className="text-xs text-text-body flex items-start gap-1.5">
                        <span className="text-text-placeholder mt-0.5">&bull;</span>{d}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {currentOverlay.overlay_content.impact?.downstream_risk && (
                <div className="rounded-xl border border-border p-3">
                  <h4 className="text-[11px] font-semibold text-[#666666] uppercase tracking-wide mb-1">
                    Downstream Risk
                  </h4>
                  <p className="text-xs text-text-body">
                    {currentOverlay.overlay_content.impact.downstream_risk}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* No step active: show visible features or scorecard (feature mode only) */}
      {!isEpicMode && !currentStep && (
        <>
          <div className="px-4 py-3 border-b border-border">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-text-body">
                {showScorecard ? 'Review Scorecard' : 'Features'}
              </h3>
              <button
                onClick={() => setShowScorecard(!showScorecard)}
                className="text-xs text-brand-primary hover:text-[#25785A] transition-colors"
              >
                {showScorecard ? 'Show Contextual' : 'View Scorecard'}
              </button>
            </div>
            {!showScorecard && visibleOverlays.length > 0 && (
              <p className="text-xs text-text-placeholder mt-1">
                {visibleOverlays.length} feature{visibleOverlays.length !== 1 ? 's' : ''} on this page
              </p>
            )}
          </div>

          <div className="flex-1 overflow-y-auto p-3 space-y-3 custom-scrollbar">
            {showScorecard ? (
              // Scorecard view: compact list of all features with verdict dots
              <div className="space-y-1">
                {overlays.map((o) => {
                  const name = o.overlay_content?.feature_name || o.handoff_feature_name || 'Unknown'
                  const v = o.consultant_verdict
                  return (
                    <div
                      key={o.id}
                      className="flex items-center gap-2.5 px-3 py-2 rounded-xl hover:bg-[#F4F4F4] transition-colors"
                    >
                      <span
                        className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${
                          v === 'aligned' ? 'bg-brand-primary' :
                          v === 'needs_adjustment' ? 'bg-amber-400' :
                          v === 'off_track' ? 'bg-red-400' :
                          'bg-gray-300'
                        }`}
                      />
                      <span className="text-sm text-text-body truncate flex-1">{name}</span>
                      <span className="text-[10px] text-text-placeholder">
                        {Math.round((o.confidence ?? 0) * 100)}%
                      </span>
                    </div>
                  )
                })}
              </div>
            ) : visibleOverlays.length > 0 ? (
              // Contextual view: verdict cards for visible features
              visibleOverlays.map((o) => (
                <FeatureVerdictCard
                  key={o.id}
                  overlay={o}
                  prototypeId={prototypeId}
                  source="consultant"
                  onVerdictSubmit={onVerdictSubmit}
                />
              ))
            ) : (
              <p className="text-sm text-text-placeholder text-center py-8">
                Navigate the prototype or start the guided tour to see features.
              </p>
            )}
          </div>
        </>
      )}

      {/* Progress footer */}
      <div className="px-4 py-3 border-t border-border">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-text-placeholder">
            {reviewedCount}/{verdictCounts.total} features reviewed
          </span>
        </div>
        <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden flex">
          {verdictCounts.aligned > 0 && (
            <div
              className="h-full bg-brand-primary transition-all duration-300"
              style={{ width: `${(verdictCounts.aligned / verdictCounts.total) * 100}%` }}
            />
          )}
          {verdictCounts.needsAdj > 0 && (
            <div
              className="h-full bg-amber-400 transition-all duration-300"
              style={{ width: `${(verdictCounts.needsAdj / verdictCounts.total) * 100}%` }}
            />
          )}
          {verdictCounts.offTrack > 0 && (
            <div
              className="h-full bg-red-400 transition-all duration-300"
              style={{ width: `${(verdictCounts.offTrack / verdictCounts.total) * 100}%` }}
            />
          )}
        </div>
      </div>
    </div>
  )
}

/**
 * Converts a global card index (across all phases) to the local index within
 * the current phase. Mirrors the logic in ReviewInfoPanel.
 */
function getPhaseLocalIndex(
  plan: EpicOverlayPlan,
  phase: EpicTourPhase,
  globalIndex: number
): number {
  let offset = 0
  const phaseSizes: [EpicTourPhase, number][] = [
    ['vision_journey', plan.vision_epics.length],
    ['ai_deep_dive', plan.ai_flow_cards.length],
    ['horizons', plan.horizon_cards.length],
    ['discovery', Math.min(plan.discovery_threads.length, 3)],
  ]
  for (const [p, size] of phaseSizes) {
    if (p === phase) {
      return globalIndex - offset
    }
    offset += size
  }
  return 0
}
