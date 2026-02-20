/**
 * TaskDetailModal — Centered modal overlay
 *
 * Shows task details with type-specific content:
 * - Proposal tasks: ProposalPreview with apply/discard
 * - All others: description, related entity, priority, actions
 */

'use client'

import { useState, useEffect } from 'react'
import { formatDistanceToNow } from 'date-fns'
import {
  X,
  CheckCircle,
  XCircle,
  ExternalLink,
  Loader2,
  AlertCircle,
  Sparkles,
  FileText,
  Target,
  Search,
  MessageSquare,
  User,
  Clock,
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { API_V1 } from '@/lib/config'
import { ProposalPreview } from '@/app/projects/[projectId]/components/ProposalPreview'
import type { Task } from '@/lib/api'

// =============================================================================
// Types & Config
// =============================================================================

interface TaskDetailModalProps {
  task: Task
  projectId: string
  isOpen: boolean
  onClose: () => void
  onComplete: (taskId: string) => Promise<void>
  onDismiss: (taskId: string) => Promise<void>
}

const TASK_TYPE_CONFIG: Record<string, { icon: typeof CheckCircle; label: string }> = {
  proposal:      { icon: FileText,      label: 'Proposal' },
  gap:           { icon: AlertCircle,   label: 'Gap Analysis' },
  manual:        { icon: CheckCircle,   label: 'Manual Task' },
  enrichment:    { icon: Sparkles,      label: 'Enrichment' },
  validation:    { icon: Target,        label: 'Validation' },
  research:      { icon: Search,        label: 'Research' },
  collaboration: { icon: MessageSquare, label: 'Client Collaboration' },
}

function getPriorityMeta(score: number) {
  if (score >= 70) return { label: 'High', color: '#25785A' }
  if (score >= 40) return { label: 'Medium', color: '#3FAF7A' }
  return { label: 'Low', color: '#E5E5E5' }
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

// =============================================================================
// Component
// =============================================================================

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

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [isOpen, onClose])

  // Fetch proposal details if this is a proposal task
  useEffect(() => {
    if (!isOpen) return
    if (task.task_type !== 'proposal' || !task.source_id) return

    const fetchProposal = async () => {
      setIsLoading(true)
      setError(null)
      try {
        const response = await fetch(`${API_V1}/proposals/${task.source_id}`, {
          headers: { 'X-API-Key': process.env.NEXT_PUBLIC_API_KEY || '' },
        })
        if (!response.ok) throw new Error('Failed to fetch proposal details')
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
      const response = await fetch(`${API_V1}/proposals/${proposalId}/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': process.env.NEXT_PUBLIC_API_KEY || '' },
      })
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to apply proposal')
      }
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
      const response = await fetch(`${API_V1}/proposals/${proposalId}/discard`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': process.env.NEXT_PUBLIC_API_KEY || '' },
      })
      if (!response.ok) throw new Error('Failed to discard proposal')
      await onDismiss(task.id)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to discard proposal')
    } finally {
      setIsApplying(false)
    }
  }

  if (!isOpen) return null

  const typeConf = TASK_TYPE_CONFIG[task.task_type] || TASK_TYPE_CONFIG.manual
  const TypeIcon = typeConf.icon
  const priorityMeta = getPriorityMeta(task.priority_score)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <style>{`@keyframes modalIn { from { opacity: 0; transform: scale(0.97); } to { opacity: 1; transform: scale(1); } }`}</style>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/30 transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div
        className="relative bg-white rounded-2xl shadow-xl flex flex-col w-full max-w-[560px] max-h-[85vh]"
        style={{ animation: 'modalIn 200ms ease-out' }}
      >
        {/* Header */}
        <div className="flex-shrink-0 border-b border-[#E5E5E5] px-6 py-5">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              {/* Pills */}
              <div className="flex items-center gap-2 mb-3">
                <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-[#E8F5E9] text-[#25785A]">
                  <TypeIcon className="w-3 h-3" />
                  {typeConf.label}
                </span>
                <span
                  className="inline-flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-0.5 rounded-full"
                  style={{
                    background: priorityMeta.color === '#E5E5E5' ? '#F0F0F0' : `${priorityMeta.color}18`,
                    color: priorityMeta.color === '#E5E5E5' ? '#666' : priorityMeta.color,
                  }}
                >
                  {priorityMeta.label} Priority
                </span>
                {task.requires_client_input && (
                  <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-[#E8F5E9] text-[#25785A]">
                    <User className="w-3 h-3" />
                    Client Input
                  </span>
                )}
              </div>

              {/* Title */}
              <h2 className="text-[18px] font-bold text-[#1D1D1F] leading-snug">
                {task.title}
              </h2>

              {/* Meta */}
              <div className="flex items-center gap-3 mt-2 text-[12px] text-[#999]">
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  {formatDistanceToNow(new Date(task.created_at), { addSuffix: true })}
                </span>
                {task.gate_stage && (
                  <span className="capitalize">{task.gate_stage.replace(/_/g, ' ')}</span>
                )}
                {task.source_type && task.source_type !== 'manual' && (
                  <span className="capitalize">{task.source_type.replace(/_/g, ' ')}</span>
                )}
              </div>

              {/* Priority bar */}
              <div className="flex items-center gap-2 mt-3">
                <div className="flex-1 h-1.5 bg-[#F0F0F0] rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${Math.min(task.priority_score, 100)}%`,
                      background: priorityMeta.color,
                    }}
                  />
                </div>
                <span className="text-[11px] font-medium text-[#666]">{task.priority_score}</span>
              </div>
            </div>

            <button
              onClick={onClose}
              className="p-2 text-[#999] hover:text-[#333] hover:bg-[#F0F0F0] rounded-lg transition-colors flex-shrink-0"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {error && (
            <div className="mb-4 p-3 bg-[#FEF2F2] border border-[#FECACA] rounded-xl text-[#991B1B] text-[13px] flex items-start gap-2">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {isLoading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="w-6 h-6 text-[#3FAF7A] animate-spin" />
              <span className="ml-3 text-[13px] text-[#666]">Loading details...</span>
            </div>
          ) : task.task_type === 'proposal' && proposalData ? (
            <ProposalPreview
              proposal={proposalData}
              onApply={handleApplyProposal}
              onDiscard={handleDiscardProposal}
              isApplying={isApplying}
            />
          ) : (
            <div className="space-y-5">
              {/* Description */}
              {task.description && (
                <div>
                  <h3 className="text-[13px] font-bold text-[#1D1D1F] mb-2">Description</h3>
                  <div className="bg-[#FAFAFA] rounded-xl p-4 border border-[#E5E5E5]">
                    <p className="text-[13px] text-[#333] leading-relaxed">{task.description}</p>
                  </div>
                </div>
              )}

              {/* Related entity */}
              {task.anchored_entity_type && task.anchored_entity_id && (
                <div>
                  <h3 className="text-[13px] font-bold text-[#1D1D1F] mb-2">Related Entity</h3>
                  <a
                    href={`/projects/${projectId}?entity=${task.anchored_entity_type}&id=${task.anchored_entity_id}`}
                    className="flex items-center gap-2.5 bg-[#FAFAFA] rounded-xl p-4 border border-[#E5E5E5] hover:border-[#3FAF7A] transition-colors group"
                  >
                    <div className="w-8 h-8 rounded-lg bg-[#E8F5E9] flex items-center justify-center flex-shrink-0">
                      <ExternalLink className="w-4 h-4 text-[#25785A]" />
                    </div>
                    <div>
                      <p className="text-[13px] font-medium text-[#333] group-hover:text-[#25785A] transition-colors capitalize">
                        View {task.anchored_entity_type}
                      </p>
                      <p className="text-[11px] text-[#999]">Open in workspace</p>
                    </div>
                  </a>
                </div>
              )}

              {/* Metadata grid */}
              <div>
                <h3 className="text-[13px] font-bold text-[#1D1D1F] mb-2">Details</h3>
                <div className="grid grid-cols-2 gap-3">
                  <MetaItem label="Status" value={task.status.replace(/_/g, ' ')} />
                  <MetaItem label="Type" value={typeConf.label} />
                  <MetaItem label="Created" value={new Date(task.created_at).toLocaleDateString()} />
                  {task.due_date && <MetaItem label="Due" value={new Date(task.due_date).toLocaleDateString()} />}
                  {task.assigned_to && <MetaItem label="Assigned" value={task.assigned_to} />}
                  {task.gate_stage && <MetaItem label="Gate" value={task.gate_stage.replace(/_/g, ' ')} />}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer actions */}
        {task.task_type !== 'proposal' && (
          <div className="flex-shrink-0 border-t border-[#E5E5E5] px-6 py-4 bg-white rounded-b-2xl">
            <div className="flex gap-3">
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
          </div>
        )}
      </div>
    </div>
  )
}

// =============================================================================
// Helpers
// =============================================================================

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-[#FAFAFA] rounded-lg px-3 py-2.5 border border-[#F0F0F0]">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-[#999] mb-0.5">{label}</p>
      <p className="text-[13px] text-[#333] capitalize">{value}</p>
    </div>
  )
}

function groupChangesByType(changes: any[]): Record<string, any[]> {
  if (!changes || !Array.isArray(changes)) return {}
  const grouped: Record<string, any[]> = {}
  for (const change of changes) {
    const type = change.entity_type || change.type || 'unknown'
    if (!grouped[type]) grouped[type] = []
    grouped[type].push({
      ...change,
      entity_type: type,
      evidence: change.evidence || [],
      rationale: change.rationale || '',
    })
  }
  return grouped
}
