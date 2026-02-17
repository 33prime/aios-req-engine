"""Database operations for ICP consultant scores."""

from typing import Any, Optional
from uuid import UUID

from app.db.supabase_client import get_supabase as get_client


async def upsert_consultant_score(
    user_id: UUID,
    profile_id: UUID,
    score: float,
    signal_count: int,
    scoring_breakdown: dict[str, Any],
) -> dict[str, Any]:
    """Upsert a consultant's ICP score (unique per user+profile)."""
    client = get_client()
    data = {
        "user_id": str(user_id),
        "profile_id": str(profile_id),
        "score": score,
        "signal_count": signal_count,
        "scoring_breakdown": scoring_breakdown,
        "computed_at": "now()",
    }
    result = (
        client.table("icp_consultant_scores")
        .upsert(data, on_conflict="user_id,profile_id")
        .execute()
    )
    return result.data[0]


async def get_user_scores(user_id: UUID) -> list[dict[str, Any]]:
    """Get all ICP scores for a user."""
    client = get_client()
    result = (
        client.table("icp_consultant_scores")
        .select("*, icp_profiles(name, description)")
        .eq("user_id", str(user_id))
        .order("score", desc=True)
        .execute()
    )
    return result.data or []


async def get_leaderboard(profile_id: UUID, limit: int = 20) -> list[dict[str, Any]]:
    """Get top-scoring consultants for a profile."""
    client = get_client()
    result = (
        client.table("icp_consultant_scores")
        .select("*")
        .eq("profile_id", str(profile_id))
        .order("score", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []
