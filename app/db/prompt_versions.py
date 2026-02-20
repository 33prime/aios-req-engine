"""Database access layer for prompt versions."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def create_prompt_version(
    prototype_id: UUID,
    version_number: int,
    prompt_text: str,
    parent_version_id: UUID | None = None,
    generation_model: str | None = None,
    generation_chain: str | None = None,
    input_context_snapshot: dict[str, Any] | None = None,
    learnings_injected: list[dict[str, Any]] | None = None,
    tokens_input: int = 0,
    tokens_output: int = 0,
    tokens_cache_read: int = 0,
    tokens_cache_create: int = 0,
    estimated_cost_usd: float = 0,
) -> dict[str, Any]:
    """Create an immutable prompt version record."""
    supabase = get_supabase()
    data = {
        "prototype_id": str(prototype_id),
        "version_number": version_number,
        "prompt_text": prompt_text,
        "parent_version_id": str(parent_version_id) if parent_version_id else None,
        "generation_model": generation_model,
        "generation_chain": generation_chain,
        "input_context_snapshot": input_context_snapshot or {},
        "learnings_injected": learnings_injected or [],
        "tokens_input": tokens_input,
        "tokens_output": tokens_output,
        "tokens_cache_read": tokens_cache_read,
        "tokens_cache_create": tokens_cache_create,
        "estimated_cost_usd": estimated_cost_usd,
    }
    response = supabase.table("prompt_versions").insert(data).execute()
    if not response.data:
        raise ValueError("Failed to create prompt version")
    logger.info(f"Created prompt version v{version_number} for prototype {prototype_id}")
    return response.data[0]


def get_prompt_version(version_id: UUID) -> dict[str, Any] | None:
    """Get a prompt version by ID."""
    supabase = get_supabase()
    response = (
        supabase.table("prompt_versions")
        .select("*")
        .eq("id", str(version_id))
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def list_prompt_versions(prototype_id: UUID) -> list[dict[str, Any]]:
    """List all prompt versions for a prototype, ordered by version number."""
    supabase = get_supabase()
    response = (
        supabase.table("prompt_versions")
        .select("*")
        .eq("prototype_id", str(prototype_id))
        .order("version_number", desc=False)
        .execute()
    )
    return response.data or []


def get_latest_prompt_version(prototype_id: UUID) -> dict[str, Any] | None:
    """Get the most recent prompt version for a prototype."""
    supabase = get_supabase()
    response = (
        supabase.table("prompt_versions")
        .select("*")
        .eq("prototype_id", str(prototype_id))
        .order("version_number", desc=True)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None
