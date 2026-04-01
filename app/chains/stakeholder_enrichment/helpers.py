"""Shared helpers for stakeholder enrichment chains.

Field change tracking and update application — preserved from
the old SI agent tools to maintain enrichment_revisions tracking.
"""

from uuid import UUID

from app.core.logging import get_logger
from app.db.stakeholders import update_stakeholder

logger = get_logger(__name__)


def track_field_changes(
    stakeholder_id: UUID,
    project_id: UUID,
    stakeholder: dict,
    updates: dict,
    source: str = "si_enrichment",
) -> list[str]:
    """Track which fields changed and record enrichment revision."""
    from app.db.supabase_client import get_supabase

    changed_fields = []
    changes = {}

    skip = {
        "updated_at", "version", "intelligence_version",
        "last_intelligence_at", "profile_completeness",
    }

    for key, new_val in updates.items():
        if key in skip:
            continue
        old_val = stakeholder.get(key)
        if old_val != new_val and new_val is not None:
            changed_fields.append(key)
            changes[key] = {
                "old": str(old_val)[:200] if old_val else None,
                "new": str(new_val)[:200],
            }

    if changed_fields:
        try:
            sb = get_supabase()
            current_version = stakeholder.get("version", 1)
            sb.table("enrichment_revisions").insert({
                "project_id": str(project_id),
                "entity_type": "stakeholder",
                "entity_id": str(stakeholder_id),
                "entity_label": stakeholder.get("name", "")[:100],
                "revision_type": "enriched",
                "changes": changes,
                "revision_number": current_version + 1,
                "diff_summary": (
                    f"Enriched: {', '.join(changed_fields[:5])}"
                ),
                "created_by": source,
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to track enrichment revision: {e}")

    return changed_fields


def apply_updates(
    stakeholder_id: UUID,
    project_id: UUID,
    stakeholder: dict,
    updates: dict,
) -> tuple[dict, list[str]]:
    """Apply updates, track changes, bump version."""
    current_version = stakeholder.get("version", 1)
    intel_version = stakeholder.get("intelligence_version", 0)

    updates["version"] = current_version + 1
    updates["intelligence_version"] = intel_version + 1
    updates["last_intelligence_at"] = "now()"

    changed = track_field_changes(
        stakeholder_id, project_id, stakeholder, updates,
    )

    result = update_stakeholder(stakeholder_id, updates)
    return result, changed
