'use client'

import { useState } from 'react'
import { Calendar, ChevronDown } from 'lucide-react'

interface AgendaItem {
  title: string
  description?: string
  duration?: string | number
  questions?: string[]
}

interface MeetingAgendaProps {
  agenda: Record<string, unknown> | null
  isUpcoming: boolean
}

function parseAgendaItems(agenda: Record<string, unknown>): AgendaItem[] {
  return Object.entries(agenda).map(([key, item]) => {
    if (typeof item === 'string') {
      return { title: item }
    }
    const obj = item as Record<string, unknown>
    return {
      title: (obj.title as string) || key,
      description: obj.description as string | undefined,
      duration: obj.duration as string | number | undefined,
      questions: obj.questions as string[] | undefined,
    }
  })
}

export function MeetingAgenda({ agenda, isUpcoming }: MeetingAgendaProps) {
  const [expandedItems, setExpandedItems] = useState<Set<number>>(new Set([0]))

  const items = agenda && Object.keys(agenda).length > 0 ? parseAgendaItems(agenda) : []

  const toggleItem = (index: number) => {
    setExpandedItems((prev) => {
      const next = new Set(prev)
      if (next.has(index)) next.delete(index)
      else next.add(index)
      return next
    })
  }

  const totalDuration = items.reduce((sum, item) => {
    const d = typeof item.duration === 'number' ? item.duration : parseInt(String(item.duration)) || 0
    return sum + d
  }, 0)

  return (
    <div className="mt-7">
      <div className="flex items-center justify-between mb-3.5">
        <div className="text-[15px] font-semibold text-text-primary">Agenda</div>
      </div>

      {items.length > 0 ? (
        <>
          <div className="flex flex-col gap-0">
            {items.map((item, i) => {
              const isExpanded = expandedItems.has(i)
              return (
                <div
                  key={i}
                  className="bg-white border border-border rounded-lg overflow-hidden mb-2 hover:shadow-[0_2px_4px_rgba(0,0,0,0.04)] transition-shadow"
                >
                  <button
                    onClick={() => toggleItem(i)}
                    className="w-full flex items-center gap-2.5 px-3.5 py-3 text-left"
                  >
                    <div className="w-6 h-6 rounded-full bg-[#E0EFF3] text-accent text-[11px] font-bold flex items-center justify-center flex-shrink-0">
                      {i + 1}
                    </div>
                    <div className="flex-1 text-[14px] font-medium text-text-primary">
                      {item.title}
                    </div>
                    {item.duration && (
                      <span className="text-[11px] font-semibold text-text-muted bg-surface-subtle px-2 py-[2px] rounded whitespace-nowrap">
                        {typeof item.duration === 'number' ? `${item.duration} min` : item.duration}
                      </span>
                    )}
                    <ChevronDown
                      className={`w-[18px] h-[18px] text-[#D0D0D0] transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                    />
                  </button>
                  {isExpanded && (item.description || item.questions) && (
                    <div className="px-3.5 pb-3.5 pl-12">
                      {item.description && (
                        <p className="text-[13px] text-text-muted leading-relaxed mb-2">
                          {item.description}
                        </p>
                      )}
                      {item.questions && item.questions.length > 0 && (
                        <ul className="space-y-1">
                          {item.questions.map((q, qi) => (
                            <li key={qi} className="text-[12px] text-text-secondary pl-3.5 relative">
                              <span className="absolute left-0 text-[#88BABF] font-bold">?</span>
                              {q}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {totalDuration > 0 && (
            <div className="flex items-center justify-between pt-3 text-[13px] font-medium text-text-muted">
              <span>{totalDuration} min total</span>
            </div>
          )}
        </>
      ) : (
        <div className="bg-white border border-border rounded-lg py-8 text-center">
          <Calendar className="w-8 h-8 text-[#D0D0D0] mx-auto mb-2" />
          <p className="text-[13px] text-text-muted">
            {isUpcoming
              ? 'No agenda items yet — use chat to generate one'
              : 'No agenda was set for this meeting'}
          </p>
        </div>
      )}
    </div>
  )
}
