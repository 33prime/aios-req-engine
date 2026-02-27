'use client'

import type { BusinessDriver, VisionAlignment } from '@/types/workspace'

interface ImportanceDotsProps {
  driver: BusinessDriver
}

interface DotInfo {
  filled: boolean
  strong: boolean
  label: string
}

function getDots(driver: BusinessDriver): DotInfo[] {
  const evidenceCount = driver.evidence?.length ?? 0
  const featureCount = driver.linked_feature_count ?? 0
  const personaCount = driver.linked_persona_count ?? 0
  const alignment = driver.vision_alignment

  return [
    {
      filled: evidenceCount >= 1,
      strong: evidenceCount >= 3,
      label: evidenceCount > 0 ? `${evidenceCount} evidence source${evidenceCount !== 1 ? 's' : ''}` : 'no evidence',
    },
    {
      filled: featureCount >= 1,
      strong: featureCount >= 3,
      label: featureCount > 0 ? `${featureCount} feature${featureCount !== 1 ? 's' : ''} linked` : 'no features linked',
    },
    {
      filled: personaCount >= 1,
      strong: false,
      label: personaCount > 0 ? `${personaCount} persona${personaCount !== 1 ? 's' : ''} linked` : 'no persona',
    },
    {
      filled: alignment === 'high' || alignment === 'medium',
      strong: alignment === 'high',
      label: alignment ? `${alignment} alignment` : 'no alignment data',
    },
  ]
}

export function ImportanceDots({ driver }: ImportanceDotsProps) {
  const dots = getDots(driver)
  const tooltip = dots.map(d => d.label).join(', ')

  return (
    <div className="flex items-center gap-1" title={tooltip}>
      {dots.map((dot, i) => (
        <span
          key={i}
          className={`w-1.5 h-1.5 rounded-full ${
            dot.strong
              ? 'bg-[#25785A]'
              : dot.filled
                ? 'bg-brand-primary'
                : 'bg-border'
          }`}
        />
      ))}
    </div>
  )
}
