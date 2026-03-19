'use client'

/**
 * WorkbenchNode — Full architect-mode agent card for the Intelligence Workbench canvas.
 *
 * Replaces AIAgentCard with richer information: technique badge, I/O columns,
 * confidence bar, rhythm badge, and description.
 */

import type { DerivedAgent, FlowLayoutPosition, FlowCardSize } from '@/types/workspace'

interface Props {
  agent: DerivedAgent
  position: FlowLayoutPosition
  sizeClass: FlowCardSize
  isSelected: boolean
  isDimmed: boolean
  isConnected: boolean
  onClick: () => void
  onHover: (id: string | null) => void
}

const TECHNIQUE_LABELS: Record<string, { label: string; color: string; bg: string }> = {
  llm: { label: 'LLM', color: '#5B21B6', bg: 'rgba(91,33,182,0.08)' },
  classification: { label: 'Classification', color: '#044159', bg: 'rgba(4,65,89,0.08)' },
  embeddings: { label: 'Embeddings', color: '#1B6B3A', bg: 'rgba(63,175,122,0.08)' },
  rules: { label: 'Rules', color: '#8B6914', bg: 'rgba(212,160,23,0.08)' },
  hybrid: { label: 'Hybrid', color: '#0A1E2F', bg: 'rgba(10,30,47,0.08)' },
}

const RHYTHM_LABELS: Record<string, string> = {
  triggered: '⚡ Triggered',
  always_on: '◉ Always On',
  on_demand: '◇ On Demand',
  periodic: '↻ Periodic',
}

export function WorkbenchNode({
  agent,
  position,
  sizeClass,
  isSelected,
  isDimmed,
  isConnected,
  onClick,
  onHover,
}: Props) {
  const technique = TECHNIQUE_LABELS[agent.technique || 'llm']
  const rhythm = RHYTHM_LABELS[agent.rhythm || 'on_demand']
  const isHero = sizeClass === 'size-hero'
  const tiers = agent.confidenceTiers

  return (
    <div
      className="absolute cursor-pointer transition-all duration-200"
      style={{
        left: position.x,
        top: position.y,
        width: position.w,
        opacity: isDimmed ? 0.25 : 1,
        transform: isSelected ? 'translateY(-2px)' : isConnected ? 'translateY(-1px)' : 'none',
        zIndex: isSelected ? 10 : isConnected ? 5 : 1,
      }}
      onClick={onClick}
      onMouseEnter={() => onHover(agent.id)}
      onMouseLeave={() => onHover(null)}
    >
      <div
        className="rounded-xl p-4 h-full transition-all duration-200"
        style={{
          background: '#fff',
          border: `1.5px solid ${
            isSelected
              ? '#3FAF7A'
              : isConnected
                ? 'rgba(63,175,122,0.4)'
                : 'rgba(10,30,47,0.10)'
          }`,
          boxShadow: isSelected
            ? '0 4px 20px rgba(63,175,122,0.15)'
            : isConnected
              ? '0 2px 12px rgba(0,0,0,0.06)'
              : '0 1px 4px rgba(0,0,0,0.04)',
        }}
      >
        {/* Header: Icon + Name + Technique */}
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-lg flex-shrink-0">{agent.icon}</span>
            <div className="min-w-0">
              <p
                className="text-[12px] font-semibold text-[#0A1E2F] truncate"
                style={{ maxWidth: position.w - 80 }}
              >
                {agent.name}
              </p>
            </div>
          </div>
          <span
            className="flex-shrink-0 px-1.5 py-0.5 rounded text-[9px] font-medium"
            style={{ color: technique.color, background: technique.bg }}
          >
            {technique.label}
          </span>
        </div>

        {/* Role description */}
        <p
          className="text-[11px] text-[#4A5568] leading-snug mb-2"
          style={{
            display: '-webkit-box',
            WebkitLineClamp: isHero ? 3 : 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {agent.role}
        </p>

        {/* I/O columns (compact) */}
        <div className="flex gap-3 mb-2">
          <div className="flex-1 min-w-0">
            <p className="text-[9px] font-medium text-[#D4A017] uppercase tracking-wide mb-0.5">
              In
            </p>
            <div className="space-y-0.5">
              {agent.dataNeeds.slice(0, isHero ? 3 : 2).map((d, i) => (
                <p key={i} className="text-[10px] text-[#718096] truncate">
                  {d.source}
                </p>
              ))}
            </div>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[9px] font-medium text-[#3FAF7A] uppercase tracking-wide mb-0.5">
              Out
            </p>
            <div className="space-y-0.5">
              {agent.produces.slice(0, isHero ? 3 : 2).map((p, i) => (
                <p key={i} className="text-[10px] text-[#718096] truncate">
                  {p}
                </p>
              ))}
            </div>
          </div>
        </div>

        {/* Confidence bar */}
        {tiers && (
          <div className="mb-2">
            <div className="flex h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(0,0,0,0.04)' }}>
              {tiers.high > 0 && (
                <div
                  className="h-full"
                  style={{ width: `${tiers.high}%`, background: '#3FAF7A' }}
                />
              )}
              {tiers.medium > 0 && (
                <div
                  className="h-full"
                  style={{ width: `${tiers.medium}%`, background: '#D4A017' }}
                />
              )}
              {tiers.low > 0 && (
                <div
                  className="h-full"
                  style={{ width: `${tiers.low}%`, background: 'rgba(10,30,47,0.15)' }}
                />
              )}
            </div>
          </div>
        )}

        {/* Footer: Rhythm + Maturity */}
        <div className="flex items-center justify-between">
          <span className="text-[9px] text-[#718096]">{rhythm}</span>
          <span
            className="px-1.5 py-0.5 rounded text-[9px] font-medium"
            style={{
              color:
                agent.maturity === 'expert'
                  ? '#1B6B3A'
                  : agent.maturity === 'reliable'
                    ? '#044159'
                    : '#8B6914',
              background:
                agent.maturity === 'expert'
                  ? 'rgba(63,175,122,0.10)'
                  : agent.maturity === 'reliable'
                    ? 'rgba(4,65,89,0.08)'
                    : 'rgba(212,160,23,0.10)',
            }}
          >
            {agent.maturity}
          </span>
        </div>
      </div>
    </div>
  )
}
