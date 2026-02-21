'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import {
  Send,
  Loader2,
  MessageCircle,
  CheckCircle2,
  Sparkles,
  ArrowUpRight,
  Plus,
  Trash2,
  Shuffle,
  ChevronDown,
  ChevronRight,
  Paperclip,
  X,
} from 'lucide-react'
import { Markdown } from '@/components/ui/Markdown'
import { useChat, type ChatMessage } from '@/lib/useChat'
import { uploadDocument, processDocument, getDocumentStatus } from '@/lib/api'
import type { FlowOpenQuestion } from '@/types/workspace'

// Tools that mutate solution flow data — trigger cascade on completion
const MUTATING_TOOLS = new Set([
  'update_solution_flow_step',
  'add_solution_flow_step',
  'remove_solution_flow_step',
  'reorder_solution_flow_steps',
  'resolve_solution_flow_question',
  'escalate_to_client',
  'refine_solution_flow_step',
])

interface FlowStepChatProps {
  projectId: string
  stepId: string
  stepTitle: string
  openQuestions?: FlowOpenQuestion[]
  onToolResult?: (toolName: string, result: any) => void
}

export function FlowStepChat({
  projectId,
  stepId,
  stepTitle,
  openQuestions = [],
  onToolResult,
}: FlowStepChatProps) {
  const [input, setInput] = useState('')
  const [solvingQuestion, setSolvingQuestion] = useState<FlowOpenQuestion | null>(null)
  const [resolvedFlash, setResolvedFlash] = useState(false)
  const [questionListOpen, setQuestionListOpen] = useState(false)
  const [uploadingFiles, setUploadingFiles] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const processedToolCountRef = useRef(0)

  const {
    messages,
    isLoading,
    sendMessage,
    addLocalMessage,
  } = useChat({
    projectId,
    pageContext: 'brd:solution-flow',
    focusedEntity: {
      type: 'solution_flow_step',
      data: { id: stepId, title: stepTitle },
    },
  })

  const activeQuestions = openQuestions.filter(q => q.status === 'open')

  // Reset state when step changes
  useEffect(() => {
    processedToolCountRef.current = 0
    setSolvingQuestion(null)
    setResolvedFlash(false)
    setQuestionListOpen(false)
  }, [stepId])

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Detect tool completions and fire cascade callback + auto-advance
  useEffect(() => {
    if (!onToolResult) return
    const allToolCalls = messages.flatMap(m =>
      m.role === 'assistant' ? (m.toolCalls || []) : []
    )
    const newCompletions = allToolCalls.slice(processedToolCountRef.current)
    for (const tc of newCompletions) {
      if (tc.status === 'complete' && tc.result?.success && MUTATING_TOOLS.has(tc.tool_name)) {
        onToolResult(tc.tool_name, tc.result)

        // Auto-advance: show resolved flash then pick next question
        if (tc.tool_name === 'resolve_solution_flow_question') {
          setResolvedFlash(true)
          setSolvingQuestion(null)
          setTimeout(() => {
            setResolvedFlash(false)
            // Auto-advance to next open question
            const remaining = activeQuestions.filter(
              q => q.question !== tc.result?.question_text
            )
            if (remaining.length > 0) {
              setSolvingQuestion(remaining[0])
            }
          }, 1500)
        }
      }
    }
    processedToolCountRef.current = allToolCalls.length
  }, [messages, onToolResult, activeQuestions])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return
    const msg = input.trim()
    setInput('')
    await sendMessage(msg)
  }

  // "Solve" flow — user clicks solve on a question
  const handleSolveQuestion = (q: FlowOpenQuestion) => {
    setSolvingQuestion(q)
    setQuestionListOpen(false)
  }

  const handleCancelSolve = () => {
    setSolvingQuestion(null)
  }

  // "Ask Client →" flow
  const handleAskClient = async (q: FlowOpenQuestion) => {
    if (isLoading) return
    setQuestionListOpen(false)
    await sendMessage(
      `I need to escalate the question "${q.question}" to the client. Can you suggest who would know this and escalate it?`
    )
  }

  // File upload
  const processFiles = useCallback(async (files: File[]) => {
    const allowedTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      'image/png', 'image/jpeg', 'image/webp', 'image/gif',
    ]
    const validFiles = files.filter(f => allowedTypes.includes(f.type))
    if (validFiles.length === 0) {
      addLocalMessage({ role: 'assistant', content: 'Accepted formats: PDF, DOCX, XLSX, PPTX, or images.' })
      return
    }
    setUploadingFiles(true)
    const docIds: string[] = []
    for (const file of validFiles) {
      try {
        const resp = await uploadDocument(projectId, file)
        if (!resp.is_duplicate) {
          processDocument(resp.id).catch(() => {})
          docIds.push(resp.id)
        }
        addLocalMessage({
          role: 'assistant',
          content: `Analyzing **${file.name}** in the context of this step...`,
        })
      } catch {
        addLocalMessage({ role: 'assistant', content: `Failed to upload ${file.name}.` })
      }
    }
    setUploadingFiles(false)

    // Poll for completion then auto-send analysis prompt
    for (const docId of docIds) {
      let attempts = 0
      const poll = setInterval(async () => {
        attempts++
        if (attempts > 60) { clearInterval(poll); return }
        try {
          const status = await getDocumentStatus(docId)
          if (status.processing_status === 'completed') {
            clearInterval(poll)
            const fname = status.original_filename || 'the document'
            await sendMessage(
              `I uploaded **${fname}** for the step "${stepTitle}". Update the step with any relevant findings — information fields, actors, and open questions. Apply changes directly.`
            )
          } else if (status.processing_status === 'failed') {
            clearInterval(poll)
          }
        } catch { clearInterval(poll) }
      }, 2000)
    }
  }, [projectId, stepTitle, addLocalMessage, sendMessage])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []).slice(0, 3)
    if (files.length > 0) processFiles(files)
    e.target.value = ''
  }, [processFiles])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation(); setIsDragging(true)
  }, [])
  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation(); setIsDragging(false)
  }, [])
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation(); setIsDragging(false)
    const files = Array.from(e.dataTransfer.files).slice(0, 3)
    if (files.length > 0) processFiles(files)
  }, [processFiles])

  return (
    <div
      className={`flex flex-col h-full bg-[#FAFAFA] ${isDragging ? 'ring-2 ring-[#3FAF7A] ring-inset' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Chat header with compact question counter */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#E5E5E5] bg-white shrink-0">
        <div className="flex items-center gap-2">
          <MessageCircle className="w-3.5 h-3.5 text-[#999999]" />
          <span className="text-[11px] font-medium text-[#999999] uppercase tracking-wider">Step Chat</span>
        </div>

        {/* Question counter strip */}
        {activeQuestions.length > 0 && !solvingQuestion && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => setQuestionListOpen(!questionListOpen)}
              className="flex items-center gap-1.5 text-[11px] font-medium text-[#A08050] hover:text-[#8B7355]"
            >
              <span className="w-4.5 h-4.5 flex items-center justify-center rounded bg-[#EDE8D5] text-[10px] font-bold text-[#8B7355] px-1">
                {activeQuestions.length}
              </span>
              open question{activeQuestions.length !== 1 ? 's' : ''}
            </button>
            <button
              onClick={() => handleSolveQuestion(activeQuestions[0])}
              disabled={isLoading}
              className="text-[11px] font-semibold text-[#25785A] hover:text-[#1A5C43] disabled:opacity-50"
            >
              Solve next &rarr;
            </button>
          </div>
        )}
      </div>

      {/* Expandable question list dropdown */}
      {questionListOpen && activeQuestions.length > 0 && (
        <div className="px-3 py-2 border-b border-[#E5E5E5] bg-white shrink-0 max-h-[200px] overflow-y-auto">
          <div className="space-y-1.5">
            {activeQuestions.map((q, i) => (
              <div
                key={i}
                className="rounded-lg border border-[#E5E5E5] bg-[#FAFAFA] px-3 py-2"
              >
                <p className="text-[12px] text-[#333333] leading-snug mb-1.5">{q.question}</p>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleSolveQuestion(q)}
                    disabled={isLoading}
                    className="text-[11px] font-medium text-[#25785A] hover:text-[#1A5C43] disabled:opacity-50"
                  >
                    Solve
                  </button>
                  <span className="text-[#E5E5E5]">|</span>
                  <button
                    onClick={() => handleAskClient(q)}
                    disabled={isLoading}
                    className="text-[11px] font-medium text-[#666666] hover:text-[#333333] flex items-center gap-0.5 disabled:opacity-50"
                  >
                    Ask Client <ArrowUpRight className="w-3 h-3" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 min-h-0">
        {messages.length === 0 && activeQuestions.length === 0 && (
          <div className="text-center text-xs text-[#BBBBBB] py-8">
            Ask about this step, update fields, or resolve questions
          </div>
        )}

        {messages.map((msg, i) => (
          <MessageBubble key={msg.id || i} message={msg} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        accept=".pdf,.docx,.xlsx,.pptx,.png,.jpg,.jpeg,.webp"
        multiple
        onChange={handleFileSelect}
      />

      {/* Resolved flash */}
      {resolvedFlash && (
        <div className="px-4 py-2 bg-[#F0FFF4] border-t border-[#3FAF7A]/20 shrink-0 flex items-center gap-2">
          <CheckCircle2 className="w-3.5 h-3.5 text-[#3FAF7A]" />
          <span className="text-[12px] font-medium text-[#25785A]">Resolved</span>
        </div>
      )}

      {/* Solving question prompt — above input, not top banner */}
      {solvingQuestion && !resolvedFlash && (
        <div className="px-3 py-2 bg-[#EDE8D5]/40 border-t border-[#C4A97D]/20 shrink-0">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <div className="text-[10px] uppercase tracking-wider text-[#A08050] mb-0.5 font-medium">
                Answering
              </div>
              <p className="text-[12px] text-[#333333] leading-snug">{solvingQuestion.question}</p>
            </div>
            <button
              onClick={handleCancelSolve}
              className="shrink-0 mt-0.5 text-[#BBBBBB] hover:text-[#999999]"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Input bar */}
      <form onSubmit={handleSubmit} className="flex items-center gap-2 px-3 py-2.5 border-t border-[#E5E5E5] bg-white">
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploadingFiles || isLoading}
          className="w-8 h-8 flex items-center justify-center rounded-lg text-[#999999] hover:text-[#666666] hover:bg-[#F4F4F4] transition-colors disabled:opacity-30"
          title="Upload file"
        >
          {uploadingFiles ? <Loader2 className="w-4 h-4 animate-spin" /> : <Paperclip className="w-4 h-4" />}
        </button>
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder={solvingQuestion ? 'Your answer...' : 'Refine this step...'}
          className="flex-1 text-[13px] px-3 py-2 rounded-lg bg-[#F4F4F4] border border-[#E5E5E5] focus:outline-none focus:border-[#3FAF7A]/40 focus:ring-1 focus:ring-[#3FAF7A]/10 placeholder:text-[#BBBBBB]"
          disabled={isLoading}
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey && solvingQuestion && input.trim()) {
              e.preventDefault()
              const answer = input.trim()
              const qRef = solvingQuestion.question.length > 50
                ? solvingQuestion.question.slice(0, 50) + '...'
                : solvingQuestion.question
              setInput('')
              sendMessage(`${answer}\n\n[resolve: ${qRef}]`)
            }
          }}
        />
        <button
          type="submit"
          disabled={!input.trim() || isLoading}
          className="w-8 h-8 flex items-center justify-center rounded-lg bg-[#0A1E2F] text-white disabled:opacity-30 hover:bg-[#0D2A35] transition-colors"
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
        </button>
      </form>
    </div>
  )
}

// =============================================================================
// Message Bubble with Markdown + Inline Result Cards
// =============================================================================

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'
  const [toolsExpanded, setToolsExpanded] = useState(false)

  const toolCalls = message.toolCalls || []
  const completedTools = toolCalls.filter(tc => tc.status === 'complete')
  const runningTools = toolCalls.filter(tc => tc.status === 'running' || tc.status === 'pending')

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[90%] rounded-xl px-3 py-2 text-[13px] leading-relaxed ${
          isUser
            ? 'bg-[#0A1E2F] text-white'
            : 'bg-white border border-[#E5E5E5] text-[#333333]'
        }`}
      >
        {/* Message content — Markdown for assistant, plain for user */}
        {isUser ? (
          message.content
        ) : (
          message.content && <Markdown content={message.content} className="text-[13px] leading-relaxed" />
        )}

        {/* Running tool indicators */}
        {runningTools.map((tc, i) => (
          <div key={`run-${i}`} className="mt-1.5 text-[11px] flex items-center gap-1 text-[#999999]">
            <Loader2 className="w-3 h-3 animate-spin" />
            {tc.tool_name.replace(/_/g, ' ')}
          </div>
        ))}

        {/* Completed tool summary — collapsible */}
        {completedTools.length > 0 && (
          <div className="mt-1.5">
            <button
              onClick={() => setToolsExpanded(!toolsExpanded)}
              className={`text-[11px] flex items-center gap-1 ${isUser ? 'text-white/50' : 'text-[#999999]'} hover:opacity-80`}
            >
              {toolsExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
              {completedTools.length} tool{completedTools.length !== 1 ? 's' : ''} completed
            </button>
            {toolsExpanded && completedTools.map((tc, i) => (
              <div key={`done-${i}`} className={`mt-0.5 text-[11px] flex items-center gap-1 ${isUser ? 'text-white/40' : 'text-[#BBBBBB]'}`}>
                <span className="text-[#3FAF7A]">&#x2713;</span>
                {tc.tool_name.replace(/_/g, ' ')}
              </div>
            ))}
          </div>
        )}

        {/* Inline result cards for completed mutating tools */}
        {completedTools.map((tc, i) => (
          <ToolResultCard key={`card-${i}`} toolName={tc.tool_name} result={tc.result} />
        ))}
      </div>
    </div>
  )
}

// =============================================================================
// Inline Tool Result Cards
// =============================================================================

function ToolResultCard({ toolName, result }: { toolName: string; result?: any }) {
  if (!result?.success) return null

  switch (toolName) {
    case 'resolve_solution_flow_question':
      return (
        <div className="mt-2 rounded-lg border-l-[3px] border-[#3FAF7A] bg-[#F0FFF4] px-3 py-2 text-[12px]">
          <div className="flex items-center gap-1.5 font-medium text-[#25785A]">
            <CheckCircle2 className="w-3.5 h-3.5" /> Question Resolved
          </div>
          {result.answer && <p className="mt-1 text-[#4A5568]">{result.answer}</p>}
        </div>
      )

    case 'update_solution_flow_step':
      return (
        <div className="mt-2 rounded-lg border-l-[3px] border-[#3FAF7A] bg-[#F0FFF4] px-3 py-2 text-[12px]">
          <div className="flex items-center gap-1.5 font-medium text-[#25785A]">
            <CheckCircle2 className="w-3.5 h-3.5" /> Updated: {(result.updated_fields || []).join(', ')}
          </div>
        </div>
      )

    case 'refine_solution_flow_step':
      return (
        <div className="mt-2 rounded-lg border-l-[3px] border-[#3FAF7A] bg-[#F0FFF4] px-3 py-2 text-[12px]">
          <div className="flex items-center gap-1.5 font-medium text-[#25785A]">
            <Sparkles className="w-3.5 h-3.5" /> Refined: {result.changes_summary || 'step updated'}
          </div>
        </div>
      )

    case 'escalate_to_client':
      return (
        <div className="mt-2 rounded-lg border-l-[3px] border-[#C4A97D] bg-[#FFFBF0] px-3 py-2 text-[12px]">
          <div className="flex items-center gap-1.5 font-medium text-[#8B7355]">
            <ArrowUpRight className="w-3.5 h-3.5" /> Queued for {result.escalated_to || 'client'}
          </div>
        </div>
      )

    case 'add_solution_flow_step':
      return (
        <div className="mt-2 rounded-lg border-l-[3px] border-[#3FAF7A] bg-[#F0FFF4] px-3 py-2 text-[12px]">
          <div className="flex items-center gap-1.5 font-medium text-[#25785A]">
            <Plus className="w-3.5 h-3.5" /> Added step: {result.title || 'new step'}
          </div>
        </div>
      )

    case 'remove_solution_flow_step':
      return (
        <div className="mt-2 rounded-lg border-l-[3px] border-[#E5E5E5] bg-[#FAFAFA] px-3 py-2 text-[12px]">
          <div className="flex items-center gap-1.5 font-medium text-[#999999]">
            <Trash2 className="w-3.5 h-3.5" /> Step removed
          </div>
        </div>
      )

    case 'reorder_solution_flow_steps':
      return (
        <div className="mt-2 rounded-lg border-l-[3px] border-[#3FAF7A] bg-[#F0FFF4] px-3 py-2 text-[12px]">
          <div className="flex items-center gap-1.5 font-medium text-[#25785A]">
            <Shuffle className="w-3.5 h-3.5" /> Steps reordered
          </div>
        </div>
      )

    default:
      return null
  }
}
