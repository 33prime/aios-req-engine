import { apiRequest } from './core'
import type {
  Organization,
  OrganizationWithRole,
  OrganizationCreate,
  OrganizationUpdate,
  OrganizationMember,
  OrganizationMemberPublic,
  Invitation,
  InvitationWithOrg,
  InvitationCreate,
  Profile,
  ProfileUpdate,
  OrganizationRole,
} from '../../types/api'

// ============================================
// Organization CRUD
// ============================================

export const listOrganizations = () =>
  apiRequest<OrganizationWithRole[]>('/organizations')

export const createOrganization = (data: OrganizationCreate) =>
  apiRequest<Organization>('/organizations', {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const getOrganization = (orgId: string) =>
  apiRequest<Organization>(`/organizations/${orgId}`)

export const updateOrganization = (orgId: string, data: OrganizationUpdate) =>
  apiRequest<Organization>(`/organizations/${orgId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })

// ============================================
// Organization Members
// ============================================

export const listOrganizationMembers = (orgId: string) =>
  apiRequest<OrganizationMemberPublic[]>(`/organizations/${orgId}/members`)

export const updateMemberRole = (
  orgId: string,
  userId: string,
  role: OrganizationRole
) =>
  apiRequest<OrganizationMember>(`/organizations/${orgId}/members/${userId}`, {
    method: 'PATCH',
    body: JSON.stringify({ organization_role: role }),
  })

export const removeOrganizationMember = (orgId: string, userId: string) =>
  apiRequest<{ message: string; user_id: string }>(
    `/organizations/${orgId}/members/${userId}`,
    { method: 'DELETE' }
  )

// ============================================
// Organization Invitations
// ============================================

export const sendInvitation = (orgId: string, data: InvitationCreate) =>
  apiRequest<Invitation>(`/organizations/${orgId}/invitations`, {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const listInvitations = (orgId: string) =>
  apiRequest<Invitation[]>(`/organizations/${orgId}/invitations`)

export const cancelInvitation = (orgId: string, invitationId: string) =>
  apiRequest<{ message: string; id: string }>(
    `/organizations/${orgId}/invitations/${invitationId}`,
    { method: 'DELETE' }
  )

export const getInvitationByToken = (token: string) =>
  apiRequest<InvitationWithOrg>(`/organizations/invitations/${token}`)

export const acceptInvitation = (token: string) =>
  apiRequest<{
    organization: Organization
    member: OrganizationMember
    message: string
  }>('/organizations/invitations/accept', {
    method: 'POST',
    body: JSON.stringify({ invite_token: token }),
  })

// ============================================
// Profile
// ============================================

export const getMyProfile = () =>
  apiRequest<Profile>('/organizations/profile/me')

export const updateMyProfile = (data: ProfileUpdate) =>
  apiRequest<Profile>('/organizations/profile/me', {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
