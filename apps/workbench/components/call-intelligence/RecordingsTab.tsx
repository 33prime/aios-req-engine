'use client'

import { useState } from 'react'
import { Phone, Clock, AlertTriangle, Loader2, Plus } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { useCallRecordings } from '@/lib/hooks/use-api'
import { formatDuration } from './constants'
import { StatusBadge } from './StatusBadge'
import { SeedDialog } from './SeedDialog'

export function RecordingsTab({
  projectId,
  onSelectRecording,
}: {
  projectId: string
  onSelectRecording: (recordingId: string) => void
}) {
  const { data: recordings, isLoading, error } = useCallRecordings(projectId)
  const [showSeedDialog, setShowSeedDialog] = useState(false)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-text-muted" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-text-muted gap-2">
        <AlertTriangle className="w-8 h-8 text-[#044159]" />
        <p className="text-sm">Failed to load recordings</p>
      </div>
    )
  }

  return (
    <>
      {showSeedDialog && <SeedDialog projectId={projectId} onClose={() => setShowSeedDialog(false)} />}
      <div className="flex flex-col h-full">
        {/* Actions bar */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-surface-muted">
          <span className="text-xs text-text-muted font-medium">
            {recordings?.length || 0} recording{(recordings?.length || 0) !== 1 ? 's' : ''}
          </span>
          <button
            onClick={() => setShowSeedDialog(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-brand-primary hover:bg-brand-primary-light rounded-md transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            Seed Recording
          </button>
        </div>

        {!recordings || recordings.length === 0 ? (
          <div className="flex flex-col items-center justify-center flex-1 text-text-muted gap-2">
            <Phone className="w-8 h-8" />
            <p className="text-sm">No call recordings yet.</p>
            <p className="text-xs">Record a meeting or seed a recording to get started.</p>
          </div>
        ) : (
          <div className="overflow-y-auto flex-1">
            <table className="w-full">
              <thead className="sticky top-0 bg-surface-muted z-10">
                <tr className="text-xs text-text-muted font-medium uppercase tracking-wide">
                  <th className="text-left px-4 py-3">Recording</th>
                  <th className="text-left px-4 py-3">Status</th>
                  <th className="text-left px-4 py-3">Duration</th>
                  <th className="text-left px-4 py-3">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {recordings.map((rec) => (
                  <tr
                    key={rec.id}
                    onClick={() => rec.status === 'complete' ? onSelectRecording(rec.id) : undefined}
                    className={`text-sm transition-colors ${
                      rec.status === 'complete'
                        ? 'hover:bg-surface-muted cursor-pointer'
                        : 'opacity-70'
                    }`}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Phone className="w-4 h-4 text-text-muted shrink-0" />
                        <span className="text-text-body font-medium truncate">
                          {rec.title || (rec.meeting_id ? 'Meeting Recording' : 'Recording')}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={rec.status} />
                    </td>
                    <td className="px-4 py-3 text-text-muted">
                      <div className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5" />
                        {formatDuration(rec.duration_seconds)}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-text-muted">
                      {formatDistanceToNow(new Date(rec.created_at), { addSuffix: true })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  )
}
