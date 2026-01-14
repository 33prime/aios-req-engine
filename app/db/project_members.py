"""Database operations for project members."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from app.core.schemas_auth import (
    MemberRole,
    ProjectMember,
    ProjectMemberCreate,
    ProjectMemberWithUser,
    User,
    UserPublic,
)
from app.db.supabase_client import get_supabase as get_client


async def get_project_member(project_id: UUID, user_id: UUID) -> Optional[ProjectMember]:
    """Get a specific project member."""
    client = get_client()
    result = (
        client.table("project_members")
        .select("*")
        .eq("project_id", str(project_id))
        .eq("user_id", str(user_id))
        .execute()
    )
    if result.data:
        return ProjectMember(**result.data[0])
    return None


async def add_project_member(
    project_id: UUID,
    user_id: UUID,
    role: MemberRole,
    invited_by: Optional[UUID] = None,
) -> ProjectMember:
    """Add a member to a project."""
    client = get_client()
    member_data = {
        "project_id": str(project_id),
        "user_id": str(user_id),
        "role": role.value,
        "invited_by": str(invited_by) if invited_by else None,
    }
    result = client.table("project_members").insert(member_data).execute()
    return ProjectMember(**result.data[0])


async def remove_project_member(project_id: UUID, user_id: UUID) -> bool:
    """Remove a member from a project."""
    client = get_client()
    result = (
        client.table("project_members")
        .delete()
        .eq("project_id", str(project_id))
        .eq("user_id", str(user_id))
        .execute()
    )
    return len(result.data) > 0


async def accept_project_invitation(project_id: UUID, user_id: UUID) -> Optional[ProjectMember]:
    """Mark a project invitation as accepted."""
    client = get_client()
    result = (
        client.table("project_members")
        .update({"accepted_at": datetime.utcnow().isoformat()})
        .eq("project_id", str(project_id))
        .eq("user_id", str(user_id))
        .execute()
    )
    if result.data:
        return ProjectMember(**result.data[0])
    return None


async def list_project_members(
    project_id: UUID,
    role: Optional[MemberRole] = None,
) -> list[ProjectMember]:
    """List all members of a project."""
    client = get_client()
    query = client.table("project_members").select("*").eq("project_id", str(project_id))

    if role:
        query = query.eq("role", role.value)

    result = query.order("invited_at", desc=False).execute()
    return [ProjectMember(**row) for row in result.data]


async def list_project_members_with_users(
    project_id: UUID,
    role: Optional[MemberRole] = None,
) -> list[ProjectMemberWithUser]:
    """List project members with user details."""
    client = get_client()

    # Join with users table - specify the foreign key explicitly to avoid ambiguity
    # (project_members has both user_id and invited_by referencing users)
    query = (
        client.table("project_members")
        .select("*, users!project_members_user_id_fkey(*)")
        .eq("project_id", str(project_id))
    )

    if role:
        query = query.eq("role", role.value)

    result = query.order("invited_at", desc=False).execute()

    members = []
    for row in result.data:
        user_data = row.pop("users")
        member = ProjectMember(**row)
        user = UserPublic(**user_data)
        members.append(
            ProjectMemberWithUser(
                **member.model_dump(),
                user=user,
            )
        )
    return members


async def list_user_projects(
    user_id: UUID,
    role: Optional[MemberRole] = None,
) -> list[UUID]:
    """List all project IDs a user is a member of."""
    client = get_client()
    query = client.table("project_members").select("project_id").eq("user_id", str(user_id))

    if role:
        query = query.eq("role", role.value)

    result = query.execute()
    return [UUID(row["project_id"]) for row in result.data]


async def is_project_member(
    project_id: UUID,
    user_id: UUID,
    required_role: Optional[MemberRole] = None,
) -> bool:
    """Check if a user is a member of a project."""
    member = await get_project_member(project_id, user_id)
    if not member:
        return False
    if required_role and member.role != required_role:
        return False
    return True


async def get_project_client(project_id: UUID) -> Optional[ProjectMember]:
    """Get the client member of a project (assumes one client per project)."""
    members = await list_project_members(project_id, role=MemberRole.CLIENT)
    return members[0] if members else None


async def get_project_consultant(project_id: UUID) -> Optional[ProjectMember]:
    """Get the consultant member of a project."""
    members = await list_project_members(project_id, role=MemberRole.CONSULTANT)
    return members[0] if members else None
