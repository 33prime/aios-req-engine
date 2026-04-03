'use client'

/**
 * IntelligenceChatPanel — Contextual "Discuss" sidebar for intelligence architecture items.
 *
 * Opens when user clicks "Discuss" on an open question or architecture item.
 * Uses useChat with pageContext='intelligence:architecture' for SSE streaming.
 */

import { useState, useRef, useEffect } from 'react'
import { X, Send, Loader2, MessageCircle } from 'lucide-react'
import { Markdown } from '@/components/ui/Markdown'
import { useChat, type ChatMessage } from '@/lib/useChat'

interface ChatContext {
  section: string
  question: string
  context: string
}

interface Props {
  projectId: string
  chatContext: ChatContext
  onClose: () => void
}

const SUGGESTIONS = [
  'Is this essential for launch?',
  'What\'s the simplest version?',
  'How does this connect to outcomes?',
  'What would surprise a client here?',
]

export function IntelligenceChatPanel({ projectId, chatContext, onClose }: Props) {
  const [input, setInput] = useState('')
  const msgsRef = useRef<HTMLDivElement>(null)

  const { messages, isLoading, sendMessage, clearMessages } = useChat({
    projectId,
    pageContext: 'intelligence:architecture',
    focusedEntity: {
      type: 'architecture_item',
      data: { section: chatContext.section, question: chatContext.question, context: chatContext.context },
    },
  })

  // Auto-send the question as first message when context changes
  const lastCtxRef = useRef<string>('')
  useEffect(() => {
    const key = `${chatContext.section}:${chatContext.question}`
    if (key !== lastCtxRef.current) {
      lastCtxRef.current = key
      clearMessages()
      if (chatContext.question) {
        sendMessage(chatContext.question, { silent: true })
      }
    }
  }, [chatContext.section, chatContext.question]) // eslint-disable-line react-hooks/exhaustive-deps

  // Scroll to bottom on new messages
  useEffect(() => {
    if (msgsRef.current) msgsRef.current.scrollTop = msgsRef.current.scrollHeight
  }, [messages])

  const handleSend = () => {
    if (!input.trim() || isLoading) return
    sendMessage(input.trim())
    setInput('')
  }

  const handleSuggestion = (text: string) => {
    if (isLoading) return
    sendMessage(text)
  }

  return (
    <div className="w-[360px] border-l border-[rgba(10,30,47,0.08)] bg-white flex flex-col flex-shrink-0">
      {/* Header */}
      <div className="flex items-center gap-2 px-3.5 py-3 border-b border-[rgba(10,30,47,0.08)]">
        <MessageCircle size={14} className="text-[#3FAF7A]" />
        <span className="text-[12px] font-bold text-[#0A1E2F] flex-1">Discuss</span>
        <button onClick={onClose} className="p-1 text-[#A0AEC0] hover:text-[#0A1E2F] transition-colors">
          <X size={14} />
        </button>
      </div>

      {/* Context banner */}
      <div className="px-3.5 py-2 border-b border-[rgba(63,175,122,0.15)]" style={{ background: 'rgba(63,175,122,0.06)' }}>
        <p className="text-[8px] font-bold uppercase tracking-wider text-[#1B6B3A] mb-0.5">{chatContext.section}</p>
        <p className="text-[10px] font-medium text-[#2D3748]">{chatContext.question}</p>
      </div>

      {/* Messages */}
      <div ref={msgsRef} className="flex-1 overflow-y-auto px-3.5 py-3 flex flex-col gap-2">
        {messages.map((msg, i) => (
          <div
            key={msg.id || i}
            className={`max-w-[90%] px-2.5 py-2 rounded-lg text-[10px] leading-relaxed ${
              msg.role === 'user'
                ? 'bg-[#0A1E2F] text-white/90 self-end'
                : 'bg-[rgba(10,30,47,0.04)] text-[#2D3748] self-start'
            }`}
          >
            {msg.role === 'assistant' ? (
              <Markdown content={msg.content} />
            ) : (
              msg.content
            )}
            {msg.isStreaming && (
              <span className="inline-block w-1.5 h-3 bg-[#3FAF7A] animate-pulse ml-0.5 rounded-sm" />
            )}
          </div>
        ))}
        {isLoading && messages.length === 0 && (
          <div className="flex items-center gap-2 text-[10px] text-[#718096]">
            <Loader2 size={12} className="animate-spin" />
            Thinking...
          </div>
        )}
      </div>

      {/* Suggestions */}
      {messages.length <= 2 && !isLoading && (
        <div className="px-3.5 py-2 flex flex-wrap gap-1">
          {SUGGESTIONS.map(s => (
            <button
              key={s}
              onClick={() => handleSuggestion(s)}
              className="px-2 py-1 rounded-md text-[9px] font-medium text-[#044159] transition-all hover:border-[#044159]"
              style={{ background: 'rgba(4,65,89,0.04)', border: '1px solid rgba(4,65,89,0.08)' }}
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="px-3.5 py-2 border-t border-[rgba(10,30,47,0.08)] flex gap-1.5">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') handleSend() }}
          placeholder="Ask about this intelligence..."
          className="flex-1 px-2.5 py-1.5 border border-[rgba(10,30,47,0.08)] rounded-md text-[10px] text-[#2D3748] focus:outline-none focus:border-[#3FAF7A] font-[inherit]"
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || isLoading}
          className="px-2.5 py-1.5 bg-[#3FAF7A] rounded-md text-white flex items-center justify-center hover:bg-[#33a06d] transition-colors disabled:opacity-40"
        >
          <Send size={12} />
        </button>
      </div>
    </div>
  )
}
