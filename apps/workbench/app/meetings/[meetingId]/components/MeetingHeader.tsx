'use client'

import { Calendar, Clock, Video } from 'lucide-react'
import { format } from 'date-fns'
import type { Meeting, MeetingType, MeetingStatus } from '@/types/api'

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

function formatTime(timeStr: string): string {
  return format(new Date(`2000-01-01T${timeStr}`), 'h:mm a')
}

function formatEndTime(timeStr: string, durationMinutes: number): string {
  const start = new Date(`2000-01-01T${timeStr}`)
  const end = new Date(start.getTime() + durationMinutes * 60000)
  return format(end, 'h:mm a')
}

interface MeetingHeaderProps {
  meeting: Meeting
}

export function MeetingHeader({ meeting }: MeetingHeaderProps) {
  const type = TYPE_CONFIG[meeting.meeting_type] || TYPE_CONFIG.other
  const status = STATUS_CONFIG[meeting.status] || STATUS_CONFIG.scheduled

  const dateStr = format(new Date(meeting.meeting_date + 'T00:00:00'), 'MMM d, yyyy')
  const timeRange = `${formatTime(meeting.meeting_time)} – ${formatEndTime(meeting.meeting_time, meeting.duration_minutes)}`

  return (
    <div>
      <h1 className="text-[22px] font-bold text-text-primary mb-3 leading-[1.3]">
        {meeting.title}
      </h1>
      {meeting.description && (
        <p className="text-[14px] text-text-secondary mb-3">{meeting.description}</p>
      )}

      {/* Meta pills row */}
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <span className="inline-flex items-center gap-[5px] px-3 py-1 rounded-full text-[12px] font-medium bg-surface-subtle text-text-secondary border border-border">
          <Calendar className="w-[13px] h-[13px] text-text-muted" />
          {dateStr}, {timeRange} {meeting.timezone}
        </span>
        <span className="inline-flex items-center gap-[5px] px-3 py-1 rounded-full text-[12px] font-medium bg-surface-subtle text-text-secondary border border-border">
          <Clock className="w-[13px] h-[13px] text-text-muted" />
          {meeting.duration_minutes} min
        </span>
        <span className={`inline-flex items-center px-2.5 py-[3px] rounded-[10px] text-[11px] font-semibold ${type.bg} ${type.text}`}>
          {type.label}
        </span>
        <span className={`inline-flex items-center px-2.5 py-[3px] rounded-[10px] text-[11px] font-semibold ${status.bg} ${status.text}`}>
          {status.label}
        </span>
      </div>

      {/* Google Meet link */}
      {meeting.google_meet_link && (
        <div className="mt-[6px]">
          <a
            href={meeting.google_meet_link}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-[5px] px-3 py-1 rounded-full text-[12px] font-medium bg-[#E8F5E9] text-[#25785A] border border-[#C8E6C9] hover:bg-[#D1FAE5] transition-colors"
          >
            <Video className="w-[14px] h-[14px]" />
            Join Google Meet
          </a>
        </div>
      )}
    </div>
  )
}
