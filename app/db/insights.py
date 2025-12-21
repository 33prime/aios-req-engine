"""Insights database operations for red-team findings."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def insert_insights(
    project_id: UUID,
    run_id: UUID,
    job_id: UUID | None,
    insights: list[dict[str, Any]],
    source: dict[str, Any],
) -> int:
    """
    Insert a batch of insights from red-team analysis.

    Args:
        project_id: Project UUID
        run_id: Run tracking UUID
        job_id: Job tracking UUID (optional)
        insights: List of insight dicts matching RedTeamInsight schema
        source: Source metadata dict (agent, model, prompt_version, schema_version)

    Returns:
        Number of insights inserted
    """
    if not insights:
        return 0

    supabase = get_supabase()

    try:
        rows = []
        for insight in insights:
            rows.append(
                {
                    "project_id": str(project_id),
                    "run_id": str(run_id),
                    "job_id": str(job_id) if job_id else None,
                    "status": "open",
                    "severity": insight.get("severity", "minor"),
                    "category": insight.get("category", "logic"),
                    "title": insight.get("title", ""),
                    "finding": insight.get("finding", ""),
                    "why": insight.get("why", ""),
                    "suggested_action": insight.get("suggested_action", "needs_confirmation"),
                    "targets": insight.get("targets", []),
                    "evidence": insight.get("evidence", []),
                    "source": source,
                }
            )

        response = supabase.table("insights").insert(rows).execute()

        inserted_count = len(response.data) if response.data else 0
        logger.info(
            f"Inserted {inserted_count} insights for project {project_id}",
            extra={"run_id": str(run_id), "project_id": str(project_id)},
        )
        return inserted_count

    except Exception as e:
        logger.error(f"Failed to insert insights for project {project_id}: {e}")
        raise


def update_insight_status(insight_id: UUID, status: str) -> None:
    """
    Update the status of an insight.

    Args:
        insight_id: Insight UUID
        status: New status (open, queued, applied, dismissed)

    Raises:
        ValueError: If insight not found
    """
    allowed_statuses = {"open", "queued", "applied", "dismissed"}
    if status not in allowed_statuses:
        raise ValueError(f"Invalid status: {status}. Must be one of {allowed_statuses}")

    supabase = get_supabase()

    try:
        response = (
            supabase.table("insights")
            .update({"status": status})
            .eq("id", str(insight_id))
            .execute()
        )

        if not response.data:
            raise ValueError(f"Insight not found: {insight_id}")

        logger.info(f"Updated insight {insight_id} status to {status}")

    except Exception as e:
        logger.error(f"Failed to update insight status: {e}")
        raise


def list_insights(
    project_id: UUID,
    status: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """
    List insights for a project.

    Args:
        project_id: Project UUID
        status: Optional status filter (open, queued, applied, dismissed)
        limit: Maximum number of insights to return

    Returns:
        List of insight dicts ordered by created_at desc
    """
    supabase = get_supabase()

    try:
        query = (
            supabase.table("insights")
            .select("*")
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
            .limit(limit)
        )

        if status:
            query = query.eq("status", status)

        response = query.execute()
        return response.data or []

    except Exception as e:
        logger.error(f"Failed to list insights for project {project_id}: {e}")
        raise


def list_latest_insights(
    project_id: UUID,
    limit: int = 50,
    statuses: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    List the most recent insights for a project, optionally filtered by status list.

    Args:
        project_id: Project UUID
        limit: Maximum number of insights to return (default 50)
        statuses: Optional list of statuses to filter by (e.g., ["open", "queued"])

    Returns:
        List of insight dicts ordered by created_at desc
    """
    supabase = get_supabase()

    try:
        query = (
            supabase.table("insights")
            .select("*")
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
            .limit(limit)
        )

        if statuses:
            query = query.in_("status", statuses)

        response = query.execute()
        return response.data or []

    except Exception as e:
        logger.error(f"Failed to list latest insights for project {project_id}: {e}")
        raise
