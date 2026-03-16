'use client'

import type { SolutionFlowStepSummary, FlowLayoutPosition, FlowCardSize, PersonaSummary } from '@/types/workspace'
import { SOLUTION_FLOW_PHASES, CONFIDENCE_DOT_COLOR } from '@/lib/solution-flow-constants'

interface FlowStationCardProps {
  step: SolutionFlowStepSummary
  position: FlowLayoutPosition
  sizeClass: FlowCardSize
  personas: PersonaSummary[]
  isSelected: boolean
  isDimmed: boolean
  onClick: () => void
  animationDelay?: number
}

const VALUE_BADGE_STYLES = {
  Transform: { bg: 'rgba(63,175,122,0.08)', color: '#2A8F5F', label: 'Transform' },
  Amplify: { bg: 'rgba(4,65,89,0.06)', color: '#044159', label: 'Amplify' },
  Connect: { bg: 'rgba(10,30,47,0.04)', color: '#0A1E2F', label: 'Connect' },
  Unlock: { bg: 'rgba(63,175,122,0.12)', color: '#2A8F5F', label: 'Unlock' },
} as const

function getPersonaColor(name: string): string {
  // Deterministic color from name hash — brand-safe palette
  const palette = ['#3FAF7A', '#044159', '#2D6B4A', '#0A1E2F']
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
  return palette[Math.abs(hash) % palette.length]
}

function getInitials(name: string): string {
  return name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
}

export function FlowStationCard({
  step,
  position,
  sizeClass,
  personas,
  isSelected,
  isDimmed,
  onClick,
  animationDelay = 0,
}: FlowStationCardProps) {
  const phase = SOLUTION_FLOW_PHASES[step.phase]
  const isHero = sizeClass === 'size-hero'

  // Derive value badges from step data
  const badges: (keyof typeof VALUE_BADGE_STYLES)[] = []
  if (step.confidence_breakdown?.known) badges.push('Transform')
  if (step.info_field_count > 4) badges.push('Connect')

  // Match actors to persona data for colors
  const actorDots = step.actors.slice(0, 4).map(actorName => {
    const persona = personas.find(p => p.name === actorName)
    return {
      name: actorName,
      color: getPersonaColor(actorName),
      initials: getInitials(persona?.name || actorName),
    }
  })

  const confidenceColor = step.confirmation_status === 'confirmed_client'
    ? '#3FAF7A'
    : step.confirmation_status === 'confirmed_consultant'
      ? '#0A1E2F'
      : '#E5E5E5'

  return (
    <div
      className={`absolute bg-white border rounded-xl cursor-pointer transition-all duration-300 flex flex-col gap-1.5 ${
        isSelected ? 'border-[#3FAF7A] shadow-[0_0_0_2px_rgba(63,175,122,0.25)]' : 'border-[#E5E5E5]'
      } ${isDimmed ? 'opacity-25 grayscale-[40%] pointer-events-none' : ''} ${
        isHero ? 'border-2 border-[rgba(63,175,122,0.25)] shadow-[0_2px_10px_rgba(63,175,122,0.08)]' : ''
      }`}
      style={{
        left: position.x,
        top: position.y,
        width: position.w,
        height: position.h,
        padding: '14px 16px',
        borderLeftWidth: 3,
        borderLeftColor: confidenceColor,
        animationDelay: `${animationDelay}ms`,
      }}
      onClick={onClick}
      onMouseEnter={e => {
        if (!isDimmed) {
          e.currentTarget.style.borderColor = '#3FAF7A'
          e.currentTarget.style.boxShadow = '0 6px 20px rgba(63,175,122,0.12)'
          e.currentTarget.style.transform = 'translateY(-3px)'
        }
      }}
      onMouseLeave={e => {
        if (!isSelected) {
          e.currentTarget.style.borderColor = isHero ? 'rgba(63,175,122,0.25)' : '#E5E5E5'
          e.currentTarget.style.boxShadow = isHero ? '0 2px 10px rgba(63,175,122,0.08)' : 'none'
          e.currentTarget.style.transform = 'translateY(0)'
        }
      }}
    >
      {/* Phase + Step Index */}
      <div className="flex items-center gap-1.5">
        {phase && (
          <span
            className="text-[9px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded"
            style={{ background: 'rgba(63,175,122,0.08)', color: '#2A8F5F' }}
          >
            {phase.label}
          </span>
        )}
        <span className="text-[9px] font-medium" style={{ color: '#999' }}>
          Step {step.step_index + 1}
        </span>
        {/* Value badges */}
        {badges.slice(0, 2).map(badge => (
          <span
            key={badge}
            className="text-[8px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded ml-auto first:ml-auto"
            style={{ background: VALUE_BADGE_STYLES[badge].bg, color: VALUE_BADGE_STYLES[badge].color }}
          >
            {badge}
          </span>
        ))}
      </div>

      {/* Title */}
      <div
        className="font-semibold leading-tight"
        style={{
          fontSize: isHero ? 16 : 14,
          color: '#1D1D1F',
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
        }}
      >
        {step.title}
      </div>

      {/* Goal (truncated) */}
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
        {step.goal}
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Footer: Personas + Field count */}
      <div className="flex items-center justify-between pt-1.5 border-t" style={{ borderColor: '#F5F5F5' }}>
        <div className="flex">
          {actorDots.map((dot, i) => (
            <div
              key={dot.name}
              className="w-[18px] h-[18px] rounded-full flex items-center justify-center text-[7px] font-bold text-white border-2 border-white"
              style={{ background: dot.color, marginLeft: i > 0 ? -4 : 0 }}
              title={dot.name}
            >
              {dot.initials}
            </div>
          ))}
        </div>
        <span className="text-[9px] font-medium" style={{ color: '#999' }}>
          {step.info_field_count} fields
        </span>
      </div>
    </div>
  )
}
