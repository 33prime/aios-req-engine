'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import { getAgentChatHistory, sendAgentChatMessage } from '@/lib/api/intel-layer'
import type { AgentChatMessage } from '@/types/workspace'

interface UseAgentChatReturn {
  messages: AgentChatMessage[]
  isLoading: boolean
  sendMessage: (text: string) => Promise<void>
}

export function useAgentChat(projectId: string, agentId: string | null): UseAgentChatReturn {
  const [messages, setMessages] = useState<AgentChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const prevAgentId = useRef<string | null>(null)

  // Load history when agentId changes
  useEffect(() => {
    if (!agentId || agentId === prevAgentId.current) return
    prevAgentId.current = agentId

    let cancelled = false
    setMessages([])

    getAgentChatHistory(projectId, agentId)
      .then((data) => {
        if (!cancelled) setMessages(data.messages)
      })
      .catch(() => {
        // History load failed — start fresh
      })

    return () => {
      cancelled = true
    }
  }, [projectId, agentId])

  const sendMessage = useCallback(
    async (text: string) => {
      if (!agentId || !text.trim() || isLoading) return

      setIsLoading(true)

      // Optimistic user message
      const userMsg: AgentChatMessage = {
        id: `temp-${Date.now()}`,
        role: 'user',
        content: text.trim(),
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, userMsg])

      try {
        const data = await sendAgentChatMessage(projectId, agentId, text.trim())

        // Append agent response
        const agentMsg: AgentChatMessage = {
          id: data.message_id,
          role: 'agent',
          content: data.response,
          created_at: new Date().toISOString(),
        }
        setMessages((prev) => [...prev, agentMsg])
      } catch {
        // Append error as system message
        const errMsg: AgentChatMessage = {
          id: `err-${Date.now()}`,
          role: 'system',
          content: 'Failed to send message. Please try again.',
          created_at: new Date().toISOString(),
        }
        setMessages((prev) => [...prev, errMsg])
      } finally {
        setIsLoading(false)
      }
    },
    [projectId, agentId, isLoading],
  )

  return { messages, isLoading, sendMessage }
}
