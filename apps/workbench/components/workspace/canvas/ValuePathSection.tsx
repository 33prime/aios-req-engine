'use client'

import { Route, Clock, Zap, AlertTriangle, Info } from 'lucide-react'
import type { ValuePathStep, AutomationLevel } from '@/types/workspace'

interface ValuePathSectionProps {
  steps: ValuePathStep[]
  rationale?: string | null
  isStale: boolean
  onRegenerate: () => void
  isSynthesizing: boolean
}

function AutomationBadge({ level }: { level: AutomationLevel }) {
  const config: Record<AutomationLevel, { dot: string; label: string; bg: string; text: string }> = {
    manual: { dot: 'bg-gray-400', label: 'Manual', bg: 'bg-gray-100', text: 'text-gray-600' },
    semi_automated: { dot: 'bg-amber-400', label: 'Semi-auto', bg: 'bg-amber-50', text: 'text-amber-700' },
    fully_automated: { dot: 'bg-[#3FAF7A]', label: 'Automated', bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
  }
  const c = config[level] || config.manual
  return (
    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium ${c.bg} ${c.text} rounded`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      {c.label}
    </span>
  )
}

function RoiDot({ impact }: { impact: string }) {
  const color = impact === 'high' ? 'bg-[#3FAF7A]' : impact === 'medium' ? 'bg-gray-400' : 'bg-gray-300'
  return <span className={`w-2 h-2 rounded-full ${color} shrink-0`} title={`ROI: ${impact}`} />
}

export function ValuePathSection({
  steps,
  rationale,
  isStale,
  onRegenerate,
  isSynthesizing,
}: ValuePathSectionProps) {
  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Route className="w-4 h-4 text-[#3FAF7A]" />
          <h2 className="text-[16px] font-semibold text-[#333333]">Value Path</h2>
          {steps.length > 0 && (
            <span className="text-[12px] text-[#999999]">({steps.length} steps)</span>
          )}
        </div>
        {isStale && steps.length > 0 && (
          <button
            onClick={onRegenerate}
            disabled={isSynthesizing}
            className="inline-flex items-center gap-1 px-3 py-1 text-[11px] font-medium text-amber-700 bg-amber-50 border border-amber-200 rounded-lg hover:bg-amber-100 transition-colors disabled:opacity-50"
          >
            <AlertTriangle className="w-3 h-3" />
            Regenerate
          </button>
        )}
      </div>

      {steps.length === 0 ? (
        <div className={`bg-white rounded-2xl shadow-md border px-6 py-8 text-center ${
          isStale ? 'border-amber-300' : 'border-[#E5E5E5]'
        }`}>
          <Route className="w-8 h-8 text-[#999999] mx-auto mb-3" />
          <p className="text-[13px] text-[#666666]">
            No value path synthesized yet. Click <strong>Synthesize Value Path</strong> above
            to generate the prototype blueprint.
          </p>
        </div>
      ) : (
        <div className={`bg-white rounded-2xl shadow-md border ${
          isStale ? 'border-amber-300' : 'border-[#E5E5E5]'
        } overflow-hidden`}>
          {/* Rationale header */}
          {rationale && (
            <div className="px-5 py-3 bg-[#F4F4F4] border-b border-[#E5E5E5]">
              <div className="flex items-start gap-2">
                <Info className="w-3.5 h-3.5 text-[#999999] mt-0.5 shrink-0" />
                <p className="text-[12px] text-[#666666] italic leading-relaxed">{rationale}</p>
              </div>
            </div>
          )}

          {/* Steps timeline */}
          <div className="px-5 py-4">
            {steps.map((step, idx) => (
              <ValuePathStepCard
                key={step.step_index}
                step={step}
                displayIndex={idx + 1}
                isLast={idx === steps.length - 1}
              />
            ))}
          </div>
        </div>
      )}
    </section>
  )
}

function ValuePathStepCard({
  step,
  displayIndex,
  isLast,
}: {
  step: ValuePathStep
  displayIndex: number
  isLast: boolean
}) {
  return (
    <div className="flex gap-3">
      {/* Left: numbered badge + connector */}
      <div className="flex flex-col items-center shrink-0">
        <div className="w-7 h-7 rounded-full bg-[#0A1E2F] flex items-center justify-center shrink-0">
          <span className="text-[11px] font-bold text-white">{displayIndex}</span>
        </div>
        {!isLast && (
          <div className="w-0 flex-1 border-l-2 border-dashed border-[#E5E5E5] min-h-[16px]" />
        )}
      </div>

      {/* Right: step content */}
      <div className="flex-1 min-w-0 pb-4">
        <div className="border border-[#E5E5E5] rounded-xl px-3.5 py-2.5 hover:shadow-sm transition-shadow">
          {/* Title row */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[13px] font-medium text-[#333333]">{step.title}</span>
            {step.actor_persona_name && (
              <span className="px-2 py-0.5 text-[10px] font-medium bg-[#E8F5E9] text-[#25785A] rounded-full">
                {step.actor_persona_name}
              </span>
            )}
            <AutomationBadge level={step.automation_level} />
            {step.time_minutes != null && (
              <span className="inline-flex items-center gap-0.5 text-[11px] text-[#999999]">
                <Clock className="w-3 h-3" />
                {step.time_minutes}m
              </span>
            )}
            <RoiDot impact={step.roi_impact} />
          </div>

          {/* Description */}
          {step.description && (
            <p className="text-[12px] text-[#666666] mt-1">{step.description}</p>
          )}

          {/* Pain + Goal */}
          {step.pain_addressed && (
            <p className="text-[11px] text-[#999999] mt-1.5 italic">Pain: {step.pain_addressed}</p>
          )}
          {step.goal_served && (
            <p className="text-[11px] text-[#25785A] mt-0.5 italic">Goal: {step.goal_served}</p>
          )}

          {/* Linked features */}
          {step.linked_feature_names.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {step.linked_feature_names.map((name, i) => (
                <span
                  key={step.linked_feature_ids[i] || i}
                  className="px-1.5 py-0.5 text-[10px] font-medium bg-[#F0F0F0] text-[#666666] rounded-lg"
                >
                  {name}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
