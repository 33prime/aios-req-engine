/**
 * CallsPanel - Call Intelligence panel for the Bottom Dock
 *
 * Two tabs:
 * 1. Recordings — list of call recordings with status badges
 * 2. Insights — detail view for a selected recording (analysis, feature reactions, signals, etc.)
 */

'use client'

import { useState, useEffect } from 'react'
import {
  Phone,
  Clock,
  ChevronDown,
  ChevronUp,
  Star,
  ThumbsUp,
  HelpCircle,
  XCircle,
  MinusCircle,
  AlertTriangle,
  Target,
  DollarSign,
  Calendar,
  CheckSquare,
  Zap,
  RefreshCw,
  Loader2,
} from 'lucide-react'
import { formatDistanceToNow, format } from 'date-fns'
import { useCallRecordings } from '@/lib/hooks/use-api'
import { getCallDetails, analyzeRecording } from '@/lib/api'
import type {
  CallRecording,
  CallDetails,
  CallRecordingStatus,
  ReactionType,
  CallSignalType,
  NuggetType,
  SentimentType,
  FeatureInsight,
  CallSignal,
  ContentNugget,
  CompetitiveMention,
  TranscriptSegment,
} from '@/types/call-intelligence'

// ============================================================================
// Status & Badge Helpers
// ============================================================================

const STATUS_STYLES: Record<CallRecordingStatus, string> = {
  complete: 'bg-brand-primary-light text-brand-primary',
  analyzing: 'bg-amber-100 text-amber-700 animate-pulse',
  transcribing: 'bg-amber-100 text-amber-700 animate-pulse',
  bot_scheduled: 'bg-blue-100 text-blue-700',
  recording: 'bg-blue-100 text-blue-700 animate-pulse',
  pending: 'bg-blue-100 text-blue-700',
  failed: 'bg-red-100 text-red-700',
  skipped: 'bg-gray-100 text-gray-500',
}

const STATUS_LABELS: Record<CallRecordingStatus, string> = {
  complete: 'Complete',
  analyzing: 'Analyzing…',
  transcribing: 'Transcribing…',
  bot_scheduled: 'Scheduled',
  recording: 'Recording…',
  pending: 'Pending',
  failed: 'Failed',
  skipped: 'Skipped',
}

function StatusBadge({ status }: { status: CallRecordingStatus }) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${STATUS_STYLES[status]}`}>
      {STATUS_LABELS[status]}
    </span>
  )
}

const REACTION_CONFIG: Record<ReactionType, { icon: typeof Star; color: string; label: string }> = {
  excited: { icon: Star, color: 'text-green-600 bg-green-50', label: 'Excited' },
  interested: { icon: ThumbsUp, color: 'text-blue-600 bg-blue-50', label: 'Interested' },
  neutral: { icon: MinusCircle, color: 'text-gray-500 bg-gray-50', label: 'Neutral' },
  confused: { icon: HelpCircle, color: 'text-amber-600 bg-amber-50', label: 'Confused' },
  resistant: { icon: XCircle, color: 'text-red-600 bg-red-50', label: 'Resistant' },
}

const SIGNAL_TYPE_STYLES: Record<CallSignalType, string> = {
  pain_point: 'bg-red-100 text-red-700',
  goal: 'bg-green-100 text-green-700',
  budget_indicator: 'bg-amber-100 text-amber-700',
  timeline: 'bg-blue-100 text-blue-700',
  decision_criteria: 'bg-purple-100 text-purple-700',
  risk_factor: 'bg-orange-100 text-orange-700',
}

const SIGNAL_TYPE_ICONS: Record<CallSignalType, typeof AlertTriangle> = {
  pain_point: AlertTriangle,
  goal: Target,
  budget_indicator: DollarSign,
  timeline: Calendar,
  decision_criteria: CheckSquare,
  risk_factor: Zap,
}

const SIGNAL_TYPE_LABELS: Record<CallSignalType, string> = {
  pain_point: 'Pain Point',
  goal: 'Goal',
  budget_indicator: 'Budget',
  timeline: 'Timeline',
  decision_criteria: 'Decision Criteria',
  risk_factor: 'Risk Factor',
}

const NUGGET_TYPE_STYLES: Record<NuggetType, string> = {
  testimonial: 'bg-green-100 text-green-700',
  soundbite: 'bg-blue-100 text-blue-700',
  statistic: 'bg-purple-100 text-purple-700',
  use_case: 'bg-amber-100 text-amber-700',
  objection: 'bg-red-100 text-red-700',
  vision_statement: 'bg-indigo-100 text-indigo-700',
}

const NUGGET_TYPE_LABELS: Record<NuggetType, string> = {
  testimonial: 'Testimonial',
  soundbite: 'Soundbite',
  statistic: 'Statistic',
  use_case: 'Use Case',
  objection: 'Objection',
  vision_statement: 'Vision',
}

const SENTIMENT_STYLES: Record<SentimentType, string> = {
  positive: 'bg-green-100 text-green-700',
  neutral: 'bg-gray-100 text-gray-600',
  negative: 'bg-red-100 text-red-700',
}

function formatDuration(seconds: number | null | undefined): string {
  if (!seconds) return '—'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

// ============================================================================
// Engagement Gauge
// ============================================================================

function EngagementGauge({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const color = pct < 40 ? 'text-red-500' : pct < 70 ? 'text-amber-500' : 'text-green-500'
  const trackColor = pct < 40 ? 'stroke-red-100' : pct < 70 ? 'stroke-amber-100' : 'stroke-green-100'
  const fillColor = pct < 40 ? 'stroke-red-500' : pct < 70 ? 'stroke-amber-500' : 'stroke-green-500'
  const circumference = 2 * Math.PI * 40
  const dashOffset = circumference - (pct / 100) * circumference

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width="96" height="96" viewBox="0 0 96 96">
        <circle cx="48" cy="48" r="40" fill="none" strokeWidth="8" className={trackColor} />
        <circle
          cx="48" cy="48" r="40" fill="none" strokeWidth="8"
          className={fillColor}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          transform="rotate(-90 48 48)"
        />
        <text x="48" y="48" textAnchor="middle" dominantBaseline="central"
          className={`text-xl font-bold ${color}`} fill="currentColor">
          {pct}%
        </text>
      </svg>
      <span className="text-xs text-text-muted font-medium">Engagement</span>
    </div>
  )
}

// ============================================================================
// Collapsible Section
// ============================================================================

function CollapsibleSection({
  title,
  count,
  defaultOpen = true,
  children,
}: {
  title: string
  count: number
  defaultOpen?: boolean
  children: React.ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)

  if (count === 0) return null

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 bg-surface-muted hover:bg-gray-50 transition-colors"
      >
        <span className="text-sm font-semibold text-text-body">
          {title} <span className="text-text-muted font-normal">({count})</span>
        </span>
        {open ? <ChevronUp className="w-4 h-4 text-text-muted" /> : <ChevronDown className="w-4 h-4 text-text-muted" />}
      </button>
      {open && <div className="p-4 space-y-3">{children}</div>}
    </div>
  )
}

// ============================================================================
// Insight Sub-sections
// ============================================================================

function FeatureReactionsSection({ insights }: { insights: FeatureInsight[] }) {
  return (
    <CollapsibleSection title="Feature Reactions" count={insights.length}>
      {insights.map((fi, i) => {
        const cfg = REACTION_CONFIG[fi.reaction]
        const Icon = cfg.icon
        return (
          <div key={fi.id || i} className="flex items-start gap-3 p-3 bg-white rounded-lg border border-border">
            <div className={`p-1.5 rounded-md ${cfg.color}`}>
              <Icon className="w-4 h-4" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-text-body">{fi.feature_name}</span>
                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${cfg.color}`}>
                  {cfg.label}
                </span>
                {fi.is_aha_moment && (
                  <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
                )}
              </div>
              {fi.quote && (
                <blockquote className="mt-1.5 text-xs text-text-muted italic border-l-2 border-border pl-2">
                  &ldquo;{fi.quote}&rdquo;
                </blockquote>
              )}
              {fi.context && <p className="mt-1 text-xs text-text-muted">{fi.context}</p>}
            </div>
          </div>
        )
      })}
    </CollapsibleSection>
  )
}

function MarketSignalsSection({ signals }: { signals: CallSignal[] }) {
  return (
    <CollapsibleSection title="Market Signals" count={signals.length}>
      {signals.map((sig, i) => {
        const Icon = SIGNAL_TYPE_ICONS[sig.signal_type]
        return (
          <div key={sig.id || i} className="p-3 bg-white rounded-lg border border-border space-y-2">
            <div className="flex items-center gap-2">
              <Icon className="w-4 h-4 text-text-muted" />
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${SIGNAL_TYPE_STYLES[sig.signal_type]}`}>
                {SIGNAL_TYPE_LABELS[sig.signal_type]}
              </span>
              <span className="text-sm font-medium text-text-body">{sig.title}</span>
            </div>
            {sig.description && <p className="text-xs text-text-muted">{sig.description}</p>}
            {/* Intensity bar */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-text-muted">Intensity</span>
              <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-brand-primary rounded-full transition-all"
                  style={{ width: `${Math.round(sig.intensity * 100)}%` }}
                />
              </div>
              <span className="text-xs text-text-muted">{Math.round(sig.intensity * 100)}%</span>
            </div>
            {sig.quote && (
              <blockquote className="text-xs text-text-muted italic border-l-2 border-border pl-2">
                &ldquo;{sig.quote}&rdquo;
              </blockquote>
            )}
          </div>
        )
      })}
    </CollapsibleSection>
  )
}

function ContentNuggetsSection({ nuggets }: { nuggets: ContentNugget[] }) {
  return (
    <CollapsibleSection title="Content Nuggets" count={nuggets.length}>
      {nuggets.map((n, i) => (
        <div key={n.id || i} className="p-3 bg-white rounded-lg border border-border space-y-2">
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${NUGGET_TYPE_STYLES[n.nugget_type]}`}>
              {NUGGET_TYPE_LABELS[n.nugget_type]}
            </span>
            {n.speaker && <span className="text-xs text-text-muted">— {n.speaker}</span>}
          </div>
          <p className="text-sm text-text-body">{n.content}</p>
          {/* Reuse score bar */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-text-muted">Reuse potential</span>
            <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-brand-primary rounded-full transition-all"
                style={{ width: `${Math.round(n.reuse_score * 100)}%` }}
              />
            </div>
            <span className="text-xs text-text-muted">{Math.round(n.reuse_score * 100)}%</span>
          </div>
        </div>
      ))}
    </CollapsibleSection>
  )
}

function CompetitiveMentionsSection({ mentions }: { mentions: CompetitiveMention[] }) {
  return (
    <CollapsibleSection title="Competitive Mentions" count={mentions.length}>
      {mentions.map((m, i) => (
        <div key={m.id || i} className="p-3 bg-white rounded-lg border border-border space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-text-body">{m.competitor_name}</span>
            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${SENTIMENT_STYLES[m.sentiment]}`}>
              {m.sentiment}
            </span>
          </div>
          {m.context && <p className="text-xs text-text-muted">{m.context}</p>}
          {m.quote && (
            <blockquote className="text-xs text-text-muted italic border-l-2 border-border pl-2">
              &ldquo;{m.quote}&rdquo;
            </blockquote>
          )}
          {m.feature_comparison && (
            <p className="text-xs text-text-muted"><span className="font-medium">Comparison:</span> {m.feature_comparison}</p>
          )}
        </div>
      ))}
    </CollapsibleSection>
  )
}

function TranscriptSection({ segments }: { segments: TranscriptSegment[] }) {
  const [open, setOpen] = useState(false)

  if (segments.length === 0) return null

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 bg-surface-muted hover:bg-gray-50 transition-colors"
      >
        <span className="text-sm font-semibold text-text-body">
          Transcript <span className="text-text-muted font-normal">({segments.length} segments)</span>
        </span>
        {open ? <ChevronUp className="w-4 h-4 text-text-muted" /> : <ChevronDown className="w-4 h-4 text-text-muted" />}
      </button>
      {open && (
        <div className="max-h-80 overflow-y-auto p-4 space-y-2">
          {segments.map((seg, i) => (
            <div key={i} className="flex gap-3 text-sm">
              <span className="shrink-0 text-xs text-text-muted font-mono w-12 pt-0.5 text-right">
                {formatDuration(Math.round(seg.start))}
              </span>
              <div className="flex-1 min-w-0">
                <span className="text-xs font-semibold text-brand-accent">{seg.speaker}</span>
                <p className="text-text-body">{seg.text}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Recordings Tab
// ============================================================================

function RecordingsTab({
  projectId,
  onSelectRecording,
}: {
  projectId: string
  onSelectRecording: (recordingId: string) => void
}) {
  const { data: recordings, isLoading, error } = useCallRecordings(projectId)

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
        <AlertTriangle className="w-8 h-8 text-red-400" />
        <p className="text-sm">Failed to load recordings</p>
      </div>
    )
  }

  if (!recordings || recordings.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-text-muted gap-2">
        <Phone className="w-8 h-8" />
        <p className="text-sm">No call recordings yet.</p>
        <p className="text-xs">Record a meeting to get started.</p>
      </div>
    )
  }

  return (
    <div className="overflow-y-auto h-full">
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
                    {rec.meeting_id ? `Meeting Recording` : `Recording`}
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
  )
}

// ============================================================================
// Insights Tab
// ============================================================================

function InsightsTab({
  recordingId,
  onBack,
}: {
  recordingId: string
  onBack: () => void
}) {
  const [details, setDetails] = useState<CallDetails | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reanalyzing, setReanalyzing] = useState(false)

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
      // Ignore — fire-and-forget
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
        <button onClick={onBack} className="text-xs text-brand-primary hover:underline">
          Back to recordings
        </button>
      </div>
    )
  }

  const { recording, analysis, transcript, feature_insights, call_signals, content_nuggets, competitive_mentions } = details

  return (
    <div className="overflow-y-auto h-full p-6 space-y-6">
      {/* Back button */}
      <button onClick={onBack} className="text-sm text-brand-primary hover:underline">
        &larr; Back to recordings
      </button>

      {/* Header */}
      <div className="flex items-start justify-between gap-6">
        <div className="flex-1 min-w-0">
          <h4 className="text-lg font-semibold text-text-body">
            {recording.meeting_id ? 'Meeting Recording' : 'Call Recording'}
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
            <EngagementGauge score={analysis.engagement_score} />
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

      {/* Insight sections */}
      <FeatureReactionsSection insights={feature_insights} />
      <MarketSignalsSection signals={call_signals} />
      <ContentNuggetsSection nuggets={content_nuggets} />
      <CompetitiveMentionsSection mentions={competitive_mentions} />

      {/* Transcript */}
      {transcript && <TranscriptSection segments={transcript.segments} />}

      {/* Empty analysis state */}
      {!analysis && feature_insights.length === 0 && call_signals.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 text-text-muted gap-2">
          <p className="text-sm">No analysis available yet.</p>
          <button
            onClick={handleReanalyze}
            disabled={reanalyzing}
            className="text-sm text-brand-primary hover:underline"
          >
            {reanalyzing ? 'Queuing…' : 'Run analysis now'}
          </button>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Main Panel
// ============================================================================

type Tab = 'recordings' | 'insights'

export function CallsPanel({ projectId }: { projectId: string }) {
  const [activeTab, setActiveTab] = useState<Tab>('recordings')
  const [selectedRecordingId, setSelectedRecordingId] = useState<string | null>(null)

  const handleSelectRecording = (recordingId: string) => {
    setSelectedRecordingId(recordingId)
    setActiveTab('insights')
  }

  const handleBack = () => {
    setSelectedRecordingId(null)
    setActiveTab('recordings')
  }

  return (
    <div className="flex flex-col h-full">
      {/* Tab bar */}
      <div className="flex items-center gap-1 px-6 py-2 border-b border-border bg-white shrink-0">
        <button
          onClick={() => setActiveTab('recordings')}
          className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
            activeTab === 'recordings'
              ? 'bg-brand-primary-light text-brand-primary'
              : 'text-text-muted hover:text-text-body hover:bg-surface-muted'
          }`}
        >
          Recordings
        </button>
        <button
          onClick={() => selectedRecordingId && setActiveTab('insights')}
          disabled={!selectedRecordingId}
          className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
            activeTab === 'insights'
              ? 'bg-brand-primary-light text-brand-primary'
              : 'text-text-muted hover:text-text-body hover:bg-surface-muted'
          } disabled:opacity-40 disabled:cursor-not-allowed`}
        >
          Insights
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'recordings' && (
          <RecordingsTab projectId={projectId} onSelectRecording={handleSelectRecording} />
        )}
        {activeTab === 'insights' && selectedRecordingId && (
          <InsightsTab recordingId={selectedRecordingId} onBack={handleBack} />
        )}
      </div>
    </div>
  )
}
