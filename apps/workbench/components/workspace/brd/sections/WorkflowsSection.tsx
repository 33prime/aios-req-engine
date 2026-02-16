'use client'

import { useState } from 'react'
import { Workflow, Clock, Plus, Pencil, Link2, Trash2, ChevronRight } from 'lucide-react'
import { SectionHeader } from '../components/SectionHeader'
import { BRDStatusBadge } from '../components/StatusBadge'
import { StaleIndicator } from '../components/StaleIndicator'
import type {
  VpStepBRDSummary,
  WorkflowPair,
  WorkflowStepSummary,
  ROISummary,
  AutomationLevel,
  SectionScore,
} from '@/types/workspace'

interface WorkflowsSectionProps {
  workflows: VpStepBRDSummary[]
  workflowPairs?: WorkflowPair[]
  roiSummary?: ROISummary[]
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
  onConfirmAll: (entityType: string, ids: string[]) => void
  // Workflow CRUD callbacks
  onCreateWorkflow?: () => void
  onEditWorkflow?: (workflowId: string) => void
  onDeleteWorkflow?: (workflowId: string) => void
  onPairWorkflow?: (workflowId: string) => void
  onCreateStep?: (workflowId: string, stateType: 'current' | 'future') => void
  onEditStep?: (workflowId: string, stepId: string) => void
  onDeleteStep?: (workflowId: string, stepId: string) => void
  onRefreshEntity?: (entityType: string, entityId: string) => void
  onStatusClick?: (entityType: string, entityId: string, entityName: string, status?: string | null) => void
  onViewStepDetail?: (stepId: string) => void
  onViewWorkflowDetail?: (workflowId: string) => void
  sectionScore?: SectionScore | null
}

// ============================================================================
// Automation Level Badge
// ============================================================================

function AutomationBadge({ level }: { level: AutomationLevel }) {
  const config: Record<AutomationLevel, { dot: string; label: string; bg: string; text: string }> = {
    manual: { dot: 'bg-gray-400', label: 'Manual', bg: 'bg-gray-100', text: 'text-gray-600' },
    semi_automated: { dot: 'bg-amber-400', label: 'Semi-auto', bg: 'bg-amber-50', text: 'text-amber-700' },
    fully_automated: { dot: 'bg-[#3FAF7A]', label: 'Automated', bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
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
// ROI Footer Bar
// ============================================================================

function ROIFooter({ roi }: { roi: ROISummary }) {
  const pct = Math.min(Math.max(roi.time_saved_percent, 0), 100)
  return (
    <div className="mt-4 pt-4 border-t border-[#E5E5E5] space-y-2">
      {/* Progress bar */}
      <div className="flex items-center gap-2">
        <span className="text-[11px] text-[#666666] w-16 shrink-0">Time saved</span>
        <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-[#3FAF7A] rounded-full transition-all"
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="text-[11px] font-medium text-[#333333] w-10 text-right">
          {roi.time_saved_percent}%
        </span>
      </div>
      {/* Stats row */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-[#666666]">
        <span>
          {roi.current_total_minutes}min → {roi.future_total_minutes}min
        </span>
        <span className="font-medium text-[#25785A]">
          Saves {roi.time_saved_minutes}min/run
        </span>
        {roi.cost_saved_per_week > 0 && (
          <span>
            ${roi.cost_saved_per_week.toLocaleString()}/wk (${roi.cost_saved_per_year.toLocaleString()}/yr)
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
// Step Card (numbered badge + connector line)
// ============================================================================

function StepCard({
  step,
  index,
  isLast,
  stateType,
  onEdit,
  onDelete,
  onViewDetail,
}: {
  step: WorkflowStepSummary
  index: number
  isLast: boolean
  stateType: 'current' | 'future'
  onEdit?: () => void
  onDelete?: () => void
  onViewDetail?: () => void
}) {
  return (
    <div className="flex gap-3 group/step">
      {/* Left: numbered badge + connector line */}
      <div className="flex flex-col items-center shrink-0">
        <div className="w-7 h-7 rounded-full bg-[#0A1E2F] flex items-center justify-center shrink-0">
          <span className="text-[11px] font-bold text-white">{index}</span>
        </div>
        {!isLast && (
          <div className="w-0 flex-1 border-l-2 border-dashed border-[#E5E5E5] min-h-[16px]" />
        )}
      </div>

      {/* Right: step content */}
      <div className="flex-1 min-w-0 pb-4">
        <div
          className={`bg-white border border-[#E5E5E5] rounded-xl px-3.5 py-2.5 hover:shadow-sm transition-shadow ${onViewDetail ? 'cursor-pointer' : ''}`}
          onClick={onViewDetail}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="text-[13px] font-medium text-[#333333]">{step.label}</span>
                <AutomationBadge level={step.automation_level} />
                {step.time_minutes != null && (
                  <span className="inline-flex items-center gap-0.5 text-[11px] text-[#999999]">
                    <Clock className="w-3 h-3" />
                    {step.time_minutes}m
                  </span>
                )}
              </div>
              {step.description && (
                <p className="text-[12px] text-[#666666] mt-1 line-clamp-2">{step.description}</p>
              )}
            </div>

            {/* Hover actions */}
            {(onEdit || onDelete) && (
              <div className="flex items-center gap-0.5 opacity-0 group-hover/step:opacity-100 transition-opacity shrink-0" onClick={(e) => e.stopPropagation()}>
                {onEdit && (
                  <button onClick={onEdit} className="p-1 rounded hover:bg-gray-100 text-[#999999] hover:text-[#333333]" title="Edit step">
                    <Pencil className="w-3 h-3" />
                  </button>
                )}
                {onDelete && (
                  <button onClick={onDelete} className="p-1 rounded hover:bg-red-50 text-[#999999] hover:text-red-500" title="Delete step">
                    <Trash2 className="w-3 h-3" />
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Pain / Benefit text (grey italic, no red) */}
          {stateType === 'current' && step.pain_description && (
            <p className="text-[11px] text-[#999999] mt-1.5 italic">Pain: {step.pain_description}</p>
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

          {/* Feature links (future side only) */}
          {stateType === 'future' && step.feature_names && step.feature_names.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1.5">
              {step.feature_names.map((name, i) => (
                <span
                  key={step.feature_ids?.[i] || i}
                  className="px-1.5 py-0.5 text-[10px] font-medium bg-blue-50 text-blue-700 rounded"
                >
                  {name}
                </span>
              ))}
            </div>
          )}
        </div>
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
  workflowId,
  onCreateStep,
  onEditStep,
  onDeleteStep,
  onViewStepDetail,
}: {
  steps: WorkflowStepSummary[]
  stateType: 'current' | 'future'
  workflowId?: string | null
  onCreateStep?: (stateType: 'current' | 'future') => void
  onEditStep?: (stepId: string) => void
  onDeleteStep?: (stepId: string) => void
  onViewStepDetail?: (stepId: string) => void
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
          {isCurrent ? 'Current (Manual)' : 'Future (Automated)'}
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
              onEdit={onEditStep ? () => onEditStep(step.id) : undefined}
              onDelete={onDeleteStep ? () => onDeleteStep(step.id) : undefined}
              onViewDetail={onViewStepDetail ? () => onViewStepDetail(step.id) : undefined}
            />
          ))}
        </div>
      ) : (
        <p className="text-[12px] text-[#999999] italic py-3 px-3">No steps yet</p>
      )}

      {/* Add Step button */}
      {onCreateStep && workflowId && (
        <button
          onClick={() => onCreateStep(stateType)}
          className="inline-flex items-center gap-1 px-3 py-1.5 text-[11px] font-medium text-[#666666] hover:text-[#25785A] hover:bg-[#E8F5E9] rounded-lg transition-colors mt-1"
        >
          <Plus className="w-3 h-3" />
          Add Step
        </button>
      )}
    </div>
  )
}

// ============================================================================
// Workflow Accordion Card
// ============================================================================

function WorkflowAccordionCard({
  pair,
  onConfirm,
  onNeedsReview,
  onEditWorkflow,
  onDeleteWorkflow,
  onPairWorkflow,
  onCreateStep,
  onEditStep,
  onDeleteStep,
  onRefreshEntity,
  onStatusClick,
  onViewStepDetail,
  onViewWorkflowDetail,
}: {
  pair: WorkflowPair
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
  onEditWorkflow?: (workflowId: string) => void
  onDeleteWorkflow?: (workflowId: string) => void
  onPairWorkflow?: (workflowId: string) => void
  onCreateStep?: (workflowId: string, stateType: 'current' | 'future') => void
  onEditStep?: (workflowId: string, stepId: string) => void
  onDeleteStep?: (workflowId: string, stepId: string) => void
  onRefreshEntity?: (entityType: string, entityId: string) => void
  onStatusClick?: (entityType: string, entityId: string, entityName: string, status?: string | null) => void
  onViewStepDetail?: (stepId: string) => void
  onViewWorkflowDetail?: (workflowId: string) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [hasBeenExpanded, setHasBeenExpanded] = useState(false)

  const currentMin = pair.current_steps.reduce((sum, s) => sum + (s.time_minutes || 0), 0)
  const futureMin = pair.future_steps.reduce((sum, s) => sum + (s.time_minutes || 0), 0)

  const createStepHandler = onCreateStep
    ? (stateType: 'current' | 'future') => {
        const wfId = stateType === 'current' ? pair.current_workflow_id : pair.future_workflow_id
        if (wfId) onCreateStep(wfId, stateType)
      }
    : undefined
  const editStepHandler = onEditStep
    ? (stepId: string) => onEditStep(pair.future_workflow_id || pair.current_workflow_id || pair.id, stepId)
    : undefined
  const deleteStepHandler = onDeleteStep
    ? (stepId: string) => onDeleteStep(pair.future_workflow_id || pair.current_workflow_id || pair.id, stepId)
    : undefined

  return (
    <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] overflow-hidden">
      {/* Header row — clickable */}
      <button
        onClick={() => { const next = !expanded; setExpanded(next); if (next && !hasBeenExpanded) setHasBeenExpanded(true) }}
        className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-gray-50/50 transition-colors"
      >
        <ChevronRight
          className={`w-4 h-4 text-[#999999] shrink-0 transition-transform duration-200 ${expanded ? 'rotate-90' : ''}`}
        />
        <Workflow className="w-4 h-4 text-[#3FAF7A] shrink-0" />
        <span
          className={`text-[14px] font-semibold text-[#333333] truncate ${onViewWorkflowDetail ? 'hover:text-[#25785A] hover:underline cursor-pointer' : ''}`}
          onClick={onViewWorkflowDetail ? (e) => { e.stopPropagation(); onViewWorkflowDetail(pair.id) } : undefined}
        >
          {pair.name}
        </span>
        {/* Time summaries */}
        {currentMin > 0 && (
          <span className="text-[11px] text-[#999999] shrink-0">Current: {currentMin}min</span>
        )}
        {futureMin > 0 && (
          <span className="text-[11px] text-[#999999] shrink-0">Future: {futureMin}min</span>
        )}

        {/* Staleness indicator */}
        {pair.is_stale && (
          <StaleIndicator reason={pair.stale_reason || undefined} />
        )}

        {/* Right side: status badge + ROI savings + action buttons */}
        <div className="ml-auto flex items-center gap-2 shrink-0" onClick={(e) => e.stopPropagation()}>
          <BRDStatusBadge
            status={pair.confirmation_status}
            onClick={onStatusClick ? () => onStatusClick('workflow', pair.id, pair.name, pair.confirmation_status) : undefined}
          />
          {pair.roi && pair.roi.time_saved_minutes > 0 && (
            <span className="text-[11px] font-medium text-[#25785A] bg-[#E8F5E9] px-2 py-0.5 rounded">
              {pair.roi.time_saved_minutes}min saved ({pair.roi.time_saved_percent}%)
            </span>
          )}
          {onPairWorkflow && !pair.current_workflow_id && (
            <button onClick={() => onPairWorkflow(pair.id)} className="p-1 rounded text-[#999999] hover:text-blue-600 hover:bg-blue-50" title="Pair with current-state workflow">
              <Link2 className="w-3.5 h-3.5" />
            </button>
          )}
          {onEditWorkflow && (
            <button onClick={() => onEditWorkflow(pair.id)} className="p-1 rounded text-[#999999] hover:text-[#333333] hover:bg-gray-100" title="Edit workflow">
              <Pencil className="w-3.5 h-3.5" />
            </button>
          )}
          {onDeleteWorkflow && (
            <button onClick={() => onDeleteWorkflow(pair.id)} className="p-1 rounded text-[#999999] hover:text-red-500 hover:bg-red-50" title="Delete workflow">
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </button>

      {/* Expanded body */}
      {hasBeenExpanded && (
        <div
          className={`overflow-hidden transition-all duration-200 ${expanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'}`}
        >
          <div className="px-5 pb-5 pt-1">
            {pair.description && (
              <p className="text-[12px] text-[#666666] mb-4">{pair.description}</p>
            )}

            {/* Side-by-side columns */}
            {(pair.current_steps.length > 0 || pair.future_steps.length > 0) ? (
              <div className="flex gap-6">
                {(pair.current_steps.length > 0 || pair.current_workflow_id) && (
                  <StepColumn
                    steps={pair.current_steps}
                    stateType="current"
                    workflowId={pair.current_workflow_id}
                    onCreateStep={createStepHandler}
                    onEditStep={editStepHandler}
                    onDeleteStep={deleteStepHandler}
                    onViewStepDetail={onViewStepDetail}
                  />
                )}
                <StepColumn
                  steps={pair.future_steps}
                  stateType="future"
                  workflowId={pair.future_workflow_id}
                  onCreateStep={createStepHandler}
                  onEditStep={editStepHandler}
                  onDeleteStep={deleteStepHandler}
                  onViewStepDetail={onViewStepDetail}
                />
              </div>
            ) : (
              <p className="text-[12px] text-[#999999] italic py-2">No steps added yet</p>
            )}

            {pair.roi && <ROIFooter roi={pair.roi} />}
          </div>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Main WorkflowsSection
// ============================================================================

export function WorkflowsSection({
  workflows,
  workflowPairs = [],
  roiSummary = [],
  onConfirm,
  onNeedsReview,
  onConfirmAll,
  onCreateWorkflow,
  onEditWorkflow,
  onDeleteWorkflow,
  onPairWorkflow,
  onCreateStep,
  onEditStep,
  onDeleteStep,
  onRefreshEntity,
  onStatusClick,
  onViewStepDetail,
  onViewWorkflowDetail,
  sectionScore,
}: WorkflowsSectionProps) {
  const hasWorkflowPairs = workflowPairs.length > 0

  const confirmedCount = hasWorkflowPairs
    ? workflowPairs.filter(
        (wp) => wp.confirmation_status === 'confirmed_consultant' || wp.confirmation_status === 'confirmed_client'
      ).length
    : workflows.filter(
        (w) => w.confirmation_status === 'confirmed_consultant' || w.confirmation_status === 'confirmed_client'
      ).length

  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <SectionHeader
          title="Key Workflows"
          count={hasWorkflowPairs ? workflowPairs.length : workflows.length}
          confirmedCount={confirmedCount}
          onConfirmAll={() =>
            hasWorkflowPairs
              ? onConfirmAll('workflow', workflowPairs.map((wp) => wp.id))
              : onConfirmAll('vp_step', workflows.map((w) => w.id))
          }
          sectionScore={sectionScore}
        />
        {onCreateWorkflow && (
          <button
            onClick={onCreateWorkflow}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-[#666666] bg-white border border-[#E5E5E5] rounded-xl hover:bg-[#E8F5E9] hover:text-[#25785A] hover:border-[#3FAF7A] transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            Add Workflow
          </button>
        )}
      </div>

      {/* Workflow Pairs (branded accordion cards) */}
      {hasWorkflowPairs && (
        <div className="space-y-3 mb-6">
          {workflowPairs.map((pair) => (
            <WorkflowAccordionCard
              key={pair.id}
              pair={pair}
              onConfirm={onConfirm}
              onNeedsReview={onNeedsReview}
              onEditWorkflow={onEditWorkflow}
              onDeleteWorkflow={onDeleteWorkflow}
              onPairWorkflow={onPairWorkflow}
              onCreateStep={onCreateStep}
              onEditStep={onEditStep}
              onDeleteStep={onDeleteStep}
              onRefreshEntity={onRefreshEntity}
              onStatusClick={onStatusClick}
              onViewStepDetail={onViewStepDetail}
              onViewWorkflowDetail={onViewWorkflowDetail}
            />
          ))}
        </div>
      )}

      {/* Legacy flat VP steps (shown when no workflow pairs) */}
      {!hasWorkflowPairs && (
        <>
          {workflows.length === 0 ? (
            <p className="text-[13px] text-[#999999] italic">No workflows mapped yet</p>
          ) : (
            <div className="space-y-3">
              {workflows.map((step, idx) => (
                <LegacyStepCard
                  key={step.id}
                  step={step}
                  index={idx + 1}
                  onConfirm={() => onConfirm('vp_step', step.id)}
                  onNeedsReview={() => onNeedsReview('vp_step', step.id)}
                  onRefresh={onRefreshEntity ? () => onRefreshEntity('vp_step', step.id) : undefined}
                  onStatusClick={onStatusClick ? () => onStatusClick('vp_step', step.id, step.title, step.confirmation_status) : undefined}
                />
              ))}
            </div>
          )}
        </>
      )}
    </section>
  )
}

// ============================================================================
// Legacy flat step card (branded accordion style)
// ============================================================================

function LegacyStepCard({
  step,
  index,
  onConfirm,
  onNeedsReview,
  onRefresh,
  onStatusClick,
}: {
  step: VpStepBRDSummary
  index: number
  onConfirm: () => void
  onNeedsReview: () => void
  onRefresh?: () => void
  onStatusClick?: () => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [hasBeenExpanded, setHasBeenExpanded] = useState(false)

  return (
    <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] overflow-hidden">
      <button
        onClick={() => { const next = !expanded; setExpanded(next); if (next && !hasBeenExpanded) setHasBeenExpanded(true) }}
        className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-gray-50/50 transition-colors"
      >
        <ChevronRight
          className={`w-4 h-4 text-[#999999] shrink-0 transition-transform duration-200 ${expanded ? 'rotate-90' : ''}`}
        />
        <div className="w-7 h-7 rounded-full bg-[#0A1E2F] flex items-center justify-center shrink-0">
          <span className="text-[11px] font-bold text-white">{index}</span>
        </div>
        <span className="text-[14px] font-semibold text-[#333333] truncate">{step.title}</span>
        {step.actor_persona_name && (
          <span className="px-2 py-0.5 text-[10px] font-medium bg-[#E8F5E9] text-[#25785A] rounded-full shrink-0">
            {step.actor_persona_name}
          </span>
        )}
        <span className="ml-auto shrink-0" onClick={(e) => e.stopPropagation()}>
          <BRDStatusBadge
            status={step.confirmation_status}
            onClick={onStatusClick}
          />
        </span>
        {step.is_stale && (
          <StaleIndicator reason={step.stale_reason || undefined} />
        )}
      </button>

      {hasBeenExpanded && (
        <div
          className={`overflow-hidden transition-all duration-200 ${expanded ? 'max-h-[500px] opacity-100' : 'max-h-0 opacity-0'}`}
        >
          <div className="px-5 pb-4 pt-1 space-y-3">
            {step.description && (
              <p className="text-[13px] text-[#666666] leading-relaxed">
                {step.description}
              </p>
            )}

            {step.actor_persona_name && (
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] text-[#999999]">Actor:</span>
                <span className="px-2 py-0.5 text-[11px] font-medium bg-[#E8F5E9] text-[#25785A] rounded-full">
                  {step.actor_persona_name}
                </span>
              </div>
            )}

            {step.feature_names && step.feature_names.length > 0 && (
              <div>
                <span className="text-[11px] text-[#999999] block mb-1">Features:</span>
                <div className="flex flex-wrap gap-1">
                  {step.feature_names.map((name, i) => (
                    <span
                      key={step.feature_ids?.[i] || i}
                      className="px-2 py-0.5 text-[11px] font-medium bg-blue-50 text-blue-700 rounded-full"
                    >
                      {name}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
