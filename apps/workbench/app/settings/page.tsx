'use client'

import { useEffect, useState, useCallback } from 'react'
import { Building2, User, Loader } from 'lucide-react'
import { useRouter } from 'next/navigation'
import {
  OrganizationDetailsCard,
  TeamMembersCard,
  PendingInvitationsCard,
  InviteMemberModal,
} from '@/components/organizations'
import { ProfileTab } from '@/components/profile'
import { useAuth } from '@/components/auth/AuthProvider'
import {
  listOrganizations,
  listOrganizationMembers,
  listInvitations,
  getCurrentOrganization,
  setCurrentOrganization,
} from '@/lib/api'
import { AppSidebar } from '@/components/workspace/AppSidebar'
import type {
  OrganizationWithRole,
  OrganizationMemberPublic,
  Invitation,
} from '@/types/api'

export default function SettingsPage() {
  const router = useRouter()
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState<'profile' | 'organization'>('profile')
  const [isLoading, setIsLoading] = useState(true)
  const [organization, setOrganization] = useState<OrganizationWithRole | null>(null)
  const [members, setMembers] = useState<OrganizationMemberPublic[]>([])
  const [invitations, setInvitations] = useState<Invitation[]>([])
  const [showInviteModal, setShowInviteModal] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  const currentUserId = user?.id || ''

  const loadOrganizationData = useCallback(async () => {
    try {
      // Get organizations and find current one
      const orgs = await listOrganizations()

      let currentOrgId = getCurrentOrganization()
      if (!currentOrgId && orgs.length > 0) {
        currentOrgId = orgs[0].id
        setCurrentOrganization(currentOrgId)
        localStorage.setItem('currentOrganizationId', currentOrgId)
      }

      const currentOrg = orgs.find(o => o.id === currentOrgId) || orgs[0]
      setOrganization(currentOrg || null)

      if (currentOrg) {
        // Load members and invitations
        const [membersData, invitationsData] = await Promise.all([
          listOrganizationMembers(currentOrg.id),
          listInvitations(currentOrg.id).catch(() => []),
        ])
        setMembers(membersData)
        setInvitations(invitationsData)
      }
    } catch (error) {
      console.error('Failed to load organization data:', error)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadOrganizationData()
  }, [loadOrganizationData])

  useEffect(() => {
    const handleOrgChange = () => {
      setIsLoading(true)
      loadOrganizationData()
    }

    window.addEventListener('organization-changed', handleOrgChange)
    return () => window.removeEventListener('organization-changed', handleOrgChange)
  }, [loadOrganizationData])

  const handleInviteSuccess = () => {
    loadOrganizationData()
  }

  const sidebarWidth = sidebarCollapsed ? 64 : 224

  if (isLoading) {
    return (
      <>
        <AppSidebar
          isCollapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
        <div
          className="min-h-screen bg-zinc-50 flex items-center justify-center transition-all duration-300"
          style={{ marginLeft: sidebarWidth }}
        >
          <div className="flex items-center gap-2 text-zinc-500">
            <Loader className="w-5 h-5 animate-spin" />
            <span className="text-[13px]">Loading settings...</span>
          </div>
        </div>
      </>
    )
  }

  return (
    <>
      <AppSidebar
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      <div
        className="min-h-screen bg-zinc-50 transition-all duration-300"
        style={{ marginLeft: sidebarWidth }}
      >
        <div className="max-w-4xl mx-auto px-4 py-8">
          <div className="mb-8">
            <h1 className="text-[16px] font-semibold text-zinc-900">Settings</h1>
            <p className="text-[13px] text-zinc-500">Manage your profile and organization</p>
          </div>

          {/* Tab Navigation */}
          <div className="border-b border-zinc-200 mb-6">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab('profile')}
                className={`flex items-center gap-2 py-3 px-1 border-b-2 text-[13px] font-medium transition-colors ${
                  activeTab === 'profile'
                    ? 'border-emerald-600 text-emerald-600'
                    : 'border-transparent text-zinc-500 hover:text-zinc-700 hover:border-zinc-300'
                }`}
              >
                <User className="w-4 h-4" />
                Profile
              </button>
              <button
                onClick={() => setActiveTab('organization')}
                className={`flex items-center gap-2 py-3 px-1 border-b-2 text-[13px] font-medium transition-colors ${
                  activeTab === 'organization'
                    ? 'border-emerald-600 text-emerald-600'
                    : 'border-transparent text-zinc-500 hover:text-zinc-700 hover:border-zinc-300'
                }`}
              >
                <Building2 className="w-4 h-4" />
                Organization
              </button>
            </nav>
          </div>

          {/* Content */}
          <div className="space-y-6">
              {activeTab === 'organization' && (
                <>
                  {organization ? (
                    <>
                      <OrganizationDetailsCard
                        organization={organization}
                        userRole={organization.current_user_role}
                        onUpdate={(updated) => {
                          setOrganization({ ...updated, current_user_role: organization.current_user_role })
                        }}
                      />

                      <TeamMembersCard
                        members={members}
                        currentUserId={currentUserId}
                        organizationId={organization.id}
                        userRole={organization.current_user_role}
                        onInviteClick={() => setShowInviteModal(true)}
                        onMembersChange={loadOrganizationData}
                      />

                      <PendingInvitationsCard
                        invitations={invitations}
                        organizationId={organization.id}
                        userRole={organization.current_user_role}
                        onInvitationsChange={loadOrganizationData}
                      />

                      <InviteMemberModal
                        organizationId={organization.id}
                        organizationName={organization.name}
                        isOpen={showInviteModal}
                        onClose={() => setShowInviteModal(false)}
                        onSuccess={handleInviteSuccess}
                      />
                    </>
                  ) : (
                    <div className="rounded-xl border border-zinc-200 bg-white shadow-sm p-8 text-center">
                      <Building2 className="w-10 h-10 text-zinc-300 mx-auto mb-4" />
                      <h3 className="text-[14px] font-semibold text-zinc-900 mb-2">
                        No Organization
                      </h3>
                      <p className="text-[13px] text-zinc-600 mb-4">
                        Create an organization to collaborate with your team.
                      </p>
                    </div>
                  )}
                </>
              )}

              {activeTab === 'profile' && (
                <ProfileTab onLogout={() => router.push('/auth/login')} />
              )}
          </div>
        </div>
      </div>
    </>
  )
}
