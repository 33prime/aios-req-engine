'use client'

import { useState, useMemo } from 'react'
import type { FeatureOverlay, TourStep, OverlayQuestion } from '@/types/prototype'

interface ContextualSidebarProps {
  overlays: FeatureOverlay[]
  currentStep: TourStep | null
  visibleFeatures: string[]
  sessionId: string
  onAnswerSubmit: (questionId: string, answer: string) => void
  answeredQuestionIds: Set<string>
}

const PRIORITY_DOT: Record<string, string> = {
  high: 'bg-brand-primary',
  medium: 'bg-brand-accent',
  low: 'bg-gray-300',
}

const STATUS_STYLES: Record<string, string> = {
  understood: 'bg-emerald-100 text-emerald-800',
  partial: 'bg-brand-accent/10 text-brand-primary',
  unknown: 'bg-gray-100 text-gray-600',
}

/**
 * Contextual sidebar shown during guided tour.
 * Displays the current tour step's details and questions with inline answer inputs.
 * Falls back to visible feature questions when tour is not active.
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

  // Get questions to display
  const displayQuestions = useMemo((): { questions: OverlayQuestion[]; featureName: string; source: 'step' | 'visible' }[] => {
    if (currentStep) {
      return [{
        questions: currentStep.questions.sort((a, b) => {
          const order = { high: 0, medium: 1, low: 2 }
          return (order[a.priority] ?? 2) - (order[b.priority] ?? 2)
        }),
        featureName: currentStep.featureName,
        source: 'step',
      }]
    }

    // Fallback: visible features
    return overlays
      .filter((o) => o.feature_id && visibleFeatures.includes(o.feature_id))
      .filter((o) => o.overlay_content && o.overlay_content.questions.length > 0)
      .map((o) => ({
        questions: o.overlay_content!.questions,
        featureName: o.overlay_content!.feature_name,
        source: 'visible' as const,
      }))
  }, [currentStep, overlays, visibleFeatures])

  // Count totals
  const allQuestions = overlays.flatMap((o) => o.overlay_content?.questions || [])
  const totalQuestions = allQuestions.length
  const answeredCount = allQuestions.filter((q) => answeredQuestionIds.has(q.id)).length

  const handleSubmit = (questionId: string) => {
    if (!inputValue.trim()) return
    onAnswerSubmit(questionId, inputValue.trim())
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
          <h3 className="text-sm font-semibold text-ui-headingDark">Questions</h3>
          <p className="text-xs text-ui-supportText mt-1">
            {visibleFeatures.length > 0
              ? `Showing questions for ${visibleFeatures.length} visible features`
              : 'Navigate or start the tour to see contextual questions'}
          </p>
        </div>
      )}

      {/* Questions list */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3 custom-scrollbar">
        {displayQuestions.map(({ questions, featureName, source }, groupIdx) => (
          <div key={groupIdx}>
            {source === 'visible' && (
              <h4 className="text-xs font-semibold text-ui-headingDark uppercase tracking-wide mb-2">
                {featureName}
              </h4>
            )}
            <div className="space-y-2">
              {questions.map((q) => {
                const isAnswered = answeredQuestionIds.has(q.id) || !!q.answer
                const isEditing = activeInputId === q.id

                return (
                  <div
                    key={q.id}
                    className={`rounded-lg border p-3 transition-colors ${
                      isAnswered
                        ? 'border-emerald-200 bg-emerald-50/50'
                        : isEditing
                          ? 'border-brand-primary bg-brand-primary/[0.02]'
                          : 'border-ui-cardBorder hover:border-brand-accent'
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      <span
                        className={`mt-1 w-2 h-2 rounded-full flex-shrink-0 ${
                          PRIORITY_DOT[q.priority] || PRIORITY_DOT.low
                        }`}
                      />
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm ${isAnswered ? 'text-ui-supportText' : 'text-ui-bodyText'}`}>
                          {q.question}
                        </p>

                        {isAnswered && (
                          <div className="flex items-start gap-1.5 mt-2">
                            <svg className="w-3.5 h-3.5 text-emerald-600 mt-0.5 flex-shrink-0" viewBox="0 0 16 16" fill="none">
                              <path d="M3 8L6.5 11.5L13 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                            </svg>
                            <span className="text-xs text-emerald-700">
                              {q.answer || 'Answered'}
                            </span>
                          </div>
                        )}

                        {!isAnswered && !isEditing && (
                          <button
                            onClick={() => {
                              setActiveInputId(q.id)
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
                                if (e.key === 'Enter') handleSubmit(q.id)
                                if (e.key === 'Escape') setActiveInputId(null)
                              }}
                              placeholder="Type your answer..."
                              className="flex-1 px-2.5 py-1.5 text-sm border border-ui-cardBorder rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary"
                              autoFocus
                            />
                            <button
                              onClick={() => handleSubmit(q.id)}
                              disabled={!inputValue.trim()}
                              className="px-3 py-1.5 bg-brand-primary text-white text-xs font-medium rounded-lg hover:bg-[#033344] disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              Save
                            </button>
                          </div>
                        )}
                      </div>
                      <span className="text-badge text-ui-supportText flex-shrink-0 uppercase">
                        {q.priority[0]}
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        ))}

        {/* Metadata fallback for steps with 0 questions */}
        {currentStep && displayQuestions.length > 0 && displayQuestions[0].questions.length === 0 && currentContent && (
          <div className="space-y-3">
            {currentContent.triggers.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-ui-headingDark uppercase tracking-wide mb-1">Triggers</h4>
                <ul className="space-y-0.5">
                  {currentContent.triggers.map((t, i) => (
                    <li key={i} className="text-sm text-ui-bodyText flex items-start gap-1.5">
                      <span className="text-ui-supportText mt-1">&bull;</span>{t}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {currentContent.business_rules.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-ui-headingDark uppercase tracking-wide mb-1">Business Rules</h4>
                <ul className="space-y-0.5">
                  {currentContent.business_rules.map((br, i) => (
                    <li key={i} className="text-sm text-ui-bodyText">{br.rule}</li>
                  ))}
                </ul>
              </div>
            )}
            <p className="text-xs text-ui-supportText italic">No questions for this feature.</p>
          </div>
        )}

        {displayQuestions.length === 0 && !currentStep && (
          <p className="text-sm text-ui-supportText text-center py-8">
            No questions to display. Navigate the prototype or start the guided tour.
          </p>
        )}
      </div>

      {/* Progress footer */}
      <div className="px-4 py-3 border-t border-ui-cardBorder">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-ui-supportText">
            {answeredCount}/{totalQuestions} questions answered
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
            style={{ width: totalQuestions > 0 ? `${(answeredCount / totalQuestions) * 100}%` : '0%' }}
          />
        </div>
      </div>
    </div>
  )
}
