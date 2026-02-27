/**
 * ProposalPreview Component
 *
 * Displays a batch proposal with preview/apply workflow.
 * Shows summary, changes grouped by type, evidence, and action buttons.
 *
 * Features:
 * - Collapsible change cards with before/after views
 * - Evidence badges
 * - Apply/Discard actions with confirmation
 * - Different views: summary, detailed, diff
 */

'use client'

import { useState } from 'react'
import { ChevronDown, ChevronRight, CheckCircle2, Edit3, Trash2, FileText, Users, Layers, Target } from 'lucide-react'

interface EvidenceItem {
  chunk_id: string
  excerpt: string
  rationale: string
}

interface Change {
  entity_type: 'feature' | 'vp_step' | 'persona' | 'business_driver' | 'stakeholder' | 'constraint' | 'competitor_ref'
  operation: 'create' | 'update' | 'delete'
  entity_id?: string
  before?: any
  after: any
  evidence?: EvidenceItem[]
  rationale?: string
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
  changes_by_type?: Record<string, Change[]>
}

interface ProposalPreviewProps {
  proposal: ProposalData
  onApply?: (proposalId: string) => void
  onDiscard?: (proposalId: string) => void
  isApplying?: boolean
}

export function ProposalPreview({ proposal, onApply, onDiscard, isApplying }: ProposalPreviewProps) {
  const [expandedChanges, setExpandedChanges] = useState<Set<string>>(new Set())
  const [showConfirmation, setShowConfirmation] = useState(false)

  const toggleChange = (key: string) => {
    const newExpanded = new Set(expandedChanges)
    if (newExpanded.has(key)) {
      newExpanded.delete(key)
    } else {
      newExpanded.add(key)
    }
    setExpandedChanges(newExpanded)
  }

  const handleApply = () => {
    if (proposal.total_changes > 3 && !showConfirmation) {
      setShowConfirmation(true)
    } else {
      onApply?.(proposal.proposal_id)
      setShowConfirmation(false)
    }
  }

  const handleDiscard = () => {
    onDiscard?.(proposal.proposal_id)
  }

  return (
    <div className="border border-border rounded-lg bg-white shadow-sm overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-brand-primary-light to-brand-primary-light px-4 py-3 border-b border-border">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-brand-primary-light rounded-lg flex items-center justify-center">
                <Layers className="h-4 w-4 text-brand-primary" />
              </div>
              <div>
                <h3 className="font-semibold text-text-body text-sm">{proposal.title}</h3>
                {proposal.description && (
                  <p className="text-xs text-text-placeholder mt-0.5">{proposal.description}</p>
                )}
              </div>
            </div>
          </div>
          <StatusBadge status={proposal.status} />
        </div>
      </div>

      {/* Summary Stats */}
      <div className="px-4 py-3 bg-surface-muted border-b border-border">
        <div className="flex items-center gap-4 text-sm">
          {proposal.creates > 0 && (
            <div className="flex items-center gap-1.5">
              <div className="w-5 h-5 bg-emerald-100 rounded flex items-center justify-center">
                <span className="text-xs font-medium text-emerald-700">+</span>
              </div>
              <span className="text-[#666666]">
                {proposal.creates} {proposal.creates === 1 ? 'create' : 'creates'}
              </span>
            </div>
          )}
          {proposal.updates > 0 && (
            <div className="flex items-center gap-1.5">
              <div className="w-5 h-5 bg-teal-50 rounded flex items-center justify-center">
                <Edit3 className="h-3 w-3 text-teal-700" />
              </div>
              <span className="text-[#666666]">
                {proposal.updates} {proposal.updates === 1 ? 'update' : 'updates'}
              </span>
            </div>
          )}
          {proposal.deletes > 0 && (
            <div className="flex items-center gap-1.5">
              <div className="w-5 h-5 bg-gray-100 rounded flex items-center justify-center">
                <Trash2 className="h-3 w-3 text-gray-600" />
              </div>
              <span className="text-[#666666]">
                {proposal.deletes} {proposal.deletes === 1 ? 'delete' : 'deletes'}
              </span>
            </div>
          )}
          <div className="ml-auto text-xs text-text-placeholder">
            {proposal.total_changes} total {proposal.total_changes === 1 ? 'change' : 'changes'}
          </div>
        </div>
      </div>

      {/* Changes List */}
      <div className="divide-y divide-border max-h-96 overflow-y-auto">
        {proposal.changes_by_type &&
          Object.entries(proposal.changes_by_type).map(([entityType, changes]) => (
            <div key={entityType} className="p-4">
              <div className="flex items-center gap-2 mb-3">
                {getEntityIcon(entityType)}
                <h4 className="text-sm font-medium text-text-body capitalize">
                  {entityType.replace('_', ' ')}s ({changes.length})
                </h4>
              </div>
              <div className="space-y-2">
                {changes.map((change, idx) => {
                  const changeKey = `${entityType}-${idx}`
                  const isExpanded = expandedChanges.has(changeKey)

                  return (
                    <div
                      key={changeKey}
                      className="border border-border rounded-lg overflow-hidden bg-white"
                    >
                      {/* Change Header */}
                      <button
                        onClick={() => toggleChange(changeKey)}
                        className="w-full flex items-center gap-3 p-3 hover:bg-surface-muted transition-colors text-left"
                      >
                        <div className="flex-shrink-0">
                          {isExpanded ? (
                            <ChevronDown className="h-4 w-4 text-text-placeholder" />
                          ) : (
                            <ChevronRight className="h-4 w-4 text-text-placeholder" />
                          )}
                        </div>
                        <OperationBadge operation={change.operation} />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-text-body truncate">
                            {getChangeName(change)}
                          </p>
                        </div>
                        {change.evidence && change.evidence.length > 0 && (
                          <div className="flex items-center gap-1 px-2 py-1 bg-emerald-50 rounded text-xs text-emerald-700">
                            <FileText className="h-3 w-3" />
                            <span>{change.evidence.length}</span>
                          </div>
                        )}
                      </button>

                      {/* Change Details (Expanded) */}
                      {isExpanded && (
                        <div className="px-3 pb-3 pt-0 space-y-3 border-t border-border bg-surface-muted">
                          {/* Rationale */}
                          {change.rationale && (
                            <div className="pt-3">
                              <p className="text-xs font-medium text-[#666666] mb-1">Why:</p>
                              <p className="text-sm text-text-body">{change.rationale}</p>
                            </div>
                          )}

                          {/* Before/After */}
                          {change.operation === 'update' && change.before && (
                            <div className="space-y-2">
                              <div className="bg-gray-50 border border-gray-200 rounded p-2">
                                <p className="text-xs font-medium text-gray-600 mb-1">Before:</p>
                                <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono overflow-x-auto">
                                  {JSON.stringify(change.before, null, 2)}
                                </pre>
                              </div>
                              <div className="bg-emerald-50 border border-emerald-200 rounded p-2">
                                <p className="text-xs font-medium text-emerald-800 mb-1">After:</p>
                                <pre className="text-xs text-emerald-700 whitespace-pre-wrap font-mono overflow-x-auto">
                                  {JSON.stringify(change.after, null, 2)}
                                </pre>
                              </div>
                            </div>
                          )}

                          {change.operation === 'create' && (
                            <div className="bg-emerald-50 border border-emerald-200 rounded p-2">
                              <p className="text-xs font-medium text-emerald-800 mb-1">New:</p>
                              <pre className="text-xs text-emerald-700 whitespace-pre-wrap font-mono overflow-x-auto">
                                {JSON.stringify(change.after, null, 2)}
                              </pre>
                            </div>
                          )}

                          {/* Evidence */}
                          {change.evidence && change.evidence.length > 0 && (
                            <div>
                              <p className="text-xs font-medium text-[#666666] mb-2">
                                Evidence ({change.evidence.length}):
                              </p>
                              <div className="space-y-2">
                                {change.evidence.map((ev, evIdx) => (
                                  <div
                                    key={evIdx}
                                    className="bg-emerald-50 border border-emerald-100 rounded p-2"
                                  >
                                    <p className="text-xs text-emerald-900 italic mb-1">
                                      &ldquo;{ev.excerpt}&rdquo;
                                    </p>
                                    <p className="text-xs text-emerald-700">{ev.rationale}</p>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
      </div>

      {/* Actions */}
      {proposal.status !== 'applied' && proposal.status !== 'discarded' && (
        <div className="px-4 py-3 bg-surface-muted border-t border-border">
          {showConfirmation ? (
            <div className="space-y-3">
              <div className="flex items-start gap-2 p-3 bg-emerald-50 border border-emerald-200 rounded-lg">
                <AlertCircleIcon className="w-4 h-4 text-emerald-600 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-emerald-900">Confirm Application</p>
                  <p className="text-xs text-emerald-700 mt-1">
                    This will apply {proposal.total_changes} changes to your project. This action
                    cannot be undone.
                  </p>
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleApply}
                  disabled={isApplying}
                  className="flex-1 px-4 py-2 text-sm font-medium text-white bg-brand-primary hover:bg-[#25785A] rounded-lg transition-colors disabled:opacity-50"
                >
                  {isApplying ? 'Applying...' : 'Confirm & Apply'}
                </button>
                <button
                  onClick={() => setShowConfirmation(false)}
                  disabled={isApplying}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="flex gap-2">
              <button
                onClick={handleApply}
                disabled={isApplying}
                className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-white bg-brand-primary hover:bg-[#25785A] rounded-lg transition-colors disabled:opacity-50"
              >
                {isApplying ? (
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <CheckCircle2 className="h-4 w-4" />
                )}
                {isApplying ? 'Applying...' : 'Apply All'}
              </button>
              <button
                onClick={handleDiscard}
                disabled={isApplying}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50"
              >
                Discard
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// Helper Components

function AlertCircleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  )
}

function StatusBadge({ status }: { status: string }) {
  const config = {
    pending: { bg: 'bg-gray-100', text: 'text-gray-700', label: 'Pending' },
    previewed: { bg: 'bg-emerald-50', text: 'text-emerald-700', label: 'Previewed' },
    applied: { bg: 'bg-emerald-100', text: 'text-emerald-700', label: 'Applied' },
    discarded: { bg: 'bg-gray-100', text: 'text-gray-500', label: 'Discarded' },
  }[status] || { bg: 'bg-gray-100', text: 'text-gray-700', label: status }

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
      {config.label}
    </span>
  )
}

function OperationBadge({ operation }: { operation: string }) {
  const config = {
    create: { icon: '+', bg: 'bg-emerald-100', text: 'text-emerald-700', label: 'Create' },
    update: { icon: <Edit3 className="h-3 w-3" />, bg: 'bg-teal-50', text: 'text-teal-700', label: 'Update' },
    delete: { icon: <Trash2 className="h-3 w-3" />, bg: 'bg-gray-100', text: 'text-gray-600', label: 'Delete' },
  }[operation] || { icon: '?', bg: 'bg-gray-100', text: 'text-gray-700', label: operation }

  return (
    <div className={`flex items-center gap-1 px-2 py-1 rounded ${config.bg}`}>
      {typeof config.icon === 'string' ? (
        <span className={`text-xs font-bold ${config.text}`}>{config.icon}</span>
      ) : (
        <span className={config.text}>{config.icon}</span>
      )}
      <span className={`text-xs font-medium ${config.text}`}>{config.label}</span>
    </div>
  )
}

function getEntityIcon(entityType: string) {
  const icons: Record<string, JSX.Element> = {
    feature: <Target className="h-4 w-4 text-emerald-600" />,
    vp_step: <Layers className="h-4 w-4 text-teal-600" />,
    persona: <Users className="h-4 w-4 text-emerald-700" />,
    business_driver: <FileText className="h-4 w-4 text-teal-700" />,
    stakeholder: <Users className="h-4 w-4 text-emerald-600" />,
    constraint: <Target className="h-4 w-4 text-emerald-800" />,
    competitor_ref: <FileText className="h-4 w-4 text-teal-600" />,
  }
  return icons[entityType] || <FileText className="h-4 w-4 text-gray-600" />
}

function getChangeName(change: Change): string {
  const data = change.after || change.before || {}
  // Handle various entity naming conventions
  return (
    data.name ||
    data.label ||
    data.title ||
    data.slug ||
    data.description?.slice(0, 50) ||
    data.driver_type ||
    data.reference_type ||
    'Untitled'
  )
}
