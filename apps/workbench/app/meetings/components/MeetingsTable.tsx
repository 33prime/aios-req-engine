'use client'

import { Calendar, Clock, Video } from 'lucide-react'
import { format } from 'date-fns'
import type { Meeting, MeetingType, MeetingStatus } from '@/types/api'

interface MeetingsTableProps {
  meetings: Meeting[]
  onRowClick: (meeting: Meeting) => void
}

const TYPE_BADGE: Record<MeetingType, { bg: string; text: string; label: string }> = {
  discovery: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]', label: 'Discovery' },
  validation: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]', label: 'Validation' },
  review: { bg: 'bg-[#F0F0F0]', text: 'text-[#666]', label: 'Review' },
  other: { bg: 'bg-[#F0F0F0]', text: 'text-[#666]', label: 'Other' },
}

const STATUS_BADGE: Record<MeetingStatus, { bg: string; text: string; label: string }> = {
  scheduled: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]', label: 'Scheduled' },
  completed: { bg: 'bg-[#F0F0F0]', text: 'text-[#666]', label: 'Completed' },
  cancelled: { bg: 'bg-[#F0F0F0]', text: 'text-[#999]', label: 'Cancelled' },
}

const AVATAR_COLORS = ['#044159', '#25785A', '#3FAF7A', '#88BABF', '#0A1E2F']

function formatMeetingDate(dateStr: string): string {
  const d = new Date(dateStr)
  return format(d, 'EEE, MMM d')
}

function formatMeetingTime(timeStr: string): string {
  return format(new Date(`2000-01-01T${timeStr}`), 'h:mm a')
}

export function MeetingsTable({ meetings, onRowClick }: MeetingsTableProps) {
  if (meetings.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
        <Calendar className="w-10 h-10 text-gray-300 mx-auto mb-3" />
        <p className="text-[14px] font-medium text-[#37352f] mb-1">No meetings found</p>
        <p className="text-[13px] text-[#999999]">
          Try adjusting your filters or schedule a new meeting.
        </p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <table className="w-full">
        <thead>
          <tr className="border-b border-gray-100 bg-gray-50/50">
            <th className="text-left px-4 py-2.5 text-[11px] font-semibold text-[#999999] uppercase tracking-wider">
              Meeting
            </th>
            <th className="text-left px-4 py-2.5 text-[11px] font-semibold text-[#999999] uppercase tracking-wider">
              Type
            </th>
            <th className="text-left px-4 py-2.5 text-[11px] font-semibold text-[#999999] uppercase tracking-wider">
              Date & Time
            </th>
            <th className="text-left px-4 py-2.5 text-[11px] font-semibold text-[#999999] uppercase tracking-wider">
              Duration
            </th>
            <th className="text-left px-4 py-2.5 text-[11px] font-semibold text-[#999999] uppercase tracking-wider">
              Participants
            </th>
            <th className="text-left px-4 py-2.5 text-[11px] font-semibold text-[#999999] uppercase tracking-wider">
              Status
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {meetings.map((m) => {
            const typeBadge = TYPE_BADGE[m.meeting_type] || TYPE_BADGE.other
            const statusBadge = STATUS_BADGE[m.status] || STATUS_BADGE.scheduled
            const participantCount = m.stakeholder_ids?.length || 0
            const hasRecording = m.google_meet_link && m.status === 'completed'

            return (
              <tr
                key={m.id}
                onClick={() => onRowClick(m)}
                className="hover:bg-gray-50/50 cursor-pointer transition-colors"
              >
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#3FAF7A] to-[#25785A] flex items-center justify-center text-white flex-shrink-0">
                      <Calendar className="w-3.5 h-3.5" />
                    </div>
                    <div className="min-w-0">
                      <span className="text-[13px] font-medium text-[#37352f] truncate block">
                        {m.title}
                      </span>
                      {m.project_name && (
                        <span className="text-[11px] text-[#999999] truncate block">
                          {m.project_name}
                        </span>
                      )}
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${typeBadge.bg} ${typeBadge.text}`}>
                    {typeBadge.label}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="text-[13px] font-medium text-[#37352f]">
                    {formatMeetingDate(m.meeting_date)}
                  </div>
                  <div className="text-[11px] text-[#999999]">
                    {formatMeetingTime(m.meeting_time)}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1 text-[13px] text-[#666666]">
                    <Clock className="w-3 h-3" />
                    {m.duration_minutes} min
                  </div>
                </td>
                <td className="px-4 py-3">
                  {participantCount > 0 ? (
                    <div className="flex items-center">
                      {Array.from({ length: Math.min(participantCount, 3) }).map((_, i) => (
                        <div
                          key={i}
                          className="w-6 h-6 rounded-full border-2 border-white flex items-center justify-center text-white text-[8px] font-bold flex-shrink-0"
                          style={{
                            background: AVATAR_COLORS[i % AVATAR_COLORS.length],
                            marginLeft: i > 0 ? '-6px' : '0',
                          }}
                        >
                          {i + 1}
                        </div>
                      ))}
                      {participantCount > 3 && (
                        <div
                          className="w-6 h-6 rounded-full border-2 border-white bg-gray-100 flex items-center justify-center text-[9px] font-semibold text-[#666] flex-shrink-0"
                          style={{ marginLeft: '-6px' }}
                        >
                          +{participantCount - 3}
                        </div>
                      )}
                    </div>
                  ) : (
                    <span className="text-[12px] text-[#999999]">&mdash;</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${statusBadge.bg} ${statusBadge.text}`}>
                      {statusBadge.label}
                    </span>
                    {hasRecording && (
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-semibold bg-[#E8F5E9] text-[#25785A]">
                        <Video className="w-3 h-3" />
                      </span>
                    )}
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
