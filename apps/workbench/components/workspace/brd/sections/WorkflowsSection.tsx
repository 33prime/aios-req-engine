'use client'

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
// Workflow State Column (reusable for current/future side)
// ============================================================================

const stateConfig = {
  current: {
    label: 'Current State',
    subtitle: 'How it works today',
    headerColor: 'text-red-700',
    borderColor: 'border-red-200',
  },
  future: {
    label: 'Future State',
    subtitle: 'How the system improves it',
    headerColor: 'text-teal-700',
    borderColor: 'border-teal-200',
  },
} as const

function WorkflowStateColumn({
  steps,
  stateType,
  workflowId,
  onCreateStep,
  onEditStep,
  onDeleteStep,
}: {
  steps: WorkflowStepSummary[]
  stateType: 'current' | 'future'
  workflowId?: string | null
  onCreateStep?: (stateType: 'current' | 'future') => void
  onEditStep?: (stepId: string) => void
  onDeleteStep?: (stepId: string) => void
}) {
  const cfg = stateConfig[stateType]
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h4 className={`text-[12px] font-semibold ${cfg.headerColor} uppercase tracking-wide`}>
          {cfg.label}
        </h4>
        {onCreateStep && workflowId && (
          <button
            onClick={() => onCreateStep(stateType)}
            className="p-0.5 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100"
            title={`Add ${stateType} step`}
          >
            <Plus className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
      <p className="text-[11px] text-gray-400 mb-2">{cfg.subtitle}</p>
      <div className={`space-y-0.5 border-l-2 ${cfg.borderColor} pl-1`}>
        {steps.map((step) => (
          <WorkflowStepRow
            key={step.id}
            step={step}
            stateType={stateType}
            onEdit={onEditStep ? () => onEditStep(step.id) : undefined}
            onDelete={onDeleteStep ? () => onDeleteStep(step.id) : undefined}
          />
        ))}
      </div>
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

      {/* Workflow Pairs (accordion cards with side-by-side current/future) */}
      {hasWorkflowPairs && (
        <div className="space-y-2 mb-6">
          {workflowPairs.map((pair) => {
            const stepCount = pair.current_steps.length + pair.future_steps.length
            const subtitleParts: string[] = []
            if (pair.owner) subtitleParts.push(`Owner: ${pair.owner}`)
            subtitleParts.push(`${stepCount} step${stepCount !== 1 ? 's' : ''}`)

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

            const hasBothSides = pair.current_steps.length > 0 && pair.future_steps.length > 0

            return (
              <CollapsibleCard
                key={pair.id}
                title={pair.name}
                subtitle={subtitleParts.join(' \u00b7 ')}
                icon={<Workflow className="w-4 h-4 text-blue-400" />}
                status={pair.confirmation_status}
                isStale={pair.is_stale}
                staleReason={pair.stale_reason}
                onRefresh={onRefreshEntity ? () => onRefreshEntity('workflow', pair.id) : undefined}
                defaultExpanded={false}
                onConfirm={() => onConfirm('workflow', pair.id)}
                onNeedsReview={() => onNeedsReview('workflow', pair.id)}
                actions={
                  <div className="flex items-center gap-1.5">
                    {pair.roi && (
                      <span className="text-[11px] font-medium text-teal-700 bg-teal-50 px-2 py-0.5 rounded">
                        {pair.roi.time_saved_minutes}min saved ({pair.roi.time_saved_percent}%)
                      </span>
                    )}
                    {onPairWorkflow && !pair.current_workflow_id && (
                      <button onClick={() => onPairWorkflow(pair.id)} className="p-1 rounded text-gray-400 hover:text-blue-600 hover:bg-blue-50" title="Pair with current-state workflow">
                        <Link2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                    {onEditWorkflow && (
                      <button onClick={() => onEditWorkflow(pair.id)} className="p-1 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-200" title="Edit workflow">
                        <Pencil className="w-3.5 h-3.5" />
                      </button>
                    )}
                    {onDeleteWorkflow && (
                      <button onClick={() => onDeleteWorkflow(pair.id)} className="p-1 rounded text-gray-400 hover:text-red-500 hover:bg-red-50" title="Delete workflow">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                }
              >
                <div className="space-y-3">
                  {pair.description && (
                    <p className="text-[12px] text-gray-500">{pair.description}</p>
                  )}

                  {hasBothSides ? (
                    <div className="grid grid-cols-2 gap-4">
                      <WorkflowStateColumn
                        steps={pair.current_steps}
                        stateType="current"
                        workflowId={pair.current_workflow_id}
                        onCreateStep={createStepHandler}
                        onEditStep={editStepHandler}
                        onDeleteStep={deleteStepHandler}
                      />
                      <WorkflowStateColumn
                        steps={pair.future_steps}
                        stateType="future"
                        workflowId={pair.future_workflow_id}
                        onCreateStep={createStepHandler}
                        onEditStep={editStepHandler}
                        onDeleteStep={deleteStepHandler}
                      />
                    </div>
                  ) : (
                    <div>
                      {pair.future_steps.length > 0 && (
                        <WorkflowStateColumn
                          steps={pair.future_steps}
                          stateType="future"
                          workflowId={pair.future_workflow_id}
                          onCreateStep={createStepHandler}
                          onEditStep={editStepHandler}
                          onDeleteStep={deleteStepHandler}
                        />
                      )}
                      {pair.current_steps.length > 0 && (
                        <WorkflowStateColumn
                          steps={pair.current_steps}
                          stateType="current"
                          workflowId={pair.current_workflow_id}
                          onCreateStep={createStepHandler}
                          onEditStep={editStepHandler}
                          onDeleteStep={deleteStepHandler}
                        />
                      )}
                      {pair.current_steps.length === 0 && pair.future_steps.length === 0 && (
                        <p className="text-[12px] text-gray-400 italic py-2">No steps added yet</p>
                      )}
                    </div>
                  )}

                  {pair.roi && <ROIFooter roi={pair.roi} />}
                </div>
              </CollapsibleCard>
            )
          })}
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
