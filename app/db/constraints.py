"""Database operations for constraints table.

Stores constraints, requirements, risks, KPIs, and assumptions extracted from signals.
Separated from features table for cleaner entity architecture.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


# Valid constraint types
CONSTRAINT_TYPES = {
    "technical",      # "Must support 10k users"
    "compliance",     # "HIPAA compliance required"
    "integration",    # "Must sync with Salesforce"
    "business",       # "Budget under $50k"
    "timeline",       # "Must launch by Q3"
    "risk",           # "Risk of scope creep"
    "kpi",            # "Reduce churn by 20%"
    "assumption",     # "Users have modern browsers"
}

SEVERITY_LEVELS = {"must_have", "should_have", "nice_to_have"}


def create_constraint(
    project_id: UUID,
    title: str,
    constraint_type: str,
    description: str | None = None,
    severity: str = "should_have",
    evidence: list[dict] | None = None,
    extracted_from_signal_id: UUID | None = None,
    linked_feature_ids: list[UUID] | None = None,
    linked_vp_step_ids: list[UUID] | None = None,
    confirmation_status: str = "ai_generated",
) -> dict[str, Any]:
    """
    Create a new constraint.

    Args:
        project_id: Project UUID
        title: Constraint title
        constraint_type: Type (technical, compliance, risk, kpi, etc.)
        description: Detailed description
        severity: must_have, should_have, or nice_to_have
        evidence: List of evidence dicts
        extracted_from_signal_id: Source signal UUID
        linked_feature_ids: Related feature UUIDs
        linked_vp_step_ids: Related VP step UUIDs
        confirmation_status: Confirmation workflow status

    Returns:
        Created constraint dict
    """
    supabase = get_supabase()

    # Validate constraint_type
    if constraint_type not in CONSTRAINT_TYPES:
        logger.warning(f"Unknown constraint type '{constraint_type}', defaulting to 'technical'")
        constraint_type = "technical"

    # Validate severity
    if severity not in SEVERITY_LEVELS:
        severity = "should_have"

    data = {
        "project_id": str(project_id),
        "title": title,
        "constraint_type": constraint_type,
        "description": description,
        "severity": severity,
        "evidence": evidence or [],
        "confirmation_status": confirmation_status,
    }

    if extracted_from_signal_id:
        data["extracted_from_signal_id"] = str(extracted_from_signal_id)

    if linked_feature_ids:
        data["linked_feature_ids"] = [str(fid) for fid in linked_feature_ids]

    if linked_vp_step_ids:
        data["linked_vp_step_ids"] = [str(vid) for vid in linked_vp_step_ids]

    response = supabase.table("constraints").insert(data).execute()

    if not response.data:
        raise ValueError("Failed to create constraint")

    constraint = response.data[0]

    logger.info(
        f"Created constraint '{title}' ({constraint_type}) for project {project_id}",
        extra={
            "project_id": str(project_id),
            "constraint_id": constraint["id"],
            "constraint_type": constraint_type,
        },
    )

    return constraint


def get_constraint(constraint_id: UUID) -> dict[str, Any] | None:
    """Get a constraint by ID."""
    supabase = get_supabase()

    response = (
        supabase.table("constraints")
        .select("*")
        .eq("id", str(constraint_id))
        .maybe_single()
        .execute()
    )

    return response.data


def list_constraints(
    project_id: UUID,
    constraint_type: str | None = None,
    severity: str | None = None,
    confirmation_status: str | None = None,
) -> list[dict[str, Any]]:
    """
    List constraints for a project with optional filters.

    Args:
        project_id: Project UUID
        constraint_type: Filter by type
        severity: Filter by severity
        confirmation_status: Filter by status

    Returns:
        List of constraint dicts
    """
    supabase = get_supabase()

    query = (
        supabase.table("constraints")
        .select("*")
        .eq("project_id", str(project_id))
    )

    if constraint_type:
        query = query.eq("constraint_type", constraint_type)

    if severity:
        query = query.eq("severity", severity)

    if confirmation_status:
        query = query.eq("confirmation_status", confirmation_status)

    response = query.order("created_at", desc=True).execute()

    return response.data or []


def list_constraints_by_type(project_id: UUID) -> dict[str, list[dict]]:
    """
    Get constraints grouped by type.

    Returns:
        Dict mapping constraint_type to list of constraints
    """
    constraints = list_constraints(project_id)

    grouped = {ctype: [] for ctype in CONSTRAINT_TYPES}

    for c in constraints:
        ctype = c.get("constraint_type", "technical")
        if ctype in grouped:
            grouped[ctype].append(c)

    return grouped


def update_constraint(
    constraint_id: UUID,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """
    Update a constraint.

    Args:
        constraint_id: Constraint UUID
        updates: Dict of fields to update

    Returns:
        Updated constraint dict
    """
    supabase = get_supabase()

    # Validate updates
    if "constraint_type" in updates and updates["constraint_type"] not in CONSTRAINT_TYPES:
        del updates["constraint_type"]

    if "severity" in updates and updates["severity"] not in SEVERITY_LEVELS:
        del updates["severity"]

    # Convert UUID lists to strings
    if "linked_feature_ids" in updates:
        updates["linked_feature_ids"] = [str(fid) for fid in updates["linked_feature_ids"]]

    if "linked_vp_step_ids" in updates:
        updates["linked_vp_step_ids"] = [str(vid) for vid in updates["linked_vp_step_ids"]]

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    response = (
        supabase.table("constraints")
        .update(updates)
        .eq("id", str(constraint_id))
        .execute()
    )

    if not response.data:
        raise ValueError(f"Constraint not found: {constraint_id}")

    logger.info(f"Updated constraint {constraint_id}", extra={"constraint_id": str(constraint_id)})

    return response.data[0]


def delete_constraint(constraint_id: UUID) -> bool:
    """Delete a constraint."""
    supabase = get_supabase()

    response = (
        supabase.table("constraints")
        .delete()
        .eq("id", str(constraint_id))
        .execute()
    )

    logger.info(f"Deleted constraint {constraint_id}", extra={"constraint_id": str(constraint_id)})

    return True


def update_constraint_status(
    constraint_id: UUID,
    status: str,
) -> dict[str, Any]:
    """
    Update confirmation status for a constraint.

    Args:
        constraint_id: Constraint UUID
        status: New confirmation status

    Returns:
        Updated constraint dict
    """
    return update_constraint(constraint_id, {"confirmation_status": status})


def upsert_constraint(
    project_id: UUID,
    title: str,
    constraint_type: str,
    **kwargs,
) -> dict[str, Any]:
    """
    Upsert a constraint (insert or update by project_id + title + type).

    If a constraint with the same title and type exists, update it.
    Otherwise, create a new one.
    """
    supabase = get_supabase()

    # Check for existing
    existing = (
        supabase.table("constraints")
        .select("id")
        .eq("project_id", str(project_id))
        .eq("title", title)
        .eq("constraint_type", constraint_type)
        .maybe_single()
        .execute()
    )

    if existing.data:
        # Update existing
        return update_constraint(UUID(existing.data["id"]), kwargs)
    else:
        # Create new
        return create_constraint(
            project_id=project_id,
            title=title,
            constraint_type=constraint_type,
            **kwargs,
        )


def get_must_have_constraints(project_id: UUID) -> list[dict[str, Any]]:
    """Get all must_have constraints for a project."""
    return list_constraints(project_id, severity="must_have")


def get_risks(project_id: UUID) -> list[dict[str, Any]]:
    """Get all risk-type constraints for a project."""
    return list_constraints(project_id, constraint_type="risk")


def get_kpis(project_id: UUID) -> list[dict[str, Any]]:
    """Get all KPI-type constraints for a project."""
    return list_constraints(project_id, constraint_type="kpi")


def link_constraint_to_feature(
    constraint_id: UUID,
    feature_id: UUID,
) -> dict[str, Any]:
    """Link a constraint to a feature."""
    constraint = get_constraint(constraint_id)
    if not constraint:
        raise ValueError(f"Constraint not found: {constraint_id}")

    linked = constraint.get("linked_feature_ids", []) or []
    feature_str = str(feature_id)

    if feature_str not in linked:
        linked.append(feature_str)

    return update_constraint(constraint_id, {"linked_feature_ids": linked})


def link_constraint_to_vp_step(
    constraint_id: UUID,
    vp_step_id: UUID,
) -> dict[str, Any]:
    """Link a constraint to a VP step."""
    constraint = get_constraint(constraint_id)
    if not constraint:
        raise ValueError(f"Constraint not found: {constraint_id}")

    linked = constraint.get("linked_vp_step_ids", []) or []
    step_str = str(vp_step_id)

    if step_str not in linked:
        linked.append(step_str)

    return update_constraint(constraint_id, {"linked_vp_step_ids": linked})
