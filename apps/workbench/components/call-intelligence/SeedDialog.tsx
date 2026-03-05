'use client'

import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import { seedRecording } from '@/lib/api'

export function SeedDialog({
  projectId,
  meetingId,
  onClose,
}: {
  projectId: string
  meetingId?: string
  onClose: () => void
}) {
  const [audioUrl, setAudioUrl] = useState('')
  const [title, setTitle] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async () => {
    if (!audioUrl.trim()) return
    setSubmitting(true)
    try {
      await seedRecording(projectId, audioUrl.trim(), title.trim() || undefined, meetingId)
      onClose()
    } catch (e) {
      console.error('Seed failed:', e)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md space-y-4" onClick={e => e.stopPropagation()}>
        <h3 className="text-lg font-semibold text-text-body">Seed Recording</h3>
        <p className="text-sm text-text-muted">Paste a public audio URL to run the full analysis pipeline without a live call.</p>
        <div className="space-y-3">
          <div>
            <label className="text-xs font-medium text-text-muted block mb-1">Audio URL</label>
            <input
              type="url"
              value={audioUrl}
              onChange={e => setAudioUrl(e.target.value)}
              placeholder="https://example.com/recording.mp3"
              className="w-full px-3 py-2 text-sm border border-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent outline-none"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-text-muted block mb-1">Title (optional)</label>
            <input
              type="text"
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="Discovery Call #1"
              className="w-full px-3 py-2 text-sm border border-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent outline-none"
            />
          </div>
        </div>
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 text-sm text-text-muted hover:text-text-body">Cancel</button>
          <button
            onClick={handleSubmit}
            disabled={!audioUrl.trim() || submitting}
            className="px-4 py-2 text-sm font-medium text-white bg-brand-primary rounded-lg hover:bg-brand-primary-hover disabled:opacity-50"
          >
            {submitting ? (
              <span className="flex items-center gap-1.5">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Seeding...
              </span>
            ) : (
              'Seed Recording'
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
