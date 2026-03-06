'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, CheckCircle, Loader2 } from 'lucide-react'
import { Markdown } from '@/components/ui/Markdown'
import { useStationChat } from '@/hooks/useStationChat'
import { ChatQuickActions, isEscalationMessage } from '@/components/portal/ChatQuickActions'
import type { StationSlug, StationChatMessage } from '@/types/portal'

interface StationChatProps {
  projectId: string
  station: StationSlug
  greeting?: string
  onToolResult?: (toolName: string, result: Record<string, unknown>) => void
  epicTitle?: string
  epicNarrative?: string
  assumptionText?: string
  consultantName?: string
}

export function StationChat({ projectId, station, greeting, onToolResult, epicTitle, epicNarrative, assumptionText, consultantName }: StationChatProps) {
  const { messages, isLoading, sendMessage, error } = useStationChat({
    projectId,
    station,
    onToolResult,
    epicTitle,
    epicNarrative,
    assumptionText,
  })
  const [input, setInput] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll on new messages
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  const handleSubmit = () => {
    if (!input.trim() || isLoading) return
    sendMessage(input.trim())
    setInput('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {/* Greeting */}
        {greeting && messages.length === 0 && (
          <div className="flex gap-2">
            <div className="max-w-[85%] rounded-xl rounded-tl-sm bg-surface-subtle px-3 py-2">
              <p className="text-sm text-text-secondary">{greeting}</p>
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}

        {/* Typing indicator */}
        {isLoading && messages[messages.length - 1]?.role !== 'assistant' && (
          <div className="flex gap-2">
            <div className="rounded-xl rounded-tl-sm bg-surface-subtle px-3 py-2">
              <Loader2 className="w-4 h-4 text-text-placeholder animate-spin" />
            </div>
          </div>
        )}
      </div>

      {/* Quick actions after escalation */}
      {messages.length > 0 &&
        !isLoading &&
        messages[messages.length - 1]?.role === 'assistant' &&
        isEscalationMessage(messages[messages.length - 1]?.content || '') && (
          <ChatQuickActions
            consultantName={consultantName}
            onClearedUp={() => {
              // Client resolved their concern — could update assumption to 'great'
              sendMessage("Actually, that clears things up. I'm good with this!")
            }}
            onAlmost={() => {
              sendMessage("I'm almost there, but I'd still like to discuss this on the call.")
            }}
            onTalkTo={() => {
              sendMessage("Yes, let's save this for the call.")
            }}
          />
        )}

      {/* Error */}
      {error && (
        <div className="px-4 py-1.5">
          <p className="text-xs text-red-500">{error}</p>
        </div>
      )}

      {/* Input */}
      <div className="flex-shrink-0 border-t border-border px-4 py-3">
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            rows={1}
            className="flex-1 resize-none text-sm px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-brand-primary-ring focus:border-brand-primary"
          />
          <button
            onClick={handleSubmit}
            disabled={!input.trim() || isLoading}
            className="p-2 rounded-lg bg-brand-primary text-white hover:bg-brand-primary-hover disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}

function MessageBubble({ message }: { message: StationChatMessage }) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex gap-2 ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] rounded-xl px-3 py-2 ${
          isUser
            ? 'rounded-tr-sm bg-brand-primary text-white'
            : 'rounded-tl-sm bg-surface-subtle'
        }`}
      >
        {isUser ? (
          <p className="text-sm">{message.content}</p>
        ) : (
          <>
            {message.content && (
              <Markdown content={message.content} className="text-sm text-text-body" />
            )}
            {message.isStreaming && !message.content && (
              <Loader2 className="w-4 h-4 text-text-placeholder animate-spin" />
            )}
          </>
        )}

        {/* Tool result cards */}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="mt-2 space-y-1">
            {message.toolCalls.map((tc, j) => (
              <div
                key={j}
                className="flex items-center gap-1.5 text-xs text-text-muted bg-white/80 rounded px-2 py-1"
              >
                <CheckCircle className="w-3 h-3 text-brand-primary flex-shrink-0" />
                <span>{toolResultSummary(tc.tool_name, tc.result)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function toolResultSummary(name: string, result?: Record<string, unknown>): string {
  if (result?.error) return `Error: ${result.error}`
  const msg = result?.message as string | undefined
  if (msg) return msg
  const labels: Record<string, string> = {
    update_context_section: 'Updated context',
    add_metric: 'Added metric',
    add_user: 'Added user',
    add_competitor: 'Added competitor',
    add_design_inspiration: 'Added inspiration',
    add_tribal_knowledge: 'Saved knowledge',
    complete_info_request: 'Completed question',
    get_pending_questions: 'Retrieved questions',
    get_context_summary: 'Checked progress',
    suggest_next_action: 'Suggested next step',
  }
  return labels[name] || `Executed ${name.replace(/_/g, ' ')}`
}
