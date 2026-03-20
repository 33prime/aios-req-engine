'use client'

import { useState, useRef, useEffect } from 'react'
import type { IntelLayerAgent } from '@/types/workspace'
import { useAgentChat } from '@/hooks/useAgentChat'

interface Props {
  agent: IntelLayerAgent
  projectId: string
}

export function AgentChatTab({ agent, projectId }: Props) {
  const { messages, isLoading, sendMessage } = useAgentChat(projectId, agent.id)
  const [input, setInput] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, isLoading])

  const handleSend = () => {
    if (!input.trim() || isLoading) return
    sendMessage(input.trim())
    setInput('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleSuggestion = (text: string) => {
    sendMessage(text)
  }

  const introText = agent.chat_intro || `I'm ${agent.name}. ${agent.role_description.split('.')[0]}.`
  const suggestions = agent.chat_suggestions.length > 0
    ? agent.chat_suggestions
    : [`What do you do day-to-day?`, `What tools do you use?`, `When do you escalate to ${agent.partner_role || 'your human partner'}?`]
  const showIntro = messages.length === 0
  const showSuggestions = messages.length === 0

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-2.5 min-h-0">
        {/* Intro message from agent */}
        {showIntro && (
          <div
            className="rounded-xl px-3 py-2 text-[11px] leading-relaxed max-w-[85%]"
            style={{ background: 'rgba(10,30,47,0.04)', color: '#2D3748' }}
          >
            {introText}
          </div>
        )}

        {/* Suggestion buttons */}
        {showSuggestions && (
          <div className="flex flex-wrap gap-1 pt-1">
            {suggestions.map((suggestion, i) => (
              <button
                key={i}
                onClick={() => handleSuggestion(suggestion)}
                className="px-2.5 py-1 rounded text-[10px] transition-colors hover:bg-[rgba(4,65,89,0.08)]"
                style={{ color: '#044159', background: 'rgba(4,65,89,0.04)' }}
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}

        {/* Message bubbles */}
        {messages.map((msg) => {
          if (msg.role === 'system') {
            return (
              <div key={msg.id} className="flex justify-center">
                <span
                  className="text-[10px] px-3 py-1 rounded-full"
                  style={{ color: '#718096', background: 'rgba(0,0,0,0.03)' }}
                >
                  {msg.content}
                </span>
              </div>
            )
          }

          const isUser = msg.role === 'user'
          return (
            <div
              key={msg.id}
              className={`rounded-xl px-3 py-2 text-[11px] leading-relaxed max-w-[85%] ${
                isUser ? 'ml-auto' : 'mr-auto'
              }`}
              style={
                isUser
                  ? { background: '#0A1E2F', color: 'rgba(255,255,255,0.9)' }
                  : { background: 'rgba(10,30,47,0.04)', color: '#2D3748' }
              }
            >
              {msg.content}
            </div>
          )
        })}

        {/* Loading indicator */}
        {isLoading && (
          <div className="mr-8 rounded-lg px-3 py-2" style={{ background: 'rgba(0,0,0,0.03)' }}>
            <span className="inline-block w-2 h-2 rounded-full animate-pulse" style={{ background: '#3FAF7A' }} />
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className="flex-shrink-0 px-4 pb-3 pt-2" style={{ borderTop: '1px solid rgba(0,0,0,0.04)' }}>
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Ask ${agent.name}...`}
            className="flex-1 rounded-lg px-2.5 py-1.5 text-[11px] focus:outline-none focus:ring-1 focus:ring-[#3FAF7A]"
            style={{ background: '#fff', border: '1px solid rgba(10,30,47,0.10)' }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="px-3 py-1.5 rounded-lg text-[11px] font-medium text-white transition-colors"
            style={{ background: !input.trim() || isLoading ? '#A0AEC0' : '#3FAF7A' }}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  )
}
