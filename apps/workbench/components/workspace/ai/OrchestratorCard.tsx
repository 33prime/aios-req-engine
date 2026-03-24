'use client'

/**
 * OrchestratorCard — Expandable card for a goal-driven orchestrating agent.
 *
 * Collapsed: header (icon + name + goal + badge) → workflow chain
 * Expanded: 3 tabs — Sub-Agents & Tools | Talk to Agent | See in Action
 *
 * Sub-agents are clickable → opens detail panel with their own Profile | Chat | Try It
 * The orchestrator's direct tools use AgentToolCard (expandable).
 * Talk to Agent / See in Action operate on the orchestrator itself.
 */

import { useState, useMemo } from 'react'
import {
  Shield, Briefcase, Compass, Eye, Cpu, Bot,
  ChevronRight, ChevronDown,
  Tag, BarChart2, Clock, Lock, Map, PenLine,
  Activity, ListOrdered, CreditCard, ExternalLink,
  Search, FileText, Repeat, Target, CheckSquare,
  Link, Building2, Rocket, TrendingUp, AlertTriangle,
  MessageCircle, Sparkles, GitBranch,
} from 'lucide-react'
import type { IntelLayerAgent } from '@/types/workspace'
import { AgentToolCard } from './AgentToolCard'
import { AgentChatTab } from './AgentChatTab'
import { AgentTryItTab } from './AgentTryItTab'

// ── Icon mapping ──

function iconForAgent(agent: IntelLayerAgent): React.ElementType {
  const typeMap: Record<string, React.ElementType> = {
    orchestrator: Shield, classifier: Tag, matcher: Search,
    predictor: TrendingUp, watcher: Eye, generator: Sparkles,
    processor: Cpu,
  }
  return typeMap[agent.agent_type] || Shield
}

function iconForToolName(name: string): React.ElementType {
  const lower = name.toLowerCase()
  if (lower.includes('score') || lower.includes('rank') || lower.includes('completeness')) return BarChart2
  if (lower.includes('route') || lower.includes('router') || lower.includes('checklist') || lower.includes('engine')) return Map
  if (lower.includes('fresh') || lower.includes('stale') || lower.includes('monitor') || lower.includes('detect')) return Clock
  if (lower.includes('permission') || lower.includes('valid') || lower.includes('access') || lower.includes('guard')) return Lock
  if (lower.includes('card') || lower.includes('eac')) return CreditCard
  if (lower.includes('referral') || lower.includes('match')) return ExternalLink
  if (lower.includes('search') || lower.includes('find')) return Search
  if (lower.includes('draft') || lower.includes('outreach') || lower.includes('write')) return PenLine
  if (lower.includes('prior') || lower.includes('sort') || lower.includes('order')) return ListOrdered
  if (lower.includes('risk') || lower.includes('flag') || lower.includes('alert')) return AlertTriangle
  if (lower.includes('tier') || lower.includes('classify') || lower.includes('class')) return Target
  if (lower.includes('crm') || lower.includes('map') || lower.includes('sync')) return Link
  if (lower.includes('input') || lower.includes('valid')) return CheckSquare
  if (lower.includes('structure') || lower.includes('entity') || lower.includes('bar') || lower.includes('verif')) return Building2
  if (lower.includes('forecast') || lower.includes('revenue')) return TrendingUp
  if (lower.includes('plan') || lower.includes('assemble') || lower.includes('export') || lower.includes('handoff') || lower.includes('document')) return FileText
  if (lower.includes('nudge') || lower.includes('message') || lower.includes('chat')) return MessageCircle
  if (lower.includes('switch') || lower.includes('mode') || lower.includes('reconcil')) return Repeat
  if (lower.includes('audit') || lower.includes('log') || lower.includes('compliance')) return GitBranch
  if (lower.includes('portfolio') || lower.includes('aggregat')) return Activity
  return Cpu
}

// ── Badge ──

function getBadgeInfo(agent: IntelLayerAgent): { label: string; cls: string } {
  const subs = agent.sub_agents || []
  const hasAutonomous = subs.some(s => s.rhythm === 'always_on' || (s.autonomy_level ?? 0) > 70)
  const hasPeriodic = agent.rhythm === 'periodic' || subs.some(s => s.rhythm === 'periodic')

  if (hasAutonomous) return { label: 'Autonomous', cls: 'bg-[rgba(63,175,122,0.08)] text-[#1B6B3A] border-[rgba(63,175,122,0.15)]' }
  if (hasPeriodic) return { label: 'Periodic', cls: 'bg-[rgba(4,65,89,0.06)] text-[#044159] border-[rgba(4,65,89,0.10)]' }
  return { label: 'Orchestrator', cls: 'bg-[rgba(4,65,89,0.06)] text-[#044159] border-[rgba(4,65,89,0.10)]' }
}

// ── Props ──

type OrchestratorTab = 'inventory' | 'chat' | 'tryit'

interface Props {
  agent: IntelLayerAgent
  projectId: string
  isExpanded: boolean
  onToggle: () => void
  onSubAgentClick: (subAgent: IntelLayerAgent) => void
}

export function OrchestratorCard({ agent, projectId, isExpanded, onToggle, onSubAgentClick }: Props) {
  const [activeTab, setActiveTab] = useState<OrchestratorTab>('inventory')
  const [expandedToolId, setExpandedToolId] = useState<string | null>(null)

  const subAgents = agent.sub_agents || []
  const directTools = agent.tools || []
  const badge = getBadgeInfo(agent)
  const IconComponent = iconForAgent(agent)

  // Build workflow chain
  const workflowNodes = useMemo(() => {
    type WfNode = { id: string; name: string; type: 'sub_agent' | 'tool'; pills: string[]; agent?: IntelLayerAgent }
    const items: Array<{ order: number; node: WfNode }> = []

    for (const sub of subAgents) {
      const toolNames = (sub.tools || []).slice(0, 3).map(t => {
        const words = t.name.split(' ')
        return words.length > 2 ? words.slice(0, 2).join(' ') : t.name
      })
      items.push({
        order: sub.display_order ?? 50,
        node: { id: sub.id, name: sub.name, type: 'sub_agent', pills: toolNames.length > 0 ? toolNames : [sub.technique || 'AI'], agent: sub },
      })
    }

    for (const tool of directTools) {
      items.push({
        order: tool.display_order ?? 50,
        node: { id: tool.id, name: tool.name, type: 'tool', pills: tool.data_touches?.slice(0, 2) || [] },
      })
    }

    items.sort((a, b) => a.order - b.order)
    return items.map(i => i.node)
  }, [subAgents, directTools])

  return (
    <div
      className={`bg-white rounded-xl overflow-hidden transition-all duration-200 ${
        isExpanded
          ? 'border-[1.5px] border-[#3FAF7A] shadow-[0_4px_20px_rgba(63,175,122,0.10)]'
          : 'border-[1.5px] border-[rgba(10,30,47,0.08)] hover:border-[rgba(63,175,122,0.15)] hover:shadow-[0_4px_20px_rgba(63,175,122,0.08)]'
      }`}
    >
      {/* ── Header ── */}
      <div className="flex items-start gap-3 px-4 py-3.5 cursor-pointer" onClick={onToggle}>
        <div
          className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ background: 'rgba(63,175,122,0.08)', border: '1px solid rgba(63,175,122,0.15)' }}
        >
          <IconComponent size={18} className="text-[#3FAF7A]" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <p className="text-[14px] font-bold text-[#0A1E2F] truncate">{agent.name}</p>
            <span className={`px-2 py-0.5 rounded-md text-[8px] font-bold uppercase tracking-wide flex-shrink-0 border ${badge.cls}`}>
              {badge.label}
            </span>
          </div>
          <p className="text-[11px] text-[#718096] leading-relaxed line-clamp-2">{agent.role_description}</p>
        </div>
        <div className="flex-shrink-0 pt-1 text-[#A0AEC0]">
          {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </div>
      </div>

      {/* ── Workflow Chain ── */}
      <div className="px-4 pb-3">
        <div className="flex items-start overflow-x-auto pb-1" style={{ scrollbarWidth: 'thin' }}>
          {workflowNodes.map((node, i) => (
            <div key={node.id} className="flex items-start flex-shrink-0">
              <div
                className="rounded-md px-2.5 py-2 transition-all min-w-[105px] max-w-[135px] cursor-pointer hover:bg-[rgba(0,0,0,0.03)]"
                style={{ background: 'rgba(0,0,0,0.02)', border: '1px solid rgba(10,30,47,0.08)' }}
                onClick={(e) => {
                  e.stopPropagation()
                  if (node.type === 'sub_agent' && node.agent) onSubAgentClick(node.agent)
                }}
              >
                <p
                  className="text-[7px] font-bold uppercase tracking-wider mb-1"
                  style={{ color: node.type === 'sub_agent' ? '#3FAF7A' : '#044159' }}
                >
                  {node.type === 'sub_agent' ? 'Sub-Agent' : 'Tool'}
                </p>
                <p className="text-[9px] font-semibold text-[#0A1E2F] leading-snug mb-1.5 line-clamp-2">{node.name}</p>
                <div className="flex flex-wrap gap-1">
                  {node.pills.map((pill, j) => (
                    <span key={j} className="px-1.5 py-px rounded text-[7px] font-medium" style={{ background: 'rgba(0,0,0,0.03)', border: '1px solid rgba(10,30,47,0.06)', color: '#718096' }}>
                      {pill}
                    </span>
                  ))}
                </div>
              </div>
              {i < workflowNodes.length - 1 && (
                <div className="flex items-center px-1 text-[#A0AEC0]" style={{ marginTop: 16 }}>
                  <ChevronRight size={10} />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* ── Expanded Detail ── */}
      {isExpanded && (
        <div className="border-t border-[rgba(10,30,47,0.08)]">
          {/* Tabs */}
          <div className="px-4 pt-3 pb-0">
            <div className="flex gap-0 border-b border-[rgba(10,30,47,0.08)]">
              {([
                { id: 'inventory' as OrchestratorTab, label: 'Sub-Agents & Tools' },
                { id: 'chat' as OrchestratorTab, label: 'Talk to Agent' },
                { id: 'tryit' as OrchestratorTab, label: 'See in Action' },
              ]).map(tab => (
                <button
                  key={tab.id}
                  onClick={(e) => { e.stopPropagation(); setActiveTab(tab.id) }}
                  className="px-3 py-2 text-[11px] font-medium transition-all relative"
                  style={{
                    color: activeTab === tab.id ? '#0A1E2F' : '#A0AEC0',
                  }}
                >
                  {tab.label}
                  {activeTab === tab.id && (
                    <div className="absolute bottom-0 left-3 right-3 h-[2px] bg-[#3FAF7A] rounded-full" />
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Tab Content */}
          <div onClick={e => e.stopPropagation()}>
            {activeTab === 'inventory' && (
              <div className="px-4 py-3">
                {/* Sub-Agents */}
                {subAgents.length > 0 && (
                  <div className="mb-3">
                    <p className="text-[9px] font-bold uppercase tracking-wider text-[#A0AEC0] mb-2">
                      Sub-Agents (AI)
                    </p>
                    <div className="space-y-1.5">
                      {subAgents.map(sub => {
                        const SubIcon = iconForAgent(sub)
                        return (
                          <div
                            key={sub.id}
                            className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg cursor-pointer transition-all hover:bg-[rgba(63,175,122,0.04)]"
                            style={{ border: '1px solid rgba(10,30,47,0.08)', borderLeft: '2px solid #3FAF7A' }}
                            onClick={() => onSubAgentClick(sub)}
                          >
                            <SubIcon size={14} className="text-[#3FAF7A] flex-shrink-0" />
                            <div className="flex-1 min-w-0">
                              <p className="text-[11px] font-semibold text-[#0A1E2F]">{sub.name}</p>
                              <p className="text-[9px] text-[#718096] truncate">{sub.role_description}</p>
                            </div>
                            <span className="text-[7px] font-bold uppercase px-1.5 py-0.5 rounded bg-[rgba(63,175,122,0.08)] text-[#1B6B3A] flex-shrink-0">
                              AI
                            </span>
                            <ChevronRight size={12} className="text-[#A0AEC0] flex-shrink-0" />
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}

                {/* Direct Tools */}
                {directTools.length > 0 && (
                  <div>
                    <p className="text-[9px] font-bold uppercase tracking-wider text-[#A0AEC0] mb-2">
                      Tools
                    </p>
                    <div className="grid grid-cols-2 gap-1.5">
                      {directTools.map(tool => {
                        const ToolIcon = iconForToolName(tool.name)
                        // Use AgentToolCard for expandable detail
                        return (
                          <AgentToolCard
                            key={tool.id}
                            tool={{ ...tool, icon: tool.icon || '' }}
                            isExpanded={expandedToolId === tool.id}
                            onToggle={() => setExpandedToolId(prev => prev === tool.id ? null : tool.id)}
                          />
                        )
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'chat' && (
              <div style={{ height: 360 }}>
                <AgentChatTab agent={agent} projectId={projectId} />
              </div>
            )}

            {activeTab === 'tryit' && (
              <div style={{ height: 400 }}>
                <AgentTryItTab
                  agent={agent}
                  projectId={projectId}
                  onValidated={() => {}}
                />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
