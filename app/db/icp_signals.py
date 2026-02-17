"""Database operations for ICP signals."""

from typing import Any, Optional
from uuid import UUID

from app.db.supabase_client import get_supabase as get_client


async def insert_icp_signal(data: dict[str, Any]) -> dict[str, Any]:
    """Insert a single ICP signal."""
    client = get_client()
    result = client.table("icp_signals").insert(data).execute()
    return result.data[0]


async def insert_icp_signals_batch(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Batch insert ICP signals."""
    if not signals:
        return []
    client = get_client()
    result = client.table("icp_signals").insert(signals).execute()
    return result.data or []


async def get_review_queue(limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    """Get signals pending review."""
    client = get_client()
    result = (
        client.table("icp_signals")
        .select("*")
        .eq("routing_status", "review")
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return result.data or []


async def get_outlier_signals(limit: int = 50) -> list[dict[str, Any]]:
    """Get outlier signals for clustering."""
    client = get_client()
    result = (
        client.table("icp_signals")
        .select("*")
        .eq("routing_status", "outlier")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


async def update_signal_routing(
    signal_id: UUID,
    routing_status: str,
    matched_profile_id: UUID | None = None,
    confidence_score: float = 0,
) -> Optional[dict[str, Any]]:
    """Update routing status of a signal."""
    client = get_client()
    data: dict[str, Any] = {
        "routing_status": routing_status,
        "confidence_score": confidence_score,
        "routed_at": "now()",
    }
    if matched_profile_id:
        data["matched_profile_id"] = str(matched_profile_id)

    result = (
        client.table("icp_signals")
        .update(data)
        .eq("id", str(signal_id))
        .execute()
    )
    return result.data[0] if result.data else None


async def get_signal_metrics() -> dict[str, Any]:
    """Get aggregated signal metrics."""
    client = get_client()

    # Total counts by routing status
    total_result = client.table("icp_signals").select("id", count="exact").execute()
    auto_result = (
        client.table("icp_signals")
        .select("id", count="exact")
        .eq("routing_status", "auto_routed")
        .execute()
    )
    review_result = (
        client.table("icp_signals")
        .select("id", count="exact")
        .eq("routing_status", "review")
        .execute()
    )
    outlier_result = (
        client.table("icp_signals")
        .select("id", count="exact")
        .eq("routing_status", "outlier")
        .execute()
    )
    dismissed_result = (
        client.table("icp_signals")
        .select("id", count="exact")
        .eq("routing_status", "dismissed")
        .execute()
    )

    return {
        "total_signals": total_result.count or 0,
        "auto_routed": auto_result.count or 0,
        "review_pending": review_result.count or 0,
        "outliers": outlier_result.count or 0,
        "dismissed": dismissed_result.count or 0,
    }


async def get_user_signals(user_id: UUID, limit: int = 100) -> list[dict[str, Any]]:
    """Get signals for a specific user."""
    client = get_client()
    result = (
        client.table("icp_signals")
        .select("*")
        .eq("user_id", str(user_id))
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []
