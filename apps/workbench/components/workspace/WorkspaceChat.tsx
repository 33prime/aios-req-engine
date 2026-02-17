/**
 * WorkspaceChat - Premium AI Command Center
 *
 * Full chat adapted for sidebar context:
 * - Message list with streaming
 * - Slash command autocomplete
 * - File drag-and-drop
 * - Tool execution indicators (compact)
 * - Proactive message cards
 * - Quick action row (scrollable)
 * - Inline prompts for /create-task, /create-stakeholder, /remember
 * - Next best actions integration
 */

'use client'

import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import {
  Send,
  Loader2,
  X,
  Sparkles,
  CheckCircle2,
  Layers,
  Upload,
  Paperclip,
  Zap,
  Lightbulb,
  ArrowRight,
  Target,
  Users,
  FileText,
  ChevronDown,
} from 'lucide-react'
import { Markdown } from '../../components/ui/Markdown'
import {
  useAssistant,
  type QuickAction,
  type ProactiveMessage,
  type CommandDefinition,
  getModeConfig,
} from '@/lib/assistant'
import { uploadDocument, processDocument, getNextActions, type NextAction } from '@/lib/api'
import { ACTION_ICONS } from '@/lib/action-constants'

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
}

// =============================================================================
// Constants
// =============================================================================

const ACTION_COMMANDS: Record<string, (a: NextAction) => string> = {
  confirm_critical: () => 'Help me review and confirm the must-have features',
  stakeholder_gap: (a) => `Help me identify a ${a.suggested_stakeholder_role} for this project`,
  section_gap: (a) => `Help me improve the ${a.target_entity_type?.replace(/_/g, ' ')} section`,
  missing_evidence: () => 'What evidence do we need to gather for unsupported features?',
  validate_pains: () => 'Help me validate the high-severity pain points with stakeholders',
  missing_vision: () => 'Help me draft a vision statement for this project',
  missing_metrics: () => 'Help me define success metrics and KPIs for this project',
  open_question_critical: (a) => `Help me resolve this critical question: ${a.title}`,
  open_question_blocking: (a) => `Help me answer this open question: ${a.title}`,
  stale_belief: (a) => `Help me verify this assumption: ${a.title}`,
  revisit_decision: (a) => `Help me revisit this decision: ${a.title}`,
  contradiction_unresolved: () => 'Help me resolve the contradictions in our knowledge graph',
  cross_entity_gap: (a) => `Help me find a ${a.suggested_stakeholder_role} to validate the evidence gap`,
  temporal_stale: () => 'Help me review stale features that need updating',
}

const STARTER_CARDS = [
  { icon: Target, label: 'Review features', hint: 'Confirm must-have priorities', command: '/status' },
  { icon: Users, label: 'Add stakeholder', hint: 'Track key people', command: '/create-stakeholder' },
  { icon: FileText, label: 'Upload document', hint: 'Feed in signals', command: null },
  { icon: Lightbulb, label: 'Discover gaps', hint: 'Find what\'s missing', command: '/discover-check' },
]

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
}: WorkspaceChatProps) {
  const [input, setInput] = useState('')
  const [showCommandSuggestions, setShowCommandSuggestions] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const [uploadingFiles, setUploadingFiles] = useState(false)
  const [activePrompt, setActivePrompt] = useState<{
    type: 'create-task' | 'create-stakeholder' | 'remember'
    step?: 'type' | 'content'
    memoryType?: 'decision' | 'learning' | 'question'
  } | null>(null)
  const [promptInput, setPromptInput] = useState('')
  const [promptSubmitting, setPromptSubmitting] = useState(false)
  const [nextActions, setNextActions] = useState<NextAction[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const promptInputRef = useRef<HTMLInputElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const prevLoading = useRef(externalLoading)

  // Assistant hook
  const {
    context,
    sendMessage: assistantSendMessage,
    isCommand,
    getCommandSuggestions,
    getQuickActions,
    executeQuickAction,
    dismissProactiveMessage,
    setActiveTab: setAssistantTab,
  } = useAssistant()

  const modeConfig = useMemo(() => getModeConfig(context.mode), [context.mode])

  // Fetch next actions on mount
  useEffect(() => {
    getNextActions(projectId).then(r => setNextActions(r.actions)).catch(() => {})
  }, [projectId])

  // Re-fetch when streaming completes (isLoading transitions true→false)
  useEffect(() => {
    if (prevLoading.current && !externalLoading) {
      getNextActions(projectId).then(r => setNextActions(r.actions)).catch(() => {})
    }
    prevLoading.current = externalLoading
  }, [externalLoading, projectId])

  // Command suggestions
  const commandSuggestions = useMemo(() => {
    if (!input.startsWith('/')) return []
    return getCommandSuggestions(input)
  }, [input, getCommandSuggestions])

  useEffect(() => {
    setShowCommandSuggestions(input.startsWith('/') && commandSuggestions.length > 0)
  }, [input, commandSuggestions])

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [externalMessages, context.messages])

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
      setShowCommandSuggestions(false)

      // Check for prompt-needing commands
      const commandsNeedingPrompt = [
        { pattern: /^\/(create-task|add-task|new-task)$/i, type: 'create-task' as const },
        { pattern: /^\/(create-stakeholder|add-stakeholder)$/i, type: 'create-stakeholder' as const },
        { pattern: /^\/(remember|add-to-memory)$/i, type: 'remember' as const },
      ]

      for (const cmd of commandsNeedingPrompt) {
        if (cmd.pattern.test(trimmedInput)) {
          setActivePrompt({ type: cmd.type, step: cmd.type === 'remember' ? 'type' : undefined })
          setPromptInput('')
          setTimeout(() => promptInputRef.current?.focus(), 100)
          return
        }
      }

      if (isCommand(trimmedInput)) {
        await assistantSendMessage(trimmedInput)
      } else {
        externalSendMessage(trimmedInput)
      }
    },
    [input, externalLoading, isCommand, assistantSendMessage, externalSendMessage]
  )

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSubmit(e)
      }
      if (e.key === 'Tab' && showCommandSuggestions && commandSuggestions.length > 0) {
        e.preventDefault()
        setInput('/' + commandSuggestions[0].name + ' ')
        setShowCommandSuggestions(false)
      }
      if (e.key === 'Escape') {
        setShowCommandSuggestions(false)
      }
    },
    [handleSubmit, showCommandSuggestions, commandSuggestions]
  )

  // Quick actions
  const handleQuickAction = useCallback(
    async (action: QuickAction) => {
      if (action.command) {
        setInput(action.command)
        inputRef.current?.focus()
      } else if (action.navigateTo?.tab) {
        setAssistantTab(action.navigateTo.tab)
      } else {
        await executeQuickAction(action.id)
      }
    },
    [executeQuickAction, setAssistantTab]
  )

  const handleCommandSelect = useCallback((cmd: CommandDefinition) => {
    setInput('/' + cmd.name + ' ')
    setShowCommandSuggestions(false)
    inputRef.current?.focus()
  }, [])

  // Next action click handler
  const handleNextAction = useCallback(
    (action: NextAction) => {
      const commandFn = ACTION_COMMANDS[action.action_type]
      const message = commandFn ? commandFn(action) : action.title
      externalSendMessage(message)
    },
    [externalSendMessage]
  )

  // Inline prompt
  const handlePromptSubmit = useCallback(async () => {
    if (!activePrompt || promptSubmitting) return
    const value = promptInput.trim()
    if (!value && activePrompt.type !== 'remember') return

    setPromptSubmitting(true)
    try {
      if (activePrompt.type === 'create-task') {
        await assistantSendMessage(`/create-task "${value}"`)
      } else if (activePrompt.type === 'create-stakeholder') {
        await assistantSendMessage(`/create-stakeholder "${value}"`)
      } else if (activePrompt.type === 'remember' && activePrompt.step === 'content' && activePrompt.memoryType && value) {
        await assistantSendMessage(`/remember ${activePrompt.memoryType} "${value}"`)
      }
    } finally {
      setPromptSubmitting(false)
      setActivePrompt(null)
      setPromptInput('')
      inputRef.current?.focus()
    }
  }, [activePrompt, promptInput, promptSubmitting, assistantSendMessage])

  const handleMemoryTypeSelect = useCallback((type: 'decision' | 'learning' | 'question') => {
    setActivePrompt({ type: 'remember', step: 'content', memoryType: type })
    setPromptInput('')
    setTimeout(() => promptInputRef.current?.focus(), 100)
  }, [])

  const handlePromptCancel = useCallback(() => {
    setActivePrompt(null)
    setPromptInput('')
    inputRef.current?.focus()
  }, [])

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

      for (const file of validFiles) {
        try {
          const response = await uploadDocument(projectId, file)
          results.push({ file: file.name, success: true })
          if (!response.is_duplicate) {
            processDocument(response.id).catch(() => {})
          }
        } catch (err) {
          results.push({ file: file.name, success: false, error: err instanceof Error ? err.message : 'Failed' })
        }
      }

      setUploadingFiles(false)

      const successCount = results.filter((r) => r.success).length
      const failedFiles = results.filter((r) => !r.success)

      if (successCount > 0) {
        const names = results.filter((r) => r.success).map((r) => r.file).join(', ')
        onAddLocalMessage?.({
          role: 'assistant',
          content: `Uploaded: ${names}\n\nProcessing in background. Insights will be extracted automatically.`,
        })
      }
      if (failedFiles.length > 0) {
        const errors = failedFiles.map((f) => `${f.file}: ${f.error}`).join('\n- ')
        onAddLocalMessage?.({ role: 'assistant', content: `Upload failed:\n- ${errors}` })
      }
    },
    [projectId, onAddLocalMessage]
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

  // Merged messages
  const allMessages = useMemo(() => {
    const combined = [
      ...externalMessages.map((m) => ({
        ...m,
        id: m.id || `ext-${Math.random()}`,
        timestamp: m.timestamp || new Date(),
      })),
      ...context.messages.map((m) => ({
        id: m.id,
        role: m.role as 'user' | 'assistant' | 'system',
        content: m.content,
        timestamp: m.timestamp,
        metadata: m.metadata as Record<string, unknown> | undefined,
        toolCalls: m.toolCalls,
        isStreaming: m.isStreaming,
      })),
    ].sort((a, b) => (a.timestamp?.getTime() || 0) - (b.timestamp?.getTime() || 0))
    return combined
  }, [externalMessages, context.messages])

  // Determine if thinking (loading but no streamed content yet)
  const lastMessage = allMessages[allMessages.length - 1]
  const isThinking = externalLoading && (!lastMessage || lastMessage.role === 'user' || !lastMessage.isStreaming)

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

      {/* Proactive Messages */}
      {context.pendingProactiveMessages.length > 0 && (
        <div className="px-3 py-2 space-y-1.5 bg-white border-b border-[#E5E5E5] flex-shrink-0">
          {context.pendingProactiveMessages.map((msg, index) => (
            <ProactiveCard
              key={index}
              message={msg}
              onDismiss={() => dismissProactiveMessage(index)}
              onAction={handleQuickAction}
            />
          ))}
        </div>
      )}

      {/* Quick Actions — scrollable row */}
      <div className="px-3 py-2 border-b border-[#E5E5E5] bg-[#F4F4F4] flex-shrink-0">
        <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-hide">
          <Sparkles className="h-3 w-3 text-[#999999] flex-shrink-0" />
          {modeConfig.quickActions.slice(0, 5).map((action) => (
            <button
              key={action.id}
              onClick={() => handleQuickAction(action)}
              disabled={action.disabled}
              className={`px-2.5 py-1 text-xs font-medium rounded-xl whitespace-nowrap transition-colors flex-shrink-0 ${
                action.variant === 'primary'
                  ? 'bg-[#E8F5E9] text-[#25785A] hover:bg-[#3FAF7A] hover:text-white'
                  : 'bg-white text-[#333333] border border-[#E5E5E5] hover:bg-[#F4F4F4]'
              } disabled:opacity-50`}
            >
              {action.label}
            </button>
          ))}
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
        {allMessages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full px-4">
            {/* Branded empty state */}
            <div className="w-14 h-14 rounded-2xl bg-[#E8F5E9] flex items-center justify-center mb-3">
              <Sparkles className="h-7 w-7 text-[#3FAF7A]" />
            </div>
            <p className="text-[14px] font-semibold text-[#333333] mb-1">AIOS Assistant</p>
            <p className="text-[12px] text-[#666666] text-center mb-4">
              Your AI partner for requirements engineering
            </p>

            {/* Starter cards */}
            <div className="w-full space-y-2 mb-4">
              {STARTER_CARDS.map((card) => {
                const Icon = card.icon
                return (
                  <button
                    key={card.label}
                    onClick={() => {
                      if (card.command) {
                        setInput(card.command)
                        inputRef.current?.focus()
                      } else {
                        fileInputRef.current?.click()
                      }
                    }}
                    className="w-full flex items-center gap-3 p-3 bg-white border border-[#E5E5E5] rounded-2xl hover:border-[#3FAF7A] hover:shadow-sm transition-all text-left group"
                  >
                    <div className="w-8 h-8 rounded-xl bg-[#F4F4F4] flex items-center justify-center flex-shrink-0 group-hover:bg-[#E8F5E9] transition-colors">
                      <Icon className="h-4 w-4 text-[#666666] group-hover:text-[#3FAF7A] transition-colors" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-[12px] font-medium text-[#333333]">{card.label}</p>
                      <p className="text-[11px] text-[#999999]">{card.hint}</p>
                    </div>
                    <ArrowRight className="h-3.5 w-3.5 text-[#E5E5E5] group-hover:text-[#3FAF7A] transition-colors flex-shrink-0" />
                  </button>
                )
              })}
            </div>

            {/* Next actions in empty state */}
            {nextActions.length > 0 && (
              <div className="w-full">
                <p className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2">Start Here</p>
                {nextActions.slice(0, 2).map((action, idx) => {
                  const Icon = ACTION_ICONS[action.action_type] || Target
                  return (
                    <button
                      key={idx}
                      onClick={() => handleNextAction(action)}
                      className="w-full flex items-center gap-3 p-3 bg-white border border-[#E5E5E5] rounded-2xl hover:border-[#3FAF7A] hover:shadow-sm transition-all text-left group mb-2"
                    >
                      <span className="flex items-center justify-center w-6 h-6 rounded-full bg-[#E8F5E9] text-[11px] font-semibold text-[#25785A] flex-shrink-0">
                        {idx + 1}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-[12px] font-medium text-[#333333]">{action.title}</p>
                        <p className="text-[11px] text-[#999999] truncate">{action.description}</p>
                      </div>
                      <ArrowRight className="h-3.5 w-3.5 text-[#E5E5E5] group-hover:text-[#3FAF7A] transition-colors flex-shrink-0" />
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        ) : (
          <>
            {allMessages.map((message, index) => (
              <SidebarMessageBubble
                key={message.id || `msg-${index}`}
                message={message}
                onSendMessage={externalSendMessage}
              />
            ))}

            {/* Thinking indicator */}
            {isThinking && <ThinkingIndicator />}

            {/* Next actions after last message */}
            {!externalLoading && nextActions.length > 0 && (
              <NextActionsSuggestion
                actions={nextActions.slice(0, 2)}
                onAction={handleNextAction}
              />
            )}

            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t border-[#E5E5E5] bg-white px-3 py-2.5 flex-shrink-0">
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.xlsx,.pptx,.png,.jpg,.jpeg,.webp,.gif"
          className="hidden"
          onChange={handleFileInputChange}
        />

        {/* Inline Prompt */}
        {activePrompt && (
          <div className="mb-2 p-2.5 bg-[#F4F4F4] rounded-2xl border border-[#E5E5E5]">
            {activePrompt.type === 'create-task' && (
              <InlinePrompt
                icon="task"
                label="Create Task"
                placeholder="e.g., Review persona updates"
                value={promptInput}
                onChange={setPromptInput}
                onSubmit={handlePromptSubmit}
                onCancel={handlePromptCancel}
                submitLabel="Create"
                submitting={promptSubmitting}
                inputRef={promptInputRef}
              />
            )}
            {activePrompt.type === 'create-stakeholder' && (
              <InlinePrompt
                icon="person"
                label="Add Stakeholder"
                placeholder="e.g., John Smith"
                value={promptInput}
                onChange={setPromptInput}
                onSubmit={handlePromptSubmit}
                onCancel={handlePromptCancel}
                submitLabel="Add"
                submitting={promptSubmitting}
                inputRef={promptInputRef}
              />
            )}
            {activePrompt.type === 'remember' && activePrompt.step === 'type' && (
              <div>
                <p className="text-xs font-medium text-[#333333] mb-2">Add to Memory</p>
                <div className="flex items-center gap-1.5">
                  <button onClick={() => handleMemoryTypeSelect('decision')} className="px-2 py-1 bg-[#E8F5E9] text-[#25785A] text-xs font-medium rounded-xl hover:bg-[#3FAF7A] hover:text-white transition-colors">Decision</button>
                  <button onClick={() => handleMemoryTypeSelect('learning')} className="px-2 py-1 bg-[#E8F5E9] text-[#25785A] text-xs font-medium rounded-xl hover:bg-[#3FAF7A] hover:text-white transition-colors">Learning</button>
                  <button onClick={() => handleMemoryTypeSelect('question')} className="px-2 py-1 bg-[#E8F5E9] text-[#25785A] text-xs font-medium rounded-xl hover:bg-[#3FAF7A] hover:text-white transition-colors">Question</button>
                  <button onClick={handlePromptCancel} className="ml-auto text-xs text-[#999999] hover:text-[#333333]">Cancel</button>
                </div>
              </div>
            )}
            {activePrompt.type === 'remember' && activePrompt.step === 'content' && (
              <InlinePrompt
                icon="memory"
                label={`Add ${activePrompt.memoryType}`}
                placeholder={
                  activePrompt.memoryType === 'decision' ? 'e.g., Chose mobile-first approach'
                    : activePrompt.memoryType === 'learning' ? 'e.g., Client prefers visual mockups'
                      : 'e.g., What is the budget timeline?'
                }
                value={promptInput}
                onChange={setPromptInput}
                onSubmit={handlePromptSubmit}
                onCancel={handlePromptCancel}
                submitLabel="Save"
                submitting={promptSubmitting}
                inputRef={promptInputRef}
              />
            )}
          </div>
        )}

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
            {showCommandSuggestions && (
              <SidebarCommandAutocomplete
                suggestions={commandSuggestions}
                onSelect={handleCommandSelect}
              />
            )}
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything or type / for commands..."
              disabled={externalLoading}
              rows={1}
              className="w-full px-3 py-2 bg-[#F4F4F4] focus:bg-white border border-[#E5E5E5] rounded-2xl resize-none focus:outline-none focus:ring-2 focus:ring-[#3FAF7A]/20 focus:border-[#3FAF7A] disabled:bg-[#F4F4F4] disabled:text-[#999999] text-[13px]"
              style={{ minHeight: '36px', maxHeight: '80px' }}
            />
            {input.startsWith('/') && (
              <div className="absolute right-2 top-1/2 -translate-y-1/2">
                <Zap className="h-3.5 w-3.5 text-[#3FAF7A]" />
              </div>
            )}
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
          Enter to send &middot; / for commands &middot; Tab to complete
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

function NextActionsSuggestion({
  actions,
  onAction,
}: {
  actions: NextAction[]
  onAction: (action: NextAction) => void
}) {
  return (
    <div className="border border-[#E5E5E5] rounded-2xl bg-white shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-3 py-2 bg-[#F4F4F4] border-b border-[#E5E5E5]">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded-lg bg-[#E8F5E9] flex items-center justify-center">
            <Lightbulb className="w-3 h-3 text-[#3FAF7A]" />
          </div>
          <span className="text-[12px] font-semibold text-[#333333]">Suggested Next</span>
        </div>
      </div>

      {/* Action items */}
      <div className="divide-y divide-[#E5E5E5]">
        {actions.map((action, idx) => (
          <button
            key={idx}
            onClick={() => onAction(action)}
            className="w-full px-3 py-2.5 flex items-start gap-2.5 hover:bg-[#F4F4F4]/50 transition-colors text-left group"
          >
            <span className="flex items-center justify-center w-5 h-5 rounded-full bg-[#E8F5E9] text-[10px] font-semibold text-[#25785A] flex-shrink-0 mt-0.5">
              {idx + 1}
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-[12px] font-medium text-[#333333]">{action.title}</p>
              <p className="text-[11px] text-[#999999] truncate">{action.description}</p>
            </div>
            <ArrowRight className="h-3.5 w-3.5 text-[#E5E5E5] group-hover:text-[#3FAF7A] transition-colors flex-shrink-0 mt-0.5" />
          </button>
        ))}
      </div>
    </div>
  )
}

function InlinePrompt({
  icon,
  label,
  placeholder,
  value,
  onChange,
  onSubmit,
  onCancel,
  submitLabel,
  submitting,
  inputRef,
}: {
  icon: 'task' | 'person' | 'memory'
  label: string
  placeholder: string
  value: string
  onChange: (val: string) => void
  onSubmit: () => void
  onCancel: () => void
  submitLabel: string
  submitting: boolean
  inputRef: React.RefObject<HTMLInputElement>
}) {
  return (
    <div>
      <p className="text-xs font-medium text-[#333333] mb-1.5">{label}</p>
      <div className="flex items-center gap-1.5">
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') { e.preventDefault(); onSubmit() }
            if (e.key === 'Escape') onCancel()
          }}
          placeholder={placeholder}
          className="flex-1 px-2.5 py-1.5 border border-[#E5E5E5] rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-[#3FAF7A]/20 focus:border-[#3FAF7A]"
          disabled={submitting}
        />
        <button
          onClick={onSubmit}
          disabled={!value.trim() || submitting}
          className="px-2.5 py-1.5 bg-[#3FAF7A] text-white text-xs font-medium rounded-xl disabled:opacity-50 hover:bg-[#25785A] transition-colors"
        >
          {submitting ? <Loader2 className="h-3 w-3 animate-spin" /> : submitLabel}
        </button>
        <button onClick={onCancel} disabled={submitting} className="text-xs text-[#999999] hover:text-[#333333]">
          Cancel
        </button>
      </div>
    </div>
  )
}

function ProactiveCard({
  message,
  onDismiss,
  onAction,
}: {
  message: ProactiveMessage
  onDismiss: () => void
  onAction: (action: QuickAction) => void
}) {
  return (
    <div className="flex items-start gap-2 p-2.5 rounded-2xl border border-[#E5E5E5] bg-white shadow-sm">
      <div className="w-6 h-6 rounded-lg bg-[#E8F5E9] flex items-center justify-center flex-shrink-0">
        <Lightbulb className="h-3.5 w-3.5 text-[#3FAF7A]" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-[#333333]">{message.message}</p>
        {message.actions && message.actions.length > 0 && (
          <div className="flex items-center gap-1.5 mt-1.5">
            {message.actions.map((action) => (
              <button
                key={action.id}
                onClick={() => onAction(action)}
                className="px-2 py-0.5 text-[11px] font-medium rounded-lg bg-[#E8F5E9] text-[#25785A] hover:bg-[#3FAF7A] hover:text-white transition-colors"
              >
                {action.label}
              </button>
            ))}
          </div>
        )}
      </div>
      {message.dismissable !== false && (
        <button onClick={onDismiss} className="p-0.5 hover:bg-[#F4F4F4] rounded flex-shrink-0">
          <X className="h-3 w-3 text-[#999999]" />
        </button>
      )}
    </div>
  )
}

function SidebarCommandAutocomplete({
  suggestions,
  onSelect,
}: {
  suggestions: CommandDefinition[]
  onSelect: (cmd: CommandDefinition) => void
}) {
  return (
    <div className="absolute bottom-full left-0 right-0 mb-1 bg-white border border-[#E5E5E5] rounded-2xl shadow-md overflow-hidden z-50">
      <div className="px-3 py-1.5 text-[10px] text-[#999999] bg-[#F4F4F4] border-b border-[#E5E5E5] font-medium uppercase tracking-wide">
        Commands
      </div>
      <div className="max-h-48 overflow-y-auto">
        {suggestions.map((cmd) => (
          <button
            key={cmd.name}
            onClick={() => onSelect(cmd)}
            className="w-full flex items-center gap-2 px-3 py-1.5 hover:bg-[#F4F4F4] text-left transition-colors"
          >
            <span className="font-mono text-[12px] text-[#3FAF7A]">/{cmd.name}</span>
            <span className="text-[12px] text-[#666666] truncate">{cmd.description}</span>
          </button>
        ))}
      </div>
      <div className="px-3 py-1.5 text-[10px] text-[#999999] bg-[#F4F4F4] border-t border-[#E5E5E5]">
        Tab to complete &middot; Esc to close
      </div>
    </div>
  )
}

/** Compact message bubble for sidebar */
function SidebarMessageBubble({
  message,
  onSendMessage,
}: {
  message: ChatMessage
  onSendMessage?: (msg: string) => void | Promise<void>
}) {
  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'
  const [showToolDetails, setShowToolDetails] = useState(false)

  const signalResult = message.toolCalls?.find(
    (t) => t.tool_name === 'add_signal' && t.status === 'complete' && t.result?.processed
  )?.result

  const hasRunningTools = message.toolCalls?.some((t) => t.status === 'running')
  const completedToolCount = message.toolCalls?.filter((t) => t.status === 'complete').length || 0

  if (isSystem) return null

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
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
              <p className="text-xs whitespace-pre-wrap break-words">{message.content}</p>
            ) : (
              <>
                <Markdown content={message.content} className="text-xs" />
                {message.isStreaming && (
                  <span className="inline-block w-1.5 h-4 ml-0.5 bg-[#3FAF7A] rounded-full animate-pulse" />
                )}
              </>
            )}
          </div>
        )}

        {/* Tool Calls — compact */}
        {!isUser && message.toolCalls && message.toolCalls.length > 0 && (
          <div className="mt-1.5">
            {hasRunningTools ? (
              /* Running state — inline card */
              <div className="flex items-center gap-2 px-3 py-2 bg-[#F4F4F4] rounded-xl border border-[#E5E5E5]">
                <Loader2 className="h-3.5 w-3.5 animate-spin text-[#3FAF7A]" />
                <span className="text-[11px] text-[#333333]">
                  {getToolDisplayName(message.toolCalls.find((t) => t.status === 'running')?.tool_name || '')}
                </span>
              </div>
            ) : (
              /* Completed state — collapsed line */
              <button
                onClick={() => setShowToolDetails(!showToolDetails)}
                className="flex items-center gap-1.5 text-[11px] text-[#999999] hover:text-[#333333] transition-colors"
              >
                <CheckCircle2 className="h-3 w-3 text-[#3FAF7A]" />
                <span>{completedToolCount} action{completedToolCount !== 1 ? 's' : ''} completed</span>
                <ChevronDown className={`h-2.5 w-2.5 transition-transform ${showToolDetails ? 'rotate-180' : ''}`} />
              </button>
            )}

            {showToolDetails && (
              <div className="mt-1.5 space-y-1 pl-3 border-l-2 border-[#E5E5E5]">
                {message.toolCalls.map((tool, idx) => (
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
    add_stakeholder: 'Adding stakeholder',
    enrich_features: 'Enriching features',
    enrich_personas: 'Enriching personas',
    generate_value_path: 'Generating VP',
    search_research: 'Searching',
    semantic_search_research: 'Semantic search',
    find_evidence_gaps: 'Finding gaps',
    propose_features: 'Creating proposal',
    apply_proposal: 'Applying changes',
    analyze_gaps: 'Analyzing gaps',
    get_project_status: 'Project status',
    add_signal: 'Processing signal',
    generate_meeting_agenda: 'Meeting agenda',
    generate_client_email: 'Drafting email',
  }
  return names[toolName] || toolName.replace(/_/g, ' ')
}

export default WorkspaceChat
