/**
 * Change History Viewer Component
 *
 * Shows the revision history for any strategic foundation entity
 * (business drivers, competitors, stakeholders, risks)
 */

'use client'

import React, { useState, useEffect } from 'react'
import { History, Loader2, Clock, User, FileText, ChevronDown, ChevronRight } from 'lucide-react'
import { Card, CardHeader } from '@/components/ui'

interface Revision {
  id: string
  entity_type: string
  entity_id: string
  entity_label: string
  revision_type: string
  revision_number: number | null
  created_by: string | null
  created_at: string
  changes: Record<string, { old: any; new: any }> | null
  diff_summary: string | null
  source_signal_id: string | null
}

interface ChangeHistoryViewerProps {
  entityType: string
  entityId: string
  limit?: number
}

export function ChangeHistoryViewer({
  entityType,
  entityId,
  limit = 20,
}: ChangeHistoryViewerProps) {
  const [revisions, setRevisions] = useState<Revision[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedRevisions, setExpandedRevisions] = useState<Set<string>>(new Set())

  useEffect(() => {
    loadRevisions()
  }, [entityType, entityId])

  const loadRevisions = async () => {
    try {
      setLoading(true)
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE
      const res = await fetch(
        `${baseUrl}/v1/state/${entityType}/${entityId}/revisions?limit=${limit}`
      )

      if (!res.ok) throw new Error('Failed to load revisions')

      const data = await res.json()
      setRevisions(data.revisions || [])
    } catch (error) {
      console.error('Error loading revisions:', error)
    } finally {
      setLoading(false)
    }
  }

  const toggleExpanded = (revisionId: string) => {
    const newExpanded = new Set(expandedRevisions)
    if (newExpanded.has(revisionId)) {
      newExpanded.delete(revisionId)
    } else {
      newExpanded.add(revisionId)
    }
    setExpandedRevisions(newExpanded)
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMins / 60)
    const diffDays = Math.floor(diffHours / 24)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`

    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }

  const getRevisionTypeColor = (type: string) => {
    switch (type) {
      case 'initial_extraction':
      case 'created':
        return 'bg-emerald-50 text-emerald-700'
      case 'enrichment':
      case 'updated':
        return 'bg-blue-50 text-blue-700'
      case 'confirmation':
        return 'bg-purple-50 text-purple-700'
      case 'merged':
        return 'bg-orange-50 text-orange-700'
      default:
        return 'bg-gray-50 text-gray-700'
    }
  }

  const getCreatedByColor = (createdBy: string | null) => {
    switch (createdBy) {
      case 'client':
        return 'bg-green-100 text-green-700'
      case 'consultant':
        return 'bg-blue-100 text-blue-700'
      case 'di_agent':
      case 'system':
        return 'bg-purple-100 text-purple-700'
      default:
        return 'bg-gray-100 text-gray-700'
    }
  }

  if (loading) {
    return (
      <Card>
        <CardHeader title="Change History" icon={History} />
        <div className="p-8 flex items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-brand-primary" />
        </div>
      </Card>
    )
  }

  if (revisions.length === 0) {
    return (
      <Card>
        <CardHeader title="Change History" icon={History} />
        <div className="p-8 text-center">
          <History className="h-12 w-12 mx-auto text-gray-300 mb-3" />
          <p className="text-sm text-gray-500">No change history yet</p>
        </div>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader title={`Change History (${revisions.length})`} icon={History} />
      <div className="p-4">
        <div className="space-y-3">
          {revisions.map((revision, index) => {
            const isExpanded = expandedRevisions.has(revision.id)
            const hasChanges = revision.changes && Object.keys(revision.changes).length > 0

            return (
              <div
                key={revision.id}
                className="border border-gray-200 rounded-lg overflow-hidden"
              >
                {/* Revision Header */}
                <div
                  className={`p-3 bg-gray-50 ${hasChanges ? 'cursor-pointer hover:bg-gray-100' : ''}`}
                  onClick={() => hasChanges && toggleExpanded(revision.id)}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3 flex-1 min-w-0">
                      {/* Expansion Icon */}
                      {hasChanges ? (
                        isExpanded ? (
                          <ChevronDown className="h-4 w-4 text-gray-400 flex-shrink-0 mt-0.5" />
                        ) : (
                          <ChevronRight className="h-4 w-4 text-gray-400 flex-shrink-0 mt-0.5" />
                        )
                      ) : (
                        <div className="h-4 w-4 flex-shrink-0" />
                      )}

                      {/* Revision Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap mb-1">
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${getRevisionTypeColor(revision.revision_type)}`}>
                            {revision.revision_type.replace('_', ' ')}
                          </span>
                          {revision.created_by && (
                            <span className={`px-2 py-0.5 rounded text-xs font-medium ${getCreatedByColor(revision.created_by)}`}>
                              {revision.created_by}
                            </span>
                          )}
                          {revision.revision_number && (
                            <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                              v{revision.revision_number}
                            </span>
                          )}
                        </div>

                        {revision.diff_summary && (
                          <p className="text-sm text-gray-700 leading-relaxed">
                            {revision.diff_summary}
                          </p>
                        )}

                        <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {formatDate(revision.created_at)}
                          </span>
                          {hasChanges && (
                            <span className="flex items-center gap-1">
                              <FileText className="h-3 w-3" />
                              {Object.keys(revision.changes!).length} field{Object.keys(revision.changes!).length !== 1 ? 's' : ''} changed
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Expanded Changes */}
                {isExpanded && hasChanges && (
                  <div className="p-3 bg-white border-t border-gray-200">
                    <div className="space-y-2">
                      {Object.entries(revision.changes!).map(([field, change]) => (
                        <div key={field} className="text-sm">
                          <div className="font-medium text-gray-700 mb-1">
                            {field.replace(/_/g, ' ')}
                          </div>
                          <div className="grid grid-cols-2 gap-2">
                            <div className="p-2 bg-red-50 rounded border border-red-100">
                              <div className="text-xs font-medium text-red-600 mb-1">Before</div>
                              <div className="text-xs text-gray-700 whitespace-pre-wrap break-words">
                                {change.old !== null && change.old !== undefined
                                  ? typeof change.old === 'object'
                                    ? JSON.stringify(change.old, null, 2)
                                    : String(change.old)
                                  : '(empty)'}
                              </div>
                            </div>
                            <div className="p-2 bg-emerald-50 rounded border border-emerald-100">
                              <div className="text-xs font-medium text-emerald-600 mb-1">After</div>
                              <div className="text-xs text-gray-700 whitespace-pre-wrap break-words">
                                {change.new !== null && change.new !== undefined
                                  ? typeof change.new === 'object'
                                    ? JSON.stringify(change.new, null, 2)
                                    : String(change.new)
                                  : '(empty)'}
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </Card>
  )
}
