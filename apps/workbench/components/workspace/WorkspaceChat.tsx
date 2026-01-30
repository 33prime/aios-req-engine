/**
 * WorkspaceChat - Full chat adapted for sidebar context
 *
 * Ports all ChatPanel functionality into a narrow sidebar:
 * - Message list with streaming
 * - Slash command autocomplete
 * - File drag-and-drop
 * - Tool execution indicators (compact)
 * - Proactive message cards
 * - Quick action row (scrollable)
 * - Inline prompts for /create-task, /create-stakeholder, /remember
 */

'use client'

import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import {
  Send,
  Loader2,
  X,
  Sparkles,
  ChevronRight,
  AlertCircle,
  Info,
  Zap,
  CheckCircle2,
  Layers,
  Upload,
  Paperclip,
} from 'lucide-react'
import { Markdown } from '../../components/ui/Markdown'
import {
  useAssistant,
  type Message,
  type QuickAction,
  type ProactiveMessage,
  type CommandDefinition,
  getModeConfig,
} from '@/lib/assistant'
import { uploadDocument, processDocument } from '@/lib/api'

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
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const promptInputRef = useRef<HTMLInputElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

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
        <div className="absolute inset-0 z-50 bg-brand-teal/5 border-2 border-dashed border-brand-teal rounded-lg flex items-center justify-center pointer-events-none">
          <div className="text-center p-4">
            <Upload className="h-8 w-8 text-brand-teal mx-auto mb-2" />
            <p className="text-sm font-medium text-brand-teal">Drop files here</p>
            <p className="text-xs text-ui-supportText mt-0.5">PDF, DOCX, XLSX, PPTX, images (max 5)</p>
          </div>
        </div>
      )}

      {/* Upload progress overlay */}
      {uploadingFiles && (
        <div className="absolute inset-0 z-50 bg-white/90 flex items-center justify-center">
          <div className="text-center p-4">
            <Loader2 className="h-8 w-8 text-brand-teal mx-auto mb-2 animate-spin" />
            <p className="text-sm font-medium text-ui-bodyText">Uploading...</p>
          </div>
        </div>
      )}

      {/* Proactive Messages */}
      {context.pendingProactiveMessages.length > 0 && (
        <div className="px-3 py-2 space-y-1.5 bg-amber-50 border-b border-amber-200 flex-shrink-0">
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
      <div className="px-3 py-2 border-b border-ui-cardBorder bg-ui-background flex-shrink-0">
        <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-hide">
          <Sparkles className="h-3 w-3 text-ui-supportText flex-shrink-0" />
          {modeConfig.quickActions.slice(0, 5).map((action) => (
            <button
              key={action.id}
              onClick={() => handleQuickAction(action)}
              disabled={action.disabled}
              className={`px-2.5 py-1 text-xs font-medium rounded-full whitespace-nowrap transition-colors flex-shrink-0 ${
                action.variant === 'primary'
                  ? 'bg-brand-teal text-white hover:bg-brand-tealDark'
                  : action.variant === 'warning'
                    ? 'bg-amber-100 text-amber-800 hover:bg-amber-200'
                    : 'bg-white text-ui-bodyText border border-ui-cardBorder hover:bg-ui-buttonGray'
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
          <div className="flex flex-col items-center justify-center h-full px-4 text-center">
            <Sparkles className="h-8 w-8 text-ui-supportText/50 mb-2" />
            <p className="text-sm text-ui-supportText mb-3">
              Type a message or use /commands
            </p>
            <div className="flex flex-wrap justify-center gap-1.5">
              {modeConfig.suggestedCommands.slice(0, 3).map((cmd) => (
                <button
                  key={cmd}
                  onClick={() => setInput(cmd)}
                  className="px-2.5 py-1 bg-ui-background text-ui-bodyText rounded-full text-xs font-mono hover:bg-ui-buttonGrayHover transition-colors"
                >
                  {cmd}
                </button>
              ))}
            </div>
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
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t border-ui-cardBorder bg-white px-3 py-2.5 flex-shrink-0">
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
          <div className="mb-2 p-2.5 bg-ui-background rounded-lg border border-ui-cardBorder">
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
                <p className="text-xs font-medium text-ui-bodyText mb-2">Add to Memory</p>
                <div className="flex items-center gap-1.5">
                  <button onClick={() => handleMemoryTypeSelect('decision')} className="px-2 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded-lg hover:bg-blue-200">Decision</button>
                  <button onClick={() => handleMemoryTypeSelect('learning')} className="px-2 py-1 bg-green-100 text-green-800 text-xs font-medium rounded-lg hover:bg-green-200">Learning</button>
                  <button onClick={() => handleMemoryTypeSelect('question')} className="px-2 py-1 bg-amber-100 text-amber-800 text-xs font-medium rounded-lg hover:bg-amber-200">Question</button>
                  <button onClick={handlePromptCancel} className="ml-auto text-xs text-ui-supportText hover:text-ui-bodyText">Cancel</button>
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
            className="p-2 text-ui-supportText hover:text-ui-bodyText hover:bg-ui-background rounded-lg transition-colors flex-shrink-0"
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
              placeholder="Message or /command..."
              disabled={externalLoading}
              rows={1}
              className="w-full px-3 py-2 border border-ui-cardBorder rounded-lg resize-none focus:outline-none focus:ring-1 focus:ring-brand-teal focus:border-brand-teal disabled:bg-ui-background disabled:text-ui-supportText text-sm"
              style={{ minHeight: '36px', maxHeight: '80px' }}
            />
            {input.startsWith('/') && (
              <div className="absolute right-2 top-1/2 -translate-y-1/2">
                <Zap className="h-3.5 w-3.5 text-brand-teal" />
              </div>
            )}
          </div>
          <button
            type="submit"
            disabled={!input.trim() || externalLoading}
            className="p-2 bg-brand-teal hover:bg-brand-tealDark text-white rounded-lg disabled:opacity-50 transition-colors flex-shrink-0"
          >
            {externalLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </button>
        </form>
        <p className="text-[11px] text-ui-supportText mt-1.5">
          Enter to send &middot; / for commands &middot; Tab to complete
        </p>
      </div>
    </div>
  )
}

// =============================================================================
// Sub-components — compact for sidebar
// =============================================================================

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
      <p className="text-xs font-medium text-ui-bodyText mb-1.5">{label}</p>
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
          className="flex-1 px-2.5 py-1.5 border border-ui-cardBorder rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-brand-teal"
          disabled={submitting}
        />
        <button
          onClick={onSubmit}
          disabled={!value.trim() || submitting}
          className="px-2.5 py-1.5 bg-brand-teal text-white text-xs font-medium rounded-lg disabled:opacity-50 hover:bg-brand-tealDark transition-colors"
        >
          {submitting ? <Loader2 className="h-3 w-3 animate-spin" /> : submitLabel}
        </button>
        <button onClick={onCancel} disabled={submitting} className="text-xs text-ui-supportText hover:text-ui-bodyText">
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
  const styles = {
    high: 'border-red-200 bg-red-50',
    medium: 'border-amber-200 bg-amber-50',
    low: 'border-blue-200 bg-blue-50',
  }
  const icons = {
    high: <AlertCircle className="h-3.5 w-3.5 text-red-600 flex-shrink-0" />,
    medium: <Info className="h-3.5 w-3.5 text-amber-600 flex-shrink-0" />,
    low: <Info className="h-3.5 w-3.5 text-blue-600 flex-shrink-0" />,
  }

  return (
    <div className={`flex items-start gap-2 p-2 rounded-lg border ${styles[message.priority]}`}>
      {icons[message.priority]}
      <div className="flex-1 min-w-0">
        <p className="text-xs text-gray-800">{message.message}</p>
        {message.actions && message.actions.length > 0 && (
          <div className="flex items-center gap-1.5 mt-1.5">
            {message.actions.map((action) => (
              <button
                key={action.id}
                onClick={() => onAction(action)}
                className={`px-2 py-0.5 text-[11px] font-medium rounded transition-colors ${
                  action.variant === 'primary'
                    ? 'bg-brand-teal text-white hover:bg-brand-tealDark'
                    : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
                }`}
              >
                {action.label}
              </button>
            ))}
          </div>
        )}
      </div>
      {message.dismissable !== false && (
        <button onClick={onDismiss} className="p-0.5 hover:bg-black/5 rounded flex-shrink-0">
          <X className="h-3 w-3 text-gray-500" />
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
    <div className="absolute bottom-full left-0 right-0 mb-1 bg-white border border-ui-cardBorder rounded-lg shadow-lg overflow-hidden z-50">
      <div className="p-1.5 text-[11px] text-ui-supportText bg-ui-background border-b border-ui-cardBorder font-medium">
        Commands (Tab to complete)
      </div>
      <div className="max-h-48 overflow-y-auto">
        {suggestions.map((cmd) => (
          <button
            key={cmd.name}
            onClick={() => onSelect(cmd)}
            className="w-full flex items-center gap-2 px-3 py-1.5 hover:bg-ui-background text-left transition-colors"
          >
            <span className="font-mono text-xs text-brand-teal">/{cmd.name}</span>
            <span className="text-xs text-ui-supportText truncate">{cmd.description}</span>
          </button>
        ))}
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

  if (isSystem) return null

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={isUser ? 'max-w-[90%]' : 'w-full'}>
        {/* Message Content */}
        {message.content && (
          <div
            className={`px-3 py-2 rounded-lg ${
              isUser
                ? 'bg-brand-teal text-white ml-auto'
                : 'bg-ui-background text-ui-bodyText'
            }`}
          >
            {isUser ? (
              <p className="text-xs whitespace-pre-wrap break-words">{message.content}</p>
            ) : (
              <>
                <Markdown content={message.content} className="text-xs" />
                {message.isStreaming && (
                  <span className="inline-block w-1 h-3 ml-0.5 bg-current animate-pulse" />
                )}
              </>
            )}
          </div>
        )}

        {/* Tool Calls — compact single-line */}
        {!isUser && message.toolCalls && message.toolCalls.length > 0 && (
          <div className="mt-1">
            <button
              onClick={() => setShowToolDetails(!showToolDetails)}
              className="flex items-center gap-1.5 text-[11px] text-ui-supportText hover:text-ui-bodyText transition-colors"
            >
              {hasRunningTools ? (
                <Loader2 className="h-3 w-3 animate-spin text-brand-teal" />
              ) : (
                <Sparkles className="h-3 w-3" />
              )}
              <span>{hasRunningTools ? 'Running...' : `${message.toolCalls.length} tool${message.toolCalls.length > 1 ? 's' : ''}`}</span>
              <ChevronRight className={`h-2.5 w-2.5 transition-transform ${showToolDetails ? 'rotate-90' : ''}`} />
            </button>

            {showToolDetails && (
              <div className="mt-1 space-y-1 pl-3 border-l-2 border-ui-cardBorder">
                {message.toolCalls.map((tool, idx) => (
                  <div
                    key={idx}
                    className={`text-[11px] px-2 py-1 rounded ${
                      tool.status === 'running' ? 'bg-brand-teal/5 text-brand-teal' :
                      tool.status === 'error' ? 'bg-red-50 text-red-600' :
                      'bg-ui-background text-ui-supportText'
                    }`}
                  >
                    {getToolDisplayName(tool.tool_name)}
                    {tool.status === 'error' && tool.error && (
                      <span className="ml-1 text-red-500">- {tool.error}</span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Signal Result Card — compact */}
        {signalResult && signalResult.proposal_id && (
          <div className="mt-1.5 p-2 bg-amber-50 border border-amber-200 rounded-lg">
            <div className="flex items-center gap-2 mb-1.5">
              <Layers className="h-3.5 w-3.5 text-amber-600" />
              <span className="text-xs font-medium text-amber-900">
                Proposal: {signalResult.total_changes || 0} changes
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => onSendMessage?.(`Apply proposal ${signalResult.proposal_id}`)}
                className="px-2 py-1 bg-amber-600 hover:bg-amber-700 text-white text-[11px] font-medium rounded transition-colors flex items-center gap-1"
              >
                <CheckCircle2 className="h-3 w-3" />
                Apply
              </button>
              <button
                onClick={() => onSendMessage?.(`Discard proposal ${signalResult.proposal_id}`)}
                className="px-2 py-1 bg-white text-gray-700 text-[11px] font-medium rounded border border-gray-300 hover:bg-gray-50 transition-colors"
              >
                Discard
              </button>
            </div>
          </div>
        )}

        {/* Timestamp */}
        {message.timestamp && (
          <p className="text-[10px] text-ui-supportText mt-0.5">
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
