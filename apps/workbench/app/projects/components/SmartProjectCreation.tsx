/**
 * SmartProjectCreation Component
 *
 * AI-powered chat interface for creating new projects.
 * Uses Claude Haiku 3.5 for fast, intelligent conversations.
 *
 * Features:
 * - Full-screen chat modal with navy gradient header
 * - Navy user bubbles (right-aligned), white assistant cards (left-aligned)
 * - Smooth SSE streaming with animations
 * - Markdown rendering (bold, bullets)
 * - Automatic project creation when conversation completes
 */

'use client'

import { useState, useEffect, useRef, FormEvent, useMemo } from 'react'
import { X, Lightbulb, ArrowRight } from 'lucide-react'
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
          <span className="text-[#3FAF7A] mt-0.5">•</span>
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
        {/* Modal */}
        <div
          className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full h-[66vh] flex flex-col overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header with navy gradient */}
          <div className="relative bg-gradient-to-r from-[#0A1E2F] to-[#0D2A35] px-4 py-3.5 text-white flex-shrink-0">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-10 h-10 rounded-2xl bg-white/10 backdrop-blur-sm flex items-center justify-center">
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

          {/* Messages area */}
          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-2.5 bg-[#F4F4F4]">
            {messages.map((msg) => (
              <div key={msg.id} className={`flex items-start message-enter ${msg.role === 'user' ? 'justify-end' : ''}`}>
                <div className="max-w-[80%]">
                  {msg.role === 'assistant' ? (
                    /* AI Message — white card */
                    <div className="bg-white border border-[#E5E5E5] rounded-2xl rounded-bl-md px-4 py-3 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
                      <div className="text-[13px] leading-relaxed text-[#333333]">
                        {renderMarkdown(msg.content)}
                      </div>
                    </div>
                  ) : (
                    /* User Message — navy bubble */
                    <div className="bg-[#0A1E2F] text-white rounded-2xl rounded-br-md px-4 py-3 shadow-sm">
                      <div className="text-[13px] leading-relaxed whitespace-pre-wrap">
                        {msg.content}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* Typing indicator */}
            {isLoading && !messages.some(m => m.isStreaming) && (
              <div className="flex items-start message-enter">
                <div className="max-w-[80%]">
                  <div className="bg-white border border-[#E5E5E5] rounded-2xl rounded-bl-md px-4 py-3 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
                    <div className="flex items-center gap-2">
                      <div className="flex gap-1">
                        <div
                          className="w-1.5 h-1.5 bg-[#3FAF7A] rounded-full animate-bounce"
                          style={{ animationDelay: '0ms' }}
                        />
                        <div
                          className="w-1.5 h-1.5 bg-[#3FAF7A] rounded-full animate-bounce"
                          style={{ animationDelay: '150ms' }}
                        />
                        <div
                          className="w-1.5 h-1.5 bg-[#3FAF7A] rounded-full animate-bounce"
                          style={{ animationDelay: '300ms' }}
                        />
                      </div>
                      <span className="text-[12px] text-[#999999]">Thinking...</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Project created success message */}
            {projectCreated && (
              <div className="flex items-start message-enter">
                <div className="max-w-[80%]">
                  <div className="bg-[#E8F5E9] border border-[#3FAF7A]/20 rounded-2xl rounded-bl-md px-4 py-3">
                    <div className="flex items-start gap-2.5">
                      <div className="w-6 h-6 rounded-full bg-[#3FAF7A] flex items-center justify-center flex-shrink-0">
                        <svg className="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                      <div className="flex-1">
                        <p className="text-[13px] font-medium text-[#333333]">
                          Project &ldquo;{projectCreated.name}&rdquo; created successfully!
                        </p>
                        <p className="text-[11px] text-[#666666] mt-0.5">
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
            className="border-t border-[#E5E5E5] px-4 py-3.5 bg-white flex-shrink-0"
          >
            <div className="flex items-center gap-2.5">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Write your answer"
                className="flex-1 px-3.5 py-2.5 bg-[#F4F4F4] focus:bg-white border border-[#E5E5E5] rounded-2xl text-[13px] focus:outline-none focus:ring-2 focus:ring-[#3FAF7A]/20 focus:border-[#3FAF7A] transition-all"
                disabled={isLoading || !!projectCreated}
                autoFocus
              />
              <button
                type="submit"
                disabled={!input.trim() || isLoading || !!projectCreated}
                className="px-4 py-2.5 bg-[#3FAF7A] text-white rounded-2xl hover:bg-[#25785A] transition-colors font-medium flex items-center gap-1.5 shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
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
