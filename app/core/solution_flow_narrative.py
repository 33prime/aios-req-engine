"""Solution Flow background narrative builder.

Zero-LLM-cost provenance narrative from DB reads.
Builds 2-4 sentence narrative explaining where a step came from
and how confident its grounding is.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


def build_step_narrative(step: dict[str, Any], project_id: UUID) -> str:
    """Build a provenance narrative for a solution flow step.

    Sources:
    - Linked entity names + confirmation statuses
    - Linked entity signal counts (from source_signal_ids)
    - Step's own revision count and preserved_from_version

    Returns a 2-4 sentence human-readable narrative.
    """
    from app.core.solution_flow_context import _resolve_entity_names_batch
    from app.db.supabase_client import get_supabase

    parts: list[str] = []

    # Resolve linked entity names and statuses
    ids_by_table: dict[str, list[str]] = {}
    for key, table in [
        ("linked_feature_ids", "features"),
        ("linked_workflow_ids", "workflows"),
        ("linked_data_entity_ids", "data_entities"),
    ]:
        ids = step.get(key) or []
        if ids:
            ids_by_table[table] = ids

    if not ids_by_table:
        return "This step was generated from project context without specific entity links."

    name_lookup = _resolve_entity_names_batch(ids_by_table)

    # Batch-fetch entity details per table (replaces N+1 per-ID queries)
    supabase = get_supabase()
    entity_details: list[str] = []

    for table, ids in ids_by_table.items():
        entity_type = {
            "features": "Feature",
            "workflows": "Workflow",
            "data_entities": "Data Entity",
        }.get(table, "Entity")

        # Single batch query for all IDs in this table
        status_map: dict[str, dict] = {}
        try:
            result = supabase.table(table).select(
                "id, confirmation_status, source_signal_ids"
            ).in_("id", ids).execute()
            status_map = {row["id"]: row for row in (result.data or [])}
        except Exception:
            pass

        for eid in ids:
            name = name_lookup.get(eid, eid[:8])
            data = status_map.get(eid)
            if data:
                status = data.get("confirmation_status", "ai_generated")
                signals = data.get("source_signal_ids") or []
                signal_count = len(signals) if isinstance(signals, list) else 0
                status_label = _format_status(status)
                entity_details.append(
                    f"{entity_type}: {name} ({status_label}, {signal_count} signal{'s' if signal_count != 1 else ''})"
                )
            else:
                entity_details.append(f"{entity_type}: {name}")

    if entity_details:
        parts.append(
            "This step was derived from " + _join_list(entity_details) + "."
        )

    # Step's own history
    preserved = step.get("preserved_from_version")
    version = step.get("generation_version", 1)

    if preserved:
        parts.append(
            f"The step was preserved from generation v{preserved} "
            f"into the current v{version}."
        )
    elif version > 1:
        parts.append(f"Generated in version {version}.")

    return " ".join(parts) if parts else ""


def _format_status(status: str) -> str:
    """Format confirmation status for display."""
    return {
        "confirmed_consultant": "confirmed by consultant",
        "confirmed_client": "confirmed by client",
        "ai_generated": "AI-generated",
        "needs_review": "needs review",
        "needs_client": "needs client input",
    }.get(status, status)


def _join_list(items: list[str]) -> str:
    """Join items with commas and 'and'."""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"
