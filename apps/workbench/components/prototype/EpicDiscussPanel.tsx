'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { Send, Loader2 } from 'lucide-react'
import type { Epic } from '@/types/epic-overlay'
import { sendEpicDiscussMessage } from '@/lib/api/prototypes'
import { Markdown } from '@/components/ui/Markdown'

interface DiscussMessage {
  role: 'user' | 'assistant'
  content: string
}

interface EpicDiscussPanelProps {
  epic: Epic
  epicIndex: number
  sessionId: string
}

export default function EpicDiscussPanel({
  epic,
  epicIndex,
  sessionId,
}: EpicDiscussPanelProps) {
  const [messages, setMessages] = useState<DiscussMessage[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Reset messages when epic changes
  useEffect(() => {
    setMessages([])
    setInput('')
  }, [epicIndex])

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const handleSend = useCallback(async () => {
    const text = input.trim()
    if (!text || isLoading) return

    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setIsLoading(true)

    try {
      const result = await sendEpicDiscussMessage(sessionId, epicIndex, text)
      setMessages((prev) => [...prev, { role: 'assistant', content: result.response }])
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Sorry, something went wrong. Try again.' },
      ])
    } finally {
      setIsLoading(false)
      inputRef.current?.focus()
    }
  }, [input, isLoading, sessionId, epicIndex])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend]
  )

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {messages.length === 0 && (
          <p className="text-xs text-[#999] text-center mt-8">
            Ask anything about &ldquo;{epic.title}&rdquo;...
          </p>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`text-xs leading-relaxed ${
              msg.role === 'user'
                ? 'text-[#37352f] bg-[#F4F4F4] rounded-lg px-3 py-2 ml-6'
                : 'text-[#37352f] pr-6'
            }`}
          >
            {msg.role === 'assistant' ? (
              <Markdown content={msg.content} className="text-[12px] leading-relaxed" />
            ) : (
              msg.content
            )}
          </div>
        ))}
        {isLoading && (
          <div className="flex items-center gap-2 text-xs text-[#999]">
            <Loader2 className="w-3 h-3 animate-spin" />
            Thinking...
          </div>
        )}
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t border-border">
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Discuss ${epic.title}...`}
            className="flex-1 text-xs border border-border rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-1 focus:ring-brand-primary max-h-32"
            rows={3}
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="p-2 text-brand-primary hover:bg-brand-primary/10 rounded-lg disabled:opacity-30 transition-colors"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  )
}
