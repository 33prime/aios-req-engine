'use client'

import type { PatternRendererProps } from './types'

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
const EVENT_COLORS = ['#3FAF7A', '#044159', '#D4A017', '#2D6B4A', '#0A1E2F']

export function CalendarPattern({ fields }: PatternRendererProps) {
  const events = fields.slice(0, 5)
  return (
    <div className="rounded-[7px] overflow-hidden" style={{ border: '1px solid #E2E8F0' }}>
      {/* Calendar header */}
      <div className="flex items-center justify-between px-3 py-2" style={{ background: '#EDF2F7' }}>
        <span className="text-[9px] font-semibold" style={{ color: '#0A1E2F' }}>March 2026</span>
        <div className="flex gap-1">
          <button className="text-[9px] px-1.5 py-0.5 rounded" style={{ color: '#718096' }}>&larr;</button>
          <button className="text-[9px] px-1.5 py-0.5 rounded" style={{ color: '#718096' }}>&rarr;</button>
        </div>
      </div>
      {/* Day headers */}
      <div className="grid grid-cols-5 gap-px bg-[#E2E8F0]">
        {DAYS.map(day => (
          <div key={day} className="bg-white px-1.5 py-1 text-center text-[8px] font-semibold" style={{ color: '#718096' }}>
            {day}
          </div>
        ))}
      </div>
      {/* Grid cells */}
      <div className="grid grid-cols-5 gap-px bg-[#E2E8F0]">
        {Array.from({ length: 15 }, (_, i) => {
          const day = i + 1
          const event = events[i % events.length]
          const hasEvent = i < events.length || (i > 6 && i < 10)
          return (
            <div key={i} className="bg-white p-1.5 min-h-[48px]">
              <div className="text-[8px] font-medium mb-0.5" style={{ color: '#4A5568' }}>{day}</div>
              {hasEvent && (
                <div
                  className="rounded-[3px] px-1 py-0.5 text-[7px] truncate"
                  style={{
                    background: `${EVENT_COLORS[i % EVENT_COLORS.length]}12`,
                    color: EVENT_COLORS[i % EVENT_COLORS.length],
                  }}
                >
                  {event?.name || 'Event'}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
