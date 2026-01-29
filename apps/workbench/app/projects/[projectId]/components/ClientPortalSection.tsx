'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  Users,
  ExternalLink,
  UserPlus,
  Trash2,
  RefreshCw,
  CheckCircle,
  Clock,
  AlertCircle,
} from 'lucide-react'
import * as api from '@/lib/api'

interface ClientPortalSectionProps {
  projectId: string
  projectName: string
  onPhaseChange?: () => void
}

export default function ClientPortalSection({
  projectId,
  projectName,
  onPhaseChange,
}: ClientPortalSectionProps) {
  const [portalEnabled, setPortalEnabled] = useState(false)
  const [portalPhase, setPortalPhase] = useState<string>('pre_call')
  const [collaborationPhase, setCollaborationPhase] = useState<string>('pre_discovery')
  const [members, setMembers] = useState<api.ProjectMember[]>([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [showInviteModal, setShowInviteModal] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      // Load project details to get portal status
      const project = await api.getProjectDetails(projectId)
      setPortalEnabled(project.portal_enabled || false)
      setPortalPhase(project.portal_phase || 'pre_call')
      setCollaborationPhase(project.collaboration_phase || 'pre_discovery')

      // Load members
      try {
        const membersData = await api.getProjectMembers(projectId)
        setMembers(membersData.members.filter((m) => m.role === 'client'))
      } catch {
        // Members endpoint may not exist yet
        setMembers([])
      }
    } catch (err) {
      console.error('Failed to load portal data:', err)
      setError('Failed to load portal data')
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleEnablePortal = async () => {
    try {
      setActionLoading('enable')
      await api.updatePortalConfig(projectId, { portal_enabled: true })
      setPortalEnabled(true)
    } catch (err) {
      console.error('Failed to enable portal:', err)
      setError('Failed to enable portal')
    } finally {
      setActionLoading(null)
    }
  }

  const handleDisablePortal = async () => {
    try {
      setActionLoading('disable')
      await api.updatePortalConfig(projectId, { portal_enabled: false })
      setPortalEnabled(false)
    } catch (err) {
      console.error('Failed to disable portal:', err)
      setError('Failed to disable portal')
    } finally {
      setActionLoading(null)
    }
  }

  const handleAdvancePhase = async () => {
    try {
      setActionLoading('advance')

      // 1. Create a Discovery Call touchpoint
      const touchpoint = await api.createTouchpoint(projectId, {
        type: 'discovery_call',
        title: 'Discovery Call',
        description: 'Initial discovery call with client',
      })

      // 2. Mark it as completed (outcomes are numeric stats)
      await api.completeTouchpoint(projectId, touchpoint.id, {})

      // 3. Update portal phase to post_call (if not already)
      if (portalPhase !== 'post_call') {
        await api.updatePortalConfig(projectId, { portal_phase: 'post_call' })
      }

      // 4. Advance collaboration phase to validation
      await api.setCollaborationPhase(projectId, 'validation')

      setPortalPhase('post_call')
      setCollaborationPhase('validation')
      // Notify parent to refresh
      onPhaseChange?.()
    } catch (err) {
      console.error('Failed to advance phase:', err)
      setError('Failed to advance phase')
    } finally {
      setActionLoading(null)
    }
  }

  const handleRemoveMember = async (userId: string) => {
    try {
      setActionLoading(`remove-${userId}`)
      await api.removeProjectMember(projectId, userId)
      setMembers((prev) => prev.filter((m) => m.user_id !== userId))
    } catch (err) {
      console.error('Failed to remove member:', err)
      setError('Failed to remove member')
    } finally {
      setActionLoading(null)
    }
  }

  const handleResendInvite = async (userId: string) => {
    try {
      setActionLoading(`resend-${userId}`)
      await api.resendInvite(projectId, userId)
    } catch (err) {
      console.error('Failed to resend invite:', err)
      setError('Failed to resend invite')
    } finally {
      setActionLoading(null)
    }
  }

  const clientPortalUrl = `http://localhost:3001/${projectId}`

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="flex items-center gap-2 text-gray-500">
          <RefreshCw className="w-4 h-4 animate-spin" />
          Loading portal data...
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Error message */}
      {error && (
        <div className="p-3 bg-red-50 rounded-lg flex items-center gap-2 text-sm text-red-700">
          <AlertCircle className="w-4 h-4" />
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-auto text-red-500 hover:text-red-700"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Portal Status */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-gray-700">Status:</span>
            {portalEnabled ? (
              <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-[#009b87]/10 text-[#009b87]">
                <CheckCircle className="w-3 h-3" />
                Enabled
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                <Clock className="w-3 h-3" />
                Not Enabled
              </span>
            )}
            {portalEnabled && (
              <span className="text-xs text-gray-500 capitalize">
                ({portalPhase.replace('_', ' ')})
              </span>
            )}
          </div>
          {portalEnabled ? (
            <div className="flex items-center gap-3">
              {/* Show button if: pre_call OR mixed state (post_call but still pre_discovery) */}
              {(portalPhase === 'pre_call' || (portalPhase === 'post_call' && collaborationPhase === 'pre_discovery')) && (
                <button
                  onClick={handleAdvancePhase}
                  disabled={actionLoading === 'advance'}
                  className="px-3 py-1.5 bg-[#009b87] text-white text-sm font-medium rounded-lg hover:bg-[#007a6a] disabled:opacity-50"
                >
                  {actionLoading === 'advance' ? 'Advancing...' :
                   portalPhase === 'post_call' ? 'Complete Discovery Setup' : 'Mark Discovery Complete'}
                </button>
              )}
              <a
                href={clientPortalUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-sm text-[#009b87] hover:text-[#007a6a]"
              >
                <ExternalLink className="w-4 h-4" />
                View Portal
              </a>
              <button
                onClick={handleDisablePortal}
                disabled={actionLoading === 'disable'}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                {actionLoading === 'disable' ? 'Disabling...' : 'Disable'}
              </button>
            </div>
          ) : (
            <button
              onClick={handleEnablePortal}
              disabled={actionLoading === 'enable'}
              className="px-4 py-2 bg-[#009b87] text-white text-sm font-medium rounded-lg hover:bg-[#007a6a] disabled:opacity-50"
            >
              {actionLoading === 'enable' ? 'Enabling...' : 'Enable Portal'}
            </button>
          )}
        </div>

        {portalEnabled && (
          <>
            {/* Invited Clients */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Users className="w-4 h-4 text-gray-500" />
                  <span className="text-sm font-medium text-gray-700">
                    Invited Clients ({members.length})
                  </span>
                </div>
                <button
                  onClick={() => setShowInviteModal(true)}
                  className="flex items-center gap-1 px-3 py-1.5 text-sm text-[#009b87] hover:text-[#007a6a] hover:bg-[#009b87]/10 rounded-lg transition-colors"
                >
                  <UserPlus className="w-4 h-4" />
                  Invite Client
                </button>
              </div>

              {members.length === 0 ? (
                <div className="text-sm text-gray-500 bg-gray-50 rounded-lg p-4 text-center">
                  No clients invited yet. Click "Invite Client" to add one.
                </div>
              ) : (
                <div className="space-y-2">
                  {members.map((member) => (
                    <div
                      key={member.id}
                      className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                    >
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          {member.user?.email || 'Unknown'}
                        </div>
                        {member.user?.first_name && (
                          <div className="text-xs text-gray-500">
                            {member.user.first_name} {member.user.last_name}
                          </div>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        {member.accepted_at ? (
                          <span className="text-xs text-[#009b87] flex items-center gap-1">
                            <CheckCircle className="w-3 h-3" />
                            Accepted
                          </span>
                        ) : (
                          <span className="text-xs text-gray-500 flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            Pending
                          </span>
                        )}
                        <button
                          onClick={() => handleResendInvite(member.user_id)}
                          disabled={actionLoading === `resend-${member.user_id}`}
                          className="p-1 text-gray-400 hover:text-[#009b87]"
                          title="Resend invite"
                        >
                          <RefreshCw
                            className={`w-4 h-4 ${
                              actionLoading === `resend-${member.user_id}`
                                ? 'animate-spin'
                                : ''
                            }`}
                          />
                        </button>
                        <button
                          onClick={() => handleRemoveMember(member.user_id)}
                          disabled={actionLoading === `remove-${member.user_id}`}
                          className="p-1 text-gray-400 hover:text-red-600"
                          title="Remove client"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

          </>
        )}

      {/* Invite Modal */}
      {showInviteModal && (
        <InviteClientModal
          projectId={projectId}
          projectName={projectName}
          onClose={() => setShowInviteModal(false)}
          onSuccess={(member) => {
            setMembers((prev) => [...prev, member])
            setShowInviteModal(false)
          }}
        />
      )}
    </div>
  )
}

// Invite Client Modal Component
interface InviteClientModalProps {
  projectId: string
  projectName: string
  onClose: () => void
  onSuccess: (member: api.ProjectMember) => void
}

function InviteClientModal({
  projectId,
  projectName,
  onClose,
  onSuccess,
}: InviteClientModalProps) {
  const [email, setEmail] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim()) return

    try {
      setLoading(true)
      setError(null)
      const result = await api.inviteClient(projectId, {
        email: email.trim(),
        first_name: firstName.trim() || undefined,
        last_name: lastName.trim() || undefined,
        send_email: true,
      })

      // Construct a member object from the result
      const member: api.ProjectMember = {
        id: result.project_member.id,
        user_id: result.user.id,
        role: 'client',
        invited_at: new Date().toISOString(),
        accepted_at: null,
        user: {
          id: result.user.id,
          email: result.user.email,
          first_name: result.user.first_name || firstName.trim() || null,
          last_name: result.user.last_name || lastName.trim() || null,
          company_name: null,
        },
      }

      onSuccess(member)
    } catch (err: any) {
      console.error('Failed to invite client:', err)
      setError(err.message || 'Failed to send invite')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white rounded-xl shadow-xl w-full max-w-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Invite Client to Portal
        </h3>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email Address *
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="client@example.com"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#009b87] focus:border-transparent"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                First Name
              </label>
              <input
                type="text"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                placeholder="John"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#009b87] focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Last Name
              </label>
              <input
                type="text"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                placeholder="Doe"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#009b87] focus:border-transparent"
              />
            </div>
          </div>

          {error && (
            <div className="p-3 bg-red-50 border border-red-100 rounded-lg text-sm text-red-700">
              {error}
            </div>
          )}

          <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-600">
            A magic link email will be sent to this address, allowing the client
            to access the portal for "{projectName}".
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !email.trim()}
              className="px-4 py-2 bg-[#009b87] text-white text-sm font-medium rounded-lg hover:bg-[#007a6a] disabled:opacity-50"
            >
              {loading ? 'Sending...' : 'Send Invite'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
