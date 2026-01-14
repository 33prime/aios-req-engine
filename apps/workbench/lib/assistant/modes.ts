/**
 * AI Assistant Command Center - Mode Configurations
 *
 * Defines how the assistant behaves in different contexts.
 * Each mode has its own system prompt, quick actions, and focus areas.
 */

import type {
  AssistantMode,
  TabType,
  ModeConfig,
  QuickAction,
} from './types'

// =============================================================================
// Tab to Mode Mapping
// =============================================================================

/**
 * Map tab types to assistant modes.
 */
export const TAB_MODE_MAP: Record<TabType, AssistantMode> = {
  'overview': 'overview',
  'definition': 'general',
  'features': 'features',
  'personas': 'personas',
  'value-path': 'value_path',
  'research': 'research',
  'sources': 'signals',
  'insights': 'research',
  'activity': 'general',
  'strategic-context': 'briefing',
  'creative-brief': 'briefing',
}

/**
 * Get the assistant mode for a given tab.
 */
export function getModeForTab(tab: TabType): AssistantMode {
  return TAB_MODE_MAP[tab] ?? 'general'
}

// =============================================================================
// Mode Configurations
// =============================================================================

export const MODE_CONFIGS: Record<AssistantMode, ModeConfig> = {
  // Overview mode - Project health and recommendations
  overview: {
    systemPrompt: `You are an AI assistant helping manage a product requirements project.
You are currently in Overview mode, focused on project health and progress.

Your role:
- Summarize project readiness and blockers
- Identify areas needing attention
- Suggest prioritized next steps
- Help prepare for meetings

Be concise and actionable. Focus on what needs immediate attention.`,

    quickActions: [
      {
        id: 'check-status',
        label: 'Check Status',
        command: '/status',
        variant: 'default',
      },
      {
        id: 'prep-meeting',
        label: 'Prep Meeting',
        command: '/briefing',
        variant: 'default',
      },
      {
        id: 'review-pending',
        label: 'Review Pending',
        command: '/review',
        variant: 'primary',
      },
    ],

    focusEntities: ['project', 'blocker', 'warning'],
    proactiveMessages: true,
    suggestedCommands: ['/status', '/briefing', '/review'],
    contextFields: ['readinessScore', 'blockers', 'warnings', 'pendingConfirmations', 'stats'],
  },

  // Signals mode - Signal processing and claim routing
  signals: {
    systemPrompt: `You are an AI assistant helping process and route signals.
You are currently in Signals mode, focused on ingesting and processing new information.

Your role:
- Help understand signal content and claims
- Route claims to appropriate entities
- Identify new entities from signals
- Track signal attribution

Focus on accuracy and proper attribution of information.`,

    quickActions: [
      {
        id: 'process-signal',
        label: 'Process Signal',
        icon: 'zap',
        variant: 'primary',
      },
      {
        id: 'view-claims',
        label: 'View Claims',
        icon: 'list',
      },
      {
        id: 'bulk-process',
        label: 'Bulk Process',
        icon: 'layers',
      },
    ],

    focusEntities: ['signal', 'claim'],
    proactiveMessages: true,
    suggestedCommands: ['/analyze', '/add', '/surgical'],
    contextFields: ['recentSignals', 'pendingClaims', 'processedToday'],
  },

  // Features mode - Feature management
  features: {
    systemPrompt: `You are an AI assistant helping manage product features.
You are currently in Features mode, focused on feature development and refinement.

Your role:
- Help analyze and improve feature definitions
- Ensure acceptance criteria are complete
- Track feature-persona relationships
- Identify gaps in feature coverage

Be specific about what makes features well-defined and actionable.`,

    quickActions: [
      {
        id: 'analyze-feature',
        label: 'Analyze',
        command: '/analyze',
        variant: 'default',
      },
      {
        id: 'enrich-feature',
        label: 'Enrich',
        command: '/enrich',
        variant: 'primary',
      },
      {
        id: 'add-feature',
        label: 'Add Feature',
        command: '/add feature',
        variant: 'default',
      },
      {
        id: 'confirm-feature',
        label: 'Confirm',
        command: '/confirm',
        variant: 'default',
      },
    ],

    focusEntities: ['feature'],
    proactiveMessages: true,
    suggestedCommands: ['/analyze', '/enrich', '/add feature', '/confirm'],
    contextFields: ['selectedFeature', 'relatedPersonas', 'acceptanceCriteria'],
  },

  // Personas mode - Persona development
  personas: {
    systemPrompt: `You are an AI assistant helping develop user personas.
You are currently in Personas mode, focused on understanding and documenting users.

Your role:
- Help flesh out persona details
- Identify pain points and goals
- Connect personas to features
- Ensure personas are evidence-based

Focus on making personas actionable and grounded in real user signals.`,

    quickActions: [
      {
        id: 'analyze-persona',
        label: 'Analyze',
        command: '/analyze',
        variant: 'default',
      },
      {
        id: 'enrich-persona',
        label: 'Enrich',
        command: '/enrich',
        variant: 'primary',
      },
      {
        id: 'add-persona',
        label: 'Add Persona',
        command: '/add persona',
        variant: 'default',
      },
      {
        id: 'view-evidence',
        label: 'View Evidence',
        icon: 'file-text',
      },
    ],

    focusEntities: ['persona'],
    proactiveMessages: true,
    suggestedCommands: ['/analyze', '/enrich', '/add persona', '/history'],
    contextFields: ['selectedPersona', 'painPoints', 'goals', 'relatedFeatures'],
  },

  // Value Path mode - VP flow analysis
  value_path: {
    systemPrompt: `You are an AI assistant helping design value path flows.
You are currently in Value Path mode, focused on user journey and value delivery.

Your role:
- Help structure the user journey
- Ensure logical step progression
- Connect VP steps to features
- Identify gaps in the value path

Focus on the end-to-end user experience and value realization.`,

    quickActions: [
      {
        id: 'analyze-step',
        label: 'Analyze Step',
        command: '/analyze',
        variant: 'default',
      },
      {
        id: 'add-step',
        label: 'Add Step',
        command: '/add vp_step',
        variant: 'primary',
      },
      {
        id: 'reorder-steps',
        label: 'Reorder',
        icon: 'move',
      },
      {
        id: 'view-flow',
        label: 'View Flow',
        icon: 'git-branch',
      },
    ],

    focusEntities: ['vp_step'],
    proactiveMessages: true,
    suggestedCommands: ['/analyze', '/add vp_step', '/surgical'],
    contextFields: ['selectedStep', 'adjacentSteps', 'supportingFeatures'],
  },

  // Research mode - Research queries and gap analysis
  research: {
    systemPrompt: `You are an AI assistant helping with product research.
You are currently in Research mode, focused on gathering and analyzing information.

Your role:
- Help identify research gaps
- Suggest research questions
- Analyze research findings
- Connect insights to entities

Focus on evidence-based decision making and filling knowledge gaps.`,

    quickActions: [
      {
        id: 'identify-gaps',
        label: 'Find Gaps',
        icon: 'search',
        variant: 'primary',
      },
      {
        id: 'suggest-questions',
        label: 'Suggest Questions',
        icon: 'help-circle',
      },
      {
        id: 'analyze-insights',
        label: 'Analyze Insights',
        command: '/analyze',
      },
    ],

    focusEntities: ['insight', 'signal', 'research_gap'],
    proactiveMessages: true,
    suggestedCommands: ['/analyze', '/add', '/status'],
    contextFields: ['recentInsights', 'researchGaps', 'pendingQuestions'],
  },

  // Briefing mode - Pre-meeting prep
  briefing: {
    systemPrompt: `You are an AI assistant helping prepare for meetings.
You are currently in Briefing mode, focused on summarization and preparation.

Your role:
- Generate meeting-ready summaries
- Highlight key discussion points
- Identify decisions needed
- Prepare stakeholder-appropriate content

Focus on clarity and actionability for meeting contexts.`,

    quickActions: [
      {
        id: 'client-briefing',
        label: 'Client Briefing',
        command: '/briefing client',
        variant: 'primary',
      },
      {
        id: 'internal-briefing',
        label: 'Internal Briefing',
        command: '/briefing internal',
      },
      {
        id: 'export-notes',
        label: 'Export Notes',
        icon: 'download',
      },
    ],

    focusEntities: ['project', 'decision', 'blocker'],
    proactiveMessages: false,
    suggestedCommands: ['/briefing', '/status', '/review'],
    contextFields: ['readinessScore', 'blockers', 'pendingDecisions', 'recentChanges'],
  },

  // General mode - Default fallback
  general: {
    systemPrompt: `You are an AI assistant helping manage a product requirements project.
You can help with any aspect of the project including features, personas, value paths, and research.

Available commands:
- /status - Check project health
- /analyze - Analyze selected entity
- /enrich - Trigger AI enrichment
- /add - Add new entities
- /confirm - Confirm entities
- /help - See all commands

How can I help you today?`,

    quickActions: [
      {
        id: 'check-status',
        label: 'Check Status',
        command: '/status',
        variant: 'default',
      },
      {
        id: 'help',
        label: 'Help',
        command: '/help',
        variant: 'default',
      },
    ],

    focusEntities: [],
    proactiveMessages: false,
    suggestedCommands: ['/help', '/status'],
    contextFields: ['readinessScore', 'stats'],
  },
}

/**
 * Get configuration for a mode.
 */
export function getModeConfig(mode: AssistantMode): ModeConfig {
  return MODE_CONFIGS[mode] ?? MODE_CONFIGS.general
}

/**
 * Get quick actions for a mode.
 */
export function getQuickActionsForMode(mode: AssistantMode): QuickAction[] {
  return getModeConfig(mode).quickActions
}

/**
 * Get system prompt for a mode.
 */
export function getSystemPromptForMode(mode: AssistantMode): string {
  return getModeConfig(mode).systemPrompt
}

/**
 * Get suggested commands for a mode.
 */
export function getSuggestedCommandsForMode(mode: AssistantMode): string[] {
  return getModeConfig(mode).suggestedCommands
}

// =============================================================================
// Dynamic Mode Adjustments
// =============================================================================

/**
 * Adjust mode configuration based on context.
 * Returns modified quick actions based on current state.
 */
export function getContextualQuickActions(
  mode: AssistantMode,
  context: {
    hasSelectedEntity: boolean
    hasPendingConfirmations: boolean
    hasBlockers: boolean
    entityType?: string
  }
): QuickAction[] {
  const baseActions = [...getModeConfig(mode).quickActions]
  const contextualActions: QuickAction[] = []

  // Add contextual actions based on state
  if (context.hasSelectedEntity) {
    // Add entity-specific actions
    if (!baseActions.some(a => a.command === '/analyze')) {
      contextualActions.push({
        id: 'ctx-analyze',
        label: 'Analyze Selected',
        command: '/analyze',
      })
    }
    if (!baseActions.some(a => a.command === '/enrich')) {
      contextualActions.push({
        id: 'ctx-enrich',
        label: 'Enrich Selected',
        command: '/enrich',
        variant: 'primary',
      })
    }
  }

  if (context.hasPendingConfirmations) {
    if (!baseActions.some(a => a.command === '/review')) {
      contextualActions.push({
        id: 'ctx-review',
        label: 'Review Pending',
        command: '/review',
        variant: 'warning',
      })
    }
  }

  if (context.hasBlockers) {
    contextualActions.push({
      id: 'ctx-blockers',
      label: 'View Blockers',
      command: '/blockers',
      variant: 'danger',
    })
  }

  // Merge and dedupe
  const allActions = [...baseActions, ...contextualActions]
  const seen = new Set<string>()
  return allActions.filter(action => {
    const key = action.id
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

// =============================================================================
// Mode Transitions
// =============================================================================

/**
 * Define valid mode transitions and their behaviors.
 */
export const MODE_TRANSITIONS: Record<AssistantMode, {
  allowedFrom: AssistantMode[]
  onEnter?: string  // Message to show when entering this mode
}> = {
  overview: {
    allowedFrom: ['general', 'features', 'personas', 'value_path', 'research', 'signals', 'briefing'],
    onEnter: 'Switched to Overview mode. I can help you check project health and plan next steps.',
  },
  signals: {
    allowedFrom: ['general', 'overview', 'features', 'personas'],
    onEnter: 'Switched to Signals mode. I can help process and route incoming signals.',
  },
  features: {
    allowedFrom: ['general', 'overview', 'personas', 'value_path', 'signals'],
    onEnter: 'Switched to Features mode. I can help analyze and improve feature definitions.',
  },
  personas: {
    allowedFrom: ['general', 'overview', 'features', 'value_path', 'signals'],
    onEnter: 'Switched to Personas mode. I can help develop and refine user personas.',
  },
  value_path: {
    allowedFrom: ['general', 'overview', 'features', 'personas'],
    onEnter: 'Switched to Value Path mode. I can help design the user journey.',
  },
  research: {
    allowedFrom: ['general', 'overview', 'features', 'personas', 'signals'],
    onEnter: 'Switched to Research mode. I can help identify gaps and analyze findings.',
  },
  briefing: {
    allowedFrom: ['general', 'overview'],
    onEnter: 'Switched to Briefing mode. I can help prepare meeting summaries and discussion points.',
  },
  general: {
    allowedFrom: ['overview', 'signals', 'features', 'personas', 'value_path', 'research', 'briefing'],
  },
}

/**
 * Get the transition message when entering a mode.
 */
export function getModeTransitionMessage(mode: AssistantMode): string | undefined {
  return MODE_TRANSITIONS[mode]?.onEnter
}
