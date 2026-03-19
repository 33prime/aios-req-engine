import { useMemo } from 'react'
import type {
  SolutionFlowOverview,
  SolutionFlowStepDetail,
  DerivedAgent,
  AgentType,
  AgentMaturity,
  AgentDataNeed,
  AgentTechnique,
  AgentRhythm,
  ConfidenceTiers,
  EvolutionStep,
} from '@/types/workspace'

const AGENT_TYPE_KEYWORDS: Array<[AgentType, string[]]> = [
  ['classifier', ['classify', 'categoriz', 'sort', 'label', 'tag']],
  ['matcher', ['match', 'connect', 'link', 'recommend', 'map']],
  ['predictor', ['predict', 'forecast', 'estimate', 'anticipat', 'project']],
  ['watcher', ['monitor', 'watch', 'alert', 'track', 'detect']],
  ['generator', ['generate', 'create', 'assembl', 'report', 'compil', 'summar']],
]

const AGENT_ICONS: Record<AgentType, string> = {
  classifier: '◈',
  matcher: '⬢',
  predictor: '◇',
  watcher: '◉',
  generator: '◆',
  processor: '⬡',
}

const TECHNIQUE_MAP: Record<AgentType, AgentTechnique> = {
  classifier: 'classification',
  matcher: 'embeddings',
  predictor: 'llm',
  watcher: 'rules',
  generator: 'llm',
  processor: 'hybrid',
}

const RHYTHM_KEYWORDS: Array<[AgentRhythm, string[]]> = [
  ['always_on', ['monitor', 'watch', 'continuous', 'real-time', 'stream']],
  ['periodic', ['daily', 'weekly', 'scheduled', 'batch', 'periodic']],
  ['triggered', ['trigger', 'event', 'signal', 'ingest', 'on change']],
]

function inferTechnique(type: AgentType, behaviors: string[]): AgentTechnique {
  const text = behaviors.join(' ').toLowerCase()
  if (text.includes('embed') || text.includes('vector') || text.includes('similarity')) return 'embeddings'
  if (text.includes('rule') || text.includes('threshold') || text.includes('regex')) return 'rules'
  if (text.includes('hybrid') || text.includes('multi-model')) return 'hybrid'
  if (text.includes('classify') || text.includes('categoriz')) return 'classification'
  return TECHNIQUE_MAP[type] || 'llm'
}

function inferRhythm(phase: number, role: string, behaviors: string[]): AgentRhythm {
  const text = [...behaviors, role].join(' ').toLowerCase()
  for (const [rhythm, keywords] of RHYTHM_KEYWORDS) {
    if (keywords.some(k => text.includes(k))) return rhythm
  }
  // Early steps tend to be triggered, later steps on-demand
  if (phase <= 2) return 'triggered'
  return 'on_demand'
}

function parseConfidenceTiers(breakdown: Record<string, number>): ConfidenceTiers {
  const total = Object.values(breakdown).reduce((s, v) => s + v, 0) || 1
  return {
    high: Math.round(((breakdown.known || 0) / total) * 100),
    medium: Math.round(((breakdown.partially_known || 0) / total) * 100),
    low: Math.round(((breakdown.unknown || 0) / total) * 100),
  }
}

function parseEvolution(trajectory: string | undefined | null): EvolutionStep[] {
  if (!trajectory) return []
  // Split trajectory on common separators: periods, semicolons, numbered items
  const parts = trajectory
    .split(/[.;]|\d+\)|\d+\./)
    .map(s => s.trim())
    .filter(s => s.length > 5 && s.length < 120)
    .slice(0, 5)

  // First half marked done, rest pending
  return parts.map((label, i) => ({
    label,
    done: i < Math.ceil(parts.length / 2),
  }))
}

function inferAgentType(behaviors: string[], role: string): AgentType {
  const text = [...behaviors, role].join(' ').toLowerCase()
  for (const [type, keywords] of AGENT_TYPE_KEYWORDS) {
    if (keywords.some(k => text.includes(k))) return type
  }
  return 'processor'
}

function inferMaturity(confidence: Record<string, number>): AgentMaturity {
  const total = Object.values(confidence).reduce((s, v) => s + v, 0)
  if (total === 0) return 'learning'
  const known = confidence.known || 0
  const ratio = known / total
  if (ratio > 0.6) return 'expert'
  if (ratio > 0.3) return 'reliable'
  return 'learning'
}

function cleanAgentName(role: string, title: string): string {
  // If there's an explicit agent_name-style role, clean it up
  if (role.length <= 40) return role
  // Fall back to step title
  return title
}

function extractTransform(
  pains: Array<{ text: string; persona?: string } | string> | null | undefined,
  goals: string[] | null | undefined
): { before: string; after: string } {
  const before = pains?.[0]
    ? (typeof pains[0] === 'string' ? pains[0] : pains[0].text)
    : 'Manual process'
  const after = goals?.[0] || 'AI-assisted automation'
  return { before, after }
}

export function useAgentDerivation(
  flow: SolutionFlowOverview | null | undefined,
  stepDetails?: Map<string, SolutionFlowStepDetail>
) {
  return useMemo(() => {
    if (!flow?.steps?.length) {
      return { agents: [] as DerivedAgent[], agentCount: 0, avgAutomation: 0, hasMinimumAgents: false }
    }

    // Filter steps that have AI config with a role
    const aiSteps = flow.steps
      .map((summary, index) => {
        const detail = stepDetails?.get(summary.id)
        return { summary, detail, index }
      })
      .filter(({ detail }) => {
        if (!detail?.ai_config) return false
        return detail.ai_config.role || detail.ai_config.ai_role
      })

    // Build output arrays per agent for dependency computation
    const agentOutputs = new Map<string, string[]>()
    aiSteps.forEach(({ summary, detail }) => {
      if (!detail) return
      const outputs = detail.information_fields
        ?.filter(f => f.type === 'computed' || f.type === 'displayed')
        .map(f => f.name.toLowerCase()) || []
      agentOutputs.set(summary.id, outputs)
    })

    // Build agents
    const agents: DerivedAgent[] = aiSteps.map(({ summary, detail, index }) => {
      const config = detail!.ai_config!
      const role = config.role || config.ai_role || ''
      const name = config.agent_name || cleanAgentName(role, summary.title)
      const type = config.agent_type || inferAgentType(config.behaviors || [], role)

      // Compute dependencies from data_inputs matching other agents' outputs
      const inputs = detail!.information_fields
        ?.filter(f => f.type === 'captured')
        .map(f => f.name.toLowerCase()) || []

      const dependsOnIds: string[] = []
      const feedsIds: string[] = []

      aiSteps.forEach(other => {
        if (other.summary.id === summary.id) return
        const otherOutputs = agentOutputs.get(other.summary.id) || []
        // If any of our inputs match their outputs, we depend on them
        if (inputs.some(inp => otherOutputs.some(out => out.includes(inp) || inp.includes(out)))) {
          dependsOnIds.push(other.summary.id)
        }
        // If any of our outputs match their inputs, we feed them
        const otherDetail = stepDetails?.get(other.summary.id)
        const otherInputs = otherDetail?.information_fields
          ?.filter(f => f.type === 'captured')
          .map(f => f.name.toLowerCase()) || []
        const ourOutputs = agentOutputs.get(summary.id) || []
        if (ourOutputs.some(out => otherInputs.some(inp => out.includes(inp) || inp.includes(out)))) {
          feedsIds.push(other.summary.id)
        }
      })

      // Data needs
      const dataNeeds: AgentDataNeed[] = config.data_requirements?.map(dr => ({
        source: dr.source,
        amount: dr.volume || '',
        quality: dr.quality_needed || 'good',
      })) || inputs.slice(0, 4).map(inp => ({
        source: inp,
        amount: '',
        quality: 'good' as const,
      }))

      // Produces
      const produces = (agentOutputs.get(summary.id) || []).slice(0, 5)

      const automationRate = config.automation_estimate
        ?? Math.round(((summary.confidence_breakdown?.known || 0) / Math.max(summary.info_field_count, 1)) * 100)

      const { before, after } = extractTransform(
        detail?.pain_points_addressed,
        detail?.goals_addressed
      )

      return {
        id: summary.id,
        name,
        role: summary.goal || role,
        type,
        icon: AGENT_ICONS[type],
        sourceStepId: summary.id,
        sourceStepIndex: index,
        sourceStepTitle: summary.title,
        dataNeeds,
        produces,
        humanPartners: summary.actors || [],
        feedsAgentIds: feedsIds,
        dependsOnAgentIds: dependsOnIds,
        maturity: inferMaturity(summary.confidence_breakdown || {}),
        automationRate: Math.min(100, Math.max(0, automationRate)),
        transform: { before, after },
        dailyWork: detail?.mock_data_narrative || '',
        growth: config.learning_trajectory || detail?.background_narrative || '',
        insight: detail?.background_narrative || '',
        humanValueStatement: config.human_value_statement || detail?.human_value_statement || null,
        // Workbench extensions
        technique: inferTechnique(type, config.behaviors || []),
        rhythm: inferRhythm(index, role, config.behaviors || []),
        confidenceTiers: parseConfidenceTiers(summary.confidence_breakdown || {}),
        evolution: parseEvolution(config.learning_trajectory),
      }
    })

    const avgAutomation = agents.length
      ? Math.round(agents.reduce((s, a) => s + a.automationRate, 0) / agents.length)
      : 0

    return {
      agents,
      agentCount: agents.length,
      avgAutomation,
      hasMinimumAgents: agents.length > 3,
    }
  }, [flow, stepDetails])
}
