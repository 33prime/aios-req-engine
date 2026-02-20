"""Database access layer for eval runs and gaps."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


# =============================================================================
# Eval runs
# =============================================================================


def create_eval_run(
    prompt_version_id: UUID,
    prototype_id: UUID,
    iteration_number: int = 1,
    **fields: Any,
) -> dict[str, Any]:
    """Create an eval run record."""
    supabase = get_supabase()
    data = {
        "prompt_version_id": str(prompt_version_id),
        "prototype_id": str(prototype_id),
        "iteration_number": iteration_number,
        **{k: (str(v) if isinstance(v, UUID) else v) for k, v in fields.items()},
    }
    response = supabase.table("eval_runs").insert(data).execute()
    if not response.data:
        raise ValueError("Failed to create eval run")
    logger.info(f"Created eval run for prototype {prototype_id}, iteration {iteration_number}")
    return response.data[0]


def get_eval_run(run_id: UUID) -> dict[str, Any] | None:
    """Get an eval run by ID."""
    supabase = get_supabase()
    response = (
        supabase.table("eval_runs")
        .select("*")
        .eq("id", str(run_id))
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def list_eval_runs(
    prototype_id: UUID | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List eval runs, optionally filtered by prototype."""
    supabase = get_supabase()
    query = supabase.table("eval_runs").select("*")
    if prototype_id:
        query = query.eq("prototype_id", str(prototype_id))
    response = query.order("created_at", desc=True).limit(limit).execute()
    return response.data or []


def update_eval_run(run_id: UUID, **fields: Any) -> dict[str, Any]:
    """Update an eval run with new fields."""
    supabase = get_supabase()
    update_data = {k: (str(v) if isinstance(v, UUID) else v) for k, v in fields.items()}
    response = (
        supabase.table("eval_runs")
        .update(update_data)
        .eq("id", str(run_id))
        .execute()
    )
    if not response.data:
        raise ValueError(f"Failed to update eval run {run_id}")
    return response.data[0]


# =============================================================================
# Eval gaps
# =============================================================================


def create_eval_gap(
    eval_run_id: UUID,
    dimension: str,
    description: str,
    severity: str = "medium",
    feature_ids: list[str] | None = None,
    gap_pattern: str | None = None,
) -> dict[str, Any]:
    """Create a normalized gap record."""
    supabase = get_supabase()
    data = {
        "eval_run_id": str(eval_run_id),
        "dimension": dimension,
        "description": description,
        "severity": severity,
        "feature_ids": feature_ids or [],
        "gap_pattern": gap_pattern,
    }
    response = supabase.table("eval_gaps").insert(data).execute()
    if not response.data:
        raise ValueError("Failed to create eval gap")
    return response.data[0]


def list_eval_gaps(eval_run_id: UUID) -> list[dict[str, Any]]:
    """List all gaps for an eval run."""
    supabase = get_supabase()
    response = (
        supabase.table("eval_gaps")
        .select("*")
        .eq("eval_run_id", str(eval_run_id))
        .order("created_at", desc=False)
        .execute()
    )
    return response.data or []


def resolve_gap(
    gap_id: UUID,
    resolved_in_run_id: UUID,
) -> dict[str, Any]:
    """Mark a gap as resolved by a subsequent run."""
    supabase = get_supabase()
    response = (
        supabase.table("eval_gaps")
        .update({
            "resolved_in_run_id": str(resolved_in_run_id),
            "resolved_at": "now()",
        })
        .eq("id", str(gap_id))
        .execute()
    )
    if not response.data:
        raise ValueError(f"Failed to resolve gap {gap_id}")
    return response.data[0]


def get_unresolved_gaps(prototype_id: UUID) -> list[dict[str, Any]]:
    """Get all unresolved gaps for a prototype across all eval runs."""
    supabase = get_supabase()
    response = (
        supabase.table("eval_gaps")
        .select("*, eval_runs!inner(prototype_id)")
        .eq("eval_runs.prototype_id", str(prototype_id))
        .is_("resolved_in_run_id", "null")
        .execute()
    )
    return response.data or []


# =============================================================================
# Dashboard stats
# =============================================================================


def get_dashboard_stats() -> dict[str, Any]:
    """Compute aggregate eval stats for the admin dashboard."""
    supabase = get_supabase()

    # All runs
    runs_resp = (
        supabase.table("eval_runs")
        .select("id, prototype_id, overall_score, action, iteration_number, estimated_cost_usd, created_at")
        .order("created_at", desc=True)
        .execute()
    )
    runs = runs_resp.data or []

    if not runs:
        return {
            "total_runs": 0,
            "avg_score": 0,
            "first_pass_rate": 0,
            "top_gaps": [],
            "version_distribution": {},
            "score_trend": [],
            "avg_iterations": 0,
            "total_cost_usd": 0,
        }

    total_runs = len(runs)
    avg_score = sum(r.get("overall_score", 0) for r in runs) / total_runs
    total_cost = sum(r.get("estimated_cost_usd", 0) for r in runs)

    # First-pass rate: prototypes accepted on iteration 1
    iteration_1_runs = [r for r in runs if r.get("iteration_number") == 1]
    first_pass_accepted = sum(1 for r in iteration_1_runs if r.get("action") == "accept")
    first_pass_rate = first_pass_accepted / max(len(iteration_1_runs), 1)

    # Version distribution (final action per prototype)
    proto_final: dict[str, str] = {}
    for r in sorted(runs, key=lambda x: x.get("created_at", "")):
        proto_final[r["prototype_id"]] = r.get("action", "pending")
    version_dist: dict[str, int] = {}
    for action in proto_final.values():
        version_dist[action] = version_dist.get(action, 0) + 1

    # Average iterations per prototype
    proto_iters: dict[str, int] = {}
    for r in runs:
        pid = r["prototype_id"]
        proto_iters[pid] = max(proto_iters.get(pid, 0), r.get("iteration_number", 1))
    avg_iterations = sum(proto_iters.values()) / max(len(proto_iters), 1)

    # Score trend (last 20 runs, chronological)
    score_trend = [
        {"date": r.get("created_at", "")[:10], "score": r.get("overall_score", 0)}
        for r in sorted(runs, key=lambda x: x.get("created_at", ""))[-20:]
    ]

    # Top gaps by dimension
    gaps_resp = (
        supabase.table("eval_gaps")
        .select("dimension")
        .is_("resolved_in_run_id", "null")
        .execute()
    )
    gap_counts: dict[str, int] = {}
    for g in (gaps_resp.data or []):
        dim = g.get("dimension", "unknown")
        gap_counts[dim] = gap_counts.get(dim, 0) + 1
    top_gaps = sorted(
        [{"dimension": k, "count": v} for k, v in gap_counts.items()],
        key=lambda x: -x["count"],
    )[:8]

    return {
        "total_runs": total_runs,
        "avg_score": round(avg_score, 4),
        "first_pass_rate": round(first_pass_rate, 4),
        "top_gaps": top_gaps,
        "version_distribution": version_dist,
        "score_trend": score_trend,
        "avg_iterations": round(avg_iterations, 2),
        "total_cost_usd": round(total_cost, 6),
    }
