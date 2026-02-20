"""EntityPatch Applicator — surgical persistence for Signal Pipeline v2.

Applies EntityPatch[] to the database with:
- Confidence-based auto-apply (high+ → apply, low/conflict → escalate)
- Confirmation hierarchy protection (never downgrade confirmed entities)
- Evidence appending (merge operations)
- State revision tracking
- Staleness propagation

Usage:
    from app.db.patch_applicator import apply_entity_patches

    result = await apply_entity_patches(
        project_id=project_id,
        patches=entity_patches,
        run_id=run_id,
        signal_id=signal_id,
    )
"""

from __future__ import annotations

import logging
import re
from typing import Any
from uuid import UUID, uuid4

from app.core.schemas_entity_patch import (
    ConfidenceTier,
    EntityPatch,
    PatchApplicationResult,
)
from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)


# Confidence tiers that get auto-applied
AUTO_APPLY_TIERS: set[ConfidenceTier] = {"very_high", "high", "medium"}

# Confirmation hierarchy — higher index = stronger, never downgrade
CONFIRMATION_HIERARCHY = {
    "ai_generated": 0,
    "needs_client": 1,
    "confirmed_consultant": 2,
    "confirmed_client": 3,
}

# Authority → confirmation status mapping
AUTHORITY_TO_STATUS = {
    "client": "confirmed_client",
    "consultant": "confirmed_consultant",
    "research": "ai_generated",
    "prototype": "ai_generated",
}

# Entity type → table name mapping
ENTITY_TABLE_MAP = {
    "feature": "features",
    "persona": "personas",
    "stakeholder": "stakeholders",
    "workflow": "workflows",
    "workflow_step": "vp_steps",
    "data_entity": "data_entities",
    "business_driver": "business_drivers",
    "constraint": "constraints",
    "competitor": "competitor_references",
    "vision": "projects",  # Vision is stored on the project itself
    "solution_flow_step": "solution_flow_steps",
}

# Tables that have a slug column
TABLES_WITH_SLUG = {"prd_sections", "personas"}

# Tables that have source_signal_ids UUID[] column
TABLES_WITH_SIGNAL_IDS = {
    "features", "personas", "prd_sections", "stakeholders",
    "business_drivers", "competitor_references",
    "vp_steps", "constraints", "data_entities",
}

# Tables that have a version INTEGER column
TABLES_WITH_VERSION = {
    "features", "personas", "vp_steps", "constraints",
    "business_drivers", "competitor_references", "data_entities", "stakeholders",
    "solution_flow_steps",
}

# Field name normalization: LLM-generated names → actual DB column names
TABLE_FIELD_RENAMES: dict[str, dict[str, str]] = {
    "constraints": {"name": "title"},
}


async def apply_entity_patches(
    project_id: UUID,
    patches: list[EntityPatch],
    run_id: UUID,
    signal_id: UUID | None = None,
    auto_apply_threshold: set[ConfidenceTier] | None = None,
) -> PatchApplicationResult:
    """Apply a batch of EntityPatches to the database.

    Args:
        project_id: Project UUID
        patches: List of EntityPatch to apply
        run_id: Run tracking UUID
        signal_id: Source signal UUID (for evidence linking)
        auto_apply_threshold: Override which confidence tiers auto-apply

    Returns:
        PatchApplicationResult with applied/skipped/escalated details
    """
    if auto_apply_threshold is None:
        auto_apply_threshold = AUTO_APPLY_TIERS

    result = PatchApplicationResult()

    for patch in patches:
        # Escalate low-confidence and conflict patches
        if patch.confidence not in auto_apply_threshold:
            result.escalated.append({
                "entity_type": patch.entity_type,
                "operation": patch.operation,
                "reason": f"Confidence '{patch.confidence}' below auto-apply threshold",
                "patch_summary": _summarize_patch(patch),
                "confidence": patch.confidence,
                "confidence_reasoning": patch.confidence_reasoning,
            })
            continue

        try:
            applied = await _apply_single_patch(project_id, patch, signal_id, run_id)
            if applied:
                result.applied.append(applied)
                result.entity_ids_modified.append(applied["entity_id"])

                # Increment counters
                op = applied["operation"]
                if op == "create":
                    result.created_count += 1
                elif op == "merge":
                    result.merged_count += 1
                elif op == "update":
                    result.updated_count += 1
                elif op == "stale":
                    result.staled_count += 1
                elif op == "delete":
                    result.deleted_count += 1
            else:
                result.skipped.append({
                    "entity_type": patch.entity_type,
                    "reason": "Apply returned None (entity not found or no-op)",
                    "patch_summary": _summarize_patch(patch),
                })
        except Exception as e:
            logger.error(f"Failed to apply patch: {e}", exc_info=True)
            result.skipped.append({
                "entity_type": patch.entity_type,
                "reason": f"Error: {str(e)[:200]}",
                "patch_summary": _summarize_patch(patch),
            })

    # Record state revision if anything was applied
    if result.entity_ids_modified:
        try:
            _record_state_revision(project_id, run_id, signal_id, result)
        except Exception as e:
            logger.warning(f"State revision recording failed: {e}")

    # Record chunk impacts for evidence tracking
    if signal_id and result.applied:
        try:
            _record_evidence_links(patches, result.applied)
        except Exception as e:
            logger.warning(f"Evidence link recording failed: {e}")

    logger.info(
        f"Patch application complete: {result.total_applied} applied, "
        f"{len(result.skipped)} skipped, {result.total_escalated} escalated"
    )

    return result


# =============================================================================
# Single patch dispatch
# =============================================================================


async def _apply_single_patch(
    project_id: UUID,
    patch: EntityPatch,
    signal_id: UUID | None,
    run_id: UUID | None = None,
) -> dict | None:
    """Apply a single EntityPatch. Returns applied dict or None."""
    operation = patch.operation
    entity_type = patch.entity_type

    # Special case: vision patches update the project directly
    if entity_type == "vision":
        return _apply_vision_patch(project_id, patch)

    table = ENTITY_TABLE_MAP.get(entity_type)
    if not table:
        logger.warning(f"Unknown entity type: {entity_type}")
        return None

    # Resolve truncated UUIDs (LLM sometimes outputs only prefix)
    if patch.target_entity_id and operation in ("merge", "update", "stale", "delete"):
        patch = _resolve_target_entity_id(project_id, patch, table)

    if operation == "create":
        return _apply_create(project_id, patch, table, signal_id, run_id)
    elif operation == "merge":
        return _apply_merge(project_id, patch, table, signal_id, run_id)
    elif operation == "update":
        return _apply_update(project_id, patch, table, signal_id, run_id)
    elif operation == "stale":
        return _apply_stale(patch, table)
    elif operation == "delete":
        return _apply_delete(patch, table)
    else:
        logger.warning(f"Unknown operation: {operation}")
        return None


# =============================================================================
# UUID resolution (prefix-matching fallback)
# =============================================================================


# Standard UUID length with dashes: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
_FULL_UUID_LEN = 36


def _resolve_target_entity_id(
    project_id: UUID,
    patch: EntityPatch,
    table: str,
) -> EntityPatch:
    """Resolve truncated target_entity_id to full UUID via prefix match.

    LLMs sometimes output only the first 8 chars of a UUID. This queries the
    project's entities to find the unique match. If ambiguous (multiple matches)
    or not found, returns the patch unchanged (will fail naturally downstream).
    """
    target_id = patch.target_entity_id
    if not target_id or len(target_id) >= _FULL_UUID_LEN:
        return patch  # Already full UUID or missing

    # Try to parse as a valid UUID first — if it works, it's already valid
    try:
        UUID(target_id)
        return patch  # Valid UUID (e.g. 32 hex chars without dashes)
    except ValueError:
        pass  # Not a valid UUID, try prefix match

    # Only attempt prefix matching for hex-like strings (UUID fragments)
    # Skip obviously non-UUID strings like "feat-1", "my-entity", etc.
    stripped = target_id.lower().replace("-", "")
    if not stripped or not all(c in "0123456789abcdef" for c in stripped):
        return patch  # Not a UUID prefix

    sb = get_supabase()
    prefix = stripped

    try:
        # Query entities in this project, filter by ID prefix using LIKE
        # Postgres UUID cast to text for prefix matching
        response = (
            sb.table(table)
            .select("id")
            .eq("project_id", str(project_id))
            .execute()
        )
        candidates = response.data or []

        matches = [
            str(c["id"]) for c in candidates
            if str(c["id"]).replace("-", "").startswith(prefix)
        ]

        if len(matches) == 1:
            resolved_id = matches[0]
            logger.info(
                f"Resolved truncated UUID {target_id!r} → {resolved_id} "
                f"for {patch.entity_type} {patch.operation}"
            )
            # Return a new patch with the resolved ID
            return EntityPatch(
                operation=patch.operation,
                entity_type=patch.entity_type,
                target_entity_id=resolved_id,
                payload=patch.payload,
                evidence=patch.evidence,
                confidence=patch.confidence,
                confidence_reasoning=patch.confidence_reasoning,
                source_authority=patch.source_authority,
                mention_count=patch.mention_count,
                belief_impact=patch.belief_impact,
                answers_question=patch.answers_question,
            )
        elif len(matches) > 1:
            logger.warning(
                f"Ambiguous UUID prefix {target_id!r}: {len(matches)} matches in {table}"
            )
        else:
            logger.warning(
                f"No match for UUID prefix {target_id!r} in {table} (project {project_id})"
            )
    except Exception as e:
        logger.warning(f"UUID prefix resolution failed: {e}")

    return patch  # Return unchanged


# =============================================================================
# Payload normalization
# =============================================================================


def _normalize_payload(table: str, payload: dict) -> dict:
    """Normalize LLM-generated payload fields to match actual DB columns.

    - Renames fields per TABLE_FIELD_RENAMES (e.g. constraints.name → title)
    - Strips slug for tables that don't have it
    - Strips source_signal_ids for tables that don't have it
    """
    result = payload.copy()

    # Apply field renames for this table
    renames = TABLE_FIELD_RENAMES.get(table, {})
    for old_name, new_name in renames.items():
        if old_name in result and new_name not in result:
            result[new_name] = result.pop(old_name)
        elif old_name in result:
            del result[old_name]  # new_name already set, drop duplicate

    # Strip slug for tables that don't have it
    if table not in TABLES_WITH_SLUG and "slug" in result:
        del result["slug"]

    # Strip source_signal_ids for tables that don't have it
    if table not in TABLES_WITH_SIGNAL_IDS and "source_signal_ids" in result:
        del result["source_signal_ids"]

    return result


# =============================================================================
# Operation handlers
# =============================================================================


def _apply_create(
    project_id: UUID,
    patch: EntityPatch,
    table: str,
    signal_id: UUID | None,
    run_id: UUID | None = None,
) -> dict | None:
    """Create a new entity from patch payload."""
    sb = get_supabase()
    payload = patch.payload.copy()

    # Set standard fields
    payload["project_id"] = str(project_id)
    confirmation_status = AUTHORITY_TO_STATUS.get(patch.source_authority, "ai_generated")
    payload["confirmation_status"] = confirmation_status

    # Generate slug only for tables that have the column
    if table in TABLES_WITH_SLUG:
        name = payload.get("name", payload.get("label", "unnamed"))
        if "slug" not in payload and name:
            payload["slug"] = re.sub(r"[^a-z0-9]+", "-", name.lower())[:50]

    # Add evidence from signal (only for tables with source_signal_ids)
    if signal_id and table in TABLES_WITH_SIGNAL_IDS and "source_signal_ids" not in payload:
        payload["source_signal_ids"] = [str(signal_id)]

    # Add evidence quotes to evidence field if entity supports it
    if patch.evidence:
        existing_evidence = payload.get("evidence") or []
        for ev in patch.evidence:
            existing_evidence.append({
                "chunk_id": ev.chunk_id,
                "quote": ev.quote,
                "page_or_section": ev.page_or_section,
            })
        payload["evidence"] = existing_evidence

    # Set initial version for tables that support it
    if table in TABLES_WITH_VERSION:
        payload.setdefault("version", 1)

    # Normalize payload fields to match actual DB columns
    payload = _normalize_payload(table, payload)

    # Resolve display name for logging (check all common name columns)
    display_name = (
        payload.get("name")
        or payload.get("label")
        or payload.get("title")
        or payload.get("description", "unnamed")
    )

    try:
        response = sb.table(table).insert(payload).execute()
        if response.data:
            entity = response.data[0]
            entity_id = str(entity.get("id", ""))

            # Record revision (fire-and-forget)
            _record_entity_revision(
                project_id=project_id,
                entity_type=patch.entity_type,
                entity_id=entity_id,
                entity_label=display_name,
                old_entity=None,
                new_entity=entity,
                operation="create",
                signal_id=signal_id,
                run_id=run_id,
            )

            return {
                "entity_type": patch.entity_type,
                "entity_id": entity_id,
                "operation": "create",
                "name": display_name,
                "confirmation_status": confirmation_status,
            }
    except Exception as e:
        logger.error(f"Create failed for {patch.entity_type}: {e}")
        raise

    return None


def _apply_merge(
    project_id: UUID,
    patch: EntityPatch,
    table: str,
    signal_id: UUID | None,
    run_id: UUID | None = None,
) -> dict | None:
    """Merge new evidence/data into an existing entity."""
    if not patch.target_entity_id:
        logger.warning("Merge patch missing target_entity_id")
        return None

    sb = get_supabase()

    # Load existing entity
    try:
        response = (
            sb.table(table)
            .select("*")
            .eq("id", patch.target_entity_id)
            .single()
            .execute()
        )
        existing = response.data
    except Exception:
        logger.warning(f"Entity {patch.target_entity_id} not found for merge")
        return None

    if not existing:
        return None

    # Check confirmation hierarchy — don't downgrade
    existing_status = existing.get("confirmation_status", "ai_generated")
    new_status = AUTHORITY_TO_STATUS.get(patch.source_authority, "ai_generated")
    if CONFIRMATION_HIERARCHY.get(new_status, 0) < CONFIRMATION_HIERARCHY.get(existing_status, 0):
        new_status = existing_status  # Keep higher status

    updates: dict[str, Any] = {"updated_at": "now()"}

    # Merge evidence
    if patch.evidence:
        existing_evidence = existing.get("evidence") or []
        for ev in patch.evidence:
            existing_evidence.append({
                "chunk_id": ev.chunk_id,
                "quote": ev.quote,
                "page_or_section": ev.page_or_section,
            })
        updates["evidence"] = existing_evidence

    # Merge signal IDs (only for tables that have the column)
    if signal_id and table in TABLES_WITH_SIGNAL_IDS:
        existing_signals = existing.get("source_signal_ids") or []
        signal_str = str(signal_id)
        if signal_str not in existing_signals:
            existing_signals.append(signal_str)
            updates["source_signal_ids"] = existing_signals

    # Merge payload fields (only update non-confirmed fields)
    normalized_payload = _normalize_payload(table, patch.payload)
    for field, value in normalized_payload.items():
        if field in ("id", "project_id", "created_at", "updated_at"):
            continue
        existing_value = existing.get(field)
        if existing_value is None or existing_status == "ai_generated":
            updates[field] = value

    # Upgrade confirmation status if warranted
    if CONFIRMATION_HIERARCHY.get(new_status, 0) > CONFIRMATION_HIERARCHY.get(existing_status, 0):
        updates["confirmation_status"] = new_status

    # Increment version for tables that support it
    if table in TABLES_WITH_VERSION:
        updates["version"] = (existing.get("version") or 1) + 1

    entity_name = existing.get("name", existing.get("label", existing.get("title", "")))

    try:
        update_response = sb.table(table).update(updates).eq("id", patch.target_entity_id).execute()
        updated_row = update_response.data[0] if update_response.data else {**existing, **updates}

        # Record revision (fire-and-forget)
        _record_entity_revision(
            project_id=project_id,
            entity_type=patch.entity_type,
            entity_id=patch.target_entity_id,
            entity_label=entity_name,
            old_entity=existing,
            new_entity=updated_row,
            operation="merge",
            signal_id=signal_id,
            run_id=run_id,
        )

        return {
            "entity_type": patch.entity_type,
            "entity_id": patch.target_entity_id,
            "operation": "merge",
            "name": entity_name,
            "fields_merged": list(updates.keys()),
        }
    except Exception as e:
        logger.error(f"Merge failed for {patch.target_entity_id}: {e}")
        raise


def _apply_update(
    project_id: UUID,
    patch: EntityPatch,
    table: str,
    signal_id: UUID | None = None,
    run_id: UUID | None = None,
) -> dict | None:
    """Update specific fields on an existing entity."""
    if not patch.target_entity_id:
        logger.warning("Update patch missing target_entity_id")
        return None

    sb = get_supabase()

    # Load existing to check confirmation hierarchy
    try:
        response = (
            sb.table(table)
            .select("*")
            .eq("id", patch.target_entity_id)
            .single()
            .execute()
        )
        existing = response.data
    except Exception:
        logger.warning(f"Entity {patch.target_entity_id} not found for update")
        return None

    if not existing:
        return None

    existing_status = existing.get("confirmation_status", "ai_generated")
    new_authority_status = AUTHORITY_TO_STATUS.get(patch.source_authority, "ai_generated")

    # Don't update confirmed entities from weaker authority
    if (
        CONFIRMATION_HIERARCHY.get(existing_status, 0) > CONFIRMATION_HIERARCHY.get(new_authority_status, 0)
        and existing_status != "ai_generated"
    ):
        logger.info(
            f"Skipping update to {patch.target_entity_id}: "
            f"confirmed at {existing_status}, patch authority is {patch.source_authority}"
        )
        return None

    # Normalize payload fields to match actual DB columns
    normalized_payload = _normalize_payload(table, patch.payload)

    updates: dict[str, Any] = {"updated_at": "now()"}
    for field, value in normalized_payload.items():
        if field in ("id", "project_id", "created_at"):
            continue
        updates[field] = value

    # Increment version for tables that support it
    if table in TABLES_WITH_VERSION:
        updates["version"] = (existing.get("version") or 1) + 1

    entity_name = existing.get("name", existing.get("label", existing.get("title", "")))

    try:
        update_response = sb.table(table).update(updates).eq("id", patch.target_entity_id).execute()
        updated_row = update_response.data[0] if update_response.data else {**existing, **updates}

        # Record revision (fire-and-forget)
        _record_entity_revision(
            project_id=project_id,
            entity_type=patch.entity_type,
            entity_id=patch.target_entity_id,
            entity_label=entity_name,
            old_entity=existing,
            new_entity=updated_row,
            operation="update",
            signal_id=signal_id,
            run_id=run_id,
        )

        return {
            "entity_type": patch.entity_type,
            "entity_id": patch.target_entity_id,
            "operation": "update",
            "name": entity_name,
            "fields_updated": list(normalized_payload.keys()),
        }
    except Exception as e:
        logger.error(f"Update failed for {patch.target_entity_id}: {e}")
        raise


def _apply_stale(
    patch: EntityPatch,
    table: str,
) -> dict | None:
    """Mark an entity as stale."""
    if not patch.target_entity_id:
        logger.warning("Stale patch missing target_entity_id")
        return None

    sb = get_supabase()
    stale_reason = patch.payload.get("stale_reason", "Contradicted by new signal")

    try:
        sb.table(table).update({
            "is_stale": True,
            "stale_reason": stale_reason,
            "stale_since": "now()",
            "updated_at": "now()",
        }).eq("id", patch.target_entity_id).execute()

        return {
            "entity_type": patch.entity_type,
            "entity_id": patch.target_entity_id,
            "operation": "stale",
            "stale_reason": stale_reason,
        }
    except Exception as e:
        logger.error(f"Stale marking failed for {patch.target_entity_id}: {e}")
        raise


def _apply_delete(
    patch: EntityPatch,
    table: str,
) -> dict | None:
    """Soft-delete if ai_generated, mark stale if confirmed."""
    if not patch.target_entity_id:
        logger.warning("Delete patch missing target_entity_id")
        return None

    sb = get_supabase()

    # Check current status
    try:
        response = (
            sb.table(table)
            .select("confirmation_status, name")
            .eq("id", patch.target_entity_id)
            .single()
            .execute()
        )
        existing = response.data
    except Exception:
        return None

    if not existing:
        return None

    existing_status = existing.get("confirmation_status", "ai_generated")

    if existing_status == "ai_generated":
        # Safe to delete ai_generated entities
        try:
            sb.table(table).delete().eq("id", patch.target_entity_id).execute()
            return {
                "entity_type": patch.entity_type,
                "entity_id": patch.target_entity_id,
                "operation": "delete",
                "name": existing.get("name", ""),
            }
        except Exception as e:
            logger.error(f"Delete failed for {patch.target_entity_id}: {e}")
            raise
    else:
        # Confirmed entities get marked stale instead
        return _apply_stale(
            EntityPatch(
                operation="stale",
                entity_type=patch.entity_type,
                target_entity_id=patch.target_entity_id,
                payload={"stale_reason": "Marked for deletion by new signal, but confirmed — needs review"},
                confidence=patch.confidence,
                source_authority=patch.source_authority,
            ),
            table,
        )


def _apply_vision_patch(project_id: UUID, patch: EntityPatch) -> dict | None:
    """Special handler: update vision statement on the project."""
    sb = get_supabase()
    statement = patch.payload.get("statement", "")
    if not statement:
        return None

    try:
        sb.table("projects").update({
            "vision": statement,
            "updated_at": "now()",
        }).eq("id", str(project_id)).execute()

        return {
            "entity_type": "vision",
            "entity_id": str(project_id),
            "operation": patch.operation,
            "name": statement[:80],
        }
    except Exception as e:
        logger.error(f"Vision update failed: {e}")
        raise


# =============================================================================
# Helpers
# =============================================================================


def _summarize_patch(patch: EntityPatch) -> str:
    """Short summary of a patch for logging/escalation."""
    name = (
        patch.payload.get("name")
        or patch.payload.get("label")
        or patch.payload.get("title")
        or patch.payload.get("description", "")
    )
    return f"{patch.operation} {patch.entity_type}: {name}"[:100]


def _record_state_revision(
    project_id: UUID,
    run_id: UUID,
    signal_id: UUID | None,
    result: PatchApplicationResult,
) -> None:
    """Record a state revision for audit trail."""
    from app.db.revisions import insert_state_revision

    insert_state_revision(
        project_id=project_id,
        run_id=run_id,
        job_id=None,
        input_summary={
            "source": "signal_pipeline_v2",
            "signal_id": str(signal_id) if signal_id else None,
            "patches_applied": result.total_applied,
            "patches_escalated": result.total_escalated,
        },
        diff={
            "created": result.created_count,
            "merged": result.merged_count,
            "updated": result.updated_count,
            "staled": result.staled_count,
            "deleted": result.deleted_count,
            "entity_ids": result.entity_ids_modified,
        },
    )


def _record_entity_revision(
    project_id: UUID,
    entity_type: str,
    entity_id: str,
    entity_label: str,
    old_entity: dict | None,
    new_entity: dict,
    operation: str,
    signal_id: UUID | None,
    run_id: UUID | None,
) -> None:
    """Fire-and-forget revision tracking after patch application."""
    try:
        from app.core.change_tracking import track_entity_change

        track_entity_change(
            project_id=project_id,
            entity_type=entity_type,
            entity_id=UUID(entity_id),
            entity_label=entity_label,
            old_entity=old_entity,
            new_entity=new_entity,
            trigger_event=f"signal_pipeline_v2_{operation}",
            source_signal_id=signal_id,
            run_id=run_id,
            created_by="signal_pipeline_v2",
        )
    except Exception as e:
        logger.debug(f"Revision tracking failed for {entity_type} {entity_id}: {e}")


def _record_evidence_links(
    patches: list[EntityPatch],
    applied_results: list[dict],
) -> None:
    """Link chunk evidence to modified entities.

    Iterates applied patches and calls record_chunk_impacts per entity,
    matching patches to their applied results by target_entity_id.
    """
    from app.db.signals import record_chunk_impacts

    # Build map of entity_id → applied result (for merge/update/stale matches)
    applied_map = {a["entity_id"]: a for a in applied_results}

    for patch in patches:
        if not patch.evidence:
            continue

        chunk_ids = [ev.chunk_id for ev in patch.evidence if ev.chunk_id]
        if not chunk_ids:
            continue

        # Find the entity_id — for merge/update it's target_entity_id,
        # for create it's in the applied results
        entity_id = patch.target_entity_id
        if not entity_id:
            # For creates, match by entity_type + name in applied results
            for a in applied_results:
                if a["entity_type"] == patch.entity_type and a["operation"] == "create":
                    entity_id = a["entity_id"]
                    break

        if not entity_id or entity_id not in applied_map:
            continue

        try:
            record_chunk_impacts(
                chunk_ids=chunk_ids,
                entity_type=patch.entity_type,
                entity_id=UUID(entity_id),
            )
        except Exception as e:
            logger.warning(f"Evidence link failed for {entity_id}: {e}")
