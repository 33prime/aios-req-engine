/**
 * AI Assistant Command Center - Commands
 *
 * Slash command definitions and handlers for the AI assistant.
 * Each command is context-aware and can access project data.
 */

import type {
  CommandDefinition,
  CommandArgs,
  CommandResult,
  AssistantContext,
  QuickAction,
} from './types'

// =============================================================================
// Command Registry
// =============================================================================

const commands: Map<string, CommandDefinition> = new Map()

/**
 * Register a command in the registry.
 */
export function registerCommand(command: CommandDefinition): void {
  commands.set(command.name, command)
  command.aliases?.forEach((alias) => {
    commands.set(alias, command)
  })
}

/**
 * Get a command by name or alias.
 */
export function getCommand(name: string): CommandDefinition | undefined {
  return commands.get(name.toLowerCase())
}

/**
 * Get all registered commands (unique, no aliases).
 */
export function getAllCommands(): CommandDefinition[] {
  const seen = new Set<string>()
  const result: CommandDefinition[] = []

  commands.forEach((cmd) => {
    if (!seen.has(cmd.name)) {
      seen.add(cmd.name)
      result.push(cmd)
    }
  })

  return result
}

/**
 * Find commands matching a partial input.
 */
export function findMatchingCommands(input: string): CommandDefinition[] {
  const normalizedInput = input.toLowerCase().replace(/^\//, '')
  return getAllCommands().filter(
    (cmd) =>
      cmd.name.startsWith(normalizedInput) ||
      cmd.aliases?.some((alias) => alias.startsWith(normalizedInput))
  )
}

// =============================================================================
// Command Definitions
// =============================================================================

// /status - Project health overview
registerCommand({
  name: 'status',
  description: 'Show project health, blockers, and recommendations',
  aliases: ['health', 'overview'],
  examples: ['/status', '/health'],
  execute: async (_args, context): Promise<CommandResult> => {
    const { projectData } = context

    if (!projectData) {
      return {
        success: false,
        message: 'No project data available. Please select a project first.',
      }
    }

    const readiness = projectData.readinessScore ?? 0
    const blockers = projectData.blockers ?? []
    const warnings = projectData.warnings ?? []
    const pending = projectData.pendingConfirmations ?? 0

    let message = `## Project Status\n\n`
    message += `**Readiness Score:** ${readiness}/100\n\n`

    if (projectData.stats) {
      message += `### Stats\n`
      message += `- Features: ${projectData.stats.features}\n`
      message += `- Personas: ${projectData.stats.personas}\n`
      message += `- Value Path Steps: ${projectData.stats.vpSteps}\n`
      message += `- Signals: ${projectData.stats.signals}\n\n`
    }

    if (blockers.length > 0) {
      message += `### 🚫 Blockers (${blockers.length})\n`
      blockers.forEach((b) => {
        message += `- ${b}\n`
      })
      message += '\n'
    }

    if (warnings.length > 0) {
      message += `### ⚠️ Warnings (${warnings.length})\n`
      warnings.forEach((w) => {
        message += `- ${w}\n`
      })
      message += '\n'
    }

    if (pending > 0) {
      message += `### ⏳ Pending Confirmations: ${pending}\n`
    }

    const actions: QuickAction[] = []
    if (pending > 0) {
      actions.push({
        id: 'review-pending',
        label: 'Review Pending',
        command: '/review',
        variant: 'primary',
      })
    }
    if (blockers.length > 0) {
      actions.push({
        id: 'address-blockers',
        label: 'Address Blockers',
        command: '/blockers',
      })
    }

    return {
      success: true,
      message,
      actions,
    }
  },
})

// /briefing - Pre-meeting prep
registerCommand({
  name: 'briefing',
  description: 'Generate a pre-meeting briefing with key discussion points',
  aliases: ['prep', 'meeting'],
  args: [
    {
      name: 'type',
      type: 'string',
      required: false,
      description: 'Meeting type: client, internal, review',
    },
  ],
  examples: ['/briefing', '/briefing client', '/prep internal'],
  execute: async (args, context): Promise<CommandResult> => {
    const meetingType = (args.type as string) || 'general'
    const { projectData } = context

    if (!projectData) {
      return {
        success: false,
        message: 'No project data available.',
      }
    }

    let message = `## ${meetingType.charAt(0).toUpperCase() + meetingType.slice(1)} Meeting Briefing\n\n`

    message += `### Quick Stats\n`
    message += `- Readiness: ${projectData.readinessScore ?? 0}/100\n`
    message += `- Pending Confirmations: ${projectData.pendingConfirmations ?? 0}\n\n`

    if (meetingType === 'client') {
      message += `### Discussion Points\n`
      message += `1. Review any items needing client confirmation\n`
      message += `2. Validate key personas and their priorities\n`
      message += `3. Discuss feature acceptance criteria\n\n`
    } else if (meetingType === 'internal') {
      message += `### Internal Focus Areas\n`
      message += `1. Review AI-generated content accuracy\n`
      message += `2. Address any blockers\n`
      message += `3. Plan enrichment priorities\n\n`
    }

    if ((projectData.blockers?.length ?? 0) > 0) {
      message += `### Blockers to Address\n`
      projectData.blockers?.forEach((b) => {
        message += `- ${b}\n`
      })
    }

    return {
      success: true,
      message,
      actions: [
        {
          id: 'export-briefing',
          label: 'Export Briefing',
          icon: 'download',
        },
      ],
    }
  },
})

// /analyze - Analyze selected entity
registerCommand({
  name: 'analyze',
  description: 'Analyze the selected entity for gaps and improvements',
  aliases: ['check', 'inspect'],
  examples: ['/analyze', '/check'],
  execute: async (_args, context): Promise<CommandResult> => {
    const { selectedEntity } = context

    if (!selectedEntity) {
      return {
        success: false,
        message:
          'No entity selected. Please select a feature, persona, or VP step to analyze.',
        actions: [
          {
            id: 'go-features',
            label: 'Go to Features',
            navigateTo: { tab: 'features' },
          },
          {
            id: 'go-personas',
            label: 'Go to Personas',
            navigateTo: { tab: 'personas' },
          },
        ],
      }
    }

    let message = `## Analysis: ${selectedEntity.name}\n\n`
    message += `**Type:** ${selectedEntity.type}\n`
    message += `**Status:** ${selectedEntity.status ?? 'Unknown'}\n\n`

    // Generate analysis based on entity type
    switch (selectedEntity.type) {
      case 'feature':
        message += `### Feature Analysis\n`
        message += `- Check acceptance criteria completeness\n`
        message += `- Verify persona alignment\n`
        message += `- Review related signals\n`
        break
      case 'persona':
        message += `### Persona Analysis\n`
        message += `- Verify pain points are documented\n`
        message += `- Check feature coverage\n`
        message += `- Review evidence from signals\n`
        break
      case 'vp_step':
        message += `### Value Path Step Analysis\n`
        message += `- Verify step connections\n`
        message += `- Check supporting features\n`
        message += `- Review measurable outcomes\n`
        break
    }

    return {
      success: true,
      message,
      actions: [
        {
          id: 'enrich-entity',
          label: 'Enrich',
          command: '/enrich',
          variant: 'primary',
        },
        {
          id: 'view-history',
          label: 'View History',
          command: '/history',
        },
      ],
    }
  },
})

// /enrich - Trigger enrichment
registerCommand({
  name: 'enrich',
  description: 'Trigger AI enrichment for the selected entity',
  aliases: ['enhance', 'improve'],
  args: [
    {
      name: 'target',
      type: 'entity',
      required: false,
      description: 'Entity to enrich (defaults to selected)',
    },
  ],
  examples: ['/enrich', '/enrich feature:123'],
  execute: async (_args, context): Promise<CommandResult> => {
    const { selectedEntity } = context

    if (!selectedEntity) {
      return {
        success: false,
        message: 'No entity selected to enrich.',
      }
    }

    // In a real implementation, this would call the enrichment API
    return {
      success: true,
      message: `Enrichment queued for ${selectedEntity.type} "${selectedEntity.name}".\n\nThe AI will analyze signals and research to enhance this entity.`,
      data: {
        entityId: selectedEntity.id,
        entityType: selectedEntity.type,
        status: 'queued',
      },
    }
  },
})

// /add - Add new entity
registerCommand({
  name: 'add',
  description: 'Add a new feature, persona, or value path step',
  aliases: ['create', 'new'],
  args: [
    {
      name: 'type',
      type: 'string',
      required: true,
      description: 'Entity type: feature, persona, vp_step',
    },
    {
      name: 'name',
      type: 'string',
      required: true,
      description: 'Name of the new entity',
    },
  ],
  examples: [
    '/add feature User Authentication',
    '/add persona Power User',
    '/create vp_step Onboarding',
  ],
  execute: async (args, context): Promise<CommandResult> => {
    const entityType = args.type as string
    const name = args.name as string

    if (!entityType || !name) {
      return {
        success: false,
        message:
          'Please specify both type and name.\n\nUsage: `/add <type> <name>`\n\nExample: `/add feature User Dashboard`',
      }
    }

    const validTypes = ['feature', 'persona', 'vp_step']
    if (!validTypes.includes(entityType)) {
      return {
        success: false,
        message: `Invalid entity type "${entityType}".\n\nValid types: ${validTypes.join(', ')}`,
      }
    }

    // In a real implementation, this would call the create API
    return {
      success: true,
      message: `Created new ${entityType}: "${name}"\n\nThe entity has been added with status "ai_generated" and will need confirmation.`,
      data: {
        entityType,
        name,
        status: 'ai_generated',
      },
      navigateTo: {
        tab: entityType === 'feature' ? 'features' : entityType === 'persona' ? 'personas' : 'value-path',
      },
    }
  },
})

// /confirm - Confirm entities
registerCommand({
  name: 'confirm',
  description: 'Confirm the selected entity or all pending',
  aliases: ['approve', 'validate'],
  args: [
    {
      name: 'level',
      type: 'string',
      required: false,
      description: 'Confirmation level: consultant, client',
    },
  ],
  examples: ['/confirm', '/confirm consultant', '/confirm client'],
  execute: async (args, context): Promise<CommandResult> => {
    const { selectedEntity } = context
    const level = (args.level as string) || 'consultant'

    if (!selectedEntity) {
      return {
        success: false,
        message: 'No entity selected to confirm.',
        actions: [
          {
            id: 'review-all',
            label: 'Review All Pending',
            command: '/review',
          },
        ],
      }
    }

    const validLevels = ['consultant', 'client']
    if (!validLevels.includes(level)) {
      return {
        success: false,
        message: `Invalid confirmation level "${level}".\n\nValid levels: ${validLevels.join(', ')}`,
      }
    }

    return {
      success: true,
      message: `Confirmed ${selectedEntity.type} "${selectedEntity.name}" at ${level} level.\n\nThis entity will now be used in PRD generation and can trigger enrichment cascades.`,
      data: {
        entityId: selectedEntity.id,
        entityType: selectedEntity.type,
        confirmationStatus: `confirmed_${level}`,
      },
    }
  },
})

// /review - Review pending items
registerCommand({
  name: 'review',
  description: 'Review all items pending confirmation',
  aliases: ['pending'],
  args: [
    {
      name: 'type',
      type: 'string',
      required: false,
      description: 'Filter by type: feature, persona, vp_step',
    },
  ],
  examples: ['/review', '/review feature', '/pending persona'],
  execute: async (args, context): Promise<CommandResult> => {
    const filterType = args.type as string | undefined
    const { projectData } = context

    const pending = projectData?.pendingConfirmations ?? 0

    if (pending === 0) {
      return {
        success: true,
        message: '✓ No items pending confirmation!\n\nAll entities have been reviewed.',
      }
    }

    let message = `## Pending Review\n\n`
    message += `**${pending} items** need confirmation.\n\n`

    if (filterType) {
      message += `Filtered by: ${filterType}\n\n`
    }

    message += `### Review Options\n`
    message += `1. Click on each item to review and confirm\n`
    message += `2. Use \`/confirm consultant\` or \`/confirm client\` to set confirmation level\n`
    message += `3. Use bulk actions to confirm multiple items\n`

    return {
      success: true,
      message,
      actions: [
        {
          id: 'bulk-confirm',
          label: 'Bulk Confirm',
          variant: 'primary',
        },
        {
          id: 'export-pending',
          label: 'Export List',
        },
      ],
      navigateTo: filterType
        ? {
            tab:
              filterType === 'feature'
                ? 'features'
                : filterType === 'persona'
                  ? 'personas'
                  : 'value-path',
          }
        : undefined,
    }
  },
})

// /history - View entity history
registerCommand({
  name: 'history',
  description: 'View version history for the selected entity',
  aliases: ['versions', 'changelog'],
  examples: ['/history', '/versions'],
  execute: async (_args, context): Promise<CommandResult> => {
    const { selectedEntity } = context

    if (!selectedEntity) {
      return {
        success: false,
        message: 'No entity selected. Please select an entity to view its history.',
      }
    }

    // In real implementation, would fetch from entity_versioning API
    return {
      success: true,
      message: `## History: ${selectedEntity.name}\n\n*Loading version history...*\n\nThis will show all changes made to this entity, including:\n- Who made each change\n- What fields were modified\n- Source signals that contributed`,
      data: {
        entityId: selectedEntity.id,
        entityType: selectedEntity.type,
      },
    }
  },
})

// /surgical - Apply surgical update
registerCommand({
  name: 'surgical',
  description: 'Apply a targeted update to a specific field',
  aliases: ['update', 'edit'],
  args: [
    {
      name: 'field',
      type: 'string',
      required: true,
      description: 'Field to update',
    },
    {
      name: 'value',
      type: 'string',
      required: true,
      description: 'New value',
    },
  ],
  examples: ['/surgical description "New description"', '/update name "Better Name"'],
  execute: async (args, context): Promise<CommandResult> => {
    const { selectedEntity } = context
    const field = args.field as string
    const value = args.value as string

    if (!selectedEntity) {
      return {
        success: false,
        message: 'No entity selected to update.',
      }
    }

    if (!field || !value) {
      return {
        success: false,
        message: 'Please specify both field and value.\n\nUsage: `/surgical <field> "<value>"`',
      }
    }

    return {
      success: true,
      message: `Updated ${selectedEntity.type} "${selectedEntity.name}":\n\n**${field}** → "${value}"\n\nA new version has been created with this change.`,
      data: {
        entityId: selectedEntity.id,
        entityType: selectedEntity.type,
        field,
        newValue: value,
      },
    }
  },
})

// /help - Show available commands
registerCommand({
  name: 'help',
  description: 'Show available commands and usage',
  aliases: ['?', 'commands'],
  args: [
    {
      name: 'command',
      type: 'string',
      required: false,
      description: 'Get help for a specific command',
    },
  ],
  examples: ['/help', '/help status', '/? enrich'],
  execute: async (args): Promise<CommandResult> => {
    const cmdName = args.command as string | undefined

    if (cmdName) {
      const cmd = getCommand(cmdName)
      if (!cmd) {
        return {
          success: false,
          message: `Unknown command: ${cmdName}\n\nUse \`/help\` to see all available commands.`,
        }
      }

      let message = `## /${cmd.name}\n\n`
      message += `${cmd.description}\n\n`

      if (cmd.aliases?.length) {
        message += `**Aliases:** ${cmd.aliases.map((a) => `/${a}`).join(', ')}\n\n`
      }

      if (cmd.args?.length) {
        message += `**Arguments:**\n`
        cmd.args.forEach((arg) => {
          message += `- \`${arg.name}\` (${arg.type}${arg.required ? ', required' : ''}): ${arg.description}\n`
        })
        message += '\n'
      }

      if (cmd.examples?.length) {
        message += `**Examples:**\n`
        cmd.examples.forEach((ex) => {
          message += `- \`${ex}\`\n`
        })
      }

      return { success: true, message }
    }

    // Show all commands
    let message = `## Available Commands\n\n`

    const allCommands = getAllCommands()
    allCommands.forEach((cmd) => {
      message += `**/${cmd.name}** - ${cmd.description}\n`
    })

    message += `\n*Type \`/help <command>\` for detailed usage.*`

    return { success: true, message }
  },
})

// /clear - Clear conversation
registerCommand({
  name: 'clear',
  description: 'Clear the conversation history',
  aliases: ['reset'],
  examples: ['/clear', '/reset'],
  execute: async (): Promise<CommandResult> => {
    return {
      success: true,
      message: 'Conversation cleared.',
      data: { action: 'clear_messages' },
    }
  },
})

// =============================================================================
// Command Parsing
// =============================================================================

/**
 * Check if input is a command.
 */
export function isCommand(input: string): boolean {
  return input.trim().startsWith('/')
}

/**
 * Parse command input into name and arguments.
 */
export function parseCommand(input: string): {
  name: string
  args: CommandArgs
  rawArgs: string
} {
  const trimmed = input.trim()

  if (!trimmed.startsWith('/')) {
    return { name: '', args: {}, rawArgs: '' }
  }

  // Remove leading slash
  const withoutSlash = trimmed.slice(1)

  // Split into command name and rest
  const spaceIndex = withoutSlash.indexOf(' ')

  if (spaceIndex === -1) {
    return {
      name: withoutSlash.toLowerCase(),
      args: {},
      rawArgs: '',
    }
  }

  const name = withoutSlash.slice(0, spaceIndex).toLowerCase()
  const rawArgs = withoutSlash.slice(spaceIndex + 1).trim()

  // Parse arguments based on command definition
  const command = getCommand(name)
  const args: CommandArgs = {}

  if (command?.args) {
    // Simple parsing: split by spaces, respecting quotes
    const tokens = parseTokens(rawArgs)

    command.args.forEach((argDef, index) => {
      if (index < tokens.length) {
        args[argDef.name] = tokens[index]
      }
    })
  } else {
    // No defined args, put everything in 'input'
    args.input = rawArgs
  }

  return { name, args, rawArgs }
}

/**
 * Parse a string into tokens, respecting quoted strings.
 */
function parseTokens(input: string): string[] {
  const tokens: string[] = []
  let current = ''
  let inQuotes = false
  let quoteChar = ''

  for (const char of input) {
    if ((char === '"' || char === "'") && !inQuotes) {
      inQuotes = true
      quoteChar = char
    } else if (char === quoteChar && inQuotes) {
      inQuotes = false
      quoteChar = ''
    } else if (char === ' ' && !inQuotes) {
      if (current) {
        tokens.push(current)
        current = ''
      }
    } else {
      current += char
    }
  }

  if (current) {
    tokens.push(current)
  }

  return tokens
}

/**
 * Execute a parsed command.
 */
export async function executeCommand(
  name: string,
  args: CommandArgs,
  context: AssistantContext
): Promise<CommandResult> {
  const command = getCommand(name)

  if (!command) {
    const suggestions = findMatchingCommands(name)
    let message = `Unknown command: /${name}`

    if (suggestions.length > 0) {
      message += `\n\nDid you mean?\n`
      suggestions.slice(0, 3).forEach((cmd) => {
        message += `- /${cmd.name}\n`
      })
    }

    return {
      success: false,
      message,
    }
  }

  try {
    return await command.execute(args, context)
  } catch (error) {
    return {
      success: false,
      message: `Command failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
    }
  }
}

// =============================================================================
// Exports
// =============================================================================

export { commands }
