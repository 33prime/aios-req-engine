/**
 * TouchpointHistory Component
 *
 * Expandable accordion showing completed collaboration touchpoints
 * with outcomes summaries. Groups touchpoints by type and shows
 * aggregated stats.
 */

'use client'

import React, { useState, useEffect } from 'react'
import {
  History,
  ChevronDown,
  ChevronUp,
  ChevronRight,
  Calendar,
  UserCheck,
  MessageSquare,
  Phone,
  CheckCircle,
  Loader2,
} from 'lucide-react'
import { formatDistanceToNow, format } from 'date-fns'
import { getCollaborationHistory, type CollaborationHistoryResponse } from '@/lib/api'

interface TouchpointSummary {
  id: string
  type: string
  title: string
  status: string
  sequence_number: number
  outcomes_summary: string
  completed_at: string | null
  created_at: string
}

interface TouchpointHistoryProps {
  projectId: string
  defaultExpanded?: boolean
}

const touchpointTypeConfig: Record<string, {
  icon: typeof Calendar
  label: string
  color: string
  bgColor: string
}> = {
  discovery_call: {
    icon: Phone,
    label: 'Discovery Call',
    color: 'text-[#009b87]',
    bgColor: 'bg-[#009b87]/10',
  },
  validation_round: {
    icon: UserCheck,
    label: 'Validation Round',
    color: 'text-[#009b87]',
    bgColor: 'bg-[#009b87]/10',
  },
  follow_up_call: {
    icon: Phone,
    label: 'Follow-up Call',
    color: 'text-[#009b87]',
    bgColor: 'bg-[#009b87]/10',
  },
  prototype_review: {
    icon: MessageSquare,
    label: 'Prototype Review',
    color: 'text-[#009b87]',
    bgColor: 'bg-[#009b87]/10',
  },
  feedback_session: {
    icon: MessageSquare,
    label: 'Feedback Session',
    color: 'text-[#009b87]',
    bgColor: 'bg-[#009b87]/10',
  },
}

export function TouchpointHistory({
  projectId,
  defaultExpanded = false,
}: TouchpointHistoryProps) {
  const [expanded, setExpanded] = useState(defaultExpanded)
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<CollaborationHistoryResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Fetch history when expanded
  useEffect(() => {
    if (expanded && !data && !loading) {
      loadHistory()
    }
  }, [expanded])

  const loadHistory = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await getCollaborationHistory(projectId)
      setData(response)
    } catch (err) {
      console.error('Failed to load history:', err)
      setError('Failed to load collaboration history')
    } finally {
      setLoading(false)
    }
  }

  const touchpoints = data?.touchpoints || []
  const hasHistory = touchpoints.length > 0

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Header - always clickable */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <History className="w-5 h-5 text-gray-400" />
          <div className="text-left">
            <h2 className="text-lg font-semibold text-gray-900">Collaboration History</h2>
            {data && hasHistory && (
              <p className="text-sm text-gray-500">
                {touchpoints.length} completed touchpoint{touchpoints.length !== 1 ? 's' : ''}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {hasHistory && (
            <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded-full">
              {touchpoints.length}
            </span>
          )}
          {expanded ? (
            <ChevronUp className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          )}
        </div>
      </button>

      {/* Content */}
      {expanded && (
        <div className="border-t border-gray-100">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 text-gray-400 animate-spin" />
            </div>
          ) : error ? (
            <div className="p-4 text-center text-red-600 text-sm">
              {error}
            </div>
          ) : !hasHistory ? (
            <EmptyState />
          ) : (
            <div className="divide-y divide-gray-100">
              {/* Aggregated stats */}
              {data && (
                <div className="p-4 bg-gray-50">
                  <div className="grid grid-cols-4 gap-4 text-center">
                    <StatItem
                      label="Questions"
                      value={data.total_questions_answered}
                    />
                    <StatItem
                      label="Documents"
                      value={data.total_documents_received}
                    />
                    <StatItem
                      label="Features"
                      value={data.total_features_extracted}
                    />
                    <StatItem
                      label="Confirmed"
                      value={data.total_items_confirmed}
                    />
                  </div>
                </div>
              )}

              {/* Touchpoint list */}
              {touchpoints.map((touchpoint) => (
                <TouchpointItem key={touchpoint.id} touchpoint={touchpoint} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function EmptyState() {
  return (
    <div className="p-8 text-center">
      <History className="w-10 h-10 text-gray-300 mx-auto mb-3" />
      <p className="text-sm text-gray-500">No completed touchpoints yet.</p>
      <p className="text-xs text-gray-400 mt-1">
        Completed discovery calls and validation rounds will appear here.
      </p>
    </div>
  )
}

function StatItem({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <span className="text-lg font-bold text-gray-900">{value}</span>
      <p className="text-xs text-gray-500">{label}</p>
    </div>
  )
}

function TouchpointItem({ touchpoint }: { touchpoint: TouchpointSummary }) {
  const [detailsOpen, setDetailsOpen] = useState(false)
  const config = touchpointTypeConfig[touchpoint.type] || touchpointTypeConfig.discovery_call
  const TypeIcon = config.icon

  const completedDate = touchpoint.completed_at
    ? format(new Date(touchpoint.completed_at), 'MMM d, yyyy')
    : null

  const completedAgo = touchpoint.completed_at
    ? formatDistanceToNow(new Date(touchpoint.completed_at), { addSuffix: true })
    : null

  return (
    <div className="p-4">
      <div
        className="flex items-start gap-3 cursor-pointer"
        onClick={() => setDetailsOpen(!detailsOpen)}
      >
        {/* Icon */}
        <div className={`w-8 h-8 ${config.bgColor} rounded-lg flex items-center justify-center flex-shrink-0`}>
          <TypeIcon className={`w-4 h-4 ${config.color}`} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4 className="font-medium text-gray-900">{touchpoint.title}</h4>
            {touchpoint.sequence_number > 1 && (
              <span className="text-xs text-gray-400">#{touchpoint.sequence_number}</span>
            )}
            <CheckCircle className="w-4 h-4 text-green-500" />
          </div>

          <p className="text-sm text-gray-600 mt-0.5">{touchpoint.outcomes_summary}</p>

          {completedDate && (
            <p className="text-xs text-gray-400 mt-1">
              Completed {completedDate} ({completedAgo})
            </p>
          )}
        </div>

        {/* Expand icon */}
        <ChevronRight
          className={`w-4 h-4 text-gray-400 transition-transform ${
            detailsOpen ? 'rotate-90' : ''
          }`}
        />
      </div>

      {/* Expanded details */}
      {detailsOpen && (
        <div className="mt-3 ml-11 p-3 bg-gray-50 rounded-lg">
          <p className="text-sm text-gray-600">
            Detailed touchpoint view coming soon. This will show:
          </p>
          <ul className="text-xs text-gray-500 mt-2 space-y-1">
            <li>• Questions asked and client answers</li>
            <li>• Documents requested and received</li>
            <li>• Entities extracted or confirmed</li>
            <li>• Meeting recording (if applicable)</li>
          </ul>
        </div>
      )}
    </div>
  )
}

export default TouchpointHistory
