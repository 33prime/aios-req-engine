'use client'

import type { DerivedAgent, FlowLayoutPosition, FlowCardSize, PersonaSummary } from '@/types/workspace'

interface AIAgentCardProps {
  agent: DerivedAgent
  position: FlowLayoutPosition
  sizeClass: FlowCardSize
  personas: PersonaSummary[]
  isSelected: boolean
  isDimmed: boolean
  isConnected: boolean
  onClick: () => void
  onHover: () => void
  onUnhover: () => void
  animationDelay?: number
}

const AGENT_TYPE_LABELS: Record<string, string> = {
  processor: 'Processor',
  classifier: 'Classifier',
  matcher: 'Matcher',
  predictor: 'Predictor',
  watcher: 'Watcher',
  generator: 'Generator',
}

const ICON_STYLES: Record<string, { bg: string; color: string }> = {
  classifier: { bg: 'rgba(63,175,122,0.08)', color: '#2A8F5F' },
  matcher: { bg: 'rgba(4,65,89,0.06)', color: '#044159' },
  predictor: { bg: 'rgba(10,30,47,0.05)', color: '#0A1E2F' },
  watcher: { bg: 'rgba(4,65,89,0.06)', color: '#044159' },
  generator: { bg: 'rgba(63,175,122,0.08)', color: '#2A8F5F' },
  processor: { bg: 'rgba(10,30,47,0.04)', color: '#0A1E2F' },
}

const MATURITY_STYLES: Record<string, { bg: string; color: string }> = {
  learning: { bg: 'rgba(4,65,89,0.08)', color: '#044159' },
  reliable: { bg: 'rgba(63,175,122,0.08)', color: '#2A8F5F' },
  expert: { bg: 'rgba(63,175,122,0.15)', color: '#2A8F5F' },
}

function getPersonaColor(name: string): string {
  const palette = ['#3FAF7A', '#044159', '#2D6B4A', '#0A1E2F']
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
  return palette[Math.abs(hash) % palette.length]
}

export function AIAgentCard({
  agent,
  position,
  sizeClass,
  personas,
  isSelected,
  isDimmed,
  isConnected,
  onClick,
  onHover,
  onUnhover,
  animationDelay = 0,
}: AIAgentCardProps) {
  const isHero = sizeClass === 'size-hero'
  const iconStyle = ICON_STYLES[agent.type] || ICON_STYLES.processor
  const matStyle = MATURITY_STYLES[agent.maturity] || MATURITY_STYLES.learning

  const feedsLabel = agent.feedsAgentIds.length
    ? `Feeds ${agent.feedsAgentIds.length} agent${agent.feedsAgentIds.length > 1 ? 's' : ''}`
    : 'End of pipeline'

  return (
    <div
      className={`absolute bg-white rounded-xl cursor-pointer transition-all duration-300 flex flex-col gap-1.5 z-[2] ${
        isSelected ? 'border-[#3FAF7A] shadow-[0_0_0_2px_rgba(63,175,122,0.25)]' : ''
      } ${isDimmed ? 'opacity-25 grayscale-[40%] pointer-events-none' : ''} ${
        isConnected ? 'opacity-100 border-[rgba(63,175,122,0.3)] shadow-[0_2px_8px_rgba(63,175,122,0.08)]' : ''
      }`}
      style={{
        left: position.x,
        top: position.y,
        width: position.w,
        height: position.h,
        padding: '14px 16px',
        border: isSelected
          ? '2px solid #3FAF7A'
          : isHero
            ? '2px solid rgba(63,175,122,0.25)'
            : '1px solid #E5E5E5',
        boxShadow: isHero ? '0 2px 10px rgba(63,175,122,0.08)' : undefined,
        animationDelay: `${animationDelay}ms`,
      }}
      onClick={onClick}
      onMouseEnter={(e) => {
        onHover()
        if (!isDimmed) {
          e.currentTarget.style.borderColor = '#3FAF7A'
          e.currentTarget.style.boxShadow = '0 6px 20px rgba(63,175,122,0.12)'
          e.currentTarget.style.transform = 'translateY(-3px)'
        }
      }}
      onMouseLeave={(e) => {
        onUnhover()
        if (!isSelected) {
          e.currentTarget.style.borderColor = isHero ? 'rgba(63,175,122,0.25)' : '#E5E5E5'
          e.currentTarget.style.boxShadow = isHero ? '0 2px 10px rgba(63,175,122,0.08)' : 'none'
          e.currentTarget.style.transform = 'translateY(0)'
        }
      }}
    >
      {/* Head: icon + maturity */}
      <div className="flex items-center gap-2">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center text-[15px] flex-shrink-0"
          style={{ background: iconStyle.bg, color: iconStyle.color }}
        >
          {agent.icon}
        </div>
        <span
          className="text-[8px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded ml-auto"
          style={{ background: matStyle.bg, color: matStyle.color }}
        >
          {agent.maturity}
        </span>
      </div>

      {/* Name */}
      <div
        className="font-semibold leading-tight"
        style={{ fontSize: isHero ? 16 : 14, color: '#1D1D1F' }}
      >
        {agent.name}
      </div>

      {/* Role (truncated) */}
      <div
        className="text-[11px] leading-relaxed"
        style={{
          color: '#7B7B7B',
          display: '-webkit-box',
          WebkitLineClamp: isHero ? 3 : 2,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
        }}
      >
        {agent.role}
      </div>

      {/* Data pills */}
      <div className="flex gap-1 flex-wrap mt-0.5">
        {agent.dataNeeds.slice(0, 2).map((d, i) => (
          <span
            key={i}
            className="text-[9px] font-medium px-1.5 py-0.5 rounded"
            style={{ background: '#F5F5F5', color: '#4B4B4B' }}
          >
            {d.amount || d.source}
          </span>
        ))}
      </div>

      {/* Automation bar */}
      <div className="mt-1">
        <div className="flex justify-between text-[9px] mb-1" style={{ color: '#999' }}>
          <span>{agent.automationRate}% automated</span>
        </div>
        <div className="h-[3px] rounded-sm overflow-hidden" style={{ background: '#F5F5F5' }}>
          <div
            className="h-full rounded-sm transition-all duration-600"
            style={{ width: `${agent.automationRate}%`, background: '#3FAF7A' }}
          />
        </div>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Footer */}
      <div className="flex items-center justify-between pt-1.5 border-t" style={{ borderColor: '#F5F5F5' }}>
        <div className="flex">
          {agent.humanPartners.slice(0, 3).map((name, i) => (
            <div
              key={name}
              className="w-[18px] h-[18px] rounded-full flex items-center justify-center text-[7px] font-bold text-white border-2 border-white"
              style={{ background: getPersonaColor(name), marginLeft: i > 0 ? -4 : 0 }}
              title={name}
            >
              {name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()}
            </div>
          ))}
        </div>
        <span className="text-[9px] font-medium" style={{ color: '#999' }}>
          {feedsLabel}
        </span>
      </div>
    </div>
  )
}
