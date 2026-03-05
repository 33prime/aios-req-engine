'use client'

import { useState, useEffect } from 'react'
import {
  Clock,
  AlertTriangle,
  RefreshCw,
  Loader2,
  BarChart3,
} from 'lucide-react'
import { format } from 'date-fns'
import { getCallDetails, analyzeRecording } from '@/lib/api'
import type { CallDetails } from '@/types/call-intelligence'
import { formatDuration } from './constants'
import { StatusBadge } from './StatusBadge'
import { ScoreGauge } from './ScoreGauge'
import { EngagementHeatmap } from './EngagementHeatmap'
import { SyncedTranscript } from './SyncedTranscript'
import {
  AhaMomentHero,
  FeatureReactionsSection,
  MarketSignalsSection,
  ContentNuggetsSection,
  CompetitiveMentionsSection,
} from './InsightSections'

export function InsightsView({
  recordingId,
  onBack,
}: {
  recordingId: string
  onBack?: () => void
}) {
  const [details, setDetails] = useState<CallDetails | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reanalyzing, setReanalyzing] = useState(false)
  const [activeTimestamp, setActiveTimestamp] = useState<number | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    getCallDetails(recordingId)
      .then((d) => { if (!cancelled) setDetails(d) })
      .catch((e) => { if (!cancelled) setError(e.message || 'Failed to load') })
      .finally(() => { if (!cancelled) setLoading(false) })

    return () => { cancelled = true }
  }, [recordingId])

  const handleReanalyze = async () => {
    setReanalyzing(true)
    try {
      await analyzeRecording(recordingId)
    } catch {
      // fire-and-forget
    } finally {
      setReanalyzing(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-text-muted" />
      </div>
    )
  }

  if (error || !details) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-text-muted gap-2">
        <AlertTriangle className="w-8 h-8 text-red-400" />
        <p className="text-sm">{error || 'Recording not found'}</p>
        {onBack && <button onClick={onBack} className="text-xs text-brand-primary hover:underline">Back to recordings</button>}
      </div>
    )
  }

  const { recording, analysis, transcript, feature_insights, call_signals, content_nuggets, competitive_mentions } = details

  return (
    <div className="overflow-y-auto h-full p-6 space-y-6">
      {onBack && <button onClick={onBack} className="text-sm text-brand-primary hover:underline">&larr; Back to recordings</button>}

      {/* Header */}
      <div className="flex items-start justify-between gap-6">
        <div className="flex-1 min-w-0">
          <h4 className="text-lg font-semibold text-text-body">
            {recording.title || (recording.meeting_id ? 'Meeting Recording' : 'Call Recording')}
          </h4>
          <div className="flex items-center gap-4 mt-1 text-sm text-text-muted">
            <span>{format(new Date(recording.created_at), 'MMM d, yyyy h:mm a')}</span>
            {recording.duration_seconds && (
              <span className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5" />
                {formatDuration(recording.duration_seconds)}
              </span>
            )}
            <StatusBadge status={recording.status} />
          </div>
        </div>

        <div className="flex items-center gap-3">
          {analysis?.engagement_score != null && (
            <ScoreGauge score={analysis.engagement_score} label="Engagement" />
          )}
          <button
            onClick={handleReanalyze}
            disabled={reanalyzing}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-text-muted hover:text-text-body bg-surface-muted hover:bg-gray-100 rounded-md transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${reanalyzing ? 'animate-spin' : ''}`} />
            Re-analyze
          </button>
        </div>
      </div>

      {/* Executive Summary */}
      {analysis?.executive_summary && (
        <div className="p-4 bg-surface-muted rounded-lg border border-border">
          <h5 className="text-xs font-semibold text-text-muted uppercase tracking-wide mb-2">Executive Summary</h5>
          <p className="text-sm text-text-body leading-relaxed">{analysis.executive_summary}</p>
        </div>
      )}

      {/* Engagement Heatmap */}
      {analysis?.engagement_timeline && (
        <EngagementHeatmap
          timeline={analysis.engagement_timeline}
          durationSeconds={recording.duration_seconds}
          onSeek={setActiveTimestamp}
        />
      )}

      {/* Aha Moment Hero Cards */}
      <AhaMomentHero insights={feature_insights} />

      {/* Signal Pipeline Recap */}
      {recording.signal_id && (
        <div className="p-3 bg-blue-50 rounded-lg border border-blue-200 flex items-center gap-3">
          <BarChart3 className="w-4 h-4 text-blue-600 shrink-0" />
          <span className="text-xs text-blue-800">
            This call generated a signal ({feature_insights.length} feature reactions, {call_signals.length} market signals)
          </span>
        </div>
      )}

      {/* Insight sections */}
      <FeatureReactionsSection insights={feature_insights} />
      <MarketSignalsSection signals={call_signals} />
      <ContentNuggetsSection nuggets={content_nuggets} />
      <CompetitiveMentionsSection mentions={competitive_mentions} />

      {/* Synced Transcript */}
      {transcript && (
        <SyncedTranscript
          segments={transcript.segments}
          timeline={analysis?.engagement_timeline}
          activeTimestamp={activeTimestamp}
          onSegmentClick={setActiveTimestamp}
        />
      )}

      {/* Empty analysis state */}
      {!analysis && feature_insights.length === 0 && call_signals.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 text-text-muted gap-2">
          <p className="text-sm">No analysis available yet.</p>
          <button
            onClick={handleReanalyze}
            disabled={reanalyzing}
            className="text-sm text-brand-primary hover:underline"
          >
            {reanalyzing ? 'Queuing...' : 'Run analysis now'}
          </button>
        </div>
      )}
    </div>
  )
}
