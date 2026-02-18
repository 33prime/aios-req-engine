'use client'

import { useState, useCallback } from 'react'
import {
  Sparkles,
  Send,
  Loader2,
  Check,
  ArrowRight,
  Upload,
  MessageSquare,
} from 'lucide-react'
import type { ProjectContextFrame, TerseAction } from '@/lib/api'
import { answerTerseAction } from '@/lib/api'
import { useContextFrame } from '@/lib/hooks/use-api'
import {
  GAP_SOURCE_ICONS,
  GAP_SOURCE_COLORS,
  PHASE_LABELS,
  PHASE_DESCRIPTIONS,
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
  // SWR-cached context frame — shared with WorkspaceLayout badge count
  const { data: frame, error: swrError, isLoading: loading, mutate: revalidate } = useContextFrame(projectId)
  const error = swrError ? 'Failed to load actions' : null

  // Inline answer state
  const [answerInputs, setAnswerInputs] = useState<Record<string, string>>({})
  const [submitting, setSubmitting] = useState<Record<string, boolean>>({})
  const [cascadeResults, setCascadeResults] = useState<Record<string, string>>({})
  const [fadingIds, setFadingIds] = useState<Set<string>>(new Set())

  const loadActions = useCallback(() => {
    revalidate()
  }, [revalidate])

  // Handle inline answer submission
  const handleAnswer = useCallback(async (action: TerseAction) => {
    const text = answerInputs[action.action_id]?.trim()
    if (!text) return

    setSubmitting(s => ({ ...s, [action.action_id]: true }))
    try {
      const res = await answerTerseAction(projectId, action, text)
      setCascadeResults(prev => ({ ...prev, [action.action_id]: res.summary }))

      // Fade the resolved action
      setFadingIds(prev => new Set(prev).add(action.action_id))

      // Clear input
      setAnswerInputs(prev => {
        const next = { ...prev }
        delete next[action.action_id]
        return next
      })

      // After fade, reload
      setTimeout(() => {
        setFadingIds(prev => {
          const next = new Set(prev)
          next.delete(action.action_id)
          return next
        })
        loadActions()
        onCascade?.()
      }, 1200)
    } catch (err) {
      console.error('Answer submission failed:', err)
    } finally {
      setSubmitting(s => ({ ...s, [action.action_id]: false }))
    }
  }, [projectId, answerInputs, loadActions, onCascade])

  if (loading && frame === undefined) {
    return (
      <div className="flex flex-col h-full">
        <PanelHeader phase={null} progress={0} />
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
        <PanelHeader phase={null} progress={0} />
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center">
            <p className="text-[12px] text-[#999999]">{error}</p>
            <button
              onClick={loadActions}
              className="mt-2 text-[11px] font-medium text-[#3FAF7A] hover:underline"
            >
              Try again
            </button>
          </div>
        </div>
      </div>
    )
  }

  const actions = frame?.actions ?? []
  const phase = frame?.phase ?? 'empty'

  return (
    <div className="flex flex-col h-full bg-white border-r border-[#E5E5E5]">
      <PanelHeader
        phase={phase}
        progress={frame?.phase_progress ?? 0}
        onRefresh={loadActions}
        loading={loading}
      />

      {/* Action cards */}
      <div className="flex-1 overflow-y-auto">
        {actions.length === 0 ? (
          <PhaseEmptyState phase={phase} />
        ) : (
          <div className="p-3 space-y-2">
            {actions.map((action) => (
              <TerseActionCard
                key={action.action_id}
                action={action}
                answerText={answerInputs[action.action_id] ?? ''}
                onAnswerChange={(text) =>
                  setAnswerInputs(prev => ({ ...prev, [action.action_id]: text }))
                }
                onSubmitAnswer={() => handleAnswer(action)}
                isSubmitting={submitting[action.action_id] ?? false}
                cascadeResult={cascadeResults[action.action_id]}
                isFading={fadingIds.has(action.action_id)}
                onNavigate={onNavigate}
              />
            ))}
          </div>
        )}

        {/* Open questions summary */}
        {frame?.open_questions && frame.open_questions.length > 0 && (
          <div className="px-3 pb-3">
            <OpenQuestionsSummary
              questions={frame.open_questions}
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
  onRefresh,
  loading,
}: {
  phase: string | null
  progress: number
  onRefresh?: () => void
  loading?: boolean
}) {
  const phaseLabel = phase ? PHASE_LABELS[phase] || phase : '...'
  const progressPct = Math.round(progress * 100)

  return (
    <div className="px-4 py-3 border-b border-[#E5E5E5] bg-[#0A1E2F] flex-shrink-0">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-[#3FAF7A]" />
          <h2 className="text-[13px] font-semibold text-white">Next Actions</h2>
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
    </div>
  )
}

// =============================================================================
// Phase-aware empty state
// =============================================================================

function PhaseEmptyState({ phase }: { phase: string }) {
  const description = PHASE_DESCRIPTIONS[phase] || 'No actions right now'

  return (
    <div className="p-6 text-center">
      <Sparkles className="w-8 h-8 text-[#3FAF7A] mx-auto mb-3 opacity-50" />
      <p className="text-[13px] font-medium text-[#333333]">
        {phase === 'refining' ? 'Looking good' : 'Ready when you are'}
      </p>
      <p className="text-[12px] text-[#999999] mt-1">{description}</p>
    </div>
  )
}

// =============================================================================
// Terse Action Card
// =============================================================================

function TerseActionCard({
  action,
  answerText,
  onAnswerChange,
  onSubmitAnswer,
  isSubmitting,
  cascadeResult,
  isFading,
  onNavigate,
}: {
  action: TerseAction
  answerText: string
  onAnswerChange: (text: string) => void
  onSubmitAnswer: () => void
  isSubmitting: boolean
  cascadeResult?: string
  isFading: boolean
  onNavigate?: (entityType: string, entityId: string | null) => void
}) {
  const sourceColor = GAP_SOURCE_COLORS[action.gap_source] || '#999999'
  const Icon = GAP_SOURCE_ICONS[action.gap_type] || GAP_SOURCE_ICONS[action.gap_source] || Sparkles

  return (
    <div
      className={`
        border border-[#E5E5E5] rounded-xl bg-white overflow-hidden
        transition-all duration-500
        ${isFading ? 'opacity-0 scale-95 -translate-y-2' : 'opacity-100'}
        shadow-sm hover:shadow-md
      `}
    >
      {/* One sentence + CTA */}
      <div className="px-4 py-3">
        <div className="flex items-start gap-3">
          {/* Priority number */}
          <span
            className="flex items-center justify-center w-5 h-5 rounded-full text-[11px] font-semibold flex-shrink-0 mt-0.5"
            style={{
              backgroundColor: sourceColor + '18',
              color: sourceColor,
            }}
          >
            {action.priority}
          </span>

          <div className="flex-1 min-w-0">
            {/* Source badge */}
            <div className="flex items-center gap-1.5 mb-1">
              <Icon className="w-3 h-3 flex-shrink-0" style={{ color: sourceColor }} />
              <span
                className="text-[10px] font-medium uppercase tracking-wide"
                style={{ color: sourceColor }}
              >
                {action.gap_source}
              </span>
            </div>

            {/* The sentence */}
            <p className="text-[13px] text-[#333333] leading-relaxed">
              {action.sentence}
            </p>
          </div>
        </div>

        {/* CTA area */}
        <div className="mt-3 ml-8">
          {/* Cascade result — show instead of CTA */}
          {cascadeResult ? (
            <div className="flex items-start gap-2 px-3 py-2 bg-[#E8F5E9] rounded-lg">
              <Check className="w-3.5 h-3.5 text-[#25785A] flex-shrink-0 mt-0.5" />
              <p className="text-[12px] text-[#25785A]">{cascadeResult}</p>
            </div>
          ) : action.cta_type === 'inline_answer' ? (
            /* Inline answer input */
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={answerText}
                onChange={e => onAnswerChange(e.target.value)}
                placeholder={action.question_placeholder || 'Type your answer...'}
                className="flex-1 px-3 py-1.5 text-[12px] border border-[#E5E5E5] rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-[#3FAF7A] placeholder:text-[#CCCCCC]"
                onKeyDown={e => {
                  if (e.key === 'Enter' && answerText.trim()) onSubmitAnswer()
                }}
                disabled={isSubmitting}
              />
              <button
                onClick={onSubmitAnswer}
                disabled={isSubmitting || !answerText.trim()}
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
          ) : action.cta_type === 'upload_doc' ? (
            /* Upload CTA */
            <button
              onClick={() => onNavigate?.('signal', null)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-[#0A1E2F] bg-[#F0F0F0] hover:bg-[#E5E5E5] rounded-lg transition-colors"
            >
              <Upload className="w-3 h-3" />
              {action.cta_label}
            </button>
          ) : (
            /* Discuss CTA */
            <button
              onClick={() => onNavigate?.('chat', null)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-[#3FAF7A] bg-[#E8F5E9] hover:bg-[#D4EDD9] rounded-lg transition-colors"
            >
              <MessageSquare className="w-3 h-3" />
              {action.cta_label}
            </button>
          )}

          {/* Entity link */}
          {action.entity_type && action.entity_id &&
            action.entity_type !== 'project' && (
              <button
                onClick={() => onNavigate?.(action.entity_type!, action.entity_id)}
                className="mt-1.5 inline-flex items-center gap-1 text-[11px] text-[#3FAF7A] hover:underline"
              >
                <ArrowRight className="w-3 h-3" />
                {action.entity_name || 'View entity'}
              </button>
            )}
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// Open Questions Summary
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
            <span className="inline-flex items-center px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-[#F0F0F0] text-[#666666]">
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
