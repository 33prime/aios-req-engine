'use client'

import { useState, useEffect } from 'react'
import { Clock, Sparkles, ChevronDown, ChevronUp, AlertCircle, ArrowRight } from 'lucide-react'
import { listEntityRevisions } from '@/lib/api'

// Simple relative time formatter
function formatDistanceToNow(date: Date): string {
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffMins < 1) return 'less than a minute'
  if (diffMins < 60) return `${diffMins} minute${diffMins === 1 ? '' : 's'}`
  if (diffHours < 24) return `${diffHours} hour${diffHours === 1 ? '' : 's'}`
  if (diffDays < 30) return `${diffDays} day${diffDays === 1 ? '' : 's'}`
  return date.toLocaleDateString()
}

// Truncate long text for display
function truncateText(text: string | null | undefined, maxLength: number = 60): string {
  if (!text) return '(empty)'
  const str = typeof text === 'string' ? text : JSON.stringify(text)
  if (str.length <= maxLength) return str
  return str.substring(0, maxLength) + '...'
}

// Format who made the change
function formatAuthor(createdBy: string | null | undefined): string {
  if (!createdBy || createdBy === 'system') return 'System'
  if (createdBy === 'chat_assistant') return 'AI Assistant'
  if (createdBy === 'consultant') return 'Consultant'
  return createdBy
}

interface Revision {
  id: string
  entity_type: string
  entity_id: string
  revision_number: number
  change_type: string  // 'created', 'enriched', 'updated'
  changes: Record<string, any>
  diff_summary: string
  created_at: string
  created_by?: string
  source_signal_id?: string
}

interface ChangeLogTimelineProps {
  entityType: 'prd_section' | 'vp_step' | 'feature' | 'persona'
  entityId: string
  limit?: number
}

export default function ChangeLogTimeline({
  entityType,
  entityId,
  limit = 10,
}: ChangeLogTimelineProps) {
  const [revisions, setRevisions] = useState<Revision[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())

  useEffect(() => {
    const fetchRevisions = async () => {
      try {
        setLoading(true)
        setError(null)
        const response = await listEntityRevisions(entityType, entityId, limit)
        setRevisions(response.revisions)
      } catch (err) {
        console.error('Failed to fetch revisions:', err)
        setError('Failed to load change history')
      } finally {
        setLoading(false)
      }
    }

    fetchRevisions()
  }, [entityType, entityId, limit])

  const toggleExpanded = (revisionId: string) => {
    const newExpanded = new Set(expandedIds)
    if (newExpanded.has(revisionId)) {
      newExpanded.delete(revisionId)
    } else {
      newExpanded.add(revisionId)
    }
    setExpandedIds(newExpanded)
  }

  const getRevisionTypeBadge = (type: string) => {
    switch (type) {
      case 'created':
        return (
          <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-green-100 text-green-800">
            <Sparkles className="h-3 w-3 mr-1" />
            Created
          </span>
        )
      case 'enriched':
        return (
          <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-blue-100 text-blue-800">
            <Sparkles className="h-3 w-3 mr-1" />
            Enriched
          </span>
        )
      case 'updated':
        return (
          <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-purple-100 text-purple-800">
            <Clock className="h-3 w-3 mr-1" />
            Updated
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-800">
            {type}
          </span>
        )
    }
  }

  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp)
      return formatDistanceToNow(date) + ' ago'
    } catch {
      return timestamp
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center space-x-2 text-red-600 py-4">
        <AlertCircle className="h-5 w-5" />
        <span>{error}</span>
      </div>
    )
  }

  if (revisions.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <Clock className="h-12 w-12 mx-auto mb-2 opacity-50" />
        <p>No enrichment history yet</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Timeline */}
      <div className="relative">
        {/* Vertical line */}
        <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200" />

        {/* Revision entries */}
        <div className="space-y-6">
          {revisions.map((revision, index) => (
            <div key={revision.id} className="relative pl-10">
              {/* Timeline dot */}
              <div
                className={`absolute left-0 top-1 h-8 w-8 rounded-full border-4 border-white flex items-center justify-center ${
                  index === 0
                    ? 'bg-blue-500'
                    : revision.change_type === 'created'
                    ? 'bg-green-500'
                    : 'bg-gray-300'
                }`}
              >
                <Sparkles className="h-4 w-4 text-white" />
              </div>

              {/* Revision content */}
              <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
                <div className="p-4">
                  {/* Header row with badge and timestamp */}
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      {getRevisionTypeBadge(revision.change_type)}
                      <span className="text-xs text-gray-400">
                        by <span className="text-gray-600">{formatAuthor(revision.created_by)}</span>
                      </span>
                    </div>
                    <span className="text-xs text-gray-400">{formatTimestamp(revision.created_at)}</span>
                  </div>

                  {/* Show individual field changes if available */}
                  {revision.changes && Object.keys(revision.changes).length > 0 ? (
                    <div className="space-y-2">
                      {Object.entries(revision.changes).slice(0, expandedIds.has(revision.id) ? undefined : 2).map(([field, change]) => (
                        <div key={field} className="text-sm">
                          <span className="font-medium text-gray-700">{field}</span>
                          <div className="flex items-center gap-2 mt-1 text-xs">
                            <span className="px-2 py-1 bg-red-50 text-red-700 rounded line-through max-w-[45%] truncate">
                              {truncateText(change?.before, 40)}
                            </span>
                            <ArrowRight className="h-3 w-3 text-gray-400 flex-shrink-0" />
                            <span className="px-2 py-1 bg-green-50 text-green-700 rounded max-w-[45%] truncate">
                              {truncateText(change?.after, 40)}
                            </span>
                          </div>
                        </div>
                      ))}
                      {/* Show more button if there are more changes */}
                      {Object.keys(revision.changes).length > 2 && !expandedIds.has(revision.id) && (
                        <button
                          onClick={() => toggleExpanded(revision.id)}
                          className="text-xs text-blue-600 hover:text-blue-800"
                        >
                          +{Object.keys(revision.changes).length - 2} more changes
                        </button>
                      )}
                    </div>
                  ) : (
                    /* Fallback to summary text if no detailed changes */
                    <p className="text-sm text-gray-600">
                      {revision.diff_summary || 'Changes applied'}
                    </p>
                  )}

                  {/* Collapse button when expanded */}
                  {expandedIds.has(revision.id) && revision.changes && Object.keys(revision.changes).length > 2 && (
                    <button
                      onClick={() => toggleExpanded(revision.id)}
                      className="text-xs text-gray-500 hover:text-gray-700 mt-2"
                    >
                      Show less
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
