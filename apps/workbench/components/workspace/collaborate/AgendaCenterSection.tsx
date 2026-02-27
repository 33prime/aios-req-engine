'use client'

import { useState } from 'react'
import { Calendar, ChevronDown, ChevronRight, Plus } from 'lucide-react'
import { useMeetings } from '@/lib/hooks/use-api'

interface AgendaCenterSectionProps {
  projectId: string
}

export function AgendaCenterSection({ projectId }: AgendaCenterSectionProps) {
  const [isOpen, setIsOpen] = useState(true)
  const { data: meetings } = useMeetings(projectId, 'scheduled')

  const upcoming = (meetings ?? [])
    .filter(m => new Date(m.meeting_date) >= new Date())
    .sort((a, b) => new Date(a.meeting_date).getTime() - new Date(b.meeting_date).getTime())
    .slice(0, 5)

  return (
    <div className="bg-white rounded-2xl border border-border shadow-sm overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-surface-page transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <Calendar className="w-4 h-4 text-brand-primary" />
          <span className="text-[11px] uppercase tracking-wider text-text-placeholder font-semibold">
            Agenda Center
          </span>
          {upcoming.length > 0 && (
            <span className="px-1.5 py-0.5 bg-brand-primary-light text-[#25785A] text-[10px] font-bold rounded-full min-w-[18px] text-center">
              {upcoming.length}
            </span>
          )}
        </div>
        {isOpen ? <ChevronDown className="w-4 h-4 text-text-placeholder" /> : <ChevronRight className="w-4 h-4 text-text-placeholder" />}
      </button>

      {isOpen && (
        <div className="px-5 pb-4 space-y-3">
          {upcoming.length === 0 ? (
            <p className="text-[12px] text-text-placeholder py-2">No upcoming meetings scheduled.</p>
          ) : (
            upcoming.map(meeting => {
              const date = new Date(meeting.meeting_date)
              const dateLabel = formatAgendaDate(date)
              const time = meeting.meeting_time || date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
              const agendaItems = (meeting.agenda as { items?: string[] })?.items ?? []

              return (
                <div key={meeting.id} className="bg-white rounded-xl border border-border p-4">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h4 className="text-sm font-semibold text-text-body">{meeting.title}</h4>
                      {meeting.description && (
                        <p className="text-[11px] text-text-placeholder mt-0.5 line-clamp-1">{meeting.description}</p>
                      )}
                    </div>
                    <span className="text-[11px] uppercase tracking-wider text-text-placeholder whitespace-nowrap ml-3">
                      {dateLabel}, {time}
                    </span>
                  </div>

                  {agendaItems.length > 0 && (
                    <div className="mt-3">
                      <p className="text-[11px] font-medium text-[#666666] mb-1.5">
                        Agenda ({agendaItems.length} items)
                      </p>
                      <ul className="space-y-1">
                        {agendaItems.map((item, i) => (
                          <li key={i} className="flex items-start gap-2 text-sm text-[#666666]">
                            <span className="w-1.5 h-1.5 rounded-full bg-brand-primary mt-1.5 flex-shrink-0" />
                            {item}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="flex items-center justify-between mt-3 pt-3 border-t border-[#F4F4F4]">
                    <button className="text-[11px] text-brand-primary hover:text-[#25785A] font-medium flex items-center gap-1">
                      <Plus className="w-3 h-3" />
                      Add Item
                    </button>
                    <button className="text-[11px] text-[#666666] hover:text-text-body font-medium">
                      Push to Portal
                    </button>
                  </div>
                </div>
              )
            })
          )}
        </div>
      )}
    </div>
  )
}

function formatAgendaDate(date: Date): string {
  const now = new Date()
  const tomorrow = new Date(now)
  tomorrow.setDate(tomorrow.getDate() + 1)

  if (date.toDateString() === now.toDateString()) return 'Today'
  if (date.toDateString() === tomorrow.toDateString()) return 'Tomorrow'
  return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
}
