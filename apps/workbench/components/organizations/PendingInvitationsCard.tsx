'use client'

import { useState } from 'react'
import { Clock, Mail, XCircle, Loader } from 'lucide-react'
import { cancelInvitation } from '@/lib/api'
import { formatDateShort } from '@/lib/date-utils'
import type { Invitation, OrganizationRole } from '@/types/api'

interface PendingInvitationsCardProps {
  invitations: Invitation[]
  organizationId: string
  userRole: OrganizationRole
  onInvitationsChange?: () => void
}

export default function PendingInvitationsCard({
  invitations,
  organizationId,
  userRole,
  onInvitationsChange,
}: PendingInvitationsCardProps) {
  const [cancellingId, setCancellingId] = useState<string | null>(null)

  const canManageInvitations = userRole === 'Owner' || userRole === 'Admin'

  const isExpired = (invitation: Invitation) => {
    return new Date(invitation.expires_at) < new Date() || invitation.status === 'expired'
  }

  const handleCancel = async (invitationId: string) => {
    if (!confirm('Are you sure you want to cancel this invitation?')) return

    setCancellingId(invitationId)
    try {
      await cancelInvitation(organizationId, invitationId)
      onInvitationsChange?.()
    } catch (error) {
      console.error('Failed to cancel invitation:', error)
    } finally {
      setCancellingId(null)
    }
  }

  const getRoleBadgeColor = (role: OrganizationRole) => {
    switch (role) {
      case 'Admin':
        return 'bg-blue-100 text-brand-primary-hover'
      case 'Member':
        return 'bg-zinc-100 text-zinc-700'
      default:
        return 'bg-zinc-100 text-zinc-700'
    }
  }

  const pendingInvitations = invitations.filter(i => i.status === 'pending')

  if (pendingInvitations.length === 0) {
    return null
  }

  return (
    <div className="rounded-xl border border-zinc-200 bg-white shadow-sm p-6">
      <div className="flex items-center space-x-4 mb-6">
        <div className="p-1.5 rounded-full bg-amber-100 text-amber-600">
          <Clock className="w-4 h-4" />
        </div>
        <p className="text-[13px] text-zinc-800" style={{ fontWeight: '600' }}>
          Pending Invitations ({pendingInvitations.length})
        </p>
      </div>

      <div className="space-y-2">
        {pendingInvitations.map((invitation) => {
          const expired = isExpired(invitation)

          return (
            <div
              key={invitation.id}
              className={`flex items-center justify-between p-3 border rounded-lg transition-colors ${
                expired
                  ? 'bg-red-50 border-red-200'
                  : 'border-zinc-200 hover:bg-zinc-50'
              }`}
            >
              <div className="flex items-center gap-3">
                <div className={`p-1.5 rounded-full ${expired ? 'bg-red-100' : 'bg-zinc-100'}`}>
                  <Mail className={`w-3.5 h-3.5 ${expired ? 'text-red-600' : 'text-zinc-500'}`} />
                </div>
                <div>
                  <p className={`text-[13px] font-medium ${expired ? 'text-red-800' : 'text-zinc-900'}`}>
                    {invitation.email}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[11px] text-zinc-500">
                      Sent {formatDateShort(invitation.created_at)}
                    </span>
                    <span className="text-zinc-300">·</span>
                    <span className={`text-[11px] ${expired ? 'text-red-600' : 'text-zinc-500'}`}>
                      {expired ? 'Expired' : `Expires ${formatDateShort(invitation.expires_at)}`}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${getRoleBadgeColor(invitation.organization_role)}`}>
                  {invitation.organization_role}
                </span>

                {canManageInvitations && (
                  cancellingId === invitation.id ? (
                    <Loader className="w-4 h-4 animate-spin text-zinc-400" />
                  ) : (
                    <button
                      onClick={() => handleCancel(invitation.id)}
                      className="p-1 hover:bg-red-50 rounded text-zinc-400 hover:text-red-600 transition-colors"
                      title="Cancel invitation"
                    >
                      <XCircle className="w-4 h-4" />
                    </button>
                  )
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
