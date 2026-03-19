'use client'

/**
 * WorkbenchDetailPanel — Slide-in panel (520px right) for the Intelligence Workbench.
 *
 * Layout: detail content (scrollable top), chat (fixed bottom).
 * Try It: input in chat area, output opens as modal to the LEFT of the panel.
 */

import { useState, useEffect, useCallback } from 'react'
import type { DerivedAgent, AgentExecuteResponse } from '@/types/workspace'
import { useChat, type ChatMessage } from '@/lib/useChat'
import { executeAgent, getAgentExample } from '@/lib/api/workspace'
import { AgentOutputRenderer } from './AgentOutputRenderer'

interface Props {
  agent: DerivedAgent
  agents: DerivedAgent[]
  projectId: string
  onClose: () => void
}

const TECHNIQUE_LABELS: Record<string, string> = {
  llm: 'Large Language Model',
  classification: 'Classification Pipeline',
  embeddings: 'Embedding Similarity',
  rules: 'Rule-Based Engine',
  hybrid: 'Hybrid AI Pipeline',
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-5">
      <p className="text-[10px] font-medium text-[#A0AEC0] uppercase tracking-wide mb-2">
        {title}
      </p>
      {children}
    </div>
  )
}

export function WorkbenchDetailPanel({ agent, agents, projectId, onClose }: Props) {
  // Try It state
  const [tryInput, setTryInput] = useState('')
  const [isRunning, setIsRunning] = useState(false)
  const [isLoadingExample, setIsLoadingExample] = useState(false)
  const [outputResult, setOutputResult] = useState<AgentExecuteResponse | null>(null)
  const [outputOpen, setOutputOpen] = useState(false)

  // Chat
  const { messages, sendMessage, isLoading } = useChat({
    projectId,
    pageContext: 'intelligence:workbench',
    focusedEntity: {
      type: 'agent',
      data: {
        id: agent.sourceStepId,
        title: agent.name,
        goal: agent.role,
        agent_type: agent.type,
      },
    },
  })
  const [chatInput, setChatInput] = useState('')

  // ESC closes output modal first, then panel
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (outputOpen) setOutputOpen(false)
        else onClose()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose, outputOpen])

  const handleLoadExample = useCallback(async () => {
    setIsLoadingExample(true)
    try {
      const example = await getAgentExample(projectId, agent.type)
      setTryInput(example.example_input)
    } catch { /* ignore */ }
    setIsLoadingExample(false)
  }, [projectId, agent.type])

  const handleRun = useCallback(async () => {
    if (!tryInput.trim()) return
    setIsRunning(true)
    try {
      const response = await executeAgent(projectId, {
        agent_type: agent.type,
        agent_name: agent.name,
        input_text: tryInput.trim(),
        step_id: agent.sourceStepId,
      })
      setOutputResult(response)
      setOutputOpen(true)
    } catch { /* ignore */ }
    setIsRunning(false)
  }, [projectId, agent, tryInput])

  const handleSend = () => {
    if (!chatInput.trim() || isLoading) return
    sendMessage(chatInput.trim())
    setChatInput('')
  }

  const tiers = agent.confidenceTiers
  const evolution = agent.evolution || []
  const feedNames = agent.feedsAgentIds
    .map(id => agents.find(a => a.id === id)?.name)
    .filter(Boolean)
  const depNames = agent.dependsOnAgentIds
    .map(id => agents.find(a => a.id === id)?.name)
    .filter(Boolean)

  const suggestions = [
    `What data does ${agent.name} need?`,
    `How could we improve confidence?`,
    `What happens when ${agent.name} is uncertain?`,
    `How does it connect to other agents?`,
  ]

  return (
    <>
      {/* Backdrop — only covers left of panel */}
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
        <div
          className="flex items-center gap-3 px-5 py-3 flex-shrink-0"
          style={{ borderBottom: '1px solid rgba(10,30,47,0.08)' }}
        >
          <span className="text-xl">{agent.icon}</span>
          <div className="flex-1 min-w-0">
            <p className="text-[13px] font-semibold text-[#0A1E2F] truncate">{agent.name}</p>
            <p className="text-[11px] text-[#4A5568]">{agent.role}</p>
          </div>
          <div className="flex items-center gap-2">
            <span
              className="px-2 py-0.5 rounded text-[10px] font-medium"
              style={{
                color: agent.maturity === 'expert' ? '#1B6B3A' : agent.maturity === 'reliable' ? '#044159' : '#8B6914',
                background: agent.maturity === 'expert' ? 'rgba(63,175,122,0.10)' : agent.maturity === 'reliable' ? 'rgba(4,65,89,0.08)' : 'rgba(212,160,23,0.10)',
              }}
            >
              {agent.maturity}
            </span>
            <span className="text-[10px] text-[#718096]">{agent.automationRate}% auto</span>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-[rgba(0,0,0,0.04)] transition-colors text-[#718096]">✕</button>
        </div>

        {/* Scrollable detail content */}
        <div className="flex-1 overflow-y-auto px-5 py-4 min-h-0">
          {/* Try It section */}
          <Section title="Try It">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-[11px] text-[#4A5568]">Test {agent.name} with real data</p>
                <button
                  onClick={handleLoadExample}
                  disabled={isLoadingExample}
                  className="text-[11px] font-medium"
                  style={{ color: '#3FAF7A' }}
                >
                  {isLoadingExample ? 'Loading...' : 'Load project example'}
                </button>
              </div>
              <textarea
                value={tryInput}
                onChange={e => setTryInput(e.target.value)}
                placeholder="Paste a meeting transcript, email, or any text..."
                className="w-full rounded-lg p-2.5 text-[11px] text-[#2D3748] leading-relaxed resize-none focus:outline-none focus:ring-1 focus:ring-[#3FAF7A]"
                style={{
                  background: 'rgba(0,0,0,0.02)',
                  border: '1px solid rgba(10,30,47,0.10)',
                  minHeight: 80,
                  maxHeight: 140,
                }}
              />
              <button
                onClick={handleRun}
                disabled={isRunning || !tryInput.trim()}
                className="w-full rounded-lg py-2 text-[11px] font-semibold text-white transition-all"
                style={{
                  background: isRunning || !tryInput.trim() ? '#A0AEC0' : '#3FAF7A',
                  cursor: isRunning || !tryInput.trim() ? 'not-allowed' : 'pointer',
                }}
              >
                {isRunning ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Running...
                  </span>
                ) : (
                  `Run ${agent.name}`
                )}
              </button>
              {outputResult && !outputOpen && (
                <button
                  onClick={() => setOutputOpen(true)}
                  className="w-full rounded-lg py-2 text-[11px] font-medium transition-all"
                  style={{
                    border: '1px solid rgba(63,175,122,0.3)',
                    background: 'rgba(63,175,122,0.04)',
                    color: '#2A8F5F',
                  }}
                >
                  View last output ({outputResult.execution_time_ms}ms)
                </button>
              )}
            </div>
          </Section>

          {/* Technique */}
          <Section title="AI Technique">
            <p className="text-[12px] text-[#2D3748]">
              {TECHNIQUE_LABELS[agent.technique || 'llm'] || agent.technique}
            </p>
          </Section>

          {/* Value Delivered */}
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

          {/* Confidence Architecture */}
          {tiers && (
            <Section title="Confidence Architecture">
              <div className="space-y-2">
                {[
                  { label: 'High Confidence', value: tiers.high, color: '#3FAF7A', desc: 'Act autonomously' },
                  { label: 'Medium Confidence', value: tiers.medium, color: '#D4A017', desc: 'Flag for review' },
                  { label: 'Low Confidence', value: tiers.low, color: 'rgba(10,30,47,0.25)', desc: 'Defer to human' },
                ].map((tier, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <div className="w-20"><p className="text-[10px] text-[#4A5568]">{tier.label}</p></div>
                    <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: 'rgba(0,0,0,0.04)' }}>
                      <div className="h-full rounded-full transition-all duration-500" style={{ width: `${tier.value}%`, background: tier.color }} />
                    </div>
                    <span className="text-[10px] text-[#718096] w-8 text-right">{tier.value}%</span>
                    <span className="text-[9px] text-[#A0AEC0] w-24">{tier.desc}</span>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Evolution Path */}
          {evolution.length > 0 && (
            <Section title="Evolution Path">
              <div className="space-y-2">
                {evolution.map((step, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <span className="flex-shrink-0 w-4 h-4 rounded-full flex items-center justify-center text-[10px] mt-0.5" style={{ background: step.done ? '#3FAF7A' : 'rgba(0,0,0,0.06)', color: step.done ? '#fff' : '#A0AEC0' }}>
                      {step.done ? '✓' : i + 1}
                    </span>
                    <p className="text-[11px] leading-snug" style={{ color: step.done ? '#4A5568' : '#A0AEC0' }}>{step.label}</p>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Connections */}
          {(feedNames.length > 0 || depNames.length > 0) && (
            <Section title="Connections">
              {depNames.length > 0 && (
                <div className="mb-2">
                  <p className="text-[10px] text-[#718096] mb-1">Depends on:</p>
                  <div className="flex flex-wrap gap-1">
                    {depNames.map((n, i) => (<span key={i} className="px-2 py-0.5 rounded text-[10px] text-[#044159]" style={{ background: 'rgba(4,65,89,0.06)' }}>{n}</span>))}
                  </div>
                </div>
              )}
              {feedNames.length > 0 && (
                <div>
                  <p className="text-[10px] text-[#718096] mb-1">Feeds:</p>
                  <div className="flex flex-wrap gap-1">
                    {feedNames.map((n, i) => (<span key={i} className="px-2 py-0.5 rounded text-[10px] text-[#1B6B3A]" style={{ background: 'rgba(63,175,122,0.08)' }}>{n}</span>))}
                  </div>
                </div>
              )}
            </Section>
          )}

          {/* Transformation */}
          {agent.transform.before !== 'Manual process' && (
            <Section title="The Transformation">
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

        {/* Chat — always fixed at bottom */}
        <div
          className="flex-shrink-0 flex flex-col"
          style={{ borderTop: '1px solid rgba(10,30,47,0.08)', height: 200, background: '#FAFAFA' }}
        >
          <div className="flex-1 overflow-y-auto px-4 py-2 space-y-2">
            {messages.length === 0 && (
              <div className="space-y-2">
                <p className="text-[10px] text-[#718096]">Ask about {agent.name}</p>
                <div className="flex flex-wrap gap-1">
                  {suggestions.map((s, i) => (
                    <button
                      key={i}
                      onClick={() => sendMessage(s)}
                      className="px-2 py-1 rounded text-[10px] text-[#044159] transition-colors hover:bg-[rgba(4,65,89,0.08)]"
                      style={{ background: 'rgba(4,65,89,0.04)' }}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((msg: ChatMessage, i: number) => (
              <div
                key={i}
                className={`rounded-lg px-2.5 py-1.5 text-[11px] leading-relaxed ${
                  msg.role === 'user' ? 'ml-8 bg-[#3FAF7A] text-white' : 'mr-8 text-[#2D3748]'
                }`}
                style={msg.role === 'assistant' ? { background: 'rgba(0,0,0,0.03)' } : undefined}
              >
                {msg.content}
              </div>
            ))}
            {isLoading && (
              <div className="mr-8 rounded-lg px-2.5 py-1.5" style={{ background: 'rgba(0,0,0,0.03)' }}>
                <span className="inline-block w-2 h-2 rounded-full bg-[#3FAF7A] animate-pulse" />
              </div>
            )}
          </div>
          <div className="px-4 pb-2 pt-1" style={{ borderTop: '1px solid rgba(0,0,0,0.04)' }}>
            <div className="flex gap-2">
              <input
                value={chatInput}
                onChange={e => setChatInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
                placeholder={`Ask about ${agent.name}...`}
                className="flex-1 rounded-lg px-2.5 py-1.5 text-[11px] focus:outline-none focus:ring-1 focus:ring-[#3FAF7A]"
                style={{ background: '#fff', border: '1px solid rgba(10,30,47,0.10)' }}
              />
              <button
                onClick={handleSend}
                disabled={!chatInput.trim() || isLoading}
                className="px-3 py-1.5 rounded-lg text-[11px] font-medium text-white transition-colors"
                style={{ background: !chatInput.trim() || isLoading ? '#A0AEC0' : '#3FAF7A' }}
              >
                Send
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Output Modal — opens to the LEFT of the panel */}
      {outputOpen && outputResult && (
        <>
          <div
            className="fixed top-0 left-0 bottom-0 z-[200]"
            style={{ right: 520, background: 'rgba(10,30,47,0.35)' }}
            onClick={() => setOutputOpen(false)}
          />
          <div
            className="fixed z-[205] flex flex-col bg-white rounded-xl shadow-2xl overflow-hidden"
            style={{
              top: '5%',
              bottom: '5%',
              right: 536,
              width: 520,
              maxWidth: 'calc(100vw - 560px)',
              animation: 'wbOutputIn 0.25s ease',
            }}
          >
            <style>{`@keyframes wbOutputIn { from { opacity: 0; transform: translateX(12px) scale(0.97); } to { opacity: 1; transform: translateX(0) scale(1); } }`}</style>

            {/* Modal header */}
            <div
              className="flex items-center gap-3 px-5 py-3 flex-shrink-0"
              style={{ borderBottom: '1px solid rgba(10,30,47,0.08)', background: 'linear-gradient(135deg, #FAFAFA 0%, rgba(63,175,122,0.03) 100%)' }}
            >
              <span className="text-lg">{agent.icon}</span>
              <div className="flex-1 min-w-0">
                <p className="text-[13px] font-semibold text-[#0A1E2F]">{agent.name} Output</p>
                <p className="text-[10px] text-[#718096]">
                  Processed in {outputResult.execution_time_ms}ms
                </p>
              </div>
              <button
                onClick={() => setOutputOpen(false)}
                className="p-1 rounded-lg hover:bg-[rgba(0,0,0,0.04)] transition-colors text-[#718096] text-[12px]"
              >
                ✕
              </button>
            </div>

            {/* Output content */}
            <div className="flex-1 overflow-y-auto px-5 py-4">
              <AgentOutputRenderer
                agentType={outputResult.agent_type}
                output={outputResult.output}
                executionTimeMs={outputResult.execution_time_ms}
              />
            </div>
          </div>
        </>
      )}
    </>
  )
}
