'use client'

import { FileText } from 'lucide-react'

interface MeetingNotesProps {
  summary: string | null
  isUpcoming: boolean
}

export function MeetingNotes({ summary, isUpcoming }: MeetingNotesProps) {
  return (
    <div className="mt-7">
      <div className="flex items-center gap-2 mb-3.5">
        <span className="text-[15px] font-semibold text-text-primary">Meeting Notes</span>
        {summary && (
          <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-[#88BABF] bg-[rgba(136,186,191,0.12)] px-[7px] py-[2px] rounded">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor" stroke="none">
              <path d="M12 0L14.59 8.41L23 11L14.59 13.59L12 22L9.41 13.59L1 11L9.41 8.41L12 0Z" transform="scale(0.75) translate(4,4)" />
            </svg>
            AI Generated
          </span>
        )}
      </div>

      <div className="bg-white border border-border rounded-lg p-4 min-h-[120px]">
        {summary ? (
          <div className="text-[13px] text-text-secondary leading-relaxed whitespace-pre-wrap">
            {summary}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <FileText className="w-8 h-8 text-[#D0D0D0] mb-2" />
            <p className="text-[13px] text-text-muted">
              {isUpcoming
                ? 'Notes will appear here after the meeting'
                : 'No summary available — record your next meeting to auto-generate one'}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
