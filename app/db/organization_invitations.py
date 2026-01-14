"""Database operations for organization invitations."""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from app.core.schemas_organizations import (
    Invitation,
    InvitationCreate,
    InvitationStatus,
    InvitationWithOrg,
    OrganizationRole,
)
from app.db.supabase_client import get_supabase as get_client


async def get_invitation_by_id(invitation_id: UUID) -> Optional[Invitation]:
    """Get an invitation by ID."""
    client = get_client()
    result = (
        client.table("organization_invitations")
        .select("*")
        .eq("id", str(invitation_id))
        .execute()
    )
    if result.data:
        return Invitation(**result.data[0])
    return None


async def get_invitation_by_token(token: str) -> Optional[Invitation]:
    """Get an invitation by its invite token."""
    client = get_client()
    result = (
        client.table("organization_invitations")
        .select("*")
        .eq("invite_token", token)
        .execute()
    )
    if result.data:
        return Invitation(**result.data[0])
    return None


async def get_invitation_with_org(token: str) -> Optional[InvitationWithOrg]:
    """Get an invitation with organization details."""
    client = get_client()
    result = (
        client.table("organization_invitations")
        .select("*, organizations(name, logo_url), users(first_name, last_name)")
        .eq("invite_token", token)
        .execute()
    )

    if not result.data:
        return None

    row = result.data[0]
    org_data = row.pop("organizations", {}) or {}
    invited_by_data = row.pop("users", {}) or {}

    invited_by_name = None
    if invited_by_data.get("first_name"):
        if invited_by_data.get("last_name"):
            invited_by_name = f"{invited_by_data['first_name']} {invited_by_data['last_name']}"
        else:
            invited_by_name = invited_by_data["first_name"]

    return InvitationWithOrg(
        **row,
        organization_name=org_data.get("name", "Unknown"),
        organization_logo_url=org_data.get("logo_url"),
        invited_by_name=invited_by_name,
    )


async def create_invitation(
    organization_id: UUID,
    data: InvitationCreate,
    invited_by_user_id: UUID,
    expires_in_days: int = 7,
) -> Invitation:
    """Create a new invitation."""
    client = get_client()

    expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

    invitation_data = {
        "organization_id": str(organization_id),
        "email": data.email.lower(),
        "organization_role": data.organization_role.value,
        "invited_by_user_id": str(invited_by_user_id),
        "expires_at": expires_at.isoformat(),
    }

    result = client.table("organization_invitations").insert(invitation_data).execute()
    return Invitation(**result.data[0])


async def cancel_invitation(invitation_id: UUID) -> Optional[Invitation]:
    """Cancel a pending invitation."""
    client = get_client()
    result = (
        client.table("organization_invitations")
        .update({"status": InvitationStatus.CANCELLED.value})
        .eq("id", str(invitation_id))
        .eq("status", InvitationStatus.PENDING.value)
        .execute()
    )
    if result.data:
        return Invitation(**result.data[0])
    return None


async def accept_invitation(invitation_id: UUID) -> Optional[Invitation]:
    """Mark an invitation as accepted."""
    client = get_client()
    result = (
        client.table("organization_invitations")
        .update({
            "status": InvitationStatus.ACCEPTED.value,
            "accepted_at": datetime.utcnow().isoformat(),
        })
        .eq("id", str(invitation_id))
        .eq("status", InvitationStatus.PENDING.value)
        .execute()
    )
    if result.data:
        return Invitation(**result.data[0])
    return None


async def expire_invitation(invitation_id: UUID) -> Optional[Invitation]:
    """Mark an invitation as expired."""
    client = get_client()
    result = (
        client.table("organization_invitations")
        .update({"status": InvitationStatus.EXPIRED.value})
        .eq("id", str(invitation_id))
        .execute()
    )
    if result.data:
        return Invitation(**result.data[0])
    return None


async def list_pending_invitations(
    organization_id: UUID,
) -> list[Invitation]:
    """List all pending invitations for an organization."""
    client = get_client()
    result = (
        client.table("organization_invitations")
        .select("*")
        .eq("organization_id", str(organization_id))
        .eq("status", InvitationStatus.PENDING.value)
        .order("created_at", desc=True)
        .execute()
    )
    return [Invitation(**row) for row in result.data]


async def list_all_invitations(
    organization_id: UUID,
    include_expired: bool = False,
) -> list[Invitation]:
    """List all invitations for an organization."""
    client = get_client()
    query = (
        client.table("organization_invitations")
        .select("*")
        .eq("organization_id", str(organization_id))
    )

    if not include_expired:
        query = query.neq("status", InvitationStatus.EXPIRED.value)

    result = query.order("created_at", desc=True).execute()
    return [Invitation(**row) for row in result.data]


async def get_pending_invitation_for_email(
    organization_id: UUID,
    email: str,
) -> Optional[Invitation]:
    """Get pending invitation for a specific email in an organization."""
    client = get_client()
    result = (
        client.table("organization_invitations")
        .select("*")
        .eq("organization_id", str(organization_id))
        .eq("email", email.lower())
        .eq("status", InvitationStatus.PENDING.value)
        .execute()
    )
    if result.data:
        return Invitation(**result.data[0])
    return None


async def list_invitations_for_email(email: str) -> list[InvitationWithOrg]:
    """List all pending invitations for an email address."""
    client = get_client()
    result = (
        client.table("organization_invitations")
        .select("*, organizations(name, logo_url), users(first_name, last_name)")
        .eq("email", email.lower())
        .eq("status", InvitationStatus.PENDING.value)
        .order("created_at", desc=True)
        .execute()
    )

    invitations = []
    for row in result.data:
        org_data = row.pop("organizations", {}) or {}
        invited_by_data = row.pop("users", {}) or {}

        invited_by_name = None
        if invited_by_data.get("first_name"):
            if invited_by_data.get("last_name"):
                invited_by_name = f"{invited_by_data['first_name']} {invited_by_data['last_name']}"
            else:
                invited_by_name = invited_by_data["first_name"]

        invitations.append(
            InvitationWithOrg(
                **row,
                organization_name=org_data.get("name", "Unknown"),
                organization_logo_url=org_data.get("logo_url"),
                invited_by_name=invited_by_name,
            )
        )

    return invitations


async def delete_invitation(invitation_id: UUID) -> bool:
    """Hard delete an invitation."""
    client = get_client()
    result = (
        client.table("organization_invitations")
        .delete()
        .eq("id", str(invitation_id))
        .execute()
    )
    return len(result.data) > 0


async def expire_old_invitations() -> int:
    """Expire all invitations past their expiry date. Returns count expired."""
    client = get_client()
    result = (
        client.table("organization_invitations")
        .update({"status": InvitationStatus.EXPIRED.value})
        .eq("status", InvitationStatus.PENDING.value)
        .lt("expires_at", datetime.utcnow().isoformat())
        .execute()
    )
    return len(result.data)
