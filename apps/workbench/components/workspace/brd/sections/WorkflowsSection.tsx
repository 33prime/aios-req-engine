'use client'

import { useState } from 'react'
import { Workflow, Clock, Plus, Pencil, Link2, Trash2 } from 'lucide-react'
import { SectionHeader } from '../components/SectionHeader'
import { CollapsibleCard } from '../components/CollapsibleCard'
import type {
  VpStepBRDSummary,
  WorkflowPair,
  WorkflowStepSummary,
  ROISummary,
  AutomationLevel,
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
}

// ============================================================================
// Automation Level Badge
// ============================================================================

function AutomationBadge({ level }: { level: AutomationLevel }) {
  const config: Record<AutomationLevel, { dot: string; label: string; bg: string; text: string }> = {
    manual: { dot: 'bg-red-400', label: 'Manual', bg: 'bg-red-50', text: 'text-red-700' },
    semi_automated: { dot: 'bg-yellow-400', label: 'Semi-auto', bg: 'bg-yellow-50', text: 'text-yellow-700' },
    fully_automated: { dot: 'bg-green-400', label: 'Automated', bg: 'bg-green-50', text: 'text-green-700' },
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
    <div className="mt-3 pt-3 border-t border-gray-200 space-y-2">
      {/* Progress bar */}
      <div className="flex items-center gap-2">
        <span className="text-[11px] text-gray-500 w-16 shrink-0">Time saved</span>
        <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-teal-500 rounded-full transition-all"
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="text-[11px] font-medium text-[#37352f] w-10 text-right">
          {roi.time_saved_percent}%
        </span>
      </div>
      {/* Stats row */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-gray-500">
        <span>
          {roi.current_total_minutes}min → {roi.future_total_minutes}min
        </span>
        <span className="font-medium text-teal-700">
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
// Single Step Row
// ============================================================================

function WorkflowStepRow({
  step,
  stateType,
  onEdit,
  onDelete,
}: {
  step: WorkflowStepSummary
  stateType: 'current' | 'future'
  onEdit?: () => void
  onDelete?: () => void
}) {
  return (
    <div className="group/step py-2 px-3 rounded hover:bg-gray-50/60 transition-colors">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-[12px] font-medium text-gray-400 w-4">{step.step_index}.</span>
            <span className="text-[13px] font-medium text-[#37352f] truncate">{step.label}</span>
            <AutomationBadge level={step.automation_level} />
          </div>
          {step.description && (
            <p className="text-[12px] text-gray-500 mt-0.5 ml-5 line-clamp-2">{step.description}</p>
          )}
        </div>
        {/* Time + actions */}
        <div className="flex items-center gap-1 shrink-0">
          {step.time_minutes != null && (
            <span className="inline-flex items-center gap-0.5 text-[11px] text-gray-400">
              <Clock className="w-3 h-3" />
              {step.time_minutes}m
            </span>
          )}
          {(onEdit || onDelete) && (
            <div className="flex items-center gap-0.5 opacity-0 group-hover/step:opacity-100 transition-opacity">
              {onEdit && (
                <button onClick={onEdit} className="p-1 rounded hover:bg-gray-200 text-gray-400 hover:text-gray-600" title="Edit step">
                  <Pencil className="w-3 h-3" />
                </button>
              )}
              {onDelete && (
                <button onClick={onDelete} className="p-1 rounded hover:bg-red-50 text-gray-400 hover:text-red-500" title="Delete step">
                  <Trash2 className="w-3 h-3" />
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Pain / Benefit text */}
      {stateType === 'current' && step.pain_description && (
        <p className="text-[11px] text-red-600/70 mt-1 ml-5 italic">Pain: {step.pain_description}</p>
      )}
      {stateType === 'future' && step.benefit_description && (
        <p className="text-[11px] text-teal-600/70 mt-1 ml-5 italic">Benefit: {step.benefit_description}</p>
      )}

      {/* Feature links (future side only) */}
      {stateType === 'future' && step.feature_names && step.feature_names.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1 ml-5">
          {step.feature_names.map((name, i) => (
            <span
              key={step.feature_ids?.[i] || i}
              className="px-1.5 py-0.5 text-[10px] font-medium bg-teal-50 text-teal-700 rounded"
            >
              {name}
            </span>
          ))}
        </div>
      )}

      {/* Actor */}
      {step.actor_persona_name && (
        <div className="mt-1 ml-5">
          <span className="px-1.5 py-0.5 text-[10px] font-medium bg-indigo-50 text-indigo-700 rounded">
            {step.actor_persona_name}
          </span>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Workflow Pair Card (Side-by-Side)
// ============================================================================

function WorkflowPairCard({
  pair,
  onEdit,
  onDelete,
  onPair,
  onCreateStep,
  onEditStep,
  onDeleteStep,
}: {
  pair: WorkflowPair
  onEdit?: () => void
  onDelete?: () => void
  onPair?: () => void
  onCreateStep?: (stateType: 'current' | 'future') => void
  onEditStep?: (stepId: string) => void
  onDeleteStep?: (stepId: string) => void
}) {
  const [expanded, setExpanded] = useState(true)
  const hasBothSides = pair.current_steps.length > 0 && pair.future_steps.length > 0
  const currentWfId = pair.current_workflow_id
  const futureWfId = pair.future_workflow_id

  return (
    <div className="border border-[#e9e9e7] rounded-lg shadow-sm bg-white overflow-hidden">
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 bg-gray-50/60 border-b border-[#e9e9e7] cursor-pointer hover:bg-gray-100/60 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2 min-w-0">
          <Workflow className="w-4 h-4 text-blue-500 shrink-0" />
          <span className="text-[14px] font-semibold text-[#37352f] truncate">{pair.name}</span>
          {pair.owner && (
            <span className="text-[11px] text-gray-400">
              Owner: {pair.owner}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1.5 shrink-0" onClick={(e) => e.stopPropagation()}>
          {pair.roi && (
            <span className="text-[11px] font-medium text-teal-700 bg-teal-50 px-2 py-0.5 rounded">
              {pair.roi.time_saved_minutes}min saved ({pair.roi.time_saved_percent}%)
            </span>
          )}
          {onPair && !pair.current_workflow_id && (
            <button onClick={onPair} className="p-1 rounded text-gray-400 hover:text-blue-600 hover:bg-blue-50" title="Pair with current-state workflow">
              <Link2 className="w-3.5 h-3.5" />
            </button>
          )}
          {onEdit && (
            <button onClick={onEdit} className="p-1 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-200" title="Edit workflow">
              <Pencil className="w-3.5 h-3.5" />
            </button>
          )}
          {onDelete && (
            <button onClick={onDelete} className="p-1 rounded text-gray-400 hover:text-red-500 hover:bg-red-50" title="Delete workflow">
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {expanded && (
        <div className="p-4">
          {pair.description && (
            <p className="text-[12px] text-gray-500 mb-3">{pair.description}</p>
          )}

          {/* Side-by-side columns */}
          {hasBothSides ? (
            <div className="grid grid-cols-2 gap-4">
              {/* Current state */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-[12px] font-semibold text-red-700 uppercase tracking-wide">
                    Current State
                  </h4>
                  {onCreateStep && currentWfId && (
                    <button
                      onClick={() => onCreateStep('current')}
                      className="p-0.5 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100"
                      title="Add current step"
                    >
                      <Plus className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
                <p className="text-[11px] text-gray-400 mb-2">How it works today</p>
                <div className="space-y-0.5 border-l-2 border-red-200 pl-1">
                  {pair.current_steps.map((step) => (
                    <WorkflowStepRow
                      key={step.id}
                      step={step}
                      stateType="current"
                      onEdit={onEditStep ? () => onEditStep(step.id) : undefined}
                      onDelete={onDeleteStep ? () => onDeleteStep(step.id) : undefined}
                    />
                  ))}
                </div>
              </div>

              {/* Future state */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-[12px] font-semibold text-teal-700 uppercase tracking-wide">
                    Future State
                  </h4>
                  {onCreateStep && futureWfId && (
                    <button
                      onClick={() => onCreateStep('future')}
                      className="p-0.5 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100"
                      title="Add future step"
                    >
                      <Plus className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
                <p className="text-[11px] text-gray-400 mb-2">How the system improves it</p>
                <div className="space-y-0.5 border-l-2 border-teal-200 pl-1">
                  {pair.future_steps.map((step) => (
                    <WorkflowStepRow
                      key={step.id}
                      step={step}
                      stateType="future"
                      onEdit={onEditStep ? () => onEditStep(step.id) : undefined}
                      onDelete={onDeleteStep ? () => onDeleteStep(step.id) : undefined}
                    />
                  ))}
                </div>
              </div>
            </div>
          ) : (
            /* Single-side view (only current or only future) */
            <div>
              {pair.future_steps.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-[12px] font-semibold text-teal-700 uppercase tracking-wide">
                      Future State
                    </h4>
                    {onCreateStep && futureWfId && (
                      <button
                        onClick={() => onCreateStep('future')}
                        className="p-0.5 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100"
                      >
                        <Plus className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                  <div className="space-y-0.5 border-l-2 border-teal-200 pl-1">
                    {pair.future_steps.map((step) => (
                      <WorkflowStepRow
                        key={step.id}
                        step={step}
                        stateType="future"
                        onEdit={onEditStep ? () => onEditStep(step.id) : undefined}
                        onDelete={onDeleteStep ? () => onDeleteStep(step.id) : undefined}
                      />
                    ))}
                  </div>
                </div>
              )}
              {pair.current_steps.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-[12px] font-semibold text-red-700 uppercase tracking-wide">
                      Current State
                    </h4>
                    {onCreateStep && currentWfId && (
                      <button
                        onClick={() => onCreateStep('current')}
                        className="p-0.5 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100"
                      >
                        <Plus className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                  <div className="space-y-0.5 border-l-2 border-red-200 pl-1">
                    {pair.current_steps.map((step) => (
                      <WorkflowStepRow
                        key={step.id}
                        step={step}
                        stateType="current"
                        onEdit={onEditStep ? () => onEditStep(step.id) : undefined}
                        onDelete={onDeleteStep ? () => onDeleteStep(step.id) : undefined}
                      />
                    ))}
                  </div>
                </div>
              )}
              {pair.current_steps.length === 0 && pair.future_steps.length === 0 && (
                <p className="text-[12px] text-gray-400 italic py-2">No steps added yet</p>
              )}
            </div>
          )}

          {/* ROI Footer */}
          {pair.roi && <ROIFooter roi={pair.roi} />}
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
}: WorkflowsSectionProps) {
  const confirmedCount = workflows.filter(
    (w) => w.confirmation_status === 'confirmed_consultant' || w.confirmation_status === 'confirmed_client'
  ).length

  const hasWorkflowPairs = workflowPairs.length > 0

  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <SectionHeader
          title="Key Workflows"
          count={hasWorkflowPairs ? workflowPairs.length : workflows.length}
          confirmedCount={confirmedCount}
          onConfirmAll={() => onConfirmAll('vp_step', workflows.map((w) => w.id))}
        />
        {onCreateWorkflow && (
          <button
            onClick={onCreateWorkflow}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-gray-600 bg-white border border-gray-200 rounded-md hover:bg-blue-50 hover:text-blue-700 hover:border-blue-200 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            Add Workflow
          </button>
        )}
      </div>

      {/* Workflow Pairs (side-by-side current/future view) */}
      {hasWorkflowPairs && (
        <div className="space-y-4 mb-6">
          {workflowPairs.map((pair) => (
            <WorkflowPairCard
              key={pair.id}
              pair={pair}
              onEdit={onEditWorkflow ? () => onEditWorkflow(pair.id) : undefined}
              onDelete={onDeleteWorkflow ? () => onDeleteWorkflow(pair.id) : undefined}
              onPair={onPairWorkflow ? () => onPairWorkflow(pair.id) : undefined}
              onCreateStep={
                onCreateStep
                  ? (stateType) => {
                      const wfId = stateType === 'current' ? pair.current_workflow_id : pair.future_workflow_id
                      if (wfId) onCreateStep(wfId, stateType)
                    }
                  : undefined
              }
              onEditStep={
                onEditStep
                  ? (stepId) => onEditStep(pair.future_workflow_id || pair.current_workflow_id || pair.id, stepId)
                  : undefined
              }
              onDeleteStep={
                onDeleteStep
                  ? (stepId) => onDeleteStep(pair.future_workflow_id || pair.current_workflow_id || pair.id, stepId)
                  : undefined
              }
            />
          ))}
        </div>
      )}

      {/* Legacy flat VP steps (shown when no workflow pairs, or alongside them for unmapped steps) */}
      {!hasWorkflowPairs && (
        <>
          {workflows.length === 0 ? (
            <p className="text-[13px] text-[rgba(55,53,47,0.45)] italic">No workflows mapped yet</p>
          ) : (
            <div className="space-y-2">
              {workflows.map((step, idx) => (
                <CollapsibleCard
                  key={step.id}
                  title={`${idx + 1}. ${step.title}`}
                  subtitle={step.actor_persona_name ? `Actor: ${step.actor_persona_name}` : undefined}
                  icon={<Workflow className="w-4 h-4 text-blue-400" />}
                  status={step.confirmation_status}
                  isStale={step.is_stale}
                  staleReason={step.stale_reason}
                  onRefresh={onRefreshEntity ? () => onRefreshEntity('vp_step', step.id) : undefined}
                  onConfirm={() => onConfirm('vp_step', step.id)}
                  onNeedsReview={() => onNeedsReview('vp_step', step.id)}
                >
                  <div className="space-y-3">
                    {step.description && (
                      <p className="text-[13px] text-[rgba(55,53,47,0.65)] leading-relaxed">
                        {step.description}
                      </p>
                    )}

                    {/* Actor persona chip */}
                    {step.actor_persona_name && (
                      <div className="flex items-center gap-1.5">
                        <span className="text-[11px] text-gray-400">Actor:</span>
                        <span className="px-2 py-0.5 text-[11px] font-medium bg-indigo-50 text-indigo-700 rounded-full">
                          {step.actor_persona_name}
                        </span>
                      </div>
                    )}

                    {/* Feature links */}
                    {step.feature_names && step.feature_names.length > 0 && (
                      <div>
                        <span className="text-[11px] text-gray-400 block mb-1">Features:</span>
                        <div className="flex flex-wrap gap-1">
                          {step.feature_names.map((name, i) => (
                            <span
                              key={step.feature_ids?.[i] || i}
                              className="px-2 py-0.5 text-[11px] font-medium bg-teal-50 text-teal-700 rounded-full"
                            >
                              {name}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </CollapsibleCard>
              ))}
            </div>
          )}
        </>
      )}
    </section>
  )
}
