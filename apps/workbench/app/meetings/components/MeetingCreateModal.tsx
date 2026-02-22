'use client'

import { useState } from 'react'
import { X, Calendar, Video, AlertCircle } from 'lucide-react'
import type { MeetingType } from '@/types/api'

interface MeetingCreateModalProps {
  open: boolean
  projects: { id: string; name: string }[]
  googleConnected: boolean
  onClose: () => void
  onSave: (data: {
    project_id: string
    title: string
    meeting_date: string
    meeting_time: string
    meeting_type: MeetingType
    duration_minutes: number
    timezone: string
    description?: string
    create_calendar_event?: boolean
    attendee_emails?: string[]
  }) => Promise<void>
}

const TYPES: { value: MeetingType; label: string }[] = [
  { value: 'discovery', label: 'Discovery' },
  { value: 'validation', label: 'Validation' },
  { value: 'review', label: 'Review' },
  { value: 'other', label: 'Other' },
]

const DURATIONS = [
  { value: 30, label: '30 min' },
  { value: 45, label: '45 min' },
  { value: 60, label: '60 min' },
  { value: 90, label: '90 min' },
  { value: 120, label: '2 hours' },
]

const TIMEZONES = [
  { value: 'America/New_York', label: 'Eastern (ET)' },
  { value: 'America/Chicago', label: 'Central (CT)' },
  { value: 'America/Denver', label: 'Mountain (MT)' },
  { value: 'America/Los_Angeles', label: 'Pacific (PT)' },
  { value: 'UTC', label: 'UTC' },
  { value: 'Europe/London', label: 'London (GMT)' },
]

export function MeetingCreateModal({ open, projects, googleConnected, onClose, onSave }: MeetingCreateModalProps) {
  const [title, setTitle] = useState('')
  const [projectId, setProjectId] = useState(projects[0]?.id || '')
  const [meetingType, setMeetingType] = useState<MeetingType>('discovery')
  const [date, setDate] = useState('')
  const [time, setTime] = useState('10:00')
  const [duration, setDuration] = useState(60)
  const [timezone, setTimezone] = useState('America/New_York')
  const [description, setDescription] = useState('')
  const [createCalendarEvent, setCreateCalendarEvent] = useState(googleConnected)
  const [autoRecord, setAutoRecord] = useState(false)
  const [saving, setSaving] = useState(false)

  if (!open) return null

  const handleSave = async () => {
    if (!title.trim() || !projectId || !date || !time) return
    setSaving(true)
    try {
      await onSave({
        project_id: projectId,
        title: title.trim(),
        meeting_date: date,
        meeting_time: time,
        meeting_type: meetingType,
        duration_minutes: duration,
        timezone,
        description: description.trim() || undefined,
        create_calendar_event: createCalendarEvent && googleConnected,
      })
      // Reset
      setTitle('')
      setDescription('')
      setDate('')
      setTime('10:00')
      setMeetingType('discovery')
      setDuration(60)
    } finally {
      setSaving(false)
    }
  }

  const labelCls = 'block text-[12px] font-medium text-[#666666] mb-1'
  const inputCls = 'w-full px-3 py-1.5 text-[13px] bg-white border border-gray-200 rounded-md focus:outline-none focus:ring-1 focus:ring-[#3FAF7A] focus:border-[#3FAF7A]'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <div className="relative bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <h2 className="text-[16px] font-semibold text-[#37352f]">Schedule Meeting</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 transition-colors">
            <X className="w-4 h-4 text-gray-400" />
          </button>
        </div>

        {/* Body */}
        <div className="px-5 py-4 space-y-3">
          {/* Title */}
          <div>
            <label className={labelCls}>Title *</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Requirements Kickoff with Acme Corp"
              className={inputCls}
            />
          </div>

          {/* Project */}
          <div>
            <label className={labelCls}>Project *</label>
            <select
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              className={inputCls}
            >
              <option value="">Select project...</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>

          {/* Meeting Type — pill selector */}
          <div>
            <label className={labelCls}>Meeting Type</label>
            <div className="flex gap-2 flex-wrap">
              {TYPES.map((t) => (
                <button
                  key={t.value}
                  type="button"
                  onClick={() => setMeetingType(t.value)}
                  className={`
                    px-3 py-1.5 text-[12px] font-medium rounded-full border transition-colors
                    ${meetingType === t.value
                      ? 'bg-[#E8F5E9] text-[#25785A] border-[#3FAF7A]'
                      : 'bg-white text-[#666] border-gray-200 hover:border-gray-300'
                    }
                  `}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* Date + Time + Duration */}
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className={labelCls}>Date *</label>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className={inputCls}
              />
            </div>
            <div>
              <label className={labelCls}>Time *</label>
              <input
                type="time"
                value={time}
                onChange={(e) => setTime(e.target.value)}
                className={inputCls}
              />
            </div>
            <div>
              <label className={labelCls}>Duration</label>
              <select
                value={duration}
                onChange={(e) => setDuration(Number(e.target.value))}
                className={inputCls}
              >
                {DURATIONS.map((d) => (
                  <option key={d.value} value={d.value}>{d.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Timezone */}
          <div>
            <label className={labelCls}>Timezone</label>
            <select
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              className={inputCls}
            >
              {TIMEZONES.map((tz) => (
                <option key={tz.value} value={tz.value}>{tz.label}</option>
              ))}
            </select>
          </div>

          {/* Description */}
          <div>
            <label className={labelCls}>Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              placeholder="Meeting purpose and context (optional)"
              className={`${inputCls} resize-none`}
            />
          </div>

          {/* Toggles */}
          <div className="border-t border-gray-100 pt-3 space-y-2.5">
            {/* Calendar toggle */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <Calendar className="w-4 h-4 text-[#999]" />
                <div>
                  <p className="text-[13px] font-medium text-[#37352f]">Create Google Calendar event</p>
                  {googleConnected ? (
                    <p className="text-[11px] text-[#999999]">Auto-generates a Google Meet link</p>
                  ) : (
                    <p className="text-[11px] text-[#999] flex items-center gap-1">
                      <AlertCircle className="w-3 h-3" />
                      Connect Google in Settings to enable
                    </p>
                  )}
                </div>
              </div>
              <button
                type="button"
                disabled={!googleConnected}
                onClick={() => setCreateCalendarEvent(!createCalendarEvent)}
                className={`
                  relative w-9 h-5 rounded-full transition-colors flex-shrink-0
                  ${!googleConnected ? 'bg-gray-100 cursor-not-allowed' : createCalendarEvent ? 'bg-[#3FAF7A]' : 'bg-gray-200'}
                `}
              >
                <span
                  className={`
                    absolute top-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-transform
                    ${createCalendarEvent && googleConnected ? 'left-[18px]' : 'left-0.5'}
                  `}
                />
              </button>
            </div>

            {/* Recording toggle */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <Video className="w-4 h-4 text-[#999]" />
                <div>
                  <p className="text-[13px] font-medium text-[#37352f]">Auto-record this meeting</p>
                  <p className="text-[11px] text-[#999999]">Participants receive consent notifications</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setAutoRecord(!autoRecord)}
                className={`
                  relative w-9 h-5 rounded-full transition-colors flex-shrink-0
                  ${autoRecord ? 'bg-[#3FAF7A]' : 'bg-gray-200'}
                `}
              >
                <span
                  className={`
                    absolute top-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-transform
                    ${autoRecord ? 'left-[18px]' : 'left-0.5'}
                  `}
                />
              </button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-gray-100">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-[13px] font-medium text-gray-600 bg-white border border-gray-200 rounded-md hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!title.trim() || !projectId || !date || !time || saving}
            className="px-3 py-1.5 text-[13px] font-medium text-white bg-[#3FAF7A] rounded-md hover:bg-[#25785A] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? 'Scheduling...' : 'Schedule Meeting'}
          </button>
        </div>
      </div>
    </div>
  )
}
