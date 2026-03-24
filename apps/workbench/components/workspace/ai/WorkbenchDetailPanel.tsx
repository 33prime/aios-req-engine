'use client'

/**
 * WorkbenchDetailPanel — 3-tab slide-in panel for agents.
 *
 * For sub-agents (agent_role === 'sub_agent'):
 *   Tabs: Profile | Talk to {Name} | See in Action
 *   Uses existing AgentProfileTab, AgentChatTab, AgentTryItTab
 *
 * For orchestrators (agent_role === 'orchestrator'):
 *   Single overview tab (no chat, no try-it — orchestrators coordinate, they don't execute)
 *
 * For legacy peers (agent_role === 'peer' or DerivedAgent):
 *   Falls back to legacy rendering for backward compatibility
 */

import { useState, useEffect, useCallback } from 'react'
import type { DerivedAgent, IntelLayerAgent } from '@/types/workspace'

// DB-backed agent tab components
import { AgentProfileTab } from './AgentProfileTab'
import { AgentChatTab } from './AgentChatTab'
import { AgentTryItTab } from './AgentTryItTab'

// Legacy imports for derived agents
import { useChat, type ChatMessage } from '@/lib/useChat'
import { executeAgent, getAgentExample } from '@/lib/api/workspace'
import type { AgentExecuteResponse, AgentExampleResponse } from '@/types/workspace'
import { AgentOutputModal } from './AgentOutputModal'
import { ExampleInputCard } from './ExampleInputCard'
import { ProcessingAnimation } from './ProcessingAnimation'

type AgentLike = DerivedAgent | IntelLayerAgent
type TabId = 'profile' | 'chat' | 'tryit'

function isDbAgent(a: AgentLike): a is IntelLayerAgent {
  return 'tools' in a && 'autonomy_level' in a
}

interface Props {
  agent: AgentLike
  agents: AgentLike[]
  projectId: string
  onClose: () => void
  onAgentValidated?: () => void
  parentAgentName?: string
}

export function WorkbenchDetailPanel({ agent, agents, projectId, onClose, onAgentValidated, parentAgentName }: Props) {
  const [activeTab, setActiveTab] = useState<TabId>('profile')
  const db = isDbAgent(agent)
  const isOrchestrator = db && agent.agent_role === 'orchestrator'
  const isSubAgent = db && agent.agent_role === 'sub_agent'

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  // Reset tab when agent changes
  useEffect(() => { setActiveTab('profile') }, [agent.id])

  const name = agent.name
  const isValidated = db && agent.validation_status === 'validated'

  // Determine which tabs to show
  const tabs: Array<{ id: TabId; label: string }> = isOrchestrator
    ? [{ id: 'profile', label: 'Overview' }]
    : [
        { id: 'profile', label: 'Profile' },
        { id: 'chat', label: `Talk to ${name.split(' ')[0]}` },
        { id: 'tryit', label: 'See in Action' },
      ]

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed top-0 left-0 bottom-0 z-[190]"
        style={{ right: 520, background: 'rgba(10,30,47,0.15)' }}
        onClick={onClose}
      />

      {/* Panel */}
      <div
        className="fixed right-0 top-0 bottom-0 z-[210] flex flex-col bg-white shadow-2xl"
        style={{ width: 520, maxWidth: '95vw' }}
      >
        {/* Header */}
        <div className="flex items-center gap-3 px-5 py-3 flex-shrink-0" style={{ borderBottom: '1px solid rgba(10,30,47,0.08)' }}>
          <button onClick={onClose} className="p-1 rounded-md hover:bg-[rgba(0,0,0,0.04)] transition-colors text-[#A0AEC0] flex-shrink-0">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5"><line x1="1" y1="1" x2="13" y2="13"/><line x1="13" y1="1" x2="1" y2="13"/></svg>
          </button>

          <div className="flex-1 min-w-0">
            {/* Breadcrumb for sub-agents */}
            {isSubAgent && parentAgentName && (
              <p className="text-[9px] text-[#A0AEC0] font-medium truncate mb-0.5">
                Part of {parentAgentName}
              </p>
            )}
            <div className="flex items-center gap-2">
              <p className="text-[13px] font-semibold text-[#0A1E2F] truncate">{name}</p>
              {isValidated && (
                <div className="w-4 h-4 rounded-full flex items-center justify-center text-[8px] text-white flex-shrink-0" style={{ background: '#3FAF7A' }}>&#x2713;</div>
              )}
              {isSubAgent && (
                <span className="text-[7px] font-bold uppercase px-1.5 py-px rounded bg-[rgba(63,175,122,0.08)] text-[#1B6B3A] flex-shrink-0">AI</span>
              )}
            </div>
          </div>

          {/* Tabs */}
          <div className="flex items-center gap-0.5 ml-auto rounded-lg p-0.5 flex-shrink-0" style={{ background: 'rgba(10,30,47,0.04)' }}>
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className="px-2.5 py-1 rounded-md text-[10px] font-medium transition-all"
                style={{
                  background: activeTab === tab.id ? '#fff' : 'transparent',
                  color: activeTab === tab.id ? '#0A1E2F' : '#A0AEC0',
                  boxShadow: activeTab === tab.id ? '0 1px 2px rgba(0,0,0,0.06)' : 'none',
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-hidden min-h-0">
          {db ? (
            <>
              {activeTab === 'profile' && (
                <div className="h-full overflow-y-auto">
                  <AgentProfileTab agent={agent} agents={agents as IntelLayerAgent[]} />
                </div>
              )}
              {activeTab === 'chat' && !isOrchestrator && (
                <AgentChatTab agent={agent} projectId={projectId} />
              )}
              {activeTab === 'tryit' && !isOrchestrator && (
                <AgentTryItTab
                  agent={agent}
                  projectId={projectId}
                  onValidated={onAgentValidated || (() => {})}
                />
              )}
            </>
          ) : (
            // Legacy derived-agent panel
            <LegacyDetailContent
              agent={agent as DerivedAgent}
              agents={agents as DerivedAgent[]}
              projectId={projectId}
              activeTab={activeTab}
            />
          )}
        </div>
      </div>
    </>
  )
}

// ═══════════════════════════════════════════════
// Legacy panel content for derived agents (preserved for fallback)
// ═══════════════════════════════════════════════

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-5">
      <p className="text-[10px] font-medium text-[#A0AEC0] uppercase tracking-wide mb-2">{title}</p>
      {children}
    </div>
  )
}

function LegacyDetailContent({
  agent, agents, projectId, activeTab,
}: {
  agent: DerivedAgent
  agents: DerivedAgent[]
  projectId: string
  activeTab: TabId
}) {
  const [tryInput, setTryInput] = useState('')
  const [isRunning, setIsRunning] = useState(false)
  const [isLoadingExample, setIsLoadingExample] = useState(false)
  const [exampleData, setExampleData] = useState<AgentExampleResponse | null>(null)
  const [outputResult, setOutputResult] = useState<AgentExecuteResponse | null>(null)
  const [outputOpen, setOutputOpen] = useState(false)
  const [runStartedAt, setRunStartedAt] = useState<number | null>(null)
  const [inputMode, setInputMode] = useState<'empty' | 'example' | 'custom'>('empty')

  const { messages, sendMessage, isLoading } = useChat({
    projectId,
    pageContext: 'intelligence:workbench',
    focusedEntity: { type: 'agent', data: { id: agent.sourceStepId, title: agent.name, goal: agent.role, agent_type: agent.type } },
  })
  const [chatInput, setChatInput] = useState('')

  const handleLoadExample = useCallback(async () => {
    setIsLoadingExample(true)
    try {
      const example = await getAgentExample(projectId, agent.type)
      setExampleData(example); setTryInput(example.example_input); setInputMode('example')
    } catch { /* ignore */ }
    setIsLoadingExample(false)
  }, [projectId, agent.type])

  const handleRun = useCallback(async () => {
    if (!tryInput.trim()) return
    setIsRunning(true); setRunStartedAt(Date.now())
    try {
      const response = await executeAgent(projectId, { agent_type: agent.type, agent_name: agent.name, input_text: tryInput.trim(), step_id: agent.sourceStepId })
      setOutputResult(response); setOutputOpen(true)
    } catch { /* ignore */ }
    setIsRunning(false); setRunStartedAt(null)
  }, [projectId, agent, tryInput])

  const handleSend = () => {
    if (!chatInput.trim() || isLoading) return
    sendMessage(chatInput.trim()); setChatInput('')
  }

  const feedNames = agent.feedsAgentIds.map(id => agents.find(a => a.id === id)?.name).filter(Boolean)
  const depNames = agent.dependsOnAgentIds.map(id => agents.find(a => a.id === id)?.name).filter(Boolean)
  const tiers = agent.confidenceTiers
  const suggestions = [`What data does ${agent.name} need?`, `How could we improve confidence?`, `What happens when ${agent.name} is uncertain?`]

  if (activeTab === 'chat') {
    return (
      <div className="flex flex-col h-full" style={{ background: '#FAFAFA' }}>
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
          {messages.length === 0 && (
            <div className="space-y-2">
              <p className="text-[10px] text-[#718096]">Ask about {agent.name}</p>
              <div className="flex flex-wrap gap-1">
                {suggestions.map((s, i) => (
                  <button key={i} onClick={() => sendMessage(s)} className="px-2 py-1 rounded text-[10px] text-[#044159] transition-colors hover:bg-[rgba(4,65,89,0.08)]" style={{ background: 'rgba(4,65,89,0.04)' }}>{s}</button>
                ))}
              </div>
            </div>
          )}
          {messages.map((msg: ChatMessage, i: number) => (
            <div key={i} className={`rounded-lg px-2.5 py-1.5 text-[11px] leading-relaxed ${msg.role === 'user' ? 'ml-8 bg-[#3FAF7A] text-white' : 'mr-8 text-[#2D3748]'}`} style={msg.role === 'assistant' ? { background: 'rgba(0,0,0,0.03)' } : undefined}>{msg.content}</div>
          ))}
          {isLoading && <div className="mr-8 rounded-lg px-2.5 py-1.5" style={{ background: 'rgba(0,0,0,0.03)' }}><span className="inline-block w-2 h-2 rounded-full bg-[#3FAF7A] animate-pulse" /></div>}
        </div>
        <div className="px-4 pb-3 pt-1 flex-shrink-0" style={{ borderTop: '1px solid rgba(0,0,0,0.04)' }}>
          <div className="flex gap-2">
            <input value={chatInput} onChange={e => setChatInput(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }} placeholder={`Ask about ${agent.name}...`} className="flex-1 rounded-lg px-2.5 py-1.5 text-[11px] focus:outline-none focus:ring-1 focus:ring-[#3FAF7A]" style={{ background: '#fff', border: '1px solid rgba(10,30,47,0.10)' }} />
            <button onClick={handleSend} disabled={!chatInput.trim() || isLoading} className="px-3 py-1.5 rounded-lg text-[11px] font-medium text-white transition-colors" style={{ background: !chatInput.trim() || isLoading ? '#A0AEC0' : '#3FAF7A' }}>Send</button>
          </div>
        </div>
      </div>
    )
  }

  if (activeTab === 'tryit') {
    return (
      <div className="h-full overflow-y-auto px-5 py-4">
        <Section title="Try It">
          <div className="space-y-2">
            {isRunning && <ProcessingAnimation agentType={agent.type} agentName={agent.name} isRunning={isRunning} startedAt={runStartedAt} />}
            {!isRunning && inputMode === 'example' && exampleData && (
              <ExampleInputCard example={exampleData} agentName={agent.name} onRun={handleRun} onSwitchToCustom={() => { setInputMode('custom'); setTryInput('') }} isRunning={isRunning} />
            )}
            {!isRunning && inputMode !== 'example' && (
              <>
                <div className="flex items-center justify-between">
                  <p className="text-[11px] text-[#4A5568]">Test {agent.name} with real data</p>
                  <button onClick={handleLoadExample} disabled={isLoadingExample} className="text-[11px] font-medium" style={{ color: '#3FAF7A' }}>{isLoadingExample ? 'Loading...' : 'Load example'}</button>
                </div>
                <textarea value={tryInput} onChange={e => setTryInput(e.target.value)} placeholder="Paste text..." className="w-full rounded-lg p-2.5 text-[11px] text-[#2D3748] leading-relaxed resize-none focus:outline-none focus:ring-1 focus:ring-[#3FAF7A]" style={{ background: 'rgba(0,0,0,0.02)', border: '1px solid rgba(10,30,47,0.10)', minHeight: 80 }} />
                <button onClick={handleRun} disabled={!tryInput.trim()} className="w-full rounded-lg py-2 text-[11px] font-semibold text-white transition-all" style={{ background: !tryInput.trim() ? '#A0AEC0' : '#3FAF7A' }}>Run {agent.name}</button>
              </>
            )}
            {outputResult && !outputOpen && !isRunning && (
              <button onClick={() => setOutputOpen(true)} className="w-full rounded-lg py-2 text-[11px] font-medium" style={{ border: '1px solid rgba(63,175,122,0.3)', background: 'rgba(63,175,122,0.04)', color: '#2A8F5F' }}>View output ({outputResult.execution_time_ms}ms)</button>
            )}
          </div>
        </Section>
        {outputResult && <AgentOutputModal agent={agent} result={outputResult} isOpen={outputOpen} onClose={() => setOutputOpen(false)} />}
      </div>
    )
  }

  // Profile tab (legacy)
  return (
    <div className="h-full overflow-y-auto px-5 py-4">
      <Section title="Value Delivered">
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg p-2.5 text-center" style={{ background: 'rgba(63,175,122,0.06)' }}>
            <p className="text-[16px] font-bold text-[#3FAF7A]">{agent.automationRate}%</p>
            <p className="text-[10px] text-[#718096]">Automation</p>
          </div>
          <div className="rounded-lg p-2.5 text-center" style={{ background: 'rgba(4,65,89,0.04)' }}>
            <p className="text-[16px] font-bold text-[#044159]">{agent.dataNeeds.length}</p>
            <p className="text-[10px] text-[#718096]">Data Sources</p>
          </div>
        </div>
      </Section>

      {tiers && (
        <Section title="Confidence Architecture">
          <div className="space-y-2">
            {[
              { label: 'High', value: tiers.high, color: '#3FAF7A' },
              { label: 'Medium', value: tiers.medium, color: '#D4A017' },
              { label: 'Low', value: tiers.low, color: 'rgba(10,30,47,0.25)' },
            ].map((tier, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="w-16"><p className="text-[10px] text-[#4A5568]">{tier.label}</p></div>
                <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: 'rgba(0,0,0,0.04)' }}>
                  <div className="h-full rounded-full" style={{ width: `${tier.value}%`, background: tier.color }} />
                </div>
                <span className="text-[10px] text-[#718096] w-8 text-right">{tier.value}%</span>
              </div>
            ))}
          </div>
        </Section>
      )}

      {(feedNames.length > 0 || depNames.length > 0) && (
        <Section title="Connections">
          {depNames.length > 0 && <div className="mb-2"><p className="text-[10px] text-[#718096] mb-1">Depends on:</p><div className="flex flex-wrap gap-1">{depNames.map((n, i) => <span key={i} className="px-2 py-0.5 rounded text-[10px] text-[#044159]" style={{ background: 'rgba(4,65,89,0.06)' }}>{n}</span>)}</div></div>}
          {feedNames.length > 0 && <div><p className="text-[10px] text-[#718096] mb-1">Feeds:</p><div className="flex flex-wrap gap-1">{feedNames.map((n, i) => <span key={i} className="px-2 py-0.5 rounded text-[10px] text-[#1B6B3A]" style={{ background: 'rgba(63,175,122,0.08)' }}>{n}</span>)}</div></div>}
        </Section>
      )}

      {agent.transform.before !== 'Manual process' && (
        <Section title="Transformation">
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg p-2.5" style={{ background: 'rgba(220,80,80,0.04)' }}>
              <p className="text-[9px] font-medium text-[#9B2C2C] uppercase mb-1">Before</p>
              <p className="text-[11px] text-[#4A5568]">{agent.transform.before}</p>
            </div>
            <div className="rounded-lg p-2.5" style={{ background: 'rgba(63,175,122,0.04)' }}>
              <p className="text-[9px] font-medium text-[#1B6B3A] uppercase mb-1">After</p>
              <p className="text-[11px] text-[#4A5568]">{agent.transform.after}</p>
            </div>
          </div>
        </Section>
      )}
    </div>
  )
}
