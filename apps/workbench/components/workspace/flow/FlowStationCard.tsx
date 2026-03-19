'use client'

import type { SolutionFlowStepSummary, SolutionFlowStepDetail, PersonaSummary } from '@/types/workspace'
import { PHASE_CARD_STYLE } from '@/lib/solution-flow-constants'

interface FlowStationCardProps {
  step: SolutionFlowStepSummary
  detail?: SolutionFlowStepDetail | null
  personas: PersonaSummary[]
  isSelected: boolean
  isDimmed: boolean
  onClick: () => void
  animationDelay?: number
  isStarred?: boolean
  onToggleStar?: () => void
}

function getPersonaColor(name: string): string {
  const palette = ['#3FAF7A', '#044159', '#2D6B4A', '#0A1E2F']
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
  return palette[Math.abs(hash) % palette.length]
}

function getInitials(name: string): string {
  return name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
}

/** Extract first sentence from a narrative string */
function firstSentence(text: string): string {
  const match = text.match(/^[^.!?]+[.!?]/)
  return match ? match[0] : text.slice(0, 120)
}

export function FlowStationCard({
  step,
  detail,
  personas,
  isSelected,
  isDimmed,
  onClick,
  animationDelay = 0,
  isStarred = false,
  onToggleStar,
}: FlowStationCardProps) {
  const style = PHASE_CARD_STYLE[step.phase] || PHASE_CARD_STYLE.admin
  const isCore = step.phase === 'core_experience'

  // Blurb: prefer story_headline, then first sentence of mock_data_narrative, then goal
  const blurb = detail?.story_headline
    || (detail?.mock_data_narrative ? firstSentence(detail.mock_data_narrative) : step.goal)

  // Transformation snippet for core cards
  const painBefore = detail?.pain_points_addressed?.[0]
  const beforeText = painBefore ? (typeof painBefore === 'string' ? painBefore : painBefore.text) : null
  const afterText = detail?.goals_addressed?.[0] || detail?.success_criteria?.[0] || null
  const showTransform = isCore && beforeText && afterText

  // Actor dots
  const actorDots = step.actors.slice(0, 4).map(actorName => ({
    name: actorName,
    color: getPersonaColor(actorName),
    initials: getInitials(actorName),
  }))

  // Bottom badges
  const hasAI = !!(detail?.ai_config?.role || detail?.ai_config?.ai_role)
  const questionCount = step.open_question_count

  return (
    <div
      className={`rounded-[10px] cursor-pointer transition-all duration-300 relative overflow-hidden ${
        isSelected ? 'shadow-[0_0_0_2px_rgba(63,175,122,0.25)]' : ''
      } ${isDimmed ? 'opacity-[0.15] grayscale-[40%] pointer-events-none' : ''}`}
      style={{
        background: style.bg,
        border: `1px solid ${isSelected ? '#3FAF7A' : style.border}`,
        padding: isCore ? '16px 18px' : '14px 16px',
        animationDelay: `${animationDelay}ms`,
        animation: 'fadeUp 0.4s ease backwards',
      }}
      onClick={onClick}
      onMouseEnter={e => {
        if (!isDimmed) {
          e.currentTarget.style.transform = 'translateY(-2px)'
          e.currentTarget.style.borderColor = style.hoverBorder
          e.currentTarget.style.boxShadow = style.hoverShadow
        }
      }}
      onMouseLeave={e => {
        if (!isSelected) {
          e.currentTarget.style.transform = 'translateY(0)'
          e.currentTarget.style.borderColor = style.border
          e.currentTarget.style.boxShadow = 'none'
        }
      }}
    >
      {/* Top: Index + Title + Persona dots */}
      <div className="flex items-center gap-1.5 mb-[5px]">
        <div
          className="w-5 h-5 rounded-[6px] flex items-center justify-center text-[9px] font-bold flex-shrink-0"
          style={{ background: style.idxBg, color: style.idxColor }}
        >
          {step.step_index + 1}
        </div>
        <div
          className="flex-1 font-semibold leading-tight min-w-0"
          style={{
            fontSize: isCore ? 13 : 12,
            color: '#0A1E2F',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {step.title}
        </div>
        <div className="flex items-center flex-shrink-0 gap-1">
          {actorDots.map((dot, i) => (
            <div
              key={dot.name}
              className="w-4 h-4 rounded-full flex items-center justify-center text-[6px] font-bold text-white border-2 border-white"
              style={{ background: dot.color, marginLeft: i > 0 ? -3 : 0 }}
              title={dot.name}
            >
              {dot.initials}
            </div>
          ))}
          {onToggleStar && (
            <button
              onClick={e => { e.stopPropagation(); onToggleStar() }}
              className="w-4 h-4 flex items-center justify-center text-[10px] transition-all ml-0.5"
              style={{ color: isStarred ? '#D4A017' : 'rgba(0,0,0,0.15)' }}
              title={isStarred ? 'Remove from highlights' : 'Add to highlights'}
            >
              {isStarred ? '\u2605' : '\u2606'}
            </button>
          )}
        </div>
      </div>

      {/* Blurb */}
      <div
        className="leading-[1.5] mb-1.5"
        style={{
          fontSize: isCore ? 11 : 10,
          color: isCore ? '#2D3748' : '#4A5568',
          display: '-webkit-box',
          WebkitLineClamp: 3,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
        }}
      >
        {blurb}
      </div>

      {/* Transformation snippet (core cards only) */}
      {showTransform && (
        <div
          className="flex gap-1.5 items-center rounded-[6px] mb-1"
          style={{ padding: '5px 9px', background: 'rgba(63,175,122,0.05)' }}
        >
          <span className="text-[9px] line-through" style={{ color: '#718096', textDecorationColor: 'rgba(0,0,0,0.18)' }}>
            {beforeText}
          </span>
          <span className="text-[10px] font-bold" style={{ color: '#3FAF7A' }}>→</span>
          <span className="text-[9px] font-semibold" style={{ color: '#2A8F5F' }}>
            {afterText}
          </span>
        </div>
      )}

      {/* Bottom badges */}
      <div className="flex items-center gap-1 mt-1 flex-wrap">
        {hasAI && (
          <span
            className="inline-flex items-center gap-[3px] text-[8px] font-semibold px-[7px] py-[2px] rounded-[3px]"
            style={{ background: 'rgba(4,65,89,0.05)', color: '#044159' }}
          >
            ◈ AI
          </span>
        )}
        {questionCount > 0 && (
          <span
            className="inline-flex items-center gap-[3px] text-[8px] font-semibold px-[7px] py-[2px] rounded-[3px]"
            style={{ background: 'rgba(212,160,23,0.08)', color: '#8B6914' }}
          >
            ? {questionCount}
          </span>
        )}
      </div>

      <style jsx>{`
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}
