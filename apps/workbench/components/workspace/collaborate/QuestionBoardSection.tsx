'use client'

import { useState, useEffect } from 'react'
import { Package, ChevronDown, ChevronRight, Sparkles, Send, X, CheckCircle, Clock, MessageCircle, Loader2 } from 'lucide-react'
import { usePendingItems, useCollaborationCurrent } from '@/lib/hooks/use-api'
import { generateClientPackage, sendClientPackage, removePendingItem } from '@/lib/api'
import type { ClientPackage } from '@/types/api'

interface QuestionBoardSectionProps {
  projectId: string
  synthesizeTrigger?: number
}

export function QuestionBoardSection({ projectId, synthesizeTrigger }: QuestionBoardSectionProps) {
  const [isOpen, setIsOpen] = useState(true)
  const { data: pending, mutate: mutatePending } = usePendingItems(projectId)
  const { data: collab, mutate: mutateCollab } = useCollaborationCurrent(projectId)
  const [isSynthesizing, setIsSynthesizing] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [draftPackage, setDraftPackage] = useState<ClientPackage | null>(null)
  const [error, setError] = useState<string | null>(null)

  const items = pending?.items ?? []
  const answeredCount = collab?.portal_sync?.questions?.completed ?? 0
  const sentCount = collab?.portal_sync?.questions?.in_progress ?? 0

  // External trigger to synthesize (from Action Queue)
  useEffect(() => {
    if (synthesizeTrigger && synthesizeTrigger > 0 && items.length > 0 && !isSynthesizing && !draftPackage) {
      handleSynthesize()
    }
  }, [synthesizeTrigger])

  const handleSynthesize = async () => {
    setIsSynthesizing(true)
    setError(null)
    try {
      const result = await generateClientPackage(projectId, {
        include_asset_suggestions: true,
        max_questions: 10,
      })
      setDraftPackage(result.package)
    } catch (err) {
      setError('Failed to synthesize package')
      console.error('Failed to synthesize:', err)
    } finally {
      setIsSynthesizing(false)
    }
  }

  const handleSendPackage = async () => {
    if (!draftPackage) return
    setIsSending(true)
    setError(null)
    try {
      await sendClientPackage(draftPackage.id)
      setDraftPackage(null)
      mutatePending()
      mutateCollab()
    } catch (err) {
      setError('Failed to send package')
      console.error('Failed to send package:', err)
    } finally {
      setIsSending(false)
    }
  }

  const handleRemoveItem = async (itemId: string) => {
    try {
      await removePendingItem(itemId)
      mutatePending()
    } catch (err) {
      console.error('Failed to remove item:', err)
    }
  }

  const totalBadge = items.length + (draftPackage ? 1 : 0)

  const typeLabel = (type: string) => {
    const labels: Record<string, string> = {
      feature: 'Feature', persona: 'Persona', vp_step: 'Value Path',
      question: 'Question', goal: 'Goal', kpi: 'KPI', pain_point: 'Pain Point',
      stakeholder: 'Stakeholder', workflow: 'Workflow', data_entity: 'Data Entity',
      constraint: 'Constraint', competitor: 'Competitor', document: 'Document',
    }
    return labels[type] || type
  }

  return (
    <div className="bg-white rounded-2xl border border-[#E5E5E5] shadow-[0_1px_2px_rgba(0,0,0,0.04)] overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-[#FAFAFA] transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <Package className="w-4 h-4 text-[#3FAF7A]" />
          <span className="text-[11px] uppercase tracking-wider text-[#999999] font-semibold">
            Portal Pipeline
          </span>
          {totalBadge > 0 && (
            <span className="px-1.5 py-0.5 bg-[#3FAF7A]/10 text-[#25785A] text-[10px] font-bold rounded-full min-w-[18px] text-center">
              {totalBadge}
            </span>
          )}
        </div>
        {isOpen ? <ChevronDown className="w-4 h-4 text-[#999999]" /> : <ChevronRight className="w-4 h-4 text-[#999999]" />}
      </button>

      {isOpen && (
        <div className="px-5 pb-4 space-y-4">
          {error && (
            <p className="text-[12px] text-red-500 bg-red-50 rounded-lg px-3 py-2">{error}</p>
          )}

          {/* Pending Items Queue */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-[11px] uppercase tracking-wider text-[#999999] font-semibold">
                Pending Items ({items.length})
              </p>
              {items.length > 0 && !draftPackage && (
                <button
                  onClick={handleSynthesize}
                  disabled={isSynthesizing}
                  className="bg-[#3FAF7A] text-white rounded-lg px-3 py-1.5 text-[12px] font-medium hover:bg-[#25785A] transition-colors disabled:opacity-50 flex items-center gap-1.5"
                >
                  {isSynthesizing ? (
                    <>
                      <Loader2 className="w-3 h-3 animate-spin" />
                      Synthesizing...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-3 h-3" />
                      Package for Client
                    </>
                  )}
                </button>
              )}
            </div>

            {items.length === 0 ? (
              <div className="rounded-xl border border-dashed border-[#E5E5E5] p-4 text-center">
                <Package className="w-6 h-6 mx-auto mb-1.5 text-[#E5E5E5]" />
                <p className="text-[12px] text-[#999999]">No pending items</p>
                <p className="text-[11px] text-[#CCCCCC] mt-0.5">
                  Mark entities for client review from the BRD canvas or chat
                </p>
              </div>
            ) : (
              <div className="space-y-1.5">
                {items.map(item => (
                  <div
                    key={item.id}
                    className="flex items-center justify-between gap-2 rounded-lg bg-[#F9F9F9] px-3 py-2 group"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-[#0A1E2F]/8 text-[#0A1E2F] flex-shrink-0">
                        {typeLabel(item.item_type)}
                      </span>
                      <span className="text-[13px] text-[#333333] truncate">{item.title}</span>
                    </div>
                    <button
                      onClick={() => handleRemoveItem(item.id)}
                      className="text-[#CCCCCC] hover:text-[#999999] opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Draft Package */}
          {draftPackage && (
            <div className="rounded-xl border border-[#3FAF7A]/30 bg-[#3FAF7A]/5 p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-[#3FAF7A]" />
                  <span className="text-[13px] font-medium text-[#333333]">
                    Draft Package — {draftPackage.questions?.length ?? 0} questions
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setDraftPackage(null)}
                    className="text-[12px] text-[#666666] hover:text-[#333333] px-2 py-1 rounded-lg hover:bg-white/50 transition-colors"
                  >
                    Discard
                  </button>
                  <button
                    onClick={handleSendPackage}
                    disabled={isSending}
                    className="bg-[#3FAF7A] text-white rounded-lg px-3 py-1.5 text-[12px] font-medium hover:bg-[#25785A] transition-colors disabled:opacity-50 flex items-center gap-1.5"
                  >
                    {isSending ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      <Send className="w-3 h-3" />
                    )}
                    Send to Client
                  </button>
                </div>
              </div>

              {/* Question preview */}
              <div className="space-y-2">
                {(draftPackage.questions ?? []).slice(0, 5).map((q, i) => (
                  <div key={q.id || i} className="bg-white/60 rounded-lg px-3 py-2">
                    <p className="text-[13px] text-[#333333]">{q.question_text}</p>
                    {q.why_asking && (
                      <p className="text-[11px] text-[#999999] mt-1">{q.why_asking}</p>
                    )}
                  </div>
                ))}
                {(draftPackage.questions?.length ?? 0) > 5 && (
                  <p className="text-[11px] text-[#999999] text-center">
                    +{(draftPackage.questions?.length ?? 0) - 5} more questions
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Status Summary (sent / answered) */}
          {(sentCount > 0 || answeredCount > 0) && (
            <div className="flex items-center gap-4 pt-1">
              {sentCount > 0 && (
                <div className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-[#0A1E2F]" />
                  <span className="text-[12px] text-[#666666]">
                    {sentCount} sent, awaiting response
                  </span>
                </div>
              )}
              {answeredCount > 0 && (
                <div className="flex items-center gap-1.5">
                  <CheckCircle className="w-3.5 h-3.5 text-[#3FAF7A]" />
                  <span className="text-[12px] text-[#666666]">
                    {answeredCount} answered
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
