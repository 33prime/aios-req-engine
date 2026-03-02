'use client'

/**
 * ReviewBubble — Unified floating side panel for the workspace.
 *
 * Two modes:
 * - **Briefing mode** (default): Briefing | Chat tabs
 * - **Review mode**: Review | Chat tabs (when session + epicPlan + epicCardIndex provided)
 *
 * Mode is auto-detected from the presence of review-specific props.
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { Info, MessageSquare, X, Zap, FileText, Loader2, Plus } from 'lucide-react'
import { WorkspaceChat, type ChatMessage } from '@/components/workspace/WorkspaceChat'
import { IntelligenceBriefingPanel } from '@/components/workspace/brd/components/briefing/IntelligenceBriefingPanel'
import { ClientPulseStrip } from '@/components/workspace/ClientPulseStrip'
import ReviewInfoPanel from './ReviewInfoPanel'
import type { PrototypeSession } from '@/types/prototype'
import type { EpicOverlayPlan, EpicTourPhase, EpicConfirmation } from '@/types/epic-overlay'
import type { ChatEntityDetectionResult, TerseAction } from '@/lib/api'
import type { ConversationStarter } from '@/types/workspace'

export const SIDE_PANEL_WIDTH = 420
/** @deprecated Use SIDE_PANEL_WIDTH */
export const BRAIN_PANEL_WIDTH = SIDE_PANEL_WIDTH
/** @deprecated Use SIDE_PANEL_WIDTH */
export const REVIEW_PANEL_WIDTH = SIDE_PANEL_WIDTH

type PanelTab = 'primary' | 'chat'

interface ReviewBubbleProps {
  projectId: string

  // Chat props (always required)
  messages: ChatMessage[]
  isChatLoading: boolean
  onSendMessage: (content: string) => Promise<void> | void
  onSendSignal?: (type: string, content: string, source: string) => Promise<void>
  onAddLocalMessage?: (msg: ChatMessage) => void
  onOpenChange: (isOpen: boolean) => void

  // Briefing mode props
  actionCount?: number
  onCascade?: () => void
  contextActions?: TerseAction[]
  onNewChat?: () => void
  onSetConversationContext?: (context: string) => void
  onNavigateToCollaborate?: () => void
  hideClientPulse?: boolean

  // Entity detection
  entityDetection?: ChatEntityDetectionResult | null
  isSavingAsSignal?: boolean
  onSaveAsSignal?: () => Promise<void>
  onDismissDetection?: () => void

  // Review mode props (optional — triggers review mode when all present)
  session?: PrototypeSession
  epicPlan?: EpicOverlayPlan
  epicPhase?: EpicTourPhase
  epicCardIndex?: number | null
  epicConfirmations?: EpicConfirmation[]
  onEpicAdvance?: () => void
}

export function ReviewBubble({
  projectId,
  messages,
  isChatLoading,
  onSendMessage,
  onSendSignal,
  onAddLocalMessage,
  onOpenChange,
  // Briefing
  actionCount = 0,
  onCascade,
  contextActions,
  onNewChat,
  onSetConversationContext,
  onNavigateToCollaborate,
  hideClientPulse,
  // Entity detection
  entityDetection,
  isSavingAsSignal,
  onSaveAsSignal,
  onDismissDetection,
  // Review
  session,
  epicPlan,
  epicPhase = 'vision_journey',
  epicCardIndex,
  epicConfirmations = [],
  onEpicAdvance,
}: ReviewBubbleProps) {
  const isReviewMode = !!(session && epicPlan && epicCardIndex != null)

  const [isOpen, setIsOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<PanelTab>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('side-panel-tab')
      if (stored === 'chat') return 'chat'
    }
    return 'primary'
  })
  const panelRef = useRef<HTMLDivElement>(null)

  const updateOpen = useCallback(
    (open: boolean) => {
      setIsOpen(open)
      onOpenChange(open)
    },
    [onOpenChange]
  )

  // Auto-open panel when entering review mode
  const prevReviewMode = useRef(isReviewMode)
  useEffect(() => {
    if (isReviewMode && !prevReviewMode.current) {
      updateOpen(true)
      setActiveTab('primary')
    }
    prevReviewMode.current = isReviewMode
  }, [isReviewMode, updateOpen])

  // Persist tab preference
  useEffect(() => {
    localStorage.setItem('side-panel-tab', activeTab)
  }, [activeTab])

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

  // Handle "entity chat" navigation from briefing panel
  const handleNavigate = useCallback(
    (entityType: string, _entityId: string | null) => {
      if (entityType === 'chat') {
        setActiveTab('chat')
      }
    },
    []
  )

  // Handle conversation starter → chat with context injection
  const handleStartConversation = useCallback(
    (starter: ConversationStarter) => {
      setActiveTab('chat')
      if (!isOpen) updateOpen(true)
      if (starter.chat_context) {
        onSetConversationContext?.(starter.chat_context)
      }
      setTimeout(() => {
        onSendMessage(starter.question)
      }, 100)
    },
    [isOpen, updateOpen, onSendMessage, onSetConversationContext]
  )

  // Handle "Upload a document" → switch to chat tab and trigger file input
  const handleUploadDocument = useCallback(() => {
    setActiveTab('chat')
    if (!isOpen) updateOpen(true)
    setTimeout(() => {
      const chatFileInput = document.querySelector<HTMLInputElement>(
        '#workspace-chat-file-input'
      )
      chatFileInput?.click()
    }, 150)
  }, [isOpen, updateOpen])

  // Review mode: phase-specific confirmed count for badge
  const phaseConfirmed = isReviewMode
    ? epicConfirmations.filter((c) => {
        const phaseMap: Record<EpicTourPhase, string> = {
          vision_journey: 'vision',
          ai_deep_dive: 'ai_flow',
          horizons: 'horizon',
          discovery: 'discovery',
        }
        return c.card_type === phaseMap[epicPhase] && c.verdict
      }).length
    : 0

  // Bubble badge count and icon
  const badgeCount = isReviewMode ? phaseConfirmed : actionCount
  const BubbleIcon = isReviewMode ? Info : MessageSquare

  return (
    <>
      {/* Floating bubble — only when panel is closed */}
      {!isOpen && (
        <button
          id="brain-bubble-trigger"
          onClick={() => updateOpen(true)}
          className="fixed bottom-6 right-6 z-50 w-12 h-12 rounded-full bg-[#0A1E2F] hover:bg-[#0D2A35] shadow-lg hover:shadow-xl flex items-center justify-center transition-all duration-200"
          title="Open assistant (⌘J)"
        >
          <BubbleIcon className="w-5 h-5 text-brand-primary" />
          {badgeCount > 0 && (
            <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 flex items-center justify-center rounded-full bg-brand-primary text-white text-[10px] font-bold">
              {badgeCount > 9 ? '9+' : badgeCount}
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
        style={{ width: SIDE_PANEL_WIDTH }}
      >
        {/* Tab header */}
        <div className="px-3 py-2.5 border-b border-border flex-shrink-0">
          <div className="flex items-center gap-2">
            <div className="flex-1 flex items-center bg-[#F4F4F4] rounded-xl p-1">
              <button
                onClick={() => setActiveTab('primary')}
                className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all duration-150 ${
                  activeTab === 'primary'
                    ? 'bg-white text-[#0A1E2F] shadow-sm'
                    : 'text-[#666666] hover:text-text-body'
                }`}
              >
                {isReviewMode ? (
                  <>
                    <Info className="w-3.5 h-3.5" />
                    Review
                  </>
                ) : (
                  <>
                    <Zap className="w-3.5 h-3.5" />
                    Briefing
                    {actionCount > 0 && (
                      <span className="ml-1 min-w-[16px] h-[16px] px-1 flex items-center justify-center rounded-full bg-brand-primary text-white text-[9px] font-bold">
                        {actionCount}
                      </span>
                    )}
                  </>
                )}
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

            {/* New Chat button — only in chat tab with messages */}
            {activeTab === 'chat' && messages.length > 0 && onNewChat && (
              <button
                onClick={onNewChat}
                className="p-1.5 rounded-lg hover:bg-[#F4F4F4] transition-colors"
                title="New conversation"
              >
                <Plus className="w-4 h-4 text-[#666666]" />
              </button>
            )}

            {/* Close */}
            <button
              onClick={() => updateOpen(false)}
              className="p-1.5 rounded-lg text-text-placeholder hover:bg-[#F4F4F4] hover:text-[#666666] transition-colors"
              title="Close (Esc)"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Client Pulse Strip — briefing mode only, hidden on Collaborate */}
        {!isReviewMode && !hideClientPulse && (
          <ClientPulseStrip projectId={projectId} onClick={onNavigateToCollaborate} />
        )}

        {/* Content */}
        <div className="flex-1 overflow-hidden relative">
          {activeTab === 'primary' ? (
            isReviewMode ? (
              epicCardIndex != null ? (
                <div className="h-full overflow-y-auto">
                  <ReviewInfoPanel
                    epicPlan={epicPlan!}
                    epicPhase={epicPhase}
                    epicCardIndex={epicCardIndex}
                    sessionId={session!.id}
                    confirmations={epicConfirmations}
                    onAdvance={onEpicAdvance ?? (() => {})}
                  />
                </div>
              ) : (
                <div className="p-6 text-center">
                  <p className="text-[13px] text-[#666666]">
                    Start the tour to review epics
                  </p>
                </div>
              )
            ) : (
              <IntelligenceBriefingPanel
                projectId={projectId}
                onNavigate={handleNavigate}
                onCascade={onCascade}
                onStartConversation={handleStartConversation}
                onUploadDocument={handleUploadDocument}
              />
            )
          ) : (
            <WorkspaceChat
              projectId={projectId}
              messages={messages}
              isLoading={isChatLoading}
              onSendMessage={onSendMessage}
              onSendSignal={onSendSignal}
              onAddLocalMessage={onAddLocalMessage}
              contextActions={!isReviewMode ? contextActions : undefined}
            />
          )}

          {/* Chat-as-Signal Detection Card */}
          {activeTab === 'chat' && entityDetection && entityDetection.should_extract && (
            <div className="absolute bottom-2 left-2 right-2 z-10">
              <div className="bg-white border border-border rounded-xl shadow-lg p-3">
                <div className="flex items-start gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-[#E8F5E9] flex items-center justify-center flex-shrink-0">
                    <FileText className="w-4 h-4 text-[#25785A]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[12px] font-medium text-text-body">
                      Found requirements in our chat
                    </p>
                    <p className="text-[11px] text-[#666666] mt-0.5">
                      {entityDetection.entity_count} entities:{' '}
                      {entityDetection.entity_hints
                        .slice(0, 3)
                        .map((h) => h.name)
                        .join(', ')}
                      {entityDetection.entity_hints.length > 3 &&
                        ` +${entityDetection.entity_hints.length - 3} more`}
                    </p>
                    <div className="flex items-center gap-2 mt-2">
                      <button
                        onClick={onSaveAsSignal}
                        disabled={isSavingAsSignal}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-medium text-white bg-brand-primary hover:bg-[#25785A] rounded-lg transition-colors disabled:opacity-50"
                      >
                        {isSavingAsSignal ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                          <FileText className="w-3 h-3" />
                        )}
                        {isSavingAsSignal ? 'Saving...' : 'Save as Requirements'}
                      </button>
                      <button
                        onClick={onDismissDetection}
                        className="px-3 py-1.5 text-[11px] font-medium text-[#666666] hover:text-text-body transition-colors"
                      >
                        Keep Going
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  )
}

export default ReviewBubble
