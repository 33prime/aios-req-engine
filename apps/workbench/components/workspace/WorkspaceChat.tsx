/**
 * WorkspaceChat - Smart Project Chat
 *
 * Full chat adapted for BrainBubble slide-over:
 * - Message list with streaming
 * - File drag-and-drop
 * - Tool execution indicators (compact)
 * - Dynamic starter cards from context frame actions
 * - Next best actions integration
 */

'use client'

import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import {
  Send,
  Loader2,
  Sparkles,
  CheckCircle2,
  Layers,
  Upload,
  Paperclip,
  Lightbulb,
  ArrowRight,
  ChevronDown,
  MessageSquare,
  FileText,
} from 'lucide-react'
import { Markdown } from '../../components/ui/Markdown'
import { uploadDocument, processDocument, getDocumentStatus } from '@/lib/api'
import type { TerseAction } from '@/lib/api'
import { GAP_SOURCE_ICONS } from '@/lib/action-constants'
import { QuickActionCards } from './QuickActionCards'

// =============================================================================
// Types
// =============================================================================

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

interface WorkspaceChatProps {
  projectId: string
  messages: ChatMessage[]
  isLoading: boolean
  onSendMessage: (content: string) => Promise<void> | void
  onSendSignal?: (type: string, content: string, source: string) => Promise<void>
  onAddLocalMessage?: (msg: ChatMessage) => void
  /** Dynamic actions from context frame for starter cards */
  contextActions?: TerseAction[]
}

// =============================================================================
// Main Component
// =============================================================================

export function WorkspaceChat({
  projectId,
  messages: externalMessages,
  isLoading: externalLoading,
  onSendMessage: externalSendMessage,
  onSendSignal,
  onAddLocalMessage,
  contextActions,
}: WorkspaceChatProps) {
  const [input, setInput] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [uploadingFiles, setUploadingFiles] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [externalMessages])

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  // Handle submit
  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      if (!input.trim() || externalLoading) return
      const trimmedInput = input.trim()
      setInput('')
      externalSendMessage(trimmedInput)
    },
    [input, externalLoading, externalSendMessage]
  )

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSubmit(e)
      }
    },
    [handleSubmit]
  )

  // File upload
  const handleFileSelect = useCallback(() => {
    fileInputRef.current?.click()
  }, [])

  const processFiles = useCallback(
    async (files: File[]) => {
      const allowedTypes = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'image/png', 'image/jpeg', 'image/webp', 'image/gif',
      ]

      const validFiles = files.filter((f) => allowedTypes.includes(f.type))
      if (validFiles.length === 0) {
        onAddLocalMessage?.({
          role: 'assistant',
          content: 'Accepted formats: PDF, DOCX, XLSX, PPTX, or images.',
        })
        return
      }

      setUploadingFiles(true)
      const results: { file: string; success: boolean; error?: string }[] = []
      const documentIds: string[] = []

      for (const file of validFiles) {
        try {
          const response = await uploadDocument(projectId, file)
          results.push({ file: file.name, success: true })
          if (!response.is_duplicate) {
            processDocument(response.id).catch(() => {})
            documentIds.push(response.id)
          }
        } catch (err) {
          results.push({ file: file.name, success: false, error: err instanceof Error ? err.message : 'Failed' })
        }
      }

      setUploadingFiles(false)

      const successCount = results.filter((r) => r.success).length
      const failedFiles = results.filter((r) => !r.success)
      const successNames = results.filter((r) => r.success).map((r) => r.file)

      if (successCount > 0) {
        const bold = successNames.map((n) => `**${n}**`).join(', ')
        onAddLocalMessage?.({
          role: 'assistant',
          content: `Give me a minute to dig into ${bold} — I'll come back with some questions for you.`,
        })
      }
      if (failedFiles.length > 0) {
        const errors = failedFiles.map((f) => `${f.file}: ${f.error}`).join('\n- ')
        onAddLocalMessage?.({ role: 'assistant', content: `Hmm, had trouble with:\n- ${errors}\n\nThe other files are still processing.` })
      }

      // Two-phase polling for processing completion
      if (documentIds.length === 0) return

      for (const docId of documentIds) {
        let attempts = 0
        const maxAttempts = 90 // 3 minutes at 2s intervals
        let phase: 'extraction' | 'entity_analysis' = 'extraction'
        let done = false // Guard against async race conditions

        const poll = setInterval(async () => {
          if (done) return // Prevent overlapping async callbacks
          attempts++
          if (attempts > maxAttempts) {
            done = true
            clearInterval(poll)
            return
          }
          try {
            const status = await getDocumentStatus(docId)
            if (done) return // Re-check after async gap

            if (status.processing_status === 'failed') {
              done = true
              clearInterval(poll)
              return
            }

            // Phase 1: Wait for document extraction to complete
            if (phase === 'extraction') {
              if (status.processing_status === 'completed') {
                // Check if clarification is needed — stop polling if so
                if (status.needs_clarification) {
                  done = true
                  clearInterval(poll)
                  onAddLocalMessage?.({
                    role: 'assistant',
                    content: status.clarification_question || 'I have a question about this document — what type of document is it?',
                  })
                  return
                }

                // Phase 1 done — trigger LLM analysis
                const docClass = status.document_class || 'document'
                const classLabels: Record<string, string> = {
                  prd: 'product requirements doc', transcript: 'meeting transcript',
                  spec: 'technical spec', email: 'email thread', presentation: 'presentation',
                  research: 'research document', process_doc: 'process document',
                }
                const label = classLabels[docClass] || docClass
                const fname = status.original_filename || 'the document'

                // If no signal_id or entity extraction not applicable, this is the final step
                if (!status.signal_id || status.entity_extraction_status === 'not_applicable') {
                  done = true
                  clearInterval(poll)
                  setTimeout(() => {
                    externalSendMessage(
                      `I just uploaded **${fname}** (classified as ${label}). Check the document status and give me a quick take — what's in there?`
                    )
                  }, 500)
                  return
                }

                // Transition to Phase 2 — show progress message and trigger LLM
                phase = 'entity_analysis'
                onAddLocalMessage?.({
                  role: 'assistant',
                  content: `Got it — **${fname}** is a **${label}**. Extracting requirements now, I'll have a full summary shortly...`,
                })
                setTimeout(() => {
                  externalSendMessage(
                    `I just uploaded **${fname}** (classified as ${label}). Check the document status and give me a quick initial take — what's in there? Entity extraction is still running in the background.`
                  )
                }, 500)
              }
            }

            // Phase 2: Wait for V2 entity extraction to complete
            if (phase === 'entity_analysis') {
              if (status.entity_extraction_status === 'completed') {
                done = true
                clearInterval(poll)

                // Show entity counts as an assistant message (not blue user bubble)
                const entities = status.extracted_entities
                const countParts: string[] = []
                if (entities) {
                  if (entities.features.length > 0) countParts.push(`${entities.features.length} features`)
                  if (entities.personas.length > 0) countParts.push(`${entities.personas.length} personas`)
                  if (entities.vp_steps.length > 0) countParts.push(`${entities.vp_steps.length} workflow steps`)
                  if (entities.constraints.length > 0) countParts.push(`${entities.constraints.length} constraints`)
                  if (entities.stakeholders.length > 0) countParts.push(`${entities.stakeholders.length} stakeholders`)
                }
                const fname = status.original_filename || 'document'
                if (countParts.length > 0) {
                  onAddLocalMessage?.({
                    role: 'assistant',
                    content: `Analysis complete for **${fname}** — extracted ${countParts.join(', ')}. You can ask me to review any of these, or check the BRD to see what was added.`,
                  })
                } else {
                  onAddLocalMessage?.({
                    role: 'assistant',
                    content: `Finished analyzing **${fname}**. Check the BRD to see what was extracted.`,
                  })
                }
              }
            }
          } catch {
            done = true
            clearInterval(poll)
          }
        }, 2000)
      }
    },
    [projectId, onAddLocalMessage, externalSendMessage]
  )

  const handleFileInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files || []).slice(0, 5)
      if (files.length > 0) processFiles(files)
      e.target.value = ''
    },
    [processFiles]
  )

  // Drag and drop
  const handleDragOver = useCallback((e: React.DragEvent) => { e.preventDefault(); e.stopPropagation() }, [])
  const handleDragEnter = useCallback((e: React.DragEvent) => { e.preventDefault(); e.stopPropagation(); setIsDragging(true) }, [])
  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation()
    if (e.currentTarget.contains(e.relatedTarget as Node)) return
    setIsDragging(false)
  }, [])
  const handleFileDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault(); e.stopPropagation(); setIsDragging(false)
      const files = Array.from(e.dataTransfer.files).slice(0, 5)
      if (files.length > 0) processFiles(files)
    },
    [processFiles]
  )

  // Determine if thinking (loading but no streamed content yet)
  const lastMessage = externalMessages[externalMessages.length - 1]
  const isThinking = externalLoading && (!lastMessage || lastMessage.role === 'user' || !lastMessage.isStreaming)

  // Build conversational starters — NOT the same as action cards
  // These are chat prompts that help the user start a conversation
  interface StarterCard {
    prompt: string
    label: string
    icon: typeof MessageSquare
  }

  const starterCards = useMemo((): StarterCard[] => {
    const cards: StarterCard[] = []

    if (!contextActions || contextActions.length === 0) {
      return [
        { label: 'Describe the project', prompt: 'Let me tell you about this project...', icon: MessageSquare },
        { label: 'Upload a document', prompt: '', icon: Upload },
        { label: 'What should I focus on?', prompt: 'What should I focus on right now?', icon: Lightbulb },
      ]
    }

    // Always include "what should I focus on" as first option
    cards.push({
      label: 'What should I focus on?',
      prompt: 'What should I focus on right now?',
      icon: Lightbulb,
    })

    // Convert top 2 actions into conversational prompts
    for (const action of contextActions.slice(0, 2)) {
      if (action.cta_type === 'upload_doc') {
        cards.push({ label: 'Upload a document', prompt: '', icon: Upload })
      } else if (action.cta_type === 'inline_answer') {
        cards.push({
          label: action.sentence.length > 50 ? action.sentence.slice(0, 47) + '...' : action.sentence,
          prompt: `Help me with: ${action.sentence}`,
          icon: GAP_SOURCE_ICONS[action.gap_type] || GAP_SOURCE_ICONS[action.gap_source] || MessageSquare,
        })
      } else {
        cards.push({
          label: action.sentence.length > 50 ? action.sentence.slice(0, 47) + '...' : action.sentence,
          prompt: action.sentence,
          icon: GAP_SOURCE_ICONS[action.gap_type] || GAP_SOURCE_ICONS[action.gap_source] || MessageSquare,
        })
      }
    }

    // Always include upload option if not already there
    if (!cards.some(c => c.prompt === '')) {
      cards.push({ label: 'Upload a document', prompt: '', icon: Upload })
    }

    return cards.slice(0, 4)
  }, [contextActions])

  return (
    <div
      className="flex flex-col h-full"
      onDragOver={handleDragOver}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDrop={handleFileDrop}
    >
      {/* Drag overlay */}
      {isDragging && (
        <div className="absolute inset-0 z-50 bg-[#3FAF7A]/5 border-2 border-dashed border-[#3FAF7A] rounded-2xl flex items-center justify-center pointer-events-none">
          <div className="text-center p-4">
            <Upload className="h-8 w-8 text-[#3FAF7A] mx-auto mb-2" />
            <p className="text-sm font-medium text-[#3FAF7A]">Drop files here</p>
            <p className="text-xs text-[#666666] mt-0.5">PDF, DOCX, XLSX, PPTX, images (max 5)</p>
          </div>
        </div>
      )}

      {/* Upload progress overlay */}
      {uploadingFiles && (
        <div className="absolute inset-0 z-50 bg-white/90 flex items-center justify-center">
          <div className="text-center p-4">
            <Loader2 className="h-8 w-8 text-[#3FAF7A] mx-auto mb-2 animate-spin" />
            <p className="text-sm font-medium text-[#333333]">Uploading...</p>
          </div>
        </div>
      )}

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
        {externalMessages.length === 0 ? (
          <div className="flex flex-col items-center justify-start pt-12 h-full px-4">
            {/* Branded empty state */}
            <div className="w-14 h-14 rounded-2xl bg-[#E8F5E9] flex items-center justify-center mb-3">
              <Sparkles className="h-7 w-7 text-[#3FAF7A]" />
            </div>
            <p className="text-[14px] font-semibold text-[#333333] mb-1">AIOS Assistant</p>
            <p className="text-[12px] text-[#666666] text-center mb-4">
              Your AI partner for requirements engineering
            </p>

            {/* Conversational starters */}
            <div className="w-full space-y-2 mb-4">
              {starterCards.map((card, idx) => {
                const Icon = card.icon
                return (
                  <button
                    key={idx}
                    onClick={() => card.prompt === ''
                      ? fileInputRef.current?.click()
                      : externalSendMessage(card.prompt)
                    }
                    className="w-full flex items-center gap-3 p-3 bg-white border border-[#E5E5E5] rounded-2xl hover:border-[#3FAF7A] hover:shadow-sm transition-all text-left group"
                  >
                    <div className="w-8 h-8 rounded-xl bg-[#F4F4F4] flex items-center justify-center flex-shrink-0 group-hover:bg-[#E8F5E9] transition-colors">
                      <Icon className="h-4 w-4 text-[#666666] group-hover:text-[#3FAF7A] transition-colors" />
                    </div>
                    <p className="flex-1 text-[13px] font-medium text-[#333333] min-w-0">{card.label}</p>
                    <ArrowRight className="h-3.5 w-3.5 text-[#E5E5E5] group-hover:text-[#3FAF7A] transition-colors flex-shrink-0" />
                  </button>
                )
              })}
            </div>
          </div>
        ) : (
          <>
            {externalMessages.map((message, index) => (
              <SidebarMessageBubble
                key={message.id || `msg-${index}`}
                message={message}
                onSendMessage={externalSendMessage}
                isLast={index === externalMessages.length - 1}
              />
            ))}

            {/* Thinking indicator */}
            {isThinking && <ThinkingIndicator />}

            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t border-[#E5E5E5] bg-white px-3 py-2.5 flex-shrink-0">
        {/* Hidden file input */}
        <input
          id="workspace-chat-file-input"
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.xlsx,.pptx,.png,.jpg,.jpeg,.webp,.gif"
          className="hidden"
          onChange={handleFileInputChange}
        />

        <form onSubmit={handleSubmit} className="flex items-end gap-1.5">
          <button
            type="button"
            onClick={handleFileSelect}
            className="p-2 text-[#999999] hover:text-[#3FAF7A] hover:bg-[#E8F5E9] rounded-xl transition-colors flex-shrink-0"
            title="Attach file"
          >
            <Paperclip className="h-4 w-4" />
          </button>
          <div className="relative flex-1">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything..."
              disabled={externalLoading}
              rows={1}
              className="w-full px-3 py-2 bg-[#F4F4F4] focus:bg-white border border-[#E5E5E5] rounded-2xl resize-none focus:outline-none focus:ring-2 focus:ring-[#3FAF7A]/20 focus:border-[#3FAF7A] disabled:bg-[#F4F4F4] disabled:text-[#999999] text-[13px]"
              style={{ minHeight: '36px', maxHeight: '80px' }}
            />
          </div>
          <button
            type="submit"
            disabled={!input.trim() || externalLoading}
            className="p-2 bg-[#3FAF7A] hover:bg-[#25785A] text-white rounded-2xl shadow-sm disabled:opacity-50 transition-colors flex-shrink-0"
          >
            {externalLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </button>
        </form>
        <p className="text-[11px] text-[#999999] mt-1.5">
          Enter to send &middot; Drop files to upload
        </p>
      </div>
    </div>
  )
}

// =============================================================================
// Sub-components
// =============================================================================

function ThinkingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="flex items-center gap-2 px-4 py-3 bg-white border border-[#E5E5E5] rounded-2xl rounded-bl-md shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
        <div className="flex gap-1">
          <div className="w-1.5 h-1.5 rounded-full bg-[#3FAF7A] animate-bounce" />
          <div className="w-1.5 h-1.5 rounded-full bg-[#3FAF7A] animate-bounce [animation-delay:150ms]" />
          <div className="w-1.5 h-1.5 rounded-full bg-[#3FAF7A] animate-bounce [animation-delay:300ms]" />
        </div>
        <span className="text-[12px] text-[#999999]">Thinking...</span>
      </div>
    </div>
  )
}

/** Compact message bubble for sidebar */
function SidebarMessageBubble({
  message,
  onSendMessage,
  isLast = false,
}: {
  message: ChatMessage
  onSendMessage?: (msg: string) => void | Promise<void>
  isLast?: boolean
}) {
  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'
  const [showToolDetails, setShowToolDetails] = useState(false)

  const signalResult = message.toolCalls?.find(
    (t) => t.tool_name === 'add_signal' && t.status === 'complete' && t.result?.processed
  )?.result

  // Quick Action Cards (from suggest_actions tool)
  const actionCards = message.toolCalls?.filter(
    (t) => t.tool_name === 'suggest_actions' && t.status === 'complete' && t.result?.cards
  )

  // Auto-convert generate_client_email results into email_draft cards
  const emailResult = message.toolCalls?.find(
    (t) => t.tool_name === 'generate_client_email' && t.status === 'complete' && t.result?.success && t.result?.subject
  )?.result
  const emailCards = emailResult ? [{
    card_type: 'email_draft',
    id: 'email-auto',
    data: { to: emailResult.client_name || 'Client', subject: emailResult.subject, body: emailResult.body }
  }] : null

  // Auto-convert generate_meeting_agenda results into meeting cards
  const meetingResult = message.toolCalls?.find(
    (t) => t.tool_name === 'generate_meeting_agenda' && t.status === 'complete' && t.result?.success && t.result?.agenda
  )?.result
  const meetingCards = meetingResult ? [{
    card_type: 'meeting',
    id: 'meeting-auto',
    data: {
      topic: meetingResult.title || 'Client Meeting',
      attendees: [],
      agenda: (meetingResult.agenda || []).map((a: any) => `${a.topic} (${a.time_minutes}min)`)
    }
  }] : null

  const hasRunningTools = message.toolCalls?.some((t) => t.status === 'running')
  // Filter card-rendered tools from completed tool display
  const cardToolNames = new Set(['suggest_actions'])
  if (emailCards) cardToolNames.add('generate_client_email')
  if (meetingCards) cardToolNames.add('generate_meeting_agenda')
  const visibleToolCalls = cardToolNames.size > 1 || actionCards?.length
    ? message.toolCalls?.filter((t) => !cardToolNames.has(t.tool_name))
    : message.toolCalls
  const completedToolCount = visibleToolCalls?.filter((t) => t.status === 'complete').length || 0

  if (isSystem) return null

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} ${isLast ? 'message-enter' : ''}`}>
      <div className={isUser ? 'max-w-[90%]' : 'w-full'}>
        {/* Message Content */}
        {message.content && (
          <div
            className={
              isUser
                ? 'bg-[#0A1E2F] text-white rounded-2xl rounded-br-md px-4 py-3 shadow-sm ml-auto'
                : 'bg-white border border-[#E5E5E5] rounded-2xl rounded-bl-md px-4 py-3 shadow-[0_1px_2px_rgba(0,0,0,0.04)] text-[#333333]'
            }
          >
            {isUser ? (
              <p className="text-[13px] leading-relaxed whitespace-pre-wrap break-words">{message.content}</p>
            ) : (
              <>
                <Markdown content={message.content} className="text-[13px] leading-relaxed" />
                {message.isStreaming && (
                  <span className="inline-block w-0.5 h-[18px] ml-0.5 bg-[#3FAF7A] rounded-full animate-pulse" />
                )}
              </>
            )}
          </div>
        )}

        {/* Tool Calls — compact */}
        {!isUser && visibleToolCalls && visibleToolCalls.length > 0 && (
          <div className="mt-1.5">
            {hasRunningTools ? (
              /* Running state — inline card */
              <div className="flex items-center gap-2 px-3 py-2 bg-[#F4F4F4] rounded-xl border border-[#E5E5E5]">
                <Loader2 className="h-3.5 w-3.5 animate-spin text-[#3FAF7A]" />
                <span className="text-[11px] text-[#333333]">
                  {getToolDisplayName(message.toolCalls?.find((t) => t.status === 'running')?.tool_name || '')}
                </span>
              </div>
            ) : (
              /* Completed state — inline summary with tool names */
              <button
                onClick={() => setShowToolDetails(!showToolDetails)}
                className="flex items-center gap-1.5 text-[11px] text-[#999999] hover:text-[#333333] transition-colors"
              >
                <CheckCircle2 className="h-3 w-3 text-[#3FAF7A] flex-shrink-0" />
                <span className="truncate">
                  {visibleToolCalls
                    .filter(t => t.status === 'complete')
                    .map(t => getToolDisplayName(t.tool_name))
                    .join(', ')}
                </span>
                <ChevronDown className={`h-2.5 w-2.5 flex-shrink-0 transition-transform ${showToolDetails ? 'rotate-180' : ''}`} />
              </button>
            )}

            {showToolDetails && (
              <div className="mt-1.5 space-y-1 pl-3 border-l-2 border-[#E5E5E5]">
                {visibleToolCalls.map((tool, idx) => (
                  <div
                    key={idx}
                    className="flex items-center gap-1.5 text-[11px] px-2 py-1 rounded-lg"
                  >
                    {tool.status === 'running' ? (
                      <Loader2 className="h-2.5 w-2.5 animate-spin text-[#3FAF7A]" />
                    ) : tool.status === 'error' ? (
                      <div className="w-2.5 h-2.5 rounded-full bg-red-400" />
                    ) : tool.status === 'complete' ? (
                      <CheckCircle2 className="h-2.5 w-2.5 text-[#3FAF7A]" />
                    ) : (
                      <div className="w-2.5 h-2.5 rounded-full bg-[#E5E5E5]" />
                    )}
                    <span className={tool.status === 'error' ? 'text-red-600' : 'text-[#666666]'}>
                      {getToolDisplayName(tool.tool_name)}
                    </span>
                    {tool.status === 'error' && tool.error && (
                      <span className="text-red-500">- {tool.error}</span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Signal Result Card */}
        {signalResult && signalResult.proposal_id && (
          <div className="mt-1.5 border border-[#E5E5E5] rounded-2xl bg-white shadow-sm overflow-hidden">
            <div className="flex items-center gap-2 px-3 py-2 bg-[#F4F4F4] border-b border-[#E5E5E5]">
              <Layers className="h-3.5 w-3.5 text-[#3FAF7A]" />
              <span className="text-xs font-medium text-[#333333]">
                Proposal: {signalResult.total_changes || 0} changes
              </span>
            </div>
            <div className="flex items-center gap-1.5 px-3 py-2">
              <button
                onClick={() => onSendMessage?.(`Apply proposal ${signalResult.proposal_id}`)}
                className="px-3 py-1.5 bg-[#3FAF7A] hover:bg-[#25785A] text-white text-[11px] font-medium rounded-xl transition-colors flex items-center gap-1"
              >
                <CheckCircle2 className="h-3 w-3" />
                Apply
              </button>
              <button
                onClick={() => onSendMessage?.(`Discard proposal ${signalResult.proposal_id}`)}
                className="px-3 py-1.5 bg-[#F0F0F0] hover:bg-[#E5E5E5] text-[#666666] text-[11px] font-medium rounded-xl transition-colors"
              >
                Discard
              </button>
            </div>
          </div>
        )}

        {/* Quick Action Cards (from suggest_actions + auto-converted tool results) */}
        {actionCards?.map((tc, i) => (
          <QuickActionCards
            key={`actions-${i}`}
            cards={tc.result.cards}
            onAction={(command) => onSendMessage?.(command)}
          />
        ))}
        {emailCards && (
          <QuickActionCards cards={emailCards} onAction={(command) => onSendMessage?.(command)} />
        )}
        {meetingCards && (
          <QuickActionCards cards={meetingCards} onAction={(command) => onSendMessage?.(command)} />
        )}

        {/* Timestamp */}
        {message.timestamp && (
          <p className="text-[10px] text-[#999999] mt-0.5">
            {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </p>
        )}
      </div>
    </div>
  )
}

function getToolDisplayName(toolName: string): string {
  const names: Record<string, string> = {
    generate_strategic_context: 'Strategic context',
    get_strategic_context: 'Fetching context',
    identify_stakeholders: 'Finding stakeholders',
    search: 'Searching',
    get_project_status: 'Project status',
    add_signal: 'Processing signal',
    generate_meeting_agenda: 'Meeting agenda',
    generate_client_email: 'Drafting email',
    create_entity: 'Creating entity',
    update_entity: 'Updating entity',
    update_strategic_context: 'Updating context',
    create_task: 'Creating task',
    suggest_actions: 'Suggesting actions',
  }
  return names[toolName] || toolName.replace(/_/g, ' ')
}

export default WorkspaceChat
