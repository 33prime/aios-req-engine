'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { MessageSquare, X, Zap, FileText, Loader2, Plus } from 'lucide-react'
import type { ChatMessage } from './WorkspaceChat'
import { WorkspaceChat } from './WorkspaceChat'
import { IntelligenceBriefingPanel } from './brd/components/briefing/IntelligenceBriefingPanel'
import { ClientPulseStrip } from './ClientPulseStrip'
import type { ChatEntityDetectionResult, TerseAction } from '@/lib/api'
import type { ConversationStarter } from '@/types/workspace'

// =============================================================================
// Types
// =============================================================================

type BrainTab = 'actions' | 'chat'

interface BrainBubbleProps {
  projectId: string
  /** Action count for badge */
  actionCount?: number
  /** Whether Haiku has a new proactive nudge */
  hasNewInsight?: boolean

  // Chat props
  messages: ChatMessage[]
  isChatLoading: boolean
  onSendMessage: (content: string) => Promise<void> | void
  onSendSignal?: (type: string, content: string, source: string) => Promise<void>
  onAddLocalMessage?: (msg: ChatMessage) => void

  // Action props
  onNavigate?: (entityType: string, entityId: string | null) => void
  onCascade?: () => void

  // Chat-as-signal
  entityDetection?: ChatEntityDetectionResult | null
  isSavingAsSignal?: boolean
  onSaveAsSignal?: () => Promise<void>
  onDismissDetection?: () => void

  /** Pre-select a tab when opening */
  defaultTab?: BrainTab

  /** Notify parent of open state changes (for BRD compression) */
  onOpenChange?: (isOpen: boolean) => void

  /** Context frame actions for dynamic starter cards */
  contextActions?: TerseAction[]

  /** Start a new chat conversation */
  onNewChat?: () => void

  /** Set conversation context for next chat message */
  onSetConversationContext?: (context: string) => void

  /** Navigate to the Collaborate view */
  onNavigateToCollaborate?: () => void

  /** Hide the pulse strip (e.g., when already on Collaborate) */
  hideClientPulse?: boolean
}

// Panel width constant — shared with WorkspaceLayout for margin calculation
export const BRAIN_PANEL_WIDTH = 475

// =============================================================================
// BrainBubble — floating button + side panel that compresses BRD
// =============================================================================

export function BrainBubble({
  projectId,
  actionCount = 0,
  hasNewInsight = false,
  messages,
  isChatLoading,
  onSendMessage,
  onSendSignal,
  onAddLocalMessage,
  onNavigate,
  onCascade,
  entityDetection,
  isSavingAsSignal,
  onSaveAsSignal,
  onDismissDetection,
  defaultTab,
  onOpenChange,
  contextActions,
  onNewChat,
  onSetConversationContext,
  onNavigateToCollaborate,
  hideClientPulse,
}: BrainBubbleProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<BrainTab>(() => {
    if (typeof window !== 'undefined') {
      return (localStorage.getItem('brain-panel-tab') as BrainTab) || 'actions'
    }
    return 'actions'
  })
  const panelRef = useRef<HTMLDivElement>(null)

  // Notify parent of open state changes
  const updateOpen = useCallback((open: boolean) => {
    setIsOpen(open)
    onOpenChange?.(open)
  }, [onOpenChange])

  // Persist tab preference
  useEffect(() => {
    localStorage.setItem('brain-panel-tab', activeTab)
  }, [activeTab])

  // Apply default tab when it changes (e.g., "Discuss in chat →" CTA)
  useEffect(() => {
    if (defaultTab) {
      setActiveTab(defaultTab)
      updateOpen(true)
    }
  }, [defaultTab, updateOpen])

  // Keyboard shortcuts: Escape to close, Cmd+J to toggle
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

  // Handle "Discuss in chat →" from action cards (legacy — switches tab only)
  const handleNavigate = useCallback((entityType: string, entityId: string | null) => {
    if (entityType === 'chat') {
      setActiveTab('chat')
      return
    }
    // Forward navigation to parent
    onNavigate?.(entityType, entityId)
  }, [onNavigate])

  // Handle "Discuss in chat" with full context injection
  const handleDiscussInChat = useCallback((action: import('@/lib/api').TerseAction) => {
    // 1. Switch to chat tab
    setActiveTab('chat')
    // 2. Open panel if closed
    if (!isOpen) updateOpen(true)
    // 3. Auto-send a contextual message
    const entityContext = action.entity_name ? ` (${action.entity_name})` : ''
    const message = `Let's discuss: ${action.sentence}${entityContext}`
    // Small delay to allow tab switch to render before sending
    setTimeout(() => {
      onSendMessage(message)
    }, 100)
  }, [isOpen, updateOpen, onSendMessage])

  // Handle "Upload a document" from briefing panel → switch to chat tab (which has file upload)
  const handleUploadDocument = useCallback(() => {
    setActiveTab('chat')
    if (!isOpen) updateOpen(true)
    // Trigger the file input in WorkspaceChat after tab switch renders
    setTimeout(() => {
      const chatFileInput = document.querySelector<HTMLInputElement>('#workspace-chat-file-input')
      chatFileInput?.click()
    }, 150)
  }, [isOpen, updateOpen])

  // Handle conversation starter → chat with context injection
  const handleStartConversation = useCallback((starter: ConversationStarter) => {
    // 1. Switch to chat tab
    setActiveTab('chat')
    // 2. Open panel if closed
    if (!isOpen) updateOpen(true)
    // 3. Store conversation context for the next message
    if (starter.chat_context) {
      onSetConversationContext?.(starter.chat_context)
    }
    // 4. Send the starter's question as the first user message
    setTimeout(() => {
      onSendMessage(starter.question)
    }, 100)
  }, [isOpen, updateOpen, onSendMessage, onSetConversationContext])

  return (
    <>
      {/* Floating Bubble — only visible when panel is closed */}
      {!isOpen && (
        <button
          id="brain-bubble-trigger"
          onClick={() => updateOpen(true)}
          className={`
            fixed bottom-6 right-6 z-50
            w-12 h-12 rounded-full
            bg-[#0A1E2F] hover:bg-[#0D2A35]
            shadow-lg hover:shadow-xl
            flex items-center justify-center
            transition-all duration-200
            ${hasNewInsight ? 'animate-pulse' : ''}
          `}
          title="Open assistant (⌘J)"
        >
          <MessageSquare className="w-5 h-5 text-[#3FAF7A]" />

          {/* Badge — action count */}
          {actionCount > 0 && (
            <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 flex items-center justify-center rounded-full bg-[#3FAF7A] text-white text-[10px] font-bold">
              {actionCount > 9 ? '9+' : actionCount}
            </span>
          )}

          {/* Green dot — new insight */}
          {hasNewInsight && actionCount === 0 && (
            <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-[#3FAF7A] ring-2 ring-white" />
          )}
        </button>
      )}

      {/* Side Panel — fixed right, BRD compresses via marginRight */}
      <div
        ref={panelRef}
        className={`
          fixed top-0 right-0 h-screen z-40
          bg-white border-l border-[#E5E5E5]
          shadow-2xl
          flex flex-col
          transition-all duration-300 ease-in-out
          ${isOpen ? 'translate-x-0' : 'translate-x-full'}
        `}
        style={{ width: BRAIN_PANEL_WIDTH }}
      >
        {/* Tab Header */}
        <div className="px-4 py-3 border-b border-[#E5E5E5] flex-shrink-0">
          <div className="flex items-center gap-2">
            {/* Pill Toggle */}
            <div className="flex-1 flex items-center bg-[#F4F4F4] rounded-xl p-1">
              <button
                onClick={() => setActiveTab('actions')}
                className={`
                  flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg
                  text-[12px] font-medium transition-all duration-150
                  ${activeTab === 'actions'
                    ? 'bg-white text-[#0A1E2F] shadow-sm'
                    : 'text-[#666666] hover:text-[#333333]'
                  }
                `}
              >
                <Zap className="w-3.5 h-3.5" />
                Briefing
                {actionCount > 0 && (
                  <span className="ml-1 min-w-[16px] h-[16px] px-1 flex items-center justify-center rounded-full bg-[#3FAF7A] text-white text-[9px] font-bold">
                    {actionCount}
                  </span>
                )}
              </button>
              <button
                onClick={() => setActiveTab('chat')}
                className={`
                  flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg
                  text-[12px] font-medium transition-all duration-150
                  ${activeTab === 'chat'
                    ? 'bg-white text-[#0A1E2F] shadow-sm'
                    : 'text-[#666666] hover:text-[#333333]'
                  }
                `}
              >
                <MessageSquare className="w-3.5 h-3.5" />
                Chat
              </button>
            </div>

            {/* New Chat */}
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
              className="p-1.5 rounded-lg hover:bg-[#F4F4F4] transition-colors"
              title="Close (Esc)"
            >
              <X className="w-4 h-4 text-[#999999]" />
            </button>
          </div>
        </div>

        {/* Client Pulse Strip — persistent awareness (hidden on Collaborate) */}
        {!hideClientPulse && (
          <ClientPulseStrip projectId={projectId} onClick={onNavigateToCollaborate} />
        )}

        {/* Tab Content */}
        <div className="flex-1 overflow-hidden relative">
          {activeTab === 'actions' ? (
            <IntelligenceBriefingPanel
              projectId={projectId}
              onNavigate={handleNavigate}
              onCascade={onCascade}
              onStartConversation={handleStartConversation}
              onUploadDocument={handleUploadDocument}
            />
          ) : (
            <WorkspaceChat
              projectId={projectId}
              messages={messages}
              isLoading={isChatLoading}
              onSendMessage={onSendMessage}
              onSendSignal={onSendSignal}
              onAddLocalMessage={onAddLocalMessage}
              contextActions={contextActions}
            />
          )}

          {/* Chat-as-Signal Detection Card */}
          {activeTab === 'chat' && entityDetection && entityDetection.should_extract && (
            <div className="absolute bottom-2 left-2 right-2 z-10">
              <div className="bg-white border border-[#E5E5E5] rounded-xl shadow-lg p-3">
                <div className="flex items-start gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-[#E8F5E9] flex items-center justify-center flex-shrink-0">
                    <FileText className="w-4 h-4 text-[#25785A]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[12px] font-medium text-[#333333]">
                      Found requirements in our chat
                    </p>
                    <p className="text-[11px] text-[#666666] mt-0.5">
                      {entityDetection.entity_count} entities: {entityDetection.entity_hints.slice(0, 3).map(h => h.name).join(', ')}
                      {entityDetection.entity_hints.length > 3 && ` +${entityDetection.entity_hints.length - 3} more`}
                    </p>
                    <div className="flex items-center gap-2 mt-2">
                      <button
                        onClick={onSaveAsSignal}
                        disabled={isSavingAsSignal}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-medium text-white bg-[#3FAF7A] hover:bg-[#25785A] rounded-lg transition-colors disabled:opacity-50"
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
                        className="px-3 py-1.5 text-[11px] font-medium text-[#666666] hover:text-[#333333] transition-colors"
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
