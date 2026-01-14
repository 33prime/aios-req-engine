"""Database operations for organizations."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from app.core.schemas_organizations import (
    Organization,
    OrganizationCreate,
    OrganizationSummary,
    OrganizationUpdate,
    OrganizationWithRole,
    OrganizationRole,
)
from app.db.supabase_client import get_supabase as get_client


async def get_organization_by_id(org_id: UUID) -> Optional[Organization]:
    """Get an organization by ID."""
    client = get_client()
    result = (
        client.table("organizations")
        .select("*")
        .eq("id", str(org_id))
        .is_("deleted_at", "null")
        .execute()
    )
    if result.data:
        return Organization(**result.data[0])
    return None


async def get_organization_by_slug(slug: str) -> Optional[Organization]:
    """Get an organization by slug."""
    client = get_client()
    result = (
        client.table("organizations")
        .select("*")
        .eq("slug", slug)
        .is_("deleted_at", "null")
        .execute()
    )
    if result.data:
        return Organization(**result.data[0])
    return None


async def create_organization(
    data: OrganizationCreate,
    created_by_user_id: UUID,
) -> Organization:
    """Create a new organization."""
    client = get_client()
    org_data = {
        "name": data.name,
        "created_by_user_id": str(created_by_user_id),
        "logo_url": data.logo_url,
        "settings": data.settings,
    }
    # Only include slug if provided (otherwise DB trigger generates it)
    if data.slug:
        org_data["slug"] = data.slug

    result = client.table("organizations").insert(org_data).execute()
    return Organization(**result.data[0])


async def update_organization(
    org_id: UUID,
    data: OrganizationUpdate,
) -> Optional[Organization]:
    """Update an organization."""
    client = get_client()
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update_data:
        return await get_organization_by_id(org_id)

    result = (
        client.table("organizations")
        .update(update_data)
        .eq("id", str(org_id))
        .execute()
    )
    if result.data:
        return Organization(**result.data[0])
    return None


async def archive_organization(org_id: UUID) -> Optional[Organization]:
    """Archive an organization (soft delete)."""
    client = get_client()
    result = (
        client.table("organizations")
        .update({"archived_at": datetime.utcnow().isoformat()})
        .eq("id", str(org_id))
        .execute()
    )
    if result.data:
        return Organization(**result.data[0])
    return None


async def delete_organization(
    org_id: UUID,
    deleted_by_user_id: UUID,
) -> Optional[Organization]:
    """Soft delete an organization."""
    client = get_client()
    result = (
        client.table("organizations")
        .update({
            "deleted_at": datetime.utcnow().isoformat(),
            "deleted_by_user_id": str(deleted_by_user_id),
        })
        .eq("id", str(org_id))
        .execute()
    )
    if result.data:
        return Organization(**result.data[0])
    return None


async def list_user_organizations(user_id: UUID) -> list[OrganizationWithRole]:
    """List all organizations a user is a member of, with their role."""
    client = get_client()

    # Query organization_members joined with organizations
    result = (
        client.table("organization_members")
        .select("organization_role, organizations(*)")
        .eq("user_id", str(user_id))
        .execute()
    )

    orgs = []
    for row in result.data:
        if row.get("organizations") and not row["organizations"].get("deleted_at"):
            org_data = row["organizations"]
            org_data["current_user_role"] = row["organization_role"]
            orgs.append(OrganizationWithRole(**org_data))

    return orgs


async def list_organizations(
    limit: int = 100,
    offset: int = 0,
    include_archived: bool = False,
) -> list[Organization]:
    """List all organizations."""
    client = get_client()
    query = (
        client.table("organizations")
        .select("*")
        .is_("deleted_at", "null")
    )

    if not include_archived:
        query = query.is_("archived_at", "null")

    query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
    result = query.execute()

    return [Organization(**row) for row in result.data]


async def get_organization_summary(org_id: UUID) -> Optional[OrganizationSummary]:
    """Get organization summary with member and project counts."""
    client = get_client()

    # Get organization
    org_result = (
        client.table("organizations")
        .select("*")
        .eq("id", str(org_id))
        .is_("deleted_at", "null")
        .execute()
    )

    if not org_result.data:
        return None

    org = org_result.data[0]

    # Get member count
    member_result = (
        client.table("organization_members")
        .select("id", count="exact")
        .eq("organization_id", str(org_id))
        .execute()
    )
    member_count = member_result.count or 0

    # Get project count
    project_result = (
        client.table("projects")
        .select("id", count="exact")
        .eq("organization_id", str(org_id))
        .execute()
    )
    project_count = project_result.count or 0

    return OrganizationSummary(
        id=org["id"],
        name=org["name"],
        slug=org.get("slug"),
        logo_url=org.get("logo_url"),
        member_count=member_count,
        project_count=project_count,
        created_at=org["created_at"],
    )
