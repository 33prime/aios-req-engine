'use client'

import { useState } from 'react'
import { X, Info, Send } from 'lucide-react'
import { format } from 'date-fns'
import type { Meeting } from '@/types/api'
import type { StakeholderDetail } from '@/types/workspace'

function formatTime(timeStr: string): string {
  return format(new Date(`2000-01-01T${timeStr}`), 'h:mm a')
}

function formatEndTime(timeStr: string, durationMinutes: number): string {
  const start = new Date(`2000-01-01T${timeStr}`)
  const end = new Date(start.getTime() + durationMinutes * 60000)
  return format(end, 'h:mm a')
}

const AVATAR_COLORS = ['#044159', '#25785A', '#3FAF7A', '#88BABF', '#0A1E2F']

interface EmailAgendaModalProps {
  open: boolean
  meeting: Meeting
  participants: StakeholderDetail[]
  onClose: () => void
}

export function EmailAgendaModal({ open, meeting, participants, onClose }: EmailAgendaModalProps) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(
    new Set(participants.map((p) => p.id))
  )
  const [customMessage, setCustomMessage] = useState('')

  if (!open) return null

  const toggleRecipient = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const agendaItems = meeting.agenda
    ? Object.entries(meeting.agenda).map(([key, item]) => {
        if (typeof item === 'string') return { title: item, duration: '' }
        const obj = item as Record<string, unknown>
        return {
          title: (obj.title as string) || key,
          duration: obj.duration ? `(${obj.duration} min)` : '',
        }
      })
    : []

  const dateStr = format(new Date(meeting.meeting_date + 'T00:00:00'), 'MMM d, yyyy')
  const timeRange = `${formatTime(meeting.meeting_time)} – ${formatEndTime(meeting.meeting_time, meeting.duration_minutes)} ${meeting.timezone}`

  const handleSend = () => {
    const recipients = participants.filter((p) => selectedIds.has(p.id))
    onClose()
  }

  return (
    <div
      className="fixed inset-0 bg-black/40 z-[1000] flex items-center justify-center"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl w-full max-w-[560px] max-h-[85vh] overflow-y-auto shadow-[0_20px_60px_rgba(0,0,0,0.15)]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 pt-5 pb-4 border-b border-[#F0F0F0] flex items-center justify-between">
          <h3 className="text-[16px] font-semibold text-[#1D1D1F]">Send Agenda to Participants</h3>
          <button onClick={onClose} className="w-7 h-7 rounded-md flex items-center justify-center text-[#7B7B7B] hover:bg-[#F0F0F0] transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5">
          <div className="text-[11px] font-semibold text-[rgba(55,53,47,0.5)] uppercase tracking-[0.3px] mb-2">
            Recipients
          </div>
          <div className="flex flex-col gap-1.5 mb-4">
            {participants.map((p, i) => (
              <label
                key={p.id}
                className="flex items-center gap-2.5 py-1.5 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={selectedIds.has(p.id)}
                  onChange={() => toggleRecipient(p.id)}
                  className="accent-[#044159]"
                />
                <div
                  className="w-6 h-6 rounded-full flex items-center justify-center text-[9px] font-bold text-white flex-shrink-0"
                  style={{ background: `linear-gradient(135deg, ${AVATAR_COLORS[i % AVATAR_COLORS.length]}, ${AVATAR_COLORS[(i + 2) % AVATAR_COLORS.length]})` }}
                >
                  {p.name.split(' ').map((w) => w[0]).join('').toUpperCase().slice(0, 2)}
                </div>
                <div>
                  <div className="text-[13px] font-medium text-[#1D1D1F]">{p.name}</div>
                  {p.email && <div className="text-[11px] text-[#7B7B7B]">{p.email}</div>}
                </div>
              </label>
            ))}
          </div>

          <div className="text-[11px] font-semibold text-[rgba(55,53,47,0.5)] uppercase tracking-[0.3px] mb-2">
            Email Preview
          </div>
          <div className="bg-[#FAFAFA] border border-[#E5E5E5] rounded-md p-4 mb-4 max-h-[200px] overflow-y-auto">
            <h4 className="text-[13px] font-semibold text-[#1D1D1F] mb-2">
              {meeting.title} — Agenda
            </h4>
            <p className="text-[11px] text-[#7B7B7B] mb-2">
              {dateStr} &middot; {timeRange} {meeting.google_meet_link ? '· Google Meet' : ''}
            </p>
            {agendaItems.length > 0 ? (
              agendaItems.map((item, i) => (
                <div key={i} className="text-[12px] text-[#4B4B4B] py-[3px] border-b border-[#F0F0F0]">
                  <strong>{i + 1}.</strong> {item.title} {item.duration}
                </div>
              ))
            ) : (
              <p className="text-[12px] text-[#7B7B7B] italic">No agenda items to include</p>
            )}
            <p className="text-[11px] text-[#7B7B7B] mt-2">
              Please review and come prepared with any items you'd like to add.
            </p>
          </div>

          <div className="text-[11px] font-semibold text-[rgba(55,53,47,0.5)] uppercase tracking-[0.3px] mb-2">
            Personal Message (optional)
          </div>
          <textarea
            value={customMessage}
            onChange={(e) => setCustomMessage(e.target.value)}
            placeholder="Add a note to participants..."
            className="w-full px-3 py-2 border border-[#E5E5E5] rounded-md text-[13px] font-inherit resize-y min-h-[60px] outline-none focus:border-[#88BABF]"
          />
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-[#F0F0F0] flex items-center justify-between">
          <div className="flex items-center gap-1 text-[11px] text-[#7B7B7B]">
            <Info className="w-3.5 h-3.5" />
            Sent on your behalf via connected Google account
          </div>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-3 py-1.5 text-[12px] font-medium text-[#4B4B4B] bg-[#F5F5F5] rounded-md hover:bg-[#EBEBEB] transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSend}
              disabled={selectedIds.size === 0}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-white bg-[#044159] rounded-md hover:bg-[#033344] transition-colors disabled:opacity-50"
            >
              <Send className="w-3.5 h-3.5" />
              Send via Gmail
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
