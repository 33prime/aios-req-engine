'use client'

/**
 * IntelligenceWorkbench — Intelligence Layer view.
 *
 * Two data sources:
 * 1. DB-backed agents (from /intelligence-layer/agents) — preferred
 * 2. Derived agents (from useAgentDerivation) — fallback
 *
 * Shows "Build Intelligence Layer" CTA when no DB agents exist.
 * DAG canvas with dependency edges, hover highlighting, detail panel.
 */

import { useState, useMemo, useCallback, useEffect } from 'react'
import useSWR from 'swr'
import type {
  SolutionFlowOverview,
  SolutionFlowStepDetail,
  PersonaSummary,
  DerivedAgent,
  IntelLayerAgent,
  IntelLayerResponse,
} from '@/types/workspace'
import { useWeightedLayout, getSizeClass, type LayoutItem } from '@/hooks/useWeightedLayout'
import { useAgentDerivation } from '@/hooks/useAgentDerivation'
import { getSolutionFlowStep } from '@/lib/api/admin'
import { getIntelligenceAgents, generateIntelligenceLayer } from '@/lib/api/intel-layer'
import { WorkbenchNode } from './WorkbenchNode'
import { WorkbenchDetailPanel } from './WorkbenchDetailPanel'
import { AIPresentMode } from './AIPresentMode'

type AgentLike = DerivedAgent | IntelLayerAgent

interface IntelligenceWorkbenchProps {
  projectId: string
  flow: SolutionFlowOverview | null | undefined
  personas: PersonaSummary[]
}

function calcWeight(agent: AgentLike): number {
  if ('tools' in agent && 'autonomy_level' in agent) {
    // DB agent
    const a = agent as IntelLayerAgent
    return (
      a.tools.length * 12 +
      a.data_sources.length * 8 +
      (a.partner_role ? 10 : 0) +
      a.feeds_agent_ids.length * 12 +
      Math.round(a.automation_rate * 0.3)
    )
  }
  // Derived agent
  const d = agent as DerivedAgent
  return (
    d.dataNeeds.length * 8 +
    d.produces.length * 6 +
    d.humanPartners.length * 10 +
    d.feedsAgentIds.length * 12 +
    (d.transform.before !== 'Manual process' ? 10 : 0) +
    Math.round(d.automationRate * 0.3)
  )
}

function getPersonaColor(name: string): string {
  const palette = ['#3FAF7A', '#044159', '#2D6B4A', '#0A1E2F']
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
  return palette[Math.abs(hash) % palette.length]
}

function getAgentDeps(agent: AgentLike): string[] {
  if ('depends_on_agent_ids' in agent) return agent.depends_on_agent_ids
  return (agent as DerivedAgent).dependsOnAgentIds
}

function getAgentFeeds(agent: AgentLike): string[] {
  if ('feeds_agent_ids' in agent) return agent.feeds_agent_ids
  return (agent as DerivedAgent).feedsAgentIds
}

function getAgentPartners(agent: AgentLike): string[] {
  if ('partner_role' in agent && agent.partner_role) return [agent.partner_role]
  if ('humanPartners' in agent) return (agent as DerivedAgent).humanPartners
  return []
}

function getAgentAutomation(agent: AgentLike): number {
  if ('automation_rate' in agent) return agent.automation_rate
  return (agent as DerivedAgent).automationRate
}

export function IntelligenceWorkbench({ projectId, flow, personas }: IntelligenceWorkbenchProps) {
  const [activeAgentId, setActiveAgentId] = useState<string | null>(null)
  const [hoveredAgentId, setHoveredAgentId] = useState<string | null>(null)
  const [activePersona, setActivePersona] = useState<number | null>(null)
  const [presentMode, setPresentMode] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)

  // ── DB agents ──
  const { data: dbData, mutate: refreshAgents } = useSWR<IntelLayerResponse>(
    projectId ? `intel-layer-${projectId}` : null,
    () => getIntelligenceAgents(projectId),
    { revalidateOnFocus: false }
  )
  const dbAgents = dbData?.agents ?? []
  const isDbBacked = dbAgents.length > 0

  // ── Derived agents (fallback) ──
  const [stepDetails, setStepDetails] = useState<Map<string, SolutionFlowStepDetail>>(new Map())
  const [detailsFetched, setDetailsFetched] = useState(false)

  useEffect(() => {
    if (!flow?.steps?.length || detailsFetched || isDbBacked) return
    setDetailsFetched(true)
    Promise.allSettled(
      flow.steps.map(s => getSolutionFlowStep(projectId, s.id))
    ).then(results => {
      const map = new Map<string, SolutionFlowStepDetail>()
      results.forEach((r, i) => {
        if (r.status === 'fulfilled') map.set(flow.steps[i].id, r.value)
      })
      setStepDetails(map)
    })
  }, [flow, projectId, detailsFetched, isDbBacked])

  const { agents: derivedAgents, agentCount: derivedCount, avgAutomation: derivedAvg, hasMinimumAgents } = useAgentDerivation(flow, stepDetails)

  // ── Unified agent list ──
  const agents: AgentLike[] = isDbBacked ? dbAgents : derivedAgents
  const agentCount = isDbBacked ? dbAgents.length : derivedCount
  const validatedCount = isDbBacked ? dbAgents.filter(a => a.validation_status === 'validated').length : 0
  const avgAutomation = isDbBacked
    ? (dbAgents.length ? Math.round(dbAgents.reduce((s, a) => s + a.automation_rate, 0) / dbAgents.length) : 0)
    : derivedAvg

  // ── Generate handler ──
  const handleGenerate = useCallback(async () => {
    setIsGenerating(true)
    try {
      await generateIntelligenceLayer(projectId)
      await refreshAgents()
    } catch (err) {
      console.error('Failed to generate intelligence layer:', err)
    }
    setIsGenerating(false)
  }, [projectId, refreshAgents])

  // ── DAG layout ──
  const layoutItems: LayoutItem[] = useMemo(() => {
    if (!agents.length) return []
    const depthMap = new Map<string, number>()
    const rowInCol = new Map<number, number>()

    function getDepth(agent: AgentLike, visited = new Set<string>()): number {
      if (depthMap.has(agent.id)) return depthMap.get(agent.id)!
      if (visited.has(agent.id)) return 0
      visited.add(agent.id)
      const deps = getAgentDeps(agent)
      if (!deps.length) { depthMap.set(agent.id, 0); return 0 }
      const maxParent = Math.max(...deps.map(depId => {
        const parent = agents.find(a => a.id === depId)
        return parent ? getDepth(parent, visited) : -1
      }))
      const depth = maxParent + 1
      depthMap.set(agent.id, depth)
      return depth
    }

    agents.forEach(a => getDepth(a))

    return agents.map(agent => {
      const col = depthMap.get(agent.id) || 0
      const row = rowInCol.get(col) || 0
      rowInCol.set(col, row + 1)
      return { id: agent.id, weight: calcWeight(agent), column: col, row }
    })
  }, [agents])

  const { positions, totalWidth, totalHeight, heroId } = useWeightedLayout(layoutItems)

  const activeAgent = agents.find(a => a.id === activeAgentId) || null
  const isPersonaFiltered = activePersona !== null

  const connectedIds = useMemo(() => {
    if (!hoveredAgentId) return new Set<string>()
    const hovered = agents.find(a => a.id === hoveredAgentId)
    if (!hovered) return new Set<string>()
    const connected = new Set([hoveredAgentId])
    getAgentFeeds(hovered).forEach(id => connected.add(id))
    getAgentDeps(hovered).forEach(id => connected.add(id))
    return connected
  }, [hoveredAgentId, agents])

  // ── Persona list ──
  const personaList = useMemo(() => {
    const seen = new Set<string>()
    const list: { name: string; color: string; initials: string }[] = []
    agents.forEach(a => {
      getAgentPartners(a).forEach(name => {
        if (!seen.has(name)) {
          seen.add(name)
          list.push({ name, color: getPersonaColor(name), initials: name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase() })
        }
      })
    })
    return list
  }, [agents])

  const estTimeSaved = useMemo(() => {
    if (!agents.length) return '—'
    const totalRate = agents.reduce((s, a) => s + getAgentAutomation(a), 0)
    const hours = Math.round(totalRate / agents.length * 0.12 * agents.length)
    return isNaN(hours) ? '—' : `~${hours} hrs`
  }, [agents])

  // ── Empty states ──
  if (!flow || !flow.steps?.length) {
    return (
      <div className="flex-1 flex items-center justify-center min-h-0">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl flex items-center justify-center text-2xl" style={{ background: 'rgba(4,65,89,0.06)' }}>🧠</div>
          <h3 className="text-lg font-semibold mb-2" style={{ color: '#1D1D1F' }}>Intelligence Layer</h3>
          <p className="text-sm mb-6" style={{ color: '#7B7B7B' }}>Generate your Solution Flow first. The intelligence layer will visualize your AI agents and their capabilities.</p>
        </div>
      </div>
    )
  }

  // Loading state (derivation path only)
  if (!isDbBacked && stepDetails.size === 0 && !dbData) {
    return (
      <div className="flex-1 flex items-center justify-center min-h-0">
        <div className="flex items-center gap-2">
          <div className="animate-spin rounded-full h-5 w-5 border-2 border-[#3FAF7A] border-t-transparent" />
          <span className="text-sm" style={{ color: '#7B7B7B' }}>Analyzing intelligence architecture...</span>
        </div>
      </div>
    )
  }

  // No DB agents and not enough derived agents — show generate CTA
  if (!isDbBacked && !hasMinimumAgents && stepDetails.size > 0) {
    return (
      <div className="flex-1 flex items-center justify-center min-h-0">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl flex items-center justify-center text-2xl" style={{ background: 'rgba(4,65,89,0.06)' }}>🧠</div>
          <h3 className="text-lg font-semibold mb-2" style={{ color: '#1D1D1F' }}>Build Your Intelligence Layer</h3>
          <p className="text-sm mb-5" style={{ color: '#7B7B7B' }}>
            Your solution has AI capabilities ready to be configured. Build the intelligence layer to create agents with tools, autonomy levels, and human partners.
          </p>
          <button
            onClick={handleGenerate}
            disabled={isGenerating}
            className="px-5 py-2.5 rounded-lg text-sm font-semibold text-white transition-all inline-flex items-center gap-2"
            style={{ background: isGenerating ? '#A0AEC0' : '#3FAF7A' }}
          >
            {isGenerating ? (
              <><span className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" /> Building agents...</>
            ) : (
              <><span>🧠</span> Build Intelligence Layer</>
            )}
          </button>
        </div>
      </div>
    )
  }

  // No DB agents but has derived — show canvas with build CTA in header
  const showBuildCta = !isDbBacked && hasMinimumAgents

  const canvasWidth = Math.max(totalWidth + 80, 800)
  const canvasHeight = Math.max(520, totalHeight + 60)

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 px-8 pt-4 pb-3" style={{ background: '#0A1E2F' }}>
        <div className="flex items-start gap-6 mb-3">
          <div className="flex-1 max-w-[720px]">
            <p className="text-[15px] font-normal leading-relaxed" style={{ color: 'rgba(255,255,255,0.82)' }}>
              <em className="not-italic font-medium" style={{ color: '#3FAF7A' }}>Intelligence Layer</em>: {agentCount} AI agents
              {isDbBacked && <> — <em className="not-italic font-medium" style={{ color: '#3FAF7A' }}>{validatedCount}/{agentCount} validated</em></>}
              {!isDbBacked && <> — <em className="not-italic font-medium" style={{ color: '#3FAF7A' }}>{avgAutomation}% automated</em></>}
            </p>
          </div>

          <div className="flex gap-3 flex-shrink-0">
            <div className="flex flex-col items-center px-3.5 py-1.5 rounded-lg" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}>
              <span className="text-[17px] font-bold leading-tight" style={{ color: '#3FAF7A' }}>{agentCount}</span>
              <span className="text-[9px] uppercase tracking-wide font-medium" style={{ color: 'rgba(255,255,255,0.35)' }}>Agents</span>
            </div>
            {isDbBacked && (
              <div className="flex flex-col items-center px-3.5 py-1.5 rounded-lg" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}>
                <span className="text-[17px] font-bold leading-tight" style={{ color: '#3FAF7A' }}>{validatedCount}</span>
                <span className="text-[9px] uppercase tracking-wide font-medium" style={{ color: 'rgba(255,255,255,0.35)' }}>Validated</span>
              </div>
            )}
            <div className="flex flex-col items-center px-3.5 py-1.5 rounded-lg" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}>
              <span className="text-[17px] font-bold leading-tight" style={{ color: '#3FAF7A' }}>{estTimeSaved}</span>
              <span className="text-[9px] uppercase tracking-wide font-medium" style={{ color: 'rgba(255,255,255,0.35)' }}>Saved / Day</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Persona filters */}
          <div className="flex gap-1.5 flex-1">
            {personaList.map((p, i) => (
              <button
                key={p.name}
                onClick={() => setActivePersona(prev => prev === i ? null : i)}
                className="flex items-center gap-1.5 py-0.5 pl-0.5 pr-2.5 rounded-full text-[11px] font-medium transition-all"
                style={{
                  border: `1px solid ${activePersona === i ? p.color : 'rgba(255,255,255,0.1)'}`,
                  background: activePersona === i ? 'rgba(255,255,255,0.08)' : 'transparent',
                  color: activePersona === i ? '#fff' : 'rgba(255,255,255,0.55)',
                }}
              >
                <div className="w-5 h-5 rounded-full flex items-center justify-center text-[8px] font-bold text-white flex-shrink-0" style={{ background: p.color }}>{p.initials}</div>
                {p.name.split(' ')[0]}
              </button>
            ))}
          </div>

          {showBuildCta && (
            <button
              onClick={handleGenerate}
              disabled={isGenerating}
              className="px-4 py-1.5 rounded-lg text-[11px] font-semibold transition-all"
              style={{ border: '1px solid rgba(63,175,122,0.35)', background: 'rgba(63,175,122,0.08)', color: '#3FAF7A' }}
            >
              {isGenerating ? 'Building...' : '🧠 Build Intelligence Layer'}
            </button>
          )}

          <button
            onClick={() => setPresentMode(true)}
            className="px-4 py-1.5 rounded-lg text-[11px] font-semibold transition-all"
            style={{ border: '1px solid rgba(63,175,122,0.35)', background: 'rgba(63,175,122,0.08)', color: '#3FAF7A' }}
          >
            Present
          </button>
        </div>
      </div>

      {/* Canvas */}
      <div className="flex-1 overflow-auto relative">
        <div className="relative" style={{ minWidth: canvasWidth, minHeight: canvasHeight, padding: '20px 0' }}>
          <div className="absolute inset-0 pointer-events-none" style={{ background: 'linear-gradient(135deg, #FAFAFA 0%, rgba(4,65,89,0.015) 30%, rgba(63,175,122,0.02) 60%, rgba(4,65,89,0.025) 100%)' }} />

          {/* SVG edges */}
          <svg className="absolute inset-0 pointer-events-none z-[1] overflow-visible">
            <defs>
              <marker id="wbDepArrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                <path d="M 0 1 L 6 4 L 0 7 z" fill="rgba(63,175,122,0.35)" />
              </marker>
            </defs>
            {agents.map(agent =>
              getAgentFeeds(agent).map(targetId => {
                const from = positions.get(agent.id)
                const to = positions.get(targetId)
                if (!from || !to) return null
                const x1 = from.x + from.w, y1 = from.y + from.h / 2
                const x2 = to.x, y2 = to.y + to.h / 2
                const dx = x2 - x1
                const isActive = hoveredAgentId === agent.id || hoveredAgentId === targetId
                return (
                  <path
                    key={`dep-${agent.id}-${targetId}`}
                    d={`M${x1},${y1} C${x1 + dx * 0.4},${y1} ${x2 - dx * 0.4},${y2} ${x2},${y2}`}
                    fill="none"
                    stroke={isActive ? 'rgba(63,175,122,0.5)' : 'rgba(63,175,122,0.2)'}
                    strokeWidth={isActive ? 2 : 1.5}
                    strokeDasharray="6,4"
                    markerEnd="url(#wbDepArrow)"
                    className="transition-all duration-300"
                  />
                )
              })
            )}
          </svg>

          {/* Agent nodes */}
          {agents.map(agent => {
            const pos = positions.get(agent.id)
            if (!pos) return null
            const item = layoutItems.find(li => li.id === agent.id)
            const weight = item?.weight ?? 0
            const partners = getAgentPartners(agent)
            const isDimmed = hoveredAgentId
              ? !connectedIds.has(agent.id)
              : isPersonaFiltered
                ? !partners.includes(personaList[activePersona!]?.name)
                : false
            const isConnected = hoveredAgentId ? connectedIds.has(agent.id) && agent.id !== hoveredAgentId : false

            return (
              <WorkbenchNode
                key={agent.id}
                agent={agent}
                position={pos}
                sizeClass={getSizeClass(weight, agent.id === heroId)}
                isSelected={agent.id === activeAgentId}
                isDimmed={isDimmed}
                isConnected={isConnected}
                onClick={() => setActiveAgentId(agent.id)}
                onHover={(id) => setHoveredAgentId(id)}
              />
            )
          })}
        </div>
      </div>

      {/* Detail Panel */}
      {activeAgent && (
        <WorkbenchDetailPanel
          agent={activeAgent}
          agents={agents}
          projectId={projectId}
          onClose={() => setActiveAgentId(null)}
          onAgentValidated={() => refreshAgents()}
        />
      )}

      {/* Present Mode */}
      <AIPresentMode
        isOpen={presentMode}
        onClose={() => setPresentMode(false)}
        agents={agents as DerivedAgent[]}
        personas={personas}
        avgAutomation={avgAutomation}
        estTimeSaved={estTimeSaved}
      />
    </div>
  )
}
