'use client'

import { useState } from 'react'
import {
  CheckCircle,
  AlertCircle,
  Clock,
  ChevronDown,
  ChevronRight,
  Sparkles,
  Check,
  Loader2,
  Users,
  MousePointer,
  Settings,
  Layout,
  BookOpen,
  Link2,
  Zap,
  Trash2,
  RotateCcw,
  History
} from 'lucide-react'
import { Markdown } from '@/components/ui/Markdown'
import { DeleteConfirmationModal } from '@/components/ui/DeleteConfirmationModal'
import ChangeLogTimeline from '@/components/revisions/ChangeLogTimeline'
import type { Feature } from '@/types/api'

interface FeatureTableProps {
  features: Feature[]
  onConfirmationChange?: (featureId: string, newStatus: string) => Promise<void>
  onDelete?: (featureId: string) => void
  onBulkRebuild?: () => void
}

// Check if entity was recently updated (last 24 hours)
const isRecentlyUpdated = (updatedAt: string | undefined) => {
  if (!updatedAt) return false
  const diffMs = new Date().getTime() - new Date(updatedAt).getTime()
  return diffMs < 24 * 60 * 60 * 1000
}

export default function FeatureTable({ features, onConfirmationChange, onDelete, onBulkRebuild }: FeatureTableProps) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())
  const [historyExpandedIds, setHistoryExpandedIds] = useState<Set<string>>(new Set())
  const [updatingIds, setUpdatingIds] = useState<Set<string>>(new Set())
  const [deleteModal, setDeleteModal] = useState<{ featureId: string; featureName: string } | null>(null)

  const toggleHistory = (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setHistoryExpandedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const toggleExpand = (id: string) => {
    setExpandedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const handleConfirm = async (feature: Feature) => {
    if (!onConfirmationChange) return
    setUpdatingIds(prev => new Set(prev).add(feature.id))
    try {
      await onConfirmationChange(feature.id, 'confirmed_consultant')
    } finally {
      setUpdatingIds(prev => {
        const next = new Set(prev)
        next.delete(feature.id)
        return next
      })
    }
  }

  const handleNeedsReview = async (feature: Feature) => {
    if (!onConfirmationChange) return
    setUpdatingIds(prev => new Set(prev).add(feature.id))
    try {
      await onConfirmationChange(feature.id, 'needs_client')
    } finally {
      setUpdatingIds(prev => {
        const next = new Set(prev)
        next.delete(feature.id)
        return next
      })
    }
  }

  const handleRevertToDraft = async (feature: Feature) => {
    if (!onConfirmationChange) return
    setUpdatingIds(prev => new Set(prev).add(feature.id))
    try {
      await onConfirmationChange(feature.id, 'ai_generated')
    } finally {
      setUpdatingIds(prev => {
        const next = new Set(prev)
        next.delete(feature.id)
        return next
      })
    }
  }

  const handleDeleteClick = (feature: Feature) => {
    setDeleteModal({ featureId: feature.id, featureName: feature.name })
  }

  const handleDeleted = () => {
    if (onDelete && deleteModal) {
      onDelete(deleteModal.featureId)
    }
    setDeleteModal(null)
  }

  // Check if feature is confirmed (protected from bulk replace)
  const isConfirmed = (feature: Feature) => {
    const status = feature.confirmation_status || feature.status || 'ai_generated'
    return status === 'confirmed_consultant' || status === 'confirmed_client'
  }

  const getStatusBadge = (feature: Feature) => {
    const status = feature.confirmation_status || feature.status || 'ai_generated'
    switch (status) {
      case 'confirmed_client':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800"><CheckCircle className="h-3 w-3" />Client</span>
      case 'confirmed_consultant':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-emerald-100 text-emerald-800"><CheckCircle className="h-3 w-3" />Confirmed</span>
      case 'needs_client':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-800"><Clock className="h-3 w-3" />Review</span>
      default:
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">Draft</span>
    }
  }

  const getConfidenceDots = (confidence: string) => {
    const level = confidence?.toLowerCase() || 'medium'
    const filled = level === 'high' ? 3 : level === 'medium' ? 2 : 1
    return (
      <div className="flex items-center gap-0.5">
        {[1, 2, 3].map(i => (
          <div key={i} className={`w-1.5 h-1.5 rounded-full ${i <= filled ? 'bg-emerald-500' : 'bg-gray-200'}`} />
        ))}
      </div>
    )
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="grid grid-cols-[auto_1fr_100px_80px_100px_80px] gap-4 px-4 py-3 bg-gray-50 border-b border-gray-200 text-xs font-medium text-gray-500 uppercase tracking-wide">
        <div className="w-6"></div>
        <div>Feature</div>
        <div>Category</div>
        <div className="text-center">MVP</div>
        <div>Confidence</div>
        <div>Status</div>
      </div>

      {/* Rows */}
      <div className="divide-y divide-gray-100">
        {features.map(feature => {
          const isExpanded = expandedIds.has(feature.id)
          const isUpdating = updatingIds.has(feature.id)
          const isEnriched = feature.enrichment_status === 'enriched' || Boolean(feature.overview)
          const recentlyUpdated = isRecentlyUpdated((feature as any).updated_at)
          const confirmed = isConfirmed(feature)

          return (
            <div key={feature.id}>
              {/* Main Row */}
              <div
                className={`grid grid-cols-[auto_1fr_100px_80px_100px_80px] gap-4 px-4 py-3 items-center hover:bg-gray-50 cursor-pointer transition-colors ${isExpanded ? 'bg-emerald-50' : ''} ${recentlyUpdated ? 'border-l-2 border-l-yellow-400' : ''} ${confirmed ? 'bg-emerald-50/30' : ''}`}
                onClick={() => toggleExpand(feature.id)}
              >
                <div className="w-6 flex items-center">
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4 text-gray-400 group-hover:text-[#009b87]" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-gray-400 group-hover:text-[#009b87]" />
                  )}
                </div>
                <div className="flex items-center gap-2 min-w-0">
                  <span className="font-medium text-gray-900 truncate">{feature.name}</span>
                  {recentlyUpdated && !confirmed && (
                    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-yellow-100 text-yellow-700 text-xs font-medium rounded" title="Updated in the last 24 hours">
                      <Zap className="h-3 w-3" />
                      New
                    </span>
                  )}
                  {isEnriched && <Sparkles className="h-4 w-4 text-amber-500 flex-shrink-0" />}
                </div>
                <div className="text-sm text-gray-600 truncate">{feature.category}</div>
                <div className="text-center">
                  {feature.is_mvp && (
                    <span className="inline-flex items-center px-2.5 py-1 rounded text-xs font-medium bg-[#009b87] text-white">MVP</span>
                  )}
                </div>
                <div>{getConfidenceDots(feature.confidence)}</div>
                <div>{getStatusBadge(feature)}</div>
              </div>

              {/* Expanded Content */}
              {isExpanded && (
                <div className="px-4 pb-4 pt-2 bg-gray-50 border-t border-gray-100">
                  <div className="ml-6 space-y-4">
                    {/* Overview */}
                    {feature.overview && (
                      <div>
                        <h4 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-1">Overview</h4>
                        <div className="text-sm text-gray-700">
                          <Markdown content={feature.overview} />
                        </div>
                      </div>
                    )}

                    {/* Grid layout for enrichment sections */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Target Personas */}
                      {feature.target_personas && feature.target_personas.length > 0 && (
                        <div className="bg-white rounded-lg p-3 border border-gray-200">
                          <h4 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-2 flex items-center gap-1.5">
                            <Users className="h-3.5 w-3.5" />
                            Who Uses This
                          </h4>
                          <div className="space-y-1.5">
                            {feature.target_personas.map((persona, idx) => (
                              <div key={idx} className="flex items-start gap-2 text-sm">
                                <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs ${
                                  persona.role === 'primary' ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-600'
                                }`}>
                                  {persona.role === 'primary' ? 'P' : 'S'}
                                </span>
                                <div>
                                  <span className="font-medium">{persona.persona_name}</span>
                                  <span className="text-gray-500"> - {persona.context}</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* User Actions */}
                      {feature.user_actions && feature.user_actions.length > 0 && (
                        <div className="bg-white rounded-lg p-3 border border-gray-200">
                          <h4 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-2 flex items-center gap-1.5">
                            <MousePointer className="h-3.5 w-3.5" />
                            User Actions
                          </h4>
                          <ol className="space-y-1 text-sm text-gray-700 list-decimal list-inside">
                            {feature.user_actions.map((action, idx) => (
                              <li key={idx}>{action}</li>
                            ))}
                          </ol>
                        </div>
                      )}

                      {/* System Behaviors */}
                      {feature.system_behaviors && feature.system_behaviors.length > 0 && (
                        <div className="bg-white rounded-lg p-3 border border-gray-200">
                          <h4 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-2 flex items-center gap-1.5">
                            <Settings className="h-3.5 w-3.5" />
                            System Behaviors
                          </h4>
                          <ul className="space-y-1 text-sm text-gray-700">
                            {feature.system_behaviors.map((behavior, idx) => (
                              <li key={idx} className="flex items-start gap-1.5">
                                <span className="text-gray-400">•</span>
                                {behavior}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* UI Requirements */}
                      {feature.ui_requirements && feature.ui_requirements.length > 0 && (
                        <div className="bg-white rounded-lg p-3 border border-gray-200">
                          <h4 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-2 flex items-center gap-1.5">
                            <Layout className="h-3.5 w-3.5" />
                            UI Requirements
                          </h4>
                          <ul className="space-y-1 text-sm text-gray-700">
                            {feature.ui_requirements.map((req, idx) => (
                              <li key={idx} className="flex items-start gap-1.5">
                                <span className="text-gray-400">•</span>
                                {req}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Business Rules */}
                      {feature.rules && feature.rules.length > 0 && (
                        <div className="bg-white rounded-lg p-3 border border-gray-200">
                          <h4 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-2 flex items-center gap-1.5">
                            <BookOpen className="h-3.5 w-3.5" />
                            Business Rules
                          </h4>
                          <ul className="space-y-1 text-sm text-gray-700">
                            {feature.rules.map((rule, idx) => (
                              <li key={idx} className="flex items-start gap-1.5">
                                <span className="text-amber-500">!</span>
                                {rule}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Integrations */}
                      {feature.integrations && feature.integrations.length > 0 && (
                        <div className="bg-white rounded-lg p-3 border border-gray-200">
                          <h4 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-2 flex items-center gap-1.5">
                            <Link2 className="h-3.5 w-3.5" />
                            Integrations
                          </h4>
                          <div className="flex flex-wrap gap-1.5">
                            {feature.integrations.map((integration, idx) => (
                              <span key={idx} className="inline-flex items-center px-2 py-0.5 bg-purple-50 text-purple-700 text-xs rounded border border-purple-100">
                                {integration}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Evidence */}
                    {feature.evidence && feature.evidence.length > 0 && (
                      <div>
                        <h4 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-2">
                          Evidence ({feature.evidence.length})
                        </h4>
                        <div className="space-y-2">
                          {feature.evidence.slice(0, 2).map((ev: any, idx: number) => (
                            <div key={idx} className="bg-white rounded p-2 border border-gray-200 text-sm">
                              <p className="text-gray-700 italic">"{ev.excerpt}"</p>
                              <p className="text-gray-500 text-xs mt-1">{ev.rationale}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Actions */}
                    {onConfirmationChange && (
                      <div className="flex items-center gap-2 pt-2 border-t border-gray-200">
                        {isConfirmed(feature) ? (
                          <>
                            {/* Confirmed state - show status badge, revert, and delete */}
                            <span className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-[#009b87] text-white">
                              <CheckCircle className="h-4 w-4" />
                              Confirmed
                            </span>
                            <button
                              onClick={(e) => { e.stopPropagation(); handleRevertToDraft(feature) }}
                              disabled={isUpdating}
                              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                            >
                              {isUpdating ? <Loader2 className="h-4 w-4 animate-spin" /> : <RotateCcw className="h-4 w-4" />}
                              Revert to Draft
                            </button>
                            <button
                              onClick={(e) => { e.stopPropagation(); handleDeleteClick(feature) }}
                              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-white border border-red-200 text-red-600 hover:bg-red-50"
                            >
                              <Trash2 className="h-4 w-4" />
                              Delete
                            </button>
                          </>
                        ) : (
                          <>
                            {/* Draft state - show confirm and needs review */}
                            <button
                              onClick={(e) => { e.stopPropagation(); handleConfirm(feature) }}
                              disabled={isUpdating}
                              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                            >
                              {isUpdating ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle className="h-4 w-4" />}
                              Confirm
                            </button>
                            <button
                              onClick={(e) => { e.stopPropagation(); handleNeedsReview(feature) }}
                              disabled={isUpdating || feature.confirmation_status === 'needs_client'}
                              className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                                feature.confirmation_status === 'needs_client'
                                  ? 'bg-amber-600 text-white'
                                  : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                              } disabled:opacity-50`}
                            >
                              <AlertCircle className="h-4 w-4" />
                              Needs Review
                            </button>
                            <button
                              onClick={(e) => { e.stopPropagation(); handleDeleteClick(feature) }}
                              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-white border border-red-200 text-red-600 hover:bg-red-50"
                            >
                              <Trash2 className="h-4 w-4" />
                              Delete
                            </button>
                          </>
                        )}
                      </div>
                    )}

                    {/* Change History */}
                    <div className="pt-3 border-t border-gray-200">
                      <button
                        onClick={(e) => toggleHistory(feature.id, e)}
                        className="flex items-center gap-1.5 text-xs font-medium text-gray-500 hover:text-[#009b87] uppercase tracking-wide"
                      >
                        <History className="h-3.5 w-3.5" />
                        Change History
                        {historyExpandedIds.has(feature.id) ? (
                          <ChevronDown className="h-3.5 w-3.5" />
                        ) : (
                          <ChevronRight className="h-3.5 w-3.5" />
                        )}
                      </button>
                      {historyExpandedIds.has(feature.id) && (
                        <div className="mt-3">
                          <ChangeLogTimeline entityType="feature" entityId={feature.id} limit={10} />
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Delete Confirmation Modal */}
      {deleteModal && (
        <DeleteConfirmationModal
          isOpen={true}
          onClose={() => setDeleteModal(null)}
          entityType="feature"
          entityId={deleteModal.featureId}
          entityName={deleteModal.featureName}
          onDeleted={handleDeleted}
          onBulkRebuild={onBulkRebuild}
        />
      )}
    </div>
  )
}
