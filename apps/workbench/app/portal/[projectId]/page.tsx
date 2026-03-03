/**
 * Client Portal Hub — Dashboard
 *
 * Replaces the Q&A-only page with a full dashboard:
 * - Meeting card (next meeting + agenda)
 * - Prototype card (status + link)
 * - Validation queue summary → /validate
 * - Recent activity feed
 */

'use client'

import React, { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { getPortalDashboard } from '@/lib/api'
import type { PortalDashboard } from '@/types/portal'

export default function PortalHubPage() {
  const params = useParams()
  const router = useRouter()
  const projectId = params.projectId as string

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dashboard, setDashboard] = useState<PortalDashboard | null>(null)

  useEffect(() => {
    setLoading(true)
    getPortalDashboard(projectId)
      .then(setDashboard)
      .catch(err => setError(err.message || 'Failed to load'))
      .finally(() => setLoading(false))
  }, [projectId])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-[#009b87] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-gray-500">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  if (error || !dashboard) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <p className="text-red-600 mb-2">{error || 'Failed to load dashboard'}</p>
          <button
            onClick={() => window.location.reload()}
            className="text-sm text-[#009b87] hover:underline"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  const { validation_summary, upcoming_meeting, prototype_status, team_summary, recent_activity } = dashboard

  return (
    <div className="space-y-6">
      {/* Welcome header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{dashboard.project_name}</h1>
        <p className="text-gray-500 mt-1">
          {dashboard.portal_role === 'client_admin'
            ? 'Welcome back \u2014 here\u2019s your project overview.'
            : 'Welcome \u2014 here are your assigned items.'}
        </p>
      </div>

      {/* Cards grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Validation Queue Card */}
        {validation_summary && validation_summary.total_pending > 0 && (
          <button
            onClick={() => router.push(`/portal/${projectId}/validate`)}
            className="bg-white rounded-xl border border-gray-200 p-5 text-left hover:border-[#009b87] hover:shadow-sm transition-all"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-gray-500 uppercase tracking-wide">Validation Queue</span>
              {validation_summary.urgent_count > 0 && (
                <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
                  {validation_summary.urgent_count} urgent
                </span>
              )}
            </div>
            <p className="text-3xl font-bold text-gray-900">{validation_summary.total_pending}</p>
            <p className="text-sm text-gray-500 mt-1">items awaiting your review</p>
            <div className="flex flex-wrap gap-2 mt-3">
              {Object.entries(validation_summary.by_type).map(([type, count]) =>
                count > 0 ? (
                  <span key={type} className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                    {type.replace('_', ' ')}: {count}
                  </span>
                ) : null
              )}
            </div>
          </button>
        )}

        {/* Meeting Card */}
        {upcoming_meeting && (
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <span className="text-sm font-medium text-gray-500 uppercase tracking-wide">
              Upcoming Meeting
            </span>
            <p className="text-lg font-semibold text-gray-900 mt-2">
              {upcoming_meeting.title || 'Discovery Call'}
            </p>
            <p className="text-sm text-gray-500 mt-1">
              {new Date(upcoming_meeting.scheduled_at).toLocaleDateString('en-US', {
                weekday: 'long',
                month: 'long',
                day: 'numeric',
                hour: 'numeric',
                minute: '2-digit',
              })}
            </p>
            {upcoming_meeting.meeting_type && (
              <span className="inline-block mt-3 text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded">
                {upcoming_meeting.meeting_type}
              </span>
            )}
          </div>
        )}

        {/* Prototype Card */}
        {prototype_status && (
          <button
            onClick={() => router.push(`/portal/${projectId}/prototype`)}
            className="bg-white rounded-xl border border-gray-200 p-5 text-left hover:border-[#009b87] hover:shadow-sm transition-all"
          >
            <span className="text-sm font-medium text-gray-500 uppercase tracking-wide">
              Prototype
            </span>
            <p className="text-lg font-semibold text-gray-900 mt-2">
              {prototype_status.status === 'deployed' ? 'Ready for review' : prototype_status.status}
            </p>
            {prototype_status.deploy_url && (
              <p className="text-sm text-[#009b87] mt-1">Click to review the prototype</p>
            )}
          </button>
        )}

        {/* Team Summary (admin only) */}
        {team_summary && dashboard.portal_role === 'client_admin' && (
          <button
            onClick={() => router.push(`/portal/${projectId}/team`)}
            className="bg-white rounded-xl border border-gray-200 p-5 text-left hover:border-[#009b87] hover:shadow-sm transition-all"
          >
            <span className="text-sm font-medium text-gray-500 uppercase tracking-wide">
              Team Progress
            </span>
            <div className="mt-2">
              <div className="flex items-end gap-2">
                <span className="text-3xl font-bold text-gray-900">{team_summary.completion_pct}%</span>
                <span className="text-sm text-gray-500 mb-1">validated</span>
              </div>
              <div className="w-full h-2 bg-gray-100 rounded-full mt-2 overflow-hidden">
                <div
                  className="h-full bg-[#009b87] rounded-full transition-all"
                  style={{ width: `${team_summary.completion_pct}%` }}
                />
              </div>
              <p className="text-sm text-gray-500 mt-2">
                {team_summary.member_count} team members &middot; {team_summary.completed_assignments}/{team_summary.total_assignments} items
              </p>
            </div>
          </button>
        )}
      </div>

      {/* Info Requests Progress (legacy support) */}
      {dashboard.progress.total_items > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-gray-500 uppercase tracking-wide">
              Information Requests
            </span>
            <span className="text-lg font-bold text-[#009b87]">{dashboard.progress.percentage}%</span>
          </div>
          <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-[#009b87] rounded-full transition-all"
              style={{ width: `${dashboard.progress.percentage}%` }}
            />
          </div>
          <p className="text-sm text-gray-500 mt-2">
            {dashboard.progress.completed_items} of {dashboard.progress.total_items} completed
          </p>
        </div>
      )}

      {/* Recent Activity */}
      {recent_activity.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-4">
            Recent Activity
          </h2>
          <div className="space-y-3">
            {recent_activity.slice(0, 8).map(activity => (
              <div key={activity.id} className="flex items-start gap-3 text-sm">
                <span className={`
                  mt-0.5 w-2 h-2 rounded-full flex-shrink-0
                  ${activity.verdict === 'confirmed' ? 'bg-green-500' :
                    activity.verdict === 'refine' ? 'bg-amber-500' :
                    activity.verdict === 'flag' ? 'bg-red-500' : 'bg-gray-300'}
                `} />
                <div className="flex-1 min-w-0">
                  <p className="text-gray-900">
                    <span className="font-medium">
                      {activity.stakeholders?.name || 'Stakeholder'}
                    </span>
                    {' '}{activity.verdict}{' '}
                    <span className="text-gray-500">{activity.entity_type.replace('_', ' ')}</span>
                  </p>
                  {activity.notes && (
                    <p className="text-gray-500 truncate">{activity.notes}</p>
                  )}
                </div>
                <span className="text-xs text-gray-400 flex-shrink-0">
                  {new Date(activity.created_at).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                  })}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!validation_summary?.total_pending &&
       !upcoming_meeting &&
       !prototype_status &&
       dashboard.progress.total_items === 0 && (
        <div className="text-center py-12">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-2xl">&#9889;</span>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Getting Started</h2>
          <p className="text-gray-500 max-w-md mx-auto">
            Your consultant is preparing your project. Check back soon for items that need your review.
          </p>
        </div>
      )}
    </div>
  )
}
