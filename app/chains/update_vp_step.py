"""Surgical VP step update chain.

Updates individual VP steps when inputs change, rather than regenerating
the entire value path. Uses change detection to determine impact.
"""

import json
from typing import Any
from uuid import UUID

from openai import OpenAI

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.schemas_vp_v2 import SurgicalUpdateOutput, VPChangeEvent, VPStepUpdate
from app.db.features import list_features
from app.db.personas import list_personas
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


SURGICAL_UPDATE_PROMPT = """You are updating a specific Value Path step based on a change to its inputs.

You will receive:
1. The current VP step content
2. Information about what changed (feature enriched, persona updated, etc.)
3. The new/updated data

Your job is to surgically update ONLY the affected parts of the VP step, preserving everything else.

Output a JSON object with the updates to apply:
{
  "updates": {
    "narrative_user": "Updated narrative if user actions changed",
    "narrative_system": "Updated system narrative if behaviors changed",
    "rules_applied": ["Updated rules if rules changed"],
    "integrations_triggered": ["Updated integrations if changed"],
    "evidence": [{"chunk_id": null, "excerpt": "...", "source_type": "signal", "rationale": "..."}]
  },
  "reason": "Brief explanation of what was updated and why"
}

RULES:
1. Only include fields that need to change in "updates"
2. Preserve the step's overall narrative flow
3. If change doesn't affect this step, return {"updates": {}, "reason": "No updates needed"}
4. Output ONLY valid JSON, no markdown"""


def find_affected_steps(
    project_id: UUID,
    change: VPChangeEvent,
) -> list[dict[str, Any]]:
    """
    Find VP steps affected by a change.

    Args:
        project_id: Project UUID
        change: The change event

    Returns:
        List of affected VP step records
    """
    supabase = get_supabase()

    # Get all VP steps
    response = (
        supabase.table("vp_steps")
        .select("*")
        .eq("project_id", str(project_id))
        .execute()
    )
    all_steps = response.data or []

    affected = []

    for step in all_steps:
        is_affected = False

        if change.entity_type == "feature":
            # Check if this step uses the changed feature
            features_used = step.get("features_used", [])
            for f in features_used:
                if f.get("feature_id") == change.entity_id:
                    is_affected = True
                    break

        elif change.entity_type == "persona":
            # Check if this step's actor is the changed persona
            if step.get("actor_persona_id") == change.entity_id:
                is_affected = True

        elif change.entity_type == "signal":
            # New signal - check if any evidence references it
            evidence = step.get("evidence", [])
            for ev in evidence:
                if ev.get("chunk_id") and change.entity_id in str(ev.get("chunk_id", "")):
                    is_affected = True
                    break

        if is_affected:
            affected.append(step)

    return affected


def calculate_impact_ratio(
    project_id: UUID,
    affected_steps: list[dict],
) -> float:
    """
    Calculate what percentage of VP steps are affected.

    Args:
        project_id: Project UUID
        affected_steps: List of affected steps

    Returns:
        Impact ratio (0.0 to 1.0)
    """
    supabase = get_supabase()

    # Get total step count
    response = (
        supabase.table("vp_steps")
        .select("id", count="exact")
        .eq("project_id", str(project_id))
        .execute()
    )
    total = response.count or 0

    if total == 0:
        return 1.0  # No steps = need full generation

    return len(affected_steps) / total


def update_single_step(
    step: dict[str, Any],
    change: VPChangeEvent,
    changed_entity: dict[str, Any],
) -> VPStepUpdate | None:
    """
    Update a single VP step based on a change.

    Args:
        step: Current VP step data
        change: The change event
        changed_entity: The new/updated entity data

    Returns:
        VPStepUpdate if updates needed, None otherwise
    """
    settings = get_settings()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # Build context for the LLM
    prompt = f"""# Surgical VP Step Update

## Current Step
Step {step.get('step_index')}: {step.get('label')}

Current narrative_user:
{step.get('narrative_user', '')}

Current narrative_system:
{step.get('narrative_system', '')}

Current rules_applied: {json.dumps(step.get('rules_applied', []))}
Current integrations: {json.dumps(step.get('integrations_triggered', []))}

## Change Event
Type: {change.change_type}
Entity: {change.entity_type} - {change.entity_name}

## Updated Entity Data
{json.dumps(changed_entity, indent=2, default=str)[:2000]}

## Instructions
Determine what parts of this VP step need to be updated based on the change.
Only update fields that are actually affected.
Preserve the overall narrative flow and tone.
"""

    response = client.chat.completions.create(
        model=settings.FEATURES_ENRICH_MODEL,
        temperature=0.2,
        max_tokens=2048,
        messages=[
            {"role": "system", "content": SURGICAL_UPDATE_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )

    raw_output = response.choices[0].message.content or ""

    # Parse response
    try:
        cleaned = raw_output.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        cleaned = cleaned.strip()

        result = json.loads(cleaned)
        updates = result.get("updates", {})
        reason = result.get("reason", "Unknown")

        if not updates:
            return None

        return VPStepUpdate(
            step_id=step["id"],
            updates=updates,
            reason=reason,
        )

    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Failed to parse surgical update response: {e}")
        return None


def apply_step_updates(updates: list[VPStepUpdate]) -> int:
    """
    Apply updates to VP steps in the database.

    Args:
        updates: List of step updates to apply

    Returns:
        Number of steps updated
    """
    supabase = get_supabase()
    updated = 0

    for update in updates:
        try:
            # Build update data
            update_data = {
                **update.updates,
                "is_stale": False,
                "stale_reason": None,
                "updated_at": "now()",
            }

            # Check if evidence changed - update has_signal_evidence
            if "evidence" in update.updates:
                evidence = update.updates["evidence"]
                has_signal = any(
                    e.get("source_type") == "signal" for e in evidence
                )
                update_data["has_signal_evidence"] = has_signal
                if has_signal:
                    update_data["confirmation_status"] = "confirmed_consultant"

            supabase.table("vp_steps").update(update_data).eq("id", update.step_id).execute()
            updated += 1

            logger.info(f"Updated VP step {update.step_id}: {update.reason}")

        except Exception as e:
            logger.error(f"Failed to update VP step {update.step_id}: {e}")

    return updated


def mark_steps_stale(
    project_id: UUID,
    step_ids: list[str],
    reason: str,
) -> int:
    """
    Mark VP steps as stale.

    Args:
        project_id: Project UUID
        step_ids: Steps to mark stale
        reason: Why they're stale

    Returns:
        Number of steps marked stale
    """
    supabase = get_supabase()

    for step_id in step_ids:
        supabase.table("vp_steps").update({
            "is_stale": True,
            "stale_reason": reason,
            "updated_at": "now()",
        }).eq("id", step_id).execute()

    return len(step_ids)


def process_change_queue(project_id: UUID) -> dict[str, Any]:
    """
    Process pending changes in the VP change queue.

    Determines whether to do surgical updates or full regeneration.

    Args:
        project_id: Project UUID

    Returns:
        Summary of processing results
    """
    from app.chains.generate_value_path_v2 import generate_and_save_value_path

    supabase = get_supabase()

    # Get unprocessed changes
    response = (
        supabase.table("vp_change_queue")
        .select("*")
        .eq("project_id", str(project_id))
        .eq("processed", False)
        .order("created_at")
        .execute()
    )
    changes = response.data or []

    if not changes:
        return {"message": "No pending changes", "processed": 0}

    # Find all affected steps
    all_affected_ids = set()
    change_events = []

    for change in changes:
        event = VPChangeEvent(
            change_type=change["change_type"],
            entity_type=change["entity_type"],
            entity_id=change["entity_id"],
            entity_name=change.get("entity_name"),
            change_details=change.get("change_details", {}),
        )
        change_events.append((change, event))

        affected = find_affected_steps(project_id, event)
        all_affected_ids.update(s["id"] for s in affected)

    # Calculate impact
    impact_ratio = calculate_impact_ratio(project_id, list(all_affected_ids))

    logger.info(
        f"VP change processing: {len(changes)} changes, {len(all_affected_ids)} affected steps, {impact_ratio:.1%} impact"
    )

    result = {
        "changes_processed": len(changes),
        "affected_steps": len(all_affected_ids),
        "impact_ratio": impact_ratio,
    }

    if impact_ratio >= 0.5:
        # Major change - full regeneration
        logger.info("Impact >= 50%, triggering full VP regeneration")
        gen_result = generate_and_save_value_path(project_id)
        result["action"] = "full_regeneration"
        result["generation_result"] = gen_result
    else:
        # Surgical updates
        logger.info(f"Surgical update for {len(all_affected_ids)} steps")

        # Get current steps
        steps_response = (
            supabase.table("vp_steps")
            .select("*")
            .eq("project_id", str(project_id))
            .in_("id", list(all_affected_ids))
            .execute()
        )
        affected_steps = {s["id"]: s for s in (steps_response.data or [])}

        updates = []
        for change_record, event in change_events:
            # Get the changed entity
            changed_entity = _get_entity(event.entity_type, event.entity_id)
            if not changed_entity:
                continue

            # Update each affected step
            for step_id in all_affected_ids:
                step = affected_steps.get(step_id)
                if not step or step.get("consultant_edited"):
                    continue

                update = update_single_step(step, event, changed_entity)
                if update:
                    updates.append(update)

        # Apply updates
        updated_count = apply_step_updates(updates)
        result["action"] = "surgical_update"
        result["steps_updated"] = updated_count

    # Mark changes as processed
    for change in changes:
        supabase.table("vp_change_queue").update({
            "processed": True,
            "processed_at": "now()",
            "affected_step_ids": list(all_affected_ids),
        }).eq("id", change["id"]).execute()

    return result


def _get_entity(entity_type: str, entity_id: str) -> dict[str, Any] | None:
    """Get an entity by type and ID."""
    supabase = get_supabase()

    table = {
        "feature": "features",
        "persona": "personas",
        "signal": "signals",
    }.get(entity_type)

    if not table:
        return None

    try:
        response = supabase.table(table).select("*").eq("id", entity_id).single().execute()
        return response.data
    except Exception:
        return None


def queue_change(
    project_id: UUID,
    change_type: str,
    entity_type: str,
    entity_id: UUID,
    entity_name: str | None = None,
    change_details: dict | None = None,
) -> str:
    """
    Queue a change for VP processing.

    Args:
        project_id: Project UUID
        change_type: Type of change
        entity_type: Type of entity
        entity_id: Entity UUID
        entity_name: Optional entity name
        change_details: Optional additional details

    Returns:
        Change queue entry ID
    """
    supabase = get_supabase()

    response = supabase.table("vp_change_queue").insert({
        "project_id": str(project_id),
        "change_type": change_type,
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "entity_name": entity_name,
        "change_details": change_details or {},
    }).execute()

    return response.data[0]["id"] if response.data else ""
