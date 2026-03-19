'use client'

import { LANE_CONFIG } from '@/lib/solution-flow-constants'

interface PhaseTransitionSlideProps {
  phaseName: string
  phaseLabel: string
  subtitle: string
  stepCount: number
  phaseIndex: number
}

// Accent colors adapted from PHASE_CARD_STYLE for dark background usage
const PHASE_DARK_ACCENTS: Record<string, { lineColor: string; pillBg: string; pillText: string; subtitleColor: string }> = {
  entry: {
    lineColor: '#044159',
    pillBg: 'rgba(4,65,89,0.2)',
    pillText: 'rgba(4,65,89,0.9)',
    subtitleColor: 'rgba(255,255,255,0.35)',
  },
  core_experience: {
    lineColor: '#3FAF7A',
    pillBg: 'rgba(63,175,122,0.15)',
    pillText: '#3FAF7A',
    subtitleColor: 'rgba(255,255,255,0.4)',
  },
  output: {
    lineColor: 'rgba(255,255,255,0.25)',
    pillBg: 'rgba(255,255,255,0.08)',
    pillText: 'rgba(255,255,255,0.7)',
    subtitleColor: 'rgba(255,255,255,0.35)',
  },
  admin: {
    lineColor: '#718096',
    pillBg: 'rgba(113,128,150,0.15)',
    pillText: '#A0AEC0',
    subtitleColor: 'rgba(255,255,255,0.3)',
  },
}

const DEFAULT_ACCENT = PHASE_DARK_ACCENTS.core_experience

export function PhaseTransitionSlide({
  phaseName,
  phaseLabel,
  subtitle,
  stepCount,
  phaseIndex: _phaseIndex,
}: PhaseTransitionSlideProps) {
  const accent = PHASE_DARK_ACCENTS[phaseName] || DEFAULT_ACCENT
  // Use LANE_CONFIG for fallback label/subtitle
  const lane = LANE_CONFIG[phaseName]
  const displayLabel = phaseLabel || lane?.label || phaseName
  const displaySubtitle = subtitle || lane?.subtitle || ''

  return (
    <div className="flex flex-col items-center justify-center text-center" style={{ minHeight: 300 }}>
      {/* Decorative line */}
      <div
        className="mb-6"
        style={{
          width: 60,
          height: 2,
          background: accent.lineColor,
          borderRadius: 1,
        }}
      />

      {/* Phase label */}
      <h2
        className="text-[36px] font-bold text-white mb-2"
        style={{ letterSpacing: '-0.02em', lineHeight: 1.2 }}
      >
        {displayLabel}
      </h2>

      {/* Subtitle */}
      <p
        className="text-[15px] mb-5"
        style={{ color: accent.subtitleColor }}
      >
        {displaySubtitle}
      </p>

      {/* Step count pill */}
      <span
        className="text-[12px] font-semibold px-3.5 py-1.5 rounded-full"
        style={{ background: accent.pillBg, color: accent.pillText }}
      >
        {stepCount} step{stepCount !== 1 ? 's' : ''}
      </span>
    </div>
  )
}
