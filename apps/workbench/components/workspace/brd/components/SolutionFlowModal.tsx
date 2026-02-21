'use client'

import { useState, useEffect, useCallback } from 'react'
import { X, Sparkles, RefreshCw, PanelLeftClose, PanelLeftOpen } from 'lucide-react'
import { FlowStepList } from './FlowStepList'
import { FlowStepDetail } from './FlowStepDetail'
import { FlowStepChat } from './FlowStepChat'
import type {
  SolutionFlowOverview,
  SolutionFlowStepDetail as StepDetail,
  FlowOpenQuestion,
} from '@/types/workspace'
import { getSolutionFlow, getSolutionFlowStep, generateSolutionFlow } from '@/lib/api'

const PHASE_CONFIG: Record<string, { label: string; color: string }> = {
  entry: { label: 'Entry', color: 'bg-[#0A1E2F]/10 text-[#0A1E2F]' },
  core_experience: { label: 'Core', color: 'bg-[#3FAF7A]/10 text-[#25785A]' },
  output: { label: 'Output', color: 'bg-[#0D2A35]/10 text-[#0D2A35]' },
  admin: { label: 'Admin', color: 'bg-gray-100 text-[#666666]' },
}

export interface EntityLookup {
  features: Record<string, string>    // id → name
  workflows: Record<string, string>
  data_entities: Record<string, string>
}

interface SolutionFlowModalProps {
  projectId: string
  isOpen: boolean
  onClose: () => void
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
  entityLookup?: EntityLookup
}

export function SolutionFlowModal({
  projectId,
  isOpen,
  onClose,
  onConfirm,
  onNeedsReview,
  entityLookup,
}: SolutionFlowModalProps) {
  const [flow, setFlow] = useState<SolutionFlowOverview | null>(null)
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null)
  const [stepDetail, setStepDetail] = useState<StepDetail | null>(null)
  const [stepLoading, setStepLoading] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [loading, setLoading] = useState(true)
  const [sidebarOpen, setSidebarOpen] = useState(true)

  // Load flow data
  const loadFlow = useCallback(async () => {
    try {
      setLoading(true)
      const data = await getSolutionFlow(projectId)
      setFlow(data)
      // Auto-select first step
      if (data.steps?.length > 0 && !selectedStepId) {
        setSelectedStepId(data.steps[0].id)
      }
    } catch (err) {
      console.error('Failed to load solution flow:', err)
    } finally {
      setLoading(false)
    }
  }, [projectId, selectedStepId])

  useEffect(() => {
    if (isOpen) loadFlow()
  }, [isOpen, loadFlow])

  // Load step detail when selection changes
  const refreshStepDetail = useCallback(async (stepId: string) => {
    try {
      const data = await getSolutionFlowStep(projectId, stepId)
      setStepDetail(data as StepDetail)
    } catch {
      // Silent fail for background refreshes
    }
  }, [projectId])

  const refreshFlow = useCallback(async () => {
    try {
      const data = await getSolutionFlow(projectId)
      setFlow(data)
    } catch {
      // Silent fail
    }
  }, [projectId])

  useEffect(() => {
    if (!selectedStepId) {
      setStepDetail(null)
      return
    }
    let cancelled = false
    setStepLoading(true)
    getSolutionFlowStep(projectId, selectedStepId)
      .then(data => {
        if (!cancelled) {
          setStepDetail(data as StepDetail)
          setStepLoading(false)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setStepDetail(null)
          setStepLoading(false)
        }
      })
    return () => { cancelled = true }
  }, [projectId, selectedStepId])

  const handleGenerate = async () => {
    try {
      setIsGenerating(true)
      await generateSolutionFlow(projectId)
      await loadFlow()
    } catch (err) {
      console.error('Failed to generate solution flow:', err)
    } finally {
      setIsGenerating(false)
    }
  }

  // ==========================================================================
  // Cascade handler — refetch data when chat tools complete
  // ==========================================================================
  const handleToolResult = useCallback((toolName: string, result: any) => {
    if (!selectedStepId) return

    switch (toolName) {
      case 'resolve_solution_flow_question': {
        // Optimistic patch from step_data (instant), fallback to manual patch
        if (result?.step_data) {
          setStepDetail(result.step_data as StepDetail)
        } else if (stepDetail && result?.answer) {
          setStepDetail(prev => {
            if (!prev) return prev
            const updatedQuestions = (prev.open_questions || []).map(q =>
              q.question === result.question_text
                ? { ...q, status: 'resolved' as const, resolved_answer: result.answer }
                : q
            )
            return { ...prev, open_questions: updatedQuestions }
          })
        }
        refreshFlow()
        break
      }
      case 'escalate_to_client': {
        // Optimistic patch from step_data (instant), fallback to manual patch
        if (result?.step_data) {
          setStepDetail(result.step_data as StepDetail)
        } else if (stepDetail && result?.question) {
          setStepDetail(prev => {
            if (!prev) return prev
            const updatedQuestions = (prev.open_questions || []).map(q =>
              q.question === result.question
                ? { ...q, status: 'escalated' as const, escalated_to: result.escalated_to }
                : q
            )
            return { ...prev, open_questions: updatedQuestions }
          })
        }
        refreshFlow()
        break
      }
      case 'update_solution_flow_step':
      case 'refine_solution_flow_step': {
        // Optimistic patch from step_data (instant)
        if (result?.step_data) {
          setStepDetail(result.step_data as StepDetail)
        } else {
          refreshStepDetail(selectedStepId)
        }
        refreshFlow()
        break
      }
      case 'add_solution_flow_step': {
        refreshFlow().then(() => {
          // Auto-select the new step if we got a step_id back
          if (result?.step_id) {
            setSelectedStepId(result.step_id)
          }
        })
        break
      }
      case 'remove_solution_flow_step': {
        refreshFlow().then(() => {
          // If current step was deleted, select first remaining
          setFlow(prev => {
            if (!prev) return prev
            const remaining = prev.steps || []
            if (!remaining.find(s => s.id === selectedStepId) && remaining.length > 0) {
              setSelectedStepId(remaining[0].id)
            }
            return prev
          })
        })
        break
      }
      case 'reorder_solution_flow_steps': {
        refreshFlow()
        break
      }
    }
  }, [selectedStepId, stepDetail, refreshStepDetail, refreshFlow])

  if (!isOpen) return null

  const steps = flow?.steps || []
  const selectedStep = steps.find(s => s.id === selectedStepId)

  // Phase summary chips
  const phaseCountMap: Record<string, number> = {}
  for (const step of steps) {
    phaseCountMap[step.phase] = (phaseCountMap[step.phase] || 0) + 1
  }

  // Open questions from live stepDetail (not static prop)
  const openQuestions: FlowOpenQuestion[] = stepDetail
    ? (stepDetail.open_questions || []).filter(q => q.status === 'open')
    : []

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />

      {/* Modal */}
      <div className="relative w-[92vw] h-[88vh] max-w-[1600px] bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-[#E5E5E5] shrink-0">
          <div className="flex items-center gap-3">
            {/* Sidebar toggle */}
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="w-7 h-7 flex items-center justify-center rounded-md hover:bg-gray-100 transition-colors text-[#666666]"
              title={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
            >
              {sidebarOpen ? (
                <PanelLeftClose className="w-4 h-4" />
              ) : (
                <PanelLeftOpen className="w-4 h-4" />
              )}
            </button>
            <h2 className="text-base font-semibold text-[#333333]">
              {flow?.title || 'Solution Flow'}
            </h2>
            <div className="flex gap-1.5">
              {Object.entries(phaseCountMap).map(([phase, count]) => {
                const config = PHASE_CONFIG[phase] || PHASE_CONFIG.core_experience
                return (
                  <span
                    key={phase}
                    className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${config.color}`}
                  >
                    {config.label}: {count}
                  </span>
                )
              })}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {steps.length > 0 && (
              <button
                onClick={handleGenerate}
                disabled={isGenerating}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[#3FAF7A] bg-[#3FAF7A]/5 rounded-lg hover:bg-[#3FAF7A]/10 transition-colors disabled:opacity-50"
              >
                {isGenerating ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Sparkles className="w-3.5 h-3.5" />
                )}
                Regenerate
              </button>
            )}
            <button
              onClick={onClose}
              className="w-7 h-7 flex items-center justify-center rounded-md hover:bg-gray-100 transition-colors"
            >
              <X className="w-4 h-4 text-[#999999]" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 flex min-h-0">
          {loading ? (
            <div className="flex-1 flex items-center justify-center text-sm text-[#999999]">
              Loading solution flow...
            </div>
          ) : steps.length === 0 ? (
            /* No steps — generate CTA */
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center max-w-sm">
                <div className="w-14 h-14 rounded-full bg-[#3FAF7A]/10 flex items-center justify-center mx-auto mb-4">
                  <Sparkles className="w-7 h-7 text-[#3FAF7A]" />
                </div>
                <h3 className="text-base font-semibold text-[#333333] mb-2">
                  No steps yet
                </h3>
                <p className="text-sm text-[#666666] mb-5">
                  Generate a solution flow from your project data to see the goal-oriented journey.
                </p>
                <button
                  onClick={handleGenerate}
                  disabled={isGenerating}
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#3FAF7A] text-white rounded-xl text-sm font-semibold hover:bg-[#25785A] transition-colors disabled:opacity-50"
                >
                  {isGenerating ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      Generate Solution Flow
                    </>
                  )}
                </button>
              </div>
            </div>
          ) : (
            <>
              {/* Left: Step list (collapsible) */}
              <div
                className={`border-r border-[#E5E5E5] shrink-0 transition-all duration-200 overflow-hidden ${
                  sidebarOpen ? 'w-[280px]' : 'w-0'
                }`}
              >
                <div className="w-[280px] h-full">
                  <FlowStepList
                    steps={steps}
                    selectedStepId={selectedStepId}
                    onSelectStep={setSelectedStepId}
                  />
                </div>
              </div>

              {/* Center: Detail */}
              <div className="flex-1 min-w-0 overflow-hidden">
                {selectedStep ? (
                  <FlowStepDetail
                    step={stepDetail}
                    loading={stepLoading}
                    onConfirm={onConfirm}
                    onNeedsReview={onNeedsReview}
                    entityLookup={entityLookup}
                    projectId={projectId}
                  />
                ) : (
                  <div className="flex-1 flex items-center justify-center h-full text-sm text-[#999999]">
                    Select a step to view details
                  </div>
                )}
              </div>

              {/* Right: Chat */}
              {selectedStep && (
                <div className="w-[340px] shrink-0 border-l border-[#E5E5E5]">
                  <FlowStepChat
                    projectId={projectId}
                    stepId={selectedStep.id}
                    stepTitle={selectedStep.title}
                    stepGoal={stepDetail?.goal || selectedStep.goal}
                    openQuestions={openQuestions}
                    onToolResult={handleToolResult}
                  />
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
