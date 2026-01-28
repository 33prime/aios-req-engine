/**
 * EvidenceBadge Component
 *
 * Visual indicator of evidence confidence level.
 * Shows filled/unfilled dots representing confidence tiers.
 *
 * Confidence levels:
 * - client (100%): 5/5 dots - Client confirmed
 * - consultant (90%): 4/5 dots - Consultant confirmed
 * - ai_strong (70%): 3/5 dots - AI with strong evidence
 * - ai_weak (50%): 2/5 dots - AI with some evidence
 * - pending: 1/5 dots - Processing or unverified
 */

interface EvidenceBadgeProps {
  /** Confidence level */
  level: 'client' | 'consultant' | 'ai_strong' | 'ai_weak' | 'pending'
  /** Show label text */
  showLabel?: boolean
  /** Size variant */
  size?: 'sm' | 'md' | 'lg'
}

const LEVEL_CONFIG = {
  client: { dots: 5, label: 'Client Verified', color: 'bg-emerald-500' },
  consultant: { dots: 4, label: 'Consultant Verified', color: 'bg-emerald-400' },
  ai_strong: { dots: 3, label: 'Strong Evidence', color: 'bg-brand-primary' },
  ai_weak: { dots: 2, label: 'Some Evidence', color: 'bg-amber-400' },
  pending: { dots: 1, label: 'Pending', color: 'bg-gray-300' },
}

export function EvidenceBadge({ level, showLabel = false, size = 'sm' }: EvidenceBadgeProps) {
  const config = LEVEL_CONFIG[level] || LEVEL_CONFIG.pending
  const totalDots = 5

  const dotSize = {
    sm: 'w-1.5 h-1.5',
    md: 'w-2 h-2',
    lg: 'w-2.5 h-2.5',
  }[size]

  const gap = {
    sm: 'gap-0.5',
    md: 'gap-1',
    lg: 'gap-1',
  }[size]

  return (
    <div className="flex items-center gap-2">
      <div className={`flex items-center ${gap}`}>
        {Array.from({ length: totalDots }).map((_, i) => (
          <div
            key={i}
            className={`${dotSize} rounded-full ${
              i < config.dots ? config.color : 'bg-gray-200'
            }`}
          />
        ))}
      </div>
      {showLabel && (
        <span className="text-xs text-gray-600">{config.label}</span>
      )}
    </div>
  )
}

/**
 * Compact badge for showing percentage with visual indicator
 */
interface EvidencePercentageBadgeProps {
  /** Percentage of strong evidence (0-100) */
  percentage: number
  /** Optional click handler */
  onClick?: () => void
}

export function EvidencePercentageBadge({ percentage, onClick }: EvidencePercentageBadgeProps) {
  // Determine level based on percentage
  let level: 'client' | 'consultant' | 'ai_strong' | 'ai_weak' | 'pending'
  let label: string

  if (percentage >= 80) {
    level = 'client'
    label = 'Excellent'
  } else if (percentage >= 60) {
    level = 'consultant'
    label = 'Good'
  } else if (percentage >= 40) {
    level = 'ai_strong'
    label = 'Developing'
  } else if (percentage >= 20) {
    level = 'ai_weak'
    label = 'Weak'
  } else {
    level = 'pending'
    label = 'Needs Work'
  }

  const Wrapper = onClick ? 'button' : 'div'

  return (
    <Wrapper
      onClick={onClick}
      className={`flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-50 border border-gray-200 ${
        onClick ? 'cursor-pointer hover:bg-gray-100 transition-colors' : ''
      }`}
    >
      <span className="text-sm font-semibold text-gray-900">{percentage}%</span>
      <EvidenceBadge level={level} size="sm" />
      <span className="text-xs text-gray-500">{label}</span>
    </Wrapper>
  )
}
