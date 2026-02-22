/**
 * ChatPanel Component
 *
 * Enhanced chat interface with AI Assistant Command Center integration.
 * Features slash commands, quick actions, proactive messages, and mode awareness.
 *
 * Features:
 * - Sliding panel animation
 * - Message history with auto-scroll
 * - Streaming message display
 * - Tool execution indicators
 * - Slash command autocomplete
 * - Quick action buttons
 * - Proactive message alerts
 * - Mode-aware context hints
 */

'use client'

import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import {
  Send,
  Loader2,
  X,
  Minimize2,
  Sparkles,
  ChevronRight,
  AlertCircle,
  Info,
  CheckCircle2,
  Layers,
  Upload,
} from 'lucide-react'
import { ProposalPreview } from './ProposalPreview'
import { Markdown } from '../../../../components/ui/Markdown'
import {
  useAssistant,
  type Message,
  type QuickAction,
  type ProactiveMessage,
  type TabType,
  getModeConfig,
} from '@/lib/assistant'
import { uploadDocument, processDocument, type DocumentUploadResponse } from '@/lib/api'

// =============================================================================
// Types
// =============================================================================

export interface ChatMessage {
  id?: string // Add id for stable React keys
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp?: Date
  isStreaming?: boolean
  metadata?: Record<string, unknown> // Include metadata from assistant messages
  toolCalls?: Array<{
    id?: string
    tool_name: string
    status: 'pending' | 'running' | 'complete' | 'error'
    args?: Record<string, unknown>
    result?: any
    error?: string
  }>
}

interface ChatPanelProps {
  /** Whether the panel is open */
  isOpen: boolean
  /** Callback to close the panel */
  onClose: () => void
  /** Project ID */
  projectId: string
  /** Conversation messages (from useChat hook) */
  messages: ChatMessage[]
  /** Whether a message is currently being generated */
  isLoading: boolean
  /** Callback to send a message to AI backend */
  onSendMessage: (message: string) => void
  /** Callback to send a signal */
  onSendSignal?: (type: string, content: string, source: string) => void
  /** Callback to add a local message (without triggering AI) */
  onAddLocalMessage?: (message: ChatMessage) => void
  /** Current active tab for context awareness */
  activeTab?: string
  /** Whether panel is minimized */
  isMinimized?: boolean
  /** Callback to toggle minimize state */
  onToggleMinimize?: () => void
}

// =============================================================================
// Main Component
// =============================================================================

export function ChatPanel({
  isOpen,
  onClose,
  projectId,
  messages: externalMessages,
  isLoading: externalLoading,
  onSendMessage: externalSendMessage,
  onSendSignal,
  onAddLocalMessage,
  activeTab = 'overview',
  isMinimized = false,
  onToggleMinimize,
}: ChatPanelProps) {
  const [input, setInput] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [uploadingFiles, setUploadingFiles] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Use the assistant hook
  const {
    context,
    setActiveTab: setAssistantTab,
    getQuickActions,
    executeQuickAction,
    dismissProactiveMessage,
  } = useAssistant()

  // Sync active tab with assistant context
  useEffect(() => {
    if (activeTab) {
      setAssistantTab(activeTab as TabType)
    }
  }, [activeTab, setAssistantTab])

  // Get mode-specific config
  const modeConfig = useMemo(() => getModeConfig(context.mode), [context.mode])

  // Context hint based on mode
  const getContextHint = useCallback(() => {
    return modeConfig.systemPrompt.split('\n')[0].replace('You are an AI assistant ', '').slice(0, 80) + '...'
  }, [modeConfig])

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [externalMessages, context.messages])

  // Focus input when panel opens
  useEffect(() => {
    if (isOpen && !isMinimized) {
      inputRef.current?.focus()
    }
  }, [isOpen, isMinimized])

  // Handle message submission
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

  // Handle quick action click
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

  // File drag and drop handlers
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }, [])

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    // Only set dragging to false if leaving the container
    if (e.currentTarget.contains(e.relatedTarget as Node)) return
    setIsDragging(false)
  }, [])

  const handleFileDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setIsDragging(false)

      const files = Array.from(e.dataTransfer.files).slice(0, 5) // Max 5 files
      if (files.length === 0) return

      // Validate file types
      const allowedTypes = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'image/png',
        'image/jpeg',
        'image/webp',
        'image/gif',
      ]

      const validFiles = files.filter((f) => allowedTypes.includes(f.type))
      if (validFiles.length === 0) {
        onAddLocalMessage?.({
          role: 'assistant',
          content: 'I can only accept PDF, DOCX, XLSX, PPTX, or images (PNG, JPG, WEBP, GIF).',
        })
        return
      }

      setUploadingFiles(true)

      // Upload files and show progress
      const results: { file: string; success: boolean; error?: string; docId?: string }[] = []

      for (const file of validFiles) {
        try {
          const response = await uploadDocument(projectId, file)
          results.push({
            file: file.name,
            success: true,
            docId: response.id,
          })

          // Trigger processing immediately
          if (!response.is_duplicate) {
            processDocument(response.id).catch((err) =>
              console.error(`Failed to trigger processing for ${file.name}:`, err)
            )
          }
        } catch (err) {
          results.push({
            file: file.name,
            success: false,
            error: err instanceof Error ? err.message : 'Upload failed',
          })
        }
      }

      setUploadingFiles(false)

      // Show results in chat
      const successCount = results.filter((r) => r.success).length
      const failedFiles = results.filter((r) => !r.success)

      if (successCount > 0) {
        const fileNames = results
          .filter((r) => r.success)
          .map((r) => r.file)
          .join(', ')

        // Show upload confirmation - processing happens automatically in background
        // Features, personas, and other entities will be extracted and merged
        onAddLocalMessage?.({
          role: 'assistant',
          content: `📄 **Document${successCount > 1 ? 's' : ''} uploaded:** ${fileNames}\n\nProcessing in background. Features, personas, and other insights will be automatically extracted and added to your project.`,
        })
      }

      if (failedFiles.length > 0) {
        const errors = failedFiles.map((f) => `${f.file}: ${f.error}`).join('\n- ')
        onAddLocalMessage?.({
          role: 'assistant',
          content: `⚠️ **Upload failed:**\n- ${errors}`,
        })
      }
    },
    [projectId, onAddLocalMessage]
  )

  // Combined messages (external + all context messages including command results)
  const allMessages = useMemo(() => {
    // Merge external messages with ALL assistant context messages (user, assistant, system)
    const combined = [
      ...externalMessages.map(m => ({
        ...m,
        id: m.id || `ext-${Math.random()}`, // Ensure id exists
        timestamp: m.timestamp || new Date(),
      })),
      ...context.messages.map(m => ({
        id: m.id, // Include id for stable React keys
        role: m.role as 'user' | 'assistant' | 'system',
        content: m.content,
        timestamp: m.timestamp,
        metadata: m.metadata as Record<string, unknown> | undefined,
        toolCalls: m.toolCalls, // Include tool calls for display
        isStreaming: m.isStreaming,
      })),
    ].sort((a, b) => (a.timestamp?.getTime() || 0) - (b.timestamp?.getTime() || 0))

    return combined
  }, [externalMessages, context.messages])

  // If minimized, show compact docked bar
  if (isMinimized && isOpen) {
    return (
      <div className="fixed bottom-4 right-4 sm:bottom-4 sm:right-4 z-50">
        <button
          onClick={onToggleMinimize}
          className="flex items-center gap-2 px-4 py-3 bg-gradient-to-r from-[#3FAF7A] to-[#25785A] text-white rounded-lg shadow-lg hover:shadow-xl transition-all"
        >
          <MessageCircleIcon className="h-5 w-5" />
          <span className="font-medium">AI Assistant</span>
          {allMessages.length > 0 && (
            <span className="ml-1 px-2 py-0.5 bg-white/20 rounded-full text-xs">
              {allMessages.length}
            </span>
          )}
          {context.pendingProactiveMessages.length > 0 && (
            <span className="ml-1 w-2 h-2 bg-yellow-400 rounded-full animate-pulse" />
          )}
        </button>
      </div>
    )
  }

  return (
    <>
      {/* Backdrop - click to close */}
      {isOpen && !isMinimized && (
        <div
          className="fixed inset-0 bg-black/10 z-40 transition-opacity"
          onClick={onClose}
        />
      )}

      {/* Floating Panel */}
      <div
        className={`fixed top-0 right-0 h-[100dvh] w-full sm:w-[560px] bg-white shadow-2xl z-50 transition-transform duration-300 ease-in-out border-l border-gray-200 flex flex-col ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
        onDragOver={handleDragOver}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDrop={handleFileDrop}
      >
        {/* Drag overlay */}
        {isDragging && (
          <div className="absolute inset-0 z-50 bg-[#3FAF7A]/5 border-2 border-dashed border-[#3FAF7A] rounded-lg flex items-center justify-center pointer-events-none">
            <div className="text-center p-6">
              <Upload className="h-12 w-12 text-[#3FAF7A] mx-auto mb-3" />
              <p className="text-lg font-medium text-[#3FAF7A]">Drop files here</p>
              <p className="text-sm text-[#999999] mt-1">PDF, DOCX, XLSX, PPTX, or images (max 5)</p>
            </div>
          </div>
        )}

        {/* Upload progress overlay */}
        {uploadingFiles && (
          <div className="absolute inset-0 z-50 bg-white/90 flex items-center justify-center">
            <div className="text-center p-6">
              <Loader2 className="h-10 w-10 text-[#3FAF7A] mx-auto mb-3 animate-spin" />
              <p className="text-base font-medium text-[#333333]">Uploading files...</p>
            </div>
          </div>
        )}

        {/* Header */}
        <div className="flex items-center justify-between px-4 sm:px-6 py-3 sm:py-4 border-b border-gray-200 bg-gradient-to-r from-[#3FAF7A] to-[#25785A] flex-shrink-0">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h2 className="text-base sm:text-lg font-semibold text-white">AI Assistant</h2>
              <span className="px-2 py-0.5 bg-white/20 rounded text-xs text-white/90 capitalize">
                {context.mode.replace('_', ' ')} Mode
              </span>
            </div>
            <p className="text-xs text-white/80 mt-0.5 hidden sm:block truncate">{getContextHint()}</p>
          </div>
          <div className="flex items-center gap-2">
            {onToggleMinimize && (
              <button
                onClick={onToggleMinimize}
                className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                aria-label="Minimize chat"
              >
                <Minimize2 className="h-5 w-5 text-white" />
              </button>
            )}
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/10 rounded-lg transition-colors"
              aria-label="Close chat"
            >
              <X className="h-5 w-5 text-white" />
            </button>
          </div>
        </div>

        {/* Proactive Messages */}
        {context.pendingProactiveMessages.length > 0 && (
          <div className="px-4 py-2 space-y-2 bg-amber-50 border-b border-amber-200">
            {context.pendingProactiveMessages.map((msg, index) => (
              <ProactiveMessageCard
                key={index}
                message={msg}
                onDismiss={() => dismissProactiveMessage(index)}
                onAction={handleQuickAction}
              />
            ))}
          </div>
        )}

        {/* Quick Actions Bar - uses modeConfig directly for immediate updates on tab change */}
        <div className="px-3 sm:px-4 py-2 sm:py-3 border-b border-gray-100 bg-gray-50 flex-shrink-0">
          <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-hide">
            <span className="text-xs text-[#999999] whitespace-nowrap flex items-center gap-1">
              <Sparkles className="h-3 w-3" />
              Quick:
            </span>
            {modeConfig.quickActions.slice(0, 5).map((action) => (
              <button
                key={action.id}
                onClick={() => handleQuickAction(action)}
                disabled={action.disabled}
                className={`px-3 py-1.5 text-xs font-medium rounded-full whitespace-nowrap transition-colors ${
                  action.variant === 'primary'
                    ? 'bg-[#3FAF7A] text-white hover:bg-[#25785A]'
                    : action.variant === 'warning'
                      ? 'bg-amber-100 text-amber-800 hover:bg-amber-200'
                      : action.variant === 'danger'
                        ? 'bg-red-100 text-red-800 hover:bg-red-200'
                        : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-100'
                } disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                {action.label}
              </button>
            ))}
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-4 space-y-4">
          {allMessages.length === 0 ? (
            <WelcomeScreen suggestedCommands={modeConfig.suggestedCommands} onCommand={setInput} activeTab={activeTab} />
          ) : (
            <>
              {allMessages.map((message, index) => (
                <MessageBubble
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
        <div className="border-t border-gray-200 bg-white px-4 sm:px-6 py-3 sm:py-4 flex-shrink-0 pb-safe">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your project..."
              disabled={externalLoading}
              rows={1}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-[#3FAF7A] focus:border-transparent disabled:bg-gray-50 disabled:text-gray-500 text-sm"
              style={{ minHeight: '40px', maxHeight: '120px' }}
            />
            <button
              type="submit"
              disabled={!input.trim() || externalLoading}
              className="px-4 py-2 bg-[#3FAF7A] hover:bg-[#25785A] text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              aria-label="Send message"
            >
              {externalLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </button>
          </form>
          <p className="text-xs text-[#999999] mt-2">
            Press Enter to send • Shift+Enter for new line
          </p>
        </div>
      </div>
    </>
  )
}

// =============================================================================
// Sub-components
// =============================================================================

/** Welcome screen shown when no messages */
function WelcomeScreen({
  onCommand,
}: {
  suggestedCommands?: string[]
  onCommand: (cmd: string) => void
  activeTab?: string
}) {
  const starters = [
    'What should I focus on next?',
    'Summarize the current project status',
    'What gaps exist in our requirements?',
  ]

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6">
      <div className="w-12 h-12 bg-gray-100 rounded-xl flex items-center justify-center mb-3">
        <Sparkles className="h-6 w-6 text-gray-500" />
      </div>
      <h3 className="text-sm font-semibold text-gray-900 mb-1">
        AI Assistant
      </h3>
      <p className="text-sm text-gray-500 text-center max-w-[280px] mb-5">
        Ask questions, run analyses, or get help with your project requirements.
      </p>
      <div className="flex flex-wrap justify-center gap-2">
        {starters.map((prompt) => (
          <button
            key={prompt}
            onClick={() => onCommand(prompt)}
            className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-full text-xs transition-colors"
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  )
}

/** Proactive message card */
function ProactiveMessageCard({
  message,
  onDismiss,
  onAction,
}: {
  message: ProactiveMessage
  onDismiss: () => void
  onAction: (action: QuickAction) => void
}) {
  const priorityStyles = {
    high: 'border-red-300 bg-red-50',
    medium: 'border-amber-300 bg-amber-50',
    low: 'border-blue-300 bg-blue-50',
  }

  const priorityIcon = {
    high: <AlertCircle className="h-4 w-4 text-red-600" />,
    medium: <Info className="h-4 w-4 text-amber-600" />,
    low: <Info className="h-4 w-4 text-blue-600" />,
  }

  return (
    <div className={`flex items-start gap-3 p-3 rounded-lg border ${priorityStyles[message.priority]}`}>
      {priorityIcon[message.priority]}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-800">{message.message}</p>
        {message.actions && message.actions.length > 0 && (
          <div className="flex items-center gap-2 mt-2">
            {message.actions.map((action) => (
              <button
                key={action.id}
                onClick={() => onAction(action)}
                className={`px-2 py-1 text-xs font-medium rounded transition-colors ${
                  action.variant === 'primary'
                    ? 'bg-[#3FAF7A] text-white hover:bg-[#25785A]'
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
        <button
          onClick={onDismiss}
          className="p-1 hover:bg-black/5 rounded"
          aria-label="Dismiss"
        >
          <X className="h-4 w-4 text-gray-500" />
        </button>
      )}
    </div>
  )
}

/** Individual message bubble component */
function MessageBubble({
  message,
  onSendMessage,
}: {
  message: ChatMessage
  onSendMessage?: (msg: string) => void
}) {
  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'
  const [applyingProposal, setApplyingProposal] = useState<string | null>(null)
  const [showToolDetails, setShowToolDetails] = useState(true)

  // Check if any tool result contains a FULL proposal (from propose_features with changes_by_type)
  const proposalData = message.toolCalls?.find(
    (tool) =>
      tool.tool_name === 'propose_features' &&
      tool.status === 'complete' &&
      tool.result?.proposal_id &&
      tool.result?.changes_by_type // Only show full preview if we have detailed changes
  )?.result

  // Check for signal processing result (for inline approval card)
  // This handles add_signal which returns proposal_id but not full changes
  const signalResult = message.toolCalls?.find(
    (tool) =>
      tool.tool_name === 'add_signal' &&
      tool.status === 'complete' &&
      tool.result?.processed
  )?.result

  const handleApplyProposal = async (proposalId: string) => {
    if (!onSendMessage) return
    setApplyingProposal(proposalId)
    onSendMessage(`Apply proposal ${proposalId}`)
  }

  const handleDiscardProposal = async (proposalId: string) => {
    if (!onSendMessage) return
    onSendMessage(`Discard proposal ${proposalId}`)
  }

  // Check if any tools are still running
  const hasRunningTools = message.toolCalls?.some(t => t.status === 'running')
  const allToolsComplete = (message.toolCalls?.length ?? 0) > 0 && message.toolCalls?.every(t => t.status !== 'running')

  // Hide system messages entirely (mode transitions, etc.)
  if (isSystem) {
    return null
  }

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[85%] ${isUser ? 'order-2' : 'order-1'}`}>
        {/* Message Content - ALWAYS FIRST for assistant */}
        {message.content && (
          <div
            className={`px-4 py-2 rounded-lg ${
              isUser
                ? 'bg-[#3FAF7A] text-white'
                : 'bg-gray-100 text-[#333333]'
            }`}
          >
            {isUser ? (
              <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
            ) : (
              <>
                <Markdown content={message.content} className="text-sm" />
                {message.isStreaming && (
                  <span className="inline-block w-1 h-4 ml-1 bg-current animate-pulse" />
                )}
              </>
            )}
          </div>
        )}

        {/* Tool Calls - BELOW message content */}
        {!isUser && message.toolCalls && message.toolCalls.length > 0 && (
          <div className="mt-2">
            {/* Tool section header */}
            <button
              onClick={() => setShowToolDetails(!showToolDetails)}
              className="flex items-center gap-2 text-xs text-[#999999] hover:text-[#333333] transition-colors mb-1"
            >
              <Sparkles className="h-3 w-3" />
              <span className="font-medium">
                {hasRunningTools ? 'Running tools...' : `${message.toolCalls.length} tool${message.toolCalls.length > 1 ? 's' : ''} executed`}
              </span>
              <ChevronRight className={`h-3 w-3 transition-transform ${showToolDetails ? 'rotate-90' : ''}`} />
            </button>

            {/* Tool details (collapsible) */}
            {showToolDetails && (
              <div className="space-y-1.5 pl-5 border-l-2 border-gray-200">
                {message.toolCalls.map((tool, idx) => (
                  <div
                    key={idx}
                    className={`flex items-start gap-2 text-xs px-3 py-2 rounded-lg transition-all ${
                      tool.status === 'pending' || tool.status === 'running'
                        ? 'bg-[#3FAF7A]/5 border border-[#3FAF7A]/20'
                        : tool.status === 'error'
                          ? 'bg-red-50 border border-red-100'
                          : 'bg-gray-50'
                    }`}
                  >
                    {/* Status icon */}
                    <div className="flex-shrink-0 mt-0.5">
                      {(tool.status === 'pending' || tool.status === 'running') && (
                        <Loader2 className="h-3.5 w-3.5 animate-spin text-[#3FAF7A]" />
                      )}
                      {tool.status === 'complete' && (
                        <CheckIcon className="h-3.5 w-3.5 text-green-600" />
                      )}
                      {tool.status === 'error' && (
                        <XCircleIcon className="h-3.5 w-3.5 text-red-600" />
                      )}
                    </div>

                    {/* Tool info */}
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-[#333333]">
                        {getToolDisplayName(tool.tool_name)}
                      </div>
                      {/* Show brief result summary if complete */}
                      {tool.status === 'complete' && tool.result?.message && (
                        <div className="text-[#999999] mt-0.5 line-clamp-2">
                          {typeof tool.result.message === 'string'
                            ? tool.result.message.split('\n')[0].slice(0, 80)
                            : ''}
                        </div>
                      )}
                      {tool.status === 'error' && tool.result?.error && (
                        <div className="text-red-600 mt-0.5">
                          Error: {tool.result.error}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Signal Processing Result with Inline Approval */}
        {signalResult && signalResult.proposal_id && (
          <div className="mt-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 bg-amber-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <Layers className="h-4 w-4 text-amber-600" />
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="font-medium text-amber-900 text-sm">
                  Proposal Created: {signalResult.total_changes || 0} changes
                </h4>
                <p className="text-xs text-amber-700 mt-0.5">
                  {signalResult.pipeline === 'bulk' ? 'Heavyweight signal detected - ' : ''}
                  Review and apply changes to update your project.
                </p>
                <div className="flex items-center gap-2 mt-2">
                  <button
                    onClick={() => handleApplyProposal(signalResult.proposal_id)}
                    disabled={applyingProposal === signalResult.proposal_id}
                    className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white text-xs font-medium rounded-lg transition-colors disabled:opacity-50 flex items-center gap-1"
                  >
                    {applyingProposal === signalResult.proposal_id ? (
                      <>
                        <Loader2 className="h-3 w-3 animate-spin" />
                        Applying...
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="h-3 w-3" />
                        Apply Changes
                      </>
                    )}
                  </button>
                  <button
                    onClick={() => handleDiscardProposal(signalResult.proposal_id)}
                    disabled={applyingProposal === signalResult.proposal_id}
                    className="px-3 py-1.5 bg-white hover:bg-gray-50 text-gray-700 text-xs font-medium rounded-lg border border-gray-300 transition-colors disabled:opacity-50"
                  >
                    Discard
                  </button>
                  <button
                    onClick={() => onSendMessage?.(`Preview proposal ${signalResult.proposal_id}`)}
                    className="px-3 py-1.5 text-amber-700 hover:text-amber-800 text-xs font-medium underline"
                  >
                    View Details
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Proposal Preview (for propose_features tool) */}
        {proposalData && (
          <div className="mt-2">
            <ProposalPreview
              proposal={{
                proposal_id: proposalData.proposal_id,
                title: proposalData.title,
                description: proposalData.description,
                status: 'pending',
                creates: proposalData.creates_count || 0,
                updates: proposalData.updates_count || 0,
                deletes: proposalData.deletes_count || 0,
                total_changes: proposalData.total_changes || 0,
                changes_by_type: proposalData.changes_by_type,
              }}
              onApply={handleApplyProposal}
              onDiscard={handleDiscardProposal}
              isApplying={applyingProposal === proposalData.proposal_id}
            />
          </div>
        )}

        {/* Timestamp */}
        {message.timestamp && (
          <p className="text-xs text-[#999999] mt-1">
            {message.timestamp.toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </p>
        )}
      </div>
    </div>
  )
}

/** Get display name for tool */
function getToolDisplayName(toolName: string): string {
  const toolNames: Record<string, string> = {
    // Strategic Foundation
    generate_strategic_context: 'Generating strategic context',
    get_strategic_context: 'Fetching strategic context',
    update_strategic_context: 'Updating strategic context',
    identify_stakeholders: 'Identifying stakeholders',
    // Enrichment
    enrich_features: 'Enriching features',
    enrich_personas: 'Enriching personas',
    // Research
    search: 'Searching knowledge base',
    attach_evidence: 'Attaching evidence',
    query_entity_history: 'Querying entity history',
    query_knowledge_graph: 'Querying knowledge graph',
    // Analysis
    analyze_impact: 'Analyzing impact',
    get_stale_entities: 'Finding stale entities',
    refresh_stale_entity: 'Refreshing entity',
    // Status
    get_project_status: 'Getting project status',
    list_pending_confirmations: 'Listing confirmations',
    create_confirmation: 'Creating confirmation',
    // Entities
    create_entity: 'Creating entity',
    update_entity: 'Updating entity',
    // Signals
    add_signal: 'Processing signal',
    // Documents
    check_document_clarifications: 'Checking clarifications',
    respond_to_document_clarification: 'Responding to clarification',
    // Output
    generate_meeting_agenda: 'Generating meeting agenda',
    generate_client_email: 'Drafting email',
  }
  return toolNames[toolName] || toolName.replace(/_/g, ' ')
}

// =============================================================================
// Icon Components
// =============================================================================

function MessageCircleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
      />
    </svg>
  )
}

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  )
}

function XCircleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  )
}
