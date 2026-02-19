'use client'

/**
 * AI Assistant Command Center - Context Provider
 *
 * React context and hooks for the AI assistant.
 * Manages state, commands, and proactive behaviors.
 */

import {
  createContext,
  useContext,
  useReducer,
  useCallback,
  useEffect,
  useRef,
  type ReactNode,
} from 'react'

// Generate unique IDs using crypto API
const generateId = (): string => {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  // Fallback for older environments
  return `${Date.now()}-${Math.random().toString(36).substring(2, 11)}`
}

import type {
  AssistantContext,
  AssistantAction,
  AssistantMode,
  TabType,
  Entity,
  Message,
  QuickAction,
  UseAssistantReturn,
  ProactiveMessage,
  ProjectContextData,
} from './types'

import {
  getModeForTab,
  getModeConfig,
  getContextualQuickActions,
  getModeTransitionMessage,
} from './modes'

import {
  onTabChange,
  onEntitySelected,
  onIdle,
  filterExpiredMessages,
} from './proactive'

// =============================================================================
// Initial State
// =============================================================================

const createInitialContext = (projectId: string): AssistantContext => ({
  projectId,
  activeTab: 'overview',
  mode: 'overview',
  selectedEntity: null,
  messages: [],
  isLoading: false,
  // Initialize with overview mode's quick actions
  suggestedActions: getContextualQuickActions('overview', {
    hasSelectedEntity: false,
    hasPendingConfirmations: false,
    hasBlockers: false,
  }),
  pendingProactiveMessages: [],
  projectData: undefined,
})

// =============================================================================
// Reducer
// =============================================================================

function assistantReducer(
  state: AssistantContext,
  action: AssistantAction
): AssistantContext {
  switch (action.type) {
    case 'SET_TAB':
      return {
        ...state,
        activeTab: action.tab,
        mode: getModeForTab(action.tab),
      }

    case 'SET_MODE':
      return {
        ...state,
        mode: action.mode,
      }

    case 'SELECT_ENTITY':
      return {
        ...state,
        selectedEntity: action.entity
          ? { ...action.entity, selectedAt: new Date() }
          : null,
      }

    case 'ADD_MESSAGE':
      return {
        ...state,
        messages: [...state.messages, action.message],
      }

    case 'UPDATE_MESSAGE':
      return {
        ...state,
        messages: state.messages.map((m) =>
          m.id === action.id ? { ...m, ...action.updates } : m
        ),
      }

    case 'SET_LOADING':
      return {
        ...state,
        isLoading: action.isLoading,
      }

    case 'SET_QUICK_ACTIONS':
      return {
        ...state,
        suggestedActions: action.actions,
      }

    case 'ADD_PROACTIVE_MESSAGE':
      return {
        ...state,
        pendingProactiveMessages: [
          ...state.pendingProactiveMessages,
          action.message,
        ],
      }

    case 'DISMISS_PROACTIVE_MESSAGE':
      return {
        ...state,
        pendingProactiveMessages: state.pendingProactiveMessages.filter(
          (_, i) => i !== action.index
        ),
      }

    case 'UPDATE_PROJECT_DATA':
      return {
        ...state,
        projectData: {
          ...state.projectData,
          ...action.data,
        },
      }

    case 'CLEAR_MESSAGES':
      return {
        ...state,
        messages: [],
      }

    case 'RESET':
      return createInitialContext(state.projectId)

    default:
      return state
  }
}

// =============================================================================
// Context
// =============================================================================

const AssistantContextValue = createContext<UseAssistantReturn | null>(null)

// =============================================================================
// Provider Component
// =============================================================================

interface AssistantProviderProps {
  children: ReactNode
  projectId: string
  initialProjectData?: ProjectContextData
  onSendMessage?: (content: string, context: AssistantContext) => Promise<string>
  /** Callback when project data should be refreshed (e.g., after DI Agent actions) */
  onProjectDataChanged?: () => Promise<void>
}

export function AssistantProvider({
  children,
  projectId,
  initialProjectData,
  onSendMessage,
  onProjectDataChanged,
}: AssistantProviderProps) {
  const [context, dispatch] = useReducer(
    assistantReducer,
    projectId,
    createInitialContext
  )

  const idleTimerRef = useRef<NodeJS.Timeout | null>(null)
  const lastActivityRef = useRef<Date>(new Date())

  // Initialize with project data - only update when values actually change
  const prevProjectDataRef = useRef<string>('')
  useEffect(() => {
    if (initialProjectData) {
      const dataString = JSON.stringify(initialProjectData)
      if (dataString !== prevProjectDataRef.current) {
        prevProjectDataRef.current = dataString
        dispatch({ type: 'UPDATE_PROJECT_DATA', data: initialProjectData })
      }
    }
  }, [initialProjectData])

  // Update quick actions when mode or context changes
  useEffect(() => {
    const contextualActions = getContextualQuickActions(context.mode, {
      hasSelectedEntity: context.selectedEntity !== null,
      hasPendingConfirmations: (context.projectData?.pendingConfirmations ?? 0) > 0,
      hasBlockers: (context.projectData?.blockers?.length ?? 0) > 0,
      entityType: context.selectedEntity?.type,
    })
    dispatch({ type: 'SET_QUICK_ACTIONS', actions: contextualActions })
  }, [context.mode, context.selectedEntity, context.projectData])

  // Clean up expired proactive messages
  useEffect(() => {
    const interval = setInterval(() => {
      const filtered = filterExpiredMessages(context.pendingProactiveMessages)
      if (filtered.length !== context.pendingProactiveMessages.length) {
        // There were expired messages, update state
        context.pendingProactiveMessages.forEach((msg, i) => {
          if (!filtered.includes(msg)) {
            dispatch({ type: 'DISMISS_PROACTIVE_MESSAGE', index: i })
          }
        })
      }
    }, 10000) // Check every 10 seconds

    return () => clearInterval(interval)
  }, [context.pendingProactiveMessages])

  // Idle timer for proactive messages - only set up once
  const contextRef = useRef(context)
  contextRef.current = context  // Keep ref updated without triggering effect

  useEffect(() => {
    const resetIdleTimer = () => {
      lastActivityRef.current = new Date()
      if (idleTimerRef.current) {
        clearTimeout(idleTimerRef.current)
      }
      idleTimerRef.current = setTimeout(async () => {
        const message = await onIdle(contextRef.current)
        if (message) {
          dispatch({ type: 'ADD_PROACTIVE_MESSAGE', message })
        }
      }, 180000) // 3 minutes idle
    }

    resetIdleTimer()
    return () => {
      if (idleTimerRef.current) {
        clearTimeout(idleTimerRef.current)
      }
    }
  }, []) // Only run once on mount

  // Tab change handler - uses contextRef to avoid [context] dependency causing infinite loops
  const setActiveTab = useCallback(
    async (tab: TabType) => {
      const currentContext = contextRef.current
      const previousTab = currentContext.activeTab
      dispatch({ type: 'SET_TAB', tab })

      // Check for proactive messages on tab change
      const newContext = { ...currentContext, activeTab: tab, mode: getModeForTab(tab) }
      const message = await onTabChange(newContext)
      if (message) {
        dispatch({ type: 'ADD_PROACTIVE_MESSAGE', message })
      }

      // Mode transitions no longer add system messages to reduce chat clutter
    },
    [] // No dependencies - uses contextRef
  )

  // Mode change handler
  const setMode = useCallback((mode: AssistantMode) => {
    dispatch({ type: 'SET_MODE', mode })
  }, [])

  // Entity selection handler - uses contextRef to avoid [context] dependency causing infinite loops
  const selectEntity = useCallback(
    async (entity: Entity | null) => {
      dispatch({ type: 'SELECT_ENTITY', entity })

      if (entity) {
        // Check for proactive messages on entity selection
        const currentContext = contextRef.current
        const newContext = {
          ...currentContext,
          selectedEntity: { ...entity, selectedAt: new Date() },
        }
        const message = await onEntitySelected(newContext)
        if (message) {
          dispatch({ type: 'ADD_PROACTIVE_MESSAGE', message })
        }
      }
    },
    [] // No dependencies - uses contextRef
  )

  // Send message handler - uses contextRef to avoid [context] dependency causing infinite loops
  const sendMessage = useCallback(
    async (content: string) => {
      const trimmedContent = content.trim()
      if (!trimmedContent) return

      // Add user message
      const userMessage: Message = {
        id: generateId(),
        role: 'user',
        content: trimmedContent,
        timestamp: new Date(),
      }
      dispatch({ type: 'ADD_MESSAGE', message: userMessage })
      dispatch({ type: 'SET_LOADING', isLoading: true })

      try {
        const currentContext = contextRef.current
        if (onSendMessage) {
          const response = await onSendMessage(trimmedContent, currentContext)
          const assistantMessage: Message = {
            id: generateId(),
            role: 'assistant',
            content: response,
            timestamp: new Date(),
            metadata: {
              mode: currentContext.mode,
            },
          }
          dispatch({ type: 'ADD_MESSAGE', message: assistantMessage })
        }
      } catch (error) {
        const errorMessage: Message = {
          id: generateId(),
          role: 'assistant',
          content: `An error occurred: ${error instanceof Error ? error.message : 'Unknown error'}`,
          timestamp: new Date(),
        }
        dispatch({ type: 'ADD_MESSAGE', message: errorMessage })
      } finally {
        dispatch({ type: 'SET_LOADING', isLoading: false })
      }
    },
    [onSendMessage]
  )

  // Clear messages handler
  const clearMessages = useCallback(() => {
    dispatch({ type: 'CLEAR_MESSAGES' })
  }, [])

  // Get current quick actions
  const getQuickActions = useCallback((): QuickAction[] => {
    return context.suggestedActions
  }, [context.suggestedActions])

  // Execute quick action
  const executeQuickAction = useCallback(
    async (actionId: string) => {
      const action = context.suggestedActions.find((a) => a.id === actionId)
      if (!action) return

      if (action.command) {
        await sendMessage(action.command)
      } else if (action.action) {
        action.action()
      }
    },
    [context.suggestedActions, sendMessage]
  )

  // Dismiss proactive message
  const dismissProactiveMessage = useCallback((index: number) => {
    dispatch({ type: 'DISMISS_PROACTIVE_MESSAGE', index })
  }, [])

  // Build the return value
  const value: UseAssistantReturn = {
    context,
    setActiveTab,
    setMode,
    selectEntity,
    sendMessage,
    clearMessages,
    getQuickActions,
    executeQuickAction,
    dismissProactiveMessage,
  }

  return (
    <AssistantContextValue.Provider value={value}>
      {children}
    </AssistantContextValue.Provider>
  )
}

// =============================================================================
// Hook
// =============================================================================

/**
 * Hook to access the assistant context.
 */
export function useAssistant(): UseAssistantReturn {
  const context = useContext(AssistantContextValue)
  if (!context) {
    throw new Error('useAssistant must be used within an AssistantProvider')
  }
  return context
}

// =============================================================================
// Utility Hooks
// =============================================================================

/**
 * Hook for just the current mode and tab.
 */
export function useAssistantMode() {
  const { context, setActiveTab, setMode } = useAssistant()
  return {
    mode: context.mode,
    tab: context.activeTab,
    setActiveTab,
    setMode,
  }
}

/**
 * Hook for entity selection.
 */
export function useEntitySelection() {
  const { context, selectEntity } = useAssistant()
  return {
    selectedEntity: context.selectedEntity,
    selectEntity,
  }
}

/**
 * Hook for messages and sending.
 */
export function useAssistantChat() {
  const { context, sendMessage, clearMessages } = useAssistant()
  return {
    messages: context.messages,
    isLoading: context.isLoading,
    sendMessage,
    clearMessages,
  }
}

/**
 * Hook for quick actions.
 */
export function useQuickActions() {
  const { context, getQuickActions, executeQuickAction } = useAssistant()
  return {
    actions: context.suggestedActions,
    getQuickActions,
    executeQuickAction,
  }
}

/**
 * Hook for proactive messages.
 */
export function useProactiveMessages() {
  const { context, dismissProactiveMessage } = useAssistant()
  return {
    messages: context.pendingProactiveMessages,
    dismiss: dismissProactiveMessage,
  }
}

