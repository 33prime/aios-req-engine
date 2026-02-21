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
  'strategic-foundation': 'strategic_foundation',
  'personas-features': 'personas_features',
  'value-path': 'value_path',
  'sources': 'signals',
  'next-steps': 'next_steps',
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
        id: 'run-di',
        label: 'Run DI Analysis',
        command: '/di',
        variant: 'primary',
      },
      {
        id: 'view-gates',
        label: 'View Gates',
        command: '/view-gates',
        variant: 'default',
      },
    ],

    focusEntities: ['project', 'blocker', 'warning'],
    proactiveMessages: true,
    suggestedCommands: ['/status', '/di', '/view-gates'],
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
    suggestedCommands: ['/analyze', '/add feature', '/confirm'],
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
    suggestedCommands: ['/analyze', '/add persona', '/history'],
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
        id: 'analyze-value-path',
        label: 'Analyze Path',
        command: '/analyze',
        variant: 'primary',
      },
    ],

    focusEntities: ['vp_step'],
    proactiveMessages: true,
    suggestedCommands: ['/analyze'],
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

  // Strategic Foundation mode - Company info, drivers, competitors
  strategic_foundation: {
    systemPrompt: `You are helping build the strategic foundation for this project.
Focus on extracting and organizing company information, business drivers, and competitive landscape.

Your role:
- Help extract company details from signals
- Identify business drivers and objectives
- Find and track competitors
- Build strategic context

Use /run-foundation to enrich company info from signals, or /run-research for deep web research.`,

    quickActions: [
      {
        id: 'run-foundation',
        label: 'Run Foundation',
        command: '/run-foundation',
        variant: 'primary',
      },
      {
        id: 'run-research',
        label: 'Run Research',
        command: '/run-research',
        variant: 'default',
      },
      {
        id: 'enrich-drivers',
        label: 'Enrich Drivers',
        command: '/enrich-business-drivers',
        variant: 'default',
      },
      {
        id: 'view-foundation',
        label: 'View Foundation',
        command: '/view-foundation',
        variant: 'default',
      },
    ],

    focusEntities: ['company_info', 'business_driver', 'competitor', 'stakeholder'],
    proactiveMessages: true,
    suggestedCommands: ['/run-foundation', '/run-research', '/enrich-business-drivers', '/view-foundation'],
    contextFields: ['companyInfo', 'businessDrivers', 'competitors', 'stakeholders'],
  },

  // Personas & Features mode - Combined personas and features management
  personas_features: {
    systemPrompt: `You are an AI assistant helping manage personas and features.
You are currently in Personas & Features mode, focused on user personas and product features.

Your role:
- Help develop and refine user personas
- Analyze and improve feature definitions
- Connect personas to relevant features
- Ensure personas and features are evidence-based

Ask me to analyze personas, improve features, or check for gaps.`,

    quickActions: [
      {
        id: 'analyze-personas',
        label: 'Analyze Personas',
        command: '/analyze',
        variant: 'primary',
      },
      {
        id: 'add-feature',
        label: 'Add Feature',
        command: '/add feature',
        variant: 'default',
      },
    ],

    focusEntities: ['persona', 'feature'],
    proactiveMessages: true,
    suggestedCommands: ['/analyze', '/add feature', '/confirm'],
    contextFields: ['personas', 'features', 'personaFeatureLinks'],
  },

  // Next Steps mode - Action items and confirmations
  next_steps: {
    systemPrompt: `You are an AI assistant helping manage action items and confirmations.
You are currently in Next Steps mode, focused on what needs to happen next.

Your role:
- Identify items needing confirmation
- Suggest prioritized next actions
- Track pending decisions
- Help prepare for client reviews

Use /tasks to see current tasks, or /sync-tasks to analyze gaps and create tasks.`,

    quickActions: [
      {
        id: 'view-tasks',
        label: 'View Tasks',
        command: '/tasks',
        variant: 'default',
      },
      {
        id: 'sync-tasks',
        label: 'Sync Tasks',
        command: '/sync-tasks',
        variant: 'primary',
      },
    ],

    focusEntities: ['confirmation', 'decision', 'blocker'],
    proactiveMessages: true,
    suggestedCommands: ['/tasks', '/sync-tasks'],
    contextFields: ['pendingConfirmations', 'blockers', 'nextActions'],
  },

  // General mode - Default fallback
  general: {
    systemPrompt: `You are an AI assistant helping manage a product requirements project.
You can help with any aspect of the project including features, personas, value paths, and research.

Available commands:
- /status - Check project health
- /analyze - Analyze selected entity
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
    allowedFrom: ['general', 'features', 'personas', 'personas_features', 'value_path', 'research', 'signals', 'briefing', 'strategic_foundation', 'next_steps'],
    onEnter: 'Switched to Overview mode. I can help you check project health and plan next steps.',
  },
  signals: {
    allowedFrom: ['general', 'overview', 'features', 'personas', 'personas_features'],
    onEnter: 'Switched to Sources mode. I can help process and route incoming signals.',
  },
  features: {
    allowedFrom: ['general', 'overview', 'personas', 'personas_features', 'value_path', 'signals'],
    onEnter: 'Switched to Features mode. I can help analyze and improve feature definitions.',
  },
  personas: {
    allowedFrom: ['general', 'overview', 'features', 'personas_features', 'value_path', 'signals'],
    onEnter: 'Switched to Personas mode. I can help develop and refine user personas.',
  },
  personas_features: {
    allowedFrom: ['general', 'overview', 'strategic_foundation', 'value_path', 'signals', 'next_steps'],
    onEnter: 'Switched to Personas & Features. I can help analyze and refine personas and features.',
  },
  value_path: {
    allowedFrom: ['general', 'overview', 'features', 'personas', 'personas_features'],
    onEnter: 'Switched to Value Path mode. I can help design the user journey.',
  },
  research: {
    allowedFrom: ['general', 'overview', 'features', 'personas', 'personas_features', 'signals'],
    onEnter: 'Switched to Research mode. I can help identify gaps and analyze findings.',
  },
  briefing: {
    allowedFrom: ['general', 'overview'],
    onEnter: 'Switched to Briefing mode. I can help prepare meeting summaries and discussion points.',
  },
  strategic_foundation: {
    allowedFrom: ['general', 'overview', 'personas_features', 'next_steps'],
    onEnter: 'Switched to Strategic Foundation. Use /run-foundation to enrich client info.',
  },
  next_steps: {
    allowedFrom: ['general', 'overview', 'strategic_foundation', 'personas_features', 'value_path', 'signals'],
    onEnter: 'Switched to Next Steps. Use /pending-items to see what needs review.',
  },
  general: {
    allowedFrom: ['overview', 'signals', 'features', 'personas', 'personas_features', 'value_path', 'research', 'briefing', 'strategic_foundation', 'next_steps'],
  },
}

/**
 * Get the transition message when entering a mode.
 */
export function getModeTransitionMessage(mode: AssistantMode): string | undefined {
  return MODE_TRANSITIONS[mode]?.onEnter
}
