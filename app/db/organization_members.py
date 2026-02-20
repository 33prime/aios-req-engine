"""Database operations for organization members."""

from typing import Optional
from uuid import UUID

from app.core.schemas_organizations import (
    OrganizationMember,
    OrganizationMemberCreate,
    OrganizationMemberPublic,
    OrganizationMemberWithUser,
    OrganizationRole,
)
from app.db.supabase_client import get_supabase as get_client


async def get_member(
    organization_id: UUID,
    user_id: UUID,
) -> Optional[OrganizationMember]:
    """Get a specific organization member."""
    client = get_client()
    result = (
        client.table("organization_members")
        .select("*")
        .eq("organization_id", str(organization_id))
        .eq("user_id", str(user_id))
        .execute()
    )
    if result.data:
        return OrganizationMember(**result.data[0])
    return None


async def get_member_by_id(member_id: UUID) -> Optional[OrganizationMember]:
    """Get a member by their membership ID."""
    client = get_client()
    result = (
        client.table("organization_members")
        .select("*")
        .eq("id", str(member_id))
        .execute()
    )
    if result.data:
        return OrganizationMember(**result.data[0])
    return None


async def add_member(
    organization_id: UUID,
    user_id: UUID,
    role: OrganizationRole,
    invited_by_user_id: Optional[UUID] = None,
) -> OrganizationMember:
    """Add a member to an organization."""
    client = get_client()
    member_data = {
        "organization_id": str(organization_id),
        "user_id": str(user_id),
        "organization_role": role.value,
    }
    if invited_by_user_id:
        member_data["invited_by_user_id"] = str(invited_by_user_id)

    result = client.table("organization_members").insert(member_data).execute()
    return OrganizationMember(**result.data[0])


async def update_member_role(
    organization_id: UUID,
    user_id: UUID,
    new_role: OrganizationRole,
) -> Optional[OrganizationMember]:
    """Update a member's role."""
    client = get_client()
    result = (
        client.table("organization_members")
        .update({"organization_role": new_role.value})
        .eq("organization_id", str(organization_id))
        .eq("user_id", str(user_id))
        .execute()
    )
    if result.data:
        return OrganizationMember(**result.data[0])
    return None


async def remove_member(
    organization_id: UUID,
    user_id: UUID,
) -> bool:
    """Remove a member from an organization."""
    client = get_client()
    result = (
        client.table("organization_members")
        .delete()
        .eq("organization_id", str(organization_id))
        .eq("user_id", str(user_id))
        .execute()
    )
    return len(result.data) > 0


async def list_members(
    organization_id: UUID,
) -> list[OrganizationMember]:
    """List all members of an organization."""
    client = get_client()
    result = (
        client.table("organization_members")
        .select("*")
        .eq("organization_id", str(organization_id))
        .order("joined_at", desc=False)
        .execute()
    )
    return [OrganizationMember(**row) for row in result.data]


async def list_members_with_users(
    organization_id: UUID,
) -> list[OrganizationMemberPublic]:
    """List all members with user details."""
    client = get_client()

    # Join with users table to get user details
    # Use FK hint to disambiguate (user_id vs invited_by_user_id both reference users)
    result = (
        client.table("organization_members")
        .select("*, users!organization_members_user_id_fkey(email, first_name, last_name, avatar_url)")
        .eq("organization_id", str(organization_id))
        .order("joined_at", desc=False)
        .execute()
    )

    members = []
    for row in result.data:
        user_data = row.pop("users", {}) or {}
        members.append(
            OrganizationMemberPublic(
                id=row["id"],
                user_id=row["user_id"],
                email=user_data.get("email", ""),
                first_name=user_data.get("first_name"),
                last_name=user_data.get("last_name"),
                photo_url=user_data.get("avatar_url"),
                organization_role=row["organization_role"],
                joined_at=row["joined_at"],
            )
        )

    return members


async def is_org_member(
    organization_id: UUID,
    user_id: UUID,
    required_role: Optional[OrganizationRole] = None,
) -> bool:
    """Check if user is a member of the organization with optional role check."""
    member = await get_member(organization_id, user_id)
    if not member:
        return False

    if required_role:
        member_role = OrganizationRole(member.organization_role)
        return member_role >= required_role

    return True


async def get_user_role(
    organization_id: UUID,
    user_id: UUID,
) -> Optional[OrganizationRole]:
    """Get user's role in an organization."""
    member = await get_member(organization_id, user_id)
    if member:
        return OrganizationRole(member.organization_role)
    return None


async def count_members(organization_id: UUID) -> int:
    """Count members in an organization."""
    client = get_client()
    result = (
        client.table("organization_members")
        .select("id", count="exact")
        .eq("organization_id", str(organization_id))
        .execute()
    )
    return result.count or 0


async def get_owners(organization_id: UUID) -> list[OrganizationMember]:
    """Get all owners of an organization."""
    client = get_client()
    result = (
        client.table("organization_members")
        .select("*")
        .eq("organization_id", str(organization_id))
        .eq("organization_role", OrganizationRole.OWNER.value)
        .execute()
    )
    return [OrganizationMember(**row) for row in result.data]


async def transfer_ownership(
    organization_id: UUID,
    current_owner_id: UUID,
    new_owner_id: UUID,
) -> tuple[Optional[OrganizationMember], Optional[OrganizationMember]]:
    """Transfer ownership from one user to another."""
    # Demote current owner to admin
    old_owner = await update_member_role(
        organization_id, current_owner_id, OrganizationRole.ADMIN
    )
    # Promote new owner
    new_owner = await update_member_role(
        organization_id, new_owner_id, OrganizationRole.OWNER
    )
    return old_owner, new_owner
