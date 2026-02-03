"""Database operations for email routing tokens."""

from datetime import UTC
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def create_token(
    project_id: UUID,
    created_by: UUID,
    allowed_sender_domain: str | None = None,
    allowed_sender_emails: list[str] | None = None,
    max_emails: int = 100,
) -> dict:
    """Create a new email routing token for a project."""
    supabase = get_supabase()

    data = {
        "project_id": str(project_id),
        "created_by": str(created_by),
        "max_emails": max_emails,
    }

    if allowed_sender_domain:
        data["allowed_sender_domain"] = allowed_sender_domain
    if allowed_sender_emails:
        data["allowed_sender_emails"] = allowed_sender_emails

    result = supabase.table("email_routing_tokens").insert(data).execute()
    return result.data[0] if result.data else {}


def get_token_by_value(token: str) -> dict | None:
    """Look up a routing token by its value."""
    supabase = get_supabase()
    result = (
        supabase.table("email_routing_tokens")
        .select("*")
        .eq("token", token)
        .eq("is_active", True)
        .execute()
    )
    return result.data[0] if result.data else None


def validate_token(token: str, sender_email: str) -> tuple[bool, str, dict | None]:
    """
    Validate a routing token for an incoming email.

    Checks: exists, active, not expired, under rate limit, sender domain matches.

    Returns:
        Tuple of (is_valid, reason, token_record)
    """
    record = get_token_by_value(token)

    if not record:
        return False, "Token not found or inactive", None

    # Check expiry (Supabase returns ISO format)
    from datetime import datetime

    expires_at = datetime.fromisoformat(record["expires_at"].replace("Z", "+00:00"))
    if datetime.now(UTC) > expires_at:
        return False, "Token expired", record

    # Check rate limit
    if record["emails_received"] >= record["max_emails"]:
        return False, "Token rate limit exceeded", record

    # Check sender domain restriction
    if record.get("allowed_sender_domain"):
        sender_domain = sender_email.split("@")[-1].lower()
        if sender_domain != record["allowed_sender_domain"].lower():
            return False, f"Sender domain {sender_domain} not allowed", record

    # Check sender email allowlist
    allowed_emails = record.get("allowed_sender_emails") or []
    if allowed_emails and sender_email.lower() not in [
        e.lower() for e in allowed_emails
    ]:
        return False, f"Sender {sender_email} not in allowlist", record

    return True, "Valid", record


def increment_usage(token_id: UUID) -> None:
    """Increment the emails_received counter for a token."""
    supabase = get_supabase()
    # Fetch current count and increment
    record = (
        supabase.table("email_routing_tokens")
        .select("emails_received")
        .eq("id", str(token_id))
        .single()
        .execute()
    )
    if record.data:
        new_count = (record.data.get("emails_received") or 0) + 1
        supabase.table("email_routing_tokens").update(
            {"emails_received": new_count}
        ).eq("id", str(token_id)).execute()


def list_tokens(
    project_id: UUID,
    active_only: bool = True,
    limit: int = 50,
) -> list[dict]:
    """List email routing tokens for a project."""
    supabase = get_supabase()
    query = (
        supabase.table("email_routing_tokens")
        .select("*")
        .eq("project_id", str(project_id))
    )

    if active_only:
        query = query.eq("is_active", True)

    query = query.order("created_at", desc=True).limit(limit)
    result = query.execute()
    return result.data or []


def deactivate_token(token_id: UUID) -> dict | None:
    """Deactivate a routing token."""
    supabase = get_supabase()
    result = (
        supabase.table("email_routing_tokens")
        .update({"is_active": False})
        .eq("id", str(token_id))
        .execute()
    )
    return result.data[0] if result.data else None


def delete_user_tokens(user_id: UUID) -> int:
    """Delete all tokens created by a user (DSAR purge)."""
    supabase = get_supabase()
    result = (
        supabase.table("email_routing_tokens")
        .delete()
        .eq("created_by", str(user_id))
        .execute()
    )
    return len(result.data) if result.data else 0


def deactivate_expired_tokens() -> int:
    """Deactivate all expired tokens (retention policy)."""
    supabase = get_supabase()
    from datetime import datetime

    now = datetime.now(UTC).isoformat()
    result = (
        supabase.table("email_routing_tokens")
        .update({"is_active": False})
        .eq("is_active", True)
        .lt("expires_at", now)
        .execute()
    )
    count = len(result.data) if result.data else 0
    if count:
        logger.info(f"Deactivated {count} expired email routing tokens")
    return count
