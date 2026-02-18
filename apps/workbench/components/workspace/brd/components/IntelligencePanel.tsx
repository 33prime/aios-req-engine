'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  Sparkles,
  Send,
  ChevronDown,
  ChevronRight,
  Users,
  Loader2,
  Check,
  ArrowRight,
  Zap,
} from 'lucide-react'
import type { IntelligenceAction, IntelligenceActionsResult, ActionQuestion } from '@/lib/api'
import { getIntelligenceActions, answerActionQuestion } from '@/lib/api'
import {
  GAP_TYPE_ICONS,
  GAP_DOMAIN_COLORS,
  GAP_DOMAIN_LABELS,
  URGENCY_COLORS,
} from '@/lib/action-constants'

interface IntelligencePanelProps {
  projectId: string
  /** Callback when an action triggers navigation (scroll to BRD section) */
  onNavigate?: (entityType: string, entityId: string | null) => void
  /** Callback when answer cascade completes — parent should reload BRD data */
  onCascade?: () => void
}

export function IntelligencePanel({
  projectId,
  onNavigate,
  onCascade,
}: IntelligencePanelProps) {
  const [result, setResult] = useState<IntelligenceActionsResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Track which action card is expanded (show 3, expand 1 at a time)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  // Inline answer state
  const [answerInputs, setAnswerInputs] = useState<Record<string, string>>({})
  const [submitting, setSubmitting] = useState<Record<string, boolean>>({})
  const [cascadeResults, setCascadeResults] = useState<Record<string, string>>({})

  // Fading resolved actions
  const [fadingIds, setFadingIds] = useState<Set<string>>(new Set())

  const loadActions = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await getIntelligenceActions(projectId, 5)
      setResult(data)
    } catch (err) {
      setError('Failed to load intelligence')
      console.error('Intelligence load error:', err)
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    loadActions()
  }, [loadActions])

  // Handle inline answer submission
  const handleAnswer = useCallback(async (actionId: string, questionIndex: number) => {
    const text = answerInputs[actionId]?.trim()
    if (!text) return

    setSubmitting(s => ({ ...s, [actionId]: true }))
    try {
      const res = await answerActionQuestion(projectId, actionId, text, questionIndex)
      setCascadeResults(prev => ({ ...prev, [actionId]: res.summary }))

      // Fade the resolved action
      setFadingIds(prev => new Set(prev).add(actionId))

      // Clear input
      setAnswerInputs(prev => {
        const next = { ...prev }
        delete next[actionId]
        return next
      })

      // After fade animation, reload actions to get next from buffer
      setTimeout(() => {
        setFadingIds(prev => {
          const next = new Set(prev)
          next.delete(actionId)
          return next
        })
        loadActions()
        onCascade?.()
      }, 1200)
    } catch (err) {
      console.error('Answer submission failed:', err)
    } finally {
      setSubmitting(s => ({ ...s, [actionId]: false }))
    }
  }, [projectId, answerInputs, loadActions, onCascade])

  // Show 3 actions to user
  const visibleActions = result?.actions?.slice(0, 3) ?? []

  if (loading && !result) {
    return (
      <div className="flex flex-col h-full">
        <PanelHeader phase={null} progress={0} skeletonCount={0} />
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="flex items-center gap-2 text-[12px] text-[#999999]">
            <Loader2 className="w-4 h-4 animate-spin" />
            Analyzing project...
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col h-full">
        <PanelHeader phase={null} progress={0} skeletonCount={0} />
        <div className="flex-1 flex items-center justify-center p-6">
          <p className="text-[12px] text-[#999999]">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full bg-white border-r border-[#E5E5E5]">
      <PanelHeader
        phase={result?.phase ?? null}
        progress={result?.phase_progress ?? 0}
        skeletonCount={result?.skeleton_count ?? 0}
        cached={result?.narrative_cached}
        onRefresh={loadActions}
        loading={loading}
      />

      {/* Action cards */}
      <div className="flex-1 overflow-y-auto">
        {visibleActions.length === 0 ? (
          <div className="p-6 text-center">
            <Sparkles className="w-8 h-8 text-[#3FAF7A] mx-auto mb-3 opacity-50" />
            <p className="text-[13px] font-medium text-[#333333]">Looking good</p>
            <p className="text-[12px] text-[#999999] mt-1">
              No gaps detected right now
            </p>
          </div>
        ) : (
          <div className="p-3 space-y-3">
            {visibleActions.map((action, idx) => (
              <ActionCard
                key={action.action_id}
                action={action}
                index={idx}
                isExpanded={expandedId === action.action_id}
                onToggle={() =>
                  setExpandedId(
                    expandedId === action.action_id ? null : action.action_id
                  )
                }
                answerText={answerInputs[action.action_id] ?? ''}
                onAnswerChange={(text) =>
                  setAnswerInputs(prev => ({ ...prev, [action.action_id]: text }))
                }
                onSubmitAnswer={(qIdx) => handleAnswer(action.action_id, qIdx)}
                isSubmitting={submitting[action.action_id] ?? false}
                cascadeResult={cascadeResults[action.action_id]}
                isFading={fadingIds.has(action.action_id)}
                onNavigate={onNavigate}
              />
            ))}
          </div>
        )}

        {/* Open questions summary */}
        {result?.open_questions && result.open_questions.length > 0 && (
          <div className="px-3 pb-3">
            <OpenQuestionsSummary
              questions={result.open_questions}
              onNavigate={() => onNavigate?.('open_question', null)}
            />
          </div>
        )}
      </div>
    </div>
  )
}

// =============================================================================
// Panel Header
// =============================================================================

function PanelHeader({
  phase,
  progress,
  skeletonCount,
  cached,
  onRefresh,
  loading,
}: {
  phase: string | null
  progress: number
  skeletonCount: number
  cached?: boolean
  onRefresh?: () => void
  loading?: boolean
}) {
  const phaseLabel = phase
    ? phase.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())
    : '...'
  const progressPct = Math.round(progress * 100)

  return (
    <div className="px-4 py-3 border-b border-[#E5E5E5] bg-[#0A1E2F] flex-shrink-0">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-[#3FAF7A]" />
          <h2 className="text-[13px] font-semibold text-white">Intelligence</h2>
        </div>
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={loading}
            className="p-1 rounded-md hover:bg-white/10 transition-colors disabled:opacity-40"
            title="Refresh actions"
          >
            <Loader2
              className={`w-3.5 h-3.5 text-white/60 ${loading ? 'animate-spin' : ''}`}
            />
          </button>
        )}
      </div>
      <div className="mt-2 flex items-center gap-3">
        <span className="text-[11px] text-white/60">{phaseLabel}</span>
        <div className="flex-1 h-1 bg-white/10 rounded-full overflow-hidden">
          <div
            className="h-full bg-[#3FAF7A] rounded-full transition-all duration-500"
            style={{ width: `${progressPct}%` }}
          />
        </div>
        <span className="text-[11px] text-white/60">{progressPct}%</span>
      </div>
      {skeletonCount > 0 && (
        <p className="text-[10px] text-white/40 mt-1">
          {skeletonCount} gaps detected
        </p>
      )}
    </div>
  )
}

// =============================================================================
// Action Card
// =============================================================================

function ActionCard({
  action,
  index,
  isExpanded,
  onToggle,
  answerText,
  onAnswerChange,
  onSubmitAnswer,
  isSubmitting,
  cascadeResult,
  isFading,
  onNavigate,
}: {
  action: IntelligenceAction
  index: number
  isExpanded: boolean
  onToggle: () => void
  answerText: string
  onAnswerChange: (text: string) => void
  onSubmitAnswer: (questionIndex: number) => void
  isSubmitting: boolean
  cascadeResult?: string
  isFading: boolean
  onNavigate?: (entityType: string, entityId: string | null) => void
}) {
  const Icon = GAP_TYPE_ICONS[action.gap_type] || Sparkles
  const urgencyColor = URGENCY_COLORS[action.urgency] || URGENCY_COLORS.normal
  const domainColor = action.gap_domain
    ? GAP_DOMAIN_COLORS[action.gap_domain] || '#999999'
    : '#999999'
  const domainLabel = action.gap_domain
    ? GAP_DOMAIN_LABELS[action.gap_domain] || action.gap_domain
    : ''

  return (
    <div
      className={`
        border border-[#E5E5E5] rounded-xl bg-white overflow-hidden
        transition-all duration-500
        ${isFading ? 'opacity-0 scale-95 -translate-y-2' : 'opacity-100'}
        ${isExpanded ? 'shadow-md' : 'shadow-sm hover:shadow-md'}
      `}
    >
      {/* Card header — always visible */}
      <button
        onClick={onToggle}
        className="w-full px-4 py-3 flex items-start gap-3 text-left hover:bg-[#FAFAFA] transition-colors"
      >
        {/* Number badge */}
        <span
          className="flex items-center justify-center w-5 h-5 rounded-full text-[11px] font-semibold flex-shrink-0 mt-0.5"
          style={{
            backgroundColor: urgencyColor + '18',
            color: urgencyColor,
          }}
        >
          {index + 1}
        </span>

        <div className="flex-1 min-w-0">
          {/* Domain + urgency row */}
          <div className="flex items-center gap-2 mb-1">
            <Icon className="w-3.5 h-3.5 flex-shrink-0" style={{ color: domainColor }} />
            {domainLabel && (
              <span
                className="text-[10px] font-medium uppercase tracking-wide"
                style={{ color: domainColor }}
              >
                {domainLabel}
              </span>
            )}
            {(action.urgency === 'critical' || action.urgency === 'high') && (
              <span
                className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                style={{ backgroundColor: urgencyColor }}
              />
            )}
          </div>

          {/* Narrative */}
          <p className="text-[13px] text-[#333333] leading-relaxed">
            {isExpanded
              ? action.narrative
              : action.narrative.length > 120
                ? action.narrative.slice(0, 120) + '...'
                : action.narrative}
          </p>
        </div>

        {/* Expand chevron */}
        {isExpanded ? (
          <ChevronDown className="w-4 h-4 text-[#999999] flex-shrink-0 mt-1" />
        ) : (
          <ChevronRight className="w-4 h-4 text-[#999999] flex-shrink-0 mt-1" />
        )}
      </button>

      {/* Expanded content */}
      {isExpanded && (
        <div className="px-4 pb-4 border-t border-[#F0F0F0]">
          {/* Unlocks */}
          {action.unlocks && (
            <div className="mt-3 flex items-start gap-2">
              <Zap className="w-3 h-3 text-[#3FAF7A] flex-shrink-0 mt-0.5" />
              <p className="text-[12px] text-[#25785A]">{action.unlocks}</p>
            </div>
          )}

          {/* Known contacts */}
          {action.known_contacts.length > 0 && (
            <div className="mt-2 flex items-center gap-1.5 flex-wrap">
              <Users className="w-3 h-3 text-[#999999]" />
              {action.known_contacts.slice(0, 3).map((name, i) => (
                <span
                  key={i}
                  className="inline-flex items-center px-2 py-0.5 text-[10px] font-medium bg-[#E8F5E9] text-[#25785A] rounded-full"
                >
                  {name}
                </span>
              ))}
            </div>
          )}

          {/* Entity link */}
          {action.primary_entity_type !== 'project' &&
            action.primary_entity_type !== 'open_question' && (
              <button
                onClick={() =>
                  onNavigate?.(action.primary_entity_type, action.primary_entity_id)
                }
                className="mt-2 inline-flex items-center gap-1 text-[11px] text-[#3FAF7A] hover:underline"
              >
                <ArrowRight className="w-3 h-3" />
                View {action.primary_entity_name}
              </button>
            )}

          {/* Questions */}
          {action.questions.length > 0 && (
            <div className="mt-3 space-y-2">
              {action.questions.map((q, qIdx) => (
                <QuestionBlock
                  key={qIdx}
                  question={q}
                  questionIndex={qIdx}
                  answerText={answerText}
                  onAnswerChange={onAnswerChange}
                  onSubmit={() => onSubmitAnswer(qIdx)}
                  isSubmitting={isSubmitting}
                />
              ))}
            </div>
          )}

          {/* Cascade result */}
          {cascadeResult && (
            <div className="mt-3 flex items-start gap-2 px-3 py-2 bg-[#E8F5E9] rounded-lg">
              <Check className="w-3.5 h-3.5 text-[#25785A] flex-shrink-0 mt-0.5" />
              <p className="text-[12px] text-[#25785A]">{cascadeResult}</p>
            </div>
          )}

          {/* No questions — show answer prompt if answerable */}
          {action.questions.length === 0 && !cascadeResult && (
            <div className="mt-3">
              <InlineAnswerInput
                placeholder="Type your answer..."
                value={answerText}
                onChange={onAnswerChange}
                onSubmit={() => onSubmitAnswer(0)}
                isSubmitting={isSubmitting}
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// =============================================================================
// Question Block
// =============================================================================

function QuestionBlock({
  question,
  questionIndex,
  answerText,
  onAnswerChange,
  onSubmit,
  isSubmitting,
}: {
  question: ActionQuestion
  questionIndex: number
  answerText: string
  onAnswerChange: (text: string) => void
  onSubmit: () => void
  isSubmitting: boolean
}) {
  const isClient = question.target === 'client'

  return (
    <div className="rounded-lg border border-[#E5E5E5] bg-[#FAFAFA] p-3">
      <p className="text-[12px] font-medium text-[#333333]">{question.question}</p>

      {/* Routing indicator */}
      <div className="flex items-center gap-2 mt-1.5">
        {isClient && question.suggested_contact ? (
          <span className="inline-flex items-center gap-1 text-[10px] text-[#666666]">
            <Users className="w-2.5 h-2.5" />
            Ask {question.suggested_contact}
          </span>
        ) : isClient ? (
          <span className="inline-flex items-center gap-1 text-[10px] text-[#666666]">
            <Users className="w-2.5 h-2.5" />
            Needs client input
          </span>
        ) : null}
        {question.unlocks && (
          <span className="text-[10px] text-[#999999]">
            Unlocks: {question.unlocks}
          </span>
        )}
      </div>

      {/* Answer input */}
      <div className="mt-2">
        <InlineAnswerInput
          placeholder={
            isClient
              ? 'Answer directly, or we\'ll route this to the right person...'
              : 'Type your answer...'
          }
          value={answerText}
          onChange={onAnswerChange}
          onSubmit={onSubmit}
          isSubmitting={isSubmitting}
        />
      </div>
    </div>
  )
}

// =============================================================================
// Inline Answer Input
// =============================================================================

function InlineAnswerInput({
  placeholder,
  value,
  onChange,
  onSubmit,
  isSubmitting,
}: {
  placeholder: string
  value: string
  onChange: (text: string) => void
  onSubmit: () => void
  isSubmitting: boolean
}) {
  return (
    <div className="flex items-center gap-2">
      <input
        type="text"
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="flex-1 px-3 py-1.5 text-[12px] border border-[#E5E5E5] rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-[#3FAF7A] placeholder:text-[#CCCCCC]"
        onKeyDown={e => {
          if (e.key === 'Enter' && value.trim()) onSubmit()
        }}
        disabled={isSubmitting}
      />
      <button
        onClick={onSubmit}
        disabled={isSubmitting || !value.trim()}
        className="p-1.5 text-white bg-[#3FAF7A] hover:bg-[#25785A] rounded-lg disabled:opacity-40 transition-colors"
        title="Submit answer"
      >
        {isSubmitting ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
        ) : (
          <Send className="w-3.5 h-3.5" />
        )}
      </button>
    </div>
  )
}

// =============================================================================
// Open Questions Summary (bottom of panel)
// =============================================================================

function OpenQuestionsSummary({
  questions,
  onNavigate,
}: {
  questions: Array<{ id: string; question: string; priority: string; category: string }>
  onNavigate: () => void
}) {
  const critCount = questions.filter(q => q.priority === 'critical').length
  const highCount = questions.filter(q => q.priority === 'high').length

  return (
    <div className="border border-[#E5E5E5] rounded-xl bg-[#FAFAFA] p-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-medium text-[#666666]">
            {questions.length} open question{questions.length !== 1 ? 's' : ''}
          </span>
          {critCount > 0 && (
            <span className="inline-flex items-center px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-[#FEE2E2] text-[#991B1B]">
              {critCount} critical
            </span>
          )}
          {highCount > 0 && (
            <span className="inline-flex items-center px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-[#F0F0F0] text-[#666666]">
              {highCount} high
            </span>
          )}
        </div>
        <button
          onClick={onNavigate}
          className="text-[11px] font-medium text-[#3FAF7A] hover:underline"
        >
          View all
        </button>
      </div>
    </div>
  )
}
