/**
 * AI Assistant Command Center
 *
 * A context-aware AI assistant for managing product requirements.
 * Provides slash commands, proactive behaviors, and mode-specific assistance.
 *
 * Usage:
 *
 * ```tsx
 * import { AssistantProvider, useAssistant } from '@/lib/assistant'
 *
 * // Wrap your app
 * <AssistantProvider projectId={projectId}>
 *   <YourApp />
 * </AssistantProvider>
 *
 * // Use in components
 * function ChatPanel() {
 *   const { sendMessage, context } = useAssistant()
 *   // ...
 * }
 * ```
 */

// Types
export type {
  TabType,
  AssistantMode,
  Entity,
  SelectedEntity,
  Message,
  MessageMetadata,
  ToolCall,
  QuickAction,
  CommandDefinition,
  CommandArg,
  CommandArgs,
  CommandResult,
  ModeConfig,
  ProactiveTrigger,
  ProactiveMessage,
  AssistantContext,
  ProjectContextData,
  ActivityItem,
  AssistantAction,
  UseAssistantReturn,
} from './types'

// Context and Hooks
export {
  AssistantProvider,
  useAssistant,
  useAssistantMode,
  useEntitySelection,
  useAssistantChat,
  useQuickActions,
  useProactiveMessages,
} from './context'

// Commands
export {
  registerCommand,
  getCommand,
  getAllCommands,
  findMatchingCommands,
  isCommand,
  parseCommand,
  executeCommand,
} from './commands'

// Modes
export {
  TAB_MODE_MAP,
  MODE_CONFIGS,
  getModeForTab,
  getModeConfig,
  getQuickActionsForMode,
  getSystemPromptForMode,
  getSuggestedCommandsForMode,
  getContextualQuickActions,
  getModeTransitionMessage,
} from './modes'

// Proactive Behaviors
export {
  registerTrigger,
  getAllTriggers,
  getTriggersByType,
  evaluateTriggers,
  evaluateAllTriggers,
  isMessageExpired,
  filterExpiredMessages,
  sortByPriority,
  getHighestPriorityMessage,
  onTabChange,
  onEntitySelected,
  onSignalAdded,
  onIdle,
  onPeriodicCheck,
} from './proactive'
