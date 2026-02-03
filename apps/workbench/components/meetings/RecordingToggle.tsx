'use client'

import { useCallback, useEffect, useState } from 'react'
import { Mic, MicOff, Loader, AlertCircle, CheckCircle } from 'lucide-react'
import { deployBot, getBotStatus, cancelBot } from '@/lib/api'
import type { MeetingBot, BotStatus, ConsentStatus } from '@/types/api'

interface RecordingToggleProps {
  meetingId: string
  recordingEnabled?: boolean
  onRecordingChange?: (enabled: boolean) => void
  compact?: boolean
}

const STATUS_LABELS: Record<BotStatus, string> = {
  deploying: 'Deploying...',
  joining: 'Joining...',
  recording: 'Recording',
  processing: 'Processing...',
  done: 'Complete',
  failed: 'Failed',
  cancelled: 'Cancelled',
}

const CONSENT_LABELS: Record<ConsentStatus, string> = {
  pending: 'Consent Pending',
  all_consented: 'All Consented',
  opted_out: 'Opted Out',
  expired: 'Expired',
}

export function RecordingToggle({
  meetingId,
  recordingEnabled = false,
  onRecordingChange,
  compact = false,
}: RecordingToggleProps) {
  const [bot, setBot] = useState<MeetingBot | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchBotStatus = useCallback(async () => {
    try {
      const data = await getBotStatus(meetingId)
      setBot(data)
    } catch {
      // No bot deployed — that's fine
      setBot(null)
    }
  }, [meetingId])

  useEffect(() => {
    fetchBotStatus()
  }, [fetchBotStatus])

  // Poll for status when bot is active
  useEffect(() => {
    if (!bot || ['done', 'failed', 'cancelled'].includes(bot.status)) return

    const interval = setInterval(fetchBotStatus, 5000)
    return () => clearInterval(interval)
  }, [bot, fetchBotStatus])

  const handleDeploy = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await deployBot(meetingId)
      setBot(data)
      onRecordingChange?.(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to deploy recorder')
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = async () => {
    if (!bot) return
    setLoading(true)
    setError(null)
    try {
      await cancelBot(bot.id)
      setBot(null)
      onRecordingChange?.(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel')
    } finally {
      setLoading(false)
    }
  }

  const isActive = bot && !['done', 'failed', 'cancelled'].includes(bot.status)
  const isRecording = bot?.status === 'recording'
  const isDone = bot?.status === 'done'

  if (compact) {
    return (
      <div className="flex items-center gap-2">
        {isRecording && (
          <span className="flex items-center gap-1 text-xs text-red-500">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            Recording
          </span>
        )}
        {isDone && (
          <span className="flex items-center gap-1 text-xs text-emerald-600">
            <CheckCircle className="w-3 h-3" />
            Recorded
          </span>
        )}
        {!bot && recordingEnabled && (
          <button
            onClick={handleDeploy}
            disabled={loading}
            className="flex items-center gap-1 text-xs text-zinc-500 hover:text-emerald-600"
          >
            <Mic className="w-3 h-3" />
            {loading ? 'Starting...' : 'Record'}
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isRecording ? (
            <Mic className="w-4 h-4 text-red-500" />
          ) : (
            <MicOff className="w-4 h-4 text-zinc-400" />
          )}
          <span className="text-sm font-medium text-zinc-700">Meeting Recording</span>
        </div>

        {!isActive && !isDone && (
          <button
            onClick={handleDeploy}
            disabled={loading}
            className="text-xs bg-emerald-50 text-emerald-700 px-3 py-1 rounded-md hover:bg-emerald-100 disabled:opacity-50"
          >
            {loading ? (
              <span className="flex items-center gap-1">
                <Loader className="w-3 h-3 animate-spin" />
                Deploying...
              </span>
            ) : (
              'Deploy Recorder'
            )}
          </button>
        )}

        {isActive && (
          <button
            onClick={handleCancel}
            disabled={loading}
            className="text-xs bg-red-50 text-red-700 px-3 py-1 rounded-md hover:bg-red-100 disabled:opacity-50"
          >
            Cancel
          </button>
        )}
      </div>

      {error && (
        <div className="flex items-center gap-1 text-xs text-red-600">
          <AlertCircle className="w-3 h-3" />
          {error}
        </div>
      )}

      {bot && (
        <div className="bg-zinc-50 border border-zinc-200 rounded-lg p-3 space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-zinc-600">
              Status: {STATUS_LABELS[bot.status]}
            </span>
            {isRecording && (
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                <span className="text-xs text-red-500">Live</span>
              </span>
            )}
          </div>

          <div className="text-xs text-zinc-400">
            Consent: {CONSENT_LABELS[bot.consent_status]}
          </div>

          {bot.error_message && (
            <div className="text-xs text-red-500">{bot.error_message}</div>
          )}
        </div>
      )}
    </div>
  )
}
