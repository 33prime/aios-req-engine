'use client'

import {
  AlertTriangle,
  Award,
  Check,
  ArrowRight,
  Sparkles,
} from 'lucide-react'
import type { CallDetails } from '@/types/call-intelligence'
import { ScoreGauge } from './ScoreGauge'
import { CollapsibleSection } from './CollapsibleSection'
import { TalkRatioBar } from './TalkRatioBar'

export function PerformanceView({
  details,
  onBack,
}: {
  details: CallDetails | null
  onBack?: () => void
}) {
  const perf = details?.consultant_performance

  if (!perf) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-text-muted gap-2">
        <Award className="w-8 h-8" />
        <p className="text-sm">No consultant performance data available.</p>
        <p className="text-xs">Re-analyze with the consultant dimension pack to see coaching insights.</p>
        {onBack && <button onClick={onBack} className="text-xs text-brand-primary hover:underline mt-2">Back to recordings</button>}
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
      {onBack && <button onClick={onBack} className="text-sm text-brand-primary hover:underline">&larr; Back to recordings</button>}

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
