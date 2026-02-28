'use client'

import { Clock } from 'lucide-react'
import type { HorizonCard } from '@/types/epic-overlay'

interface HorizonCardComponentProps {
  card: HorizonCard
  isActive?: boolean
}

const HORIZON_COLORS: Record<number, { bg: string; border: string; badge: string; text: string }> = {
  1: { bg: 'bg-[#F0FAF4]', border: 'border-brand-primary', badge: 'bg-brand-primary text-white', text: 'text-brand-primary' },
  2: { bg: 'bg-[#E8EDF2]', border: 'border-[#0A1E2F]', badge: 'bg-[#0A1E2F] text-white', text: 'text-[#0A1E2F]' },
  3: { bg: 'bg-[#F4F4F4]', border: 'border-[#666666]', badge: 'bg-[#666666] text-white', text: 'text-[#666666]' },
}

export default function HorizonCardComponent({ card, isActive = false }: HorizonCardComponentProps) {
  const colors = HORIZON_COLORS[card.horizon] || HORIZON_COLORS[1]

  return (
    <div
      className={`rounded-xl border transition-colors ${
        isActive ? `${colors.border} ${colors.bg}` : 'border-border bg-white'
      }`}
    >
      <div className="px-4 py-3">
        {/* Header */}
        <div className="flex items-center gap-2 mb-2">
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${colors.badge}`}>
            H{card.horizon}
          </span>
          <h3 className="text-sm font-semibold text-[#37352f]">{card.title}</h3>
          <span className="text-xs text-text-placeholder ml-auto">{card.subtitle}</span>
        </div>

        {/* Unlocks list */}
        {card.unlock_summaries.length > 0 && (
          <div className="space-y-1 mb-3">
            <h4 className="text-[10px] font-semibold text-[#666666] uppercase tracking-wide flex items-center gap-1">
              <Clock className="w-3 h-3" />
              Unlocks
            </h4>
            <ul className="space-y-0.5 pl-1">
              {card.unlock_summaries.slice(0, 5).map((u, i) => (
                <li key={i} className="text-xs text-[#37352f] flex items-start gap-1.5">
                  <span className="text-text-placeholder mt-0.5">&bull;</span>
                  {u}
                </li>
              ))}
              {card.unlock_summaries.length > 5 && (
                <li className="text-xs text-text-placeholder pl-3">
                  +{card.unlock_summaries.length - 5} more
                </li>
              )}
            </ul>
          </div>
        )}

        {/* Why now */}
        {card.why_now.length > 0 && (
          <div className="mt-2 space-y-0.5">
            <h4 className="text-[10px] font-semibold text-[#666666] uppercase tracking-wide">
              Why Now
            </h4>
            {card.why_now.slice(0, 2).map((w, i) => (
              <p key={i} className="text-xs text-[#666666] italic">
                {w}
              </p>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
