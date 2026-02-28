'use client'

/**
 * ReviewBubble — Floating chat-icon panel for review mode.
 *
 * Like BrainBubble in Discovery: a floating button that opens a slide-in panel.
 * When closed, the prototype gets full width. When open, content compresses.
 *
 * Two tabs: Info (epic confirmation) | Chat (contextual discussion)
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { Info, MessageSquare, X } from 'lucide-react'
import { WorkspaceChat, type ChatMessage } from '@/components/workspace/WorkspaceChat'
import ReviewInfoPanel from './ReviewInfoPanel'
import type { PrototypeSession } from '@/types/prototype'
import type { EpicOverlayPlan, EpicTourPhase, EpicConfirmation } from '@/types/epic-overlay'

export const REVIEW_PANEL_WIDTH = 400

type ReviewTab = 'info' | 'chat'

interface ReviewBubbleProps {
  projectId: string
  // Session + epic state
  session: PrototypeSession
  epicPlan: EpicOverlayPlan
  epicPhase: EpicTourPhase
  epicCardIndex: number | null
  epicConfirmations: EpicConfirmation[]
  onEpicAdvance: () => void
  // Chat props
  messages: ChatMessage[]
  isChatLoading: boolean
  onSendMessage: (content: string) => Promise<void> | void
  onSendSignal?: (type: string, content: string, source: string) => Promise<void>
  onAddLocalMessage?: (msg: ChatMessage) => void
  // Open state — parent controls width
  onOpenChange: (isOpen: boolean) => void
}

export function ReviewBubble({
  projectId,
  session,
  epicPlan,
  epicPhase,
  epicCardIndex,
  epicConfirmations,
  onEpicAdvance,
  messages,
  isChatLoading,
  onSendMessage,
  onSendSignal,
  onAddLocalMessage,
  onOpenChange,
}: ReviewBubbleProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<ReviewTab>('info')
  const panelRef = useRef<HTMLDivElement>(null)

  const updateOpen = useCallback(
    (open: boolean) => {
      setIsOpen(open)
      onOpenChange(open)
    },
    [onOpenChange]
  )

  // Keyboard: Escape to close, Cmd+J to toggle
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        updateOpen(false)
      }
      if ((e.metaKey || e.ctrlKey) && e.key === 'j') {
        e.preventDefault()
        updateOpen(!isOpen)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, updateOpen])

  // Phase-specific confirmed count for badge
  const phaseConfirmed = epicConfirmations.filter((c) => {
    const phaseMap: Record<EpicTourPhase, string> = {
      vision_journey: 'vision',
      ai_deep_dive: 'ai_flow',
      horizons: 'horizon',
      discovery: 'discovery',
    }
    return c.card_type === phaseMap[epicPhase] && c.verdict
  }).length

  return (
    <>
      {/* Floating bubble — only when panel is closed */}
      {!isOpen && (
        <button
          onClick={() => updateOpen(true)}
          className="fixed bottom-6 right-6 z-50 w-12 h-12 rounded-full bg-[#0A1E2F] hover:bg-[#0D2A35] shadow-lg hover:shadow-xl flex items-center justify-center transition-all duration-200"
          title="Open review panel (⌘J)"
        >
          <Info className="w-5 h-5 text-brand-primary" />
          {phaseConfirmed > 0 && (
            <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 flex items-center justify-center rounded-full bg-brand-primary text-white text-[10px] font-bold">
              {phaseConfirmed}
            </span>
          )}
        </button>
      )}

      {/* Slide-in panel */}
      <div
        ref={panelRef}
        className={`fixed top-0 right-0 h-screen z-40 bg-white border-l border-border shadow-2xl flex flex-col transition-all duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
        style={{ width: REVIEW_PANEL_WIDTH }}
      >
        {/* Tab header */}
        <div className="px-3 py-2.5 border-b border-border flex-shrink-0">
          <div className="flex items-center gap-2">
            <div className="flex-1 flex items-center bg-[#F4F4F4] rounded-xl p-1">
              <button
                onClick={() => setActiveTab('info')}
                className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all duration-150 ${
                  activeTab === 'info'
                    ? 'bg-white text-[#0A1E2F] shadow-sm'
                    : 'text-[#666666] hover:text-text-body'
                }`}
              >
                <Info className="w-3.5 h-3.5" />
                Review
              </button>
              <button
                onClick={() => setActiveTab('chat')}
                className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all duration-150 ${
                  activeTab === 'chat'
                    ? 'bg-white text-[#0A1E2F] shadow-sm'
                    : 'text-[#666666] hover:text-text-body'
                }`}
              >
                <MessageSquare className="w-3.5 h-3.5" />
                Chat
              </button>
            </div>
            <button
              onClick={() => updateOpen(false)}
              className="p-1.5 rounded-lg text-text-placeholder hover:bg-[#F4F4F4] hover:text-[#666666] transition-colors"
              title="Close (Esc)"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden relative">
          {activeTab === 'info' && epicCardIndex != null ? (
            <div className="h-full overflow-y-auto">
              <ReviewInfoPanel
                epicPlan={epicPlan}
                epicPhase={epicPhase}
                epicCardIndex={epicCardIndex}
                sessionId={session.id}
                confirmations={epicConfirmations}
                onAdvance={onEpicAdvance}
              />
            </div>
          ) : activeTab === 'info' ? (
            <div className="p-6 text-center">
              <p className="text-[13px] text-[#666666]">Start the tour to review epics</p>
            </div>
          ) : (
            <WorkspaceChat
              projectId={projectId}
              messages={messages}
              isLoading={isChatLoading}
              onSendMessage={onSendMessage}
              onSendSignal={onSendSignal}
              onAddLocalMessage={onAddLocalMessage}
            />
          )}
        </div>
      </div>
    </>
  )
}

export default ReviewBubble
