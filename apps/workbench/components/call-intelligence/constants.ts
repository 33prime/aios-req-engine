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
  complete: 'bg-[#E8F5E9] text-[#25785A]',
  analyzing: 'bg-[#E0EFF3] text-[#044159] animate-pulse',
  transcribing: 'bg-[#E0EFF3] text-[#044159] animate-pulse',
  bot_scheduled: 'bg-[#E0EFF3] text-[#044159]',
  recording: 'bg-[#E0EFF3] text-[#044159] animate-pulse',
  pending: 'bg-[#F0F0F0] text-[#666]',
  failed: 'bg-[#044159] text-white',
  skipped: 'bg-[#F0F0F0] text-[#999]',
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
  excited: { icon: Star, color: 'text-[#25785A] bg-[#E8F5E9]', label: 'Excited' },
  interested: { icon: ThumbsUp, color: 'text-[#044159] bg-[#E0EFF3]', label: 'Interested' },
  neutral: { icon: MinusCircle, color: 'text-[#666] bg-[#F0F0F0]', label: 'Neutral' },
  confused: { icon: HelpCircle, color: 'text-[#044159] bg-[#E0EFF3]', label: 'Confused' },
  resistant: { icon: XCircle, color: 'text-white bg-[#044159]', label: 'Resistant' },
}

export const SIGNAL_TYPE_STYLES: Record<CallSignalType, string> = {
  pain_point: 'bg-[#044159] text-white',
  goal: 'bg-[#E8F5E9] text-[#25785A]',
  budget_indicator: 'bg-[#E0EFF3] text-[#044159]',
  timeline: 'bg-[#E0EFF3] text-[#044159]',
  decision_criteria: 'bg-[#E8F5E9] text-[#25785A]',
  risk_factor: 'bg-[#044159] text-white',
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
  testimonial: 'bg-[#E8F5E9] text-[#25785A]',
  soundbite: 'bg-[#E0EFF3] text-[#044159]',
  statistic: 'bg-[#E0EFF3] text-[#044159]',
  use_case: 'bg-[#E8F5E9] text-[#25785A]',
  objection: 'bg-[#044159] text-white',
  vision_statement: 'bg-[#E8F5E9] text-[#25785A]',
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
  positive: 'bg-[#E8F5E9] text-[#25785A]',
  neutral: 'bg-[#F0F0F0] text-[#666]',
  negative: 'bg-[#044159] text-white',
}

export function formatDuration(seconds: number | null | undefined): string {
  if (!seconds) return '\u2014'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}
