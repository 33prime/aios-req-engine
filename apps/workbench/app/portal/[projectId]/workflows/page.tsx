'use client'

import { useCallback, useEffect, useState } from 'react'
import { Check, Pencil, AlertTriangle, ChevronLeft, ChevronRight, Clock, CheckCircle2 } from 'lucide-react'
import { Spinner } from '@/components/ui/Spinner'
import { submitWorkflowVerdict } from '@/lib/api/portal'
import { usePortal } from '../PortalShell'
import type { WorkflowPair, WorkflowStepSummary, AutomationLevel, ROISummary } from '@/types/workspace'
import type { VerdictType } from '@/types/portal'

// ============================================================================
// Automation Badge (matches BRD exactly)
// ============================================================================

function AutomationBadge({ level }: { level: AutomationLevel }) {
  const config: Record<AutomationLevel, { dot: string; label: string; bg: string; text: string }> = {
    manual: { dot: 'bg-gray-400', label: 'Manual', bg: 'bg-gray-100', text: 'text-gray-600' },
    semi_automated: { dot: 'bg-amber-400', label: 'Semi-auto', bg: 'bg-amber-50', text: 'text-amber-700' },
    fully_automated: { dot: 'bg-brand-primary', label: 'Automated', bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
  }
  const c = config[level] || config.manual
  return (
    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium ${c.bg} ${c.text} rounded`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      {c.label}
    </span>
  )
}

// ============================================================================
// Step Card (numbered badge + connector, with click-to-feedback)
// ============================================================================

function StepCard({
  step,
  index,
  isLast,
  stateType,
  feedback,
  onFeedbackChange,
}: {
  step: WorkflowStepSummary
  index: number
  isLast: boolean
  stateType: 'current' | 'future'
  feedback?: string
  onFeedbackChange: (text: string | undefined) => void
}) {
  const [open, setOpen] = useState(false)

  return (
    <div className="flex gap-3">
      {/* Left: numbered badge + connector line */}
      <div className="flex flex-col items-center shrink-0">
        <div className="w-7 h-7 rounded-full bg-[#0A1E2F] flex items-center justify-center shrink-0">
          <span className="text-[11px] font-bold text-white">{index}</span>
        </div>
        {!isLast && (
          <div className="w-0 flex-1 border-l-2 border-dashed border-border min-h-[16px]" />
        )}
      </div>

      {/* Right: step content */}
      <div className="flex-1 min-w-0 pb-4">
        <div
          className={`bg-white border rounded-xl px-3.5 py-2.5 transition-all cursor-pointer hover:shadow-sm ${
            open ? 'border-brand-primary shadow-sm' : 'border-border'
          } ${feedback ? 'ring-1 ring-amber-300' : ''}`}
          onClick={() => setOpen(!open)}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="text-[13px] font-medium text-text-body">{step.label}</span>
                <AutomationBadge level={step.automation_level} />
                {step.time_minutes != null && (
                  <span className="inline-flex items-center gap-0.5 text-[11px] text-text-placeholder">
                    <Clock className="w-3 h-3" />
                    {step.time_minutes}m
                  </span>
                )}
              </div>
              {step.description && (
                <p className="text-[12px] text-[#666666] mt-1 line-clamp-2">{step.description}</p>
              )}
            </div>
            {feedback && (
              <span className="text-[10px] text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded shrink-0">
                Has feedback
              </span>
            )}
          </div>

          {/* Pain / Benefit text */}
          {stateType === 'current' && step.pain_description && (
            <p className="text-[11px] text-text-placeholder mt-1.5 italic">Pain: {step.pain_description}</p>
          )}
          {stateType === 'future' && step.benefit_description && (
            <p className="text-[11px] text-[#25785A] mt-1.5 italic">Benefit: {step.benefit_description}</p>
          )}

          {/* Actor persona pill */}
          {step.actor_persona_name && (
            <div className="mt-1.5">
              <span className="px-2 py-0.5 text-[10px] font-medium bg-[#E8F5E9] text-[#25785A] rounded-full">
                {step.actor_persona_name}
              </span>
            </div>
          )}
        </div>

        {/* Inline feedback textarea */}
        {open && (
          <div className="mt-2 ml-1">
            <textarea
              value={feedback || ''}
              onChange={e => onFeedbackChange(e.target.value || undefined)}
              rows={2}
              placeholder="Any corrections for this step? (optional)"
              className="w-full px-3 py-2 text-sm border border-border rounded-lg focus:ring-2 focus:ring-brand-primary-ring focus:border-brand-primary resize-none"
              onClick={e => e.stopPropagation()}
            />
          </div>
        )}
      </div>
    </div>
  )
}

// ============================================================================
// Step Column (Current or Future side)
// ============================================================================

function StepColumn({
  steps,
  stateType,
  stepFeedback,
  onStepFeedback,
}: {
  steps: WorkflowStepSummary[]
  stateType: 'current' | 'future'
  stepFeedback: Record<string, string>
  onStepFeedback: (stepId: string, text: string | undefined) => void
}) {
  const isCurrent = stateType === 'current'

  return (
    <div className="flex-1 min-w-0">
      {/* Column header */}
      <div className={`px-3 py-1.5 rounded-lg mb-3 ${
        isCurrent
          ? 'bg-[#F0F0F0] text-[#666666]'
          : 'bg-[#E8F5E9] text-[#25785A]'
      }`}>
        <span className="text-[11px] font-semibold uppercase tracking-wider">
          {isCurrent ? 'Today' : 'With Your Solution'}
        </span>
      </div>

      {/* Steps */}
      {steps.length > 0 ? (
        <div>
          {steps.map((step, idx) => (
            <StepCard
              key={step.id}
              step={step}
              index={idx + 1}
              isLast={idx === steps.length - 1}
              stateType={stateType}
              feedback={stepFeedback[step.id]}
              onFeedbackChange={text => onStepFeedback(step.id, text)}
            />
          ))}
        </div>
      ) : (
        <p className="text-[12px] text-text-placeholder italic py-3 px-3">No steps yet</p>
      )}
    </div>
  )
}

// ============================================================================
// ROI Bar (time only, no dollar amounts)
// ============================================================================

function ROIBar({ roi }: { roi: ROISummary }) {
  const pct = Math.min(Math.max(roi.time_saved_percent, 0), 100)
  const weeklyHours = Math.round((roi.time_saved_minutes * 5) / 60 * 10) / 10 // assume 5 runs/week

  return (
    <div className="mt-4 pt-4 border-t border-border">
      {/* Progress bar */}
      <div className="flex items-center gap-2 mb-2">
        <span className="text-[11px] text-[#666666] w-16 shrink-0">Time saved</span>
        <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-brand-primary rounded-full transition-all"
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="text-[11px] font-medium text-text-body w-10 text-right">
          {roi.time_saved_percent}%
        </span>
      </div>
      {/* Stats row */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-[#666666]">
        <span className="font-medium text-[#25785A]">
          {roi.time_saved_minutes}min saved/run
        </span>
        {weeklyHours > 0 && (
          <span className="font-medium text-[#25785A]">
            ~{weeklyHours}hrs saved/week
          </span>
        )}
        {roi.steps_automated > 0 && (
          <span>{roi.steps_automated}/{roi.steps_total} steps automated</span>
        )}
      </div>
    </div>
  )
}

// ============================================================================
// Verdict Buttons
// ============================================================================

const VERDICT_CONFIG: Record<VerdictType, { icon: typeof Check; label: string; border: string; bg: string; text: string; activeBg: string }> = {
  confirmed: {
    icon: Check,
    label: 'This is right',
    border: 'border-brand-primary',
    bg: 'bg-[#E8F5E9]',
    text: 'text-[#25785A]',
    activeBg: 'bg-[#E8F5E9]',
  },
  refine: {
    icon: Pencil,
    label: "Something's off",
    border: 'border-amber-400',
    bg: 'bg-amber-50',
    text: 'text-amber-700',
    activeBg: 'bg-amber-50',
  },
  flag: {
    icon: AlertTriangle,
    label: 'Missing steps',
    border: 'border-red-400',
    bg: 'bg-red-50',
    text: 'text-red-700',
    activeBg: 'bg-red-50',
  },
}

// ============================================================================
// Main Page
// ============================================================================

export default function WorkflowsPage() {
  const { projectId, workflowPairs, refreshWorkflows, refreshDashboard, setChatConfig } = usePortal()
  const [currentIndex, setCurrentIndex] = useState(0)
  const [verdicts, setVerdicts] = useState<Record<string, VerdictType>>({})
  const [notes, setNotes] = useState<Record<string, string>>({})
  const [stepFeedback, setStepFeedback] = useState<Record<string, Record<string, string>>>({})
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState<Set<string>>(new Set())

  const pairs = workflowPairs
  const total = pairs.length
  const reviewedCount = submitted.size
  const allReviewed = total > 0 && reviewedCount === total
  const current = pairs[currentIndex] as WorkflowPair | undefined

  // Register workflow-aware chat config
  useEffect(() => {
    const workflowName = current?.name
    setChatConfig({
      station: 'workflow',
      title: workflowName ? `Discussing: ${workflowName}` : 'Workflow Review',
      greeting: workflowName
        ? `I can help you review the "${workflowName}" workflow. What looks off, or what's missing from how your team actually works?`
        : "I can help you think through your workflows. Which one would you like to discuss?",
    })
    return () => setChatConfig(null)
  }, [setChatConfig, current?.name])

  // Initialize verdicts from existing confirmation_status
  const getExistingVerdict = useCallback((pair: WorkflowPair): VerdictType | undefined => {
    if (submitted.has(pair.id)) return verdicts[pair.id]
    if (pair.confirmation_status === 'confirmed_client') return 'confirmed'
    return undefined
  }, [submitted, verdicts])

  const handleVerdictSelect = useCallback((workflowId: string, verdict: VerdictType) => {
    setVerdicts(prev => ({ ...prev, [workflowId]: verdict }))
  }, [])

  const handleStepFeedback = useCallback((workflowId: string, stepId: string, text: string | undefined) => {
    setStepFeedback(prev => {
      const wfFeedback = { ...prev[workflowId] }
      if (text) {
        wfFeedback[stepId] = text
      } else {
        delete wfFeedback[stepId]
      }
      return { ...prev, [workflowId]: wfFeedback }
    })
  }, [])

  const handleSubmit = useCallback(async () => {
    if (!current) return
    const verdict = verdicts[current.id]
    if (!verdict) return

    setSubmitting(true)
    try {
      const feedbackEntries = stepFeedback[current.id]
      const step_feedback = feedbackEntries
        ? Object.entries(feedbackEntries).map(([step_id, text]) => ({ step_id, text }))
        : undefined

      await submitWorkflowVerdict(projectId, current.id, {
        verdict,
        notes: notes[current.id] || undefined,
        step_feedback: step_feedback?.length ? step_feedback : undefined,
      })

      setSubmitted(prev => new Set(prev).add(current.id))
      await Promise.all([refreshWorkflows(), refreshDashboard()])

      // Auto-advance to next unreviewed
      if (currentIndex < total - 1) {
        setCurrentIndex(currentIndex + 1)
      }
    } catch (err) {
      console.error('Failed to submit verdict:', err)
    } finally {
      setSubmitting(false)
    }
  }, [current, verdicts, notes, stepFeedback, projectId, refreshWorkflows, refreshDashboard, currentIndex, total])

  // Loading state (pairs come from context, but might not be loaded yet)
  if (!workflowPairs) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Spinner size="lg" label="Loading workflows..." />
      </div>
    )
  }

  // Empty state
  if (total === 0) {
    return (
      <div className="max-w-2xl space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Your Workflows</h1>
          <p className="text-text-muted mt-1">
            Help us make sure we captured your processes accurately.
          </p>
        </div>
        <div className="text-center py-16">
          <div className="w-12 h-12 bg-surface-subtle rounded-full flex items-center justify-center mx-auto mb-4">
            <Clock className="w-6 h-6 text-text-placeholder" />
          </div>
          <p className="text-text-muted">
            No workflows to review yet. Check back after your discovery call.
          </p>
        </div>
      </div>
    )
  }

  // All reviewed state
  if (allReviewed) {
    return (
      <div className="max-w-2xl space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Your Workflows</h1>
          <p className="text-text-muted mt-1">
            Help us make sure we captured your processes accurately.
          </p>
        </div>
        <div className="text-center py-16">
          <div className="w-16 h-16 bg-[#E8F5E9] rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle2 className="w-8 h-8 text-brand-primary" />
          </div>
          <h2 className="text-xl font-semibold text-text-primary mb-2">
            All workflows reviewed!
          </h2>
          <p className="text-text-muted">
            Thank you for taking the time to validate your workflows. Your feedback helps us build exactly what your team needs.
          </p>
        </div>
      </div>
    )
  }

  const progressPct = total > 0 ? Math.round((reviewedCount / total) * 100) : 0
  const selectedVerdict = current ? (verdicts[current.id] || getExistingVerdict(current)) : undefined
  const isCurrentSubmitted = current ? submitted.has(current.id) || current.confirmation_status === 'confirmed_client' : false
  const showNotes = selectedVerdict === 'refine' || selectedVerdict === 'flag'

  return (
    <div className="max-w-3xl space-y-6">
      {/* Header + progress */}
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Your Workflows</h1>
        <p className="text-text-muted mt-1">
          Help us make sure we captured your processes accurately.
        </p>
        <div className="mt-4">
          <div className="flex items-center justify-between text-sm mb-1.5">
            <span className="text-text-secondary">{reviewedCount} of {total} reviewed</span>
            <span className="font-medium text-brand-primary">{progressPct}%</span>
          </div>
          <div className="w-full h-2 bg-surface-subtle rounded-full overflow-hidden">
            <div
              className="h-full bg-brand-primary rounded-full transition-all duration-500"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>
      </div>

      {/* Workflow Card */}
      {current && (
        <div className="bg-white rounded-2xl shadow-md border border-border overflow-hidden">
          {/* Header */}
          <div className="px-6 py-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-[14px] font-semibold text-text-body">{current.name}</h2>
                {current.owner && (
                  <span className="text-[12px] text-text-placeholder mt-0.5 block">
                    Owner: {current.owner}
                  </span>
                )}
              </div>
              {isCurrentSubmitted && (
                <span className="text-[11px] font-medium px-2 py-1 bg-[#E8F5E9] text-[#25785A] rounded-full">
                  Reviewed
                </span>
              )}
            </div>
          </div>

          {/* Narrative / Description */}
          {current.description && (
            <div className="mx-6 mb-4 px-4 py-3 rounded-xl bg-gradient-to-r from-gray-50 to-slate-50 border border-border/50">
              <p className="text-[12px] text-[#666666] leading-relaxed italic">
                {current.description}
              </p>
            </div>
          )}

          {/* Two-column step layout */}
          <div className="px-6 pb-2">
            <div className="flex gap-6">
              {(current.current_steps.length > 0 || current.current_workflow_id) && (
                <StepColumn
                  steps={current.current_steps}
                  stateType="current"
                  stepFeedback={stepFeedback[current.id] || {}}
                  onStepFeedback={(stepId, text) => handleStepFeedback(current.id, stepId, text)}
                />
              )}
              <StepColumn
                steps={current.future_steps}
                stateType="future"
                stepFeedback={stepFeedback[current.id] || {}}
                onStepFeedback={(stepId, text) => handleStepFeedback(current.id, stepId, text)}
              />
            </div>
          </div>

          {/* ROI bar (time only) */}
          {current.roi && current.roi.time_saved_minutes > 0 && (
            <div className="px-6 pb-4">
              <ROIBar roi={current.roi} />
            </div>
          )}

          {/* Verdict section */}
          {!isCurrentSubmitted && (
            <div className="border-t border-border px-6 py-5">
              <p className="text-[13px] font-medium text-text-body mb-3">
                Does this accurately reflect how your team works?
              </p>

              {/* Verdict buttons */}
              <div className="grid grid-cols-3 gap-3 mb-4">
                {(Object.entries(VERDICT_CONFIG) as [VerdictType, typeof VERDICT_CONFIG[VerdictType]][]).map(([key, cfg]) => {
                  const Icon = cfg.icon
                  const isSelected = selectedVerdict === key
                  return (
                    <button
                      key={key}
                      onClick={() => handleVerdictSelect(current.id, key)}
                      className={`flex flex-col items-center gap-2 px-4 py-3.5 rounded-xl border-2 transition-all text-center ${
                        isSelected
                          ? `${cfg.border} ${cfg.activeBg} ${cfg.text} shadow-sm`
                          : 'border-border bg-white text-text-secondary hover:bg-gray-50'
                      }`}
                    >
                      <Icon className="w-5 h-5" />
                      <span className="text-[12px] font-medium">{cfg.label}</span>
                    </button>
                  )
                })}
              </div>

              {/* Notes textarea (shown for refine/flag) */}
              {showNotes && (
                <div className="mb-4">
                  <textarea
                    value={notes[current.id] || ''}
                    onChange={e => setNotes(prev => ({ ...prev, [current.id]: e.target.value }))}
                    rows={3}
                    placeholder={
                      selectedVerdict === 'refine'
                        ? "What's different from how your team actually works?"
                        : 'What steps or processes are missing?'
                    }
                    className="w-full px-3 py-2 text-sm border border-border rounded-lg focus:ring-2 focus:ring-brand-primary-ring focus:border-brand-primary resize-none"
                  />
                </div>
              )}

              {/* Submit button */}
              <button
                onClick={handleSubmit}
                disabled={!selectedVerdict || submitting}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-brand-primary text-white text-sm font-medium rounded-lg hover:bg-brand-primary-hover transition-colors disabled:opacity-50"
              >
                {submitting ? (
                  <Spinner size="sm" />
                ) : (
                  <Check className="w-4 h-4" />
                )}
                Submit Review
              </button>
            </div>
          )}

          {/* Already submitted message */}
          {isCurrentSubmitted && (
            <div className="border-t border-border px-6 py-4 bg-[#E8F5E9]/30">
              <div className="flex items-center gap-2 text-sm text-[#25785A]">
                <CheckCircle2 className="w-4 h-4" />
                <span>You&apos;ve reviewed this workflow. Thank you!</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Navigation */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => setCurrentIndex(Math.max(0, currentIndex - 1))}
          disabled={currentIndex === 0}
          className="flex items-center gap-1.5 px-4 py-2 text-sm text-text-secondary hover:text-text-primary transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <ChevronLeft className="w-4 h-4" />
          Previous
        </button>

        {/* Progress dots */}
        <div className="flex items-center gap-2">
          {pairs.map((pair, idx) => {
            const isReviewed = submitted.has(pair.id) || pair.confirmation_status === 'confirmed_client'
            const isActive = idx === currentIndex
            return (
              <button
                key={pair.id}
                onClick={() => setCurrentIndex(idx)}
                className={`w-2.5 h-2.5 rounded-full transition-all ${
                  isActive
                    ? 'bg-brand-primary scale-125'
                    : isReviewed
                      ? 'bg-brand-primary/40'
                      : 'bg-gray-300'
                }`}
                title={pair.name}
              />
            )
          })}
        </div>

        <button
          onClick={() => setCurrentIndex(Math.min(total - 1, currentIndex + 1))}
          disabled={currentIndex === total - 1}
          className="flex items-center gap-1.5 px-4 py-2 text-sm text-text-secondary hover:text-text-primary transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
        >
          Next Workflow
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}
