import {
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
} from 'lucide-react'
import type {
  CallRecordingStatus,
  ReactionType,
  CallSignalType,
  NuggetType,
  SentimentType,
} from '@/types/call-intelligence'

export const STATUS_STYLES: Record<CallRecordingStatus, string> = {
  complete: 'bg-brand-primary-light text-brand-primary',
  analyzing: 'bg-amber-100 text-amber-700 animate-pulse',
  transcribing: 'bg-amber-100 text-amber-700 animate-pulse',
  bot_scheduled: 'bg-blue-100 text-blue-700',
  recording: 'bg-blue-100 text-blue-700 animate-pulse',
  pending: 'bg-blue-100 text-blue-700',
  failed: 'bg-red-100 text-red-700',
  skipped: 'bg-gray-100 text-gray-500',
}

export const STATUS_LABELS: Record<CallRecordingStatus, string> = {
  complete: 'Complete',
  analyzing: 'Analyzing...',
  transcribing: 'Transcribing...',
  bot_scheduled: 'Scheduled',
  recording: 'Recording...',
  pending: 'Pending',
  failed: 'Failed',
  skipped: 'Skipped',
}

export const REACTION_CONFIG: Record<ReactionType, { icon: typeof Star; color: string; label: string }> = {
  excited: { icon: Star, color: 'text-green-600 bg-green-50', label: 'Excited' },
  interested: { icon: ThumbsUp, color: 'text-blue-600 bg-blue-50', label: 'Interested' },
  neutral: { icon: MinusCircle, color: 'text-gray-500 bg-gray-50', label: 'Neutral' },
  confused: { icon: HelpCircle, color: 'text-amber-600 bg-amber-50', label: 'Confused' },
  resistant: { icon: XCircle, color: 'text-red-600 bg-red-50', label: 'Resistant' },
}

export const SIGNAL_TYPE_STYLES: Record<CallSignalType, string> = {
  pain_point: 'bg-red-100 text-red-700',
  goal: 'bg-green-100 text-green-700',
  budget_indicator: 'bg-amber-100 text-amber-700',
  timeline: 'bg-blue-100 text-blue-700',
  decision_criteria: 'bg-purple-100 text-purple-700',
  risk_factor: 'bg-orange-100 text-orange-700',
}

export const SIGNAL_TYPE_ICONS: Record<CallSignalType, typeof AlertTriangle> = {
  pain_point: AlertTriangle,
  goal: Target,
  budget_indicator: DollarSign,
  timeline: Calendar,
  decision_criteria: CheckSquare,
  risk_factor: Zap,
}

export const SIGNAL_TYPE_LABELS: Record<CallSignalType, string> = {
  pain_point: 'Pain Point',
  goal: 'Goal',
  budget_indicator: 'Budget',
  timeline: 'Timeline',
  decision_criteria: 'Decision Criteria',
  risk_factor: 'Risk Factor',
}

export const NUGGET_TYPE_STYLES: Record<NuggetType, string> = {
  testimonial: 'bg-green-100 text-green-700',
  soundbite: 'bg-blue-100 text-blue-700',
  statistic: 'bg-purple-100 text-purple-700',
  use_case: 'bg-amber-100 text-amber-700',
  objection: 'bg-red-100 text-red-700',
  vision_statement: 'bg-indigo-100 text-indigo-700',
}

export const NUGGET_TYPE_LABELS: Record<NuggetType, string> = {
  testimonial: 'Testimonial',
  soundbite: 'Soundbite',
  statistic: 'Statistic',
  use_case: 'Use Case',
  objection: 'Objection',
  vision_statement: 'Vision',
}

export const SENTIMENT_STYLES: Record<SentimentType, string> = {
  positive: 'bg-green-100 text-green-700',
  neutral: 'bg-gray-100 text-gray-600',
  negative: 'bg-red-100 text-red-700',
}

export function formatDuration(seconds: number | null | undefined): string {
  if (!seconds) return '\u2014'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}
