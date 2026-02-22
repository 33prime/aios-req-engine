'use client'

import { ChevronRight } from 'lucide-react'
import { useClientPulse } from '@/lib/hooks/use-api'

interface ClientPulseStripProps {
  projectId: string
  onClick?: () => void
}

export function ClientPulseStrip({ projectId, onClick }: ClientPulseStripProps) {
  const { data: pulse } = useClientPulse(projectId)

  if (!pulse) return null

  const stats: string[] = []
  if (pulse.pending_count > 0) stats.push(`${pulse.pending_count} pending`)
  if (pulse.unread_count > 0) stats.push(`${pulse.unread_count} new`)
  if (pulse.next_meeting) {
    const d = new Date(pulse.next_meeting.date)
    const day = d.toLocaleDateString('en-US', { weekday: 'short' })
    const time = d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
    stats.push(`${day} ${time}`)
  }

  if (stats.length === 0) return null

  return (
    <button
      onClick={onClick}
      className="flex items-center justify-between w-full bg-[#F9F9F9] rounded-lg p-2.5 mx-3 mb-2 border border-[#E5E5E5] cursor-pointer hover:bg-[#F4F4F4] transition-colors"
      style={{ width: 'calc(100% - 24px)' }}
    >
      <div className="flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-[#3FAF7A] flex-shrink-0" />
        <span className="text-[11px] text-[#666666]">
          {stats.map((s, i) => (
            <span key={i}>
              {i > 0 && <span className="mx-1 text-[#CCCCCC]">&middot;</span>}
              <span className="font-medium text-[#333333]">{s}</span>
            </span>
          ))}
        </span>
      </div>
      <ChevronRight className="w-3.5 h-3.5 text-[#999999] flex-shrink-0" />
    </button>
  )
}
