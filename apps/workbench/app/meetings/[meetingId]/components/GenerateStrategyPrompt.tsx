'use client'

import { Sparkles, Loader2 } from 'lucide-react'

export function GenerateStrategyPrompt({
  onGenerate,
  generating,
}: {
  onGenerate: () => void
  generating: boolean
}) {
  return (
    <div className="mt-10 flex flex-col items-center justify-center text-center">
      <div className="w-14 h-14 rounded-2xl bg-brand-primary-light flex items-center justify-center mb-4">
        <Sparkles className="w-7 h-7 text-brand-primary" />
      </div>
      <p className="text-[15px] font-semibold text-text-body mb-1.5">Prepare for this meeting</p>
      <p className="text-[12px] text-text-muted max-w-sm mb-5 leading-relaxed">
        Generate a strategy playbook with call goals, mission-critical questions, stakeholder intel, and critical requirements.
      </p>
      <button
        onClick={onGenerate}
        disabled={generating}
        className="flex items-center gap-2 px-5 py-2.5 text-[13px] font-semibold text-white bg-brand-primary rounded-lg hover:bg-brand-primary-hover disabled:opacity-50 transition-colors"
      >
        {generating ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Generating...
          </>
        ) : (
          <>
            <Sparkles className="w-4 h-4" />
            Generate Strategy Brief
          </>
        )}
      </button>
    </div>
  )
}
