/**
 * ClientPortalModal Component
 *
 * Full modal for managing client portal - combines invite functionality,
 * client list with statuses, remove actions, and package summary.
 */

'use client'

import React, { useState, useEffect, useCallback } from 'react'
import {
  X,
  Mail,
  Users,
  UserPlus,
  ExternalLink,
  RefreshCw,
  Trash2,
  CheckCircle,
  Clock,
  AlertCircle,
  Copy,
  Check,
  Send,
  Package,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import * as api from '@/lib/api'

interface ClientPortalModalProps {
  projectId: string
  projectName: string
  isOpen: boolean
  onClose: () => void
  onRefresh?: () => void
}

export function ClientPortalModal({
  projectId,
  projectName,
  isOpen,
  onClose,
  onRefresh,
}: ClientPortalModalProps) {
  const [portalEnabled, setPortalEnabled] = useState(false)
  const [members, setMembers] = useState<api.ProjectMember[]>([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [showInviteForm, setShowInviteForm] = useState(false)

  // Invite form state
  const [email, setEmail] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')

  const portalUrl = `${window.location.origin}/portal/${projectId}`

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const project = await api.getProjectDetails(projectId)
      setPortalEnabled(project.portal_enabled || false)

      try {
        const membersData = await api.getProjectMembers(projectId)
        setMembers(membersData.members.filter((m) => m.role === 'client'))
      } catch {
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
    if (isOpen) {
      loadData()
    }
  }, [isOpen, loadData])

  const handleEnablePortal = async () => {
    try {
      setActionLoading('enable')
      await api.updatePortalConfig(projectId, { portal_enabled: true })
      setPortalEnabled(true)
      onRefresh?.()
    } catch (err) {
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
      onRefresh?.()
    } catch (err) {
      setError('Failed to disable portal')
    } finally {
      setActionLoading(null)
    }
  }

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim()) return

    try {
      setActionLoading('invite')
      setError(null)
      const result = await api.inviteClient(projectId, {
        email: email.trim(),
        first_name: firstName.trim() || undefined,
        last_name: lastName.trim() || undefined,
        send_email: true,
      })

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

      setMembers((prev) => [...prev, member])
      setEmail('')
      setFirstName('')
      setLastName('')
      setShowInviteForm(false)
      onRefresh?.()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to send invite')
    } finally {
      setActionLoading(null)
    }
  }

  const handleRemoveMember = async (userId: string) => {
    if (!confirm('Remove this client from the project?')) return
    try {
      setActionLoading(`remove-${userId}`)
      await api.removeProjectMember(projectId, userId)
      setMembers((prev) => prev.filter((m) => m.user_id !== userId))
      onRefresh?.()
    } catch (err) {
      setError('Failed to remove client')
    } finally {
      setActionLoading(null)
    }
  }

  const handleCopyLink = () => {
    navigator.clipboard.writeText(portalUrl)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (!isOpen) return null

  const pendingCount = members.filter((m) => !m.accepted_at).length
  const activeCount = members.filter((m) => m.accepted_at).length

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[85vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-teal-50 to-emerald-50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-[#009b87] rounded-lg flex items-center justify-center">
              <Mail className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Client Portal</h2>
              <p className="text-sm text-gray-600">{projectName}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {error}
              <button onClick={() => setError(null)} className="ml-auto text-red-500 hover:text-red-700">
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="w-6 h-6 animate-spin text-gray-400" />
            </div>
          ) : (
            <>
              {/* Portal Status */}
              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium text-gray-700">Portal Status</span>
                  {portalEnabled ? (
                    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                      <CheckCircle className="w-3 h-3" />
                      Enabled
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-gray-200 text-gray-600">
                      <Clock className="w-3 h-3" />
                      Disabled
                    </span>
                  )}
                </div>
                <button
                  onClick={portalEnabled ? handleDisablePortal : handleEnablePortal}
                  disabled={actionLoading === 'enable' || actionLoading === 'disable'}
                  className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                    portalEnabled
                      ? 'text-gray-600 hover:text-gray-800 hover:bg-gray-200'
                      : 'bg-[#009b87] text-white hover:bg-[#008775]'
                  }`}
                >
                  {actionLoading === 'enable' || actionLoading === 'disable'
                    ? 'Updating...'
                    : portalEnabled
                    ? 'Disable'
                    : 'Enable Portal'}
                </button>
              </div>

              {portalEnabled && (
                <>
                  {/* Portal Link */}
                  <div className="p-4 border border-gray-200 rounded-lg">
                    <label className="block text-sm font-medium text-gray-700 mb-2">Portal Link</label>
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        readOnly
                        value={portalUrl}
                        className="flex-1 px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-600"
                      />
                      <button
                        onClick={handleCopyLink}
                        className="px-3 py-2 text-sm text-gray-600 hover:text-gray-800 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors flex items-center gap-1"
                      >
                        {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
                        {copied ? 'Copied!' : 'Copy'}
                      </button>
                      <a
                        href={portalUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-3 py-2 text-sm text-[#009b87] hover:text-[#008775] border border-[#009b87] rounded-lg hover:bg-[#009b87]/5 transition-colors flex items-center gap-1"
                      >
                        <ExternalLink className="w-4 h-4" />
                        Open
                      </a>
                    </div>
                  </div>

                  {/* Invited Clients */}
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <Users className="w-4 h-4 text-gray-500" />
                        <span className="text-sm font-medium text-gray-900">
                          Invited Clients
                        </span>
                        <span className="text-xs text-gray-500">
                          {activeCount} active, {pendingCount} pending
                        </span>
                      </div>
                      <button
                        onClick={() => setShowInviteForm(!showInviteForm)}
                        className="flex items-center gap-1 px-3 py-1.5 text-sm text-[#009b87] hover:bg-[#009b87]/10 rounded-lg transition-colors"
                      >
                        <UserPlus className="w-4 h-4" />
                        {showInviteForm ? 'Cancel' : 'Invite'}
                      </button>
                    </div>

                    {/* Invite Form */}
                    {showInviteForm && (
                      <form onSubmit={handleInvite} className="mb-4 p-4 bg-blue-50 border border-blue-100 rounded-lg">
                        <div className="space-y-3">
                          <div>
                            <label className="block text-xs font-medium text-gray-700 mb-1">Email *</label>
                            <input
                              type="email"
                              value={email}
                              onChange={(e) => setEmail(e.target.value)}
                              placeholder="client@example.com"
                              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-[#009b87] focus:border-transparent"
                              required
                            />
                          </div>
                          <div className="grid grid-cols-2 gap-3">
                            <div>
                              <label className="block text-xs font-medium text-gray-700 mb-1">First Name</label>
                              <input
                                type="text"
                                value={firstName}
                                onChange={(e) => setFirstName(e.target.value)}
                                placeholder="John"
                                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-[#009b87] focus:border-transparent"
                              />
                            </div>
                            <div>
                              <label className="block text-xs font-medium text-gray-700 mb-1">Last Name</label>
                              <input
                                type="text"
                                value={lastName}
                                onChange={(e) => setLastName(e.target.value)}
                                placeholder="Doe"
                                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-[#009b87] focus:border-transparent"
                              />
                            </div>
                          </div>
                          <button
                            type="submit"
                            disabled={actionLoading === 'invite' || !email.trim()}
                            className="w-full px-4 py-2 bg-[#009b87] text-white text-sm font-medium rounded-lg hover:bg-[#008775] disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
                          >
                            {actionLoading === 'invite' ? (
                              <>
                                <RefreshCw className="w-4 h-4 animate-spin" />
                                Sending...
                              </>
                            ) : (
                              <>
                                <Send className="w-4 h-4" />
                                Send Invite
                              </>
                            )}
                          </button>
                        </div>
                      </form>
                    )}

                    {/* Client List */}
                    {members.length === 0 ? (
                      <div className="text-center py-8 bg-gray-50 rounded-lg">
                        <Users className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                        <p className="text-sm text-gray-500">No clients invited yet</p>
                        <button
                          onClick={() => setShowInviteForm(true)}
                          className="mt-2 text-sm text-[#009b87] hover:underline"
                        >
                          Invite your first client
                        </button>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {members.map((member) => (
                          <div
                            key={member.id}
                            className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                          >
                            <div className="flex items-center gap-3">
                              <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center text-sm font-medium text-gray-600">
                                {(member.user?.first_name?.[0] || member.user?.email?.[0] || '?').toUpperCase()}
                              </div>
                              <div>
                                <div className="text-sm font-medium text-gray-900">
                                  {member.user?.first_name && member.user?.last_name
                                    ? `${member.user.first_name} ${member.user.last_name}`
                                    : member.user?.email || 'Unknown'}
                                </div>
                                {member.user?.first_name && (
                                  <div className="text-xs text-gray-500">{member.user.email}</div>
                                )}
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              {member.accepted_at ? (
                                <span className="text-xs text-green-600 flex items-center gap-1 px-2 py-1 bg-green-50 rounded-full">
                                  <CheckCircle className="w-3 h-3" />
                                  Active
                                </span>
                              ) : (
                                <span className="text-xs text-amber-600 flex items-center gap-1 px-2 py-1 bg-amber-50 rounded-full">
                                  <Clock className="w-3 h-3" />
                                  Pending
                                </span>
                              )}
                              <button
                                onClick={() => handleRemoveMember(member.user_id)}
                                disabled={actionLoading === `remove-${member.user_id}`}
                                className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
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
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
          <button
            onClick={onClose}
            className="w-full px-4 py-2 text-sm text-gray-600 hover:text-gray-800 border border-gray-200 rounded-lg hover:bg-white transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

export default ClientPortalModal
