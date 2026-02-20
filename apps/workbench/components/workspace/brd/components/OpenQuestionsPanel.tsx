'use client'

import { useState } from 'react'
import {
  MessageCircle,
  ChevronDown,
  ChevronRight,
  Check,
  X,
  ExternalLink,
  Loader2,
} from 'lucide-react'
import type { OpenQuestion } from '@/types/workspace'
import { answerQuestion, dismissQuestion } from '@/lib/api'

interface OpenQuestionsPanelProps {
  projectId: string
  questions: OpenQuestion[]
  loading: boolean
  onMutate?: () => void
}

const PRIORITY_ORDER: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
}

const PRIORITY_LABELS: Record<string, { label: string; bg: string; text: string }> = {
  critical: { label: 'Critical', bg: '#FEE2E2', text: '#991B1B' },
  high: { label: 'High', bg: '#FEF3C7', text: '#92400E' },
  medium: { label: 'Medium', bg: '#F0F0F0', text: '#666666' },
  low: { label: 'Low', bg: '#F0F0F0', text: '#999999' },
}

export function OpenQuestionsPanel({ projectId, questions, loading, onMutate }: OpenQuestionsPanelProps) {
  const [expanded, setExpanded] = useState(false)
  const [answerInputs, setAnswerInputs] = useState<Record<string, string>>({})
  const [submitting, setSubmitting] = useState<Record<string, boolean>>({})

  const openQuestions = questions.filter(q => q.status === 'open')

  if (loading) return null

  if (openQuestions.length === 0) return null

  const sorted = [...openQuestions].sort(
    (a, b) => (PRIORITY_ORDER[a.priority] ?? 3) - (PRIORITY_ORDER[b.priority] ?? 3)
  )

  const criticalCount = sorted.filter(q => q.priority === 'critical').length
  const highCount = sorted.filter(q => q.priority === 'high').length

  const handleAnswer = async (questionId: string) => {
    const answer = answerInputs[questionId]?.trim()
    if (!answer) return
    setSubmitting(s => ({ ...s, [questionId]: true }))
    try {
      await answerQuestion(projectId, questionId, answer)
      setAnswerInputs(prev => {
        const next = { ...prev }
        delete next[questionId]
        return next
      })
      onMutate?.()
    } catch (err) {
      console.error('Failed to answer question:', err)
    } finally {
      setSubmitting(s => ({ ...s, [questionId]: false }))
    }
  }

  const handleDismiss = async (questionId: string) => {
    setSubmitting(s => ({ ...s, [questionId]: true }))
    try {
      await dismissQuestion(projectId, questionId)
      onMutate?.()
    } catch (err) {
      console.error('Failed to dismiss question:', err)
    } finally {
      setSubmitting(s => ({ ...s, [questionId]: false }))
    }
  }

  return (
    <div className="mb-6 border border-[#E5E5E5] rounded-2xl bg-white shadow-md overflow-hidden">
      {/* Collapsible header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-5 py-3 bg-[#F4F4F4] border-b border-[#E5E5E5] flex items-center gap-2 hover:bg-[#EEEEEE] transition-colors"
      >
        {expanded ? (
          <ChevronDown className="w-4 h-4 text-[#666666]" />
        ) : (
          <ChevronRight className="w-4 h-4 text-[#666666]" />
        )}
        <MessageCircle className="w-4 h-4 text-[#3FAF7A]" />
        <span className="text-[13px] font-semibold text-[#333333]">
          Open Questions
        </span>
        <span className="text-[11px] text-[#999999]">
          {openQuestions.length} open
        </span>
        {criticalCount > 0 && (
          <span className="inline-flex items-center px-1.5 py-0.5 text-[10px] font-medium rounded-full"
            style={{ backgroundColor: '#FEE2E2', color: '#991B1B' }}>
            {criticalCount} critical
          </span>
        )}
        {highCount > 0 && (
          <span className="inline-flex items-center px-1.5 py-0.5 text-[10px] font-medium rounded-full"
            style={{ backgroundColor: '#FEF3C7', color: '#92400E' }}>
            {highCount} high
          </span>
        )}
      </button>

      {/* Question list */}
      {expanded && (
        <div className="divide-y divide-[#E5E5E5]">
          {sorted.map(q => {
            const pl = PRIORITY_LABELS[q.priority] || PRIORITY_LABELS.medium
            const isSubmitting = submitting[q.id]
            const showAnswerInput = answerInputs[q.id] !== undefined

            return (
              <div key={q.id} className="px-5 py-3">
                <div className="flex items-start gap-2">
                  <MessageCircle className="w-3.5 h-3.5 text-[#999999] mt-0.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="text-[13px] font-medium text-[#333333]">{q.question}</p>
                      <span
                        className="inline-flex items-center px-1.5 py-0.5 text-[10px] font-medium rounded-full"
                        style={{ backgroundColor: pl.bg, color: pl.text }}
                      >
                        {pl.label}
                      </span>
                    </div>
                    {q.why_it_matters && (
                      <p className="text-[12px] text-[#666666] mt-0.5">{q.why_it_matters}</p>
                    )}
                    {q.target_entity_id && (
                      <a
                        href={`#entity-${q.target_entity_type}-${q.target_entity_id}`}
                        className="inline-flex items-center gap-1 text-[11px] text-[#3FAF7A] mt-1 hover:underline"
                      >
                        <ExternalLink className="w-2.5 h-2.5" />
                        View linked {q.target_entity_type}
                      </a>
                    )}

                    {/* Inline answer */}
                    {showAnswerInput && (
                      <div className="mt-2 flex items-center gap-2">
                        <input
                          type="text"
                          value={answerInputs[q.id] || ''}
                          onChange={e => setAnswerInputs(prev => ({ ...prev, [q.id]: e.target.value }))}
                          placeholder="Type your answer..."
                          className="flex-1 px-3 py-1.5 text-[12px] border border-[#E5E5E5] rounded-lg focus:outline-none focus:ring-1 focus:ring-[#3FAF7A]"
                          onKeyDown={e => { if (e.key === 'Enter') handleAnswer(q.id) }}
                          disabled={isSubmitting}
                        />
                        <button
                          onClick={() => handleAnswer(q.id)}
                          disabled={isSubmitting || !answerInputs[q.id]?.trim()}
                          className="p-1.5 text-[#3FAF7A] hover:bg-[#E8F5E9] rounded-lg disabled:opacity-40"
                        >
                          {isSubmitting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                        </button>
                        <button
                          onClick={() => setAnswerInputs(prev => {
                            const next = { ...prev }
                            delete next[q.id]
                            return next
                          })}
                          className="p-1.5 text-[#999999] hover:bg-[#F0F0F0] rounded-lg"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    )}

                    {/* Action buttons */}
                    {!showAnswerInput && (
                      <div className="flex items-center gap-2 mt-2">
                        <button
                          onClick={() => setAnswerInputs(prev => ({ ...prev, [q.id]: '' }))}
                          className="text-[11px] font-medium text-[#3FAF7A] hover:underline"
                          disabled={isSubmitting}
                        >
                          Answer
                        </button>
                        <button
                          onClick={() => handleDismiss(q.id)}
                          className="text-[11px] font-medium text-[#999999] hover:underline"
                          disabled={isSubmitting}
                        >
                          {isSubmitting ? 'Dismissing...' : 'Dismiss'}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
