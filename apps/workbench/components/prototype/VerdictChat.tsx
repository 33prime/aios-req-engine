'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Send, Loader2, X } from 'lucide-react'
import { prototypeSessionChat, submitPrototypeFeedback } from '@/lib/api'
import type { FeatureOverlay, FeatureVerdict, SessionContext } from '@/types/prototype'

interface ChatBubble {
  role: 'user' | 'assistant'
  content: string
}

interface VerdictChatProps {
  overlay: FeatureOverlay
  sessionId: string
  sessionContext: SessionContext | null
  verdict: FeatureVerdict
  onDone: (summary: string) => void
}

const MAX_TURNS = 5

export default function VerdictChat({
  overlay,
  sessionId,
  sessionContext,
  verdict,
  onDone,
}: VerdictChatProps) {
  const [messages, setMessages] = useState<ChatBubble[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [turnCount, setTurnCount] = useState(0)
  const [dismissed, setDismissed] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const initRef = useRef(false)

  const featureId = overlay.feature_id || overlay.id

  // Auto-scroll on new messages
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  // Generate smart opening message on mount
  useEffect(() => {
    if (initRef.current) return
    initRef.current = true

    const content = overlay.overlay_content
    const confidence = content?.confidence ?? 0
    const gaps = content?.gaps ?? []
    const suggestedVerdict = content?.suggested_verdict
    const featureName = content?.feature_name ?? 'this feature'

    // Build a meta-prompt for the AI to generate a contextual opener
    let openerPrompt = ''
    if (verdict === 'aligned') {
      openerPrompt = `I just marked "${featureName}" as Aligned (${Math.round(confidence * 100)}% confidence).`
      if (suggestedVerdict && suggestedVerdict !== 'aligned') {
        openerPrompt += ` The AI had suggested "${suggestedVerdict}" instead.`
      }
    } else if (verdict === 'needs_adjustment') {
      const gapText = gaps.length > 0 ? gaps[0].question : 'some gaps between spec and implementation'
      openerPrompt = `I marked "${featureName}" as Needs Adjustment. Key gap: ${gapText}`
    } else {
      openerPrompt = `I marked "${featureName}" as Off Track — something fundamental is wrong.`
    }

    setLoading(true)
    prototypeSessionChat(
      sessionId,
      openerPrompt,
      sessionContext ?? undefined,
      undefined,
      featureId
    )
      .then((res) => {
        setMessages([{ role: 'assistant', content: res.response }])
      })
      .catch((err) => {
        console.error('Failed to get opener:', err)
        setMessages([{
          role: 'assistant',
          content: verdict === 'aligned'
            ? 'Good call. Any edge cases or data nuances to note?'
            : 'Got it. What specifically needs to change?',
        }])
      })
      .finally(() => {
        setLoading(false)
        setTimeout(() => inputRef.current?.focus(), 100)
      })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSend = useCallback(async () => {
    const text = input.trim()
    if (!text || loading || turnCount >= MAX_TURNS) return

    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setTurnCount((c) => c + 1)
    setLoading(true)

    // Save as feedback
    try {
      await submitPrototypeFeedback(sessionId, {
        content: text,
        feedback_type: 'observation',
        feature_id: featureId,
        context: sessionContext ?? undefined,
        priority: verdict === 'off_track' ? 'high' : 'medium',
      })
    } catch (err) {
      console.error('Failed to save feedback:', err)
    }

    // Get AI response
    try {
      const res = await prototypeSessionChat(
        sessionId,
        text,
        sessionContext ?? undefined,
        undefined,
        featureId
      )
      setMessages((prev) => [...prev, { role: 'assistant', content: res.response }])
    } catch (err) {
      console.error('Chat error:', err)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Sorry, I had trouble processing that. Could you rephrase?' },
      ])
    } finally {
      setLoading(false)
    }
  }, [input, loading, turnCount, sessionId, featureId, sessionContext, verdict])

  const handleDone = useCallback(() => {
    const userMsgs = messages
      .filter((m) => m.role === 'user')
      .map((m) => m.content)
      .join(' | ')
    onDone(userMsgs)
    setDismissed(true)
  }, [messages, onDone])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend]
  )

  if (dismissed) return null

  const isMaxed = turnCount >= MAX_TURNS

  return (
    <div className="border-t border-border bg-surface-page">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-border">
        <span className="text-[10px] font-medium text-text-placeholder uppercase tracking-wide">
          Quick Chat
        </span>
        <button
          onClick={handleDone}
          className="text-[10px] text-text-placeholder hover:text-[#666666] transition-colors"
        >
          Done
        </button>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="max-h-[200px] overflow-y-auto px-3 py-2 space-y-2">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] px-3 py-1.5 rounded-xl text-xs leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-[#0A1E2F] text-white'
                  : 'bg-white border border-border text-text-body'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="px-3 py-1.5 bg-white border border-border rounded-xl">
              <Loader2 className="w-3 h-3 text-text-placeholder animate-spin" />
            </div>
          </div>
        )}
      </div>

      {/* Input or done */}
      {isMaxed ? (
        <div className="px-3 py-2 border-t border-border">
          <button
            onClick={handleDone}
            className="w-full px-3 py-1.5 text-xs font-medium text-brand-primary bg-[#E8F5E9] rounded-lg hover:bg-[#d0eed6] transition-colors"
          >
            Done &mdash; Save Notes
          </button>
        </div>
      ) : (
        <div className="flex items-center gap-2 px-3 py-2 border-t border-border">
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Why this verdict?"
            disabled={loading}
            className="flex-1 px-3 py-1.5 text-xs border border-border rounded-lg focus:outline-none focus:ring-1 focus:ring-brand-primary/30 focus:border-brand-primary text-text-body placeholder:text-text-placeholder disabled:opacity-60"
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="p-1.5 rounded-lg text-brand-primary hover:bg-[#E8F5E9] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  )
}
