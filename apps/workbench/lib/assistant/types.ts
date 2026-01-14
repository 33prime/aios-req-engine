/**
 * AI Assistant Command Center - Types
 *
 * Type definitions for the context-aware AI assistant system.
 */

// =============================================================================
// Tab and Mode Types
// =============================================================================

export type TabType =
  | 'overview'
  | 'definition'
  | 'features'
  | 'personas'
  | 'value-path'
  | 'research'
  | 'sources'
  | 'insights'
  | 'activity'
  | 'strategic-context'
  | 'creative-brief'

export type AssistantMode =
  | 'overview'      // Project health, blockers, recommendations
  | 'signals'       // Signal processing, claim routing
  | 'features'      // Feature management, enrichment
  | 'personas'      // Persona development
  | 'value_path'    // VP flow analysis
  | 'research'      // Research queries, gap analysis
  | 'briefing'      // Pre-meeting prep
  | 'general'       // Default fallback mode

// =============================================================================
// Entity Types
// =============================================================================

export interface Entity {
  id: string
  type: 'feature' | 'persona' | 'vp_step' | 'signal' | 'insight'
  name: string
  status?: string
  data?: Record<string, unknown>
}

export interface SelectedEntity extends Entity {
  selectedAt: Date
}

// =============================================================================
// Message Types
// =============================================================================

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  isStreaming?: boolean
  metadata?: MessageMetadata
  toolCalls?: ToolCall[]
}

export interface MessageMetadata {
  command?: string
  commandArgs?: string
  mode?: AssistantMode
  context?: Record<string, unknown>
}

export interface ToolCall {
  id: string
  tool_name: string
  status: 'pending' | 'running' | 'complete' | 'error'
  args?: Record<string, unknown>
  result?: unknown
  error?: string
}

// =============================================================================
// Quick Action Types
// =============================================================================

export interface QuickAction {
  id: string
  label: string
  icon?: string
  description?: string
  command?: string        // Slash command to execute
  action?: () => void     // Direct action callback
  variant?: 'default' | 'primary' | 'warning' | 'danger'
  disabled?: boolean
  navigateTo?: {          // Navigation on click
    tab?: TabType
    entityType?: string
    entityId?: string
  }
}

// =============================================================================
// Command Types
// =============================================================================

export interface CommandDefinition {
  name: string
  description: string
  aliases?: string[]
  args?: CommandArg[]
  execute: (args: CommandArgs, context: AssistantContext) => Promise<CommandResult>
  examples?: string[]
}

export interface CommandArg {
  name: string
  type: 'string' | 'number' | 'boolean' | 'entity'
  required?: boolean
  description?: string
}

export type CommandArgs = Record<string, string | number | boolean | undefined>

export interface CommandResult {
  success: boolean
  message?: string
  data?: unknown
  actions?: QuickAction[]  // Follow-up actions to suggest
  navigateTo?: {
    tab?: TabType
    entityType?: string
    entityId?: string
  }
}

// =============================================================================
// Mode Configuration Types
// =============================================================================

export interface ModeConfig {
  systemPrompt: string
  quickActions: QuickAction[]
  focusEntities: string[]
  proactiveMessages: boolean
  suggestedCommands: string[]
  contextFields: string[]  // What data to include in context
}

// =============================================================================
// Proactive Behavior Types
// =============================================================================

export interface ProactiveTrigger {
  id: string
  type: 'tab_switch' | 'signal_added' | 'entity_selected' | 'idle' | 'periodic'
  condition?: (context: AssistantContext) => boolean
  handler: (context: AssistantContext) => Promise<ProactiveMessage | null>
  cooldownMs?: number
  lastTriggered?: Date
}

export interface ProactiveMessage {
  message: string
  priority: 'low' | 'medium' | 'high'
  actions?: QuickAction[]
  dismissable?: boolean
  expiresAt?: Date
}

// =============================================================================
// Context Types
// =============================================================================

export interface AssistantContext {
  // Current state
  projectId: string
  activeTab: TabType
  mode: AssistantMode

  // Selected entity
  selectedEntity: SelectedEntity | null

  // Conversation
  messages: Message[]
  isLoading: boolean

  // Quick actions for current context
  suggestedActions: QuickAction[]

  // Proactive messages
  pendingProactiveMessages: ProactiveMessage[]

  // Project data (cached)
  projectData?: ProjectContextData
}

export interface ProjectContextData {
  name?: string
  readinessScore?: number
  blockers?: string[]
  warnings?: string[]
  pendingConfirmations?: number
  recentActivity?: ActivityItem[]
  stats?: {
    features: number
    personas: number
    vpSteps: number
    signals: number
  }
}

export interface ActivityItem {
  id: string
  type: string
  message: string
  timestamp: Date
  entityType?: string
  entityId?: string
}

// =============================================================================
// Context Actions (for useReducer)
// =============================================================================

export type AssistantAction =
  | { type: 'SET_TAB'; tab: TabType }
  | { type: 'SET_MODE'; mode: AssistantMode }
  | { type: 'SELECT_ENTITY'; entity: Entity | null }
  | { type: 'ADD_MESSAGE'; message: Message }
  | { type: 'UPDATE_MESSAGE'; id: string; updates: Partial<Message> }
  | { type: 'SET_LOADING'; isLoading: boolean }
  | { type: 'SET_QUICK_ACTIONS'; actions: QuickAction[] }
  | { type: 'ADD_PROACTIVE_MESSAGE'; message: ProactiveMessage }
  | { type: 'DISMISS_PROACTIVE_MESSAGE'; index: number }
  | { type: 'UPDATE_PROJECT_DATA'; data: Partial<ProjectContextData> }
  | { type: 'CLEAR_MESSAGES' }
  | { type: 'RESET' }

// =============================================================================
// Hook Return Types
// =============================================================================

export interface UseAssistantReturn {
  // State
  context: AssistantContext

  // Tab/Mode management
  setActiveTab: (tab: TabType) => void
  setMode: (mode: AssistantMode) => void

  // Entity selection
  selectEntity: (entity: Entity | null) => void

  // Messaging
  sendMessage: (content: string) => Promise<void>
  clearMessages: () => void

  // Commands
  executeCommand: (command: string, args?: CommandArgs) => Promise<CommandResult>
  parseAndExecute: (input: string) => Promise<void>

  // Quick actions
  getQuickActions: () => QuickAction[]
  executeQuickAction: (actionId: string) => Promise<void>

  // Proactive
  dismissProactiveMessage: (index: number) => void

  // Utilities
  isCommand: (input: string) => boolean
  getCommandSuggestions: (input: string) => CommandDefinition[]
}
