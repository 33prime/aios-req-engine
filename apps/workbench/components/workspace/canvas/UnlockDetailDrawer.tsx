'use client'

import { X, Unlock, TrendingUp, Lightbulb, Zap, Target, ArrowRight } from 'lucide-react'
import type { ValuePathUnlock, UnlockType } from '@/types/workspace'

interface UnlockDetailDrawerProps {
  stepIndex: number
  stepTitle: string
  unlock: ValuePathUnlock
  onClose: () => void
}

const UNLOCK_CONFIG: Record<UnlockType, { icon: typeof Unlock; color: string; bg: string; label: string; description: string }> = {
  capability: {
    icon: Unlock,
    color: 'text-[#25785A]',
    bg: 'bg-[#E8F5E9]',
    label: 'New Capability',
    description: 'Something the business couldn\'t do before',
  },
  scale: {
    icon: TrendingUp,
    color: 'text-[#25785A]',
    bg: 'bg-[#E8F5E9]',
    label: 'Scale Unlock',
    description: 'Removes a bottleneck or enables growth',
  },
  insight: {
    icon: Lightbulb,
    color: 'text-[#25785A]',
    bg: 'bg-[#E8F5E9]',
    label: 'New Insight',
    description: 'Visibility or data the business didn\'t have',
  },
  speed: {
    icon: Zap,
    color: 'text-[#25785A]',
    bg: 'bg-[#E8F5E9]',
    label: 'Speed Gain',
    description: 'Dramatically faster execution',
  },
}

export function UnlockDetailDrawer({
  stepIndex,
  stepTitle,
  unlock,
  onClose,
}: UnlockDetailDrawerProps) {
  const cfg = UNLOCK_CONFIG[unlock.unlock_type as UnlockType] || UNLOCK_CONFIG.capability
  const Icon = cfg.icon

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-40"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-[480px] max-w-full bg-white shadow-xl z-50 flex flex-col animate-slide-in-right">
        {/* Header */}
        <div className="flex-shrink-0 border-b border-[#E5E5E5] px-6 py-5">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3 min-w-0 flex-1">
              <div className={`w-10 h-10 rounded-full ${cfg.bg} flex items-center justify-center flex-shrink-0`}>
                <Icon className={`w-5 h-5 ${cfg.color}`} />
              </div>
              <div className="min-w-0">
                <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-semibold ${cfg.bg} ${cfg.color} rounded-full mb-1.5`}>
                  <Icon className="w-3 h-3" />
                  {cfg.label}
                </span>
                <p className="text-[11px] text-[#999999] mt-1">
                  Step {stepIndex + 1}: {stepTitle}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-[#999999] hover:text-[#666666] hover:bg-gray-100 transition-colors flex-shrink-0"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
          {/* Main description */}
          <div>
            <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2">
              What This Unlocks
            </h4>
            <div className={`${cfg.bg} border border-[#3FAF7A]/20 rounded-xl p-4`}>
              <p className="text-[14px] text-[#333333] leading-relaxed font-medium">
                {unlock.description}
              </p>
            </div>
          </div>

          {/* Unlock type explanation */}
          <div className="bg-[#F9F9F9] border border-[#E5E5E5] rounded-xl p-4">
            <div className="flex items-start gap-3">
              <div className={`w-8 h-8 rounded-full ${cfg.bg} flex items-center justify-center flex-shrink-0`}>
                <Icon className={`w-4 h-4 ${cfg.color}`} />
              </div>
              <div>
                <p className="text-[13px] font-semibold text-[#333333]">{cfg.label}</p>
                <p className="text-[12px] text-[#666666] mt-0.5">{cfg.description}</p>
              </div>
            </div>
          </div>

          {/* Strategic Value */}
          {unlock.strategic_value && (
            <div>
              <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2 flex items-center gap-1.5">
                <Target className="w-3.5 h-3.5" />
                Strategic Value
              </h4>
              <div className="bg-white border border-[#E5E5E5] rounded-xl p-4">
                <p className="text-[13px] text-[#333333] leading-relaxed">
                  {unlock.strategic_value}
                </p>
              </div>
            </div>
          )}

          {/* Enabled By */}
          {unlock.enabled_by && (
            <div>
              <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2 flex items-center gap-1.5">
                <ArrowRight className="w-3.5 h-3.5" />
                Enabled By
              </h4>
              <div className="bg-white border border-[#E5E5E5] rounded-xl p-4">
                <p className="text-[13px] text-[#666666] leading-relaxed">
                  {unlock.enabled_by}
                </p>
              </div>
            </div>
          )}

          {/* Connection to step */}
          <div className="border-t border-[#E5E5E5] pt-5">
            <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-3">
              Connected Step
            </h4>
            <div className="bg-white border border-[#E5E5E5] rounded-xl p-4 flex items-center gap-3">
              <div className="w-7 h-7 rounded-full bg-[#0A1E2F] flex items-center justify-center flex-shrink-0">
                <span className="text-[11px] font-bold text-white">{stepIndex + 1}</span>
              </div>
              <div className="min-w-0">
                <p className="text-[13px] font-medium text-[#333333] truncate">{stepTitle}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
