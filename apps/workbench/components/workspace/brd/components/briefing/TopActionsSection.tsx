'use client'

import { useState, useCallback } from 'react'
import {
  Sparkles,
  Send,
  Loader2,
  Check,
  ArrowRight,
  Upload,
  MessageSquare,
} from 'lucide-react'
import type { TerseAction } from '@/lib/api'
import { answerTerseAction } from '@/lib/api'
import {
  GAP_SOURCE_ICONS,
  GAP_SOURCE_COLORS,
} from '@/lib/action-constants'

interface TopActionsSectionProps {
  projectId: string
  actions: TerseAction[]
  onNavigate?: (entityType: string, entityId: string | null) => void
  onCascade?: () => void
  onRefresh?: () => void
  onDiscussInChat?: (action: TerseAction) => void
}

export function TopActionsSection({
  projectId,
  actions,
  onNavigate,
  onCascade,
  onRefresh,
  onDiscussInChat,
}: TopActionsSectionProps) {
  const [answerInputs, setAnswerInputs] = useState<Record<string, string>>({})
  const [submitting, setSubmitting] = useState<Record<string, boolean>>({})
  const [cascadeResults, setCascadeResults] = useState<Record<string, string>>({})
  const [fadingIds, setFadingIds] = useState<Set<string>>(new Set())

  const handleAnswer = useCallback(async (action: TerseAction) => {
    const text = answerInputs[action.action_id]?.trim()
    if (!text) return

    setSubmitting(s => ({ ...s, [action.action_id]: true }))
    try {
      const res = await answerTerseAction(projectId, action, text)
      setCascadeResults(prev => ({ ...prev, [action.action_id]: res.summary }))
      setFadingIds(prev => new Set(prev).add(action.action_id))
      setAnswerInputs(prev => {
        const next = { ...prev }
        delete next[action.action_id]
        return next
      })

      setTimeout(() => {
        setFadingIds(prev => {
          const next = new Set(prev)
          next.delete(action.action_id)
          return next
        })
        onRefresh?.()
        onCascade?.()
      }, 1200)
    } catch (err) {
      console.error('Answer submission failed:', err)
    } finally {
      setSubmitting(s => ({ ...s, [action.action_id]: false }))
    }
  }, [projectId, answerInputs, onRefresh, onCascade])

  if (actions.length === 0) return null

  return (
    <div className="border-b border-[#E5E5E5]">
      <div className="px-4 py-2.5">
        <span className="text-[11px] font-semibold text-[#666666] uppercase tracking-wide">
          Next Actions
        </span>
      </div>

      <div className="px-3 pb-3 space-y-2">
        {actions.map((action) => {
          const sourceColor = GAP_SOURCE_COLORS[action.gap_source] || '#999999'
          const Icon = GAP_SOURCE_ICONS[action.gap_type] || GAP_SOURCE_ICONS[action.gap_source] || Sparkles
          const isFading = fadingIds.has(action.action_id)

          return (
            <div
              key={action.action_id}
              className={`
                border border-[#E5E5E5] rounded-xl bg-white overflow-hidden
                transition-all duration-500 shadow-sm hover:shadow-md
                ${isFading ? 'opacity-0 scale-95 -translate-y-2' : 'opacity-100'}
              `}
            >
              <div className="px-4 py-3">
                <div className="flex items-start gap-3">
                  <span
                    className="flex items-center justify-center w-5 h-5 rounded-full text-[11px] font-semibold flex-shrink-0 mt-0.5"
                    style={{
                      backgroundColor: sourceColor + '18',
                      color: sourceColor,
                    }}
                  >
                    {action.priority}
                  </span>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 mb-1">
                      <Icon className="w-3 h-3 flex-shrink-0" style={{ color: sourceColor }} />
                      <span
                        className="text-[10px] font-medium uppercase tracking-wide"
                        style={{ color: sourceColor }}
                      >
                        {action.gap_source}
                      </span>
                    </div>
                    <p className="text-[13px] text-[#333333] leading-relaxed">
                      {action.sentence}
                    </p>
                  </div>
                </div>

                <div className="mt-3 ml-8">
                  {cascadeResults[action.action_id] ? (
                    <div className="flex items-start gap-2 px-3 py-2 bg-[#E8F5E9] rounded-lg">
                      <Check className="w-3.5 h-3.5 text-[#25785A] flex-shrink-0 mt-0.5" />
                      <p className="text-[12px] text-[#25785A]">{cascadeResults[action.action_id]}</p>
                    </div>
                  ) : action.cta_type === 'inline_answer' ? (
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        value={answerInputs[action.action_id] ?? ''}
                        onChange={e =>
                          setAnswerInputs(prev => ({ ...prev, [action.action_id]: e.target.value }))
                        }
                        placeholder={action.question_placeholder || 'Type your answer...'}
                        className="flex-1 px-3 py-1.5 text-[12px] border border-[#E5E5E5] rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-[#3FAF7A] placeholder:text-[#CCCCCC]"
                        onKeyDown={e => {
                          if (e.key === 'Enter' && (answerInputs[action.action_id] ?? '').trim()) {
                            handleAnswer(action)
                          }
                        }}
                        disabled={submitting[action.action_id] ?? false}
                      />
                      <button
                        onClick={() => handleAnswer(action)}
                        disabled={(submitting[action.action_id] ?? false) || !(answerInputs[action.action_id] ?? '').trim()}
                        className="p-1.5 text-white bg-[#3FAF7A] hover:bg-[#25785A] rounded-lg disabled:opacity-40 transition-colors"
                      >
                        {submitting[action.action_id] ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Send className="w-3.5 h-3.5" />
                        )}
                      </button>
                    </div>
                  ) : action.cta_type === 'upload_doc' ? (
                    <button
                      onClick={() => onNavigate?.('signal', null)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-[#0A1E2F] bg-[#F0F0F0] hover:bg-[#E5E5E5] rounded-lg transition-colors"
                    >
                      <Upload className="w-3 h-3" />
                      {action.cta_label}
                    </button>
                  ) : (
                    <button
                      onClick={() => onDiscussInChat ? onDiscussInChat(action) : onNavigate?.('chat', null)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-[#3FAF7A] bg-[#E8F5E9] hover:bg-[#D4EDD9] rounded-lg transition-colors"
                    >
                      <MessageSquare className="w-3 h-3" />
                      {action.cta_label}
                    </button>
                  )}

                  {action.entity_type && action.entity_id && action.entity_type !== 'project' && (
                    <button
                      onClick={() => onNavigate?.(action.entity_type!, action.entity_id)}
                      className="mt-1.5 inline-flex items-center gap-1 text-[11px] text-[#3FAF7A] hover:underline"
                    >
                      <ArrowRight className="w-3 h-3" />
                      {action.entity_name || 'View entity'}
                    </button>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
