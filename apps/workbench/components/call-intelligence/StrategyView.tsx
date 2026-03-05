'use client'

import { useState, useEffect } from 'react'
import {
  Target,
  MessageCircle,
  Zap,
  Shield,
  Users,
  TrendingUp,
  ArrowRight,
  Loader2,
  FileText,
  Sparkles,
} from 'lucide-react'
import {
  generateStrategyBrief,
  getBriefForRecording,
} from '@/lib/api'
import type {
  CallStrategyBrief,
  GoalResult,
  FocusArea,
  StakeholderIntel,
  MissionCriticalQuestion,
} from '@/types/call-intelligence'
import { ScoreGauge } from './ScoreGauge'
import { GoalStatusBadge } from './GoalStatusBadge'

export function StrategyView({
  recordingId,
  brief: initialBrief,
  projectId,
  onBack,
}: {
  recordingId?: string | null
  brief?: CallStrategyBrief | null
  projectId: string
  onBack?: () => void
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
        {onBack && <button onClick={onBack} className="text-xs text-brand-primary hover:underline mt-2">Back to recordings</button>}
      </div>
    )
  }

  const { call_goals, goal_results, mission_critical_questions, focus_areas, deal_readiness_snapshot, stakeholder_intel, ambiguity_snapshot, project_awareness_snapshot, readiness_delta } = brief

  return (
    <div className="overflow-y-auto h-full p-6 space-y-6">
      {onBack && <button onClick={onBack} className="text-sm text-brand-primary hover:underline">&larr; Back to recordings</button>}

      {/* Readiness delta hero (if post-call) */}
      {readiness_delta && (
        <div className="p-4 bg-gradient-to-r from-brand-primary-light to-green-50 rounded-xl border border-brand-primary/20">
          <div className="flex items-center gap-3">
            <TrendingUp className="w-5 h-5 text-brand-primary" />
            <span className="text-sm font-semibold text-text-body">
              Readiness moved from {readiness_delta.before_score} &rarr; {readiness_delta.after_score}
              {' '}
              <span className={readiness_delta.after_score > readiness_delta.before_score ? 'text-[#25785A]' : 'text-[#044159]'}>
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
                    fa.priority === 'high' ? 'bg-[#044159] text-white' :
                    fa.priority === 'medium' ? 'bg-[#E0EFF3] text-[#044159]' :
                    'bg-[#F0F0F0] text-[#666]'
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
                      s.influence === 'high' ? 'bg-[#044159] text-white' :
                      s.influence === 'medium' ? 'bg-[#E0EFF3] text-[#044159]' :
                      'bg-[#F0F0F0] text-[#666]'
                    }`}>
                      {s.influence}
                    </span>
                  </div>
                  {s.role && <p className="text-xs text-text-muted">{s.role}</p>}
                  {s.key_concerns.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {s.key_concerns.map((c, j) => (
                        <span key={j} className="px-1.5 py-0.5 text-[10px] bg-[#E0EFF3] text-[#044159] rounded">
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
