"""API endpoints for organization management."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header, status

from app.core.auth_middleware import AuthContext, require_auth
from app.core.schemas_organizations import (
    AcceptInvitationRequest,
    AcceptInvitationResponse,
    Invitation,
    InvitationCreate,
    InvitationWithOrg,
    Organization,
    OrganizationCreate,
    OrganizationMember,
    OrganizationMemberPublic,
    OrganizationRole,
    OrganizationSummary,
    OrganizationUpdate,
    OrganizationWithRole,
    Profile,
    ProfileUpdate,
    UpdateMemberRoleRequest,
)
from app.db.organization_invitations import (
    accept_invitation as db_accept_invitation,
    cancel_invitation,
    create_invitation,
    get_invitation_by_token,
    get_invitation_with_org,
    get_pending_invitation_for_email,
    list_pending_invitations,
)
from app.db.organization_members import (
    add_member,
    get_member,
    get_owners,
    get_user_role,
    is_org_member,
    list_members_with_users,
    remove_member,
    transfer_ownership,
    update_member_role,
)
from app.db.organizations import (
    create_organization,
    delete_organization,
    get_organization_by_id,
    get_organization_summary,
    list_user_organizations,
    update_organization,
)
from app.db.profiles import (
    get_or_create_profile,
    get_profile_by_user_id,
    update_profile,
)
from app.db.supabase_client import get_supabase as get_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/organizations", tags=["organizations"])


# ============================================================================
# Helper Dependencies
# ============================================================================


async def get_current_org_id(
    x_organization_id: Optional[str] = Header(None, alias="X-Organization-Id"),
) -> Optional[UUID]:
    """Extract organization ID from header if present."""
    if x_organization_id:
        try:
            return UUID(x_organization_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid organization ID format",
            )
    return None


async def require_org_membership(
    organization_id: UUID,
    auth: AuthContext = Depends(require_auth),
) -> tuple[AuthContext, OrganizationRole]:
    """Require user to be a member of the organization."""
    role = await get_user_role(organization_id, auth.user_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization",
        )
    return auth, role


async def require_org_admin(
    organization_id: UUID,
    auth: AuthContext = Depends(require_auth),
) -> tuple[AuthContext, OrganizationRole]:
    """Require user to be admin or owner of the organization."""
    role = await get_user_role(organization_id, auth.user_id)
    if not role or role < OrganizationRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return auth, role


async def require_org_owner(
    organization_id: UUID,
    auth: AuthContext = Depends(require_auth),
) -> tuple[AuthContext, OrganizationRole]:
    """Require user to be owner of the organization."""
    role = await get_user_role(organization_id, auth.user_id)
    if not role or role != OrganizationRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner access required",
        )
    return auth, role


# ============================================================================
# Organization CRUD
# ============================================================================


@router.get("", response_model=list[OrganizationWithRole])
async def list_organizations(
    auth: AuthContext = Depends(require_auth),
):
    """List all organizations the current user is a member of."""
    return await list_user_organizations(auth.user_id)


@router.post("", response_model=Organization)
async def create_new_organization(
    data: OrganizationCreate,
    auth: AuthContext = Depends(require_auth),
):
    """Create a new organization. The creator becomes the owner."""
    # Create the organization
    org = await create_organization(data, auth.user_id)

    # Add creator as owner
    await add_member(
        organization_id=org.id,
        user_id=auth.user_id,
        role=OrganizationRole.OWNER,
    )

    return org


@router.get("/{organization_id}", response_model=Organization)
async def get_organization(
    organization_id: UUID,
    auth: AuthContext = Depends(require_auth),
):
    """Get organization details. Requires membership."""
    # Check membership
    if not await is_org_member(organization_id, auth.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization",
        )

    org = await get_organization_by_id(organization_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    return org


@router.get("/{organization_id}/summary", response_model=OrganizationSummary)
async def get_organization_summary_endpoint(
    organization_id: UUID,
    auth: AuthContext = Depends(require_auth),
):
    """Get organization summary with counts. Requires membership."""
    if not await is_org_member(organization_id, auth.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization",
        )

    summary = await get_organization_summary(organization_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    return summary


@router.patch("/{organization_id}", response_model=Organization)
async def update_organization_endpoint(
    organization_id: UUID,
    data: OrganizationUpdate,
    auth: AuthContext = Depends(require_auth),
):
    """Update organization details. Requires admin access."""
    auth, role = await require_org_admin(organization_id, auth)

    org = await update_organization(organization_id, data)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    return org


@router.delete("/{organization_id}")
async def delete_organization_endpoint(
    organization_id: UUID,
    auth: AuthContext = Depends(require_auth),
):
    """Delete (archive) an organization. Requires owner access."""
    auth, role = await require_org_owner(organization_id, auth)

    org = await delete_organization(organization_id, auth.user_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    return {"message": "Organization deleted", "id": str(organization_id)}


# ============================================================================
# Member Management
# ============================================================================


@router.get("/{organization_id}/members", response_model=list[OrganizationMemberPublic])
async def list_organization_members(
    organization_id: UUID,
    auth: AuthContext = Depends(require_auth),
):
    """List all members of an organization. Requires membership."""
    if not await is_org_member(organization_id, auth.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization",
        )

    return await list_members_with_users(organization_id)


@router.patch("/{organization_id}/members/{user_id}", response_model=OrganizationMember)
async def update_member_role_endpoint(
    organization_id: UUID,
    user_id: UUID,
    data: UpdateMemberRoleRequest,
    auth: AuthContext = Depends(require_auth),
):
    """Update a member's role. Requires admin access."""
    auth, actor_role = await require_org_admin(organization_id, auth)

    # Can't change your own role
    if user_id == auth.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role",
        )

    # Get target member's current role
    target_role = await get_user_role(organization_id, user_id)
    if not target_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    # Only owners can promote/demote other owners or promote to owner
    if target_role == OrganizationRole.OWNER or data.organization_role == OrganizationRole.OWNER:
        if actor_role != OrganizationRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only owners can manage owner roles",
            )

    # If promoting to owner, this is a transfer
    if data.organization_role == OrganizationRole.OWNER:
        await transfer_ownership(organization_id, auth.user_id, user_id)
        return await get_member(organization_id, user_id)

    member = await update_member_role(organization_id, user_id, data.organization_role)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    return member


@router.delete("/{organization_id}/members/{user_id}")
async def remove_organization_member(
    organization_id: UUID,
    user_id: UUID,
    auth: AuthContext = Depends(require_auth),
):
    """Remove a member from an organization. Requires admin access."""
    auth, actor_role = await require_org_admin(organization_id, auth)

    # Can't remove yourself
    if user_id == auth.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove yourself. Use leave organization instead.",
        )

    # Get target member's role
    target_role = await get_user_role(organization_id, user_id)
    if not target_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    # Only owners can remove other owners
    if target_role == OrganizationRole.OWNER and actor_role != OrganizationRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can remove other owners",
        )

    success = await remove_member(organization_id, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    return {"message": "Member removed", "user_id": str(user_id)}


@router.post("/{organization_id}/leave")
async def leave_organization(
    organization_id: UUID,
    auth: AuthContext = Depends(require_auth),
):
    """Leave an organization. Owners must transfer ownership first."""
    role = await get_user_role(organization_id, auth.user_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not a member of this organization",
        )

    # Owners can't leave without transferring ownership
    if role == OrganizationRole.OWNER:
        owners = await get_owners(organization_id)
        if len(owners) == 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot leave as the only owner. Transfer ownership first or delete the organization.",
            )

    success = await remove_member(organization_id, auth.user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to leave organization",
        )

    return {"message": "Left organization", "organization_id": str(organization_id)}


# ============================================================================
# Invitation Management
# ============================================================================


@router.post("/{organization_id}/invitations", response_model=Invitation)
async def send_invitation(
    organization_id: UUID,
    data: InvitationCreate,
    auth: AuthContext = Depends(require_auth),
):
    """Send an invitation to join the organization. Requires admin access."""
    auth, role = await require_org_admin(organization_id, auth)

    # Check if user is already a member
    from app.db.users import get_user_by_email

    existing_user = await get_user_by_email(data.email)
    if existing_user:
        if await is_org_member(organization_id, existing_user.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member of this organization",
            )

    # Check for existing pending invitation
    existing_invite = await get_pending_invitation_for_email(organization_id, data.email)
    if existing_invite:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pending invitation already exists for this email",
        )

    # Can't invite as owner
    if data.organization_role == OrganizationRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot invite as owner. Invite as admin and transfer ownership later.",
        )

    invitation = await create_invitation(
        organization_id=organization_id,
        data=data,
        invited_by_user_id=auth.user_id,
    )

    return invitation


@router.get("/{organization_id}/invitations", response_model=list[Invitation])
async def list_invitations(
    organization_id: UUID,
    auth: AuthContext = Depends(require_auth),
):
    """List pending invitations for an organization. Requires admin access."""
    auth, role = await require_org_admin(organization_id, auth)
    return await list_pending_invitations(organization_id)


@router.delete("/{organization_id}/invitations/{invitation_id}")
async def cancel_invitation_endpoint(
    organization_id: UUID,
    invitation_id: UUID,
    auth: AuthContext = Depends(require_auth),
):
    """Cancel a pending invitation. Requires admin access."""
    auth, role = await require_org_admin(organization_id, auth)

    invitation = await cancel_invitation(invitation_id)
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found or already processed",
        )

    return {"message": "Invitation cancelled", "id": str(invitation_id)}


@router.get("/invitations/{token}", response_model=InvitationWithOrg)
async def get_invitation_details(
    token: str,
):
    """Get invitation details by token. Public endpoint for accept flow."""
    invitation = await get_invitation_with_org(token)
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    if invitation.is_expired:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Invitation has expired",
        )

    return invitation


@router.post("/invitations/accept", response_model=AcceptInvitationResponse)
async def accept_invitation_endpoint(
    data: AcceptInvitationRequest,
    auth: AuthContext = Depends(require_auth),
):
    """Accept an invitation and join the organization."""
    # Get invitation
    invitation = await get_invitation_by_token(data.invite_token)
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    # Check if expired
    if invitation.is_expired:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Invitation has expired",
        )

    # Check if already a member
    if await is_org_member(invitation.organization_id, auth.user_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already a member of this organization",
        )

    # Mark invitation as accepted
    await db_accept_invitation(invitation.id)

    # Add user as member
    member = await add_member(
        organization_id=invitation.organization_id,
        user_id=auth.user_id,
        role=OrganizationRole(invitation.organization_role),
        invited_by_user_id=invitation.invited_by_user_id,
    )

    # Get organization
    org = await get_organization_by_id(invitation.organization_id)

    return AcceptInvitationResponse(
        organization=org,
        member=member,
    )


# ============================================================================
# Organization Projects
# ============================================================================


@router.get("/{organization_id}/projects")
async def list_organization_projects(
    organization_id: UUID,
    auth: AuthContext = Depends(require_auth),
):
    """List all projects in an organization. Requires membership."""
    if not await is_org_member(organization_id, auth.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization",
        )

    client = get_client()
    result = (
        client.table("projects")
        .select("*")
        .eq("organization_id", str(organization_id))
        .order("created_at", desc=True)
        .execute()
    )

    return result.data


# ============================================================================
# Profile Management
# ============================================================================


@router.get("/profile/me", response_model=Profile)
async def get_my_profile(
    auth: AuthContext = Depends(require_auth),
):
    """Get the current user's profile."""
    profile = await get_profile_by_user_id(auth.user_id)
    if not profile:
        # Create profile if it doesn't exist
        profile, _ = await get_or_create_profile(
            user_id=auth.user_id,
            email=auth.user.email,
            first_name=auth.user.first_name,
            last_name=auth.user.last_name,
        )

    return profile


@router.patch("/profile/me", response_model=Profile)
async def update_my_profile(
    data: ProfileUpdate,
    auth: AuthContext = Depends(require_auth),
):
    """Update the current user's profile."""
    # Ensure profile exists
    profile = await get_profile_by_user_id(auth.user_id)
    if not profile:
        profile, _ = await get_or_create_profile(
            user_id=auth.user_id,
            email=auth.user.email,
            first_name=auth.user.first_name,
            last_name=auth.user.last_name,
        )

    updated = await update_profile(auth.user_id, data)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile",
        )

    return updated
