'use client'

import { Video, ExternalLink, Mic } from 'lucide-react'
import type { MeetingBot } from '@/types/api'

export function MeetingRecordingControl({
  bot,
  isUpcoming,
  hasGoogleMeet,
  onDeployBot,
}: {
  bot: MeetingBot | null
  isUpcoming: boolean
  hasGoogleMeet: boolean
  onDeployBot: () => void
}) {
  return (
    <div className="mt-7">
      <div className="text-[15px] font-semibold text-text-primary mb-3.5">Recording</div>

      {bot ? (
        <div className="p-4 bg-white border border-border rounded-lg space-y-3">
          <div className="flex items-center gap-2">
            <div
              className={`w-2 h-2 rounded-full ${
                bot.status === 'recording'
                  ? 'bg-red-500 animate-pulse'
                  : bot.status === 'done'
                  ? 'bg-brand-primary'
                  : bot.status === 'failed'
                  ? 'bg-red-400'
                  : 'bg-[#88BABF]'
              }`}
            />
            <span className="text-[13px] font-medium text-text-primary capitalize">{bot.status}</span>
            <span className="text-[11px] text-text-muted capitalize ml-auto">
              Consent: {bot.consent_status.replace('_', ' ')}
            </span>
          </div>

          <div className="flex items-center gap-2">
            {bot.recording_url && (
              <a
                href={bot.recording_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-text-secondary bg-surface-subtle rounded-md hover:bg-[#EBEBEB] transition-colors"
              >
                Recording
                <ExternalLink className="w-3 h-3" />
              </a>
            )}
            {bot.transcript_url && (
              <a
                href={bot.transcript_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-text-secondary bg-surface-subtle rounded-md hover:bg-[#EBEBEB] transition-colors"
              >
                Transcript
                <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
        </div>
      ) : (
        <div className="p-4 bg-white border border-border rounded-lg flex items-center gap-3">
          <Mic className="w-5 h-5 text-[#D0D0D0] shrink-0" />
          {isUpcoming && hasGoogleMeet ? (
            <div className="flex items-center justify-between flex-1">
              <span className="text-[13px] text-text-muted">No bot deployed</span>
              <button
                onClick={onDeployBot}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-white bg-accent rounded-md hover:bg-accent-hover transition-colors"
              >
                <Video className="w-3.5 h-3.5" />
                Deploy Bot
              </button>
            </div>
          ) : (
            <span className="text-[13px] text-text-muted">
              {isUpcoming ? 'Add a Google Meet link to enable recording' : 'No recording captured'}
            </span>
          )}
        </div>
      )}
    </div>
  )
}
