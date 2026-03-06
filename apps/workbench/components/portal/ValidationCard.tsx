'use client'

import { useState } from 'react'
import type { ValidationItem, VerdictType } from '@/types/portal'

interface ValidationCardProps {
  item: ValidationItem
  onVerdict: (entityType: string, entityId: string, verdict: VerdictType, notes?: string) => Promise<void>
}

const ENTITY_LABELS: Record<string, string> = {
  workflow: 'Workflow',
  business_driver: 'Business Driver',
  feature: 'Feature',
  persona: 'Persona',
  vp_step: 'Value Path Step',
  prototype_epic: 'Epic',
}

const PRIORITY_STYLES: Record<number, string> = {
  1: 'bg-red-100 text-red-700',
  2: 'bg-amber-100 text-amber-700',
  3: 'bg-surface-subtle text-text-secondary',
  4: 'bg-surface-subtle text-text-placeholder',
  5: 'bg-surface-subtle text-text-placeholder',
}

export default function ValidationCard({ item, onVerdict }: ValidationCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [localVerdict, setLocalVerdict] = useState<VerdictType | null>(
    item.existing_verdict as VerdictType | null
  )

  const handleVerdict = async (verdict: VerdictType) => {
    // Confirm is instant; refine/flag expand the notes area
    if (verdict === 'confirmed') {
      setSubmitting(true)
      try {
        await onVerdict(item.entity_type, item.entity_id, verdict)
        setLocalVerdict(verdict)
      } finally {
        setSubmitting(false)
      }
    } else {
      setExpanded(true)
      setLocalVerdict(verdict)
    }
  }

  const handleSubmitWithNotes = async () => {
    if (!localVerdict || localVerdict === 'confirmed') return
    setSubmitting(true)
    try {
      await onVerdict(item.entity_type, item.entity_id, localVerdict, notes || undefined)
    } finally {
      setSubmitting(false)
    }
  }

  const isConfirmed = localVerdict === 'confirmed'
  const isRefine = localVerdict === 'refine'
  const isFlag = localVerdict === 'flag'

  return (
    <div className={`
      bg-surface-card rounded-lg border p-5 transition-all shadow-sm
      ${isConfirmed ? 'border-green-200 bg-green-50/30' :
        isFlag ? 'border-red-200 bg-red-50/30' :
        isRefine ? 'border-amber-200 bg-amber-50/30' :
        item.is_assigned_to_me ? 'border-brand-primary/30' : 'border-border'}
    `}>
      {/* Header row */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-medium text-text-placeholder uppercase">
              {ENTITY_LABELS[item.entity_type] || item.entity_type}
            </span>
            <span className={`text-xs px-1.5 py-0.5 rounded ${PRIORITY_STYLES[item.priority] || PRIORITY_STYLES[3]}`}>
              P{item.priority}
            </span>
            {item.is_assigned_to_me && !localVerdict && (
              <span className="text-xs bg-brand-primary-light text-brand-primary px-2 py-0.5 rounded-full font-medium">
                Your review
              </span>
            )}
          </div>
          <h3 className="text-base font-semibold text-text-primary">{item.name}</h3>
        </div>

        {/* Verdict badge (after submission) */}
        {localVerdict && (
          <span className={`
            text-xs font-medium px-2.5 py-1 rounded-full
            ${isConfirmed ? 'bg-green-100 text-green-700' :
              isRefine ? 'bg-amber-100 text-amber-700' :
              'bg-red-100 text-red-700'}
          `}>
            {localVerdict}
          </span>
        )}
      </div>

      {/* Summary */}
      {item.summary && (
        <p className="text-sm text-text-secondary mb-3">{item.summary}</p>
      )}

      {/* Type-specific details */}
      {Object.keys(item.details).length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {item.details.state_type ? (
            <span className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded">
              {String(item.details.state_type)}
            </span>
          ) : null}
          {item.details.impact_area ? (
            <span className="text-xs bg-purple-50 text-purple-700 px-2 py-1 rounded">
              {String(item.details.impact_area)}
            </span>
          ) : null}
          {item.details.enrichment_status ? (
            <span className="text-xs bg-surface-subtle text-text-secondary px-2 py-1 rounded">
              {String(item.details.enrichment_status)}
            </span>
          ) : null}
        </div>
      )}

      {/* Reason */}
      {item.reason && (
        <p className="text-xs text-text-placeholder mb-3">
          Assigned because: {item.reason}
        </p>
      )}

      {/* Existing notes */}
      {item.existing_notes && !expanded && (
        <div className="text-sm text-text-muted bg-surface-subtle rounded p-2 mb-3">
          Previous notes: {item.existing_notes}
        </div>
      )}

      {/* Action buttons (only show if no verdict yet) */}
      {!localVerdict && (
        <div className="flex items-center gap-2 mt-4">
          <button
            onClick={() => handleVerdict('confirmed')}
            disabled={submitting}
            className="flex-1 py-2 text-sm font-medium rounded-lg border-2 border-green-200 text-green-700 hover:bg-green-50 transition-colors disabled:opacity-50"
          >
            {submitting ? '...' : 'Confirm'}
          </button>
          <button
            onClick={() => handleVerdict('refine')}
            disabled={submitting}
            className="flex-1 py-2 text-sm font-medium rounded-lg border-2 border-amber-200 text-amber-700 hover:bg-amber-50 transition-colors disabled:opacity-50"
          >
            Refine
          </button>
          <button
            onClick={() => handleVerdict('flag')}
            disabled={submitting}
            className="flex-1 py-2 text-sm font-medium rounded-lg border-2 border-red-200 text-red-700 hover:bg-red-50 transition-colors disabled:opacity-50"
          >
            Flag
          </button>
        </div>
      )}

      {/* Notes expansion for refine/flag */}
      {expanded && !isConfirmed && (
        <div className="mt-4 space-y-3">
          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            placeholder={
              localVerdict === 'refine'
                ? 'What should be changed or clarified?'
                : 'Why are you flagging this? What concerns do you have?'
            }
            rows={3}
            className="w-full px-3 py-2 border border-border rounded-lg text-sm focus:ring-2 focus:ring-brand-primary-ring focus:border-brand-primary resize-none"
            autoFocus
          />
          <div className="flex items-center justify-end gap-2">
            <button
              onClick={() => {
                setExpanded(false)
                setLocalVerdict(null)
                setNotes('')
              }}
              className="px-3 py-1.5 text-sm text-text-muted hover:text-text-body"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmitWithNotes}
              disabled={submitting}
              className={`
                px-4 py-1.5 text-sm font-medium text-white rounded-lg disabled:opacity-50
                ${localVerdict === 'refine' ? 'bg-amber-500 hover:bg-amber-600' : 'bg-red-500 hover:bg-red-600'}
              `}
            >
              {submitting ? 'Submitting...' : `Submit ${localVerdict}`}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
