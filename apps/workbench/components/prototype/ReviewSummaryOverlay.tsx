'use client'

import { Check, PenLine, Flag, ArrowLeft, Loader2 } from 'lucide-react'
import type { ReviewSummary } from '@/types/epic-overlay'

interface ReviewSummaryOverlayProps {
  summary: ReviewSummary
  isUpdating: boolean
  onConfirmAndUpdate: () => void
  onBackToReview: () => void
}

export default function ReviewSummaryOverlay({
  summary,
  isUpdating,
  onConfirmAndUpdate,
  onBackToReview,
}: ReviewSummaryOverlayProps) {
  const { tallies, items, total_epics, all_touched } = summary
  const hasRefines = tallies.refine > 0

  return (
    <div className="absolute inset-0 bg-white/95 backdrop-blur-sm z-30 flex items-center justify-center">
      <div className="w-full max-w-md mx-auto px-6">
        {/* Header */}
        <h2 className="text-lg font-heading font-bold text-[#0A1E2F] text-center mb-1">
          Review Summary
        </h2>
        <p className="text-xs text-[#666666] text-center mb-6">
          {total_epics} epics reviewed
        </p>

        {/* Tallies */}
        <div className="flex gap-4 justify-center mb-6">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-full bg-[#25785A]/10 flex items-center justify-center">
              <Check className="w-3 h-3 text-[#25785A]" />
            </div>
            <div>
              <p className="text-sm font-semibold text-[#0A1E2F]">{tallies.confirmed}</p>
              <p className="text-[10px] text-[#666666]">Confirmed</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-full bg-amber-500/10 flex items-center justify-center">
              <PenLine className="w-3 h-3 text-amber-600" />
            </div>
            <div>
              <p className="text-sm font-semibold text-[#0A1E2F]">{tallies.refine}</p>
              <p className="text-[10px] text-[#666666]">Refined</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center">
              <Flag className="w-3 h-3 text-[#666666]" />
            </div>
            <div>
              <p className="text-sm font-semibold text-[#0A1E2F]">{tallies.flag_for_client}</p>
              <p className="text-[10px] text-[#666666]">Flagged</p>
            </div>
          </div>
        </div>

        {/* Per-epic list */}
        <div className="bg-[#FAFAFA] rounded-lg border border-border divide-y divide-border mb-6 max-h-48 overflow-y-auto">
          {items.map((item) => (
            <div key={item.card_index} className="px-3 py-2 flex items-center gap-2">
              {item.verdict === 'confirmed' && <Check className="w-3 h-3 text-[#25785A] shrink-0" />}
              {item.verdict === 'refine' && <PenLine className="w-3 h-3 text-amber-600 shrink-0" />}
              {item.verdict === 'flag_for_client' && <Flag className="w-3 h-3 text-[#666666] shrink-0" />}
              <span className="text-xs text-[#37352f] flex-1 truncate">{item.title || `Epic ${item.card_index + 1}`}</span>
              {item.notes && (
                <span className="text-[10px] text-[#999] truncate max-w-[160px]">{item.notes}</span>
              )}
            </div>
          ))}
        </div>

        {/* Changes brief */}
        {summary.changes_brief && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2.5 mb-4">
            <p className="text-xs text-amber-900 leading-relaxed">{summary.changes_brief}</p>
            <p className="text-[9px] text-amber-500 mt-1.5">AI-generated summary</p>
          </div>
        )}

        {/* Explanation */}
        {hasRefines && (
          <p className="text-[11px] text-[#666666] text-center mb-4">
            &ldquo;Confirm &amp; Update&rdquo; will surgically update only the refined
            epics (~15-25s). Confirmed epics stay as-is.
          </p>
        )}

        {/* Action buttons */}
        <div className="flex gap-3">
          <button
            onClick={onBackToReview}
            disabled={isUpdating}
            className="flex-1 flex items-center justify-center gap-1.5 px-4 py-2.5 bg-gray-100 text-[#37352f] text-sm font-medium rounded-lg hover:bg-gray-200 disabled:opacity-50 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Review
          </button>
          <button
            onClick={onConfirmAndUpdate}
            disabled={!all_touched || isUpdating}
            className="flex-1 flex items-center justify-center gap-1.5 px-4 py-2.5 bg-brand-primary text-white text-sm font-medium rounded-lg hover:bg-[#25785A] disabled:opacity-50 transition-colors"
          >
            {isUpdating ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Updating...
              </>
            ) : hasRefines ? (
              'Confirm & Update'
            ) : (
              'Send to Client'
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
