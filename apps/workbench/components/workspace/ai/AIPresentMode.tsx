'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import type { DerivedAgent, PersonaSummary } from '@/types/workspace'
import { PresentModeShell } from '@/components/workspace/shared/PresentModeShell'
import { PresentShareToolbar } from '@/components/workspace/shared/PresentShareToolbar'

interface AIPresentModeProps {
  isOpen: boolean
  onClose: () => void
  agents: DerivedAgent[]
  personas: PersonaSummary[]
  avgAutomation: number
  estTimeSaved: string
}

const AGENT_TYPE_LABELS: Record<string, string> = {
  processor: 'Processor', classifier: 'Classifier', matcher: 'Matcher',
  predictor: 'Predictor', watcher: 'Watcher', generator: 'Generator',
}

function getPersonaColor(name: string): string {
  const palette = ['#3FAF7A', '#044159', '#2D6B4A', '#0A1E2F']
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
  return palette[Math.abs(hash) % palette.length]
}

export function AIPresentMode({
  isOpen,
  onClose,
  agents,
  personas,
  avgAutomation,
  estTimeSaved,
}: AIPresentModeProps) {
  const [currentSlide, setCurrentSlide] = useState(0)
  const contentRef = useRef<HTMLDivElement>(null)
  const totalSlides = agents.length + 2 // title + agents + summary

  useEffect(() => {
    if (!isOpen) setCurrentSlide(0)
  }, [isOpen])

  const navigate = (dir: 1 | -1) => {
    setCurrentSlide(prev => Math.max(0, Math.min(totalSlides - 1, prev + dir)))
  }

  const renderSlide = () => {
    // Title slide
    if (currentSlide === 0) {
      return (
        <div className="text-center">
          <h1 className="text-[42px] font-bold text-white mb-2.5" style={{ letterSpacing: '-0.02em' }}>
            Meet Your AI Team
          </h1>
          <p className="text-lg leading-relaxed mb-9 max-w-[600px] mx-auto" style={{ color: 'rgba(255,255,255,0.5)' }}>
            {agents.length} specialized agents working together to automate and enhance your operations
          </p>
          <div className="flex justify-center gap-7 mb-9">
            <Stat value={String(agents.length)} label="Agents" />
            <Stat value={`${avgAutomation}%`} label="Automated" />
            <Stat value={estTimeSaved} label="Saved / Day" />
          </div>
          <p className="text-[13px]" style={{ color: 'rgba(255,255,255,0.2)' }}>
            Press → to meet your team
          </p>
        </div>
      )
    }

    // Summary slide
    if (currentSlide === totalSlides - 1) {
      return (
        <div className="text-center">
          <h2 className="text-[32px] font-bold text-white mb-7" style={{ letterSpacing: '-0.01em' }}>
            Your AI Team
          </h2>

          {/* Agent grid */}
          <div className="grid grid-cols-3 gap-3 mb-8 text-left">
            {agents.map(a => (
              <div
                key={a.id}
                className="p-4 rounded-[9px]"
                style={{ background: 'rgba(255,255,255,0.035)', border: '1px solid rgba(255,255,255,0.05)' }}
              >
                <div className="text-xl mb-1.5">{a.icon}</div>
                <div className="text-sm font-semibold text-white mb-1">{a.name}</div>
                <div className="text-xs font-medium mb-0.5" style={{ color: '#3FAF7A' }}>
                  {a.automationRate}% automated
                </div>
                <div className="text-[11px]" style={{ color: 'rgba(255,255,255,0.35)' }}>
                  {AGENT_TYPE_LABELS[a.type]}
                </div>
              </div>
            ))}
          </div>

          {/* Pipeline visualization */}
          <div className="flex items-center justify-center gap-1.5 mb-7 flex-wrap">
            {agents.map((a, i) => (
              <div key={a.id} className="flex items-center gap-1.5">
                <span
                  className="px-3 py-1.5 rounded-md text-[11px] font-semibold"
                  style={{ background: 'rgba(63,175,122,0.1)', border: '1px solid rgba(63,175,122,0.15)', color: '#3FAF7A' }}
                >
                  {a.name}
                </span>
                {i < agents.length - 1 && (
                  <span className="text-sm" style={{ color: 'rgba(255,255,255,0.2)' }}>→</span>
                )}
              </div>
            ))}
          </div>

          {/* Summary stats */}
          <div className="grid grid-cols-3 gap-3.5">
            <SumStat value={String(agents.length)} label="AI Agents" />
            <SumStat value={`${avgAutomation}%`} label="Avg Automation" />
            <SumStat value={estTimeSaved} label="Daily Time Saved" />
          </div>
        </div>
      )
    }

    // Agent slide
    const agent = agents[currentSlide - 1]
    const matStyle = agent.maturity === 'expert'
      ? { bg: 'rgba(63,175,122,0.15)', color: '#3FAF7A' }
      : agent.maturity === 'reliable'
        ? { bg: 'rgba(63,175,122,0.08)', color: '#3FAF7A' }
        : { bg: 'rgba(4,65,89,0.12)', color: 'rgba(255,255,255,0.5)' }

    return (
      <div>
        {/* Agent header */}
        <div className="flex items-center gap-4 mb-2">
          <div
            className="w-[52px] h-[52px] rounded-xl flex items-center justify-center text-[26px]"
            style={{ background: 'rgba(63,175,122,0.1)', border: '1px solid rgba(63,175,122,0.15)' }}
          >
            {agent.icon}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: '#3FAF7A' }}>
                {AGENT_TYPE_LABELS[agent.type]}
              </span>
              <span className="text-[9px] font-bold uppercase px-2 py-0.5 rounded" style={matStyle}>
                {agent.maturity}
              </span>
            </div>
            <div className="text-[34px] font-bold text-white" style={{ letterSpacing: '-0.02em', lineHeight: 1.2 }}>
              {agent.name}
            </div>
          </div>
        </div>

        <p className="text-[15px] leading-relaxed mb-5" style={{ color: 'rgba(255,255,255,0.45)' }}>
          {agent.role}
        </p>

        {/* Automation bar */}
        <div className="flex items-center gap-3 mb-5">
          <span className="text-[10px] uppercase tracking-wide whitespace-nowrap" style={{ color: 'rgba(255,255,255,0.3)' }}>Automation</span>
          <div className="flex-1 h-1 rounded-sm overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
            <div className="h-full rounded-sm" style={{ width: `${agent.automationRate}%`, background: '#3FAF7A', transition: 'width 0.6s ease' }} />
          </div>
          <span className="text-sm font-semibold" style={{ color: '#3FAF7A' }}>{agent.automationRate}%</span>
        </div>

        {/* Daily work */}
        {agent.dailyWork && (
          <div
            className="text-[15px] leading-[1.7] rounded-[10px] p-4.5 mb-5"
            style={{ color: 'rgba(255,255,255,0.78)', background: 'rgba(255,255,255,0.035)', borderLeft: '3px solid #3FAF7A' }}
          >
            {agent.dailyWork}
          </div>
        )}

        {/* Transform */}
        <div
          className="grid overflow-hidden rounded-[9px] mb-5"
          style={{ gridTemplateColumns: '1fr auto 1fr', border: '1px solid rgba(255,255,255,0.06)' }}
        >
          <div className="p-3.5" style={{ background: 'rgba(4,65,89,0.15)' }}>
            <div className="text-[10px] font-semibold uppercase tracking-wide mb-1.5" style={{ color: 'rgba(255,255,255,0.35)' }}>Before</div>
            <div className="text-sm font-medium" style={{ color: 'rgba(255,255,255,0.75)' }}>{agent.transform.before}</div>
          </div>
          <div className="flex items-center justify-center px-2.5 text-lg" style={{ background: 'rgba(255,255,255,0.02)', color: '#3FAF7A' }}>→</div>
          <div className="p-3.5" style={{ background: 'rgba(63,175,122,0.08)' }}>
            <div className="text-[10px] font-semibold uppercase tracking-wide mb-1.5" style={{ color: '#3FAF7A' }}>After</div>
            <div className="text-sm font-medium" style={{ color: 'rgba(255,255,255,0.75)' }}>{agent.transform.after}</div>
          </div>
        </div>

        {/* Data diet */}
        {agent.dataNeeds.length > 0 && (
          <div className="flex flex-col gap-1.5 mb-5">
            {agent.dataNeeds.map((d, i) => (
              <div
                key={i}
                className="flex items-center gap-2.5 px-3.5 py-2 rounded-lg"
                style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.04)' }}
              >
                <span className="text-[13px] flex-1" style={{ color: 'rgba(255,255,255,0.7)' }}>{d.source}</span>
                {d.amount && <span className="text-xs font-medium" style={{ color: '#3FAF7A' }}>{d.amount}</span>}
              </div>
            ))}
          </div>
        )}

        {/* Partners */}
        {agent.humanPartners.length > 0 && (
          <div className="flex gap-2 mb-5">
            {agent.humanPartners.map(name => (
              <div
                key={name}
                className="flex items-center gap-2 px-3 py-1.5 rounded-full"
                style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)' }}
              >
                <div
                  className="w-6 h-6 rounded-full flex items-center justify-center text-[9px] font-bold text-white"
                  style={{ background: getPersonaColor(name) }}
                >
                  {name.split(' ').map(w => w[0]).join('').slice(0, 2)}
                </div>
                <span className="text-xs font-medium" style={{ color: 'rgba(255,255,255,0.6)' }}>{name}</span>
              </div>
            ))}
          </div>
        )}

        {/* Human value statement */}
        {agent.humanValueStatement && (
          <div
            className="text-[13px] leading-relaxed p-3.5 rounded-[9px] mb-4"
            style={{ color: 'rgba(255,255,255,0.78)', background: 'rgba(63,175,122,0.08)', borderLeft: '3px solid #3FAF7A' }}
          >
            <span className="text-[9px] font-semibold uppercase tracking-wide block mb-1" style={{ color: '#3FAF7A' }}>Human Value</span>
            {agent.humanValueStatement}
          </div>
        )}

        {/* Growth */}
        {agent.growth && !agent.humanValueStatement && (
          <div
            className="text-sm leading-[1.65] p-3.5 rounded-[9px] mb-4"
            style={{ color: 'rgba(255,255,255,0.65)', background: 'rgba(4,65,89,0.12)', borderLeft: '3px solid rgba(4,65,89,0.4)' }}
          >
            {agent.growth}
          </div>
        )}

        {/* Insight */}
        {agent.insight && agent.insight !== agent.growth && (
          <div
            className="text-[13px] leading-relaxed italic p-3.5 rounded-lg"
            style={{ color: 'rgba(255,255,255,0.55)', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)' }}
          >
            {agent.insight}
          </div>
        )}
      </div>
    )
  }

  const toolbar = (
    <PresentShareToolbar
      onDownloadPDF={() => window.print()}
      onScreenshot={() => {}}
      contentRef={contentRef}
    />
  )

  return (
    <PresentModeShell
      isOpen={isOpen}
      onClose={onClose}
      totalSlides={totalSlides}
      currentSlide={currentSlide}
      onNavigate={navigate}
      counterLabel={
        currentSlide === 0
          ? 'Meet Your AI Team'
          : currentSlide === totalSlides - 1
            ? 'Team Summary'
            : `Agent ${currentSlide} of ${agents.length}`
      }
      toolbar={toolbar}
    >
      {renderSlide()}
    </PresentModeShell>
  )
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div className="text-center">
      <div className="text-[28px] font-bold" style={{ color: '#3FAF7A' }}>{value}</div>
      <div className="text-[11px] uppercase tracking-wide mt-0.5" style={{ color: 'rgba(255,255,255,0.35)' }}>{label}</div>
    </div>
  )
}

function SumStat({ value, label }: { value: string; label: string }) {
  return (
    <div
      className="p-4.5 rounded-[9px] text-center"
      style={{ background: 'rgba(255,255,255,0.035)', border: '1px solid rgba(255,255,255,0.05)' }}
    >
      <div className="text-[26px] font-bold mb-1" style={{ color: '#3FAF7A' }}>{value}</div>
      <div className="text-[11px]" style={{ color: 'rgba(255,255,255,0.35)' }}>{label}</div>
    </div>
  )
}
