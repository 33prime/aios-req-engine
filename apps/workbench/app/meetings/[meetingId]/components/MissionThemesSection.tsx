'use client'

import { Compass } from 'lucide-react'
import type { MissionTheme } from '@/types/call-intelligence'

const PRIORITY_CONFIG = {
  critical: { bg: 'bg-[#044159]', text: 'text-white', border: 'border-[#044159]', label: 'Critical' },
  high: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]', border: 'border-[#C8E6C9]', label: 'High' },
  medium: { bg: 'bg-[#F0F0F0]', text: 'text-[#666]', border: 'border-[#E0E0E0]', label: 'Medium' },
} as const

function ConfidenceBar({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100)
  const color = confidence < 0.5 ? 'bg-[#3FAF7A]' : 'bg-[#D0D0D0]'
  const label = confidence < 0.3 ? 'Needs exploration' : confidence < 0.6 ? 'Partially explored' : 'Explored'

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] text-text-muted font-medium shrink-0">{label}</span>
    </div>
  )
}

function MissionThemeCard({ theme, index }: { theme: MissionTheme; index: number }) {
  const priority = PRIORITY_CONFIG[theme.priority] || PRIORITY_CONFIG.medium

  return (
    <div className="p-3.5 bg-white rounded-lg border border-border hover:border-[#D0D0D0] hover:shadow-[0_2px_4px_rgba(0,0,0,0.04)] transition-all">
      {/* Header: priority badge + theme title */}
      <div className="flex items-start gap-2.5">
        <span className="shrink-0 w-6 h-6 rounded-full bg-[#E0EFF3] text-[#044159] text-xs font-bold flex items-center justify-center mt-0.5">
          {index + 1}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-[10px] font-semibold px-1.5 py-[1px] rounded border ${priority.bg} ${priority.text} ${priority.border}`}>
              {priority.label}
            </span>
          </div>
          <p className="text-[13px] font-semibold text-text-primary leading-snug">{theme.theme}</p>
        </div>
      </div>

      {/* Context */}
      {theme.context && (
        <p className="mt-2 text-[12px] text-text-muted leading-relaxed pl-8">
          {theme.context}
        </p>
      )}

      {/* Question — tinted box */}
      {theme.question && (
        <div className="mt-2.5 ml-8 px-3 py-2 bg-[#F0F7FA] border border-[#D4E8EF] rounded-md">
          <p className="text-[12px] text-accent font-medium leading-snug">{theme.question}</p>
        </div>
      )}

      {/* Explores + evidence row */}
      <div className="mt-2.5 pl-8 flex flex-wrap items-center gap-1.5">
        {theme.explores && (
          <span className="px-2 py-0.5 text-[10px] font-medium bg-[#E0EFF3] text-[#044159] rounded-full">
            Explores: {theme.explores}
          </span>
        )}
        {theme.evidence?.map((ev, i) => (
          <span key={i} className="px-1.5 py-0.5 text-[10px] text-text-muted bg-[#F5F5F5] rounded">
            {ev}
          </span>
        ))}
      </div>

      {/* Confidence bar */}
      <div className="mt-2.5 pl-8">
        <ConfidenceBar confidence={theme.confidence} />
      </div>
    </div>
  )
}

export function MissionThemesSection({ themes }: { themes: MissionTheme[] }) {
  if (!themes || themes.length === 0) return null

  return (
    <div className="mt-7">
      <h3 className="text-[13px] font-semibold text-text-muted uppercase tracking-wide flex items-center gap-1.5 mb-3">
        <Compass className="w-3.5 h-3.5" /> Discovery Themes
      </h3>
      <div className="space-y-2.5">
        {themes.map((theme, i) => (
          <MissionThemeCard key={i} theme={theme} index={i} />
        ))}
      </div>
    </div>
  )
}
