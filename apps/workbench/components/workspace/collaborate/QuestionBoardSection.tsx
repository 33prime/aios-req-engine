'use client'

import { useState } from 'react'
import { MessageCircle, ChevronDown, ChevronRight, Edit3, Send } from 'lucide-react'
import { useCollaborationCurrent } from '@/lib/hooks/use-api'
import { generateClientPackage, sendClientPackage } from '@/lib/api'
import type { ClientPackage } from '@/types/api'

interface QuestionBoardSectionProps {
  projectId: string
}

export function QuestionBoardSection({ projectId }: QuestionBoardSectionProps) {
  const [isOpen, setIsOpen] = useState(true)
  const { data: collab } = useCollaborationCurrent(projectId)
  const [isSynthesizing, setIsSynthesizing] = useState(false)
  const [draftPackage, setDraftPackage] = useState<ClientPackage | null>(null)

  const questions = collab?.portal_sync?.questions
  const draftCount = questions?.pending ?? 0
  const sentCount = questions?.in_progress ?? 0
  const answeredCount = questions?.completed ?? 0
  const totalCount = draftCount + sentCount + answeredCount

  const handleSynthesize = async () => {
    setIsSynthesizing(true)
    try {
      const result = await generateClientPackage(projectId, {
        include_asset_suggestions: true,
        max_questions: 10,
      })
      setDraftPackage(result.package)
    } catch (err) {
      console.error('Failed to synthesize:', err)
    } finally {
      setIsSynthesizing(false)
    }
  }

  const handleSendPackage = async () => {
    if (!draftPackage) return
    try {
      await sendClientPackage(draftPackage.id)
      setDraftPackage(null)
    } catch (err) {
      console.error('Failed to send package:', err)
    }
  }

  const columns = [
    { label: 'DRAFT', count: draftCount, status: 'draft' as const },
    { label: 'SENT', count: sentCount, status: 'sent' as const },
    { label: 'ANSWERED', count: answeredCount, status: 'answered' as const },
  ]

  const statusStyles = {
    draft: 'bg-[#F4F4F4] text-[#666666]',
    sent: 'bg-[#0A1E2F]/10 text-[#0A1E2F]',
    answered: 'bg-[#3FAF7A]/10 text-[#25785A]',
  }

  return (
    <div className="bg-white rounded-2xl border border-[#E5E5E5] shadow-[0_1px_2px_rgba(0,0,0,0.04)] overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-[#FAFAFA] transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <MessageCircle className="w-4 h-4 text-[#3FAF7A]" />
          <span className="text-[11px] uppercase tracking-wider text-[#999999] font-semibold">
            Question Board
          </span>
          {totalCount > 0 && (
            <span className="px-1.5 py-0.5 bg-[#3FAF7A]/10 text-[#25785A] text-[10px] font-bold rounded-full min-w-[18px] text-center">
              {totalCount}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isOpen && (
            <button
              onClick={(e) => { e.stopPropagation(); handleSynthesize() }}
              disabled={isSynthesizing}
              className="bg-[#3FAF7A] text-white rounded-xl px-4 py-1.5 text-[12px] font-medium hover:bg-[#25785A] transition-colors disabled:opacity-50"
            >
              {isSynthesizing ? 'Synthesizing...' : 'Synthesize'}
            </button>
          )}
          {isOpen ? <ChevronDown className="w-4 h-4 text-[#999999]" /> : <ChevronRight className="w-4 h-4 text-[#999999]" />}
        </div>
      </button>

      {isOpen && (
        <div className="px-5 pb-4">
          {/* 3-column status flow */}
          <div className="grid grid-cols-3 gap-3">
            {columns.map(col => (
              <div key={col.status}>
                <p className="text-[11px] uppercase tracking-wider text-[#999999] font-semibold mb-2">
                  {col.label}
                </p>
                {col.count > 0 ? (
                  <div className="rounded-xl border border-[#E5E5E5] p-3 bg-white">
                    <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-medium ${statusStyles[col.status]}`}>
                      {col.count} question{col.count > 1 ? 's' : ''}
                    </span>
                    <p className="text-[11px] text-[#999999] mt-1.5">
                      {col.status === 'draft' && 'Ready to review & send'}
                      {col.status === 'sent' && 'Awaiting client response'}
                      {col.status === 'answered' && 'All answered'}
                    </p>
                  </div>
                ) : (
                  <div className="rounded-xl border border-dashed border-[#E5E5E5] p-3 text-center">
                    <p className="text-[11px] text-[#CCCCCC]">None</p>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Draft package preview */}
          {draftPackage && (
            <div className="mt-4 rounded-xl border border-[#3FAF7A]/30 bg-[#3FAF7A]/5 p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[12px] font-medium text-[#333333]">Draft Package</span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setDraftPackage(null)}
                    className="text-[11px] text-[#666666] hover:text-[#333333] flex items-center gap-1"
                  >
                    <Edit3 className="w-3 h-3" />
                    Edit
                  </button>
                  <button
                    onClick={handleSendPackage}
                    className="text-[11px] font-medium text-[#3FAF7A] hover:text-[#25785A] flex items-center gap-1"
                  >
                    <Send className="w-3 h-3" />
                    Send
                  </button>
                </div>
              </div>
              <p className="text-[11px] text-[#666666]">
                {draftPackage.questions?.length ?? 0} questions synthesized
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
