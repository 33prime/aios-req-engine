'use client'

import { Sparkles, ArrowRight, Zap } from 'lucide-react'
import type { SolutionFlowOverview } from '@/types/workspace'

const PHASE_CONFIG: Record<string, { label: string; color: string }> = {
  entry: { label: 'Entry', color: 'bg-[#0A1E2F]/10 text-[#0A1E2F]' },
  core_experience: { label: 'Core', color: 'bg-[#3FAF7A]/10 text-[#25785A]' },
  output: { label: 'Output', color: 'bg-[#0D2A35]/10 text-[#0D2A35]' },
  admin: { label: 'Admin', color: 'bg-[#F4F4F4] text-[#666666]' },
}

interface SolutionFlowSectionProps {
  flow: SolutionFlowOverview | null | undefined
  onOpen: () => void
  onGenerate: () => void
  isGenerating?: boolean
}

export function SolutionFlowSection({ flow, onOpen, onGenerate, isGenerating }: SolutionFlowSectionProps) {
  const steps = flow?.steps || []
  const hasSteps = steps.length > 0

  // Phase breakdown
  const phaseCountMap: Record<string, number> = {}
  for (const step of steps) {
    phaseCountMap[step.phase] = (phaseCountMap[step.phase] || 0) + 1
  }

  // Confirmation progress
  const confirmedCount = steps.filter(s =>
    s.confirmation_status === 'confirmed_consultant' || s.confirmation_status === 'confirmed_client'
  ).length
  const progressPct = steps.length > 0 ? Math.round((confirmedCount / steps.length) * 100) : 0

  // Open question count
  const totalOpenQuestions = steps.reduce((sum, s) => sum + (s.open_question_count || 0), 0)

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Zap className="w-5 h-5 text-[#0A1E2F]" />
          <h2 className="text-lg font-semibold text-[#333333]">Solution Flow</h2>
          {steps.length > 0 && (
            <span className="text-xs text-[#999999] ml-1">({steps.length})</span>
          )}
        </div>
      </div>

      {!hasSteps ? (
        /* Empty state — generate CTA */
        <div className="bg-gradient-to-br from-[#0A1E2F]/5 to-[#3FAF7A]/5 rounded-2xl border border-[#E5E5E5] p-8 text-center">
          <div className="w-12 h-12 rounded-full bg-[#3FAF7A]/10 flex items-center justify-center mx-auto mb-4">
            <Sparkles className="w-6 h-6 text-[#3FAF7A]" />
          </div>
          <h3 className="text-lg font-semibold text-[#333333] mb-2">
            Generate Solution Flow
          </h3>
          <p className="text-sm text-[#666666] mb-6 max-w-md mx-auto">
            Transform your workflows, features, and data entities into a goal-oriented journey showing what the app actually does — step by step.
          </p>
          <button
            onClick={onGenerate}
            disabled={isGenerating}
            className="inline-flex items-center gap-2 px-6 py-3 bg-[#3FAF7A] text-white rounded-xl text-sm font-semibold hover:bg-[#25785A] transition-colors disabled:opacity-50"
          >
            {isGenerating ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                Generate Solution Flow
              </>
            )}
          </button>
        </div>
      ) : (
        /* Hero card */
        <div
          className="bg-white rounded-2xl border border-[#E5E5E5] shadow-[0_1px_2px_rgba(0,0,0,0.04)] hover:shadow-[0_4px_6px_rgba(0,0,0,0.08)] transition-shadow cursor-pointer"
          onClick={onOpen}
        >
          <div className="p-6">
            {/* Summary line */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-[#0A1E2F]/8 flex items-center justify-center">
                  <Zap className="w-5 h-5 text-[#0A1E2F]" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-[#333333]">
                    {flow?.title || 'Solution Flow'}
                  </h3>
                  <p className="text-xs text-[#999999]">
                    {steps.length} steps across {Object.keys(phaseCountMap).length} phases
                  </p>
                </div>
              </div>
              <button className="flex items-center gap-1.5 text-sm text-[#3FAF7A] font-medium hover:underline">
                Open
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>

            {/* Phase breakdown chips */}
            <div className="flex flex-wrap gap-2 mb-4">
              {Object.entries(phaseCountMap).map(([phase, count]) => {
                const config = PHASE_CONFIG[phase] || PHASE_CONFIG.core_experience
                return (
                  <span
                    key={phase}
                    className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${config.color}`}
                  >
                    {config.label}: {count}
                  </span>
                )
              })}
            </div>

            {/* Confirmation progress */}
            <div className="flex items-center gap-3">
              <div className="flex-1 h-1.5 bg-[#F4F4F4] rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#3FAF7A] rounded-full transition-all"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
              <span className="text-xs text-[#999999] whitespace-nowrap">
                {confirmedCount}/{steps.length} confirmed
              </span>
            </div>

            {/* Open questions indicator */}
            {totalOpenQuestions > 0 && (
              <div className="mt-3 text-xs text-[#8B7355] bg-[#EDE8D5]/60 rounded-lg px-3 py-1.5 inline-block">
                {totalOpenQuestions} open question{totalOpenQuestions !== 1 ? 's' : ''} need attention
              </div>
            )}

            {/* Summary text */}
            {flow?.summary && (
              <p className="mt-3 text-sm text-[#666666] line-clamp-2">
                {flow.summary}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
