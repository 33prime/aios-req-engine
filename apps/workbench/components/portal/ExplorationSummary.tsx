'use client'

import { ThumbsUp, ThumbsDown, Lightbulb, CheckCircle } from 'lucide-react'

interface ExplorationSummaryProps {
  totalAssumptions: number
  agreedCount: number
  disagreedCount: number
  inspirationCount: number
  onComplete: () => void
  isSubmitting: boolean
}

export function ExplorationSummary({
  totalAssumptions,
  agreedCount,
  disagreedCount,
  inspirationCount,
  onComplete,
  isSubmitting,
}: ExplorationSummaryProps) {
  const skippedCount = totalAssumptions - agreedCount - disagreedCount

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-80px)] bg-gradient-to-b from-[#0A1E2F] to-[#15314A]">
      <div className="max-w-md mx-auto text-center px-6">
        <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-[#3FAF7A]/20 flex items-center justify-center">
          <CheckCircle className="w-8 h-8 text-[#3FAF7A]" />
        </div>

        <h1 className="text-2xl font-semibold text-white mb-3">
          Great exploration!
        </h1>

        <p className="text-base text-white/70 mb-6">
          Here&apos;s a summary of your feedback. Your consultant will review
          this before the call.
        </p>

        {/* Stats cards */}
        <div className="grid grid-cols-3 gap-3 mb-8">
          <div className="bg-white/10 rounded-xl p-3">
            <ThumbsUp className="w-5 h-5 mx-auto mb-1 text-[#3FAF7A]" />
            <p className="text-xl font-bold text-white">{agreedCount}</p>
            <p className="text-[10px] text-white/50">Agreed</p>
          </div>
          <div className="bg-white/10 rounded-xl p-3">
            <ThumbsDown className="w-5 h-5 mx-auto mb-1 text-amber-400" />
            <p className="text-xl font-bold text-white">{disagreedCount}</p>
            <p className="text-[10px] text-white/50">Disagreed</p>
          </div>
          <div className="bg-white/10 rounded-xl p-3">
            <Lightbulb className="w-5 h-5 mx-auto mb-1 text-yellow-300" />
            <p className="text-xl font-bold text-white">{inspirationCount}</p>
            <p className="text-[10px] text-white/50">New Ideas</p>
          </div>
        </div>

        {skippedCount > 0 && (
          <p className="text-sm text-white/40 mb-6">
            {skippedCount} assumption{skippedCount !== 1 ? 's' : ''} skipped — totally fine!
          </p>
        )}

        <button
          onClick={onComplete}
          disabled={isSubmitting}
          className="px-8 py-3.5 bg-[#3FAF7A] text-white text-base font-medium rounded-xl hover:bg-[#35A06D] transition-all shadow-lg shadow-[#3FAF7A]/25 disabled:opacity-50"
        >
          {isSubmitting ? 'Finishing...' : "I'm Done"}
        </button>

        <p className="mt-4 text-xs text-white/30">
          Your consultant will review these results before your call
        </p>
      </div>
    </div>
  )
}
