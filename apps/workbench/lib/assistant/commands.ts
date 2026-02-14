/**
 * AI Assistant Command Center - Commands
 *
 * Slash command definitions and handlers for the AI assistant.
 * Each command is context-aware and can access project data.
 *
 * Commands are named descriptively so users don't have to guess what they do.
 */

import type {
  CommandDefinition,
  CommandArgs,
  CommandResult,
  AssistantContext,
  QuickAction,
} from './types'
import { API_BASE } from '../config'

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
// RUN COMMANDS - Trigger AI Agents
// =============================================================================

// /run-foundation - Strategic foundation enrichment
registerCommand({
  name: 'run-foundation',
  description: 'Extract company info, business drivers, and competitors from signals',
  aliases: ['foundation', 'strategic'],
  examples: ['/run-foundation'],
  execute: async (_args, context): Promise<CommandResult> => {
    const { projectId } = context

    if (!projectId) {
      return {
        success: false,
        message: 'No project selected. Please select a project first.',
      }
    }

    const { runStrategicFoundation } = await import('@/lib/api')

    try {
      const result = await runStrategicFoundation(projectId)

      return {
        success: true,
        message: `**Strategic Foundation running...**\n\nExtracting company info, business drivers, and competitors from your signals. This usually takes 1-2 minutes.\n\nRefresh the tab when complete to see results.`,
        data: {
          jobId: result.job_id,
          action: 'strategic_foundation_started',
        },
      }
    } catch (error) {
      return {
        success: false,
        message: `Failed to start: ${error instanceof Error ? error.message : 'Unknown error'}`,
      }
    }
  },
})

// /run-research - Trigger n8n research workflow
registerCommand({
  name: 'run-research',
  description: 'Run AI research on company, competitors, and market',
  aliases: ['research'],
  args: [
    {
      name: 'focus',
      type: 'string',
      required: false,
      description: 'Optional focus area for research (e.g., "competitor pricing")',
    },
  ],
  examples: ['/run-research', '/run-research "competitor analysis"'],
  execute: async (args, context): Promise<CommandResult> => {
    const { projectId, projectData } = context
    const focus = args.focus as string | undefined

    if (!projectId) {
      return {
        success: false,
        message: 'No project selected. Please select a project first.',
      }
    }

    const { triggerN8nResearch } = await import('@/lib/api')

    try {
      const focusAreas = focus ? [focus] : []
      const result = await triggerN8nResearch(projectId, focusAreas)

      const projectName = projectData?.name || 'your project'

      let message = `## 🔬 Research Started\n\n`
      message += `Analyzing **${projectName}** across multiple dimensions:\n\n`
      message += `- Market size and growth trends\n`
      message += `- Competitor landscape and positioning\n`
      message += `- Industry pain points and opportunities\n`
      message += `- Feature benchmarking\n`
      message += `- User personas and segments\n`
      if (focus) {
        message += `\n**Special Focus:** ${focus}\n`
      }
      message += `\n---\n`
      message += `⏱️ This typically takes 2-3 minutes.\n\n`
      message += `📬 You'll receive a notification when complete, and results will appear in the **Sources tab**.\n\n`
      message += `💡 *Tip: Once research completes, run \`/run-foundation\` to extract strategic insights.*`

      return {
        success: true,
        message,
        data: {
          jobId: result.job_id,
          action: 'research_started',
        },
      }
    } catch (error) {
      return {
        success: false,
        message: `Failed to start research: ${error instanceof Error ? error.message : 'Unknown error'}`,
      }
    }
  },
})

// /discover - Run data-first discovery intelligence pipeline
registerCommand({
  name: 'discover',
  description: 'Run parallelized discovery: company intel, competitors, market data, user reviews, and business drivers',
  aliases: ['discovery'],
  args: [
    {
      name: 'focus',
      type: 'string',
      required: false,
      description: 'Optional focus areas (e.g., "competitor pricing")',
    },
  ],
  examples: ['/discover', '/discover "user pain points"'],
  execute: async (args, context): Promise<CommandResult> => {
    const { projectId, projectData } = context
    const focus = args.focus as string | undefined

    if (!projectId) {
      return {
        success: false,
        message: 'No project selected. Please select a project first.',
      }
    }

    const { runDiscovery } = await import('@/lib/api')

    try {
      const focusAreas = focus ? [focus] : []
      const result = await runDiscovery(projectId, { focus_areas: focusAreas })

      const projectName = projectData?.name || 'your project'

      let message = `## Discovery Pipeline Started\n\n`
      message += `Researching **${projectName}** with data-first intelligence:\n\n`
      message += `1. Source Mapping (SerpAPI)\n`
      message += `2. Company Intel (PDL + Firecrawl)\n`
      message += `3. Competitor Intel (PDL + Firecrawl)\n`
      message += `4. Market Evidence (Firecrawl)\n`
      message += `5. User Voice (Bright Data + Firecrawl)\n`
      message += `6. Feature Analysis\n`
      message += `7. Business Drivers (Sonnet synthesis)\n`
      message += `8. Persist & Link\n`
      if (focus) {
        message += `\n**Focus:** ${focus}\n`
      }
      message += `\n---\n`
      message += `Budget: ~$1.05 | Time: ~60-90s\n\n`
      message += `Run \`/discover-status\` to check progress.`

      return {
        success: true,
        message,
        data: {
          jobId: result.job_id,
          action: 'discovery_started',
        },
      }
    } catch (error) {
      return {
        success: false,
        message: `Failed to start discovery: ${error instanceof Error ? error.message : 'Unknown error'}`,
      }
    }
  },
})

// /discover-status - Check on running discovery pipeline
registerCommand({
  name: 'discover-status',
  description: 'Check the status of the running discovery pipeline',
  aliases: ['check-discover'],
  examples: ['/discover-status'],
  execute: async (_args, context): Promise<CommandResult> => {
    const { projectId } = context

    if (!projectId) {
      return {
        success: false,
        message: 'No project selected. Please select a project first.',
      }
    }

    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null

    try {
      // Get recent discovery jobs
      const response = await fetch(`${API_BASE}/v1/jobs?project_id=${projectId}&job_type=discovery_pipeline&limit=1`, {
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      })

      if (!response.ok) {
        throw new Error('Failed to fetch discovery status')
      }

      const jobs = await response.json()
      if (!jobs || jobs.length === 0) {
        return {
          success: true,
          message: 'No discovery pipeline runs found. Run `/discover` to start one.',
        }
      }

      const job = jobs[0]
      const { getDiscoveryProgress } = await import('@/lib/api')
      const progress = await getDiscoveryProgress(projectId, job.id)

      const statusIcons: Record<string, string> = {
        completed: 'Done',
        running: 'Running...',
        failed: 'Failed',
        skipped: 'Skipped',
        pending: 'Pending',
      }

      let message = `## Discovery Pipeline Status\n\n`
      for (const phase of progress.phases) {
        const icon = statusIcons[phase.status] || phase.status
        const summary = phase.summary ? ` — ${phase.summary}` : ''
        const duration = phase.duration_seconds ? ` (${phase.duration_seconds.toFixed(1)}s)` : ''
        message += `- **${icon}** ${phase.phase}${summary}${duration}\n`
      }
      message += `\n---\n`
      message += `Cost: $${progress.cost_so_far_usd.toFixed(2)} | Elapsed: ${progress.elapsed_seconds.toFixed(0)}s`

      if (progress.status === 'completed') {
        message += `\n\nPipeline complete!`
        if (progress.drivers_count) {
          message += ` ${progress.drivers_count} business drivers created.`
        }
        if (progress.competitors_count) {
          message += ` ${progress.competitors_count} competitors profiled.`
        }
      }

      return {
        success: true,
        message,
        data: { jobId: job.id, status: progress.status },
      }
    } catch (error) {
      return {
        success: false,
        message: `Failed to check discovery status: ${error instanceof Error ? error.message : 'Unknown error'}`,
      }
    }
  },
})

// /research-status - Check on running research
registerCommand({
  name: 'research-status',
  description: 'Check the status of running research',
  aliases: ['check-research'],
  examples: ['/research-status'],
  execute: async (_args, context): Promise<CommandResult> => {
    const { projectId } = context

    if (!projectId) {
      return {
        success: false,
        message: 'No project selected. Please select a project first.',
      }
    }


    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null

    try {
      // Get recent research jobs
      const response = await fetch(`${API_BASE}/v1/jobs?project_id=${projectId}&job_type=n8n_research&limit=5`, {
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      })

      if (!response.ok) {
        throw new Error('Failed to fetch research status')
      }

      const jobs = await response.json()

      if (!jobs || jobs.length === 0) {
        return {
          success: true,
          message: `## Research Status\n\nNo research jobs found for this project.\n\nRun \`/run-research\` to start AI research.`,
        }
      }

      let message = `## Research Status\n\n`

      for (const job of jobs.slice(0, 3)) {
        const status = job.status
        const icon = status === 'completed' ? '✅' : status === 'running' ? '🔄' : status === 'failed' ? '❌' : '⏸️'
        const date = new Date(job.created_at).toLocaleString()

        message += `${icon} **${status.toUpperCase()}** - ${date}\n`

        if (status === 'completed' && job.output_json) {
          const output = job.output_json
          message += `   Signal: \`${output.signal_id || 'N/A'}\`\n`
          message += `   Chunks: ${output.chunks_created || 0}\n`
        } else if (status === 'failed' && job.error_message) {
          message += `   Error: ${job.error_message.slice(0, 100)}\n`
        } else if (status === 'running') {
          message += `   Research in progress... check back shortly.\n`
        }
        message += '\n'
      }

      const latestJob = jobs[0]
      if (latestJob.status === 'completed') {
        message += `\n💡 Research complete! Check the **Sources tab** for results.`
      } else if (latestJob.status === 'running') {
        message += `\n⏳ Research is still running. This typically takes 2-3 minutes.`
      }

      return {
        success: true,
        message,
      }
    } catch (error) {
      return {
        success: false,
        message: `Failed to check research status: ${error instanceof Error ? error.message : 'Unknown error'}`,
      }
    }
  },
})

// /enrich-features - AI enhance all features
registerCommand({
  name: 'enrich-features',
  description: 'AI enhance ALL features with research and signal data',
  aliases: ['enhance-features'],
  examples: ['/enrich-features'],
  execute: async (_args, context): Promise<CommandResult> => {
    const { projectId } = context

    if (!projectId) {
      return {
        success: false,
        message: 'No project selected. Please select a project first.',
      }
    }

    const { enrichFeatures } = await import('@/lib/api')

    try {
      const result = await enrichFeatures(projectId, { includeResearch: true })

      return {
        success: true,
        message: `**Enriching features...**\n\nEnhancing all features with research findings, signal evidence, and acceptance criteria.\n\nThis may take a few minutes.`,
        data: {
          jobId: result.job_id,
          action: 'enrich_features_started',
        },
      }
    } catch (error) {
      return {
        success: false,
        message: `Failed to start feature enrichment: ${error instanceof Error ? error.message : 'Unknown error'}`,
      }
    }
  },
})

// /enrich-personas - AI enhance all personas
registerCommand({
  name: 'enrich-personas',
  description: 'AI enhance ALL personas with research and signal data',
  aliases: ['enhance-personas'],
  examples: ['/enrich-personas'],
  execute: async (_args, context): Promise<CommandResult> => {
    const { projectId } = context

    if (!projectId) {
      return {
        success: false,
        message: 'No project selected. Please select a project first.',
      }
    }

    const { enrichPersonas } = await import('@/lib/api')

    try {
      const result = await enrichPersonas(projectId, { includeResearch: true })

      return {
        success: true,
        message: `**Enriching personas...**\n\nEnhancing all personas with:\n- Detailed overviews and background\n- Key workflows mapped to features\n- Goals and motivations\n- Evidence from signals\n\nThis may take a few minutes.`,
        data: {
          jobId: result.job_id,
          action: 'enrich_personas_started',
        },
      }
    } catch (error) {
      return {
        success: false,
        message: `Failed to start persona enrichment: ${error instanceof Error ? error.message : 'Unknown error'}`,
      }
    }
  },
})

// /enrich-value-path - AI enhance all VP steps
registerCommand({
  name: 'enrich-value-path',
  description: 'AI enhance ALL value path steps with research and signals',
  aliases: ['enrich-vp', 'enhance-vp'],
  examples: ['/enrich-value-path'],
  execute: async (_args, context): Promise<CommandResult> => {
    const { projectId } = context

    if (!projectId) {
      return {
        success: false,
        message: 'No project selected. Please select a project first.',
      }
    }

    const { enrichVp } = await import('@/lib/api')

    try {
      const result = await enrichVp(projectId, true)

      return {
        success: true,
        message: `**Enriching value path...**\n\nEnhancing all journey steps with details, emotional mapping, and success metrics.\n\nThis may take a few minutes.`,
        data: {
          jobId: result.job_id,
          action: 'enrich_vp_started',
        },
      }
    } catch (error) {
      return {
        success: false,
        message: `Failed to start value path enrichment: ${error instanceof Error ? error.message : 'Unknown error'}`,
      }
    }
  },
})

// /enrich-kpis - AI enhance all KPIs
registerCommand({
  name: 'enrich-kpis',
  description: 'AI enhance ALL KPIs with measurement details and baselines',
  aliases: ['enhance-kpis'],
  examples: ['/enrich-kpis'],
  execute: async (_args, context): Promise<CommandResult> => {
    const { projectId } = context

    if (!projectId) {
      return {
        success: false,
        message: 'No project selected. Please select a project first.',
      }
    }


    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null

    try {
      const response = await fetch(`${API_BASE}/v1/projects/${projectId}/business-drivers/enrich-bulk?driver_type=kpi&depth=standard`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      })

      if (!response.ok) {
        throw new Error(`Failed to enrich KPIs: ${response.statusText}`)
      }

      const result = await response.json()

      return {
        success: true,
        message: `**KPI Enrichment Complete**\n\n✓ Enriched ${result.succeeded} KPI${result.succeeded !== 1 ? 's' : ''}\n${result.failed > 0 ? `✗ Failed ${result.failed}\n` : ''}\n\nKPIs now include:\n- Baseline and target values\n- Measurement methods\n- Data sources\n- Responsible teams\n\nRefresh the Strategic Foundation tab to see updates.`,
        data: {
          action: 'kpis_enriched',
          result,
          refresh_project: true,
        },
      }
    } catch (error) {
      return {
        success: false,
        message: `Failed to enrich KPIs: ${error instanceof Error ? error.message : 'Unknown error'}`,
      }
    }
  },
})

// /enrich-pain-points - AI enhance all pain points
registerCommand({
  name: 'enrich-pain-points',
  description: 'AI enhance ALL pain points with severity, impact, and workarounds',
  aliases: ['enhance-pains', 'enrich-pains'],
  examples: ['/enrich-pain-points'],
  execute: async (_args, context): Promise<CommandResult> => {
    const { projectId } = context

    if (!projectId) {
      return {
        success: false,
        message: 'No project selected. Please select a project first.',
      }
    }


    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null

    try {
      const response = await fetch(`${API_BASE}/v1/projects/${projectId}/business-drivers/enrich-bulk?driver_type=pain&depth=standard`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      })

      if (!response.ok) {
        throw new Error(`Failed to enrich pain points: ${response.statusText}`)
      }

      const result = await response.json()

      return {
        success: true,
        message: `**Pain Point Enrichment Complete**\n\n✓ Enriched ${result.succeeded} pain point${result.succeeded !== 1 ? 's' : ''}\n${result.failed > 0 ? `✗ Failed ${result.failed}\n` : ''}\n\nPain points now include:\n- Severity levels (critical/high/medium/low)\n- Frequency (constant/daily/weekly/monthly/rare)\n- Affected users\n- Business impact quantification\n- Current workarounds\n\nRefresh the Strategic Foundation tab to see updates.`,
        data: {
          action: 'pains_enriched',
          result,
          refresh_project: true,
        },
      }
    } catch (error) {
      return {
        success: false,
        message: `Failed to enrich pain points: ${error instanceof Error ? error.message : 'Unknown error'}`,
      }
    }
  },
})

// /enrich-goals - AI enhance all goals
registerCommand({
  name: 'enrich-goals',
  description: 'AI enhance ALL goals with timeframes, criteria, and dependencies',
  aliases: ['enhance-goals'],
  examples: ['/enrich-goals'],
  execute: async (_args, context): Promise<CommandResult> => {
    const { projectId } = context

    if (!projectId) {
      return {
        success: false,
        message: 'No project selected. Please select a project first.',
      }
    }


    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null

    try {
      const response = await fetch(`${API_BASE}/v1/projects/${projectId}/business-drivers/enrich-bulk?driver_type=goal&depth=standard`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      })

      if (!response.ok) {
        throw new Error(`Failed to enrich goals: ${response.statusText}`)
      }

      const result = await response.json()

      return {
        success: true,
        message: `**Goal Enrichment Complete**\n\n✓ Enriched ${result.succeeded} goal${result.succeeded !== 1 ? 's' : ''}\n${result.failed > 0 ? `✗ Failed ${result.failed}\n` : ''}\n\nGoals now include:\n- Timeframes and deadlines\n- Success criteria\n- Dependencies and prerequisites\n- Responsible owners\n\nRefresh the Strategic Foundation tab to see updates.`,
        data: {
          action: 'goals_enriched',
          result,
          refresh_project: true,
        },
      }
    } catch (error) {
      return {
        success: false,
        message: `Failed to enrich goals: ${error instanceof Error ? error.message : 'Unknown error'}`,
      }
    }
  },
})

// /enrich-business-drivers - AI enhance all business drivers
registerCommand({
  name: 'enrich-business-drivers',
  description: 'AI enhance ALL business drivers (KPIs, pain points, and goals)',
  aliases: ['enhance-drivers', 'enrich-drivers'],
  examples: ['/enrich-business-drivers'],
  execute: async (_args, context): Promise<CommandResult> => {
    const { projectId } = context

    if (!projectId) {
      return {
        success: false,
        message: 'No project selected. Please select a project first.',
      }
    }


    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null

    try {
      const response = await fetch(`${API_BASE}/v1/projects/${projectId}/business-drivers/enrich-bulk?driver_type=all&depth=standard`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      })

      if (!response.ok) {
        throw new Error(`Failed to enrich business drivers: ${response.statusText}`)
      }

      const result = await response.json()

      return {
        success: true,
        message: `**Business Driver Enrichment Complete**\n\n✓ Enriched ${result.succeeded} driver${result.succeeded !== 1 ? 's' : ''}\n${result.failed > 0 ? `✗ Failed ${result.failed}\n` : ''}\n\nAll business drivers enriched with:\n- **KPIs:** Baselines, targets, measurement methods\n- **Pain Points:** Severity, impact, workarounds\n- **Goals:** Timeframes, success criteria, dependencies\n\nRefresh the Strategic Foundation tab to see updates.`,
        data: {
          action: 'all_drivers_enriched',
          result,
          refresh_project: true,
        },
      }
    } catch (error) {
      return {
        success: false,
        message: `Failed to enrich business drivers: ${error instanceof Error ? error.message : 'Unknown error'}`,
      }
    }
  },
})

// =============================================================================
// CREATE COMMANDS
// =============================================================================

// /create-stakeholder
registerCommand({
  name: 'create-stakeholder',
  description: 'Add a new stakeholder to the project',
  aliases: ['add-stakeholder'],
  args: [
    {
      name: 'name',
      type: 'string',
      required: true,
      description: 'Name of the stakeholder',
    },
  ],
  examples: ['/create-stakeholder "John Smith"', '/create-stakeholder "Jane Doe"'],
  execute: async (args, context): Promise<CommandResult> => {
    const { projectId } = context
    const name = args.name as string || args.input as string

    if (!projectId) {
      return {
        success: false,
        message: 'No project selected. Please select a project first.',
      }
    }

    if (!name) {
      return {
        success: false,
        message: 'Please provide a name for the stakeholder.\n\nUsage: `/create-stakeholder "Name"`\n\nExample: `/create-stakeholder "John Smith"`',
      }
    }


    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null

    try {
      const response = await fetch(`${API_BASE}/v1/state/stakeholders`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          project_id: projectId,
          name: name,
          confirmation_status: 'confirmed_consultant',
        }),
      })

      if (!response.ok) {
        throw new Error(`Failed to create stakeholder: ${response.statusText}`)
      }

      const stakeholder = await response.json()

      return {
        success: true,
        message: `## Stakeholder Created\n\n**${name}** has been added to the project.\n\nYou can now:\n- Add their role and contact info\n- Assign them to confirmations\n- Link them to topics they know about`,
        data: {
          stakeholderId: stakeholder.id,
          action: 'stakeholder_created',
        },
      }
    } catch (error) {
      return {
        success: false,
        message: `Failed to create stakeholder: ${error instanceof Error ? error.message : 'Unknown error'}`,
      }
    }
  },
})

// =============================================================================
// VIEW COMMANDS - Read-Only Information
// =============================================================================

// /project-status
registerCommand({
  name: 'project-status',
  description: 'Show comprehensive project status with all entities',
  aliases: ['status', 'health'],
  examples: ['/project-status', '/status'],
  execute: async (_args, context): Promise<CommandResult> => {
    const { projectId } = context

    if (!projectId) {
      return {
        success: false,
        message: 'No project selected. Please select a project first.',
      }
    }

    const { getProjectStatus } = await import('@/lib/api')

    try {
      const status = await getProjectStatus(projectId)

      // Build formatted output
      let message = `# ${status.project.name}\n\n`

      // Readiness score with visual indicator
      const score = status.readiness.score
      const scoreBar = '█'.repeat(Math.floor(score / 10)) + '░'.repeat(10 - Math.floor(score / 10))
      message += `**Readiness:** ${scoreBar} ${score}/100\n\n`

      // Company Info
      if (status.company) {
        message += `## Company\n`
        message += `**${status.company.name || 'Unknown'}**`
        const details = [status.company.industry, status.company.stage].filter(Boolean)
        if (details.length > 0) {
          message += ` (${details.join(' • ')})`
        }
        message += '\n'
        if (status.company.location) {
          message += `📍 ${status.company.location}\n`
        }
        if (status.company.unique_selling_point) {
          message += `\n> ${status.company.unique_selling_point.slice(0, 150)}...\n`
        }
        message += '\n'
      }

      // Strategic Context
      message += `## Strategic Context\n`
      message += `*${status.strategic.total_drivers} business drivers (${status.strategic.confirmed_drivers} confirmed)*\n\n`

      if (status.strategic.pains.length > 0) {
        message += `**Pain Points (${status.strategic.pains.length})**\n`
        status.strategic.pains.slice(0, 3).forEach((p) => {
          const tag = p.status === 'confirmed' ? ' ✓' : ''
          message += `- ${p.description}${tag}\n`
        })
        message += '\n'
      }

      if (status.strategic.goals.length > 0) {
        message += `**Goals (${status.strategic.goals.length})**\n`
        status.strategic.goals.slice(0, 3).forEach((g) => {
          const tag = g.status === 'confirmed' ? ' ✓' : ''
          message += `- ${g.description}${tag}\n`
        })
        message += '\n'
      }

      if (status.strategic.kpis.length > 0) {
        message += `**Success Metrics (${status.strategic.kpis.length})**\n`
        status.strategic.kpis.slice(0, 3).forEach((k) => {
          const tag = k.status === 'confirmed' ? ' ✓' : ''
          const target = k.measurement ? ` → ${k.measurement}` : ''
          message += `- ${k.description}${target}${tag}\n`
        })
        message += '\n'
      }

      // Product State
      message += `## Product Definition\n`

      // Features
      const f = status.product.features
      message += `**Features:** ${f.total} total, ${f.mvp} MVP, ${f.confirmed} confirmed\n`
      if (f.items.length > 0) {
        f.items.slice(0, 4).forEach((feat) => {
          const mvpTag = feat.is_mvp ? '[MVP] ' : ''
          message += `  - ${mvpTag}${feat.name}\n`
        })
        if (f.total > 4) {
          message += `  - ... and ${f.total - 4} more\n`
        }
      }
      message += '\n'

      // Personas
      const p = status.product.personas
      message += `**Personas:** ${p.total} defined, ${p.primary} primary\n`
      if (p.items.length > 0) {
        p.items.slice(0, 3).forEach((persona) => {
          const primaryTag = persona.is_primary ? ' [Primary]' : ''
          const role = persona.role ? ` - ${persona.role}` : ''
          message += `  - ${persona.name}${role}${primaryTag}\n`
        })
      }
      message += '\n'

      // VP Steps
      const vp = status.product.vp_steps
      message += `**Value Path:** ${vp.total} stages\n`
      if (vp.items.length > 0) {
        vp.items.slice(0, 4).forEach((step) => {
          message += `  ${step.order}. ${step.name}\n`
        })
        if (vp.total > 4) {
          message += `  ... and ${vp.total - 4} more stages\n`
        }
      }
      message += '\n'

      // Market Context
      if (status.market.competitors.length > 0 || status.market.constraints.length > 0) {
        message += `## Market Context\n`
        if (status.market.competitors.length > 0) {
          message += `**Competitors:** ${status.market.competitors.map((c) => c.name).join(', ')}\n`
        }
        if (status.market.design_refs.length > 0) {
          message += `**Design Inspiration:** ${status.market.design_refs.join(', ')}\n`
        }
        if (status.market.constraints.length > 0) {
          message += `**Constraints:** ${status.market.constraints.map((c) => c.name).join(', ')}\n`
        }
        message += '\n'
      }

      // Stakeholders
      if (status.stakeholders.total > 0) {
        message += `## Stakeholders (${status.stakeholders.total})\n`
        status.stakeholders.items.slice(0, 3).forEach((s) => {
          const role = s.role ? ` - ${s.role}` : ''
          const type = s.type ? ` (${s.type})` : ''
          message += `- ${s.name}${role}${type}\n`
        })
        message += '\n'
      }

      // Signals
      message += `## Data Sources\n`
      message += `**Signals:** ${status.signals.total} processed\n\n`

      // Blockers and Suggestions
      if (status.readiness.blockers.length > 0) {
        message += `## ⚠️ Blockers\n`
        status.readiness.blockers.forEach((b) => {
          message += `- ${b}\n`
        })
        message += '\n'
      }

      if (status.readiness.suggestions.length > 0) {
        message += `## 💡 Suggested Next Steps\n`
        status.readiness.suggestions.forEach((s) => {
          message += `- ${s}\n`
        })
      }

      // Quick actions based on state
      const actions: QuickAction[] = []

      if (status.strategic.total_drivers === 0) {
        actions.push({
          id: 'run-foundation',
          label: 'Run Foundation',
          command: '/run-foundation',
          variant: 'primary',
        })
      }

      if (status.product.features.total === 0) {
        actions.push({
          id: 'enrich-features',
          label: 'Generate Features',
          command: '/enrich-features',
          variant: 'default',
        })
      }

      if (status.product.vp_steps.total === 0) {
        actions.push({
          id: 'enrich-vp',
          label: 'Generate Value Path',
          command: '/enrich-value-path',
          variant: 'default',
        })
      }

      return {
        success: true,
        message,
        actions,
      }
    } catch (error) {
      return {
        success: false,
        message: `Failed to get project status: ${error instanceof Error ? error.message : 'Unknown error'}`,
      }
    }
  },
})

// /pending-items
registerCommand({
  name: 'pending-items',
  description: 'List all items that need confirmation',
  aliases: ['pending', 'review'],
  examples: ['/pending-items', '/pending'],
  execute: async (_args, context): Promise<CommandResult> => {
    const { projectData } = context

    const pending = projectData?.pendingConfirmations ?? 0

    if (pending === 0) {
      return {
        success: true,
        message: '## All Caught Up!\n\nNo items pending confirmation. All entities have been reviewed.',
      }
    }

    let message = `## Pending Confirmation\n\n`
    message += `**${pending} items** need your review.\n\n`
    message += `### How to Approve\n`
    message += `1. Click on an entity (feature, persona, or VP step)\n`
    message += `2. Run the appropriate approve command:\n`
    message += `   - \`/approve-feature\`\n`
    message += `   - \`/approve-persona\`\n`
    message += `   - \`/approve-vp-step\`\n\n`
    message += `Or use the confirmation buttons in the entity detail panel.`

    return {
      success: true,
      message,
      actions: [
        {
          id: 'go-features',
          label: 'View Personas & Features',
          navigateTo: { tab: 'personas-features' },
        },
        {
          id: 'go-vp',
          label: 'View Value Path',
          navigateTo: { tab: 'value-path' },
        },
      ],
    }
  },
})

// =============================================================================
// DI AGENT COMMANDS - Design Intelligence
// =============================================================================

// /analyze-project (alias: /di)
registerCommand({
  name: 'analyze-project',
  description: 'Run Design Intelligence analysis to identify next best action',
  aliases: ['di', 'analyze'],
  examples: ['/analyze-project', '/di'],
  execute: async (_args, context): Promise<CommandResult> => {
    const { projectId } = context

    if (!projectId) {
      return {
        success: false,
        message: 'No project selected. Please select a project first.',
      }
    }

    const { invokeDIAgent } = await import('@/lib/api')

    try {
      const result = await invokeDIAgent(projectId, {
        trigger: 'user_request',
        trigger_context: 'slash command from assistant',
      })

      // Build a comprehensive response message
      let message = `## 🧠 Design Intelligence Analysis\n\n`

      // Observation section
      if (result.observation) {
        message += `### 👁️ Observed\n${result.observation}\n\n`
      } else {
        message += `### 👁️ Observed\n*No observation recorded*\n\n`
      }

      // Thinking section
      if (result.thinking) {
        message += `### 🤔 Thinking\n${result.thinking}\n\n`
      } else {
        message += `### 🤔 Thinking\n*No thinking recorded*\n\n`
      }

      // Decision section
      if (result.decision) {
        message += `### ✅ Decision\n${result.decision}\n\n`
      } else {
        message += `### ✅ Decision\n*No decision recorded*\n\n`
      }

      // Actions/Tools section
      if (result.action_type === 'tool_call' && result.tools_called?.length) {
        message += `### 🔧 Actions Taken\n`
        message += `**Tools called:** ${result.tools_called.map((t: any) => t.tool_name).join(', ')}\n\n`

        message += `| Tool | Status | Details |\n`
        message += `|------|--------|--------|\n`
        result.tools_called.forEach((tool: any) => {
          const status = tool.success ? '✅ Success' : '❌ Failed'
          const details = tool.success
            ? (tool.result?.message || 'Completed').slice(0, 50)
            : (tool.error || 'Unknown error').slice(0, 50)
          message += `| ${tool.tool_name} | ${status} | ${details} |\n`
        })
        message += '\n'

        // Show detailed results for each tool
        result.tools_called.forEach((tool: any) => {
          if (tool.success && tool.result) {
            message += `<details>\n<summary>📋 ${tool.tool_name} details</summary>\n\n`
            message += '```json\n'
            message += JSON.stringify(tool.result, null, 2).slice(0, 500)
            if (JSON.stringify(tool.result).length > 500) {
              message += '\n... (truncated)'
            }
            message += '\n```\n</details>\n\n'
          }
        })
      } else if (result.action_type === 'guidance' && result.guidance) {
        const guidance: any = result.guidance
        message += `### 💡 Guidance for Consultant\n`
        message += `${guidance.summary}\n\n`

        if (guidance.questions_to_ask?.length) {
          message += `**Questions to Ask the Client:**\n`
          guidance.questions_to_ask.forEach((q: any, i: number) => {
            message += `${i + 1}. **${q.question}**\n`
            if (q.why_ask) message += `   *Why ask:* ${q.why_ask}\n`
            if (q.listen_for?.length) message += `   *Listen for:* ${q.listen_for.join(', ')}\n`
          })
          message += '\n'
        }

        if (guidance.signals_to_watch?.length) {
          message += `**Signals to Watch:**\n`
          guidance.signals_to_watch.forEach((s: string) => {
            message += `- ${s}\n`
          })
          message += '\n'
        }

        if (guidance.what_this_unlocks) {
          message += `**What this unlocks:** ${guidance.what_this_unlocks}\n\n`
        }
      } else if (result.action_type === 'stop') {
        message += `### ⏹️ Agent Stopped\n`
        message += `*The agent stopped because:* ${result.decision || 'No reason provided'}\n\n`
      }

      // Readiness section
      message += `### 📊 Readiness\n`
      if (result.readiness_before !== undefined && result.readiness_after !== undefined) {
        const change = result.readiness_after - result.readiness_before
        const changeIcon = change > 0 ? '📈' : change < 0 ? '📉' : '➡️'
        message += `${changeIcon} **${result.readiness_before}%** → **${result.readiness_after}%**`
        if (change !== 0) {
          message += ` (${change > 0 ? '+' : ''}${change})`
        }
        message += '\n'
      } else if (result.readiness_before !== undefined) {
        message += `Current: **${result.readiness_before}%**\n`
      }

      // Gates affected
      if (result.gates_affected?.length) {
        message += `\n**Gates affected:** ${result.gates_affected.join(', ')}\n`
      }

      return {
        success: true,
        message,
        data: {
          action: 'di_agent_analysis',
          result,
          refresh_project: true
        },
      }
    } catch (error: unknown) {
      console.error('🧠 DI Agent error:', error)
      return {
        success: false,
        message: `## ❌ DI Analysis Failed\n\n**Error:** ${error instanceof Error ? error.message : 'Unknown error'}\n\nPlease check the browser console and backend logs for more details.`,
      }
    }
  },
})

// /view-foundation
registerCommand({
  name: 'view-foundation',
  description: 'View all foundation gate data for the project',
  aliases: ['foundation', 'gates'],
  examples: ['/view-foundation'],
  execute: async (_args, context): Promise<CommandResult> => {
    const { projectId } = context

    if (!projectId) {
      return {
        success: false,
        message: 'No project selected. Please select a project first.',
      }
    }

    const { getProjectFoundation } = await import('@/lib/api')

    try {
      const foundation = await getProjectFoundation(projectId)

      let message = `## 🏗️ Project Foundation\n\n`

      // Core Pain
      if (foundation.core_pain) {
        message += `### 💔 Core Pain\n`
        message += `${foundation.core_pain.statement}\n`
        message += `*Confidence: ${(foundation.core_pain.confidence * 100).toFixed(0)}%*\n\n`
      } else {
        message += `### 💔 Core Pain\n*Not yet extracted*\n\n`
      }

      // Primary Persona
      if (foundation.primary_persona) {
        message += `### 👤 Primary Persona\n`
        message += `**${foundation.primary_persona.name}** - ${foundation.primary_persona.role}\n`
        message += `*Confidence: ${(foundation.primary_persona.confidence * 100).toFixed(0)}%*\n\n`
      } else {
        message += `### 👤 Primary Persona\n*Not yet extracted*\n\n`
      }

      // Wow Moment
      if (foundation.wow_moment) {
        message += `### ✨ Wow Moment\n`
        message += `${foundation.wow_moment.description}\n`
        message += `*Confidence: ${(foundation.wow_moment.confidence * 100).toFixed(0)}%*\n\n`
      } else {
        message += `### ✨ Wow Moment\n*Not yet identified*\n\n`
      }

      // Business Case
      if (foundation.business_case) {
        message += `### 💰 Business Case\n`
        message += `**Value:** ${foundation.business_case.value_to_business}\n`
        message += `**ROI:** ${foundation.business_case.roi_framing}\n`
        message += `*Confidence: ${(foundation.business_case.confidence * 100).toFixed(0)}%*\n\n`
      } else {
        message += `### 💰 Business Case\n*Not yet extracted*\n\n`
      }

      // Budget Constraints
      if (foundation.budget_constraints) {
        message += `### 📊 Budget & Constraints\n`
        message += `**Budget:** ${foundation.budget_constraints.budget_range}\n`
        message += `**Timeline:** ${foundation.budget_constraints.timeline}\n`
        message += `*Confidence: ${(foundation.budget_constraints.confidence * 100).toFixed(0)}%*\n\n`
      } else {
        message += `### 📊 Budget & Constraints\n*Not yet extracted*\n\n`
      }

      return {
        success: true,
        message,
        data: { action: 'foundation_viewed', foundation },
      }
    } catch (error: unknown) {
      return {
        success: false,
        message: `Failed to load foundation: ${error instanceof Error ? error.message : 'Unknown error'}`,
      }
    }
  },
})

// /view-gates
registerCommand({
  name: 'view-gates',
  description: 'Show gate status from readiness assessment',
  aliases: ['gates-status'],
  examples: ['/view-gates'],
  execute: async (_args, context): Promise<CommandResult> => {
    const { projectId } = context

    if (!projectId) {
      return {
        success: false,
        message: 'No project selected. Please select a project first.',
      }
    }

    const { getReadinessScore } = await import('@/lib/api')

    try {
      const readiness = await getReadinessScore(projectId)

      // The readiness score now includes gate data
      // We'll display it in a readable format
      let message = `## 🚪 Project Gates\n\n`

      message += `**Current Phase:** ${readiness.phase || 'Unknown'}\n`
      message += `**Total Readiness:** ${readiness.score}%\n\n`

      // Display gate information if available
      const gates = readiness.gates || []

      if (gates.length > 0) {
        message += `### Gate Status\n\n`

        gates.forEach((gate) => {
          const icon = gate.is_satisfied ? '✓' : '✗'
          const status = gate.is_satisfied ? 'Satisfied' : 'Not Satisfied'

          message += `${icon} **${gate.gate_name}**: ${status}\n`
          message += `  - Confidence: ${(gate.confidence * 100).toFixed(0)}%\n`
          message += `  - Completeness: ${(gate.completeness * 100).toFixed(0)}%\n`

          if (!gate.is_satisfied && gate.reason_not_satisfied) {
            message += `  - Reason: ${gate.reason_not_satisfied}\n`
          }

          message += '\n'
        })
      } else {
        message += `*No gate data available yet. Run /analyze-project to assess gates.*\n`
      }

      return {
        success: true,
        message,
        data: { action: 'gates_viewed', readiness },
      }
    } catch (error: unknown) {
      return {
        success: false,
        message: `Failed to load gate status: ${error instanceof Error ? error.message : 'Unknown error'}`,
      }
    }
  },
})

// =============================================================================
// GAP ANALYSIS COMMANDS
// =============================================================================

// /analyze-gaps - Comprehensive gap analysis
registerCommand({
  name: 'analyze-gaps',
  description: 'Analyze gaps in foundation, evidence, and solution coverage',
  aliases: ['gaps', 'find-gaps'],
  examples: ['/analyze-gaps', '/gaps'],
  execute: async (_args, context): Promise<CommandResult> => {
    const { projectId } = context

    if (!projectId) {
      return {
        success: false,
        message: 'No project selected. Please select a project first.',
      }
    }

    const { analyzeGaps } = await import('@/lib/api')

    try {
      const result = await analyzeGaps(projectId)

      let message = `## Gap Analysis\n\n`

      // Summary
      if (result.summary) {
        message += `${result.summary}\n\n`
      }

      // Readiness
      message += `**Readiness:** ${result.total_readiness.toFixed(0)}% | **Phase:** ${result.phase || 'Unknown'}\n\n`

      // Counts
      if (result.counts) {
        const { critical_gaps = 0, high_gaps = 0, medium_gaps = 0, low_gaps = 0 } = result.counts
        message += `**Gap Counts:** `
        if (critical_gaps > 0) message += `🔴 ${critical_gaps} critical `
        if (high_gaps > 0) message += `🟠 ${high_gaps} high `
        if (medium_gaps > 0) message += `🟡 ${medium_gaps} medium `
        if (low_gaps > 0) message += `🟢 ${low_gaps} low`
        message += '\n\n'
      }

      // Priority gaps (top 5)
      if (result.priority_gaps?.length > 0) {
        message += `### Priority Gaps\n\n`
        const topGaps = result.priority_gaps.slice(0, 5)
        topGaps.forEach((gap, i) => {
          const severity = gap.severity === 'critical' ? '🔴' :
                          gap.severity === 'high' ? '🟠' :
                          gap.severity === 'medium' ? '🟡' : '🟢'
          message += `${i + 1}. ${severity} **${gap.type}**: ${gap.description}\n`
          if (gap.suggestion) {
            message += `   → *${gap.suggestion}*\n`
          }
        })
        message += '\n'
      } else {
        message += `*No significant gaps found. Project is on track!*\n\n`
      }

      message += `\n*Use /suggest-fixes to get actionable suggestions.*`

      return {
        success: true,
        message,
        data: { action: 'gaps_analyzed', result },
      }
    } catch (error: unknown) {
      return {
        success: false,
        message: `Failed to analyze gaps: ${error instanceof Error ? error.message : 'Unknown error'}`,
      }
    }
  },
})

// /analyze-requirements - Requirements gap analysis
registerCommand({
  name: 'analyze-requirements',
  description: 'Analyze logical gaps in requirements (features, personas, VP steps)',
  aliases: ['req-gaps', 'requirements-gaps'],
  examples: ['/analyze-requirements', '/req-gaps'],
  args: [
    {
      name: 'focus',
      type: 'string',
      required: false,
      description: 'Focus areas (features, personas, vp_steps)',
    },
  ],
  execute: async (args, context): Promise<CommandResult> => {
    const { projectId } = context

    if (!projectId) {
      return {
        success: false,
        message: 'No project selected. Please select a project first.',
      }
    }

    const { analyzeRequirementsGaps } = await import('@/lib/api')

    try {
      const focus = args.focus as string | undefined
      const focusAreas = focus ? focus.split(',').map(s => s.trim()) : undefined
      const result = await analyzeRequirementsGaps(projectId, focusAreas)

      let message = `## Requirements Gap Analysis\n\n`

      // Summary stats
      if (result.summary) {
        const { total_gaps, high_severity, medium_severity, low_severity, overall_completeness } = result.summary
        message += `**Total Gaps:** ${total_gaps} | `
        message += `High: ${high_severity} | Medium: ${medium_severity} | Low: ${low_severity}\n`
        if (overall_completeness !== undefined) {
          message += `**Completeness:** ${overall_completeness.toFixed(0)}%\n`
        }
        message += '\n'
      }

      // Entities analyzed
      if (result.entities_analyzed) {
        const { features = 0, personas = 0, vp_steps = 0 } = result.entities_analyzed
        message += `*Analyzed: ${features} features, ${personas} personas, ${vp_steps} VP steps*\n\n`
      }

      // Gaps (top 10)
      if (result.gaps?.length > 0) {
        message += `### Gaps Found\n\n`
        const topGaps = result.gaps.slice(0, 10)
        topGaps.forEach((gap, i) => {
          const severity = gap.severity === 'high' ? '🔴' :
                          gap.severity === 'medium' ? '🟡' : '🟢'
          message += `${i + 1}. ${severity} **${gap.gap_type}**: ${gap.description}\n`
          if (gap.suggestion) {
            message += `   → *${gap.suggestion}*\n`
          }
        })
        message += '\n'
      } else {
        message += `*No requirements gaps found!*\n\n`
      }

      // Recommendations
      if (result.recommendations?.length > 0) {
        message += `### Recommendations\n\n`
        result.recommendations.slice(0, 5).forEach((rec, i) => {
          message += `${i + 1}. ${rec}\n`
        })
      }

      return {
        success: true,
        message,
        data: { action: 'requirements_analyzed', result },
      }
    } catch (error: unknown) {
      return {
        success: false,
        message: `Failed to analyze requirements: ${error instanceof Error ? error.message : 'Unknown error'}`,
      }
    }
  },
})

// /suggest-fixes - Get suggestions to fix gaps
registerCommand({
  name: 'suggest-fixes',
  description: 'Generate actionable suggestions to fix identified gaps',
  aliases: ['fix-gaps', 'gap-fixes'],
  examples: ['/suggest-fixes', '/fix-gaps'],
  args: [
    {
      name: 'max',
      type: 'number',
      required: false,
      description: 'Maximum suggestions (1-20, default 5)',
    },
  ],
  execute: async (args, context): Promise<CommandResult> => {
    const { projectId } = context

    if (!projectId) {
      return {
        success: false,
        message: 'No project selected. Please select a project first.',
      }
    }

    const { suggestGapFixes } = await import('@/lib/api')

    try {
      const maxSuggestions = Math.min(20, Math.max(1, Number(args.max) || 5))
      const result = await suggestGapFixes(projectId, maxSuggestions)

      let message = `## Gap Fix Suggestions\n\n`

      if (result.summary) {
        message += `${result.summary}\n\n`
      }

      if (result.suggestions?.length > 0) {
        result.suggestions.forEach((suggestion, i) => {
          const severity = suggestion.severity === 'critical' ? '🔴' :
                          suggestion.severity === 'high' ? '🟠' :
                          suggestion.severity === 'medium' ? '🟡' : '🟢'
          const risk = suggestion.risk_level === 'low' ? '✅' : '⚠️'

          message += `### ${i + 1}. ${suggestion.title}\n`
          message += `${severity} ${suggestion.entity_type} | ${suggestion.action} | Risk: ${risk}\n\n`
          message += `${suggestion.description}\n\n`
        })

        if (result.auto_applicable > 0) {
          message += `\n*${result.auto_applicable} suggestions can be auto-applied.*\n`
        }
      } else {
        message += `*No suggestions needed - project is in good shape!*\n`
      }

      return {
        success: true,
        message,
        data: { action: 'fixes_suggested', result },
      }
    } catch (error: unknown) {
      return {
        success: false,
        message: `Failed to generate suggestions: ${error instanceof Error ? error.message : 'Unknown error'}`,
      }
    }
  },
})

// =============================================================================
// TASK COMMANDS - Work Item Management
// =============================================================================

// /tasks - List pending tasks
registerCommand({
  name: 'tasks',
  description: 'List pending tasks for the project',
  aliases: ['list-tasks', 'task-list'],
  examples: ['/tasks', '/tasks pending', '/tasks client'],
  args: [
    {
      name: 'filter',
      type: 'string',
      required: false,
      description: 'Filter: pending, all, client, proposals, gaps',
    },
  ],
  execute: async (args, context): Promise<CommandResult> => {
    const { projectId } = context
    const filter = (args.filter as string) || 'pending'

    if (!projectId) {
      return {
        success: false,
        message: 'No project selected. Please select a project first.',
      }
    }

    const { listTasks, getTaskStats } = await import('@/lib/api')

    try {
      // Build filter params
      const params: Record<string, unknown> = {
        limit: 20,
        sort_by: 'priority_score',
        sort_order: 'desc' as const,
      }

      if (filter === 'pending') {
        params.status = 'pending'
      } else if (filter === 'client') {
        params.requires_client_input = true
        params.status = 'pending'
      } else if (filter === 'proposals') {
        params.task_type = 'proposal'
        params.status = 'pending'
      } else if (filter === 'gaps') {
        params.task_type = 'gap'
        params.status = 'pending'
      }
      // 'all' has no status filter

      const [result, stats] = await Promise.all([
        listTasks(projectId, params),
        getTaskStats(projectId),
      ])

      if (result.tasks.length === 0) {
        return {
          success: true,
          message: `## No Tasks\n\nNo ${filter === 'all' ? '' : filter + ' '}tasks found.\n\nTasks are automatically created when:\n- Signal processing generates proposals\n- DI Agent identifies gaps\n- Entities need enrichment\n\nOr create one manually with \`/create-task\``,
          actions: [
            {
              id: 'sync-gaps',
              label: 'Sync Gap Tasks',
              command: '/sync-tasks gaps',
              variant: 'primary',
            },
          ],
        }
      }

      let message = `## Tasks (${filter})\n\n`
      message += `**${stats.by_status?.pending || 0}** pending • `
      message += `**${stats.by_status?.completed || 0}** completed • `
      message += `**${stats.client_relevant}** need client input\n\n`

      result.tasks.forEach((task, idx) => {
        const icon = task.task_type === 'gap' ? '🎯' :
                    task.task_type === 'proposal' ? '📋' :
                    task.task_type === 'enrichment' ? '✨' :
                    task.task_type === 'validation' ? '✓' : '📝'
        const clientTag = task.requires_client_input ? ' [Client]' : ''
        const priority = task.priority_score >= 70 ? '🔴' :
                        task.priority_score >= 50 ? '🟡' : '🟢'

        message += `${idx + 1}. ${icon} **${task.title}**${clientTag}\n`
        message += `   ${priority} Priority: ${task.priority_score.toFixed(0)} • Type: ${task.task_type}\n`
        if (task.description) {
          message += `   ${task.description.slice(0, 80)}${task.description.length > 80 ? '...' : ''}\n`
        }
        message += '\n'
      })

      if (result.has_more) {
        message += `*Showing ${result.tasks.length} of ${result.total} tasks*\n`
      }

      return {
        success: true,
        message,
        actions: [
          {
            id: 'sync-tasks',
            label: 'Sync Tasks',
            command: '/sync-tasks',
            variant: 'primary',
          },
          {
            id: 'view-overview',
            label: 'View in Next Steps',
            navigateTo: { tab: 'next-steps' },
          },
        ],
      }
    } catch (error) {
      return {
        success: false,
        message: `Failed to list tasks: ${error instanceof Error ? error.message : 'Unknown error'}`,
      }
    }
  },
})

// /create-task - Create a manual task
registerCommand({
  name: 'create-task',
  description: 'Create a new task to track work',
  aliases: ['add-task', 'new-task'],
  args: [
    {
      name: 'title',
      type: 'string',
      required: true,
      description: 'Task title',
    },
  ],
  examples: [
    '/create-task "Review persona updates"',
    '/create-task "Validate feature with client"',
  ],
  execute: async (args, context): Promise<CommandResult> => {
    const { projectId } = context
    const title = (args.title as string) || (args.input as string)

    if (!projectId) {
      return {
        success: false,
        message: 'No project selected. Please select a project first.',
      }
    }

    if (!title) {
      return {
        success: false,
        message: 'Please provide a task title.\n\nUsage: `/create-task "Title"`\n\nExample: `/create-task "Review persona updates"`',
      }
    }

    const { createTask } = await import('@/lib/api')

    try {
      const task = await createTask(projectId, {
        title,
        task_type: 'manual',
      })

      return {
        success: true,
        message: `## Task Created\n\n**${task.title}**\n\nID: \`${task.id}\`\nPriority: ${task.priority_score.toFixed(0)}\nStatus: ${task.status}\n\nView tasks with \`/tasks\``,
        data: {
          taskId: task.id,
          action: 'task_created',
        },
      }
    } catch (error) {
      return {
        success: false,
        message: `Failed to create task: ${error instanceof Error ? error.message : 'Unknown error'}`,
      }
    }
  },
})

// /sync-tasks - Sync tasks from gaps or enrichment needs
registerCommand({
  name: 'sync-tasks',
  description: 'Sync tasks from project state (gaps, enrichment needs)',
  aliases: ['refresh-tasks'],
  args: [
    {
      name: 'source',
      type: 'string',
      required: false,
      description: 'Source to sync: gaps, enrichment, or all (default: all)',
    },
  ],
  examples: ['/sync-tasks', '/sync-tasks gaps', '/sync-tasks enrichment'],
  execute: async (args, context): Promise<CommandResult> => {
    const { projectId } = context
    const source = (args.source as string) || 'all'

    if (!projectId) {
      return {
        success: false,
        message: 'No project selected. Please select a project first.',
      }
    }

    const { syncGapTasks, syncEnrichmentTasks } = await import('@/lib/api')

    try {
      let gapResult = { tasks_created: 0 }
      let enrichResult = { tasks_created: 0 }

      if (source === 'gaps' || source === 'all') {
        gapResult = await syncGapTasks(projectId)
      }

      if (source === 'enrichment' || source === 'all') {
        enrichResult = await syncEnrichmentTasks(projectId)
      }

      const totalCreated = gapResult.tasks_created + enrichResult.tasks_created

      if (totalCreated === 0) {
        return {
          success: true,
          message: '## Tasks Synced\n\nNo new tasks created. Project state is up to date.',
        }
      }

      let message = `## Tasks Synced\n\n`
      if (gapResult.tasks_created > 0) {
        message += `✓ Created **${gapResult.tasks_created}** gap tasks\n`
      }
      if (enrichResult.tasks_created > 0) {
        message += `✓ Created **${enrichResult.tasks_created}** enrichment tasks\n`
      }
      message += `\nView tasks with \`/tasks\``

      return {
        success: true,
        message,
        data: {
          action: 'tasks_synced',
          gap_tasks: gapResult.tasks_created,
          enrichment_tasks: enrichResult.tasks_created,
        },
      }
    } catch (error) {
      return {
        success: false,
        message: `Failed to sync tasks: ${error instanceof Error ? error.message : 'Unknown error'}`,
      }
    }
  },
})

// =============================================================================
// MEMORY COMMANDS
// =============================================================================

// /memory - View project memory
registerCommand({
  name: 'memory',
  description: 'View unified project memory (synthesized from decisions, learnings, knowledge graph)',
  aliases: ['view-memory', 'memories'],
  examples: ['/memory'],
  execute: async (_args, context): Promise<CommandResult> => {
    const { projectId } = context

    if (!projectId) {
      return {
        success: false,
        message: 'No project selected. Please select a project first.',
      }
    }

    const { getUnifiedMemory } = await import('@/lib/api')

    try {
      const memory = await getUnifiedMemory(projectId)

      if (!memory || !memory.content) {
        return {
          success: true,
          message: `## Project Memory\n\n*No memories synthesized yet.*\n\nMemory will be generated automatically after processing signals, or use \`/remember\` to add decisions, learnings, or questions.`,
        }
      }

      // Build status header with freshness info
      let statusLine = ''
      if (memory.freshness?.age_human) {
        statusLine += `*Last synthesized: ${memory.freshness.age_human}*`
      }
      if (memory.is_stale) {
        const staleReasonMap: Record<string, string> = {
          signal_processed: 'new signal processed',
          bulk_signal_processed: 'document processed',
          decision_added: 'decision added',
          learning_added: 'learning added',
          question_added: 'question added',
          beliefs_updated: 'knowledge graph updated',
        }
        const reason = memory.stale_reason ? staleReasonMap[memory.stale_reason] || memory.stale_reason : 'new updates'
        statusLine += statusLine ? ` | ` : ''
        statusLine += `**Updates available** (${reason})`
      }

      let message = `## Project Memory\n\n`
      if (statusLine) {
        message += `${statusLine}\n\n---\n\n`
      }
      message += memory.content

      return {
        success: true,
        message,
        data: {
          action: 'memory_viewed',
          is_stale: memory.is_stale,
          freshness: memory.freshness,
        },
      }
    } catch (error: unknown) {
      return {
        success: false,
        message: `Failed to load memory: ${error instanceof Error ? error.message : 'Unknown error'}`,
      }
    }
  },
})

// /remember - Add to project memory
registerCommand({
  name: 'remember',
  description: 'Add a decision, learning, or question to project memory',
  aliases: ['add-to-memory', 'note'],
  args: [
    {
      name: 'type',
      type: 'string',
      required: false,
      description: 'Memory type: decision, learning, or question',
    },
    {
      name: 'content',
      type: 'string',
      required: false,
      description: 'The content to remember',
    },
  ],
  examples: [
    '/remember decision "We chose React for the frontend"',
    '/remember learning "Client prefers visual mockups"',
    '/remember question "What is the budget timeline?"',
  ],
  execute: async (args, context): Promise<CommandResult> => {
    const { projectId } = context
    const type = args.type as string | undefined
    const content = args.content as string || args.input as string

    if (!projectId) {
      return {
        success: false,
        message: 'No project selected. Please select a project first.',
      }
    }

    // If no type provided, show usage
    if (!type || !['decision', 'learning', 'question'].includes(type)) {
      return {
        success: false,
        message: `## Add to Memory\n\nUsage: \`/remember <type> "<content>"\`\n\n**Types:**\n- \`decision\` - A key decision made\n- \`learning\` - Something learned about the project/client\n- \`question\` - An open question to resolve\n\n**Examples:**\n- \`/remember decision "We chose mobile-first approach"\`\n- \`/remember learning "Weekly check-ins work better"\`\n- \`/remember question "Who approves final designs?"\``,
      }
    }

    if (!content) {
      return {
        success: false,
        message: `Please provide content to remember.\n\nUsage: \`/remember ${type} "Your content here"\``,
      }
    }

    const { addToMemory } = await import('@/lib/api')

    try {
      await addToMemory(projectId, type, content)

      const typeLabels: Record<string, string> = {
        decision: 'Decision',
        learning: 'Learning',
        question: 'Question',
      }

      return {
        success: true,
        message: `## ${typeLabels[type]} Added\n\n"${content}"\n\nView all memories with \`/memory\``,
        data: {
          action: 'memory_added',
          type,
          content,
        },
      }
    } catch (error: unknown) {
      return {
        success: false,
        message: `Failed to add memory: ${error instanceof Error ? error.message : 'Unknown error'}`,
      }
    }
  },
})

// =============================================================================
// UTILITY COMMANDS
// =============================================================================

// /clear-chat
registerCommand({
  name: 'clear-chat',
  description: 'Clear the conversation history',
  aliases: ['clear', 'reset'],
  examples: ['/clear-chat', '/clear'],
  execute: async (): Promise<CommandResult> => {
    return {
      success: true,
      message: 'Conversation cleared.',
      data: { action: 'clear_messages' },
    }
  },
})

// /help
registerCommand({
  name: 'help',
  description: 'Show all available commands',
  aliases: ['?', 'commands'],
  args: [
    {
      name: 'command',
      type: 'string',
      required: false,
      description: 'Get help for a specific command',
    },
  ],
  examples: ['/help', '/help run-foundation'],
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

    // Show all commands grouped by category
    let message = `## Available Commands\n\n`

    message += `### AI Agents\n`
    message += `**/di** (or **/analyze-project**) - Run DI Agent analysis\n`
    message += `**/run-foundation** - Extract company info, drivers, competitors\n`
    message += `**/run-research** - Deep web research on company/market\n`
    message += `**/research-status** - Check status of running research\n`
    message += `**/enrich-features** - AI enhance all features\n`
    message += `**/enrich-personas** - AI enhance all personas\n`
    message += `**/enrich-value-path** - AI enhance all VP steps\n`
    message += `**/enrich-business-drivers** - AI enhance all drivers\n`
    message += `**/enrich-kpis** - AI enhance KPIs\n`
    message += `**/enrich-pain-points** - AI enhance pain points\n`
    message += `**/enrich-goals** - AI enhance goals\n\n`

    message += `### View Info\n`
    message += `**/status** - Project state overview\n`
    message += `**/view-foundation** - View foundation data\n`
    message += `**/view-gates** - Show gate status and readiness\n\n`

    message += `### Gap Analysis\n`
    message += `**/analyze-gaps** - Find gaps in foundation and evidence\n`
    message += `**/analyze-requirements** - Find logical gaps in requirements\n`
    message += `**/suggest-fixes** - Get actionable suggestions to fix gaps\n\n`

    message += `### Tasks\n`
    message += `**/tasks** - List pending tasks\n`
    message += `**/create-task** "title" - Create a task\n`
    message += `**/sync-tasks** - Analyze gaps + create tasks\n\n`

    message += `### Create\n`
    message += `**/create-stakeholder** "Name" - Add new stakeholder\n\n`

    message += `### Memory\n`
    message += `**/memory** - View project memory\n`
    message += `**/remember** - Add to project memory\n\n`

    message += `### Utility\n`
    message += `**/clear** - Clear conversation\n`
    message += `**/help** - Show this help\n\n`

    message += `*Type \`/help <command>\` for details.*`

    return { success: true, message }
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

    message += `\n\nType \`/help\` to see all available commands.`

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
