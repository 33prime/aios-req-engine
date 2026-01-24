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
  Mail,
  FileText,
  Mic,
  ClipboardPaste,
  Sparkles,
  ChevronRight,
  AlertCircle,
  Info,
  Zap,
} from 'lucide-react'
import { ProposalPreview } from './ProposalPreview'
import { Markdown } from '../../../../components/ui/Markdown'
import {
  useAssistant,
  type Message,
  type QuickAction,
  type ProactiveMessage,
  type CommandDefinition,
  getModeConfig,
} from '@/lib/assistant'

// =============================================================================
// Types
// =============================================================================

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp?: Date
  isStreaming?: boolean
  toolCalls?: Array<{
    tool_name: string
    status: 'running' | 'complete' | 'error'
    result?: any
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
  activeTab = 'overview',
  isMinimized = false,
  onToggleMinimize,
}: ChatPanelProps) {
  const [input, setInput] = useState('')
  const [showSignalInput, setShowSignalInput] = useState(false)
  const [signalType, setSignalType] = useState<string>('')
  const [signalContent, setSignalContent] = useState('')
  const [signalSource, setSignalSource] = useState('')
  const [sendingSignal, setSendingSignal] = useState(false)
  const [showCommandSuggestions, setShowCommandSuggestions] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Use the assistant hook
  const {
    context,
    setActiveTab: setAssistantTab,
    sendMessage: assistantSendMessage,
    isCommand,
    getCommandSuggestions,
    getQuickActions,
    executeQuickAction,
    dismissProactiveMessage,
  } = useAssistant()

  // Sync active tab with assistant context
  useEffect(() => {
    if (activeTab) {
      setAssistantTab(activeTab as any)
    }
  }, [activeTab, setAssistantTab])

  // Get mode-specific config
  const modeConfig = useMemo(() => getModeConfig(context.mode), [context.mode])

  // Get command suggestions for autocomplete
  const commandSuggestions = useMemo(() => {
    if (!input.startsWith('/')) return []
    const suggestions = getCommandSuggestions(input)
    console.log('Command suggestions for "' + input + '":', suggestions)
    return suggestions
  }, [input, getCommandSuggestions])

  // Show/hide command suggestions
  useEffect(() => {
    const shouldShow = input.startsWith('/') && commandSuggestions.length > 0
    console.log('Show command suggestions:', shouldShow, 'input:', input, 'count:', commandSuggestions.length)
    setShowCommandSuggestions(shouldShow)
  }, [input, commandSuggestions])

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
      setShowCommandSuggestions(false)

      // Check if it's a slash command
      if (isCommand(trimmedInput)) {
        // Handle through assistant (local command execution)
        await assistantSendMessage(trimmedInput)
      } else {
        // Send to external AI backend
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
      // Tab to autocomplete command
      if (e.key === 'Tab' && showCommandSuggestions && commandSuggestions.length > 0) {
        e.preventDefault()
        setInput('/' + commandSuggestions[0].name + ' ')
        setShowCommandSuggestions(false)
      }
      // Escape to close suggestions
      if (e.key === 'Escape') {
        setShowCommandSuggestions(false)
      }
    },
    [handleSubmit, showCommandSuggestions, commandSuggestions]
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

  // Handle command suggestion click
  const handleCommandSelect = useCallback((cmd: CommandDefinition) => {
    setInput('/' + cmd.name + ' ')
    setShowCommandSuggestions(false)
    inputRef.current?.focus()
  }, [])

  // Combined messages (external + all context messages including command results)
  const allMessages = useMemo(() => {
    // Merge external messages with ALL assistant context messages (user, assistant, system)
    return [
      ...externalMessages.map(m => ({
        ...m,
        timestamp: m.timestamp || new Date(),
      })),
      ...context.messages.map(m => ({
        role: m.role as 'user' | 'assistant' | 'system',
        content: m.content,
        timestamp: m.timestamp,
      })),
    ].sort((a, b) => (a.timestamp?.getTime() || 0) - (b.timestamp?.getTime() || 0))
  }, [externalMessages, context.messages])

  // If minimized, show compact docked bar
  if (isMinimized && isOpen) {
    return (
      <div className="fixed bottom-4 right-4 sm:bottom-4 sm:right-4 z-50">
        <button
          onClick={onToggleMinimize}
          className="flex items-center gap-2 px-4 py-3 bg-gradient-to-r from-brand-primary to-brand-primaryHover text-white rounded-lg shadow-lg hover:shadow-xl transition-all"
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
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 sm:px-6 py-3 sm:py-4 border-b border-gray-200 bg-gradient-to-r from-brand-primary to-brand-primaryHover flex-shrink-0">
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
            <span className="text-xs text-ui-supportText whitespace-nowrap flex items-center gap-1">
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
                    ? 'bg-brand-primary text-white hover:bg-brand-primaryHover'
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
                  key={index}
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
          {/* Signal Icon Bar */}
          {onSendSignal && !showSignalInput && (
            <div className="flex items-center gap-2 mb-3 overflow-x-auto">
              <span className="text-xs text-ui-supportText mr-1 flex-shrink-0">Add:</span>
              <SignalButton icon={Mail} label="email" onClick={() => { setSignalType('email'); setShowSignalInput(true); }} />
              <SignalButton icon={FileText} label="note" onClick={() => { setSignalType('note'); setShowSignalInput(true); }} />
              <SignalButton icon={Mic} label="transcript" onClick={() => { setSignalType('transcript'); setShowSignalInput(true); }} />
              <SignalButton icon={ClipboardPaste} label="document" onClick={() => { setSignalType('document'); setShowSignalInput(true); }} />
            </div>
          )}

          {/* Inline Signal Input */}
          {showSignalInput && (
            <SignalInputForm
              signalType={signalType}
              signalContent={signalContent}
              signalSource={signalSource}
              sendingSignal={sendingSignal}
              onContentChange={setSignalContent}
              onSourceChange={setSignalSource}
              onSubmit={async () => {
                if (signalContent.trim() && onSendSignal) {
                  setSendingSignal(true)
                  try {
                    await onSendSignal(signalType, signalContent.trim(), signalSource || 'chat')
                    setShowSignalInput(false)
                    setSignalType('')
                    setSignalContent('')
                    setSignalSource('')
                  } finally {
                    setSendingSignal(false)
                  }
                }
              }}
              onCancel={() => {
                setShowSignalInput(false)
                setSignalType('')
                setSignalContent('')
                setSignalSource('')
              }}
            />
          )}

          <form onSubmit={handleSubmit} className="flex gap-2">
            <div className="relative flex-1">
              {/* Command Autocomplete - positioned relative to input */}
              {showCommandSuggestions && (
                <CommandAutocomplete
                  suggestions={commandSuggestions}
                  onSelect={handleCommandSelect}
                />
              )}
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type a message or /command..."
                disabled={externalLoading}
                rows={1}
                className="w-full px-4 py-2 pr-10 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-transparent disabled:bg-gray-50 disabled:text-gray-500 text-sm"
                style={{ minHeight: '40px', maxHeight: '120px' }}
              />
              {input.startsWith('/') && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  <Zap className="h-4 w-4 text-brand-primary" />
                </div>
              )}
            </div>
            <button
              type="submit"
              disabled={!input.trim() || externalLoading}
              className="px-4 py-2 bg-brand-primary hover:bg-brand-primaryHover text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              aria-label="Send message"
            >
              {externalLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </button>
          </form>
          <p className="text-xs text-ui-supportText mt-2">
            Press Enter to send • Type / for commands • Tab to autocomplete
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
  suggestedCommands,
  onCommand,
  activeTab,
}: {
  suggestedCommands: string[]
  onCommand: (cmd: string) => void
  activeTab?: string
}) {
  const contextMessages: Record<string, string> = {
    'strategic-context': 'Extract company info, business drivers, and competitors from your signals.',
    'features': 'Analyze features, enrich with AI, or approve pending items.',
    'value-path': 'Design and refine the user journey steps.',
    'sources': 'Process signals and route claims to entities.',
    'overview': 'Check project health and plan next steps.',
    'personas': 'Develop and refine user personas with evidence.',
    'research': 'Search research findings and identify gaps.',
  }

  const defaultMessage = 'Use commands to run AI agents or ask questions about your project.'

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6">
      <div className="w-12 h-12 bg-gray-100 rounded-xl flex items-center justify-center mb-3">
        <Sparkles className="h-6 w-6 text-gray-500" />
      </div>
      <h3 className="text-sm font-semibold text-gray-900 mb-1">
        AI Assistant
      </h3>
      <p className="text-sm text-gray-500 text-center max-w-[280px] mb-5">
        {contextMessages[activeTab || ''] || defaultMessage}
      </p>
      <div className="flex flex-wrap justify-center gap-2">
        {suggestedCommands.map((cmd) => (
          <button
            key={cmd}
            onClick={() => onCommand(cmd)}
            className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-full text-xs font-mono transition-colors"
          >
            {cmd}
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
                    ? 'bg-brand-primary text-white hover:bg-brand-primaryHover'
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

/** Command autocomplete dropdown */
function CommandAutocomplete({
  suggestions,
  onSelect,
}: {
  suggestions: CommandDefinition[]
  onSelect: (cmd: CommandDefinition) => void
}) {
  return (
    <div className="absolute bottom-full left-0 right-0 mb-2 bg-white border border-gray-200 rounded-lg shadow-lg overflow-hidden z-50">
      <div className="p-2 text-xs text-ui-supportText bg-gray-50 border-b border-gray-200 font-medium">
        💡 Available Commands (Tab to complete)
      </div>
      <div className="max-h-64 overflow-y-auto">
        {suggestions.map((cmd) => (
          <button
            key={cmd.name}
            onClick={() => onSelect(cmd)}
            className="w-full flex items-center gap-3 px-4 py-2 hover:bg-gray-50 text-left transition-colors"
          >
            <span className="font-mono text-sm text-brand-primary">/{cmd.name}</span>
            <span className="text-sm text-ui-supportText truncate">{cmd.description}</span>
            <ChevronRight className="h-4 w-4 text-gray-400 ml-auto flex-shrink-0" />
          </button>
        ))}
      </div>
    </div>
  )
}

/** Signal type button */
function SignalButton({
  icon: Icon,
  label,
  onClick,
}: {
  icon: React.ElementType
  label: string
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors group"
      title={`Add ${label}`}
    >
      <Icon className="h-4 w-4 text-ui-supportText group-hover:text-brand-primary" />
    </button>
  )
}

/** Signal input form */
function SignalInputForm({
  signalType,
  signalContent,
  signalSource,
  sendingSignal,
  onContentChange,
  onSourceChange,
  onSubmit,
  onCancel,
}: {
  signalType: string
  signalContent: string
  signalSource: string
  sendingSignal: boolean
  onContentChange: (v: string) => void
  onSourceChange: (v: string) => void
  onSubmit: () => void
  onCancel: () => void
}) {
  const icons: Record<string, string> = {
    email: '📧',
    note: '📝',
    transcript: '🎤',
    document: '📄',
  }

  return (
    <div className="mb-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-ui-bodyText">
          {icons[signalType] || '📄'} Add {signalType}
        </span>
        <button onClick={onCancel} className="p-1 hover:bg-gray-200 rounded">
          <X className="h-4 w-4 text-ui-supportText" />
        </button>
      </div>
      <textarea
        value={signalContent}
        onChange={(e) => onContentChange(e.target.value)}
        placeholder={`Paste your ${signalType} content here...`}
        rows={4}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary resize-none"
      />
      <div className="flex items-center gap-2 mt-2">
        <input
          type="text"
          value={signalSource}
          onChange={(e) => onSourceChange(e.target.value)}
          placeholder={signalType === 'email' ? 'From: client@example.com' : 'Source (optional)'}
          className="flex-1 px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary"
        />
        <button
          onClick={onSubmit}
          disabled={!signalContent.trim() || sendingSignal}
          className="px-4 py-1.5 bg-brand-primary hover:bg-brand-primaryHover text-white rounded-lg text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-1"
        >
          {sendingSignal ? (
            <>
              <Loader2 className="h-3 w-3 animate-spin" />
              Processing...
            </>
          ) : (
            <>
              <Send className="h-3 w-3" />
              Submit
            </>
          )}
        </button>
      </div>
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

  // Check if any tool result contains a proposal
  const proposalData = message.toolCalls?.find(
    (tool) =>
      tool.tool_name === 'propose_features' &&
      tool.status === 'complete' &&
      tool.result?.proposal_id
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

  // System messages have different styling - subtle pill
  if (isSystem) {
    return (
      <div className="flex justify-center my-3">
        <div className="flex items-center gap-1.5 px-3 py-1 bg-gray-100 text-gray-500 rounded-full text-xs">
          <ChevronRight className="h-3 w-3" />
          <span>{message.content}</span>
        </div>
      </div>
    )
  }

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[85%] ${isUser ? 'order-2' : 'order-1'}`}>
        {/* Message Content - ALWAYS FIRST for assistant */}
        {message.content && (
          <div
            className={`px-4 py-2 rounded-lg ${
              isUser
                ? 'bg-brand-primary text-white'
                : 'bg-gray-100 text-ui-bodyText'
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
              className="flex items-center gap-2 text-xs text-ui-supportText hover:text-ui-bodyText transition-colors mb-1"
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
                      tool.status === 'running'
                        ? 'bg-brand-primary/5 border border-brand-primary/20'
                        : tool.status === 'error'
                          ? 'bg-red-50 border border-red-100'
                          : 'bg-gray-50'
                    }`}
                  >
                    {/* Status icon */}
                    <div className="flex-shrink-0 mt-0.5">
                      {tool.status === 'running' && (
                        <Loader2 className="h-3.5 w-3.5 animate-spin text-brand-primary" />
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
                      <div className="font-medium text-ui-bodyText">
                        {getToolDisplayName(tool.tool_name)}
                      </div>
                      {/* Show brief result summary if complete */}
                      {tool.status === 'complete' && tool.result?.message && (
                        <div className="text-ui-supportText mt-0.5 line-clamp-2">
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

        {/* Proposal Preview */}
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
          <p className="text-xs text-ui-supportText mt-1">
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
    identify_stakeholders: 'Identifying stakeholders',
    add_stakeholder: 'Adding stakeholder',
    // Enrichment
    enrich_features: 'Enriching features',
    enrich_personas: 'Enriching personas',
    generate_value_path: 'Generating value path',
    // Research
    search_research: 'Searching research',
    semantic_search_research: 'Semantic search',
    find_evidence_gaps: 'Finding evidence gaps',
    attach_evidence: 'Attaching evidence',
    // Proposals
    propose_features: 'Generating proposal',
    preview_proposal: 'Loading preview',
    apply_proposal: 'Applying changes',
    list_pending_proposals: 'Listing proposals',
    // Analysis
    analyze_gaps: 'Analyzing gaps',
    analyze_impact: 'Analyzing impact',
    get_stale_entities: 'Finding stale entities',
    refresh_stale_entity: 'Refreshing entity',
    // Status
    get_project_status: 'Getting project status',
    list_pending_confirmations: 'Listing confirmations',
    // Signals
    add_signal: 'Processing signal',
    // Creative brief
    get_creative_brief: 'Fetching creative brief',
    update_creative_brief: 'Updating creative brief',
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
