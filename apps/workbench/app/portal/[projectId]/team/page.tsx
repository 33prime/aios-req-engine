/**
 * Team Management Page (admin only)
 *
 * Progress bar, per-member cards with assignment completion.
 * Invite modal for adding new stakeholders.
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import { useParams } from 'next/navigation'
import { getTeamProgress, getTeamMembers, inviteTeamMember } from '@/lib/api/portal'
import type { TeamProgress, TeamMember, TeamInviteRequest } from '@/types/portal'

export default function TeamPage() {
  const params = useParams()
  const projectId = params.projectId as string

  const [loading, setLoading] = useState(true)
  const [progress, setProgress] = useState<TeamProgress | null>(null)
  const [members, setMembers] = useState<TeamMember[]>([])
  const [showInvite, setShowInvite] = useState(false)
  const [inviteForm, setInviteForm] = useState<TeamInviteRequest>({ email: '' })
  const [inviting, setInviting] = useState(false)
  const [inviteResult, setInviteResult] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    try {
      setError(null)
      const [progressData, membersData] = await Promise.all([
        getTeamProgress(projectId),
        getTeamMembers(projectId),
      ])
      setProgress(progressData)
      setMembers(membersData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load team data')
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleInvite = async () => {
    if (!inviteForm.email) return
    setInviting(true)
    setInviteResult(null)
    try {
      const result = await inviteTeamMember(projectId, inviteForm)
      if (result.magic_link_sent) {
        setInviteResult(`Invitation sent to ${inviteForm.email}`)
      } else {
        setInviteResult(`Added ${inviteForm.email} (invite email: ${result.magic_link_error || 'pending'})`)
      }
      setInviteForm({ email: '' })
      await loadData()
    } catch (err) {
      setInviteResult(`Error: ${err instanceof Error ? err.message : 'Failed to invite'}`)
    } finally {
      setInviting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="w-8 h-8 border-2 border-[#009b87] border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <p className="text-red-600 mb-2">{error}</p>
          <button onClick={loadData} className="text-sm text-[#009b87] hover:underline">Retry</button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Team</h1>
          <p className="text-gray-500 mt-1">Manage team members and track validation progress.</p>
        </div>
        <button
          onClick={() => setShowInvite(!showInvite)}
          className="px-4 py-2 bg-[#009b87] text-white text-sm font-medium rounded-lg hover:bg-[#008775] transition-colors"
        >
          Invite Member
        </button>
      </div>

      {/* Invite panel */}
      {showInvite && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-medium text-gray-900 mb-3">Invite a stakeholder</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <input
              type="email"
              value={inviteForm.email}
              onChange={e => setInviteForm({ ...inviteForm, email: e.target.value })}
              placeholder="Email address"
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-[#009b87] focus:border-transparent"
            />
            <input
              type="text"
              value={inviteForm.first_name || ''}
              onChange={e => setInviteForm({ ...inviteForm, first_name: e.target.value })}
              placeholder="First name"
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-[#009b87] focus:border-transparent"
            />
            <input
              type="text"
              value={inviteForm.last_name || ''}
              onChange={e => setInviteForm({ ...inviteForm, last_name: e.target.value })}
              placeholder="Last name"
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-[#009b87] focus:border-transparent"
            />
          </div>
          <div className="flex items-center gap-3 mt-3">
            <select
              value={inviteForm.portal_role || 'client_user'}
              onChange={e => setInviteForm({ ...inviteForm, portal_role: e.target.value as 'client_admin' | 'client_user' })}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
            >
              <option value="client_user">User</option>
              <option value="client_admin">Admin</option>
            </select>
            <button
              onClick={handleInvite}
              disabled={inviting || !inviteForm.email}
              className="px-4 py-2 bg-[#009b87] text-white text-sm font-medium rounded-lg hover:bg-[#008775] disabled:opacity-50"
            >
              {inviting ? 'Sending...' : 'Send Invite'}
            </button>
          </div>
          {inviteResult && (
            <p className={`text-sm mt-2 ${inviteResult.startsWith('Error') ? 'text-red-600' : 'text-green-600'}`}>
              {inviteResult}
            </p>
          )}
        </div>
      )}

      {/* Overall progress */}
      {progress && progress.total_assignments > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-gray-500 uppercase tracking-wide">
              Overall Validation Progress
            </span>
            <span className="text-2xl font-bold text-[#009b87]">
              {progress.completion_percentage}%
            </span>
          </div>
          <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-[#009b87] rounded-full transition-all"
              style={{ width: `${progress.completion_percentage}%` }}
            />
          </div>
          <div className="flex items-center gap-4 mt-3 text-sm text-gray-500">
            <span>{progress.completed} completed</span>
            <span>{progress.in_progress} in progress</span>
            <span>{progress.pending} pending</span>
          </div>
        </div>
      )}

      {/* Team members */}
      <div className="space-y-3">
        <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide">
          Members ({members.length})
        </h2>

        {members.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
            <p className="text-gray-500">No team members yet. Invite stakeholders to get started.</p>
          </div>
        ) : (
          members.map(member => {
            const pct = member.total_assignments > 0
              ? Math.round((member.completed_assignments / member.total_assignments) * 100)
              : 0
            const displayName = [member.first_name, member.last_name].filter(Boolean).join(' ') || member.email

            return (
              <div key={member.user_id} className="bg-white rounded-xl border border-gray-200 p-5">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-gray-900">{displayName}</h3>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        member.portal_role === 'client_admin'
                          ? 'bg-purple-100 text-purple-700'
                          : 'bg-gray-100 text-gray-600'
                      }`}>
                        {member.portal_role === 'client_admin' ? 'Admin' : 'User'}
                      </span>
                    </div>
                    <p className="text-sm text-gray-500">{member.email}</p>
                    {member.stakeholder_name && (
                      <p className="text-xs text-gray-400 mt-0.5">
                        Linked to: {member.stakeholder_name}
                      </p>
                    )}
                  </div>
                  <span className="text-lg font-bold text-gray-900">{pct}%</span>
                </div>

                {member.total_assignments > 0 && (
                  <>
                    <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-[#009b87] rounded-full transition-all"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <p className="text-xs text-gray-400 mt-2">
                      {member.completed_assignments}/{member.total_assignments} assignments completed
                      {member.pending_assignments > 0 && ` · ${member.pending_assignments} pending`}
                    </p>
                  </>
                )}

                {member.total_assignments === 0 && (
                  <p className="text-xs text-gray-400">No assignments yet</p>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
