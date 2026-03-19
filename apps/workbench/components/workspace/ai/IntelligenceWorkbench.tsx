'use client'

/**
 * IntelligenceWorkbench — Architect-mode intelligence architecture view.
 *
 * Replaces AIAgentsView. Agent DAG canvas with dependency edges.
 * Features: SVG edge rendering, hover highlighting, detail panel with Try It,
 * chat modal (opens to the left of panel, like Solution Flow preview).
 * Architect mode only — no client/build mode switcher.
 */

import { useState, useMemo, useCallback, useEffect } from 'react'
import type {
  SolutionFlowOverview,
  SolutionFlowStepDetail,
  PersonaSummary,
  DerivedAgent,
} from '@/types/workspace'
import { useWeightedLayout, getSizeClass, type LayoutItem } from '@/hooks/useWeightedLayout'
import { useAgentDerivation } from '@/hooks/useAgentDerivation'
import { getSolutionFlowStep } from '@/lib/api/admin'
import { WorkbenchNode } from './WorkbenchNode'
import { WorkbenchDetailPanel } from './WorkbenchDetailPanel'
import { AIPresentMode } from './AIPresentMode'

interface IntelligenceWorkbenchProps {
  projectId: string
  flow: SolutionFlowOverview | null | undefined
  personas: PersonaSummary[]
}

function calcAgentWeight(agent: DerivedAgent): number {
  return (
    agent.dataNeeds.length * 8 +
    agent.produces.length * 6 +
    agent.humanPartners.length * 10 +
    agent.feedsAgentIds.length * 12 +
    (agent.transform.before !== 'Manual process' ? 10 : 0) +
    Math.round(agent.automationRate * 0.3)
  )
}

function getPersonaColor(name: string): string {
  const palette = ['#3FAF7A', '#044159', '#2D6B4A', '#0A1E2F']
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
  return palette[Math.abs(hash) % palette.length]
}

export function IntelligenceWorkbench({ projectId, flow, personas }: IntelligenceWorkbenchProps) {
  const [activeAgentId, setActiveAgentId] = useState<string | null>(null)
  const [hoveredAgentId, setHoveredAgentId] = useState<string | null>(null)
  const [activePersona, setActivePersona] = useState<number | null>(null)
  const [presentMode, setPresentMode] = useState(false)

  // Fetch step details for agent derivation
  const [stepDetails, setStepDetails] = useState<Map<string, SolutionFlowStepDetail>>(new Map())
  const [detailsFetched, setDetailsFetched] = useState(false)

  useEffect(() => {
    if (!flow?.steps?.length || detailsFetched) return
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
  }, [flow, projectId, detailsFetched])

  const { agents, agentCount, avgAutomation, hasMinimumAgents } = useAgentDerivation(flow, stepDetails)

  // DAG layout computation
  const layoutItems: LayoutItem[] = useMemo(() => {
    if (!agents.length) return []

    const depthMap = new Map<string, number>()
    const rowInCol = new Map<number, number>()

    function getDepth(agent: DerivedAgent, visited = new Set<string>()): number {
      if (depthMap.has(agent.id)) return depthMap.get(agent.id)!
      if (visited.has(agent.id)) return 0
      visited.add(agent.id)

      if (!agent.dependsOnAgentIds.length) {
        depthMap.set(agent.id, 0)
        return 0
      }

      const maxParentDepth = Math.max(
        ...agent.dependsOnAgentIds.map(depId => {
          const parent = agents.find(a => a.id === depId)
          return parent ? getDepth(parent, visited) : -1
        })
      )
      const depth = maxParentDepth + 1
      depthMap.set(agent.id, depth)
      return depth
    }

    agents.forEach(a => getDepth(a))

    return agents.map(agent => {
      const col = depthMap.get(agent.id) || 0
      const row = rowInCol.get(col) || 0
      rowInCol.set(col, row + 1)
      return {
        id: agent.id,
        weight: calcAgentWeight(agent),
        column: col,
        row,
      }
    })
  }, [agents])

  const { positions, totalWidth, totalHeight, heroId } = useWeightedLayout(layoutItems)

  const activeAgent = agents.find(a => a.id === activeAgentId) || null
  const isPersonaFiltered = activePersona !== null

  // Connected agents for hover highlighting
  const connectedIds = useMemo(() => {
    if (!hoveredAgentId) return new Set<string>()
    const hovered = agents.find(a => a.id === hoveredAgentId)
    if (!hovered) return new Set<string>()
    const connected = new Set([hoveredAgentId])
    hovered.feedsAgentIds.forEach(id => connected.add(id))
    hovered.dependsOnAgentIds.forEach(id => connected.add(id))
    return connected
  }, [hoveredAgentId, agents])

  // Unique personas from agents
  const personaList = useMemo(() => {
    const seen = new Set<string>()
    const list: { name: string; color: string; initials: string }[] = []
    agents.forEach(a => {
      a.humanPartners.forEach(name => {
        if (!seen.has(name)) {
          seen.add(name)
          list.push({
            name,
            color: getPersonaColor(name),
            initials: name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase(),
          })
        }
      })
    })
    return list
  }, [agents])

  const togglePersona = useCallback((index: number) => {
    setActivePersona(prev => prev === index ? null : index)
  }, [])

  const estTimeSaved = useMemo(() => {
    const totalRate = agents.reduce((s, a) => s + a.automationRate, 0)
    const hours = Math.round(totalRate / agents.length * 0.12 * agents.length)
    return isNaN(hours) ? '—' : `~${hours} hrs`
  }, [agents])

  // Technique distribution
  const techniqueBreakdown = useMemo(() => {
    const counts: Record<string, number> = {}
    agents.forEach(a => {
      const t = a.technique || 'llm'
      counts[t] = (counts[t] || 0) + 1
    })
    return counts
  }, [agents])

  // Empty states
  if (!flow || !flow.steps?.length) {
    return (
      <div className="flex-1 flex items-center justify-center min-h-0">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl flex items-center justify-center text-2xl" style={{ background: 'rgba(4,65,89,0.06)' }}>
            🧠
          </div>
          <h3 className="text-lg font-semibold mb-2" style={{ color: '#1D1D1F' }}>
            Intelligence Workbench
          </h3>
          <p className="text-sm mb-6" style={{ color: '#7B7B7B' }}>
            Generate your Solution Flow first. The workbench will visualize your AI architecture — processing agents and their dependencies.
          </p>
        </div>
      </div>
    )
  }

  if (!hasMinimumAgents && stepDetails.size > 0) {
    return (
      <div className="flex-1 flex items-center justify-center min-h-0">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl flex items-center justify-center text-2xl" style={{ background: 'rgba(4,65,89,0.06)' }}>
            🧠
          </div>
          <h3 className="text-lg font-semibold mb-2" style={{ color: '#1D1D1F' }}>
            Intelligence Architecture Forming
          </h3>
          <p className="text-sm mb-2" style={{ color: '#7B7B7B' }}>
            Your solution has {agentCount} AI touchpoint{agentCount !== 1 ? 's' : ''} — not enough to visualize as a pipeline yet.
          </p>
          <p className="text-sm" style={{ color: '#999' }}>
            As your solution grows with more AI capabilities, the workbench will appear.
          </p>
        </div>
      </div>
    )
  }

  if (stepDetails.size === 0) {
    return (
      <div className="flex-1 flex items-center justify-center min-h-0">
        <div className="flex items-center gap-2">
          <div className="animate-spin rounded-full h-5 w-5 border-2 border-[#3FAF7A] border-t-transparent" />
          <span className="text-sm" style={{ color: '#7B7B7B' }}>Analyzing intelligence architecture...</span>
        </div>
      </div>
    )
  }

  const canvasWidth = Math.max(totalWidth + 80, 800)
  const canvasHeight = Math.max(520, totalHeight + 60)

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 px-8 pt-4 pb-3" style={{ background: '#0A1E2F' }}>
        <div className="flex items-start gap-6 mb-3">
          <div className="flex-1 max-w-[720px]">
            <p className="text-[15px] font-normal leading-relaxed" style={{ color: 'rgba(255,255,255,0.82)' }}>
              <em className="not-italic font-medium" style={{ color: '#3FAF7A' }}>Intelligence Architecture</em>: {agentCount} AI agents — <em className="not-italic font-medium" style={{ color: '#3FAF7A' }}>{avgAutomation}% automated</em>.
            </p>
          </div>

          <div className="flex gap-3 flex-shrink-0">
            <div className="flex flex-col items-center px-3.5 py-1.5 rounded-lg" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}>
              <span className="text-[17px] font-bold leading-tight" style={{ color: '#3FAF7A' }}>{agentCount}</span>
              <span className="text-[9px] uppercase tracking-wide font-medium" style={{ color: 'rgba(255,255,255,0.35)' }}>Agents</span>
            </div>
            <div className="flex flex-col items-center px-3.5 py-1.5 rounded-lg" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}>
              <span className="text-[17px] font-bold leading-tight" style={{ color: '#3FAF7A' }}>{avgAutomation}%</span>
              <span className="text-[9px] uppercase tracking-wide font-medium" style={{ color: 'rgba(255,255,255,0.35)' }}>Automated</span>
            </div>
            <div className="flex flex-col items-center px-3.5 py-1.5 rounded-lg" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}>
              <span className="text-[17px] font-bold leading-tight" style={{ color: '#3FAF7A' }}>{estTimeSaved}</span>
              <span className="text-[9px] uppercase tracking-wide font-medium" style={{ color: 'rgba(255,255,255,0.35)' }}>Saved / Day</span>
            </div>
          </div>
        </div>

        {/* Bottom row: technique pills + personas + present */}
        <div className="flex items-center gap-4">
          {/* Technique breakdown */}
          <div className="flex gap-1.5">
            {Object.entries(techniqueBreakdown).map(([tech, count]) => (
              <span
                key={tech}
                className="px-2 py-0.5 rounded text-[10px] font-medium"
                style={{
                  background: 'rgba(255,255,255,0.06)',
                  color: 'rgba(255,255,255,0.5)',
                  border: '1px solid rgba(255,255,255,0.08)',
                }}
              >
                {tech} × {count}
              </span>
            ))}
          </div>

          <div className="w-px h-4 mx-1" style={{ background: 'rgba(255,255,255,0.12)' }} />

          {/* Persona filters */}
          <div className="flex gap-1.5 flex-1">
            {personaList.map((p, i) => (
              <button
                key={p.name}
                onClick={() => togglePersona(i)}
                className="flex items-center gap-1.5 py-0.5 pl-0.5 pr-2.5 rounded-full text-[11px] font-medium transition-all"
                style={{
                  border: `1px solid ${activePersona === i ? p.color : 'rgba(255,255,255,0.1)'}`,
                  background: activePersona === i ? 'rgba(255,255,255,0.08)' : 'transparent',
                  color: activePersona === i ? '#fff' : 'rgba(255,255,255,0.55)',
                }}
              >
                <div
                  className="w-5 h-5 rounded-full flex items-center justify-center text-[8px] font-bold text-white flex-shrink-0"
                  style={{ background: p.color }}
                >
                  {p.initials}
                </div>
                {p.name.split(' ')[0]}
              </button>
            ))}
          </div>

          <button
            onClick={() => setPresentMode(true)}
            className="px-4 py-1.5 rounded-lg text-[11px] font-semibold transition-all"
            style={{
              border: '1px solid rgba(63,175,122,0.35)',
              background: 'rgba(63,175,122,0.08)',
              color: '#3FAF7A',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = 'rgba(63,175,122,0.18)'
              e.currentTarget.style.borderColor = '#3FAF7A'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = 'rgba(63,175,122,0.08)'
              e.currentTarget.style.borderColor = 'rgba(63,175,122,0.35)'
            }}
          >
            Present
          </button>
        </div>
      </div>

      {/* Canvas */}
      <div className="flex-1 overflow-auto relative">
        <div
          className="relative"
          style={{ minWidth: canvasWidth, minHeight: canvasHeight, padding: '20px 0' }}
        >
          {/* Background gradient */}
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              background: 'linear-gradient(135deg, #FAFAFA 0%, rgba(4,65,89,0.015) 30%, rgba(63,175,122,0.02) 60%, rgba(4,65,89,0.025) 100%)',
            }}
          />

          {/* SVG agent-to-agent dependency edges */}
          <svg className="absolute inset-0 pointer-events-none z-[1] overflow-visible">
            <defs>
              <marker id="wbDepArrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                <path d="M 0 1 L 6 4 L 0 7 z" fill="rgba(63,175,122,0.35)" />
              </marker>
            </defs>
            {agents.map(agent =>
              agent.feedsAgentIds.map(targetId => {
                const from = positions.get(agent.id)
                const to = positions.get(targetId)
                if (!from || !to) return null
                const x1 = from.x + from.w
                const y1 = from.y + from.h / 2
                const x2 = to.x
                const y2 = to.y + to.h / 2
                const dx = x2 - x1
                const cx1 = x1 + dx * 0.4
                const cx2 = x2 - dx * 0.4
                const isActive = hoveredAgentId === agent.id || hoveredAgentId === targetId
                return (
                  <path
                    key={`dep-${agent.id}-${targetId}`}
                    d={`M${x1},${y1} C${cx1},${y1} ${cx2},${y2} ${x2},${y2}`}
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
            const isDimmed = hoveredAgentId
              ? !connectedIds.has(agent.id)
              : isPersonaFiltered
                ? !agent.humanPartners.includes(personaList[activePersona!]?.name)
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

      {/* Detail Panel (slide-in, replaces modal) */}
      {activeAgent && (
        <WorkbenchDetailPanel
          agent={activeAgent}
          agents={agents}
          projectId={projectId}
          onClose={() => setActiveAgentId(null)}
        />
      )}

      {/* Present Mode (keep existing) */}
      <AIPresentMode
        isOpen={presentMode}
        onClose={() => setPresentMode(false)}
        agents={agents}
        personas={personas}
        avgAutomation={avgAutomation}
        estTimeSaved={estTimeSaved}
      />
    </div>
  )
}
