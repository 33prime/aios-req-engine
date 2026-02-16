'use client'

import { useState, useMemo } from 'react'
import type { FeatureOverlay, TourStep, FeatureGap } from '@/types/prototype'

interface ContextualSidebarProps {
  overlays: FeatureOverlay[]
  currentStep: TourStep | null
  visibleFeatures: string[]
  sessionId: string
  onAnswerSubmit: (questionId: string, answer: string) => void
  answeredQuestionIds: Set<string>
}

const AREA_STYLES: Record<string, string> = {
  business_rules: 'bg-ui-background text-ui-bodyText',
  data_handling: 'bg-ui-background text-ui-bodyText',
  user_flow: 'bg-ui-background text-ui-bodyText',
  permissions: 'bg-ui-background text-ui-bodyText',
  integration: 'bg-ui-background text-ui-bodyText',
}

const STATUS_STYLES: Record<string, string> = {
  understood: 'bg-emerald-100 text-emerald-800',
  partial: 'bg-brand-accent/10 text-brand-primary',
  unknown: 'bg-gray-100 text-gray-600',
}

/**
 * Contextual sidebar shown during guided tour.
 * Displays the current tour step's details and gap questions.
 * Falls back to visible feature gaps when tour is not active.
 */
export default function ContextualSidebar({
  overlays,
  currentStep,
  visibleFeatures,
  sessionId,
  onAnswerSubmit,
  answeredQuestionIds,
}: ContextualSidebarProps) {
  const [activeInputId, setActiveInputId] = useState<string | null>(null)
  const [inputValue, setInputValue] = useState('')
  const [showAllOverlays, setShowAllOverlays] = useState(false)

  // Get gaps to display
  const displayGaps = useMemo((): { gaps: FeatureGap[]; featureName: string; source: 'step' | 'visible' }[] => {
    if (currentStep) {
      return [{
        gaps: currentStep.gaps,
        featureName: currentStep.featureName,
        source: 'step',
      }]
    }

    // Fallback: visible features
    return overlays
      .filter((o) => o.feature_id && visibleFeatures.includes(o.feature_id))
      .filter((o) => o.overlay_content?.gaps && o.overlay_content.gaps.length > 0)
      .map((o) => ({
        gaps: o.overlay_content!.gaps,
        featureName: o.overlay_content!.feature_name,
        source: 'visible' as const,
      }))
  }, [currentStep, overlays, visibleFeatures])

  // Count totals
  const allGaps = overlays.flatMap((o) => o.overlay_content?.gaps || [])
  const totalGaps = allGaps.length
  const answeredCount = answeredQuestionIds.size

  const handleSubmit = (gapQuestion: string) => {
    if (!inputValue.trim()) return
    // Use the question text as the ID for gap-based answers
    onAnswerSubmit(gapQuestion, inputValue.trim())
    setInputValue('')
    setActiveInputId(null)
  }

  // Get overlay for current step
  const currentOverlay = currentStep
    ? overlays.find((o) => o.id === currentStep.overlayId)
    : null
  const currentContent = currentOverlay?.overlay_content

  return (
    <div className="w-[380px] flex-shrink-0 bg-white border-l border-ui-cardBorder flex flex-col h-full overflow-hidden">
      {/* Current step card */}
      {currentStep && currentContent && (
        <div className="px-4 py-3 border-b border-ui-cardBorder space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-ui-headingDark truncate">
              {currentStep.featureName}
            </h3>
            <span
              className={`text-badge px-2 py-0.5 rounded-full whitespace-nowrap ${
                STATUS_STYLES[currentOverlay?.status || 'unknown']
              }`}
            >
              {currentOverlay?.status}
            </span>
          </div>

          {currentStep.vpStepLabel && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-ui-supportText">Value Path:</span>
              <span className="text-xs font-medium text-brand-primary">{currentStep.vpStepLabel}</span>
            </div>
          )}

          <div className="flex items-center gap-4 text-xs text-ui-supportText">
            <span>Confidence: {Math.round((currentContent.confidence ?? 0) * 100)}%</span>
            <span
              className={`px-1.5 py-0.5 rounded text-badge ${
                currentStep.featureRole === 'core'
                  ? 'bg-brand-primary/10 text-brand-primary'
                  : currentStep.featureRole === 'supporting'
                    ? 'bg-brand-accent/10 text-brand-accent'
                    : 'bg-gray-100 text-gray-500'
              }`}
            >
              {currentStep.featureRole}
            </span>
          </div>

          {currentStep.description && (
            <p className="text-xs text-ui-bodyText leading-relaxed line-clamp-3">
              {currentStep.description}
            </p>
          )}
        </div>
      )}

      {/* No step active header */}
      {!currentStep && (
        <div className="px-4 py-3 border-b border-ui-cardBorder">
          <h3 className="text-sm font-semibold text-ui-headingDark">Gap Questions</h3>
          <p className="text-xs text-ui-supportText mt-1">
            {visibleFeatures.length > 0
              ? `Showing gaps for ${visibleFeatures.length} visible features`
              : 'Navigate or start the tour to see contextual gaps'}
          </p>
        </div>
      )}

      {/* Gaps list */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3 custom-scrollbar">
        {displayGaps.map(({ gaps, featureName, source }, groupIdx) => (
          <div key={groupIdx}>
            {source === 'visible' && (
              <h4 className="text-xs font-semibold text-ui-headingDark uppercase tracking-wide mb-2">
                {featureName}
              </h4>
            )}
            <div className="space-y-2">
              {gaps.map((gap, i) => {
                const gapKey = `${featureName}-${i}`
                const isAnswered = answeredQuestionIds.has(gapKey)
                const isEditing = activeInputId === gapKey

                return (
                  <div
                    key={gapKey}
                    className={`rounded-lg border p-3 transition-colors ${
                      isAnswered
                        ? 'border-emerald-200 bg-emerald-50/50'
                        : isEditing
                          ? 'border-brand-primary bg-brand-primary/[0.02]'
                          : 'border-ui-cardBorder hover:border-brand-accent'
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      <span className="mt-1 w-2 h-2 rounded-full flex-shrink-0 bg-brand-primary" />
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm ${isAnswered ? 'text-ui-supportText' : 'text-ui-bodyText'}`}>
                          {gap.question}
                        </p>

                        {gap.why_it_matters && (
                          <p className="text-[11px] text-ui-supportText mt-1 italic">{gap.why_it_matters}</p>
                        )}

                        <span className={`text-[10px] mt-1 inline-block px-1.5 py-0.5 rounded ${AREA_STYLES[gap.requirement_area] || AREA_STYLES.business_rules}`}>
                          {gap.requirement_area.replace('_', ' ')}
                        </span>

                        {isAnswered && (
                          <div className="flex items-start gap-1.5 mt-2">
                            <svg className="w-3.5 h-3.5 text-emerald-600 mt-0.5 flex-shrink-0" viewBox="0 0 16 16" fill="none">
                              <path d="M3 8L6.5 11.5L13 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                            </svg>
                            <span className="text-xs text-emerald-700">Answered</span>
                          </div>
                        )}

                        {!isAnswered && !isEditing && (
                          <button
                            onClick={() => {
                              setActiveInputId(gapKey)
                              setInputValue('')
                            }}
                            className="mt-2 text-xs text-brand-primary hover:underline"
                          >
                            Answer this question
                          </button>
                        )}

                        {isEditing && (
                          <div className="mt-2 flex gap-2">
                            <input
                              type="text"
                              value={inputValue}
                              onChange={(e) => setInputValue(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') handleSubmit(gapKey)
                                if (e.key === 'Escape') setActiveInputId(null)
                              }}
                              placeholder="Type your answer..."
                              className="flex-1 px-2.5 py-1.5 text-sm border border-ui-cardBorder rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary"
                              autoFocus
                            />
                            <button
                              onClick={() => handleSubmit(gapKey)}
                              disabled={!inputValue.trim()}
                              className="px-3 py-1.5 bg-brand-primary text-white text-xs font-medium rounded-lg hover:bg-[#033344] disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              Save
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        ))}

        {/* Metadata fallback for steps with 0 gaps */}
        {currentStep && displayGaps.length > 0 && displayGaps[0].gaps.length === 0 && currentContent && (
          <div className="space-y-3">
            {currentContent.overview?.delta && currentContent.overview.delta.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-ui-headingDark uppercase tracking-wide mb-1">Spec vs Code Gaps</h4>
                <ul className="space-y-0.5">
                  {currentContent.overview.delta.map((d, i) => (
                    <li key={i} className="text-sm text-ui-bodyText flex items-start gap-1.5">
                      <span className="text-ui-supportText mt-1">&bull;</span>{d}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {currentContent.impact?.downstream_risk && (
              <div>
                <h4 className="text-xs font-semibold text-ui-headingDark uppercase tracking-wide mb-1">Downstream Risk</h4>
                <p className="text-sm text-ui-bodyText">{currentContent.impact.downstream_risk}</p>
              </div>
            )}
            <p className="text-xs text-ui-supportText italic">No gap questions for this feature.</p>
          </div>
        )}

        {displayGaps.length === 0 && !currentStep && (
          <p className="text-sm text-ui-supportText text-center py-8">
            No gap questions to display. Navigate the prototype or start the guided tour.
          </p>
        )}
      </div>

      {/* Progress footer */}
      <div className="px-4 py-3 border-t border-ui-cardBorder">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-ui-supportText">
            {answeredCount}/{totalGaps} gaps addressed
          </span>
          <button
            onClick={() => setShowAllOverlays(!showAllOverlays)}
            className="text-xs text-brand-primary hover:underline"
          >
            {showAllOverlays ? 'Show Contextual' : 'View All Overlays'}
          </button>
        </div>
        <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-emerald-400 rounded-full transition-all duration-300"
            style={{ width: totalGaps > 0 ? `${(answeredCount / totalGaps) * 100}%` : '0%' }}
          />
        </div>
      </div>
    </div>
  )
}
