"""Database operations for strategic_context table."""

from datetime import datetime, timezone
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def get_strategic_context(project_id: UUID) -> dict | None:
    """
    Get strategic context for a project.

    Args:
        project_id: Project UUID

    Returns:
        Strategic context dict or None if not found
    """
    try:
        supabase = get_supabase()

        response = (
            supabase.table("strategic_context")
            .select("*")
            .eq("project_id", str(project_id))
            .maybe_single()
            .execute()
        )

        if response is None:
            return None

        return response.data
    except Exception as e:
        logger.warning(f"Error getting strategic context for {project_id}: {e}")
        return None


def create_strategic_context(
    project_id: UUID,
    project_type: str = "internal",
    executive_summary: str | None = None,
    opportunity: dict | None = None,
    risks: list | None = None,
    investment_case: dict | None = None,
    success_metrics: list | None = None,
    constraints: dict | None = None,
    evidence: list | None = None,
    confirmation_status: str = "ai_generated",
    generation_model: str | None = None,
) -> dict:
    """
    Create strategic context for a project.

    Args:
        project_id: Project UUID
        project_type: 'internal' or 'market_product'
        executive_summary: Executive summary text
        opportunity: Opportunity details dict
        risks: List of risk dicts
        investment_case: Investment case dict
        success_metrics: List of success metric dicts
        constraints: Constraints dict
        evidence: List of evidence dicts
        confirmation_status: Confirmation status
        generation_model: Model used for generation

    Returns:
        Created strategic context dict
    """
    supabase = get_supabase()

    context_data = {
        "project_id": str(project_id),
        "project_type": project_type,
        "executive_summary": executive_summary,
        "opportunity": opportunity or {},
        "risks": risks or [],
        "investment_case": investment_case or {},
        "success_metrics": success_metrics or [],
        "constraints": constraints or {},
        "evidence": evidence or [],
        "confirmation_status": confirmation_status,
        "generation_model": generation_model,
    }

    response = (
        supabase.table("strategic_context")
        .insert(context_data)
        .execute()
    )

    logger.info(
        f"Created strategic context for project {project_id}",
        extra={"project_id": str(project_id)},
    )

    return response.data[0]


def upsert_strategic_context(
    project_id: UUID,
    project_type: str = "internal",
    executive_summary: str | None = None,
    opportunity: dict | None = None,
    risks: list | None = None,
    investment_case: dict | None = None,
    success_metrics: list | None = None,
    constraints: dict | None = None,
    evidence: list | None = None,
    confirmation_status: str = "ai_generated",
    generation_model: str | None = None,
) -> dict:
    """
    Upsert strategic context for a project (insert or update by project_id).

    Args:
        Same as create_strategic_context

    Returns:
        Created or updated strategic context dict
    """
    supabase = get_supabase()

    context_data = {
        "project_id": str(project_id),
        "project_type": project_type,
        "executive_summary": executive_summary,
        "opportunity": opportunity or {},
        "risks": risks or [],
        "investment_case": investment_case or {},
        "success_metrics": success_metrics or [],
        "constraints": constraints or {},
        "evidence": evidence or [],
        "confirmation_status": confirmation_status,
        "generation_model": generation_model,
        "enrichment_status": "enriched",
        "enriched_at": datetime.now(timezone.utc).isoformat(),
    }

    response = (
        supabase.table("strategic_context")
        .upsert(context_data, on_conflict="project_id")
        .execute()
    )

    logger.info(
        f"Upserted strategic context for project {project_id}",
        extra={"project_id": str(project_id)},
    )

    return response.data[0]


def update_strategic_context(
    project_id: UUID,
    updates: dict,
) -> dict:
    """
    Update strategic context for a project.

    Args:
        project_id: Project UUID
        updates: Dict of fields to update

    Returns:
        Updated strategic context dict
    """
    supabase = get_supabase()

    # Add updated_at timestamp
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    response = (
        supabase.table("strategic_context")
        .update(updates)
        .eq("project_id", str(project_id))
        .execute()
    )

    if not response.data:
        raise ValueError(f"Strategic context not found for project: {project_id}")

    logger.info(
        f"Updated strategic context for project {project_id}",
        extra={"project_id": str(project_id), "fields": list(updates.keys())},
    )

    return response.data[0]


def update_strategic_context_section(
    project_id: UUID,
    section: str,
    data: dict | list,
) -> dict:
    """
    Update a specific section of strategic context.

    Args:
        project_id: Project UUID
        section: Section name (e.g., 'opportunity', 'risks', 'investment_case')
        data: New data for the section

    Returns:
        Updated strategic context dict
    """
    return update_strategic_context(project_id, {section: data})


def update_strategic_context_status(
    project_id: UUID,
    status: str,
    confirmed_by: UUID | None = None,
) -> dict:
    """
    Update confirmation status for strategic context.

    Args:
        project_id: Project UUID
        status: New confirmation status
        confirmed_by: User UUID who confirmed

    Returns:
        Updated strategic context dict
    """
    updates = {
        "confirmation_status": status,
        "confirmed_by": str(confirmed_by) if confirmed_by else None,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
    }

    return update_strategic_context(project_id, updates)


def add_risk(
    project_id: UUID,
    category: str,
    description: str,
    severity: str,
    mitigation: str | None = None,
    evidence_ids: list[str] | None = None,
) -> dict:
    """
    Add a risk to strategic context.

    Args:
        project_id: Project UUID
        category: Risk category (business, technical, compliance, competitive)
        description: Risk description
        severity: Severity level (high, medium, low)
        mitigation: Optional mitigation strategy
        evidence_ids: Optional list of evidence chunk IDs

    Returns:
        Updated strategic context dict
    """
    context = get_strategic_context(project_id)
    if not context:
        raise ValueError(f"Strategic context not found for project: {project_id}")

    risks = context.get("risks", []) or []
    new_risk = {
        "category": category,
        "description": description,
        "severity": severity,
        "mitigation": mitigation,
        "evidence_ids": evidence_ids or [],
    }
    risks.append(new_risk)

    return update_strategic_context(project_id, {"risks": risks})


def add_success_metric(
    project_id: UUID,
    metric: str,
    target: str,
    current: str | None = None,
    evidence_ids: list[str] | None = None,
) -> dict:
    """
    Add a success metric to strategic context.

    Args:
        project_id: Project UUID
        metric: Metric name
        target: Target value
        current: Current value (if known)
        evidence_ids: Optional list of evidence chunk IDs

    Returns:
        Updated strategic context dict
    """
    context = get_strategic_context(project_id)
    if not context:
        raise ValueError(f"Strategic context not found for project: {project_id}")

    metrics = context.get("success_metrics", []) or []
    new_metric = {
        "metric": metric,
        "target": target,
        "current": current,
        "evidence_ids": evidence_ids or [],
    }
    metrics.append(new_metric)

    return update_strategic_context(project_id, {"success_metrics": metrics})


def update_project_type(
    project_id: UUID,
    project_type: str,
) -> dict:
    """
    Update project type (affects investment case display).

    Args:
        project_id: Project UUID
        project_type: 'internal' or 'market_product'

    Returns:
        Updated strategic context dict
    """
    if project_type not in ("internal", "market_product"):
        raise ValueError(f"Invalid project type: {project_type}")

    return update_strategic_context(project_id, {"project_type": project_type})


def delete_strategic_context(project_id: UUID) -> None:
    """
    Delete strategic context for a project.

    Args:
        project_id: Project UUID
    """
    supabase = get_supabase()

    supabase.table("strategic_context").delete().eq("project_id", str(project_id)).execute()

    logger.info(
        f"Deleted strategic context for project {project_id}",
        extra={"project_id": str(project_id)},
    )
