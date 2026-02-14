'use client'

import { Lightbulb, ArrowRight, Users, FileText, Target, Loader2 } from 'lucide-react'
import type { NextAction } from '@/lib/api'

interface NextActionsBarProps {
  actions: NextAction[]
  loading: boolean
  onSendToCollab?: (action: NextAction) => void
}

const ACTION_ICONS: Record<string, typeof Target> = {
  confirm_critical: Target,
  stakeholder_gap: Users,
  section_gap: FileText,
  missing_evidence: FileText,
  validate_pains: Target,
  missing_vision: Lightbulb,
  missing_metrics: Target,
}

export function NextActionsBar({ actions, loading, onSendToCollab }: NextActionsBarProps) {
  if (loading) {
    return (
      <div className="mb-8 border border-[#E5E5E5] rounded-2xl bg-white shadow-md p-5">
        <div className="flex items-center gap-2 text-[12px] text-[#999999]">
          <Loader2 className="w-4 h-4 animate-spin" />
          Computing recommended actions...
        </div>
      </div>
    )
  }

  if (actions.length === 0) return null

  return (
    <div className="mb-8 border border-[#E5E5E5] rounded-2xl bg-white shadow-md overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3 bg-[#F4F4F4] border-b border-[#E5E5E5]">
        <div className="flex items-center gap-2">
          <Lightbulb className="w-4 h-4 text-[#3FAF7A]" />
          <h3 className="text-[13px] font-semibold text-[#333333]">
            Next Best Actions
          </h3>
          <span className="text-[11px] text-[#999999]">
            Top {actions.length} recommended
          </span>
        </div>
      </div>

      {/* Action items */}
      <div className="divide-y divide-[#E5E5E5]">
        {actions.map((action, idx) => {
          const Icon = ACTION_ICONS[action.action_type] || Target
          return (
            <div key={idx} className="px-5 py-3 flex items-start gap-3 hover:bg-[#F4F4F4]/50 transition-colors">
              <span className="flex items-center justify-center w-5 h-5 rounded-full bg-[#F0F0F0] text-[11px] font-medium text-[#666666] flex-shrink-0 mt-0.5">
                {idx + 1}
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <Icon className="w-3.5 h-3.5 text-[#999999] flex-shrink-0" />
                  <p className="text-[13px] font-medium text-[#333333]">{action.title}</p>
                </div>
                <p className="text-[12px] text-[#666666] mt-0.5 ml-5.5">{action.description}</p>
                {(action.suggested_stakeholder_role || action.suggested_artifact) && (
                  <div className="flex items-center gap-2 mt-1.5 ml-5.5">
                    {action.suggested_stakeholder_role && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-medium bg-[#E8F5E9] text-[#25785A] rounded-full">
                        <Users className="w-2.5 h-2.5" />
                        {action.suggested_stakeholder_role}
                      </span>
                    )}
                    {action.suggested_artifact && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-medium bg-[#F0F0F0] text-[#666666] rounded-full">
                        <FileText className="w-2.5 h-2.5" />
                        {action.suggested_artifact}
                      </span>
                    )}
                  </div>
                )}
              </div>
              {onSendToCollab && (
                <button
                  onClick={() => onSendToCollab(action)}
                  className="flex-shrink-0 inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium text-[#3FAF7A] border border-[#3FAF7A]/30 rounded-lg hover:bg-[#E8F5E9] transition-colors"
                  title="Send to Collab"
                >
                  <ArrowRight className="w-3 h-3" />
                  Collab
                </button>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
