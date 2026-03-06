'use client'

import { useState } from 'react'
import { Check, SkipForward, MessageSquare, AlertTriangle, Flag, Edit3 } from 'lucide-react'
import { answerInfoRequest, submitVerdict } from '@/lib/api/portal'
import type { InfoRequest, ValidationItem, VerdictType } from '@/types/portal'

// ============================================================================
// Question Mode
// ============================================================================

interface QuestionCardProps {
  type: 'question'
  item: InfoRequest
  onCompleted?: () => void
}

function QuestionCard({ item, onCompleted }: QuestionCardProps) {
  const [answer, setAnswer] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)

  const handleSubmit = async () => {
    if (!answer.trim()) return
    setSubmitting(true)
    try {
      await answerInfoRequest(item.id, { text: answer.trim() })
      setDone(true)
      onCompleted?.()
    } catch {
      // Swallow — user will see no change
    } finally {
      setSubmitting(false)
    }
  }

  const handleSkip = async () => {
    setSubmitting(true)
    try {
      await answerInfoRequest(item.id, {}, 'skipped')
      setDone(true)
      onCompleted?.()
    } catch {
      // Swallow
    } finally {
      setSubmitting(false)
    }
  }

  if (done) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-3 flex items-center gap-2">
        <Check className="w-4 h-4 text-green-600" />
        <span className="text-sm text-green-700">Answered: {item.title}</span>
      </div>
    )
  }

  return (
    <div className="bg-surface-card border border-border rounded-lg p-4">
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-brand-primary flex-shrink-0" />
          <h3 className="text-sm font-medium text-text-primary">{item.title}</h3>
        </div>
        {item.priority === 'high' && (
          <span className="text-[10px] bg-red-50 text-red-600 px-1.5 py-0.5 rounded font-medium flex-shrink-0">
            High
          </span>
        )}
      </div>
      {item.description && (
        <p className="text-xs text-text-muted mb-3 ml-6">{item.description}</p>
      )}
      {item.why_asking && (
        <p className="text-[11px] text-text-placeholder mb-2 ml-6 italic">{item.why_asking}</p>
      )}
      <div className="ml-6 flex items-end gap-2">
        <textarea
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder={item.example_answer || 'Type your answer...'}
          rows={2}
          className="flex-1 text-sm px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-brand-primary-ring focus:border-brand-primary resize-none"
        />
        <div className="flex flex-col gap-1">
          <button
            onClick={handleSubmit}
            disabled={!answer.trim() || submitting}
            className="px-3 py-2 text-xs font-medium bg-brand-primary text-white rounded-lg hover:bg-brand-primary-hover disabled:opacity-40 transition-colors"
          >
            Submit
          </button>
          <button
            onClick={handleSkip}
            disabled={submitting}
            className="px-3 py-2 text-xs text-text-muted hover:text-text-body transition-colors"
          >
            <SkipForward className="w-3 h-3 inline mr-0.5" />
            Skip
          </button>
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// Validation Mode
// ============================================================================

interface ValidationCardProps {
  type: 'validation'
  item: ValidationItem
  projectId: string
  onCompleted?: () => void
}

function ValidationCard({ item, projectId, onCompleted }: ValidationCardProps) {
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)
  const [selectedVerdict, setSelectedVerdict] = useState<VerdictType | null>(null)

  const handleVerdict = async (verdict: VerdictType) => {
    setSubmitting(true)
    setSelectedVerdict(verdict)
    try {
      await submitVerdict(projectId, {
        entity_type: item.entity_type,
        entity_id: item.entity_id,
        verdict,
      })
      setDone(true)
      onCompleted?.()
    } catch {
      setSelectedVerdict(null)
    } finally {
      setSubmitting(false)
    }
  }

  if (done) {
    const colors: Record<VerdictType, string> = {
      confirmed: 'bg-green-50 border-green-200 text-green-700',
      refine: 'bg-amber-50 border-amber-200 text-amber-700',
      flag: 'bg-red-50 border-red-200 text-red-700',
    }
    return (
      <div className={`border rounded-lg px-4 py-3 flex items-center gap-2 ${colors[selectedVerdict!]}`}>
        <Check className="w-4 h-4" />
        <span className="text-sm">{selectedVerdict}: {item.name}</span>
      </div>
    )
  }

  return (
    <div className="bg-surface-card border border-border rounded-lg p-4">
      <div className="flex items-start gap-2 mb-2">
        <span className="text-[10px] uppercase tracking-wide text-text-placeholder bg-surface-subtle px-1.5 py-0.5 rounded">
          {item.entity_type.replace('_', ' ')}
        </span>
      </div>
      <h3 className="text-sm font-medium text-text-primary mb-1">{item.name}</h3>
      {item.summary && (
        <p className="text-xs text-text-muted mb-3">{item.summary}</p>
      )}
      <div className="flex gap-2">
        <button
          onClick={() => handleVerdict('confirmed')}
          disabled={submitting}
          className="flex-1 px-3 py-2 text-xs font-medium border border-border rounded-lg hover:border-green-400 hover:bg-green-50 hover:text-green-800 transition-all disabled:opacity-50"
        >
          <Check className="w-3 h-3 inline mr-1" />
          Confirm
        </button>
        <button
          onClick={() => handleVerdict('refine')}
          disabled={submitting}
          className="flex-1 px-3 py-2 text-xs font-medium border border-border rounded-lg hover:border-amber-400 hover:bg-amber-50 hover:text-amber-800 transition-all disabled:opacity-50"
        >
          <Edit3 className="w-3 h-3 inline mr-1" />
          Refine
        </button>
        <button
          onClick={() => handleVerdict('flag')}
          disabled={submitting}
          className="flex-1 px-3 py-2 text-xs font-medium border border-border rounded-lg hover:border-red-400 hover:bg-red-50 hover:text-red-800 transition-all disabled:opacity-50"
        >
          <Flag className="w-3 h-3 inline mr-1" />
          Flag
        </button>
      </div>
    </div>
  )
}

// ============================================================================
// Export
// ============================================================================

type InlineActionCardProps = QuestionCardProps | ValidationCardProps

export function InlineActionCard(props: InlineActionCardProps) {
  if (props.type === 'question') return <QuestionCard {...props} />
  return <ValidationCard {...props} />
}
