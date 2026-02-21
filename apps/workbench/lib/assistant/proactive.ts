/**
 * AI Assistant Command Center - Proactive Behaviors
 *
 * Defines triggers for proactive assistant messages.
 * The assistant can surface relevant information without being asked.
 */

import type {
  ProactiveTrigger,
  ProactiveMessage,
  AssistantContext,
  QuickAction,
} from './types'

// =============================================================================
// Trigger Registry
// =============================================================================

const triggers: Map<string, ProactiveTrigger> = new Map()

/**
 * Register a proactive trigger.
 */
export function registerTrigger(trigger: ProactiveTrigger): void {
  triggers.set(trigger.id, trigger)
}

/**
 * Get all registered triggers.
 */
export function getAllTriggers(): ProactiveTrigger[] {
  return Array.from(triggers.values())
}

/**
 * Get triggers by type.
 */
export function getTriggersByType(type: ProactiveTrigger['type']): ProactiveTrigger[] {
  return getAllTriggers().filter((t) => t.type === type)
}

// =============================================================================
// Trigger Implementations
// =============================================================================

// Tab Switch Triggers
registerTrigger({
  id: 'tab-switch-overview',
  type: 'tab_switch',
  cooldownMs: 30000, // 30 seconds
  condition: (context) => context.activeTab === 'overview',
  handler: async (context): Promise<ProactiveMessage | null> => {
    const { projectData } = context

    // Only trigger if there are actionable items
    const hasBlockers = (projectData?.blockers?.length ?? 0) > 0
    const hasPending = (projectData?.pendingConfirmations ?? 0) > 0

    if (!hasBlockers && !hasPending) {
      return null
    }

    const actions: QuickAction[] = []
    let message = ''

    if (hasBlockers) {
      message = `There are ${projectData!.blockers!.length} blockers that may need attention.`
      actions.push({
        id: 'view-blockers',
        label: 'View Blockers',
        command: '/blockers',
        variant: 'warning',
      })
    }

    if (hasPending) {
      message += message ? '\n\n' : ''
      message += `${projectData!.pendingConfirmations} items are pending confirmation.`
      actions.push({
        id: 'review-pending',
        label: 'Review Pending',
        command: '/review',
        variant: 'primary',
      })
    }

    return {
      message,
      priority: hasBlockers ? 'high' : 'medium',
      actions,
      dismissable: true,
    }
  },
})

registerTrigger({
  id: 'tab-switch-personas-features-empty',
  type: 'tab_switch',
  cooldownMs: 60000, // 1 minute
  condition: (context) => context.activeTab === 'personas-features',
  handler: async (context): Promise<ProactiveMessage | null> => {
    const featureCount = context.projectData?.stats?.features ?? 0
    const personaCount = context.projectData?.stats?.personas ?? 0

    if (featureCount === 0 && personaCount === 0) {
      return {
        message: 'No personas or features defined yet. Use /run-foundation to extract from signals, or add them manually.',
        priority: 'medium',
        actions: [
          {
            id: 'run-foundation',
            label: 'Run Foundation',
            command: '/run-foundation',
            variant: 'primary',
          },
        ],
        dismissable: true,
      }
    }

    if (personaCount > 0 && personaCount < 3) {
      return {
        message: 'Tip: Well-defined products typically have 3-5 primary personas. Consider if there are other user types to capture.',
        priority: 'low',
        dismissable: true,
      }
    }

    return null
  },
})

// Entity Selection Triggers
registerTrigger({
  id: 'entity-selected-unconfirmed',
  type: 'entity_selected',
  cooldownMs: 10000, // 10 seconds
  condition: (context) => {
    const entity = context.selectedEntity
    return entity !== null && entity.status === 'ai_generated'
  },
  handler: async (context): Promise<ProactiveMessage | null> => {
    const entity = context.selectedEntity!

    return {
      message: `This ${entity.type} was AI-generated and hasn't been confirmed yet. Review it for accuracy.`,
      priority: 'medium',
      actions: [
        {
          id: 'confirm-entity',
          label: 'Confirm',
          command: '/confirm consultant',
          variant: 'primary',
        },
        {
          id: 'analyze-entity',
          label: 'Analyze First',
          command: '/analyze',
        },
      ],
      dismissable: true,
    }
  },
})

registerTrigger({
  id: 'entity-selected-needs-client',
  type: 'entity_selected',
  cooldownMs: 10000,
  condition: (context) => {
    const entity = context.selectedEntity
    return entity !== null && entity.status === 'needs_client'
  },
  handler: async (context): Promise<ProactiveMessage | null> => {
    const entity = context.selectedEntity!

    return {
      message: `This ${entity.type} needs client confirmation. Consider discussing in your next meeting.`,
      priority: 'high',
      actions: [
        {
          id: 'add-to-briefing',
          label: 'Add to Briefing',
          icon: 'file-plus',
        },
        {
          id: 'confirm-client',
          label: 'Mark Confirmed',
          command: '/confirm client',
          variant: 'primary',
        },
      ],
      dismissable: true,
    }
  },
})

// Idle Triggers
registerTrigger({
  id: 'idle-suggestions',
  type: 'idle',
  cooldownMs: 300000, // 5 minutes
  handler: async (context): Promise<ProactiveMessage | null> => {
    const { projectData, mode } = context

    // Different suggestions based on mode
    if (mode === 'personas_features' || mode === 'features') {
      const hasFeatures = (projectData?.stats?.features ?? 0) > 0
      if (hasFeatures) {
        return {
          message: 'Need help with anything? I can analyze personas, check for gaps, or review project status.',
          priority: 'low',
          actions: [
            {
              id: 'check-status',
              label: 'Check Status',
              command: '/status',
            },
            {
              id: 'analyze',
              label: 'Analyze',
              command: '/analyze',
            },
          ],
          dismissable: true,
          expiresAt: new Date(Date.now() + 60000), // Expires in 1 minute
        }
      }
    }

    return null
  },
})

// Periodic Triggers
registerTrigger({
  id: 'periodic-health-check',
  type: 'periodic',
  cooldownMs: 600000, // 10 minutes
  handler: async (context): Promise<ProactiveMessage | null> => {
    const { projectData } = context

    // Check if readiness dropped
    const readiness = projectData?.readinessScore ?? 0

    if (readiness < 50) {
      return {
        message: `Project readiness is at ${readiness}%. There may be gaps that need attention.`,
        priority: 'medium',
        actions: [
          {
            id: 'check-status',
            label: 'Check Status',
            command: '/status',
            variant: 'primary',
          },
        ],
        dismissable: true,
      }
    }

    return null
  },
})

// Signal Added Triggers
registerTrigger({
  id: 'signal-added-prompt',
  type: 'signal_added',
  cooldownMs: 5000, // 5 seconds
  handler: async (_context): Promise<ProactiveMessage | null> => {
    return {
      message: '📥 Processing your transcript now... Extracting features, personas, and business drivers. This may take 1-2 minutes.',
      priority: 'high',
      actions: [
        {
          id: 'view-sources',
          label: 'View Sources Tab',
          navigateTo: { tab: 'sources' },
        },
      ],
      dismissable: true,
      expiresAt: new Date(Date.now() + 120000), // Expires in 2 minutes
    }
  },
})

// Signal Processing Complete Trigger
registerTrigger({
  id: 'signal-processing-complete',
  type: 'signal_processed',
  cooldownMs: 2000, // 2 seconds
  handler: async (context): Promise<ProactiveMessage | null> => {
    const { signalResult, projectId } = context

    if (!signalResult) return null

    const changesCount = signalResult.changesCount || 0
    const proposalId = signalResult.proposalId

    let message = `✅ **Analysis Complete!**\n\n`
    message += `Extracted **${changesCount} changes** from your transcript.\n\n`

    const actions: QuickAction[] = []

    if (proposalId && changesCount > 0) {
      message += `📋 **${changesCount} tasks** have been created for your review.\n\n`
      message += `You can approve them all at once or review individually.`

      actions.push({
        id: 'approve-all',
        label: 'Approve All',
        command: '/approve-all-tasks',
        variant: 'primary',
      })
      actions.push({
        id: 'view-tasks',
        label: 'Review Tasks',
        command: '/tasks proposals',
      })
    } else if (changesCount > 0) {
      message += `Changes have been automatically applied to your project.`
      actions.push({
        id: 'view-changes',
        label: 'View Changes',
        command: '/project-status',
      })
    }

    actions.push({
      id: 'view-overview',
      label: 'View Overview',
      navigateTo: { tab: 'overview' },
    })

    return {
      message,
      priority: 'high',
      actions,
      dismissable: true,
    }
  },
})

// =============================================================================
// Trigger Evaluation
// =============================================================================

/**
 * Evaluate all triggers of a specific type against the current context.
 * Returns the first matching proactive message, or null if none match.
 */
export async function evaluateTriggers(
  type: ProactiveTrigger['type'],
  context: AssistantContext
): Promise<ProactiveMessage | null> {
  const relevantTriggers = getTriggersByType(type)
  const now = Date.now()

  for (const trigger of relevantTriggers) {
    // Check cooldown
    if (trigger.lastTriggered && trigger.cooldownMs) {
      const elapsed = now - trigger.lastTriggered.getTime()
      if (elapsed < trigger.cooldownMs) {
        continue
      }
    }

    // Check condition
    if (trigger.condition && !trigger.condition(context)) {
      continue
    }

    // Execute handler
    try {
      const message = await trigger.handler(context)
      if (message) {
        // Update last triggered
        trigger.lastTriggered = new Date()
        return message
      }
    } catch (error) {
      console.error(`Trigger ${trigger.id} failed:`, error)
    }
  }

  return null
}

/**
 * Evaluate all trigger types and return all matching messages.
 */
export async function evaluateAllTriggers(
  context: AssistantContext
): Promise<ProactiveMessage[]> {
  const messages: ProactiveMessage[] = []
  const types: ProactiveTrigger['type'][] = [
    'tab_switch',
    'entity_selected',
    'idle',
    'periodic',
    'signal_added',
    'signal_processed',
  ]

  for (const type of types) {
    const message = await evaluateTriggers(type, context)
    if (message) {
      messages.push(message)
    }
  }

  return messages
}

// =============================================================================
// Proactive Message Utilities
// =============================================================================

/**
 * Check if a proactive message has expired.
 */
export function isMessageExpired(message: ProactiveMessage): boolean {
  if (!message.expiresAt) return false
  return new Date() > message.expiresAt
}

/**
 * Filter out expired messages from a list.
 */
export function filterExpiredMessages(messages: ProactiveMessage[]): ProactiveMessage[] {
  return messages.filter((m) => !isMessageExpired(m))
}

/**
 * Sort messages by priority (high first).
 */
export function sortByPriority(messages: ProactiveMessage[]): ProactiveMessage[] {
  const priorityOrder = { high: 0, medium: 1, low: 2 }
  return [...messages].sort(
    (a, b) => priorityOrder[a.priority] - priorityOrder[b.priority]
  )
}

/**
 * Get the highest priority message from a list.
 */
export function getHighestPriorityMessage(
  messages: ProactiveMessage[]
): ProactiveMessage | null {
  const valid = filterExpiredMessages(messages)
  if (valid.length === 0) return null
  return sortByPriority(valid)[0]
}

// =============================================================================
// Event Handlers for Integration
// =============================================================================

/**
 * Handler to call when a tab changes.
 */
export async function onTabChange(
  context: AssistantContext
): Promise<ProactiveMessage | null> {
  return evaluateTriggers('tab_switch', context)
}

/**
 * Handler to call when an entity is selected.
 */
export async function onEntitySelected(
  context: AssistantContext
): Promise<ProactiveMessage | null> {
  return evaluateTriggers('entity_selected', context)
}

/**
 * Handler to call when a new signal is added.
 */
export async function onSignalAdded(
  context: AssistantContext
): Promise<ProactiveMessage | null> {
  return evaluateTriggers('signal_added', context)
}

/**
 * Handler to call when signal processing completes.
 */
export async function onSignalProcessed(
  context: AssistantContext
): Promise<ProactiveMessage | null> {
  return evaluateTriggers('signal_processed', context)
}

/**
 * Handler to call on idle timeout.
 */
export async function onIdle(
  context: AssistantContext
): Promise<ProactiveMessage | null> {
  return evaluateTriggers('idle', context)
}

/**
 * Handler for periodic checks.
 */
export async function onPeriodicCheck(
  context: AssistantContext
): Promise<ProactiveMessage | null> {
  return evaluateTriggers('periodic', context)
}
