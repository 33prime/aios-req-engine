'use client'

import { useState } from 'react'
import { Users, UserPlus, Trash2, Loader, ChevronDown } from 'lucide-react'
import { updateMemberRole, removeOrganizationMember } from '@/lib/api'
import type { OrganizationMemberPublic, OrganizationRole } from '@/types/api'

interface TeamMembersCardProps {
  members: OrganizationMemberPublic[]
  currentUserId: string
  organizationId: string
  userRole: OrganizationRole
  onInviteClick?: () => void
  onMembersChange?: () => void
}

export default function TeamMembersCard({
  members,
  currentUserId,
  organizationId,
  userRole,
  onInviteClick,
  onMembersChange,
}: TeamMembersCardProps) {
  const [loadingMemberId, setLoadingMemberId] = useState<string | null>(null)
  const [openRoleDropdown, setOpenRoleDropdown] = useState<string | null>(null)

  const canManageMembers = userRole === 'Owner' || userRole === 'Admin'

  const getInitials = (member: OrganizationMemberPublic) => {
    if (member.first_name && member.last_name) {
      return `${member.first_name[0]}${member.last_name[0]}`.toUpperCase()
    }
    if (member.first_name) {
      return member.first_name[0].toUpperCase()
    }
    return member.email[0].toUpperCase()
  }

  const getDisplayName = (member: OrganizationMemberPublic) => {
    if (member.first_name && member.last_name) {
      return `${member.first_name} ${member.last_name}`
    }
    if (member.first_name) {
      return member.first_name
    }
    return member.email.split('@')[0]
  }

  const getRoleBadgeColor = (role: OrganizationRole) => {
    switch (role) {
      case 'Owner':
        return 'bg-emerald-100 text-emerald-700'
      case 'Admin':
        return 'bg-blue-100 text-blue-700'
      case 'Member':
        return 'bg-zinc-100 text-zinc-700'
      default:
        return 'bg-zinc-100 text-zinc-700'
    }
  }

  const handleRoleChange = async (memberId: string, userId: string, newRole: OrganizationRole) => {
    setLoadingMemberId(memberId)
    setOpenRoleDropdown(null)
    try {
      await updateMemberRole(organizationId, userId, newRole)
      onMembersChange?.()
    } catch (error) {
      console.error('Failed to update role:', error)
    } finally {
      setLoadingMemberId(null)
    }
  }

  const handleRemoveMember = async (userId: string) => {
    if (!confirm('Are you sure you want to remove this member?')) return

    setLoadingMemberId(userId)
    try {
      await removeOrganizationMember(organizationId, userId)
      onMembersChange?.()
    } catch (error) {
      console.error('Failed to remove member:', error)
    } finally {
      setLoadingMemberId(null)
    }
  }

  const canChangeRole = (member: OrganizationMemberPublic) => {
    if (member.user_id === currentUserId) return false
    if (userRole === 'Owner') return true
    if (userRole === 'Admin' && member.organization_role === 'Member') return true
    return false
  }

  const canRemove = (member: OrganizationMemberPublic) => {
    if (member.user_id === currentUserId) return false
    if (userRole === 'Owner') return member.organization_role !== 'Owner'
    if (userRole === 'Admin') return member.organization_role === 'Member'
    return false
  }

  return (
    <div className="rounded-xl border border-zinc-200 bg-white shadow-sm p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-4">
          <div className="p-1.5 rounded-full bg-emerald-600/10 text-emerald-600">
            <Users className="w-4 h-4" />
          </div>
          <p className="text-[13px] text-zinc-800" style={{ fontWeight: '600' }}>
            Team Members ({members.length})
          </p>
        </div>
        {canManageMembers && onInviteClick && (
          <button
            onClick={onInviteClick}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors text-[12px] font-medium"
          >
            <UserPlus className="w-3.5 h-3.5" />
            Invite Member
          </button>
        )}
      </div>

      <div className="space-y-2">
        {members.map((member) => (
          <div
            key={member.id}
            className="flex items-center justify-between p-3 border border-zinc-200 rounded-lg hover:bg-zinc-50 transition-colors"
          >
            <div className="flex items-center gap-3">
              {member.photo_url ? (
                <img
                  src={member.photo_url}
                  alt={getDisplayName(member)}
                  className="w-8 h-8 rounded-full object-cover"
                />
              ) : (
                <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center">
                  <span className="text-[12px] font-semibold text-emerald-700">
                    {getInitials(member)}
                  </span>
                </div>
              )}
              <div>
                <p className="text-[13px] font-medium text-zinc-900">
                  {getDisplayName(member)}
                  {member.user_id === currentUserId && (
                    <span className="text-zinc-500 font-normal ml-1">(You)</span>
                  )}
                </p>
                <p className="text-[12px] text-zinc-600">{member.email}</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {loadingMemberId === member.id || loadingMemberId === member.user_id ? (
                <Loader className="w-4 h-4 animate-spin text-zinc-400" />
              ) : (
                <>
                  {canChangeRole(member) ? (
                    <div className="relative">
                      <button
                        onClick={() => setOpenRoleDropdown(openRoleDropdown === member.id ? null : member.id)}
                        className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium ${getRoleBadgeColor(member.organization_role)}`}
                      >
                        {member.organization_role}
                        <ChevronDown className="w-3 h-3" />
                      </button>
                      {openRoleDropdown === member.id && (
                        <div className="absolute right-0 top-full mt-1 bg-white rounded-lg shadow-lg border border-zinc-200 py-1 z-10 min-w-[100px]">
                          {(['Owner', 'Admin', 'Member'] as OrganizationRole[])
                            .filter(role => {
                              if (userRole === 'Admin') return role !== 'Owner'
                              return true
                            })
                            .map((role) => (
                              <button
                                key={role}
                                onClick={() => handleRoleChange(member.id, member.user_id, role)}
                                className={`w-full text-left px-3 py-1.5 text-[12px] hover:bg-zinc-50 ${
                                  member.organization_role === role ? 'font-medium text-emerald-600' : 'text-zinc-700'
                                }`}
                              >
                                {role}
                              </button>
                            ))}
                        </div>
                      )}
                    </div>
                  ) : (
                    <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${getRoleBadgeColor(member.organization_role)}`}>
                      {member.organization_role}
                    </span>
                  )}

                  {canRemove(member) && (
                    <button
                      onClick={() => handleRemoveMember(member.user_id)}
                      className="p-1 hover:bg-red-50 rounded text-zinc-400 hover:text-red-600 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </>
              )}
            </div>
          </div>
        ))}

        {members.length === 0 && (
          <div className="text-center py-8">
            <Users className="w-8 h-8 text-zinc-300 mx-auto mb-2" />
            <p className="text-[13px] text-zinc-500">No team members yet</p>
            {canManageMembers && (
              <button
                onClick={onInviteClick}
                className="mt-2 text-[13px] text-emerald-600 hover:text-emerald-700"
              >
                Invite your first member
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
