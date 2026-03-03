/**
 * CallsPanel - Call Intelligence panel for the Bottom Dock
 *
 * Four tabs:
 * 1. Recordings — list + seed recording + status badges + strategy brief indicators
 * 2. Strategy — pre-call strategy brief view with goals, stakeholder intel, readiness
 * 3. Insights — post-call detail view with synced transcript, engagement heatmap, aha moments
 * 4. Performance — consultant coaching dashboard
 */

'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
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
  Plus,
  FileText,
  Users,
  TrendingUp,
  MessageCircle,
  Award,
  ArrowRight,
  Check,
  X,
  Minus,
  Sparkles,
  BarChart3,
  Shield,
  Mic,
} from 'lucide-react'
import { formatDistanceToNow, format } from 'date-fns'
import { useCallRecordings } from '@/lib/hooks/use-api'
import {
  getCallDetails,
  analyzeRecording,
  seedRecording,
  generateStrategyBrief,
  getBriefForRecording,
} from '@/lib/api'
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
  CallStrategyBrief,
  ConsultantPerformance,
  GoalResult,
  FocusArea,
  StakeholderIntel,
  MissionCriticalQuestion,
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
  analyzing: 'Analyzing...',
  transcribing: 'Transcribing...',
  bot_scheduled: 'Scheduled',
  recording: 'Recording...',
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
  if (!seconds) return '\u2014'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

// ============================================================================
// Score Gauge (reusable)
// ============================================================================

function ScoreGauge({ score, label, size = 'normal' }: { score: number; label: string; size?: 'normal' | 'small' }) {
  const pct = Math.round(score * 100)
  const color = pct < 40 ? 'text-red-500' : pct < 70 ? 'text-amber-500' : 'text-green-500'
  const trackColor = pct < 40 ? 'stroke-red-100' : pct < 70 ? 'stroke-amber-100' : 'stroke-green-100'
  const fillColor = pct < 40 ? 'stroke-red-500' : pct < 70 ? 'stroke-amber-500' : 'stroke-green-500'

  const sz = size === 'small' ? 56 : 96
  const r = size === 'small' ? 22 : 40
  const sw = size === 'small' ? 5 : 8
  const center = sz / 2
  const circumference = 2 * Math.PI * r
  const dashOffset = circumference - (pct / 100) * circumference

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={sz} height={sz} viewBox={`0 0 ${sz} ${sz}`}>
        <circle cx={center} cy={center} r={r} fill="none" strokeWidth={sw} className={trackColor} />
        <circle
          cx={center} cy={center} r={r} fill="none" strokeWidth={sw}
          className={fillColor}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          transform={`rotate(-90 ${center} ${center})`}
        />
        <text x={center} y={center} textAnchor="middle" dominantBaseline="central"
          className={`${size === 'small' ? 'text-sm' : 'text-xl'} font-bold ${color}`} fill="currentColor">
          {pct}%
        </text>
      </svg>
      <span className={`${size === 'small' ? 'text-[10px]' : 'text-xs'} text-text-muted font-medium text-center leading-tight`}>{label}</span>
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
// Seed Recording Dialog
// ============================================================================

function SeedDialog({ projectId, onClose }: { projectId: string; onClose: () => void }) {
  const [audioUrl, setAudioUrl] = useState('')
  const [title, setTitle] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async () => {
    if (!audioUrl.trim()) return
    setSubmitting(true)
    try {
      await seedRecording(projectId, audioUrl.trim(), title.trim() || undefined)
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
            {submitting ? 'Seeding...' : 'Seed Recording'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// Insight Sub-sections
// ============================================================================

function AhaMomentHero({ insights }: { insights: FeatureInsight[] }) {
  const ahas = insights.filter(fi => fi.is_aha_moment)
  if (ahas.length === 0) return null

  return (
    <div className="space-y-3">
      {ahas.map((fi, i) => (
        <div key={fi.id || i} className="p-4 bg-gradient-to-r from-amber-50 to-yellow-50 border border-amber-200 rounded-xl">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="w-4 h-4 text-amber-500" />
            <span className="text-xs font-semibold text-amber-700 uppercase tracking-wide">Aha Moment</span>
            <span className="px-2 py-0.5 text-xs font-medium bg-white rounded-full text-text-body border border-amber-200">
              {fi.feature_name}
            </span>
          </div>
          {fi.quote && (
            <blockquote className="text-sm text-text-body italic leading-relaxed">
              &ldquo;{fi.quote}&rdquo;
            </blockquote>
          )}
          {fi.context && <p className="mt-2 text-xs text-text-muted">{fi.context}</p>}
        </div>
      ))}
    </div>
  )
}

function FeatureReactionsSection({ insights }: { insights: FeatureInsight[] }) {
  const nonAha = insights.filter(fi => !fi.is_aha_moment)
  return (
    <CollapsibleSection title="Feature Reactions" count={nonAha.length}>
      {nonAha.map((fi, i) => {
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
            {n.speaker && <span className="text-xs text-text-muted">\u2014 {n.speaker}</span>}
          </div>
          <p className="text-sm text-text-body">{n.content}</p>
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

// ============================================================================
// Engagement Heatmap
// ============================================================================

function EngagementHeatmap({
  timeline,
  durationSeconds,
  onSeek,
}: {
  timeline: Array<Record<string, unknown>>
  durationSeconds?: number | null
  onSeek?: (seconds: number) => void
}) {
  if (!timeline || timeline.length === 0) return null
  const duration = durationSeconds || (timeline.length > 0 ? Number(timeline[timeline.length - 1]?.timestamp_seconds || 300) + 60 : 300)

  return (
    <div className="space-y-1">
      <span className="text-xs font-medium text-text-muted">Engagement Timeline</span>
      <div className="h-6 bg-gray-100 rounded-full overflow-hidden flex cursor-pointer" title="Click to navigate">
        {timeline.map((entry, i) => {
          const ts = Number(entry.timestamp_seconds || 0)
          const nextTs = i < timeline.length - 1 ? Number(timeline[i + 1]?.timestamp_seconds || duration) : duration
          const widthPct = ((nextTs - ts) / duration) * 100
          const engagement = Number(entry.engagement_level || 0.5)
          const bg = engagement < 0.4 ? 'bg-red-400' : engagement < 0.7 ? 'bg-amber-400' : 'bg-green-400'

          return (
            <div
              key={i}
              className={`${bg} h-full relative group transition-opacity hover:opacity-80`}
              style={{ width: `${widthPct}%` }}
              onClick={() => onSeek?.(ts)}
              title={`${formatDuration(ts)} - ${String(entry.topic || 'Segment')} (${Math.round(engagement * 100)}%)`}
            />
          )
        })}
      </div>
    </div>
  )
}

// ============================================================================
// Synced Transcript Player
// ============================================================================

function SyncedTranscript({
  segments,
  timeline,
  activeTimestamp,
  onSegmentClick,
}: {
  segments: TranscriptSegment[]
  timeline?: Array<Record<string, unknown>>
  activeTimestamp?: number | null
  onSegmentClick?: (seconds: number) => void
}) {
  const scrollRef = useRef<HTMLDivElement>(null)

  const getSegmentEngagement = useCallback((seg: TranscriptSegment) => {
    if (!timeline || timeline.length === 0) return 0.5
    const ts = seg.start
    for (let i = timeline.length - 1; i >= 0; i--) {
      if (Number(timeline[i]?.timestamp_seconds || 0) <= ts) {
        return Number(timeline[i]?.engagement_level || 0.5)
      }
    }
    return 0.5
  }, [timeline])

  if (segments.length === 0) return null

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <div className="px-4 py-3 bg-surface-muted border-b border-border">
        <span className="text-sm font-semibold text-text-body">
          Transcript <span className="text-text-muted font-normal">({segments.length} segments)</span>
        </span>
      </div>
      <div ref={scrollRef} className="max-h-80 overflow-y-auto p-4 space-y-2">
        {segments.map((seg, i) => {
          const engagement = getSegmentEngagement(seg)
          const engColor = engagement < 0.4 ? 'border-l-red-400' : engagement < 0.7 ? 'border-l-amber-400' : 'border-l-green-400'
          const isActive = activeTimestamp != null && seg.start <= activeTimestamp && seg.end >= activeTimestamp

          return (
            <div
              key={i}
              className={`flex gap-3 text-sm border-l-3 pl-3 cursor-pointer hover:bg-surface-muted rounded-r-lg transition-colors ${engColor} ${isActive ? 'bg-brand-primary-light' : ''}`}
              onClick={() => onSegmentClick?.(seg.start)}
            >
              <span className="shrink-0 text-xs text-text-muted font-mono w-12 pt-0.5 text-right">
                {formatDuration(Math.round(seg.start))}
              </span>
              <div className="flex-1 min-w-0">
                <span className="text-xs font-semibold text-brand-accent">{seg.speaker}</span>
                <p className="text-text-body">{seg.text}</p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ============================================================================
// Tab 1: Recordings
// ============================================================================

function RecordingsTab({
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
        <AlertTriangle className="w-8 h-8 text-red-400" />
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

// ============================================================================
// Tab 2: Strategy Brief
// ============================================================================

function GoalStatusBadge({ achieved }: { achieved?: string }) {
  if (!achieved) return <span className="px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-500 rounded-full">Planned</span>
  const styles: Record<string, string> = {
    yes: 'bg-green-100 text-green-700',
    partial: 'bg-amber-100 text-amber-700',
    no: 'bg-red-100 text-red-700',
    unknown: 'bg-gray-100 text-gray-500',
  }
  const icons: Record<string, typeof Check> = { yes: Check, partial: Minus, no: X, unknown: HelpCircle }
  const Icon = icons[achieved] || HelpCircle
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full ${styles[achieved] || styles.unknown}`}>
      <Icon className="w-3 h-3" />
      {achieved === 'yes' ? 'Achieved' : achieved === 'partial' ? 'Partial' : achieved === 'no' ? 'Missed' : 'Unknown'}
    </span>
  )
}

function StrategyTab({
  recordingId,
  brief: initialBrief,
  projectId,
  onBack,
}: {
  recordingId?: string | null
  brief?: CallStrategyBrief | null
  projectId: string
  onBack: () => void
}) {
  const [brief, setBrief] = useState<CallStrategyBrief | null>(initialBrief || null)
  const [loading, setLoading] = useState(!initialBrief && !!recordingId)
  const [generating, setGenerating] = useState(false)

  useEffect(() => {
    if (initialBrief) { setBrief(initialBrief); return }
    if (!recordingId) return
    let cancelled = false
    setLoading(true)
    getBriefForRecording(recordingId)
      .then(b => { if (!cancelled) setBrief(b) })
      .catch(() => { if (!cancelled) setBrief(null) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [recordingId, initialBrief])

  const handleGenerate = async () => {
    setGenerating(true)
    try {
      await generateStrategyBrief(projectId)
    } catch (e) {
      console.error('Failed to generate brief:', e)
    } finally {
      setGenerating(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-text-muted" />
      </div>
    )
  }

  if (!brief) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-text-muted gap-3 p-8">
        <FileText className="w-10 h-10" />
        <p className="text-sm font-medium">No strategy brief yet</p>
        <p className="text-xs text-center max-w-xs">Generate a pre-call strategy brief to prepare with stakeholder intel, deal readiness, and mission-critical questions.</p>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-brand-primary rounded-lg hover:bg-brand-primary-hover disabled:opacity-50"
        >
          {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          Generate Strategy Brief
        </button>
        <button onClick={onBack} className="text-xs text-brand-primary hover:underline mt-2">Back to recordings</button>
      </div>
    )
  }

  const { call_goals, goal_results, mission_critical_questions, focus_areas, deal_readiness_snapshot, stakeholder_intel, ambiguity_snapshot, project_awareness_snapshot, readiness_delta } = brief

  return (
    <div className="overflow-y-auto h-full p-6 space-y-6">
      <button onClick={onBack} className="text-sm text-brand-primary hover:underline">&larr; Back to recordings</button>

      {/* Readiness delta hero (if post-call) */}
      {readiness_delta && (
        <div className="p-4 bg-gradient-to-r from-brand-primary-light to-green-50 rounded-xl border border-brand-primary/20">
          <div className="flex items-center gap-3">
            <TrendingUp className="w-5 h-5 text-brand-primary" />
            <span className="text-sm font-semibold text-text-body">
              Readiness moved from {readiness_delta.before_score} &rarr; {readiness_delta.after_score}
              {' '}
              <span className={readiness_delta.after_score > readiness_delta.before_score ? 'text-green-600' : 'text-red-600'}>
                ({readiness_delta.after_score > readiness_delta.before_score ? '+' : ''}{Math.round(readiness_delta.after_score - readiness_delta.before_score)})
              </span>
            </span>
          </div>
        </div>
      )}

      <div className="grid grid-cols-5 gap-6">
        {/* Left column (3/5) */}
        <div className="col-span-3 space-y-6">
          {/* Call Goals */}
          {call_goals && call_goals.length > 0 && (
            <div className="space-y-3">
              <h5 className="text-xs font-semibold text-text-muted uppercase tracking-wide flex items-center gap-1.5">
                <Target className="w-3.5 h-3.5" /> Call Goals
              </h5>
              {call_goals.map((goal, i) => {
                const result = goal_results?.find((r: GoalResult) => r.goal === goal.goal)
                return (
                  <div key={i} className="p-3 bg-white rounded-lg border border-border space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-start gap-2">
                        <span className="shrink-0 w-6 h-6 rounded-full bg-brand-primary-light text-brand-primary text-xs font-bold flex items-center justify-center">
                          {i + 1}
                        </span>
                        <span className="text-sm font-medium text-text-body">{goal.goal}</span>
                      </div>
                      <GoalStatusBadge achieved={result?.achieved} />
                    </div>
                    <p className="text-xs text-text-muted pl-8">Success: {goal.success_criteria}</p>
                    {result?.evidence && (
                      <p className="text-xs text-text-muted pl-8 italic">{result.evidence}</p>
                    )}
                  </div>
                )
              })}
            </div>
          )}

          {/* Mission-Critical Questions */}
          {mission_critical_questions && mission_critical_questions.length > 0 && (
            <div className="space-y-3">
              <h5 className="text-xs font-semibold text-text-muted uppercase tracking-wide flex items-center gap-1.5">
                <MessageCircle className="w-3.5 h-3.5" /> Mission-Critical Questions
              </h5>
              {mission_critical_questions.map((q: MissionCriticalQuestion, i: number) => (
                <div key={i} className="p-3 bg-white rounded-lg border border-border">
                  <p className="text-sm font-medium text-text-body">{q.question}</p>
                  <div className="flex items-center gap-2 mt-2">
                    {q.target_stakeholder && (
                      <span className="px-2 py-0.5 text-xs font-medium bg-blue-50 text-blue-700 rounded-full">
                        {q.target_stakeholder}
                      </span>
                    )}
                  </div>
                  {q.why_important && <p className="mt-1.5 text-xs text-text-muted">{q.why_important}</p>}
                </div>
              ))}
            </div>
          )}

          {/* Focus Areas */}
          {focus_areas && focus_areas.length > 0 && (
            <div className="space-y-3">
              <h5 className="text-xs font-semibold text-text-muted uppercase tracking-wide flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5" /> Focus Areas
              </h5>
              {focus_areas.map((fa: FocusArea, i: number) => (
                <div key={i} className="flex items-start gap-3 p-3 bg-white rounded-lg border border-border">
                  <span className={`shrink-0 px-2 py-0.5 text-xs font-semibold rounded-full ${
                    fa.priority === 'high' ? 'bg-red-100 text-red-700' :
                    fa.priority === 'medium' ? 'bg-amber-100 text-amber-700' :
                    'bg-gray-100 text-gray-600'
                  }`}>
                    {fa.priority}
                  </span>
                  <div>
                    <p className="text-sm font-medium text-text-body">{fa.area}</p>
                    <p className="text-xs text-text-muted mt-0.5">{fa.context}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right column (2/5) */}
        <div className="col-span-2 space-y-6">
          {/* Deal Readiness */}
          {deal_readiness_snapshot && (
            <div className="p-4 bg-white rounded-lg border border-border space-y-3">
              <h5 className="text-xs font-semibold text-text-muted uppercase tracking-wide flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5" /> Deal Readiness
              </h5>
              <div className="flex justify-center">
                <ScoreGauge score={(deal_readiness_snapshot.score || 0) / 100} label="Readiness" />
              </div>
              {deal_readiness_snapshot.components?.map((c, i) => (
                <div key={i} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-text-muted">{c.name}</span>
                    <span className="text-text-body font-medium">{Math.round(c.score)}</span>
                  </div>
                  <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full bg-brand-primary rounded-full" style={{ width: `${c.score}%` }} />
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Stakeholder Intel */}
          {stakeholder_intel && stakeholder_intel.length > 0 && (
            <div className="p-4 bg-white rounded-lg border border-border space-y-3">
              <h5 className="text-xs font-semibold text-text-muted uppercase tracking-wide flex items-center gap-1.5">
                <Users className="w-3.5 h-3.5" /> Stakeholder Intel
              </h5>
              {stakeholder_intel.map((s: StakeholderIntel, i: number) => (
                <div key={i} className="p-2 bg-surface-muted rounded-md space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-text-body">{s.name}</span>
                    <span className={`px-1.5 py-0.5 text-[10px] font-semibold rounded-full ${
                      s.influence === 'high' ? 'bg-red-100 text-red-700' :
                      s.influence === 'medium' ? 'bg-amber-100 text-amber-700' :
                      'bg-gray-100 text-gray-600'
                    }`}>
                      {s.influence}
                    </span>
                  </div>
                  {s.role && <p className="text-xs text-text-muted">{s.role}</p>}
                  {s.key_concerns.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {s.key_concerns.map((c, j) => (
                        <span key={j} className="px-1.5 py-0.5 text-[10px] bg-amber-50 text-amber-700 rounded">
                          {c.length > 40 ? c.slice(0, 40) + '...' : c}
                        </span>
                      ))}
                    </div>
                  )}
                  <p className="text-xs text-text-muted italic">{s.approach_notes}</p>
                </div>
              ))}
            </div>
          )}

          {/* Ambiguity Score */}
          {ambiguity_snapshot && typeof ambiguity_snapshot.score === 'number' && (
            <div className="p-4 bg-white rounded-lg border border-border space-y-3">
              <h5 className="text-xs font-semibold text-text-muted uppercase tracking-wide">Ambiguity</h5>
              <div className="flex justify-center">
                <ScoreGauge score={ambiguity_snapshot.score} label="Ambiguity" size="small" />
              </div>
              {ambiguity_snapshot.factors && Object.entries(ambiguity_snapshot.factors).length > 0 && (
                <div className="space-y-1">
                  {Object.entries(ambiguity_snapshot.factors).slice(0, 4).map(([cat, factors]) => (
                    <div key={cat} className="text-xs text-text-muted">
                      <span className="font-medium">{cat}</span>: confidence gap {Math.round(((factors as Record<string, number>).confidence_gap || 0) * 100)}%
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Project Snapshot */}
          {project_awareness_snapshot && (
            <div className="p-4 bg-white rounded-lg border border-border space-y-2">
              <h5 className="text-xs font-semibold text-text-muted uppercase tracking-wide">Project Snapshot</h5>
              <span className="inline-flex px-2 py-0.5 text-xs font-semibold bg-brand-primary-light text-brand-primary rounded-full">
                {project_awareness_snapshot.phase || 'unknown'}
              </span>
              {project_awareness_snapshot.flow_summary && (
                <p className="text-xs text-text-muted">{project_awareness_snapshot.flow_summary}</p>
              )}
              {project_awareness_snapshot.whats_next && project_awareness_snapshot.whats_next.length > 0 && (
                <div className="space-y-1">
                  <span className="text-[10px] font-semibold text-text-muted uppercase">What&apos;s Next</span>
                  {project_awareness_snapshot.whats_next.slice(0, 3).map((item, i) => (
                    <div key={i} className="flex items-center gap-1.5 text-xs text-text-body">
                      <ArrowRight className="w-3 h-3 text-brand-primary shrink-0" />
                      {item}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// Tab 3: Insights (upgraded)
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
        <button onClick={onBack} className="text-xs text-brand-primary hover:underline">Back to recordings</button>
      </div>
    )
  }

  const { recording, analysis, transcript, feature_insights, call_signals, content_nuggets, competitive_mentions } = details

  return (
    <div className="overflow-y-auto h-full p-6 space-y-6">
      <button onClick={onBack} className="text-sm text-brand-primary hover:underline">&larr; Back to recordings</button>

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

// ============================================================================
// Tab 4: Consultant Performance
// ============================================================================

function TalkRatioBar({ data }: { data: ConsultantPerformance['consultant_talk_ratio'] }) {
  if (!data || typeof data.consultant_share !== 'number') return null
  const consultantPct = Math.round(data.consultant_share * 100)
  const clientPct = 100 - consultantPct

  return (
    <div className="space-y-2">
      <h5 className="text-xs font-semibold text-text-muted uppercase tracking-wide">Talk Ratio</h5>
      <div className="h-6 rounded-full overflow-hidden flex">
        <div className="bg-brand-primary flex items-center justify-center" style={{ width: `${consultantPct}%` }}>
          <span className="text-[10px] font-bold text-white">{consultantPct}%</span>
        </div>
        <div className="bg-blue-200 flex items-center justify-center" style={{ width: `${clientPct}%` }}>
          <span className="text-[10px] font-bold text-blue-800">{clientPct}%</span>
        </div>
      </div>
      <div className="flex justify-between text-xs text-text-muted">
        <span>Consultant</span>
        <span>Client</span>
      </div>
      {/* Ideal range indicator */}
      <div className="relative h-1 bg-gray-100 rounded-full">
        <div className="absolute h-full bg-green-300 rounded-full" style={{ left: '30%', width: '10%' }} />
        <div className="absolute w-0.5 h-3 bg-brand-primary rounded-full -top-1" style={{ left: `${consultantPct}%` }} />
      </div>
      <p className="text-xs text-text-muted">Ideal: {data.ideal_range || '30-40%'} consultant share</p>
      {data.assessment && <p className="text-xs text-text-body italic">{data.assessment}</p>}
    </div>
  )
}

function PerformanceTab({
  details,
  onBack,
}: {
  details: CallDetails | null
  onBack: () => void
}) {
  const perf = details?.consultant_performance

  if (!perf) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-text-muted gap-2">
        <Award className="w-8 h-8" />
        <p className="text-sm">No consultant performance data available.</p>
        <p className="text-xs">Re-analyze with the consultant dimension pack to see coaching insights.</p>
        <button onClick={onBack} className="text-xs text-brand-primary hover:underline mt-2">Back to recordings</button>
      </div>
    )
  }

  const scores = [
    { key: 'question_quality', label: 'Questions', score: perf.question_quality?.score },
    { key: 'active_listening', label: 'Listening', score: perf.active_listening?.score },
    { key: 'discovery_depth', label: 'Depth', score: perf.discovery_depth?.score },
    { key: 'objection_handling', label: 'Objections', score: perf.objection_handling?.score },
    { key: 'next_steps_clarity', label: 'Next Steps', score: perf.next_steps_clarity?.score },
  ].filter(s => typeof s.score === 'number')

  return (
    <div className="overflow-y-auto h-full p-6 space-y-6">
      <button onClick={onBack} className="text-sm text-brand-primary hover:underline">&larr; Back to recordings</button>

      {/* Score gauges row */}
      {scores.length > 0 && (
        <div className="flex items-start justify-center gap-6 flex-wrap">
          {scores.map(s => (
            <ScoreGauge key={s.key} score={s.score!} label={s.label} size="small" />
          ))}
        </div>
      )}

      {/* Coaching summary */}
      {perf.consultant_summary && (
        <div className="p-4 bg-surface-muted rounded-lg border-l-4 border-brand-primary">
          <h5 className="text-xs font-semibold text-text-muted uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <Award className="w-3.5 h-3.5" /> Coaching Summary
          </h5>
          <p className="text-sm text-text-body leading-relaxed italic">{perf.consultant_summary}</p>
        </div>
      )}

      {/* Talk Ratio */}
      <TalkRatioBar data={perf.consultant_talk_ratio} />

      {/* Question Quality */}
      {perf.question_quality && (
        <CollapsibleSection title="Question Quality" count={1} defaultOpen={false}>
          <div className="space-y-3">
            {perf.question_quality.best_question && (
              <div className="p-3 bg-green-50 rounded-lg border border-green-200">
                <span className="text-xs font-semibold text-green-700">Best Question</span>
                <p className="text-sm text-text-body mt-1">&ldquo;{perf.question_quality.best_question}&rdquo;</p>
              </div>
            )}
            {typeof perf.question_quality.open_vs_closed_ratio === 'number' && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-text-muted">Open vs Closed</span>
                <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div className="h-full bg-brand-primary rounded-full" style={{ width: `${Math.round(perf.question_quality.open_vs_closed_ratio * 100)}%` }} />
                </div>
                <span className="text-xs text-text-body font-medium">{Math.round(perf.question_quality.open_vs_closed_ratio * 100)}% open</span>
              </div>
            )}
            {perf.question_quality.missed_opportunities?.length > 0 && (
              <div>
                <span className="text-xs font-semibold text-text-muted">Missed Opportunities</span>
                <ul className="mt-1 space-y-1">
                  {perf.question_quality.missed_opportunities.map((m, i) => (
                    <li key={i} className="text-xs text-text-muted flex items-start gap-1.5">
                      <AlertTriangle className="w-3 h-3 text-amber-500 shrink-0 mt-0.5" />
                      {m}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </CollapsibleSection>
      )}

      {/* Active Listening */}
      {perf.active_listening && (
        <CollapsibleSection title="Active Listening" count={1} defaultOpen={false}>
          <div className="space-y-3">
            <div className="flex gap-4">
              <div className="text-center">
                <span className="text-2xl font-bold text-text-body">{perf.active_listening.paraphrase_count || 0}</span>
                <p className="text-xs text-text-muted">Paraphrases</p>
              </div>
              {typeof perf.active_listening.follow_up_depth === 'number' && (
                <div className="text-center">
                  <span className="text-2xl font-bold text-text-body">{Math.round(perf.active_listening.follow_up_depth * 100)}%</span>
                  <p className="text-xs text-text-muted">Follow-up Depth</p>
                </div>
              )}
            </div>
            {perf.active_listening.examples?.length > 0 && (
              <div className="space-y-2">
                {perf.active_listening.examples.map((ex, i) => (
                  <blockquote key={i} className="text-xs text-text-muted italic border-l-2 border-brand-primary pl-2">
                    {ex}
                  </blockquote>
                ))}
              </div>
            )}
          </div>
        </CollapsibleSection>
      )}

      {/* Discovery Depth */}
      {perf.discovery_depth && (
        <CollapsibleSection title="Discovery Depth" count={1} defaultOpen={false}>
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="text-xs text-text-muted">Surface vs Deep</span>
              <div className="flex-1 h-5 rounded-full overflow-hidden flex">
                {(perf.discovery_depth.surface_questions || 0) > 0 && (
                  <div className="bg-amber-300 flex items-center justify-center" style={{
                    width: `${((perf.discovery_depth.surface_questions || 0) / ((perf.discovery_depth.surface_questions || 0) + (perf.discovery_depth.deep_questions || 0))) * 100}%`
                  }}>
                    <span className="text-[10px] font-bold text-amber-900">{perf.discovery_depth.surface_questions}</span>
                  </div>
                )}
                {(perf.discovery_depth.deep_questions || 0) > 0 && (
                  <div className="bg-green-400 flex items-center justify-center" style={{
                    width: `${((perf.discovery_depth.deep_questions || 0) / ((perf.discovery_depth.surface_questions || 0) + (perf.discovery_depth.deep_questions || 0))) * 100}%`
                  }}>
                    <span className="text-[10px] font-bold text-green-900">{perf.discovery_depth.deep_questions}</span>
                  </div>
                )}
              </div>
            </div>
            <div className="flex gap-3 text-xs text-text-muted">
              <span className="flex items-center gap-1"><span className="w-2 h-2 bg-amber-300 rounded-full" /> Surface</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 bg-green-400 rounded-full" /> Deep</span>
            </div>
            {perf.discovery_depth.reframe_moments?.length > 0 && (
              <div>
                <span className="text-xs font-semibold text-text-muted">Reframe Moments</span>
                <ul className="mt-1 space-y-1">
                  {perf.discovery_depth.reframe_moments.map((m, i) => (
                    <li key={i} className="text-xs text-text-body flex items-start gap-1.5">
                      <Sparkles className="w-3 h-3 text-brand-primary shrink-0 mt-0.5" />
                      {m}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </CollapsibleSection>
      )}

      {/* Objection Handling */}
      {perf.objection_handling && (
        <CollapsibleSection title="Objection Handling" count={1} defaultOpen={false}>
          <div className="space-y-3">
            <div className="flex gap-4">
              <div className="text-center">
                <span className="text-2xl font-bold text-text-body">{perf.objection_handling.objections_surfaced || 0}</span>
                <p className="text-xs text-text-muted">Surfaced</p>
              </div>
              <div className="text-center">
                <span className="text-2xl font-bold text-green-600">{perf.objection_handling.objections_addressed || 0}</span>
                <p className="text-xs text-text-muted">Addressed</p>
              </div>
            </div>
            {perf.objection_handling.technique_notes?.length > 0 && (
              <ul className="space-y-1">
                {perf.objection_handling.technique_notes.map((n, i) => (
                  <li key={i} className="text-xs text-text-muted">{n}</li>
                ))}
              </ul>
            )}
          </div>
        </CollapsibleSection>
      )}

      {/* Next Steps Clarity */}
      {perf.next_steps_clarity && (
        <CollapsibleSection title="Next Steps Clarity" count={1} defaultOpen={false}>
          <div className="space-y-3">
            {perf.next_steps_clarity.commitments_made?.length > 0 && (
              <div>
                <span className="text-xs font-semibold text-green-700">Commitments</span>
                <ul className="mt-1 space-y-1">
                  {perf.next_steps_clarity.commitments_made.map((c, i) => (
                    <li key={i} className="text-xs text-text-body flex items-start gap-1.5">
                      <Check className="w-3 h-3 text-green-600 shrink-0 mt-0.5" />
                      {c}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {perf.next_steps_clarity.follow_ups_assigned?.length > 0 && (
              <div>
                <span className="text-xs font-semibold text-blue-700">Follow-ups</span>
                <ul className="mt-1 space-y-1">
                  {perf.next_steps_clarity.follow_ups_assigned.map((f, i) => (
                    <li key={i} className="text-xs text-text-body flex items-start gap-1.5">
                      <ArrowRight className="w-3 h-3 text-blue-600 shrink-0 mt-0.5" />
                      {f}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {perf.next_steps_clarity.ambiguous_items?.length > 0 && (
              <div>
                <span className="text-xs font-semibold text-amber-700">Ambiguous Items</span>
                <ul className="mt-1 space-y-1">
                  {perf.next_steps_clarity.ambiguous_items.map((a, i) => (
                    <li key={i} className="text-xs text-text-muted flex items-start gap-1.5">
                      <AlertTriangle className="w-3 h-3 text-amber-500 shrink-0 mt-0.5" />
                      {a}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </CollapsibleSection>
      )}
    </div>
  )
}

// ============================================================================
// Main Panel
// ============================================================================

type Tab = 'recordings' | 'strategy' | 'insights' | 'performance'

export function CallsPanel({ projectId }: { projectId: string }) {
  const [activeTab, setActiveTab] = useState<Tab>('recordings')
  const [selectedRecordingId, setSelectedRecordingId] = useState<string | null>(null)
  const [loadedDetails, setLoadedDetails] = useState<CallDetails | null>(null)

  const handleSelectRecording = (recordingId: string) => {
    setSelectedRecordingId(recordingId)
    setActiveTab('insights')
    // Pre-fetch details for performance tab
    getCallDetails(recordingId)
      .then(d => setLoadedDetails(d))
      .catch(() => setLoadedDetails(null))
  }

  const handleBack = () => {
    setSelectedRecordingId(null)
    setLoadedDetails(null)
    setActiveTab('recordings')
  }

  const tabs: { key: Tab; label: string; icon: typeof Phone; disabled: boolean }[] = [
    { key: 'recordings', label: 'Recordings', icon: Phone, disabled: false },
    { key: 'strategy', label: 'Strategy', icon: FileText, disabled: false },
    { key: 'insights', label: 'Insights', icon: BarChart3, disabled: !selectedRecordingId },
    { key: 'performance', label: 'Performance', icon: Award, disabled: !selectedRecordingId },
  ]

  return (
    <div className="flex flex-col h-full">
      {/* Tab bar */}
      <div className="flex items-center gap-1 px-6 py-2 border-b border-border bg-white shrink-0">
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
        {activeTab === 'recordings' && (
          <RecordingsTab projectId={projectId} onSelectRecording={handleSelectRecording} />
        )}
        {activeTab === 'strategy' && (
          <StrategyTab
            recordingId={selectedRecordingId}
            brief={loadedDetails?.strategy_brief}
            projectId={projectId}
            onBack={handleBack}
          />
        )}
        {activeTab === 'insights' && selectedRecordingId && (
          <InsightsTab recordingId={selectedRecordingId} onBack={handleBack} />
        )}
        {activeTab === 'performance' && (
          <PerformanceTab details={loadedDetails} onBack={handleBack} />
        )}
      </div>
    </div>
  )
}
