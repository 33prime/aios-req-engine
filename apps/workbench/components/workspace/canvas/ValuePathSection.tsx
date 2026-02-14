'use client'

import { Route, Clock, AlertTriangle, Info, Unlock, TrendingUp, Lightbulb, Zap } from 'lucide-react'
import type { ValuePathStep, ValuePathUnlock, AutomationLevel, UnlockType } from '@/types/workspace'

interface ValuePathSectionProps {
  steps: ValuePathStep[]
  rationale?: string | null
  isStale: boolean
  onRegenerate: () => void
  isSynthesizing: boolean
  onStepClick?: (stepIndex: number, stepTitle: string) => void
  onUnlockClick?: (stepIndex: number, stepTitle: string, unlock: ValuePathUnlock) => void
  selectedStepIndex?: number | null
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

const UNLOCK_CONFIG: Record<UnlockType, { icon: typeof Unlock; color: string; bg: string; label: string }> = {
  capability: { icon: Unlock, color: 'text-[#25785A]', bg: 'bg-[#E8F5E9]', label: 'Capability' },
  scale: { icon: TrendingUp, color: 'text-[#25785A]', bg: 'bg-[#E8F5E9]', label: 'Scale' },
  insight: { icon: Lightbulb, color: 'text-[#25785A]', bg: 'bg-[#E8F5E9]', label: 'Insight' },
  speed: { icon: Zap, color: 'text-[#25785A]', bg: 'bg-[#E8F5E9]', label: 'Speed' },
}

function UnlockTypeBadge({ type }: { type: UnlockType }) {
  const cfg = UNLOCK_CONFIG[type] || UNLOCK_CONFIG.capability
  const Icon = cfg.icon
  return (
    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-semibold ${cfg.bg} ${cfg.color} rounded-full`}>
      <Icon className="w-3 h-3" />
      {cfg.label}
    </span>
  )
}

export function ValuePathSection({
  steps,
  rationale,
  isStale,
  onRegenerate,
  isSynthesizing,
  onStepClick,
  onUnlockClick,
  selectedStepIndex,
}: ValuePathSectionProps) {
  const unlockCounts = steps.reduce(
    (acc, step) => {
      for (const u of step.unlocks || []) {
        acc[u.unlock_type] = (acc[u.unlock_type] || 0) + 1
        acc.total++
      }
      return acc
    },
    { total: 0 } as Record<string, number>
  )

  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Route className="w-4 h-4 text-[#3FAF7A]" />
          <h2 className="text-[16px] font-semibold text-[#333333]">Value Path</h2>
          {steps.length > 0 && (
            <span className="text-[12px] text-[#999999]">({steps.length} steps)</span>
          )}
          {unlockCounts.total > 0 && (
            <span className="text-[12px] text-[#25785A] font-medium">
              {unlockCounts.total} unlock{unlockCounts.total !== 1 ? 's' : ''}
            </span>
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

          {/* Column headers */}
          <div className="flex border-b border-[#E5E5E5]">
            <div className="flex-1 px-5 py-2.5 bg-[#F0F0F0]">
              <span className="text-[11px] font-semibold text-[#666666] uppercase tracking-wide">
                The Journey
              </span>
            </div>
            {/* Gap between columns */}
            <div className="w-4 bg-[#F4F4F4] border-x border-[#E5E5E5]" />
            <div className="flex-1 px-5 py-2.5 bg-[#E8F5E9]">
              <span className="text-[11px] font-semibold text-[#25785A] uppercase tracking-wide">
                What This Unlocks
              </span>
            </div>
          </div>

          {/* Side-by-side rows */}
          {steps.map((step, idx) => (
            <ValuePathRow
              key={step.step_index}
              step={step}
              displayIndex={idx + 1}
              isLast={idx === steps.length - 1}
              isSelected={selectedStepIndex === step.step_index}
              onStepClick={onStepClick ? () => onStepClick(step.step_index, step.title) : undefined}
              onUnlockClick={onUnlockClick
                ? (unlock: ValuePathUnlock) => onUnlockClick(step.step_index, step.title, unlock)
                : undefined
              }
            />
          ))}

          {/* Summary footer */}
          {unlockCounts.total > 0 && (
            <div className="px-5 py-3 bg-[#F4F4F4] border-t border-[#E5E5E5]">
              <div className="flex items-center gap-4 text-[11px] text-[#666666]">
                <span className="font-medium text-[#333333]">
                  {steps.filter(s => s.roi_impact === 'high').length} high-impact steps
                </span>
                <span className="text-[#E5E5E5]">|</span>
                {Object.entries(UNLOCK_CONFIG).map(([type, cfg]) => {
                  const count = unlockCounts[type] || 0
                  if (count === 0) return null
                  const Icon = cfg.icon
                  return (
                    <span key={type} className="inline-flex items-center gap-1">
                      <Icon className="w-3 h-3 text-[#25785A]" />
                      {count} {cfg.label.toLowerCase()}
                    </span>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  )
}

function ValuePathRow({
  step,
  displayIndex,
  isLast,
  isSelected,
  onStepClick,
  onUnlockClick,
}: {
  step: ValuePathStep
  displayIndex: number
  isLast: boolean
  isSelected?: boolean
  onStepClick?: () => void
  onUnlockClick?: (unlock: ValuePathUnlock) => void
}) {
  const unlocks = step.unlocks || []

  return (
    <div className={`flex transition-all ${
      isSelected ? 'bg-[#F8FFF8]' : ''
    } ${!isLast ? 'border-b border-[#E5E5E5]' : ''}`}>
      {/* LEFT: Step card */}
      <div
        className={`flex-1 px-5 py-3.5 ${onStepClick ? 'cursor-pointer hover:bg-[#FAFAFA]' : ''}`}
        onClick={onStepClick}
        role={onStepClick ? 'button' : undefined}
        tabIndex={onStepClick ? 0 : undefined}
        onKeyDown={onStepClick ? (e) => { if (e.key === 'Enter' || e.key === ' ') onStepClick() } : undefined}
      >
        <div className="flex gap-3">
          {/* Numbered badge */}
          <div className="flex flex-col items-center shrink-0">
            <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${
              isSelected ? 'bg-[#3FAF7A]' : 'bg-[#0A1E2F]'
            }`}>
              <span className="text-[11px] font-bold text-white">{displayIndex}</span>
            </div>
          </div>

          {/* Step content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-[13px] font-medium text-[#333333]">{step.title}</span>
              {step.actor_persona_name && (
                <span className="px-2 py-0.5 text-[10px] font-medium bg-[#E8F5E9] text-[#25785A] rounded-full">
                  {step.actor_persona_name}
                </span>
              )}
            </div>

            <div className="flex items-center gap-2 mt-1 flex-wrap">
              <AutomationBadge level={step.automation_level} />
              {step.time_minutes != null && (
                <span className="inline-flex items-center gap-0.5 text-[11px] text-[#999999]">
                  <Clock className="w-3 h-3" />
                  {step.time_minutes}m
                </span>
              )}
            </div>

            {step.description && (
              <p className="text-[12px] text-[#666666] mt-1 line-clamp-2">{step.description}</p>
            )}

            {step.pain_addressed && (
              <p className="text-[11px] text-[#999999] mt-1.5 italic line-clamp-1">
                Pain: {step.pain_addressed}
              </p>
            )}

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

      {/* Gap between columns */}
      <div className="w-4 bg-[#F4F4F4] border-x border-[#E5E5E5] shrink-0" />

      {/* RIGHT: Unlocks */}
      <div className="flex-1 px-5 py-3.5">
        {unlocks.length > 0 ? (
          <div className="space-y-2.5">
            {unlocks.map((unlock, i) => (
              <UnlockCard
                key={i}
                unlock={unlock}
                onClick={onUnlockClick ? () => onUnlockClick(unlock) : undefined}
              />
            ))}
          </div>
        ) : (
          <div className="flex items-start gap-2 py-1">
            {step.goal_served ? (
              <>
                <div className="w-5 h-5 rounded-full bg-[#E8F5E9] flex items-center justify-center shrink-0 mt-0.5">
                  <Zap className="w-3 h-3 text-[#25785A]" />
                </div>
                <p className="text-[12px] text-[#25785A] font-medium">{step.goal_served}</p>
              </>
            ) : (
              <p className="text-[12px] text-[#999999] italic">
                Regenerate to see unlock insights
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function UnlockCard({
  unlock,
  onClick,
}: {
  unlock: ValuePathUnlock
  onClick?: () => void
}) {
  const cfg = UNLOCK_CONFIG[unlock.unlock_type as UnlockType] || UNLOCK_CONFIG.capability
  const Icon = cfg.icon

  return (
    <div
      className={`flex items-start gap-2 ${
        onClick ? 'cursor-pointer hover:bg-[#F8FFF8] -mx-2 px-2 py-1 rounded-lg transition-colors' : ''
      }`}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => { if (e.key === 'Enter' || e.key === ' ') onClick() } : undefined}
    >
      <div className={`w-5 h-5 rounded-full ${cfg.bg} flex items-center justify-center shrink-0 mt-0.5`}>
        <Icon className={`w-3 h-3 ${cfg.color}`} />
      </div>
      <div className="min-w-0">
        <div className="flex items-center gap-1.5 mb-0.5">
          <UnlockTypeBadge type={unlock.unlock_type as UnlockType} />
        </div>
        <p className="text-[12px] text-[#333333] leading-relaxed">{unlock.description}</p>
        {unlock.strategic_value && (
          <p className="text-[11px] text-[#666666] mt-0.5">{unlock.strategic_value}</p>
        )}
      </div>
    </div>
  )
}
