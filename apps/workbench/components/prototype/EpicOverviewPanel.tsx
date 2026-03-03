'use client'

import { useState, useCallback } from 'react'
import { Check, PenLine, Flag, Lock } from 'lucide-react'
import type { Epic, EpicConfirmation, EpicVerdict } from '@/types/epic-overlay'

interface EpicOverviewPanelProps {
  epic: Epic
  epicIndex: number
  sessionId: string
  confirmation?: EpicConfirmation | null
  onSubmitVerdict: (verdict: EpicVerdict, notes?: string) => Promise<void>
}

export default function EpicOverviewPanel({
  epic,
  epicIndex,
  confirmation,
  onSubmitVerdict,
}: EpicOverviewPanelProps) {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showRefineInput, setShowRefineInput] = useState(false)
  const [refineNotes, setRefineNotes] = useState('')

  const isLocked = !!confirmation?.verdict

  const handleVerdict = useCallback(
    async (verdict: EpicVerdict, notes?: string) => {
      setIsSubmitting(true)
      try {
        await onSubmitVerdict(verdict, notes)
        setShowRefineInput(false)
        setRefineNotes('')
      } finally {
        setIsSubmitting(false)
      }
    },
    [onSubmitVerdict]
  )

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* Header */}
      <div className="px-4 pt-4 pb-2">
        <h3 className="text-sm font-semibold text-[#0A1E2F]">{epic.title}</h3>
        {epic.persona_names.length > 0 && (
          <p className="text-[11px] text-[#666666] mt-0.5">
            {epic.persona_names.join(', ')}
          </p>
        )}
      </div>

      {/* Narrative */}
      <div className="px-4 py-3">
        <p className="text-sm text-[#37352f] leading-relaxed">{epic.narrative}</p>
      </div>

      {/* Provenance Quotes */}
      {epic.provenance_quotes && epic.provenance_quotes.length > 0 && (
        <div className="px-4 py-2 space-y-2">
          {epic.provenance_quotes.map((quote, i) => (
            <blockquote
              key={i}
              className="border-l-2 border-brand-primary/40 pl-3 py-1"
            >
              <p className="text-xs text-[#37352f] italic leading-relaxed">
                &ldquo;{quote.quote_text}&rdquo;
              </p>
              <p className="text-[10px] text-[#666666] mt-0.5">
                — {quote.speaker_name}
                {quote.source_label && (
                  <span className="text-[#999]"> · {quote.source_label}</span>
                )}
              </p>
            </blockquote>
          ))}
        </div>
      )}

      {/* Features */}
      {epic.features.length > 0 && (
        <div className="px-4 py-2">
          <p className="text-[10px] font-semibold text-[#666666] uppercase tracking-wider mb-1.5">
            Features
          </p>
          <div className="space-y-1">
            {epic.features.map((f) => (
              <div
                key={f.feature_id}
                className="flex items-center gap-2 text-xs text-[#37352f]"
              >
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    f.implementation_status === 'functional'
                      ? 'bg-brand-primary'
                      : f.implementation_status === 'partial'
                        ? 'bg-yellow-500'
                        : 'bg-gray-300'
                  }`}
                />
                {f.name}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Spacer */}
      <div className="flex-1" />

      {/* Verdict Actions */}
      <div className="px-4 py-3 border-t border-border">
        {isLocked ? (
          <div className="flex items-center gap-2 text-xs">
            <Lock className="w-3 h-3 text-[#666666]" />
            <span className="text-[#666666]">
              Verdict: <span className="font-medium text-[#37352f] capitalize">{confirmation?.verdict}</span>
            </span>
            {confirmation?.notes && (
              <span className="text-[#999] truncate ml-1">— {confirmation.notes}</span>
            )}
          </div>
        ) : (
          <div className="space-y-2">
            {showRefineInput ? (
              <div className="space-y-2">
                <textarea
                  value={refineNotes}
                  onChange={(e) => setRefineNotes(e.target.value)}
                  placeholder="What needs to change?"
                  className="w-full text-xs border border-border rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-1 focus:ring-brand-primary"
                  rows={3}
                  autoFocus
                />
                <div className="flex gap-2">
                  <button
                    onClick={() => handleVerdict('refine', refineNotes)}
                    disabled={!refineNotes.trim() || isSubmitting}
                    className="flex-1 px-3 py-1.5 bg-amber-500 text-white text-xs font-medium rounded-lg hover:bg-amber-600 disabled:opacity-50 transition-colors"
                  >
                    Submit Refinement
                  </button>
                  <button
                    onClick={() => {
                      setShowRefineInput(false)
                      setRefineNotes('')
                    }}
                    className="px-3 py-1.5 text-xs text-[#666666] hover:text-[#37352f] transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex gap-2">
                <button
                  onClick={() => handleVerdict('confirmed')}
                  disabled={isSubmitting}
                  className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 bg-brand-primary text-white text-xs font-medium rounded-lg hover:bg-[#25785A] disabled:opacity-50 transition-colors"
                >
                  <Check className="w-3 h-3" />
                  Confirm
                </button>
                <button
                  onClick={() => setShowRefineInput(true)}
                  disabled={isSubmitting}
                  className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 bg-amber-50 text-amber-700 text-xs font-medium rounded-lg hover:bg-amber-100 disabled:opacity-50 transition-colors border border-amber-200"
                >
                  <PenLine className="w-3 h-3" />
                  Refine
                </button>
                <button
                  onClick={() => handleVerdict('flag_for_client')}
                  disabled={isSubmitting}
                  className="flex items-center justify-center gap-1.5 px-3 py-1.5 bg-gray-50 text-[#666666] text-xs font-medium rounded-lg hover:bg-gray-100 disabled:opacity-50 transition-colors border border-gray-200"
                  title="Flag for client discussion"
                >
                  <Flag className="w-3 h-3" />
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
