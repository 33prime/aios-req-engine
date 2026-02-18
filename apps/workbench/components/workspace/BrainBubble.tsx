'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Sparkles, X, MessageSquare, Zap } from 'lucide-react'
import type { ChatMessage } from './WorkspaceChat'
import { WorkspaceChat } from './WorkspaceChat'
import { IntelligencePanel } from './brd/components/IntelligencePanel'

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

  /** Pre-select a tab when opening */
  defaultTab?: BrainTab
}

// =============================================================================
// BrainBubble — floating button + slide-over panel
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
  defaultTab,
}: BrainBubbleProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<BrainTab>(() => {
    if (typeof window !== 'undefined') {
      return (localStorage.getItem('brain-panel-tab') as BrainTab) || 'actions'
    }
    return 'actions'
  })
  const panelRef = useRef<HTMLDivElement>(null)

  // Persist tab preference
  useEffect(() => {
    localStorage.setItem('brain-panel-tab', activeTab)
  }, [activeTab])

  // Apply default tab when it changes (e.g., "Discuss in chat →" CTA)
  useEffect(() => {
    if (defaultTab) {
      setActiveTab(defaultTab)
      setIsOpen(true)
    }
  }, [defaultTab])

  // Close on Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen])

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (isOpen && panelRef.current && !panelRef.current.contains(e.target as Node)) {
        // Don't close if clicking the bubble itself
        const bubble = document.getElementById('brain-bubble-trigger')
        if (bubble?.contains(e.target as Node)) return
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen])

  // Handle "Discuss in chat →" from action cards
  const handleNavigate = useCallback((entityType: string, entityId: string | null) => {
    if (entityType === 'chat') {
      setActiveTab('chat')
      return
    }
    // Forward navigation to parent
    onNavigate?.(entityType, entityId)
  }, [onNavigate])

  return (
    <>
      {/* Floating Bubble */}
      <button
        id="brain-bubble-trigger"
        onClick={() => setIsOpen(!isOpen)}
        className={`
          fixed bottom-6 right-6 z-50
          w-12 h-12 rounded-full
          bg-[#0A1E2F] hover:bg-[#0D2A35]
          shadow-lg hover:shadow-xl
          flex items-center justify-center
          transition-all duration-200
          ${isOpen ? 'scale-90 opacity-70' : 'scale-100'}
          ${hasNewInsight && !isOpen ? 'animate-pulse' : ''}
        `}
        title="Open Brain Panel"
      >
        {isOpen ? (
          <X className="w-5 h-5 text-white" />
        ) : (
          <Sparkles className="w-5 h-5 text-[#3FAF7A]" />
        )}

        {/* Badge — action count */}
        {!isOpen && actionCount > 0 && (
          <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 flex items-center justify-center rounded-full bg-[#3FAF7A] text-white text-[10px] font-bold">
            {actionCount > 9 ? '9+' : actionCount}
          </span>
        )}

        {/* Green dot — new insight */}
        {!isOpen && hasNewInsight && actionCount === 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-[#3FAF7A] ring-2 ring-white" />
        )}
      </button>

      {/* Slide-over Panel */}
      <div
        ref={panelRef}
        className={`
          fixed top-0 right-0 h-screen z-40
          w-[380px] bg-white border-l border-[#E5E5E5]
          shadow-2xl
          flex flex-col
          transition-transform duration-300 ease-in-out
          ${isOpen ? 'translate-x-0' : 'translate-x-full'}
        `}
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
                Actions
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

            {/* Close */}
            <button
              onClick={() => setIsOpen(false)}
              className="p-1.5 rounded-lg hover:bg-[#F4F4F4] transition-colors"
              title="Close (Esc)"
            >
              <X className="w-4 h-4 text-[#999999]" />
            </button>
          </div>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-hidden">
          {activeTab === 'actions' ? (
            <IntelligencePanel
              projectId={projectId}
              onNavigate={handleNavigate}
              onCascade={onCascade}
            />
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

      {/* Backdrop when panel is open */}
      {isOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/5"
          onClick={() => setIsOpen(false)}
        />
      )}
    </>
  )
}
