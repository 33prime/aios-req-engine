'use client'

import { useState, useCallback, useRef } from 'react'
import { getAccessToken, API_BASE } from '@/lib/api/core'
import type { StationSlug, StationChatMessage } from '@/types/portal'

interface UseStationChatOptions {
  projectId: string
  station: StationSlug
  onToolResult?: (toolName: string, result: Record<string, unknown>) => void
  epicTitle?: string
  epicNarrative?: string
  assumptionText?: string
}

interface UseStationChatReturn {
  messages: StationChatMessage[]
  isLoading: boolean
  sendMessage: (message: string) => Promise<void>
  conversationId: string | null
  error: string | null
}

const MAX_HISTORY = 15

export function useStationChat({
  projectId,
  station,
  onToolResult,
  epicTitle,
  epicNarrative,
  assumptionText,
}: UseStationChatOptions): UseStationChatReturn {
  const [messages, setMessages] = useState<StationChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const onToolResultRef = useRef(onToolResult)
  onToolResultRef.current = onToolResult

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isLoading) return

      setIsLoading(true)
      setError(null)

      const userMsg: StationChatMessage = {
        role: 'user',
        content,
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, userMsg])

      let assistantContent = ''
      let toolCalls: StationChatMessage['toolCalls'] = []

      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: '', timestamp: new Date(), isStreaming: true, toolCalls: [] },
      ])

      abortRef.current = new AbortController()

      try {
        const authHeaders: Record<string, string> = {}
        const token = getAccessToken()
        if (token) authHeaders['Authorization'] = `Bearer ${token}`

        const history = messages.slice(-MAX_HISTORY).map((m) => ({
          role: m.role,
          content: m.content,
        }))

        const response = await fetch(
          `${API_BASE}/v1/portal/projects/${projectId}/chat`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...authHeaders },
            body: JSON.stringify({
              message: content,
              conversation_id: conversationId || undefined,
              conversation_history: history,
              station,
              epic_title: epicTitle || undefined,
              epic_narrative: epicNarrative || undefined,
              assumption_text: assumptionText || undefined,
            }),
            signal: abortRef.current.signal,
          }
        )

        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        if (!response.body) throw new Error('No response body')

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let sseBuffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          sseBuffer += decoder.decode(value, { stream: true })
          const events = sseBuffer.split('\n\n')
          sseBuffer = events.pop() || ''

          for (const eventBlock of events) {
            const line = eventBlock.trim()
            if (!line.startsWith('data: ')) continue

            try {
              const event = JSON.parse(line.slice(6))

              if (event.type === 'conversation_id') {
                setConversationId(event.conversation_id)
              } else if (event.type === 'text') {
                assistantContent += event.content
                setMessages((prev) => {
                  const updated = [...prev]
                  const last = updated[updated.length - 1]
                  if (last?.role === 'assistant') {
                    last.content = assistantContent
                    last.isStreaming = true
                  }
                  return updated
                })
              } else if (event.type === 'tool_result') {
                toolCalls = [...(toolCalls || []), {
                  tool_name: event.tool_name,
                  status: 'complete' as const,
                  result: event.result,
                }]
                setMessages((prev) => {
                  const updated = [...prev]
                  const last = updated[updated.length - 1]
                  if (last?.role === 'assistant') last.toolCalls = [...toolCalls!]
                  return updated
                })
                onToolResultRef.current?.(event.tool_name, event.result)
              } else if (event.type === 'done') {
                setMessages((prev) => {
                  const updated = [...prev]
                  const last = updated[updated.length - 1]
                  if (last?.role === 'assistant') last.isStreaming = false
                  return updated
                })
              } else if (event.type === 'error') {
                throw new Error(event.message || 'Chat error')
              }
            } catch (parseErr) {
              // Ignore parse errors on individual events
            }
          }
        }
      } catch (err) {
        if ((err as Error).name !== 'AbortError') {
          setError((err as Error).message)
          setMessages((prev) => {
            const updated = [...prev]
            const last = updated[updated.length - 1]
            if (last?.role === 'assistant' && last.isStreaming) updated.pop()
            return updated
          })
        }
      } finally {
        setIsLoading(false)
        abortRef.current = null
      }
    },
    [projectId, station, conversationId, messages, isLoading, epicTitle, epicNarrative, assumptionText]
  )

  return { messages, isLoading, sendMessage, conversationId, error }
}
