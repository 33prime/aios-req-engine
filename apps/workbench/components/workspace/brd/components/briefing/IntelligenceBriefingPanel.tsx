'use client'

import { useCallback, useRef } from 'react'
import { Loader2, Paperclip, Sparkles } from 'lucide-react'
import { useIntelligenceBriefing } from '@/lib/hooks/use-api'
import { PHASE_DESCRIPTIONS } from '@/lib/action-constants'
import type { ConversationStarter } from '@/types/workspace'

import { BriefingHeader } from './BriefingHeader'
import { ConversationStarterCard } from './ConversationStarterCard'

interface IntelligenceBriefingPanelProps {
  projectId: string
  onNavigate?: (entityType: string, entityId: string | null) => void
  onCascade?: () => void
  onStartConversation?: (starter: ConversationStarter) => void
  onUploadDocument?: () => void
}

/**
 * Render inline markdown: **bold** and *italic*
 */
function InlineMarkdown({ text }: { text: string }) {
  const parts: Array<{ content: string; style: 'normal' | 'bold' | 'italic' }> = []
  let remaining = text

  while (remaining.length > 0) {
    const boldMatch = remaining.match(/\*\*(.+?)\*\*/)
    const italicMatch = remaining.match(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/)

    const boldIdx = boldMatch?.index ?? Infinity
    const italicIdx = italicMatch?.index ?? Infinity

    if (boldIdx === Infinity && italicIdx === Infinity) {
      parts.push({ content: remaining, style: 'normal' })
      break
    }

    if (boldIdx <= italicIdx) {
      if (boldIdx > 0) parts.push({ content: remaining.slice(0, boldIdx), style: 'normal' })
      parts.push({ content: boldMatch![1], style: 'bold' })
      remaining = remaining.slice(boldIdx + boldMatch![0].length)
    } else {
      if (italicIdx > 0) parts.push({ content: remaining.slice(0, italicIdx), style: 'normal' })
      parts.push({ content: italicMatch![1], style: 'italic' })
      remaining = remaining.slice(italicIdx + italicMatch![0].length)
    }
  }

  return (
    <>
      {parts.map((p, i) => {
        if (p.style === 'bold') return <strong key={i} className="font-semibold">{p.content}</strong>
        if (p.style === 'italic') return <em key={i} className="italic">{p.content}</em>
        return <span key={i}>{p.content}</span>
      })}
    </>
  )
}

export function IntelligenceBriefingPanel({
  projectId,
  onNavigate,
  onCascade,
  onStartConversation,
  onUploadDocument,
}: IntelligenceBriefingPanelProps) {
  const {
    data: briefing,
    error: swrError,
    isLoading: loading,
    mutate: revalidate,
  } = useIntelligenceBriefing(projectId)

  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleRefresh = useCallback(() => {
    revalidate()
  }, [revalidate])

  const handleUploadClick = useCallback(() => {
    if (onUploadDocument) {
      onUploadDocument()
    } else {
      fileInputRef.current?.click()
    }
  }, [onUploadDocument])

  // Loading state
  if (loading && briefing === undefined) {
    return (
      <div className="flex flex-col h-full">
        <BriefingHeader phase={null} progress={0} />
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="flex items-center gap-2 text-[12px] text-[#999999]">
            <Loader2 className="w-4 h-4 animate-spin" />
            Preparing briefing...
          </div>
        </div>
      </div>
    )
  }

  // Error state
  if (swrError) {
    return (
      <div className="flex flex-col h-full">
        <BriefingHeader phase={null} progress={0} />
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center">
            <p className="text-[12px] text-[#999999]">Failed to load briefing</p>
            <button
              onClick={handleRefresh}
              className="mt-2 text-[11px] font-medium text-[#3FAF7A] hover:underline"
            >
              Try again
            </button>
          </div>
        </div>
      </div>
    )
  }

  const phase = briefing?.phase ?? 'empty'
  const progress = briefing?.situation?.phase_progress ?? 0
  const starters = briefing?.conversation_starters ?? []
  const narrative = briefing?.situation?.narrative ?? ''
  const hasContent = narrative || starters.length > 0

  return (
    <div className="flex flex-col h-full bg-white border-r border-[#E5E5E5]">
      <BriefingHeader
        phase={phase}
        progress={progress}
        narrativeCached={briefing?.narrative_cached}
        onRefresh={handleRefresh}
        loading={loading}
      />

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto">
        {!hasContent ? (
          <PhaseEmptyState phase={phase} onUpload={handleUploadClick} />
        ) : (
          <>
            {/* 2-sentence situation summary */}
            {narrative && (
              <p className="text-[13px] text-[#333333] leading-relaxed px-4 pt-4 pb-2">
                <InlineMarkdown text={narrative} />
              </p>
            )}

            {/* Conversation starter cards — each a different action type */}
            {starters.length > 0 && onStartConversation && (
              <div className="mt-2 mx-4 mb-3 rounded-xl border border-[#E5E5E5] overflow-hidden bg-white">
                {starters.map((starter) => (
                  <ConversationStarterCard
                    key={starter.starter_id}
                    starter={starter}
                    onStartConversation={onStartConversation}
                  />
                ))}
              </div>
            )}

            {/* Upload document row */}
            <div className="px-4 pb-4">
              <button
                onClick={handleUploadClick}
                className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-[13px] text-[#666666] hover:text-[#333333] hover:bg-[#F8F8F8] transition-colors"
              >
                <Paperclip className="w-4 h-4 flex-shrink-0" />
                Upload a document
              </button>
            </div>
          </>
        )}
      </div>

      {/* Hidden file input fallback */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.docx,.xlsx,.pptx,.png,.jpg,.jpeg,.webp,.gif"
        className="hidden"
      />
    </div>
  )
}

function PhaseEmptyState({ phase, onUpload }: { phase: string; onUpload: () => void }) {
  const description = PHASE_DESCRIPTIONS[phase] || 'No intelligence available yet'

  return (
    <div className="p-6 text-center">
      <Sparkles className="w-8 h-8 text-[#3FAF7A] mx-auto mb-3 opacity-50" />
      <p className="text-[13px] font-medium text-[#333333]">
        {phase === 'refining' ? 'Looking good' : 'Ready when you are'}
      </p>
      <p className="text-[12px] text-[#999999] mt-1 mb-4">{description}</p>
      <button
        onClick={onUpload}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-[12px] font-medium text-[#3FAF7A] border border-[#3FAF7A] hover:bg-[#E8F5E9] transition-colors"
      >
        <Paperclip className="w-3.5 h-3.5" />
        Upload a document
      </button>
    </div>
  )
}
