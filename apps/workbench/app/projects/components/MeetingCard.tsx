'use client'

import { Calendar } from 'lucide-react'
import type { Meeting } from '@/types/api'

interface MeetingCardProps {
  meeting: Meeting
  onClick?: () => void
}

const typeColors: Record<string, string> = {
  discovery: 'bg-emerald-100 text-emerald-700',
  validation: 'bg-blue-100 text-blue-700',
  review: 'bg-purple-100 text-purple-700',
  other: 'bg-gray-100 text-gray-700',
}

const typeLabels: Record<string, string> = {
  discovery: 'Discovery',
  validation: 'Validation',
  review: 'Review',
  other: 'Meeting',
}

function formatMeetingDateTime(dateStr: string, timeStr: string) {
  try {
    const date = new Date(dateStr)
    const [hours, minutes] = timeStr.split(':')

    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    const month = monthNames[date.getMonth()]
    const day = date.getDate()

    // Format time
    let hour = parseInt(hours, 10)
    const ampm = hour >= 12 ? 'PM' : 'AM'
    hour = hour % 12 || 12
    const formattedTime = `${hour}:${minutes}`

    return `${month} ${day} at ${formattedTime}`
  } catch {
    return dateStr
  }
}

export function MeetingCard({ meeting, onClick }: MeetingCardProps) {
  const meetingType = meeting.meeting_type || 'other'
  const displayTitle = meeting.project_name
    ? `${meeting.title} | ${meeting.project_name}`
    : meeting.title

  return (
    <button
      onClick={onClick}
      className="w-full text-left bg-white rounded-lg border border-gray-200 p-4 hover:border-[#009b87] hover:shadow-sm transition-all"
    >
      {/* Title with project name */}
      <h4 className="font-medium text-gray-900 mb-2 line-clamp-1">
        {displayTitle}
      </h4>

      {/* Meeting type badge */}
      <div className="mb-3">
        <span className={`inline-flex px-2.5 py-0.5 text-xs font-medium rounded-full ${typeColors[meetingType]}`}>
          {typeLabels[meetingType]}
        </span>
      </div>

      {/* Date and time */}
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Calendar className="w-4 h-4" />
        <span>{formatMeetingDateTime(meeting.meeting_date, meeting.meeting_time)}</span>
      </div>
    </button>
  )
}
