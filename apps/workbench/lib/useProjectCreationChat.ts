/**
 * useProjectCreationChat Hook
 *
 * Custom hook for managing project creation conversations with SSE streaming.
 * Uses Claude Haiku 4.5 for fast, intelligent responses.
 *
 * Features:
 * - SSE connection management
 * - Message history state
 * - Streaming message updates
 * - Project creation detection
 * - Error handling
 */

'use client'

import { useState, useCallback, useRef, useEffect } from 'react'

export interface ProjectCreationMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  isStreaming?: boolean
}

export interface CreatedProject {
  id: string
  name: string
  onboarding_job_id?: string
  signal_id?: string
}

interface UseProjectCreationChatOptions {
  onError?: (error: Error) => void
  onProjectCreated?: (project: CreatedProject) => void
}

interface UseProjectCreationChatReturn {
  messages: ProjectCreationMessage[]
  isLoading: boolean
  error: Error | null
  projectCreated: CreatedProject | null
  sendMessage: (message: string) => Promise<void>
  initializeChat: () => Promise<void>
  reset: () => void
}

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

/**
 * Strip any internal markers from content (fallback if backend misses any).
 * Removes complete markers like [[STEP:...]] and incomplete ones like [[STEP:...
 */
function stripMarkers(content: string): string {
  // Remove complete [[...]] markers
  let cleaned = content.replace(/\s*\[\[STEP:.*?\]\]/gs, '')
  cleaned = cleaned.replace(/\s*\[\[READY_TO_CREATE.*?\]\]/gs, '')
  cleaned = cleaned.replace(/\s*\[\[.*?\]\]/gs, '')
  // Remove incomplete markers (no closing ]])
  cleaned = cleaned.replace(/\s*\[\[[^\]]*$/g, '')
  return cleaned.trim()
}

export function useProjectCreationChat({
  onError,
  onProjectCreated,
}: UseProjectCreationChatOptions = {}): UseProjectCreationChatReturn {
  const [messages, setMessages] = useState<ProjectCreationMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const [projectCreated, setProjectCreated] = useState<CreatedProject | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const initializedRef = useRef(false)

  // Initialize chat with greeting
  const initializeChat = useCallback(async () => {
    if (initializedRef.current) return
    initializedRef.current = true

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE}/v1/project-creation/init`
      )

      if (!response.ok) {
        throw new Error(`Failed to initialize chat: ${response.statusText}`)
      }

      const data = await response.json()

      // Add initial greeting message
      setMessages([
        {
          id: generateId(),
          role: 'assistant',
          content: data.greeting,
        },
      ])
    } catch (err) {
      // Fallback greeting if init fails
      setMessages([
        {
          id: generateId(),
          role: 'assistant',
          content: "Hi! I'm here to help you set up your new project. What would you like to call it?",
        },
      ])
    }
  }, [])

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isLoading) return

      try {
        setIsLoading(true)
        setError(null)

        // Add user message immediately
        const userMessage: ProjectCreationMessage = {
          id: generateId(),
          role: 'user',
          content,
        }

        setMessages((prev) => [...prev, userMessage])

        // Prepare assistant message placeholder
        const assistantId = generateId()
        let assistantContent = ''

        setMessages((prev) => [
          ...prev,
          {
            id: assistantId,
            role: 'assistant',
            content: '',
            isStreaming: true,
          },
        ])

        // Create abort controller for this request
        abortControllerRef.current = new AbortController()

        // Build conversation history for API
        const conversationHistory = messages.map((msg) => ({
          role: msg.role,
          content: msg.content,
        }))

        // Add the new user message
        conversationHistory.push({
          role: 'user',
          content,
        })

        // Make SSE request
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_BASE}/v1/project-creation/chat`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              messages: conversationHistory,
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
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()

          if (done) break

          // Decode chunk and add to buffer
          buffer += decoder.decode(value, { stream: true })

          // Parse complete SSE events (format: "data: {...}\n\n")
          const events = buffer.split('\n\n')
          buffer = events.pop() || '' // Keep incomplete event in buffer

          for (const eventStr of events) {
            const lines = eventStr.split('\n')

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
                      // Strip any markers that might have slipped through (fallback)
                      lastMessage.content = stripMarkers(assistantContent)
                      lastMessage.isStreaming = true
                    }

                    return newMessages
                  })
                } else if (event.type === 'project_created') {
                  // Project was created
                  const project: CreatedProject = event.project
                  setProjectCreated(project)
                  onProjectCreated?.(project)
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
    [messages, isLoading, onError, onProjectCreated]
  )

  const reset = useCallback(() => {
    setMessages([])
    setError(null)
    setProjectCreated(null)
    initializedRef.current = false
    abortControllerRef.current?.abort()
    abortControllerRef.current = null
  }, [])

  return {
    messages,
    isLoading,
    error,
    projectCreated,
    sendMessage,
    initializeChat,
    reset,
  }
}
