'use client'

import { useEffect } from 'react'
import type { DerivedAgent, PersonaSummary } from '@/types/workspace'
import { useChat } from '@/lib/useChat'
import { X, Send } from 'lucide-react'
import { useState } from 'react'
import { Markdown } from '@/components/ui/Markdown'

interface AIAgentModalProps {
  projectId: string
  agent: DerivedAgent
  agents: DerivedAgent[]
  isOpen: boolean
  onClose: () => void
  personas: PersonaSummary[]
}

const AGENT_TYPE_LABELS: Record<string, string> = {
  processor: 'Processor', classifier: 'Classifier', matcher: 'Matcher',
  predictor: 'Predictor', watcher: 'Watcher', generator: 'Generator',
}

const MATURITY_STYLES: Record<string, { bg: string; color: string }> = {
  learning: { bg: 'rgba(4,65,89,0.08)', color: '#044159' },
  reliable: { bg: 'rgba(63,175,122,0.08)', color: '#2A8F5F' },
  expert: { bg: 'rgba(63,175,122,0.15)', color: '#2A8F5F' },
}

const QUALITY_STYLES: Record<string, { bg: string; color: string }> = {
  excellent: { bg: 'rgba(63,175,122,0.12)', color: '#2A8F5F' },
  good: { bg: 'rgba(63,175,122,0.08)', color: '#2A8F5F' },
  moderate: { bg: 'rgba(4,65,89,0.06)', color: '#044159' },
  dependent: { bg: 'rgba(10,30,47,0.04)', color: '#7B7B7B' },
}

function getPersonaColor(name: string): string {
  const palette = ['#3FAF7A', '#044159', '#2D6B4A', '#0A1E2F']
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
  return palette[Math.abs(hash) % palette.length]
}

export function AIAgentModal({ projectId, agent, agents, isOpen, onClose, personas }: AIAgentModalProps) {
  const [chatInput, setChatInput] = useState('')
  const matStyle = MATURITY_STYLES[agent.maturity] || MATURITY_STYLES.learning

  const { messages, sendMessage, isLoading } = useChat({
    projectId,
    pageContext: 'brd:ai-agent',
    focusedEntity: { type: 'solution_flow_step', data: { step_id: agent.sourceStepId } },
  })

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    if (isOpen) window.addEventListener('keydown', handleEsc)
    return () => window.removeEventListener('keydown', handleEsc)
  }, [isOpen, onClose])

  if (!isOpen) return null

  const handleSuggestion = (text: string) => {
    sendMessage(text)
  }

  const handleSend = () => {
    if (!chatInput.trim()) return
    sendMessage(chatInput)
    setChatInput('')
  }

  const feedAgents = agent.feedsAgentIds.map(id => agents.find(a => a.id === id)).filter(Boolean)
  const depAgents = agent.dependsOnAgentIds.map(id => agents.find(a => a.id === id)).filter(Boolean)

  return (
    <div
      className="fixed inset-0 z-[200] flex items-center justify-center p-8"
      style={{ background: 'rgba(10,30,47,0.45)' }}
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      <div
        className="bg-white rounded-[14px] w-[960px] max-w-[95vw] max-h-[85vh] flex shadow-2xl overflow-hidden relative"
        style={{ animation: 'modalIn 0.3s ease' }}
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 w-7 h-7 rounded-full flex items-center justify-center z-10 transition-colors"
          style={{ border: '1px solid #E5E5E5', background: '#F5F5F5', color: '#4B4B4B' }}
          onMouseEnter={e => { e.currentTarget.style.background = '#E5E5E5'; e.currentTarget.style.color = '#1D1D1F' }}
          onMouseLeave={e => { e.currentTarget.style.background = '#F5F5F5'; e.currentTarget.style.color = '#4B4B4B' }}
        >
          <X size={13} />
        </button>

        {/* Left: Agent Profile */}
        <div className="flex-1 min-w-0 overflow-y-auto p-7">
          {/* Header */}
          <div className="flex items-center gap-3.5 mb-2">
            <div
              className="w-11 h-11 rounded-[10px] flex items-center justify-center text-[22px] flex-shrink-0"
              style={{ background: 'rgba(63,175,122,0.08)', color: '#2A8F5F' }}
            >
              {agent.icon}
            </div>
            <div className="flex-1">
              <div className="text-[22px] font-bold" style={{ color: '#1D1D1F', letterSpacing: '-0.01em' }}>{agent.name}</div>
              <div className="text-[13px] mt-0.5" style={{ color: '#7B7B7B' }}>{agent.role}</div>
            </div>
          </div>

          <div className="flex gap-1.5 mb-5">
            <span className="text-[9px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded" style={matStyle}>
              {agent.maturity}
            </span>
            <span className="text-[9px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded" style={{ background: '#F5F5F5', color: '#4B4B4B' }}>
              {AGENT_TYPE_LABELS[agent.type]}
            </span>
            <span className="text-[9px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded" style={{ background: 'rgba(63,175,122,0.08)', color: '#2A8F5F' }}>
              {agent.automationRate}% automated
            </span>
          </div>

          {/* Daily Work */}
          {agent.dailyWork && (
            <Section label="What I Do Every Day" icon="📋">
              <div className="text-[13px] leading-[1.65] p-3.5 rounded-[9px]" style={{ background: '#F5F5F5', borderLeft: '3px solid #3FAF7A', color: '#333' }}>
                {agent.dailyWork}
              </div>
            </Section>
          )}

          {/* Transformation */}
          <Section label="The Transformation" icon="⚡">
            <div className="grid overflow-hidden rounded-[9px]" style={{ gridTemplateColumns: '1fr auto 1fr', border: '1px solid #E5E5E5' }}>
              <div className="p-3" style={{ background: 'rgba(4,65,89,0.02)' }}>
                <div className="text-[9px] font-semibold uppercase tracking-wide mb-1" style={{ color: '#044159' }}>Before</div>
                <div className="text-[12px] font-medium" style={{ color: '#333' }}>{agent.transform.before}</div>
              </div>
              <div className="flex items-center justify-center px-2 text-base" style={{ background: '#F5F5F5', color: '#3FAF7A' }}>→</div>
              <div className="p-3" style={{ background: 'rgba(63,175,122,0.025)' }}>
                <div className="text-[9px] font-semibold uppercase tracking-wide mb-1" style={{ color: '#2A8F5F' }}>After</div>
                <div className="text-[12px] font-medium" style={{ color: '#333' }}>{agent.transform.after}</div>
              </div>
            </div>
          </Section>

          {/* Data Diet */}
          {agent.dataNeeds.length > 0 && (
            <Section label="My Data Diet" icon="🍽">
              <div className="flex flex-col gap-1.5">
                {agent.dataNeeds.map((d, i) => {
                  const qs = QUALITY_STYLES[d.quality] || QUALITY_STYLES.good
                  return (
                    <div key={i} className="flex items-center gap-2.5 px-3 py-2 rounded-lg" style={{ background: '#F5F5F5' }}>
                      <div className="flex-1">
                        <div className="text-[12px] font-medium" style={{ color: '#333' }}>{d.source}</div>
                        {d.amount && <div className="text-[10px] mt-0.5" style={{ color: '#7B7B7B' }}>{d.amount}</div>}
                      </div>
                      <span className="text-[8px] font-bold uppercase px-1.5 py-0.5 rounded tracking-wide" style={qs}>{d.quality}</span>
                    </div>
                  )
                })}
              </div>
            </Section>
          )}

          {/* Produces */}
          {agent.produces.length > 0 && (
            <Section label="What I Produce" icon="📤">
              <div className="flex gap-1.5 flex-wrap">
                {agent.produces.map((p, i) => (
                  <span key={i} className="text-[11px] font-medium px-2.5 py-1 rounded" style={{ background: 'rgba(63,175,122,0.08)', color: '#2A8F5F', border: '1px solid rgba(63,175,122,0.1)' }}>
                    {p}
                  </span>
                ))}
              </div>
            </Section>
          )}

          {/* Human Partners */}
          {agent.humanPartners.length > 0 && (
            <Section label="My Human Partners" icon="👥">
              <div className="flex flex-col gap-1.5">
                {agent.humanPartners.map(name => {
                  const persona = personas.find(p => p.name === name)
                  const color = getPersonaColor(name)
                  return (
                    <div key={name} className="flex items-center gap-2.5 px-3 py-2 rounded-lg" style={{ background: '#F5F5F5' }}>
                      <div className="w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold text-white" style={{ background: color }}>
                        {name.split(' ').map(w => w[0]).join('').slice(0, 2)}
                      </div>
                      <div>
                        <div className="text-[12px] font-semibold" style={{ color: '#1D1D1F' }}>{name}</div>
                        {persona?.role && <div className="text-[10px]" style={{ color: '#7B7B7B' }}>{persona.role}</div>}
                      </div>
                    </div>
                  )
                })}
              </div>
            </Section>
          )}

          {/* Growth */}
          {agent.growth && (
            <Section label="How I Grow" icon="📈">
              <div className="text-[12px] leading-relaxed p-3 rounded-lg" style={{ background: 'rgba(4,65,89,0.02)', color: '#333', borderLeft: '3px solid #044159' }}>
                {agent.growth}
              </div>
            </Section>
          )}

          {/* Feeds */}
          <Section label="Who I Feed" icon="→">
            <div className="flex flex-col gap-1.5">
              {feedAgents.length > 0 ? feedAgents.map(a => a && (
                <div key={a.id} className="flex items-center gap-2 px-3 py-2 rounded-lg" style={{ background: '#F5F5F5' }}>
                  <span style={{ color: '#3FAF7A', fontSize: 12 }}>→</span>
                  <span className="text-[11px] font-semibold" style={{ color: '#333' }}>{a.name}</span>
                  <span className="text-[10px] ml-auto" style={{ color: '#7B7B7B' }}>{a.produces[0]}</span>
                </div>
              )) : (
                <div className="text-[11px]" style={{ color: '#999' }}>End of pipeline — produces final outputs</div>
              )}
            </div>
          </Section>

          {/* Depends On */}
          <Section label="Who I Depend On" icon="←">
            <div className="flex flex-col gap-1.5">
              {depAgents.length > 0 ? depAgents.map(a => a && (
                <div key={a.id} className="flex items-center gap-2 px-3 py-2 rounded-lg" style={{ background: '#F5F5F5' }}>
                  <span style={{ color: '#044159', fontSize: 12 }}>←</span>
                  <span className="text-[11px] font-semibold" style={{ color: '#333' }}>{a.name}</span>
                  <span className="text-[10px] ml-auto" style={{ color: '#7B7B7B' }}>{a.produces[0]}</span>
                </div>
              )) : (
                <div className="text-[11px]" style={{ color: '#999' }}>No dependencies — works independently</div>
              )}
            </div>
          </Section>

          {/* Insight */}
          {agent.insight && (
            <Section label="Consultant&apos;s Insight" icon="💡">
              <div
                className="text-[12px] leading-relaxed p-3.5 rounded-[9px] italic"
                style={{
                  background: 'linear-gradient(135deg, rgba(4,65,89,0.03), rgba(63,175,122,0.03))',
                  border: '1px solid rgba(4,65,89,0.08)',
                  color: '#333',
                }}
              >
                {agent.insight}
              </div>
            </Section>
          )}
        </div>

        {/* Right: Learning Chat */}
        <div className="w-[320px] flex-shrink-0 flex flex-col" style={{ borderLeft: '1px solid #E5E5E5', background: '#F5F5F5' }}>
          {/* Chat header */}
          <div className="flex items-center gap-2 px-4 py-3.5" style={{ borderBottom: '1px solid #E5E5E5', background: '#fff' }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="#3FAF7A"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/></svg>
            <span className="text-xs font-semibold flex-1" style={{ color: '#1D1D1F' }}>Learn About This Agent</span>
            <span className="text-[9px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded" style={{ background: 'rgba(63,175,122,0.08)', color: '#2A8F5F' }}>Agent</span>
          </div>

          {/* Chat body */}
          <div className="flex-1 overflow-y-auto px-4 py-3.5">
            {/* Context */}
            <div
              className="text-[11px] leading-relaxed p-2.5 rounded-lg mb-3"
              style={{ background: '#fff', borderLeft: '2px solid #3FAF7A', color: '#7B7B7B' }}
            >
              <strong style={{ color: '#333' }}>{agent.name}</strong> is{' '}
              {agent.maturity === 'learning'
                ? 'still learning — it needs more data and time to become reliable'
                : agent.maturity === 'expert'
                  ? 'highly trained — it handles most cases autonomously'
                  : 'working reliably — it performs well and continues to improve'}.
              {depAgents.length > 0 && ` It depends on ${depAgents.map(a => a?.name).join(' and ')}.`}
            </div>

            {/* Messages */}
            {messages.filter(m => m.role !== 'system').map((msg, i) => (
              <div
                key={i}
                className={`mb-2.5 text-[12px] leading-relaxed p-2.5 rounded-lg ${
                  msg.role === 'user' ? 'ml-6' : 'mr-2'
                }`}
                style={{
                  background: msg.role === 'user' ? 'rgba(63,175,122,0.08)' : '#fff',
                  border: msg.role === 'user' ? '1px solid rgba(63,175,122,0.15)' : '1px solid #E5E5E5',
                  color: '#333',
                }}
              >
                <Markdown content={typeof msg.content === 'string' ? msg.content : ''} />
              </div>
            ))}

            {isLoading && (
              <div className="flex items-center gap-2 p-2.5">
                <div className="animate-spin rounded-full h-3.5 w-3.5 border-2 border-[#3FAF7A] border-t-transparent" />
                <span className="text-[11px]" style={{ color: '#999' }}>Thinking...</span>
              </div>
            )}

            {/* Suggestions */}
            {messages.length <= 1 && (
              <div className="flex flex-col gap-1.5">
                <SuggestBtn onClick={() => handleSuggestion(`What data makes the ${agent.name} better?`)}>
                  <span className="font-semibold" style={{ color: '#3FAF7A' }}>?</span> What data makes this agent better?
                </SuggestBtn>
                <SuggestBtn onClick={() => handleSuggestion(`How long until ${agent.name} is fully reliable?`)}>
                  <span className="font-semibold" style={{ color: '#3FAF7A' }}>?</span> How long until it&apos;s fully reliable?
                </SuggestBtn>
                <SuggestBtn onClick={() => handleSuggestion(`What happens when ${agent.name} makes a mistake?`)}>
                  <span className="font-semibold" style={{ color: '#3FAF7A' }}>?</span> What happens when it makes a mistake?
                </SuggestBtn>
                <SuggestBtn onClick={() => handleSuggestion(`Can ${agent.name} work with less data?`)}>
                  <span className="font-semibold" style={{ color: '#3FAF7A' }}>?</span> Can it work with less data?
                </SuggestBtn>
                {agent.humanPartners[0] && (
                  <SuggestBtn onClick={() => handleSuggestion(`What does ${agent.humanPartners[0]}'s day look like working with ${agent.name}?`)}>
                    <span className="font-semibold" style={{ color: '#3FAF7A' }}>?</span> What does {agent.humanPartners[0].split(' ')[0]}&apos;s day look like?
                  </SuggestBtn>
                )}

                {agent.feedsAgentIds.length > 0 && (
                  <>
                    <div className="text-[9px] font-semibold uppercase tracking-wide mt-2.5 pt-2.5 mb-1" style={{ color: '#999', borderTop: '1px solid #E5E5E5' }}>
                      Impact Questions
                    </div>
                    <SuggestBtn onClick={() => handleSuggestion(`What breaks if ${agent.name} is inaccurate? What's the downstream impact?`)}>
                      <span className="font-semibold" style={{ color: '#3FAF7A' }}>↓</span> What breaks if this agent is inaccurate?
                    </SuggestBtn>
                  </>
                )}
              </div>
            )}
          </div>

          {/* Chat input */}
          <div className="px-3.5 py-2.5" style={{ borderTop: '1px solid #E5E5E5', background: '#fff' }}>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={chatInput}
                onChange={e => setChatInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
                placeholder="Ask about this agent..."
                className="flex-1 px-3 py-2 rounded-lg text-[12px] outline-none transition-colors"
                style={{ border: '1px solid #E5E5E5', color: '#333' }}
                onFocus={e => { e.currentTarget.style.borderColor = '#3FAF7A' }}
                onBlur={e => { e.currentTarget.style.borderColor = '#E5E5E5' }}
              />
              <button
                onClick={handleSend}
                disabled={!chatInput.trim() || isLoading}
                className="w-8 h-8 rounded-lg flex items-center justify-center transition-colors disabled:opacity-30"
                style={{ background: '#3FAF7A', color: '#fff' }}
              >
                <Send size={12} />
              </button>
            </div>
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes modalIn {
          from { opacity: 0; transform: translateY(16px) scale(0.98); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
      `}</style>
    </div>
  )
}

function Section({ label, icon, children }: { label: string; icon: string; children: React.ReactNode }) {
  return (
    <div className="mb-5">
      <div className="flex items-center gap-1.5 mb-2 mt-5">
        <span className="text-xs">{icon}</span>
        <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: '#7B7B7B' }}>{label}</span>
      </div>
      {children}
    </div>
  )
}

function SuggestBtn({ onClick, children }: { onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className="text-left px-3 py-2 rounded-lg text-[11px] leading-snug transition-all cursor-pointer"
      style={{ background: '#fff', border: '1px solid #E5E5E5', color: '#333' }}
      onMouseEnter={e => {
        e.currentTarget.style.borderColor = '#3FAF7A'
        e.currentTarget.style.background = 'rgba(63,175,122,0.04)'
      }}
      onMouseLeave={e => {
        e.currentTarget.style.borderColor = '#E5E5E5'
        e.currentTarget.style.background = '#fff'
      }}
    >
      {children}
    </button>
  )
}
