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
import { Button } from '@/components/ui/Button'

interface EvidenceItem {
  chunk_id: string
  excerpt: string
  rationale: string
}

interface Change {
  entity_type: 'feature' | 'vp_step' | 'persona' | 'business_driver'
  operation: 'create' | 'update' | 'delete'
  entity_id?: string
  before?: any
  after: any
  evidence: EvidenceItem[]
  rationale: string
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
    <div className="border border-ui-cardBorder rounded-lg bg-white shadow-sm overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-brand-primary/5 to-brand-primary/10 px-4 py-3 border-b border-ui-cardBorder">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-brand-primary/10 rounded-lg flex items-center justify-center">
                <Layers className="h-4 w-4 text-brand-primary" />
              </div>
              <div>
                <h3 className="font-semibold text-ui-text-primary text-sm">{proposal.title}</h3>
                {proposal.description && (
                  <p className="text-xs text-ui-text-tertiary mt-0.5">{proposal.description}</p>
                )}
              </div>
            </div>
          </div>
          <StatusBadge status={proposal.status} />
        </div>
      </div>

      {/* Summary Stats */}
      <div className="px-4 py-3 bg-ui-cardBg border-b border-ui-cardBorder">
        <div className="flex items-center gap-4 text-sm">
          {proposal.creates > 0 && (
            <div className="flex items-center gap-1.5">
              <div className="w-5 h-5 bg-green-100 rounded flex items-center justify-center">
                <span className="text-xs font-medium text-green-700">+</span>
              </div>
              <span className="text-ui-text-secondary">
                {proposal.creates} {proposal.creates === 1 ? 'create' : 'creates'}
              </span>
            </div>
          )}
          {proposal.updates > 0 && (
            <div className="flex items-center gap-1.5">
              <div className="w-5 h-5 bg-blue-100 rounded flex items-center justify-center">
                <Edit3 className="h-3 w-3 text-blue-700" />
              </div>
              <span className="text-ui-text-secondary">
                {proposal.updates} {proposal.updates === 1 ? 'update' : 'updates'}
              </span>
            </div>
          )}
          {proposal.deletes > 0 && (
            <div className="flex items-center gap-1.5">
              <div className="w-5 h-5 bg-red-100 rounded flex items-center justify-center">
                <Trash2 className="h-3 w-3 text-red-700" />
              </div>
              <span className="text-ui-text-secondary">
                {proposal.deletes} {proposal.deletes === 1 ? 'delete' : 'deletes'}
              </span>
            </div>
          )}
          <div className="ml-auto text-xs text-ui-text-tertiary">
            {proposal.total_changes} total {proposal.total_changes === 1 ? 'change' : 'changes'}
          </div>
        </div>
      </div>

      {/* Changes List */}
      <div className="divide-y divide-ui-cardBorder max-h-96 overflow-y-auto">
        {proposal.changes_by_type &&
          Object.entries(proposal.changes_by_type).map(([entityType, changes]) => (
            <div key={entityType} className="p-4">
              <div className="flex items-center gap-2 mb-3">
                {getEntityIcon(entityType)}
                <h4 className="text-sm font-medium text-ui-text-primary capitalize">
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
                      className="border border-ui-cardBorder rounded-lg overflow-hidden bg-white"
                    >
                      {/* Change Header */}
                      <button
                        onClick={() => toggleChange(changeKey)}
                        className="w-full flex items-center gap-3 p-3 hover:bg-ui-cardBg transition-colors text-left"
                      >
                        <div className="flex-shrink-0">
                          {isExpanded ? (
                            <ChevronDown className="h-4 w-4 text-ui-text-tertiary" />
                          ) : (
                            <ChevronRight className="h-4 w-4 text-ui-text-tertiary" />
                          )}
                        </div>
                        <OperationBadge operation={change.operation} />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-ui-text-primary truncate">
                            {getChangeName(change)}
                          </p>
                        </div>
                        {change.evidence.length > 0 && (
                          <div className="flex items-center gap-1 px-2 py-1 bg-blue-50 rounded text-xs text-blue-700">
                            <FileText className="h-3 w-3" />
                            <span>{change.evidence.length}</span>
                          </div>
                        )}
                      </button>

                      {/* Change Details (Expanded) */}
                      {isExpanded && (
                        <div className="px-3 pb-3 pt-0 space-y-3 border-t border-ui-cardBorder bg-ui-cardBg">
                          {/* Rationale */}
                          {change.rationale && (
                            <div className="pt-3">
                              <p className="text-xs font-medium text-ui-text-secondary mb-1">Why:</p>
                              <p className="text-sm text-ui-text-primary">{change.rationale}</p>
                            </div>
                          )}

                          {/* Before/After */}
                          {change.operation === 'update' && change.before && (
                            <div className="space-y-2">
                              <div className="bg-red-50 border border-red-200 rounded p-2">
                                <p className="text-xs font-medium text-red-900 mb-1">Before:</p>
                                <pre className="text-xs text-red-800 whitespace-pre-wrap font-mono overflow-x-auto">
                                  {JSON.stringify(change.before, null, 2)}
                                </pre>
                              </div>
                              <div className="bg-green-50 border border-green-200 rounded p-2">
                                <p className="text-xs font-medium text-green-900 mb-1">After:</p>
                                <pre className="text-xs text-green-800 whitespace-pre-wrap font-mono overflow-x-auto">
                                  {JSON.stringify(change.after, null, 2)}
                                </pre>
                              </div>
                            </div>
                          )}

                          {change.operation === 'create' && (
                            <div className="bg-green-50 border border-green-200 rounded p-2">
                              <p className="text-xs font-medium text-green-900 mb-1">New:</p>
                              <pre className="text-xs text-green-800 whitespace-pre-wrap font-mono overflow-x-auto">
                                {JSON.stringify(change.after, null, 2)}
                              </pre>
                            </div>
                          )}

                          {/* Evidence */}
                          {change.evidence.length > 0 && (
                            <div>
                              <p className="text-xs font-medium text-ui-text-secondary mb-2">
                                Evidence ({change.evidence.length}):
                              </p>
                              <div className="space-y-2">
                                {change.evidence.map((ev, evIdx) => (
                                  <div
                                    key={evIdx}
                                    className="bg-blue-50 border border-blue-200 rounded p-2"
                                  >
                                    <p className="text-xs text-blue-900 italic mb-1">
                                      "{ev.excerpt}"
                                    </p>
                                    <p className="text-xs text-blue-700">{ev.rationale}</p>
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
        <div className="px-4 py-3 bg-ui-cardBg border-t border-ui-cardBorder">
          {showConfirmation ? (
            <div className="space-y-3">
              <div className="flex items-start gap-2 p-3 bg-yellow-50 border border-yellow-200 rounded">
                <div className="mt-0.5">⚠️</div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-yellow-900">Confirm Application</p>
                  <p className="text-xs text-yellow-800 mt-1">
                    This will apply {proposal.total_changes} changes to your project. This action
                    cannot be undone.
                  </p>
                </div>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="primary"
                  onClick={handleApply}
                  disabled={isApplying}
                  className="flex-1"
                >
                  {isApplying ? 'Applying...' : 'Confirm & Apply'}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setShowConfirmation(false)}
                  disabled={isApplying}
                >
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex gap-2">
              <Button
                variant="primary"
                onClick={handleApply}
                disabled={isApplying}
                className="flex-1"
                icon={<CheckCircle2 className="h-4 w-4" />}
              >
                {isApplying ? 'Applying...' : 'Apply All'}
              </Button>
              <Button variant="outline" onClick={handleDiscard} disabled={isApplying}>
                Discard
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// Helper Components

function StatusBadge({ status }: { status: string }) {
  const config = {
    pending: { bg: 'bg-gray-100', text: 'text-gray-700', label: 'Pending' },
    previewed: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Previewed' },
    applied: { bg: 'bg-green-100', text: 'text-green-700', label: 'Applied' },
    discarded: { bg: 'bg-red-100', text: 'text-red-700', label: 'Discarded' },
  }[status] || { bg: 'bg-gray-100', text: 'text-gray-700', label: status }

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
      {config.label}
    </span>
  )
}

function OperationBadge({ operation }: { operation: string }) {
  const config = {
    create: { icon: '+', bg: 'bg-green-100', text: 'text-green-700', label: 'Create' },
    update: { icon: <Edit3 className="h-3 w-3" />, bg: 'bg-blue-100', text: 'text-blue-700', label: 'Update' },
    delete: { icon: <Trash2 className="h-3 w-3" />, bg: 'bg-red-100', text: 'text-red-700', label: 'Delete' },
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
  const icons = {
    feature: <Target className="h-4 w-4 text-brand-primary" />,
    vp_step: <Layers className="h-4 w-4 text-blue-600" />,
    persona: <Users className="h-4 w-4 text-green-600" />,
    business_driver: <FileText className="h-4 w-4 text-purple-600" />,
  }
  return icons[entityType as keyof typeof icons] || <FileText className="h-4 w-4 text-gray-600" />
}

function getChangeName(change: Change): string {
  const data = change.after || change.before || {}
  return data.name || data.label || data.slug || data.title || 'Untitled'
}
