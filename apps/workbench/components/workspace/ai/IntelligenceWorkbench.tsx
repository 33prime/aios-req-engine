'use client'

/**
 * IntelligenceWorkbench — Hierarchical Intelligence Layer view.
 *
 * Replaces the flat DAG canvas with a vertical list of OrchestratorCards.
 * Each orchestrator expands to show sub-agents (AI) and tools (rules).
 * Clicking a sub-agent opens the detail panel with Profile | Chat | Try It.
 *
 * Data sources:
 * 1. DB-backed agents (from /intelligence-layer/agents) — preferred
 * 2. Derived agents (from useAgentDerivation) — fallback (rendered as legacy cards)
 *
 * Shows "Build Intelligence Layer" CTA when no DB agents exist.
 */

import { useState, useMemo, useCallback, useEffect } from 'react'
import useSWR from 'swr'
import {
  Layers, Sparkles, Wrench, Bot, Zap, BookOpen,
} from 'lucide-react'
import type {
  SolutionFlowOverview,
  SolutionFlowStepDetail,
  PersonaSummary,
  DerivedAgent,
  IntelLayerAgent,
  IntelLayerResponse,
  IntelArchitecture,
} from '@/types/workspace'
import { useAgentDerivation } from '@/hooks/useAgentDerivation'
import { getSolutionFlowStep } from '@/lib/api/admin'
import { getIntelligenceAgents, generateIntelligenceLayer } from '@/lib/api/intel-layer'
import { OrchestratorCard } from './OrchestratorCard'
import { IntelligenceArchitecture } from './IntelligenceArchitecture'
import { WorkbenchDetailPanel } from './WorkbenchDetailPanel'
import { AIPresentMode } from './AIPresentMode'

type AgentLike = DerivedAgent | IntelLayerAgent

interface IntelligenceWorkbenchProps {
  projectId: string
  flow: SolutionFlowOverview | null | undefined
  personas: PersonaSummary[]
}

export function IntelligenceWorkbench({ projectId, flow, personas }: IntelligenceWorkbenchProps) {
  const [expandedOrchId, setExpandedOrchId] = useState<string | null>(null)
  const [activeSubAgent, setActiveSubAgent] = useState<IntelLayerAgent | null>(null)
  const [presentMode, setPresentMode] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)

  // ── DB agents (hierarchical) ──
  const { data: dbData, mutate: refreshAgents } = useSWR<IntelLayerResponse>(
    projectId ? `intel-layer-${projectId}` : null,
    () => getIntelligenceAgents(projectId),
    { revalidateOnFocus: false }
  )
  const topLevelAgents = dbData?.agents ?? []
  const architecture = dbData?.architecture ?? null
  const isDbBacked = topLevelAgents.length > 0

  // ── Derived agents (fallback for projects not yet generated) ──
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

  const {
    agents: derivedAgents,
    agentCount: derivedCount,
    hasMinimumAgents,
  } = useAgentDerivation(flow, stepDetails)

  // ── Stats ──
  const stats = useMemo(() => {
    if (!isDbBacked) return { orchestrators: 0, subAgents: 0, tools: 0, validated: 0 }

    let subAgents = 0
    let tools = 0
    let validated = 0

    for (const orch of topLevelAgents) {
      const subs = orch.sub_agents || []
      subAgents += subs.length
      tools += (orch.tools || []).length
      for (const sub of subs) {
        tools += (sub.tools || []).length
        if (sub.validation_status === 'validated') validated++
      }
    }

    // Count knowledge items from architecture
    let knowledge = 0
    if (architecture) {
      knowledge += (architecture.knowledge_systems?.items?.length || 0)
    }

    return {
      orchestrators: topLevelAgents.length,
      subAgents,
      tools,
      validated,
      knowledge,
    }
  }, [topLevelAgents, isDbBacked, architecture])

  // ── Intelligence profile (AI% / Rules% / Data%) ──
  const profile = useMemo(() => {
    if (!isDbBacked || !topLevelAgents.length) return { ai: 0, rules: 0, data: 0 }

    let totalSubAgents = 0
    let totalTools = 0
    let totalDataSources = 0

    for (const orch of topLevelAgents) {
      totalSubAgents += (orch.sub_agents || []).length
      totalTools += (orch.tools || []).length
      totalDataSources += (orch.data_sources || []).length
      for (const sub of orch.sub_agents || []) {
        totalDataSources += (sub.data_sources || []).length
      }
    }

    const total = totalSubAgents + totalTools + Math.ceil(totalDataSources / 3)
    if (total === 0) return { ai: 33, rules: 34, data: 33 }

    const ai = Math.round((totalSubAgents / total) * 100)
    const data = Math.round((Math.ceil(totalDataSources / 3) / total) * 100)
    const rules = 100 - ai - data

    return { ai, rules: Math.max(rules, 0), data }
  }, [topLevelAgents, isDbBacked])

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

  // ── All sub-agents for the detail panel ──
  const allSubAgents = useMemo(() => {
    const subs: IntelLayerAgent[] = []
    for (const orch of topLevelAgents) {
      for (const sub of orch.sub_agents || []) {
        subs.push(sub)
      }
    }
    return subs
  }, [topLevelAgents])

  // ── No flow? ──
  if (!flow?.steps?.length) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center px-6">
          <div className="w-14 h-14 rounded-2xl mx-auto mb-3 flex items-center justify-center" style={{ background: 'rgba(4,65,89,0.06)' }}>
            <Layers size={22} className="text-[#044159]" />
          </div>
          <p className="text-[14px] font-semibold text-[#0A1E2F] mb-1">Intelligence Layer</p>
          <p className="text-[12px] text-[#718096]">Generate your Solution Flow first to discover the intelligence your product needs.</p>
        </div>
      </div>
    )
  }

  // ── No DB agents, show generate CTA ──
  if (!isDbBacked && !isGenerating) {
    return (
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="px-5 py-4" style={{ background: '#0A1E2F' }}>
          <p className="text-[14px] font-bold text-white">Intelligence Layer</p>
          <p className="text-[11px] text-white/40 mt-1">
            {derivedCount > 0
              ? `${derivedCount} capabilities identified from your solution flow. Build the intelligence layer to explore them.`
              : 'Analyze your solution flow to identify the intelligence your product needs.'}
          </p>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center px-6">
            <div className="w-14 h-14 rounded-2xl mx-auto mb-3 flex items-center justify-center" style={{ background: 'rgba(63,175,122,0.08)' }}>
              <Sparkles size={22} className="text-[#3FAF7A]" />
            </div>
            <p className="text-[14px] font-semibold text-[#0A1E2F] mb-1">Build Your Intelligence Layer</p>
            <p className="text-[12px] text-[#718096] mb-4 max-w-xs">
              Identify the agents, tools, and knowledge that make your product smart — and what&apos;s genuinely AI vs what&apos;s rules.
            </p>
            <button
              onClick={handleGenerate}
              disabled={!hasMinimumAgents}
              className="px-5 py-2 rounded-lg text-[12px] font-semibold text-white transition-all"
              style={{ background: hasMinimumAgents ? '#3FAF7A' : '#A0AEC0' }}
            >
              Build Intelligence Layer
            </button>
          </div>
        </div>
      </div>
    )
  }

  // ── Generating ──
  if (isGenerating) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="w-6 h-6 rounded-full border-2 border-[#3FAF7A] border-t-transparent animate-spin mx-auto mb-3" />
          <p className="text-[13px] font-semibold text-[#0A1E2F]">Building intelligence layer...</p>
          <p className="text-[11px] text-[#718096] mt-1">Analyzing solution flow, identifying agents and tools</p>
        </div>
      </div>
    )
  }

  // ── Main view ──
  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
      {/* ── Header (white bg, matches playground v3) ── */}
      <div className="px-6 pt-5 pb-4 flex-shrink-0 bg-white" style={{ borderBottom: '1px solid rgba(10,30,47,0.08)' }}>
        <div className="flex items-start justify-between mb-3">
          <div>
            <p className="text-[17px] font-bold text-[#0A1E2F]" style={{ letterSpacing: '-0.02em' }}>
              Intelligence Layer
            </p>
            <p className="text-[11px] text-[#718096] mt-1 max-w-lg leading-relaxed">
              Understand the knowledge, rules, and capabilities needed to deliver every desired outcome in the simplest way possible.
            </p>
          </div>
          <div className="flex gap-1.5">
            {[
              { value: stats.orchestrators, label: 'Agents' },
              { value: stats.subAgents, label: 'AI' },
              { value: stats.tools, label: 'Tools' },
              { value: stats.knowledge, label: 'Knowledge' },
            ].map(s => (
              <div
                key={s.label}
                className="px-3 py-1.5 rounded-md text-center"
                style={{ border: '1px solid rgba(10,30,47,0.08)' }}
              >
                <p className="text-[15px] font-bold text-[#0A1E2F]">{s.value}</p>
                <p className="text-[8px] font-semibold text-[#A0AEC0] uppercase tracking-wider">{s.label}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Intelligence Profile bar */}
        <div className="flex items-center gap-3">
          <span className="text-[9px] font-semibold text-[#A0AEC0] uppercase tracking-wider">
            Intelligence Profile
          </span>
          <div className="flex-1 h-[5px] rounded-full flex overflow-hidden" style={{ background: 'rgba(10,30,47,0.06)' }}>
            <div className="h-full transition-all duration-500" style={{ width: `${profile.ai}%`, background: '#3FAF7A' }} />
            <div className="h-full transition-all duration-500" style={{ width: `${profile.rules}%`, background: '#044159' }} />
            <div className="h-full transition-all duration-500" style={{ width: `${profile.data}%`, background: 'rgba(10,30,47,0.20)' }} />
          </div>
          <div className="flex gap-3">
            {[
              { pct: profile.ai, label: 'AI', color: '#3FAF7A' },
              { pct: profile.rules, label: 'Rules', color: '#044159' },
              { pct: profile.data, label: 'Data', color: 'rgba(10,30,47,0.25)' },
            ].map(p => (
              <span key={p.label} className="flex items-center gap-1 text-[10px] font-semibold text-[#4A5568]">
                <span className="w-[5px] h-[5px] rounded-full" style={{ background: p.color }} />
                {p.pct}% {p.label}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* ── Scrollable Content ── */}
      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5" style={{ background: '#FAFBFC' }}>

        {/* ── Section 1: Intelligence Architecture ── */}
        {architecture && (
          <>
            <div className="flex items-center gap-2">
              <div className="w-5 h-5 rounded-full bg-[#0A1E2F] flex items-center justify-center">
                <span className="text-[10px] font-bold text-white">1</span>
              </div>
              <span className="text-[13px] font-bold text-[#0A1E2F]">Intelligence Architecture</span>
            </div>
            <IntelligenceArchitecture architecture={architecture} />
          </>
        )}

        {/* ── Section 2: Agents ── */}
        <div className="flex items-center gap-2 justify-between">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded-full bg-[#0A1E2F] flex items-center justify-center">
              <span className="text-[10px] font-bold text-white">{architecture ? '2' : '1'}</span>
            </div>
            <span className="text-[13px] font-bold text-[#0A1E2F]">Agents</span>
          </div>
          <span className="text-[11px] text-[#718096]">What orchestrates the intelligence</span>
        </div>

        <div className="space-y-3">
          {topLevelAgents.map(agent => (
            <OrchestratorCard
              key={agent.id}
              agent={agent}
              projectId={projectId}
              isExpanded={expandedOrchId === agent.id}
              onToggle={() => setExpandedOrchId(prev => prev === agent.id ? null : agent.id)}
              onSubAgentClick={(sub) => setActiveSubAgent(sub)}
            />
          ))}
        </div>

        {/* Regenerate CTA */}
        <div className="pt-2 pb-4 flex justify-center">
          <button
            onClick={handleGenerate}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[10px] font-medium transition-all"
            style={{
              color: '#3FAF7A',
              background: 'rgba(63,175,122,0.06)',
              border: '1px solid rgba(63,175,122,0.15)',
            }}
          >
            <Zap size={10} />
            Regenerate Intelligence Layer
          </button>
        </div>
      </div>

      {/* ── Sub-Agent Detail Panel ── */}
      {activeSubAgent && (
        <WorkbenchDetailPanel
          agent={activeSubAgent}
          agents={allSubAgents}
          projectId={projectId}
          onClose={() => setActiveSubAgent(null)}
          onAgentValidated={() => refreshAgents()}
        />
      )}

      {/* ── Present Mode ── */}
      {presentMode && (
        <AIPresentMode
          isOpen={presentMode}
          onClose={() => setPresentMode(false)}
          agents={derivedAgents}
          personas={personas}
          avgAutomation={derivedAgents.length ? Math.round(derivedAgents.reduce((s, a) => s + a.automationRate, 0) / derivedAgents.length) : 0}
          estTimeSaved={derivedAgents.length ? `${Math.round(derivedAgents.length * 0.5)}h` : '0h'}
        />
      )}
    </div>
  )
}
