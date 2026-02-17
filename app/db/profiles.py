"""Database operations for user profiles."""

from typing import Optional
from uuid import UUID

from app.core.schemas_organizations import (
    AvailabilityStatus,
    PlatformRole,
    Profile,
    ProfileCreate,
    ProfileUpdate,
)
from app.db.supabase_client import get_supabase as get_client


async def get_profile_by_user_id(user_id: UUID) -> Optional[Profile]:
    """Get a profile by user ID."""
    client = get_client()
    result = (
        client.table("profiles")
        .select("*")
        .eq("user_id", str(user_id))
        .execute()
    )
    if result.data:
        return Profile(**result.data[0])
    return None


async def get_profile_by_id(profile_id: UUID) -> Optional[Profile]:
    """Get a profile by its own ID."""
    client = get_client()
    result = (
        client.table("profiles")
        .select("*")
        .eq("id", str(profile_id))
        .execute()
    )
    if result.data:
        return Profile(**result.data[0])
    return None


async def get_profile_by_email(email: str) -> Optional[Profile]:
    """Get a profile by email."""
    client = get_client()
    result = (
        client.table("profiles")
        .select("*")
        .eq("email", email.lower())
        .execute()
    )
    if result.data:
        return Profile(**result.data[0])
    return None


async def create_profile(data: ProfileCreate) -> Profile:
    """Create a new profile."""
    client = get_client()
    profile_data = {
        "user_id": str(data.user_id),
        "email": data.email.lower(),
        "first_name": data.first_name,
        "last_name": data.last_name,
        "photo_url": data.photo_url,
        "linkedin": data.linkedin,
        "meeting_link": data.meeting_link,
        "phone_number": data.phone_number,
        "city": data.city,
        "state": data.state,
        "country": data.country,
        "platform_role": data.platform_role.value,
        "expertise_areas": data.expertise_areas,
        "certifications": data.certifications,
        "bio": data.bio,
        "availability_status": data.availability_status.value,
        "capacity": data.capacity,
        "timezone": data.timezone,
        "preferences": data.preferences,
    }

    result = client.table("profiles").insert(profile_data).execute()
    return Profile(**result.data[0])


async def update_profile(
    user_id: UUID,
    data: ProfileUpdate,
) -> Optional[Profile]:
    """Update a profile."""
    client = get_client()
    update_data = {}

    for key, value in data.model_dump().items():
        if value is not None:
            # Handle enum values
            if key == "availability_status" and isinstance(value, AvailabilityStatus):
                update_data[key] = value.value
            else:
                update_data[key] = value

    if not update_data:
        return await get_profile_by_user_id(user_id)

    result = (
        client.table("profiles")
        .update(update_data)
        .eq("user_id", str(user_id))
        .execute()
    )
    if result.data:
        return Profile(**result.data[0])
    return None


async def delete_profile(user_id: UUID) -> bool:
    """Delete a profile."""
    client = get_client()
    result = (
        client.table("profiles")
        .delete()
        .eq("user_id", str(user_id))
        .execute()
    )
    return len(result.data) > 0


async def get_or_create_profile(
    user_id: UUID,
    email: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
) -> tuple[Profile, bool]:
    """Get existing profile or create new one. Returns (profile, created)."""
    existing = await get_profile_by_user_id(user_id)
    if existing:
        return existing, False

    profile = await create_profile(
        ProfileCreate(
            user_id=user_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )
    )
    return profile, True


async def list_profiles(
    limit: int = 100,
    offset: int = 0,
) -> list[Profile]:
    """List all profiles."""
    client = get_client()
    result = (
        client.table("profiles")
        .select("*")
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return [Profile(**row) for row in result.data]


async def search_profiles(
    query: str,
    limit: int = 20,
) -> list[Profile]:
    """Search profiles by name or email."""
    client = get_client()
    result = (
        client.table("profiles")
        .select("*")
        .or_(
            f"email.ilike.%{query}%,first_name.ilike.%{query}%,last_name.ilike.%{query}%"
        )
        .limit(limit)
        .execute()
    )
    return [Profile(**row) for row in result.data]


async def list_profiles_by_availability(
    status: AvailabilityStatus,
    limit: int = 50,
) -> list[Profile]:
    """List profiles by availability status."""
    client = get_client()
    result = (
        client.table("profiles")
        .select("*")
        .eq("availability_status", status.value)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [Profile(**row) for row in result.data]


async def list_profiles_by_platform_role(
    role: PlatformRole,
    limit: int = 100,
) -> list[Profile]:
    """List profiles by platform role."""
    client = get_client()
    result = (
        client.table("profiles")
        .select("*")
        .eq("platform_role", role.value)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [Profile(**row) for row in result.data]


async def update_availability(
    user_id: UUID,
    status: AvailabilityStatus,
) -> Optional[Profile]:
    """Quick update for availability status."""
    client = get_client()
    result = (
        client.table("profiles")
        .update({"availability_status": status.value})
        .eq("user_id", str(user_id))
        .execute()
    )
    if result.data:
        return Profile(**result.data[0])
    return None


async def update_profile_enrichment(
    user_id: UUID,
    data: dict,
) -> Optional[Profile]:
    """Update enrichment-specific columns on a profile."""
    client = get_client()
    result = (
        client.table("profiles")
        .update(data)
        .eq("user_id", str(user_id))
        .execute()
    )
    if result.data:
        return Profile(**result.data[0])
    return None


async def get_consultant_context(user_id: UUID) -> Optional[dict]:
    """Get a slim consultant context dict for prompt injection.

    Returns None if profile not found or not enriched.
    """
    client = get_client()
    result = (
        client.table("profiles")
        .select(
            "first_name, last_name, consultant_summary, "
            "industry_expertise, methodology_expertise, "
            "enriched_profile, enrichment_status"
        )
        .eq("user_id", str(user_id))
        .execute()
    )
    if not result.data:
        return None

    row = result.data[0]
    if row.get("enrichment_status") != "enriched":
        return None

    name_parts = [row.get("first_name"), row.get("last_name")]
    name = " ".join(p for p in name_parts if p) or "Unknown"

    enriched = row.get("enriched_profile") or {}
    return {
        "name": name,
        "professional_summary": enriched.get("professional_summary", ""),
        "domain_expertise": enriched.get("domain_expertise", []),
        "industry_verticals": enriched.get("industry_verticals", []),
        "methodology_expertise": row.get("methodology_expertise", []),
        "consulting_approach": enriched.get("consulting_approach", {}),
    }
