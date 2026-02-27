'use client'

import { Calendar, Clock, Video, ArrowUpRight, Users } from 'lucide-react'
import { format, isToday, isTomorrow } from 'date-fns'
import type { Meeting, MeetingType, MeetingStatus } from '@/types/api'

interface MeetingCardsProps {
  meetings: Meeting[]
  onCardClick: (meeting: Meeting) => void
}

const TYPE_CONFIG: Record<MeetingType, { label: string; bg: string; text: string }> = {
  discovery: { label: 'Discovery', bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
  validation: { label: 'Validation', bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
  review: { label: 'Review', bg: 'bg-[#F0F0F0]', text: 'text-[#666]' },
  other: { label: 'Other', bg: 'bg-[#F0F0F0]', text: 'text-[#666]' },
}

const STATUS_CONFIG: Record<MeetingStatus, { label: string; bg: string; text: string }> = {
  scheduled: { label: 'Scheduled', bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
  completed: { label: 'Completed', bg: 'bg-[#F0F0F0]', text: 'text-[#666]' },
  cancelled: { label: 'Cancelled', bg: 'bg-[#F0F0F0]', text: 'text-[#999]' },
}

const AVATAR_COLORS = ['#044159', '#25785A', '#3FAF7A', '#88BABF', '#0A1E2F']

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  if (isToday(d)) return 'Today'
  if (isTomorrow(d)) return 'Tomorrow'
  return format(d, 'EEE, MMM d')
}

function formatTime(timeStr: string): string {
  return format(new Date(`2000-01-01T${timeStr}`), 'h:mm a')
}

export function MeetingCards({ meetings, onCardClick }: MeetingCardsProps) {
  if (meetings.length === 0) {
    return (
      <div className="bg-white rounded-2xl shadow-[0_1px_3px_rgba(0,0,0,0.04)] border border-border p-12 text-center">
        <Calendar className="w-10 h-10 text-gray-300 mx-auto mb-3" />
        <p className="text-[14px] font-medium text-[#37352f] mb-1">No meetings found</p>
        <p className="text-[13px] text-text-placeholder">
          Try adjusting your filters or schedule a new meeting.
        </p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {meetings.map((m) => {
        const type = TYPE_CONFIG[m.meeting_type] || TYPE_CONFIG.other
        const status = STATUS_CONFIG[m.status] || STATUS_CONFIG.scheduled
        const participantCount = m.stakeholder_ids?.length || 0
        const hasRecording = m.google_meet_link && m.status === 'completed'

        return (
          <div
            key={m.id}
            onClick={() => onCardClick(m)}
            className="bg-white rounded-2xl shadow-[0_1px_3px_rgba(0,0,0,0.04)] border border-border hover:shadow-[0_4px_12px_rgba(0,0,0,0.08)] cursor-pointer transition-shadow"
            style={{ padding: '20px' }}
          >
            {/* Header: title + type badge + arrow */}
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <p className="text-[16px] font-bold text-text-primary truncate">{m.title}</p>
                {m.project_name && (
                  <p className="text-[13px] text-[#666] truncate mt-0.5">{m.project_name}</p>
                )}
                <div className="flex items-center gap-2 mt-2">
                  <span className={`inline-block text-[11px] font-semibold px-2.5 py-0.5 rounded-full ${type.bg} ${type.text}`}>
                    {type.label}
                  </span>
                  <span className={`inline-block text-[11px] font-semibold px-2.5 py-0.5 rounded-full ${status.bg} ${status.text}`}>
                    {status.label}
                  </span>
                  {hasRecording && (
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-[#E8F5E9] text-[#25785A]">
                      <Video className="w-3 h-3" />
                      Recorded
                    </span>
                  )}
                </div>
              </div>
              <div
                className="w-8 h-8 rounded-full bg-brand-primary flex items-center justify-center hover:scale-110 transition-transform flex-shrink-0"
              >
                <ArrowUpRight className="w-4 h-4 text-white" />
              </div>
            </div>

            {/* Body: date/time + participants */}
            <div className="grid grid-cols-2 gap-4 mt-5">
              {/* Date & Time */}
              <div>
                <p className="text-[14px] font-bold text-text-primary mb-2">When</p>
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2">
                    <Calendar className="w-3.5 h-3.5 text-brand-primary flex-shrink-0" />
                    <span className="text-[13px] text-[#333]">{formatDate(m.meeting_date)}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Clock className="w-3.5 h-3.5 text-[#999] flex-shrink-0" />
                    <span className="text-[13px] text-[#333]">
                      {formatTime(m.meeting_time)} &middot; {m.duration_minutes} min
                    </span>
                  </div>
                </div>
              </div>

              {/* Participants */}
              <div className="border-l border-border pl-4">
                <p className="text-[14px] font-bold text-text-primary mb-2">Participants</p>
                {participantCount > 0 ? (
                  <div className="flex items-center">
                    {Array.from({ length: Math.min(participantCount, 4) }).map((_, i) => (
                      <div
                        key={i}
                        className="w-7 h-7 rounded-full border-2 border-white flex items-center justify-center text-white text-[9px] font-bold flex-shrink-0"
                        style={{
                          background: AVATAR_COLORS[i % AVATAR_COLORS.length],
                          marginLeft: i > 0 ? '-6px' : '0',
                        }}
                      >
                        {i + 1}
                      </div>
                    ))}
                    {participantCount > 4 && (
                      <div
                        className="w-7 h-7 rounded-full border-2 border-white bg-gray-100 flex items-center justify-center text-[10px] font-semibold text-[#666] flex-shrink-0"
                        style={{ marginLeft: '-6px' }}
                      >
                        +{participantCount - 4}
                      </div>
                    )}
                    <span className="text-[12px] text-[#999] ml-2">
                      {participantCount} {participantCount === 1 ? 'person' : 'people'}
                    </span>
                  </div>
                ) : (
                  <div className="flex items-center gap-1.5 text-[13px] text-[#999]">
                    <Users className="w-3.5 h-3.5" />
                    No participants
                  </div>
                )}
              </div>
            </div>

            {/* Timestamp */}
            {m.google_meet_link && m.status === 'scheduled' && (
              <div className="mt-4 flex items-center gap-1.5 text-[11px] text-[#25785A]">
                <Video className="w-3 h-3" />
                Google Meet linked
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
