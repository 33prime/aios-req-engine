"""Cached readiness score and status management.

This module handles caching readiness scores and status narratives
in the projects table to avoid expensive recalculations.

The readiness score and narrative are cached and updated when:
1. Entities (features, personas, vp_steps) are created/updated/deleted
2. An entity's confirmation status changes
3. Manually via the refresh endpoint

When refreshed, this module:
1. Regenerates the state snapshot (for AI context)
2. Computes the readiness score (for progress tracking)
3. Generates the status narrative (human-readable TL;DR)
"""

from datetime import UTC, datetime
from uuid import UUID

from app.core.logging import get_logger
from app.core.readiness import compute_readiness
from app.core.state_snapshot import regenerate_state_snapshot
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


async def update_project_state(project_id: UUID) -> dict:
    """
    Refresh all cached project state: snapshot, readiness, and narrative.

    This is the main entry point for refreshing project state.
    Call this whenever entities change or when user requests refresh.

    Args:
        project_id: Project UUID

    Returns:
        Dict with readiness_score, narrative, and snapshot info
    """
    logger.info(f"Refreshing full project state for {project_id}")

    # 1. Regenerate state snapshot (sync)
    snapshot = regenerate_state_snapshot(project_id)
    logger.info(f"Regenerated state snapshot for {project_id}")

    # 2. Compute readiness score (sync)
    readiness = compute_readiness(project_id)
    score = readiness.score / 100.0  # Convert 0-100 to 0-1 for storage

    # 3. Generate status narrative (async) using the fresh snapshot
    from app.chains.generate_status_narrative import generate_status_narrative
    narrative = await generate_status_narrative(project_id)
    logger.info(f"Generated status narrative for {project_id}")

    # 4. Update the projects table with cached values
    supabase = get_supabase()
    now = datetime.now(UTC).isoformat()

    supabase.table("projects").update({
        "cached_readiness_score": score,
        "readiness_calculated_at": now,
        "status_narrative": narrative,
    }).eq("id", str(project_id)).execute()

    logger.info(
        f"Updated project state for {project_id}: readiness={readiness.score}%",
        extra={"project_id": str(project_id), "score": readiness.score},
    )

    return {
        "readiness_score": readiness.score,
        "narrative": narrative,
        "snapshot_tokens": len(snapshot) // 4,
    }


def update_project_readiness(project_id: UUID) -> float:
    """
    Recalculate and cache the readiness score for a project.

    Uses the new dimensional readiness scoring (value_path, problem,
    solution, engagement) for consistency with OverviewTab.

    Args:
        project_id: Project UUID

    Returns:
        The new readiness score (0-100 as float for storage as 0-1)
    """
    try:
        # Calculate fresh score using new dimensional readiness
        readiness = compute_readiness(project_id)
        score = readiness.score / 100.0  # Convert 0-100 to 0-1 for storage

        # Update the projects table
        supabase = get_supabase()
        now = datetime.now(UTC).isoformat()

        supabase.table("projects").update({
            "cached_readiness_score": score,
            "readiness_calculated_at": now,
        }).eq("id", str(project_id)).execute()

        logger.info(
            f"Updated cached readiness score for project {project_id}: {readiness.score}%",
            extra={"project_id": str(project_id), "score": readiness.score},
        )

        return score

    except Exception as e:
        logger.error(f"Failed to update readiness score for {project_id}: {e}")
        raise


def update_all_readiness_scores() -> dict:
    """
    Update readiness scores for all active projects.

    This is useful for bulk updates or initial population.

    Returns:
        Dict with count of updated projects and any errors
    """
    supabase = get_supabase()

    try:
        # Get all active projects
        response = (
            supabase.table("projects")
            .select("id")
            .eq("status", "active")
            .execute()
        )

        projects = response.data or []
        updated = 0
        errors = []

        for project in projects:
            try:
                update_project_readiness(UUID(project["id"]))
                updated += 1
            except Exception as e:
                errors.append({"project_id": project["id"], "error": str(e)})

        logger.info(
            f"Bulk updated readiness scores: {updated} projects, {len(errors)} errors",
            extra={"updated": updated, "errors": len(errors)},
        )

        return {"updated": updated, "errors": errors}

    except Exception as e:
        logger.error(f"Failed to bulk update readiness scores: {e}")
        raise


def invalidate_project_readiness(project_id: UUID) -> None:
    """
    Mark a project's readiness score as stale (set to NULL).

    This is called when entities change, so the score gets recalculated
    on next request.

    Args:
        project_id: Project UUID
    """
    try:
        supabase = get_supabase()
        supabase.table("projects").update({
            "cached_readiness_score": None,
            "readiness_calculated_at": None,
        }).eq("id", str(project_id)).execute()

        logger.debug(f"Invalidated readiness score for project {project_id}")

    except Exception as e:
        logger.error(f"Failed to invalidate readiness score for {project_id}: {e}")
        # Don't raise - this is a non-critical operation
