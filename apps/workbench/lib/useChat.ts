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

import { useState, useCallback, useRef, useEffect } from 'react'
import { detectChatEntities, saveChatAsSignal, getConversationMessages, type ChatEntityDetectionResult } from '@/lib/api'
import { getAccessToken } from '@/lib/api/core'

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
    result?: Record<string, unknown>
    error?: string
  }>
}

// Tools that mutate project data — frontend should revalidate after these execute
const MUTATING_TOOLS = new Set([
  'create_entity', 'update_entity', 'delete_entity', 'add_signal', 'create_task',
  'create_confirmation', 'attach_evidence', 'generate_strategic_context',
  'update_strategic_context', 'update_project_type', 'identify_stakeholders',
  'update_solution_flow_step', 'refine_solution_flow_step',
  'add_solution_flow_step', 'remove_solution_flow_step',
  'reorder_solution_flow_steps', 'resolve_solution_flow_question',
])

interface UseChatOptions {
  projectId: string
  conversationId?: string
  pageContext?: string  // e.g., "brd:workflows", "canvas", "prototype"
  focusedEntity?: { type: string; data: Record<string, string> } | null
  onError?: (error: Error) => void
  /** Called after a mutating tool executes — use to revalidate SWR caches */
  onDataMutated?: () => void
}

interface UseChatReturn {
  messages: ChatMessage[]
  isLoading: boolean
  error: Error | null
  sendMessage: (message: string) => Promise<void>
  sendSignal: (type: string, content: string, source: string) => Promise<void>
  clearMessages: () => void
  addLocalMessage: (message: ChatMessage) => void
  // Conversation persistence
  conversationId: string | null
  startNewChat: () => void
  // Chat-as-signal
  entityDetection: ChatEntityDetectionResult | null
  isSavingAsSignal: boolean
  saveAsSignal: () => Promise<void>
  dismissDetection: () => void
  // Conversation starter context
  setConversationContext: (context: string) => void
}

export function useChat({
  projectId,
  conversationId: initialConversationId,
  pageContext,
  focusedEntity,
  onError,
  onDataMutated,
}: UseChatOptions): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const onDataMutatedRef = useRef(onDataMutated)
  onDataMutatedRef.current = onDataMutated
  const [conversationId, setConversationId] = useState<string | null>(initialConversationId ?? null)
  const conversationContextRef = useRef<string | null>(null)

  const setConversationContext = useCallback((context: string) => {
    conversationContextRef.current = context
  }, [])

  // Load existing conversation messages on mount (when conversationId is provided)
  useEffect(() => {
    if (!conversationId || conversationId === 'default') return

    getConversationMessages(conversationId)
      .then(({ messages: dbMessages }) => {
        if (dbMessages.length > 0) {
          const loaded: ChatMessage[] = dbMessages.map((m) => ({
            id: m.id,
            role: m.role as ChatMessage['role'],
            content: m.content,
            timestamp: new Date(m.created_at),
            metadata: m.metadata ?? undefined,
          }))
          setMessages(loaded)
        }
      })
      .catch((err) => console.error('Failed to load conversation:', err))
  }, []) // Only on mount

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
        const authHeaders: Record<string, string> = {}
        const token = getAccessToken()
        if (token) authHeaders['Authorization'] = `Bearer ${token}`

        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_BASE}/v1/chat?project_id=${projectId}`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...authHeaders,
            },
            body: JSON.stringify({
              message: content,
              conversation_id: conversationId || undefined,
              conversation_history: messages.slice(-10), // Last 10 messages
              context: {},
              page_context: pageContext || null,
              focused_entity: focusedEntity || null,
              conversation_context: conversationContextRef.current || undefined,
            }),
            signal: abortControllerRef.current.signal,
          }
        )

        // Clear conversation context after sending (one-shot)
        conversationContextRef.current = null

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }

        if (!response.body) {
          throw new Error('Response body is null')
        }

        // Read SSE stream with proper cross-chunk buffering
        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let sseBuffer = ''

        while (true) {
          const { done, value } = await reader.read()

          if (done) break

          // Decode chunk and append to buffer
          sseBuffer += decoder.decode(value, { stream: true })

          // Split on double-newline (SSE event boundary) and process complete events
          const events = sseBuffer.split('\n\n')
          // Last element may be incomplete — keep it in the buffer
          sseBuffer = events.pop() || ''

          for (const eventBlock of events) {
            const line = eventBlock.trim()
            if (!line.startsWith('data: ')) continue

            const data = line.slice(6) // Remove "data: " prefix

            try {
              const event = JSON.parse(data)

              if (event.type === 'conversation_id') {
                // Capture real conversation ID from backend
                setConversationId(event.conversation_id)
              } else if (event.type === 'text') {
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

                // Revalidate UI data after mutating tools
                if (MUTATING_TOOLS.has(event.tool_name) && !event.result?.error) {
                  onDataMutatedRef.current?.()
                }

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
              console.error('Failed to parse SSE event:', data?.slice(0, 100), parseError)
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
        const authHeaders: Record<string, string> = {}
        const token = getAccessToken()
        if (token) authHeaders['Authorization'] = `Bearer ${token}`

        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_BASE}/v1/chat?project_id=${projectId}`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...authHeaders,
            },
            body: JSON.stringify({
              message: `Add this ${type} signal and process it:\n\n${content}\n\nSource: ${source}`,
              conversation_id: conversationId || undefined,
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

        // Read SSE stream with proper cross-chunk buffering
        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let currentToolCalls: ChatMessage['toolCalls'] = []
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

            const data = line.slice(6)
            try {
              const event = JSON.parse(data)

              if (event.type === 'conversation_id') {
                setConversationId(event.conversation_id)
              } else if (event.type === 'text') {
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
                // Revalidate UI data after mutating tools
                if (MUTATING_TOOLS.has(event.tool_name) && !event.result?.error) {
                  onDataMutatedRef.current?.()
                }
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
              console.error('Failed to parse SSE event:', data?.slice(0, 100), parseError)
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

  const startNewChat = useCallback(() => {
    setMessages([])
    setConversationId(null)
    setError(null)
    setEntityDetection(null)
  }, [])

  // Add a local message without triggering AI response
  const addLocalMessage = useCallback((message: ChatMessage) => {
    setMessages((prev) => [...prev, { ...message, timestamp: message.timestamp || new Date() }])
  }, [])

  // ==========================================================================
  // Chat-as-Signal: Entity Detection
  // ==========================================================================
  const [entityDetection, setEntityDetection] = useState<ChatEntityDetectionResult | null>(null)
  const [isSavingAsSignal, setIsSavingAsSignal] = useState(false)
  const userMessageCountRef = useRef(0)
  const lastDetectionCountRef = useRef(0)
  const dismissedCountRef = useRef(0)

  // Track user messages and trigger detection every 4 new user messages
  useEffect(() => {
    const userMessages = messages.filter(m => m.role === 'user')
    userMessageCountRef.current = userMessages.length

    // Only detect if: 4+ user messages since last detection, not loading, no pending detection
    const sinceLast = userMessages.length - lastDetectionCountRef.current
    if (sinceLast >= 4 && !isLoading && !entityDetection) {
      // Don't over-prompt: if dismissed recently, wait longer
      const threshold = dismissedCountRef.current > 0 ? 6 : 4
      if (sinceLast < threshold) return

      lastDetectionCountRef.current = userMessages.length
      const recentUserMsgs = messages
        .filter(m => m.role === 'user' && m.content.trim())
        .slice(-5)
        .map(m => ({ role: m.role, content: m.content }))

      if (recentUserMsgs.length >= 3) {
        detectChatEntities(projectId, recentUserMsgs)
          .then(result => {
            if (result.should_extract && result.entity_count >= 2) {
              setEntityDetection(result)
            }
          })
          .catch(err => console.error('Entity detection failed:', err))
      }
    }
  }, [messages, isLoading, entityDetection, projectId])

  const dismissDetection = useCallback(() => {
    setEntityDetection(null)
    dismissedCountRef.current += 1
  }, [])

  const saveAsSignal = useCallback(async () => {
    if (!entityDetection) return

    setIsSavingAsSignal(true)
    try {
      // Gather the last 5-8 user messages for extraction
      const recentMsgs = messages
        .filter(m => m.content.trim())
        .slice(-10)
        .map(m => ({ role: m.role, content: m.content }))

      const result = await saveChatAsSignal(projectId, recentMsgs)

      // Add confirmation message to chat
      if (result.success) {
        addLocalMessage({
          role: 'system',
          content: `📋 Saved ${result.facts_extracted} requirements from our conversation (${result.type_summary}). The BRD has been updated.`,
          timestamp: new Date(),
        })
      } else {
        addLocalMessage({
          role: 'system',
          content: `⚠️ Could not extract requirements: ${result.error || 'Unknown error'}`,
          timestamp: new Date(),
        })
      }

      setEntityDetection(null)
      dismissedCountRef.current = 0 // Reset dismiss counter on successful save
    } catch (err) {
      console.error('Save as signal failed:', err)
    } finally {
      setIsSavingAsSignal(false)
    }
  }, [entityDetection, messages, projectId, addLocalMessage])

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    sendSignal,
    clearMessages,
    addLocalMessage,
    // Conversation persistence
    conversationId,
    startNewChat,
    // Chat-as-signal
    entityDetection,
    isSavingAsSignal,
    saveAsSignal,
    dismissDetection,
    // Conversation starter context
    setConversationContext,
  }
}
