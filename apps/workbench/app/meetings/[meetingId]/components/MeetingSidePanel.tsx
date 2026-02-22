'use client'

import { useState } from 'react'
import { Video, ExternalLink, Check, Mic } from 'lucide-react'
import { format } from 'date-fns'
import type { Meeting, MeetingType, MeetingStatus, MeetingBot } from '@/types/api'
import type { StakeholderDetail } from '@/types/workspace'

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

type SidePanelTab = 'recording' | 'details' | 'signals'

function formatTime(timeStr: string): string {
  return format(new Date(`2000-01-01T${timeStr}`), 'h:mm a')
}

function formatEndTime(timeStr: string, durationMinutes: number): string {
  const start = new Date(`2000-01-01T${timeStr}`)
  const end = new Date(start.getTime() + durationMinutes * 60000)
  return format(end, 'h:mm a')
}

interface MeetingSidePanelProps {
  meeting: Meeting
  bot: MeetingBot | null
  participants: StakeholderDetail[]
  onDeployBot: () => void
}

function DetailRow({ label, value, children }: { label: string; value?: string; children?: React.ReactNode }) {
  return (
    <div className="flex items-start py-2 border-b border-[#F5F5F5]">
      <span className="w-[120px] text-[12px] text-[#7B7B7B] flex-shrink-0 pt-[2px]">{label}</span>
      {children || <span className="text-[13px] text-[#1D1D1F] flex-1">{value}</span>}
    </div>
  )
}

export function MeetingSidePanel({ meeting, bot, participants, onDeployBot }: MeetingSidePanelProps) {
  const [activeTab, setActiveTab] = useState<SidePanelTab>('recording')

  const type = TYPE_CONFIG[meeting.meeting_type] || TYPE_CONFIG.other
  const status = STATUS_CONFIG[meeting.status] || STATUS_CONFIG.scheduled
  const isUpcoming = meeting.status === 'scheduled'

  const tabs: { key: SidePanelTab; label: string }[] = [
    { key: 'recording', label: 'Recording' },
    { key: 'details', label: 'Details' },
    { key: 'signals', label: 'Signals' },
  ]

  return (
    <div className="w-[45%] border-l border-[#E5E5E5] bg-white flex flex-col flex-shrink-0 overflow-hidden">
      {/* Tabs */}
      <div className="flex border-b border-[#E5E5E5] flex-shrink-0">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex-1 px-[18px] py-3 text-[13px] font-medium transition-colors border-b-2 ${
              activeTab === tab.key
                ? 'text-[#044159] border-[#044159]'
                : 'text-[#7B7B7B] border-transparent hover:text-[#4B4B4B]'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-5">
          {/* Recording Tab */}
          {activeTab === 'recording' && (
            <div>
              {bot ? (
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <div
                      className={`w-2 h-2 rounded-full ${
                        bot.status === 'recording'
                          ? 'bg-red-500 animate-pulse'
                          : bot.status === 'done'
                          ? 'bg-[#3FAF7A]'
                          : bot.status === 'failed'
                          ? 'bg-red-400'
                          : 'bg-[#88BABF]'
                      }`}
                    />
                    <span className="text-[13px] font-medium text-[#1D1D1F] capitalize">{bot.status}</span>
                  </div>

                  <DetailRow label="Consent" value={bot.consent_status.replace('_', ' ')} />

                  {bot.recording_url && (
                    <div className="bg-[#1a1a2e] rounded-lg aspect-video flex items-center justify-center relative overflow-hidden mb-1">
                      <div className="w-[52px] h-[52px] rounded-full bg-white/15 flex items-center justify-center cursor-pointer hover:bg-white/25 transition-colors">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="white">
                          <polygon points="5 3 19 12 5 21 5 3" />
                        </svg>
                      </div>
                    </div>
                  )}

                  {bot.transcript_url && (
                    <a
                      href={bot.transcript_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-[#4B4B4B] bg-[#F5F5F5] rounded-md hover:bg-[#EBEBEB] transition-colors"
                    >
                      View Transcript
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                  {bot.recording_url && (
                    <a
                      href={bot.recording_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-[#4B4B4B] bg-[#F5F5F5] rounded-md hover:bg-[#EBEBEB] transition-colors ml-2"
                    >
                      View Recording
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <Mic className="w-10 h-10 text-[#D0D0D0] mb-3" />
                  {isUpcoming && meeting.google_meet_link ? (
                    <>
                      <p className="text-[13px] text-[#7B7B7B] mb-3">
                        Recording will appear here after the meeting
                      </p>
                      <button
                        onClick={onDeployBot}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-white bg-[#044159] rounded-md hover:bg-[#033344] transition-colors"
                      >
                        <Video className="w-3.5 h-3.5" />
                        Deploy Recording Bot
                      </button>
                    </>
                  ) : (
                    <p className="text-[13px] text-[#7B7B7B]">
                      {isUpcoming
                        ? 'Add a Google Meet link to enable recording'
                        : 'No recording was captured for this meeting'}
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Details Tab */}
          {activeTab === 'details' && (
            <div>
              <DetailRow label="Type">
                <span className={`inline-flex items-center px-2.5 py-[3px] rounded-[10px] text-[11px] font-semibold ${type.bg} ${type.text}`}>
                  {type.label}
                </span>
              </DetailRow>
              {meeting.project_name && (
                <DetailRow label="Project" value={meeting.project_name} />
              )}
              <DetailRow label="Status">
                <span className={`inline-flex items-center px-2.5 py-[3px] rounded-[10px] text-[11px] font-semibold ${status.bg} ${status.text}`}>
                  {status.label}
                </span>
              </DetailRow>
              <DetailRow
                label="Start time"
                value={`${format(new Date(meeting.meeting_date + 'T00:00:00'), 'MMM d, yyyy')}, ${formatTime(meeting.meeting_time)}`}
              />
              <DetailRow
                label="End time"
                value={`${format(new Date(meeting.meeting_date + 'T00:00:00'), 'MMM d, yyyy')}, ${formatEndTime(meeting.meeting_time, meeting.duration_minutes)}`}
              />
              <DetailRow label="Duration" value={`${meeting.duration_minutes} minutes`} />
              <DetailRow label="Timezone" value={meeting.timezone} />
              <DetailRow label="Participants" value={`${participants.length} people`} />
              <DetailRow
                label="Created"
                value={format(new Date(meeting.created_at), 'MMM d, yyyy h:mm a')}
              />
              <DetailRow
                label="Updated"
                value={format(new Date(meeting.updated_at), 'MMM d, yyyy h:mm a')}
              />

              {/* Integrations section */}
              <div className="mt-4 pt-3 border-t border-[#F0F0F0]">
                <div className="text-[11px] font-semibold text-[#999999] uppercase tracking-[0.3px] mb-2.5">
                  Integrations
                </div>
                <DetailRow label="Google Calendar">
                  {meeting.google_calendar_event_id ? (
                    <span className="inline-flex items-center gap-1 text-[#3FAF7A] text-[12px]">
                      <Check className="w-3.5 h-3.5" />
                      Synced
                    </span>
                  ) : (
                    <span className="text-[12px] text-[#7B7B7B]">Not synced</span>
                  )}
                </DetailRow>
                {meeting.google_meet_link && (
                  <DetailRow label="Google Meet">
                    <a
                      href={meeting.google_meet_link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[12px] text-[#044159] hover:underline truncate block"
                    >
                      {meeting.google_meet_link.replace('https://', '')}
                    </a>
                  </DetailRow>
                )}
              </div>
            </div>
          )}

          {/* Signals Tab */}
          {activeTab === 'signals' && (
            <div>
              <div className="text-[11px] font-semibold text-[#999999] uppercase tracking-[0.3px] mb-3">
                Extracted Signals
              </div>
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <svg
                  className="w-10 h-10 text-[#D0D0D0] mb-3"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                >
                  <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                </svg>
                <p className="text-[13px] text-[#7B7B7B]">
                  Signals extracted from this meeting will appear here
                </p>
                <p className="text-[11px] text-[#B0B0B0] mt-1">
                  Record a meeting to auto-extract features, constraints, and personas
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
