"""Process design preferences from extracted facts into project foundation."""

from uuid import UUID

from app.core.logging import get_logger
from app.db.competitor_refs import list_competitor_refs
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def aggregate_design_preferences(project_id: UUID) -> dict | None:
    """
    Aggregate design preferences from competitor_references (design_inspiration type).

    Returns a design_preferences dict suitable for project_foundation.
    """
    refs = list_competitor_refs(project_id)

    design_refs = [r for r in refs if r.get("reference_type") == "design_inspiration"]
    feature_refs = [r for r in refs if r.get("reference_type") == "feature_inspiration"]

    if not design_refs and not feature_refs:
        return None

    # Build references list from design_inspiration
    references = [r.get("name") for r in design_refs if r.get("name")]

    # Add feature inspirations as references too
    references.extend([r.get("name") for r in feature_refs if r.get("name")])

    # Deduplicate
    references = list(set(references))

    if not references:
        return None

    return {
        "visual_style": None,  # Would need extraction to determine
        "references": references,
        "anti_references": [],  # Would need explicit extraction
        "specific_requirements": [],
    }


def update_foundation_design_preferences(project_id: UUID) -> bool:
    """
    Update project_foundation.design_preferences from aggregated references.

    Returns True if updated, False if no changes needed.
    """
    prefs = aggregate_design_preferences(project_id)

    if not prefs:
        return False

    supabase = get_supabase()

    # Check if foundation exists
    response = (
        supabase.table("project_foundation")
        .select("id, design_preferences")
        .eq("project_id", str(project_id))
        .maybe_single()
        .execute()
    )

    if response.data:
        # Update existing
        existing_prefs = response.data.get("design_preferences") or {}

        # Merge references (don't overwrite if already populated)
        merged_refs = list(set(existing_prefs.get("references", []) + prefs["references"]))

        updated_prefs = {
            **existing_prefs,
            "references": merged_refs,
        }

        supabase.table("project_foundation").update({
            "design_preferences": updated_prefs,
        }).eq("project_id", str(project_id)).execute()

        logger.info(
            f"Updated design_preferences for project {project_id}: {len(merged_refs)} references"
        )
    else:
        # Create foundation row
        supabase.table("project_foundation").insert({
            "project_id": str(project_id),
            "design_preferences": prefs,
        }).execute()

        logger.info(f"Created foundation with design_preferences for project {project_id}")

    return True
