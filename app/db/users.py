"""Database operations for users."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from app.core.schemas_auth import User, UserCreate, UserType, UserUpdate
from app.db.supabase_client import get_supabase as get_client


async def get_user_by_id(user_id: UUID) -> Optional[User]:
    """Get a user by ID."""
    client = get_client()
    result = client.table("users").select("*").eq("id", str(user_id)).execute()
    if result.data:
        return User(**result.data[0])
    return None


async def get_user_by_email(email: str) -> Optional[User]:
    """Get a user by email."""
    client = get_client()
    result = client.table("users").select("*").eq("email", email.lower()).execute()
    if result.data:
        return User(**result.data[0])
    return None


async def create_user(data: UserCreate) -> User:
    """Create a new user."""
    client = get_client()
    user_data = {
        "email": data.email.lower(),
        "user_type": data.user_type.value,
        "first_name": data.first_name,
        "last_name": data.last_name,
        "company_name": data.company_name,
    }
    result = client.table("users").insert(user_data).execute()
    return User(**result.data[0])


async def update_user(user_id: UUID, data: UserUpdate) -> Optional[User]:
    """Update a user."""
    client = get_client()
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update_data:
        return await get_user_by_id(user_id)

    result = client.table("users").update(update_data).eq("id", str(user_id)).execute()
    if result.data:
        return User(**result.data[0])
    return None


async def delete_user(user_id: UUID) -> bool:
    """Delete a user."""
    client = get_client()
    result = client.table("users").delete().eq("id", str(user_id)).execute()
    return len(result.data) > 0


async def list_users(
    user_type: Optional[UserType] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[User]:
    """List users with optional filtering."""
    client = get_client()
    query = client.table("users").select("*")

    if user_type:
        query = query.eq("user_type", user_type.value)

    query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
    result = query.execute()

    return [User(**row) for row in result.data]


async def get_or_create_user(
    email: str,
    user_type: UserType,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    company_name: Optional[str] = None,
) -> tuple[User, bool]:
    """Get existing user or create new one. Returns (user, created)."""
    existing = await get_user_by_email(email)
    if existing:
        return existing, False

    user = await create_user(
        UserCreate(
            email=email,
            user_type=user_type,
            first_name=first_name,
            last_name=last_name,
            company_name=company_name,
        )
    )
    return user, True


async def mark_welcome_seen(user_id: UUID) -> Optional[User]:
    """Mark that user has seen the welcome screen."""
    return await update_user(user_id, UserUpdate(has_seen_welcome=True))


async def search_users(
    query: str,
    user_type: Optional[UserType] = None,
    limit: int = 20,
) -> list[User]:
    """Search users by email or name."""
    client = get_client()

    # Search in email, first_name, last_name
    search_query = client.table("users").select("*")

    if user_type:
        search_query = search_query.eq("user_type", user_type.value)

    # Use ilike for case-insensitive search
    search_query = search_query.or_(
        f"email.ilike.%{query}%,first_name.ilike.%{query}%,last_name.ilike.%{query}%"
    )

    result = search_query.limit(limit).execute()
    return [User(**row) for row in result.data]
