/**
 * TaskDetailModal Component
 *
 * Modal for viewing task details with type-specific content:
 * - Proposal tasks: Show ProposalPreview with apply/discard
 * - Enrichment tasks: Show entity details with enrichment suggestions
 * - Gap tasks: Show gap analysis with suggested actions
 */

'use client'

import { useState, useEffect } from 'react'
import { X, CheckCircle, XCircle, ExternalLink, Loader2, AlertCircle, Sparkles, FileText, Target, Search, MessageSquare, User, Clock, ArrowUpCircle, ArrowRightCircle, ArrowDownCircle } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { ProposalPreview } from '@/app/projects/[projectId]/components/ProposalPreview'
import type { Task } from '@/lib/api'

interface TaskDetailModalProps {
  task: Task
  projectId: string
  isOpen: boolean
  onClose: () => void
  onComplete: (taskId: string) => Promise<void>
  onDismiss: (taskId: string) => Promise<void>
}

// Task type configuration for badges
const taskTypeConfig: Record<string, { icon: typeof CheckCircle; label: string; color: string; bgColor: string }> = {
  proposal: { icon: FileText, label: 'Proposal', color: 'text-emerald-700', bgColor: 'bg-emerald-50' },
  gap: { icon: AlertCircle, label: 'Gap Analysis', color: 'text-emerald-800', bgColor: 'bg-emerald-100' },
  manual: { icon: CheckCircle, label: 'Manual Task', color: 'text-gray-700', bgColor: 'bg-gray-100' },
  enrichment: { icon: Sparkles, label: 'Enrichment', color: 'text-teal-700', bgColor: 'bg-teal-50' },
  validation: { icon: Target, label: 'Validation', color: 'text-emerald-700', bgColor: 'bg-emerald-100' },
  research: { icon: Search, label: 'Research', color: 'text-emerald-600', bgColor: 'bg-emerald-50' },
  collaboration: { icon: MessageSquare, label: 'Client Collaboration', color: 'text-teal-700', bgColor: 'bg-teal-100' },
}

// Priority level configuration
const priorityConfig = {
  high: {
    label: 'High Priority',
    color: 'text-emerald-800',
    bgColor: 'bg-emerald-50',
    borderColor: 'border-emerald-200',
    icon: ArrowUpCircle,
  },
  medium: {
    label: 'Medium Priority',
    color: 'text-emerald-700',
    bgColor: 'bg-emerald-50',
    borderColor: 'border-emerald-100',
    icon: ArrowRightCircle,
  },
  low: {
    label: 'Low Priority',
    color: 'text-gray-600',
    bgColor: 'bg-gray-50',
    borderColor: 'border-gray-200',
    icon: ArrowDownCircle,
  },
}

function getPriorityLevel(score: number): 'high' | 'medium' | 'low' {
  if (score >= 70) return 'high'
  if (score >= 40) return 'medium'
  return 'low'
}

interface ProposalData {
  proposal_id: string
  title: string
  description?: string
  status: 'pending' | 'previewed' | 'applied' | 'discarded'
  creates: number
  updates: number
  deletes: number
  total_changes: number
  changes_by_type?: Record<string, any[]>
}

export function TaskDetailModal({
  task,
  projectId,
  isOpen,
  onClose,
  onComplete,
  onDismiss,
}: TaskDetailModalProps) {
  const [proposalData, setProposalData] = useState<ProposalData | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isApplying, setIsApplying] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch proposal details if this is a proposal task
  useEffect(() => {
    if (!isOpen) return
    if (task.task_type !== 'proposal' || !task.source_id) return

    const fetchProposal = async () => {
      setIsLoading(true)
      setError(null)

      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/v1'
        const response = await fetch(
          `${apiUrl}/proposals/${task.source_id}`,
          {
            headers: {
              'X-API-Key': process.env.NEXT_PUBLIC_API_KEY || '',
            },
          }
        )

        if (!response.ok) {
          throw new Error('Failed to fetch proposal details')
        }

        const data = await response.json()
        const groupedChanges = groupChangesByType(data.changes || [])

        setProposalData({
          proposal_id: data.id,
          title: data.title,
          description: data.description,
          status: data.status,
          creates: data.changes?.filter((c: any) => c.operation === 'create').length || 0,
          updates: data.changes?.filter((c: any) => c.operation === 'update').length || 0,
          deletes: data.changes?.filter((c: any) => c.operation === 'delete').length || 0,
          total_changes: data.changes?.length || 0,
          changes_by_type: groupedChanges,
        })
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load proposal')
      } finally {
        setIsLoading(false)
      }
    }

    fetchProposal()
  }, [isOpen, task.task_type, task.source_id])

  const handleApplyProposal = async (proposalId: string) => {
    setIsApplying(true)
    setError(null)

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/v1'
      const response = await fetch(`${apiUrl}/proposals/${proposalId}/apply`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': process.env.NEXT_PUBLIC_API_KEY || '',
        },
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to apply proposal')
      }

      // Mark task as complete after successful apply
      await onComplete(task.id)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to apply proposal')
    } finally {
      setIsApplying(false)
    }
  }

  const handleDiscardProposal = async (proposalId: string) => {
    setIsApplying(true)
    setError(null)

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/v1'
      const response = await fetch(`${apiUrl}/proposals/${proposalId}/discard`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': process.env.NEXT_PUBLIC_API_KEY || '',
        },
      })

      if (!response.ok) {
        throw new Error('Failed to discard proposal')
      }

      // Dismiss the task after discarding
      await onDismiss(task.id)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to discard proposal')
    } finally {
      setIsApplying(false)
    }
  }

  if (!isOpen) return null

  const typeConfig = taskTypeConfig[task.task_type] || taskTypeConfig.manual
  const TypeIcon = typeConfig.icon
  const priorityLevel = getPriorityLevel(task.priority_score)
  const priority = priorityConfig[priorityLevel]
  const PriorityIcon = priority.icon

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative min-h-screen flex items-center justify-center p-4">
        <div className="relative bg-white rounded-xl shadow-xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col">
          {/* Header with gradient */}
          <div className="bg-gradient-to-r from-[#044159]/5 to-[#044159]/10 px-6 py-5 border-b border-gray-200">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                {/* Type and priority badges */}
                <div className="flex items-center gap-2 mb-3">
                  <span className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full ${typeConfig.bgColor} ${typeConfig.color}`}>
                    <TypeIcon className="w-3.5 h-3.5" />
                    {typeConfig.label}
                  </span>
                  <span className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full ${priority.bgColor} ${priority.color} border ${priority.borderColor}`}>
                    <PriorityIcon className="w-3.5 h-3.5" />
                    {priority.label}
                  </span>
                  {task.requires_client_input && (
                    <span className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full bg-teal-100 text-teal-700">
                      <User className="w-3.5 h-3.5" />
                      Client Input Required
                    </span>
                  )}
                </div>

                {/* Title */}
                <h2 className="text-xl font-semibold text-gray-900">{task.title}</h2>

                {/* Meta row */}
                <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                  <span className="flex items-center gap-1.5">
                    <Clock className="w-4 h-4" />
                    Created {new Date(task.created_at).toLocaleDateString()}
                  </span>
                  {task.gate_stage && (
                    <span className="capitalize">
                      Gate: {task.gate_stage.replace(/_/g, ' ')}
                    </span>
                  )}
                  {task.source_type && task.source_type !== 'manual' && (
                    <span className="capitalize">
                      Source: {task.source_type.replace(/_/g, ' ')}
                    </span>
                  )}
                </div>
              </div>

              <button
                onClick={onClose}
                className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex items-start gap-2">
                <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 text-[#044159] animate-spin" />
                <span className="ml-3 text-gray-600">Loading details...</span>
              </div>
            ) : task.task_type === 'proposal' && proposalData ? (
              <ProposalPreview
                proposal={proposalData}
                onApply={handleApplyProposal}
                onDiscard={handleDiscardProposal}
                isApplying={isApplying}
              />
            ) : (
              <div className="space-y-6">
                {/* Task description */}
                {task.description && (
                  <div className="bg-gray-50 rounded-lg p-4 border border-gray-100">
                    <h3 className="text-sm font-medium text-gray-700 mb-2">Description</h3>
                    <p className="text-gray-600 leading-relaxed">{task.description}</p>
                  </div>
                )}

                {/* Anchored entity link */}
                {task.anchored_entity_type && task.anchored_entity_id && (
                  <div className="bg-[#044159]/5 rounded-lg p-4 border border-[#044159]/10">
                    <h3 className="text-sm font-medium text-gray-700 mb-2">Related Entity</h3>
                    <a
                      href={`/projects/${projectId}?tab=${task.anchored_entity_type}s&id=${task.anchored_entity_id}`}
                      className="inline-flex items-center gap-2 text-[#044159] hover:text-[#033344] font-medium transition-colors"
                    >
                      <ExternalLink className="w-4 h-4" />
                      View {task.anchored_entity_type}
                    </a>
                  </div>
                )}

                {/* Actions for non-proposal tasks */}
                {task.task_type !== 'proposal' && (
                  <div className="flex gap-3 pt-2">
                    <Button
                      variant="primary"
                      onClick={() => onComplete(task.id).then(onClose)}
                      icon={<CheckCircle className="w-4 h-4" />}
                      className="flex-1"
                    >
                      Mark Complete
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => onDismiss(task.id).then(onClose)}
                      icon={<XCircle className="w-4 h-4" />}
                    >
                      Dismiss
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// Helper to group changes by entity type
function groupChangesByType(changes: any[]): Record<string, any[]> {
  if (!changes || !Array.isArray(changes)) {
    return {}
  }

  const grouped: Record<string, any[]> = {}

  for (const change of changes) {
    // Handle both 'entity_type' and 'type' field names
    const type = change.entity_type || change.type || 'unknown'
    if (!grouped[type]) {
      grouped[type] = []
    }
    // Normalize the change object to ensure it has required fields
    grouped[type].push({
      ...change,
      entity_type: type,
      evidence: change.evidence || [],
      rationale: change.rationale || '',
    })
  }

  return grouped
}
