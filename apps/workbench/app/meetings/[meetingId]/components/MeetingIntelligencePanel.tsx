'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  BarChart3,
  Award,
  Mic,
  Video,
  Play,
  Plus,
  Loader2,
} from 'lucide-react'
import type { Meeting, MeetingBot } from '@/types/api'
import type { CallRecording, CallDetails, CallStrategyBrief } from '@/types/call-intelligence'
import {
  getRecordingForMeeting,
  getCallDetails,
} from '@/lib/api'
import {
  InsightsView,
  PerformanceView,
  RecordingPlayerView,
  SeedDialog,
  StatusBadge,
} from '@/components/call-intelligence'

type IntelTab = 'recording' | 'insights' | 'performance' | 'signals'

const TERMINAL_STATUSES = new Set(['complete', 'failed', 'skipped'])

export function MeetingIntelligencePanel({
  meeting,
  bot,
  projectId,
  onDeployBot,
  brief,
}: {
  meeting: Meeting
  bot: MeetingBot | null
  projectId: string
  onDeployBot: () => void
  brief?: CallStrategyBrief | null
}) {
  const [activeTab, setActiveTab] = useState<IntelTab>('recording')
  const [recording, setRecording] = useState<CallRecording | null>(null)
  const [details, setDetails] = useState<CallDetails | null>(null)
  const [loadingRecording, setLoadingRecording] = useState(true)
  const [showSeedDialog, setShowSeedDialog] = useState(false)

  // Load recording linked to this meeting
  const loadRecording = useCallback(async () => {
    try {
      const rec = await getRecordingForMeeting(meeting.id)
      setRecording(rec)
    } catch {
      setRecording(null)
    } finally {
      setLoadingRecording(false)
    }
  }, [meeting.id])

  useEffect(() => {
    loadRecording()
  }, [loadRecording])

  // If recording exists and is complete, fetch details
  useEffect(() => {
    if (!recording || recording.status !== 'complete') {
      setDetails(null)
      return
    }
    getCallDetails(recording.id)
      .then(d => setDetails(d))
      .catch(() => setDetails(null))
  }, [recording?.id, recording?.status])

  // Poll for in-progress recordings
  useEffect(() => {
    if (!recording || TERMINAL_STATUSES.has(recording.status)) return
    const interval = setInterval(async () => {
      try {
        const rec = await getRecordingForMeeting(meeting.id)
        setRecording(rec)
        if (TERMINAL_STATUSES.has(rec.status)) clearInterval(interval)
      } catch {
        // ignore
      }
    }, 10_000)
    return () => clearInterval(interval)
  }, [recording?.status, meeting.id])

  const handleSeedClose = () => {
    setShowSeedDialog(false)
    setLoadingRecording(true)
    loadRecording()
  }

  const isComplete = recording?.status === 'complete'
  const isProcessing = recording && !TERMINAL_STATUSES.has(recording.status)

  const tabs: { key: IntelTab; label: string; icon: typeof Play; disabled: boolean }[] = [
    { key: 'recording', label: 'Recording', icon: Play, disabled: false },
    { key: 'insights', label: 'Insights', icon: BarChart3, disabled: !isComplete },
    { key: 'performance', label: 'Performance', icon: Award, disabled: !isComplete },
    { key: 'signals', label: 'Signals', icon: BarChart3, disabled: !recording?.signal_id },
  ]

  if (loadingRecording) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-6 h-6 animate-spin text-text-muted" />
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full bg-white">
      {showSeedDialog && (
        <SeedDialog projectId={projectId} meetingId={meeting.id} onClose={handleSeedClose} />
      )}

      {/* Tab bar */}
      <div className="flex items-center gap-1 px-5 py-2 border-b border-border shrink-0">
        {tabs.map(tab => {
          const Icon = tab.icon
          return (
            <button
              key={tab.key}
              onClick={() => !tab.disabled && setActiveTab(tab.key)}
              disabled={tab.disabled}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                activeTab === tab.key
                  ? 'bg-brand-primary-light text-brand-primary'
                  : 'text-text-muted hover:text-text-body hover:bg-surface-muted'
              } disabled:opacity-40 disabled:cursor-not-allowed`}
            >
              <Icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {/* Unified pre-recording empty state */}
        {!recording && !isProcessing && activeTab !== 'recording' && (
          <div className="flex flex-col items-center justify-center h-full text-text-muted gap-4 p-8">
            <Mic className="w-12 h-12 text-[#D0D0D0]" />
            <p className="text-sm font-medium">Record this meeting to unlock post-call intelligence</p>
            <p className="text-xs text-center max-w-sm">
              Deploy a recording bot or seed a recording to get post-call insights, performance coaching, and signal extraction.
            </p>
            <div className="flex items-center gap-3">
              {meeting.google_meet_link && (
                <button
                  onClick={onDeployBot}
                  className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-accent rounded-lg hover:bg-accent-hover transition-colors"
                >
                  <Video className="w-4 h-4" />
                  Deploy Bot
                </button>
              )}
              <button
                onClick={() => setShowSeedDialog(true)}
                className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-brand-primary bg-brand-primary-light rounded-lg hover:bg-brand-primary/10 transition-colors"
              >
                <Plus className="w-4 h-4" />
                Seed Recording
              </button>
            </div>
          </div>
        )}

        {/* Recording in progress */}
        {isProcessing && activeTab !== 'recording' && (
          <div className="flex flex-col items-center justify-center h-full text-text-muted gap-3 p-8">
            <Loader2 className="w-8 h-8 animate-spin text-brand-primary" />
            <p className="text-sm font-medium">Processing recording...</p>
            {recording && <StatusBadge status={recording.status} />}
            <p className="text-xs text-center max-w-xs">
              The recording is being transcribed and analyzed. This tab will update automatically.
            </p>
          </div>
        )}

        {/* Recording tab */}
        {activeTab === 'recording' && isComplete && (
          <RecordingPlayerView details={details} />
        )}
        {activeTab === 'recording' && !isComplete && (
          <div className="flex flex-col items-center justify-center h-full text-text-muted gap-4 p-8">
            <Mic className="w-12 h-12 text-[#D0D0D0]" />
            <p className="text-sm font-medium">Record this meeting to unlock post-call intelligence</p>
            <p className="text-xs text-center max-w-sm">
              Deploy a recording bot or seed a recording to get insights, performance coaching, and signal extraction.
            </p>
            <div className="flex items-center gap-3">
              {meeting.google_meet_link && (
                <button
                  onClick={onDeployBot}
                  className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-accent rounded-lg hover:bg-accent-hover transition-colors"
                >
                  <Video className="w-4 h-4" />
                  Deploy Bot
                </button>
              )}
              <button
                onClick={() => setShowSeedDialog(true)}
                className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-brand-primary bg-brand-primary-light rounded-lg hover:bg-brand-primary/10 transition-colors"
              >
                <Plus className="w-4 h-4" />
                Seed Recording
              </button>
            </div>
          </div>
        )}

        {/* Insights tab */}
        {activeTab === 'insights' && isComplete && recording && (
          <InsightsView recordingId={recording.id} />
        )}

        {/* Performance tab */}
        {activeTab === 'performance' && isComplete && (
          <PerformanceView details={details} />
        )}

        {/* Signals tab */}
        {activeTab === 'signals' && recording?.signal_id && (
          <div className="p-6">
            <div className="p-4 bg-[#F0F7FA] rounded-lg border border-[#D4E8EF]">
              <p className="text-sm text-[#044159]">
                This meeting generated signal <code className="text-xs bg-white px-1.5 py-0.5 rounded border border-[#D4E8EF]">{recording.signal_id}</code> — entities extracted through the signal pipeline are visible in the workspace.
              </p>
            </div>
          </div>
        )}
        {activeTab === 'signals' && !recording?.signal_id && (
          <div className="flex flex-col items-center justify-center h-full text-text-muted gap-2 p-8">
            <svg className="w-10 h-10 text-[#D0D0D0]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
            </svg>
            <p className="text-[13px] text-text-muted">
              Signals extracted from this meeting will appear here
            </p>
            <p className="text-[11px] text-[#B0B0B0] mt-1">
              Record a meeting to auto-extract features, constraints, and personas
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
