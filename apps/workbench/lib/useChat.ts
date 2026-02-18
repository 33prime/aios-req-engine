/**
 * useChat Hook
 *
 * Custom hook for managing chat conversations with SSE streaming.
 * Handles message state, streaming responses, and tool execution.
 *
 * Features:
 * - SSE connection management
 * - Message history state
 * - Streaming message updates
 * - Tool execution tracking
 * - Error handling
 */

'use client'

import { useState, useCallback, useRef } from 'react'

export interface ChatMessage {
  id?: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp?: Date
  isStreaming?: boolean
  metadata?: Record<string, unknown>
  toolCalls?: Array<{
    id?: string
    tool_name: string
    status: 'pending' | 'running' | 'complete' | 'error'
    args?: Record<string, unknown>
    result?: any
    error?: string
  }>
}

interface UseChatOptions {
  projectId: string
  conversationId?: string
  pageContext?: string  // e.g., "brd:workflows", "canvas", "prototype"
  focusedEntity?: { type: string; data: Record<string, string> } | null
  onError?: (error: Error) => void
}

interface UseChatReturn {
  messages: ChatMessage[]
  isLoading: boolean
  error: Error | null
  sendMessage: (message: string) => Promise<void>
  sendSignal: (type: string, content: string, source: string) => Promise<void>
  clearMessages: () => void
  addLocalMessage: (message: ChatMessage) => void
}

export function useChat({
  projectId,
  conversationId = 'default',
  pageContext,
  focusedEntity,
  onError,
}: UseChatOptions): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isLoading) return

      try {
        setIsLoading(true)
        setError(null)

        // Add user message immediately
        const userMessage: ChatMessage = {
          role: 'user',
          content,
          timestamp: new Date(),
        }

        setMessages((prev) => [...prev, userMessage])

        // Prepare assistant message placeholder
        const assistantMessageId = Date.now()
        let assistantContent = ''
        let currentToolCalls: ChatMessage['toolCalls'] = []

        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: '',
            timestamp: new Date(),
            isStreaming: true,
            toolCalls: [],
          },
        ])

        // Create abort controller for this request
        abortControllerRef.current = new AbortController()

        // Make SSE request
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_BASE}/v1/chat?project_id=${projectId}`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              message: content,
              conversation_id: conversationId,
              conversation_history: messages.slice(-10), // Last 10 messages
              context: {},
              page_context: pageContext || null,
              focused_entity: focusedEntity || null,
            }),
            signal: abortControllerRef.current.signal,
          }
        )

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }

        if (!response.body) {
          throw new Error('Response body is null')
        }

        // Read SSE stream
        const reader = response.body.getReader()
        const decoder = new TextDecoder()

        while (true) {
          const { done, value } = await reader.read()

          if (done) break

          // Decode chunk
          const chunk = decoder.decode(value, { stream: true })

          // Parse SSE events (format: "data: {...}\n\n")
          const lines = chunk.split('\n')

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue

            const data = line.slice(6) // Remove "data: " prefix

            try {
              const event = JSON.parse(data)

              if (event.type === 'text') {
                // Append text to assistant message
                assistantContent += event.content

                setMessages((prev) => {
                  const newMessages = [...prev]
                  const lastMessage = newMessages[newMessages.length - 1]

                  if (lastMessage && lastMessage.role === 'assistant') {
                    lastMessage.content = assistantContent
                    lastMessage.isStreaming = true
                  }

                  return newMessages
                })
              } else if (event.type === 'tool_result') {
                // Track tool execution
                const toolCall = {
                  tool_name: event.tool_name,
                  status: 'complete' as const,
                  result: event.result,
                }

                currentToolCalls.push(toolCall)

                setMessages((prev) => {
                  const newMessages = [...prev]
                  const lastMessage = newMessages[newMessages.length - 1]

                  if (lastMessage && lastMessage.role === 'assistant') {
                    lastMessage.toolCalls = [...currentToolCalls]
                  }

                  return newMessages
                })
              } else if (event.type === 'done') {
                // Finalize assistant message
                setMessages((prev) => {
                  const newMessages = [...prev]
                  const lastMessage = newMessages[newMessages.length - 1]

                  if (lastMessage && lastMessage.role === 'assistant') {
                    lastMessage.isStreaming = false
                  }

                  return newMessages
                })
              } else if (event.type === 'error') {
                throw new Error(event.message || 'Unknown error')
              }
            } catch (parseError) {
              console.error('Failed to parse SSE event:', parseError)
            }
          }
        }
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to send message')
        setError(error)
        onError?.(error)

        // Remove streaming message on error
        setMessages((prev) => {
          const newMessages = [...prev]
          const lastMessage = newMessages[newMessages.length - 1]

          if (lastMessage && lastMessage.role === 'assistant' && lastMessage.isStreaming) {
            newMessages.pop()
          }

          return newMessages
        })
      } finally {
        setIsLoading(false)
        abortControllerRef.current = null
      }
    },
    [projectId, conversationId, messages, isLoading, pageContext, focusedEntity, onError]
  )

  const sendSignal = useCallback(
    async (type: string, content: string, source: string) => {
      if (!content.trim()) return

      try {
        setIsLoading(true)
        setError(null)

        // Add a user message indicating signal submission
        const userMessage: ChatMessage = {
          role: 'user',
          content: `📥 Adding ${type}: "${content.slice(0, 50)}${content.length > 50 ? '...' : ''}"`,
          timestamp: new Date(),
        }
        setMessages((prev) => [...prev, userMessage])

        // Add assistant message placeholder
        let assistantContent = ''
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: '',
            timestamp: new Date(),
            isStreaming: true,
            toolCalls: [],
          },
        ])

        // Create abort controller for this request
        abortControllerRef.current = new AbortController()

        // Send signal through the chat API with add_signal tool
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_BASE}/v1/chat?project_id=${projectId}`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              message: `Add this ${type} signal and process it:\n\n${content}\n\nSource: ${source}`,
              conversation_id: conversationId,
              conversation_history: messages.slice(-5),
              context: {
                hint: 'use_add_signal_tool',
              },
            }),
            signal: abortControllerRef.current.signal,
          }
        )

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }

        if (!response.body) {
          throw new Error('Response body is null')
        }

        // Read SSE stream
        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let currentToolCalls: ChatMessage['toolCalls'] = []

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value, { stream: true })
          const lines = chunk.split('\n')

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue

            const data = line.slice(6)
            try {
              const event = JSON.parse(data)

              if (event.type === 'text') {
                assistantContent += event.content
                setMessages((prev) => {
                  const newMessages = [...prev]
                  const lastMessage = newMessages[newMessages.length - 1]
                  if (lastMessage && lastMessage.role === 'assistant') {
                    lastMessage.content = assistantContent
                    lastMessage.isStreaming = true
                  }
                  return newMessages
                })
              } else if (event.type === 'tool_result') {
                currentToolCalls.push({
                  tool_name: event.tool_name,
                  status: 'complete' as const,
                  result: event.result,
                })
                setMessages((prev) => {
                  const newMessages = [...prev]
                  const lastMessage = newMessages[newMessages.length - 1]
                  if (lastMessage && lastMessage.role === 'assistant') {
                    lastMessage.toolCalls = [...currentToolCalls]
                  }
                  return newMessages
                })
              } else if (event.type === 'done') {
                setMessages((prev) => {
                  const newMessages = [...prev]
                  const lastMessage = newMessages[newMessages.length - 1]
                  if (lastMessage && lastMessage.role === 'assistant') {
                    lastMessage.isStreaming = false
                  }
                  return newMessages
                })
              } else if (event.type === 'error') {
                throw new Error(event.message || 'Unknown error')
              }
            } catch (parseError) {
              console.error('Failed to parse SSE event:', parseError)
            }
          }
        }
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to send signal')
        setError(error)
        onError?.(error)

        setMessages((prev) => {
          const newMessages = [...prev]
          const lastMessage = newMessages[newMessages.length - 1]
          if (lastMessage && lastMessage.role === 'assistant' && lastMessage.isStreaming) {
            newMessages.pop()
          }
          return newMessages
        })
      } finally {
        setIsLoading(false)
        abortControllerRef.current = null
      }
    },
    [projectId, conversationId, messages, onError]
  )

  const clearMessages = useCallback(() => {
    setMessages([])
    setError(null)
  }, [])

  // Add a local message without triggering AI response
  const addLocalMessage = useCallback((message: ChatMessage) => {
    setMessages((prev) => [...prev, { ...message, timestamp: message.timestamp || new Date() }])
  }, [])

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    sendSignal,
    clearMessages,
    addLocalMessage,
  }
}
