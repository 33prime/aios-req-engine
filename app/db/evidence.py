"""Database operations for evidence quality tracking."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

# Entity tables that have confirmation_status
ENTITY_TABLES = [
    "features",
    "personas",
    "vp_steps",
    "business_drivers",
]


def get_evidence_quality(project_id: UUID) -> dict[str, Any]:
    """
    Get evidence quality breakdown for a project.

    Aggregates confirmation_status across all entity types to provide
    a project-level view of evidence strength.

    Args:
        project_id: Project UUID

    Returns:
        Dict with:
        - breakdown: Counts by confirmation status
        - total_entities: Total entity count
        - strong_evidence_percentage: % with client or consultant confirmation
        - summary: Human-readable summary
    """
    supabase = get_supabase()

    # Aggregate counts across all entity tables
    totals = {
        "confirmed_client": 0,
        "confirmed_consultant": 0,
        "needs_client": 0,
        "ai_generated": 0,
    }

    entity_counts: dict[str, dict[str, int]] = {}

    for table in ENTITY_TABLES:
        try:
            # Get all entities for project with confirmation_status
            response = (
                supabase.table(table)
                .select("confirmation_status")
                .eq("project_id", str(project_id))
                .execute()
            )

            entities = response.data or []
            table_counts = {
                "confirmed_client": 0,
                "confirmed_consultant": 0,
                "needs_client": 0,
                "ai_generated": 0,
            }

            for entity in entities:
                status = entity.get("confirmation_status", "ai_generated")
                if status in table_counts:
                    table_counts[status] += 1
                    totals[status] += 1

            entity_counts[table] = table_counts

        except Exception as e:
            logger.warning(f"Failed to get counts from {table}: {e}")
            continue

    # Calculate totals and percentages
    total_entities = sum(totals.values())

    if total_entities > 0:
        strong_count = totals["confirmed_client"] + totals["confirmed_consultant"]
        strong_percentage = round((strong_count / total_entities) * 100)
    else:
        strong_percentage = 0

    # Build breakdown with percentages
    breakdown = {}
    for status, count in totals.items():
        percentage = round((count / total_entities) * 100) if total_entities > 0 else 0
        breakdown[status] = {
            "count": count,
            "percentage": percentage,
        }

    # Generate summary
    if strong_percentage >= 70:
        summary = f"{strong_percentage}% of entities have strong evidence (excellent)"
    elif strong_percentage >= 50:
        summary = f"{strong_percentage}% of entities have strong evidence (good)"
    elif strong_percentage >= 30:
        summary = f"{strong_percentage}% of entities have strong evidence (developing)"
    else:
        summary = f"{strong_percentage}% of entities have strong evidence (needs attention)"

    logger.info(
        f"Got evidence quality for project {project_id}: {strong_percentage}% strong",
        extra={
            "project_id": str(project_id),
            "total_entities": total_entities,
            "strong_percentage": strong_percentage,
        },
    )

    return {
        "breakdown": breakdown,
        "by_entity_type": entity_counts,
        "total_entities": total_entities,
        "strong_evidence_percentage": strong_percentage,
        "summary": summary,
    }
