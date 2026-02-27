'use client'

import { useState, useRef, useEffect } from 'react'
import type { SessionContext } from '@/types/prototype'

interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
}

interface SessionChatProps {
  sessionId: string
  context: SessionContext
  onSendMessage: (message: string) => Promise<string>
}

/**
 * Context-aware chat at the bottom of the prototype session view.
 * Shows current page + active feature context, page-change markers,
 * and auto-tags messages with SessionContext.
 */
export default function SessionChat({
  sessionId,
  context,
  onSendMessage,
}: SessionChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isCollapsed, setIsCollapsed] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const prevPageRef = useRef(context.current_page)

  // Add page-change markers
  useEffect(() => {
    if (context.current_page && context.current_page !== prevPageRef.current) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'system',
          content: `Navigated to ${context.current_page}`,
          timestamp: new Date().toISOString(),
        },
      ])
      prevPageRef.current = context.current_page
    }
  }, [context.current_page])

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const userMessage = input.trim()
    setInput('')

    setMessages((prev) => [
      ...prev,
      { role: 'user', content: userMessage, timestamp: new Date().toISOString() },
    ])

    setIsLoading(true)
    try {
      const response = await onSendMessage(userMessage)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: response, timestamp: new Date().toISOString() },
      ])
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Failed to get response. Please try again.', timestamp: new Date().toISOString() },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  if (isCollapsed) {
    return (
      <div className="border-t border-border bg-white">
        <button
          onClick={() => setIsCollapsed(false)}
          className="w-full px-4 py-2 text-sm text-text-placeholder hover:text-text-body flex items-center justify-between transition-colors"
        >
          <span>Session Chat ({messages.filter((m) => m.role !== 'system').length} messages)</span>
          <span className="text-xs">{'\u25B2'} Expand</span>
        </button>
      </div>
    )
  }

  return (
    <div className="border-t border-border bg-white flex flex-col h-[240px]">
      {/* Context bar + collapse */}
      <div className="px-4 py-2 bg-[#F4F4F4] text-[12px] text-text-placeholder flex items-center justify-between border-b border-border">
        <div className="flex items-center gap-3 truncate">
          <span>Page: {context.current_page || '/'}</span>
          {context.active_feature_name && (
            <>
              <span className="text-border">|</span>
              <span>Feature: {context.active_feature_name}</span>
            </>
          )}
        </div>
        <button
          onClick={() => setIsCollapsed(true)}
          className="text-xs text-text-placeholder hover:text-text-body ml-2 flex-shrink-0"
        >
          {'\u25BC'} Collapse
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 custom-scrollbar">
        {messages.map((msg, i) => {
          if (msg.role === 'system') {
            return (
              <div key={i} className="text-center text-[12px] text-text-placeholder my-2 flex items-center gap-2">
                <div className="flex-1 border-t border-dashed border-border" />
                <span className="px-2">{msg.content}</span>
                <div className="flex-1 border-t border-dashed border-border" />
              </div>
            )
          }

          return (
            <div
              key={i}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] text-sm ${
                  msg.role === 'user'
                    ? 'bg-[#0A1E2F] text-white rounded-2xl rounded-br-md px-4 py-3 shadow-sm'
                    : 'bg-white border border-border rounded-2xl rounded-bl-md px-4 py-3 shadow-sm text-text-body'
                }`}
              >
                {msg.content}
              </div>
            </div>
          )
        })}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white border border-border rounded-2xl rounded-bl-md px-4 py-3 shadow-sm">
              <div className="flex items-center gap-2">
                <div className="flex gap-1">
                  <div className="w-1.5 h-1.5 bg-brand-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-1.5 h-1.5 bg-brand-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-1.5 h-1.5 bg-brand-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
                <span className="text-[12px] text-text-placeholder">Thinking...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="px-4 py-3 border-t border-border">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about this feature, report observations..."
            disabled={isLoading}
            className="flex-1 px-4 py-3 text-sm bg-[#F4F4F4] focus:bg-white border border-border rounded-2xl focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary disabled:opacity-50 transition-all"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="px-4 py-3 bg-brand-primary text-white text-sm font-medium rounded-2xl hover:bg-[#25785A] transition-all duration-200 shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  )
}
