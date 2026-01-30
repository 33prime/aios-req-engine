/**
 * SmartProjectCreation Component
 *
 * AI-powered chat interface for creating new projects.
 * Uses Claude Haiku 3.5 for fast, intelligent conversations.
 *
 * Features:
 * - Full-screen chat modal with emerald gradient header
 * - Both AI and user messages with icons on left
 * - Smooth SSE streaming with animations
 * - Markdown rendering (bold, bullets)
 * - Automatic project creation when conversation completes
 */

'use client'

import { useState, useEffect, useRef, FormEvent, useMemo } from 'react'
import { X, Lightbulb, Sparkles, User, ArrowRight } from 'lucide-react'
import { useProjectCreationChat, type CreatedProject } from '@/lib/useProjectCreationChat'

/**
 * Simple markdown renderer for chat messages.
 * Handles: **bold**, bullet points (- or •), and line breaks.
 */
function renderMarkdown(text: string): React.ReactNode {
  if (!text) return null

  // Split into lines
  const lines = text.split('\n')
  const elements: React.ReactNode[] = []

  lines.forEach((line, lineIndex) => {
    // Check if it's a bullet point
    const bulletMatch = line.match(/^(\s*)([-•])\s+(.*)$/)

    if (bulletMatch) {
      const [, indent, , content] = bulletMatch
      const indentLevel = Math.floor(indent.length / 2)

      elements.push(
        <div
          key={lineIndex}
          className="flex items-start gap-2"
          style={{ marginLeft: `${indentLevel * 16}px` }}
        >
          <span className="text-[#009b87] mt-0.5">•</span>
          <span>{renderInlineMarkdown(content)}</span>
        </div>
      )
    } else if (line.trim() === '') {
      // Empty line - add spacing
      elements.push(<div key={lineIndex} className="h-2" />)
    } else {
      // Regular line
      elements.push(
        <div key={lineIndex}>{renderInlineMarkdown(line)}</div>
      )
    }
  })

  return <>{elements}</>
}

/**
 * Render inline markdown (bold text).
 */
function renderInlineMarkdown(text: string): React.ReactNode {
  if (!text) return null

  // Split by **bold** markers
  const parts = text.split(/(\*\*[^*]+\*\*)/g)

  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      // Bold text
      return (
        <strong key={index} className="font-semibold">
          {part.slice(2, -2)}
        </strong>
      )
    }
    return part
  })
}

interface SmartProjectCreationProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: (project: { id: string; name: string; onboarding_job_id?: string }) => void
}

export function SmartProjectCreation({ isOpen, onClose, onSuccess }: SmartProjectCreationProps) {
  const {
    messages,
    isLoading,
    projectCreated,
    sendMessage,
    initializeChat,
    reset,
  } = useProjectCreationChat({
    onError: (error) => {
      console.error('Project creation chat error:', error)
    },
    onProjectCreated: () => {},
  })

  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Initialize chat when modal opens
  useEffect(() => {
    if (isOpen) {
      reset()
      initializeChat()
    }
  }, [isOpen, reset, initializeChat])

  // Handle project creation success
  useEffect(() => {
    if (projectCreated) {
      // Small delay to let the final message display
      const timer = setTimeout(() => {
        onSuccess({
          id: projectCreated.id,
          name: projectCreated.name,
          onboarding_job_id: projectCreated.onboarding_job_id,
        })
      }, 1500)

      return () => clearTimeout(timer)
    }
  }, [projectCreated, onSuccess])

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return
    sendMessage(input.trim())
    setInput('')
  }

  const handleClose = () => {
    reset()
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50">
      {/* Frosted blur backdrop */}
      <div
        className="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4"
        onClick={handleClose}
      >
        {/* Modal — 25% smaller */}
        <div
          className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full h-[66vh] flex flex-col overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header with emerald gradient */}
          <div className="relative bg-gradient-to-r from-emerald-600 to-emerald-400 px-4 py-3.5 text-white flex-shrink-0">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-full bg-white bg-opacity-20 backdrop-blur-sm flex items-center justify-center">
                  <Lightbulb className="w-4.5 h-4.5" />
                </div>
                <h2 className="text-base font-bold">AI Assistant</h2>
              </div>
              <button
                onClick={handleClose}
                className="text-white hover:text-gray-200 transition-colors p-1.5"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Messages area - gray background */}
          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-2.5 bg-gray-50">
            {messages.map((msg) => (
              <div key={msg.id} className="flex items-start message-enter">
                <div className="flex-1 max-w-2xl">
                  {msg.role === 'assistant' ? (
                    /* AI Message - emerald bubble with sparkle icon */
                    <div className="bg-emerald-50 rounded-xl px-3.5 py-3 shadow-sm border border-emerald-100">
                      <div className="flex items-start gap-2.5">
                        <div className="w-6 h-6 rounded-full bg-white flex items-center justify-center flex-shrink-0">
                          <Sparkles className="w-3.5 h-3.5 text-[#009b87]" />
                        </div>
                        <div className="flex-1 text-[13px] leading-relaxed text-gray-700">
                          {renderMarkdown(msg.content)}
                        </div>
                      </div>
                    </div>
                  ) : (
                    /* User Message - white bubble with person icon */
                    <div className="bg-white rounded-xl px-3.5 py-3 shadow-sm border border-gray-200">
                      <div className="flex items-start gap-2.5">
                        <div className="w-6 h-6 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0">
                          <User className="w-3.5 h-3.5 text-gray-600" />
                        </div>
                        <div className="flex-1 text-[13px] leading-relaxed text-gray-700 whitespace-pre-wrap">
                          {msg.content}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* Typing indicator - only show if loading AND no streaming message exists */}
            {isLoading && !messages.some(m => m.isStreaming) && (
              <div className="flex items-start message-enter">
                <div className="flex-1 max-w-2xl">
                  <div className="bg-emerald-50 rounded-xl px-3.5 py-3 shadow-sm border border-emerald-100">
                    <div className="flex items-start gap-2.5">
                      <div className="w-6 h-6 rounded-full bg-white flex items-center justify-center flex-shrink-0">
                        <Sparkles className="w-3.5 h-3.5 text-[#009b87]" />
                      </div>
                      <div className="flex gap-1 pt-1.5">
                        <div
                          className="w-1.5 h-1.5 bg-[#009b87] rounded-full animate-bounce"
                          style={{ animationDelay: '0ms' }}
                        />
                        <div
                          className="w-1.5 h-1.5 bg-[#009b87] rounded-full animate-bounce"
                          style={{ animationDelay: '150ms' }}
                        />
                        <div
                          className="w-1.5 h-1.5 bg-[#009b87] rounded-full animate-bounce"
                          style={{ animationDelay: '300ms' }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Project created success message */}
            {projectCreated && (
              <div className="flex items-start message-enter">
                <div className="flex-1 max-w-2xl">
                  <div className="bg-emerald-100 rounded-xl px-3.5 py-3 shadow-sm border border-emerald-200">
                    <div className="flex items-start gap-2.5">
                      <div className="w-6 h-6 rounded-full bg-emerald-500 flex items-center justify-center flex-shrink-0">
                        <svg className="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                      <div className="flex-1">
                        <p className="text-[13px] font-medium text-emerald-800">
                          Project "{projectCreated.name}" created successfully!
                        </p>
                        <p className="text-[11px] text-emerald-600 mt-0.5">
                          Redirecting to your new workspace...
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input area */}
          <form
            onSubmit={handleSubmit}
            className="border-t border-gray-200 px-4 py-3.5 bg-white flex-shrink-0"
          >
            <div className="flex items-center gap-2.5">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Write your answer"
                className="flex-1 px-3.5 py-2.5 border border-gray-300 rounded-lg text-[13px] focus:outline-none focus:ring-2 focus:ring-[#009b87] focus:border-transparent transition-all"
                disabled={isLoading || !!projectCreated}
                autoFocus
              />
              <button
                type="submit"
                disabled={!input.trim() || isLoading || !!projectCreated}
                className="px-4 py-2.5 bg-[#009b87] text-white rounded-lg hover:bg-[#007a6b] transition-colors font-medium flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
