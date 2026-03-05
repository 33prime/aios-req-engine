'use client'

import { Check, Minus, X, HelpCircle } from 'lucide-react'

export function GoalStatusBadge({ achieved }: { achieved?: string }) {
  if (!achieved) return <span className="px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-500 rounded-full">Planned</span>
  const styles: Record<string, string> = {
    yes: 'bg-[#E8F5E9] text-[#25785A]',
    partial: 'bg-[#E0EFF3] text-[#044159]',
    no: 'bg-[#044159] text-white',
    unknown: 'bg-gray-100 text-gray-500',
  }
  const icons: Record<string, typeof Check> = { yes: Check, partial: Minus, no: X, unknown: HelpCircle }
  const Icon = icons[achieved] || HelpCircle
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full ${styles[achieved] || styles.unknown}`}>
      <Icon className="w-3 h-3" />
      {achieved === 'yes' ? 'Achieved' : achieved === 'partial' ? 'Partial' : achieved === 'no' ? 'Missed' : 'Unknown'}
    </span>
  )
}
