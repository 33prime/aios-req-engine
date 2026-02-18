"""Value Path steps database operations."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase
from app.db.confirmations import upsert_confirmation_item

logger = get_logger(__name__)


def upsert_vp_step(
    project_id: UUID,
    step_index: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    # DEPRECATED: v2 pipeline uses app/db/patch_applicator.py for surgical EntityPatch CRUD
    """
    Upsert a Value Path step for a project.

    Args:
        project_id: Project UUID
        step_index: Step number (1..N)
        payload: Step data (label, status, description, user_benefit_pain, ui_overview,
                 value_created, kpi_impact, needed, sources, evidence)

    Returns:
        Upserted VP step row as dict

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    # Fields that belong in the enrichment JSON column, not as top-level columns
    ENRICHMENT_FIELDS = {
        "business_logic", "data_schema", "transition_logic",
        "validation_rules", "error_handling", "integration_points",
        "enhanced_fields", "enrichment_model", "enrichment_prompt_version",
        "enrichment_schema_version",
    }

    # Valid top-level columns in vp_steps table
    VALID_COLUMNS = {
        "project_id", "step_index", "sort_order", "label", "status",
        "description", "user_benefit_pain", "ui_overview", "value_created",
        "kpi_impact", "needed", "sources", "evidence", "enrichment",
        "enrichment_updated_at", "created_at", "updated_at",
        "confirmation_status",  # ai_generated, confirmed_consultant, needs_client, confirmed_client
        # Workflow-related columns
        "workflow_id", "time_minutes", "pain_description", "benefit_description",
        "automation_level", "operation_type", "actor_persona_name",
    }

    try:
        # Separate enrichment fields from base payload
        enrichment_data = {}
        base_payload = {}

        for key, value in payload.items():
            if key in ENRICHMENT_FIELDS:
                enrichment_data[key] = value
            elif key in VALID_COLUMNS:
                base_payload[key] = value
            else:
                # Unknown field - try to put in enrichment to avoid errors
                logger.warning(f"Unknown VP step field '{key}' - storing in enrichment")
                enrichment_data[key] = value

        # Merge project_id and step_index into payload
        # Set sort_order if not provided (step_index * 10)
        data = {
            "project_id": str(project_id),
            "step_index": step_index,
            "sort_order": base_payload.get("sort_order", step_index * 10),
            **base_payload,
        }

        # Ensure required fields have default values (description is NOT NULL in DB)
        if not data.get("description"):
            data["description"] = data.get("label", f"Step {step_index}")

        # If there are enrichment fields, merge them into enrichment column
        if enrichment_data:
            existing_enrichment = data.get("enrichment", {}) or {}
            merged_enrichment = {**existing_enrichment, **enrichment_data}
            data["enrichment"] = merged_enrichment

        response = (
            supabase.table("vp_steps")
            .upsert(data, on_conflict="project_id,step_index")
            .execute()
        )

        if not response.data:
            raise ValueError("No data returned from upsert_vp_step")

        step = response.data[0]
        logger.info(
            f"Upserted VP step {step_index} for project {project_id}",
            extra={"project_id": str(project_id), "step_index": step_index},
        )

        # Record impact tracking if evidence is present
        if "evidence" in payload and payload["evidence"]:
            try:
                from app.db.signals import record_chunk_impacts

                chunk_ids = [e.get("chunk_id") for e in payload["evidence"] if e.get("chunk_id")]
                if chunk_ids:
                    record_chunk_impacts(
                        chunk_ids=chunk_ids,
                        entity_type="vp_step",
                        entity_id=UUID(step["id"]),
                        usage_context="evidence",
                    )
            except Exception as e:
                logger.warning(
                    f"Failed to record impact for VP step {step['id']}: {e}",
                    extra={"step_id": step["id"]},
                )
                # Don't fail the upsert if impact tracking fails

        return step

    except Exception as e:
        logger.error(
            f"Failed to upsert VP step {step_index}: {e}",
            extra={"project_id": str(project_id), "step_index": step_index},
        )
        raise


def list_vp_steps(project_id: UUID) -> list[dict[str, Any]]:
    """
    List all Value Path steps for a project.

    Args:
        project_id: Project UUID

    Returns:
        List of VP step dicts ordered by step_index

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("vp_steps")
            .select("*")
            .eq("project_id", str(project_id))
            .order("step_index")
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(f"Failed to list VP steps for project {project_id}: {e}")
        raise


def update_vp_step_status(
    step_id: UUID,
    status: str,
) -> dict[str, Any]:
    """
    Update the status of a VP step.

    Args:
        step_id: VP step UUID
        status: New status value

    Returns:
        Updated VP step dict

    Raises:
        ValueError: If step not found
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        # Build update data
        update_data = {
            "status": status,
            "confirmation_status": status,
        }

        # Mark as consultant edited if consultant confirms
        if status == "confirmed_consultant":
            update_data["consultant_edited"] = True
            update_data["consultant_edited_at"] = "now()"

        # Update step
        response = (
            supabase.table("vp_steps")
            .update(update_data)
            .eq("id", str(step_id))
            .execute()
        )

        if not response.data:
            raise ValueError(f"VP step not found: {step_id}")

        updated_step = response.data[0]
        logger.info(f"Updated status for VP step {step_id} to {status}")

        # If marked as needs_client, create a confirmation item
        if status == "needs_client":
            project_id = updated_step.get("project_id")
            step_index = updated_step.get("step_index", 0)
            label = updated_step.get("label", f"Step {step_index}")

            # Get needed items from step if available
            needed = updated_step.get("needed", [])
            ask = needed[0].get("ask", f"Please review and confirm {label}.") if needed else f"Please review and confirm {label}."
            why = needed[0].get("why", "Consultant marked this step as needing client input.") if needed else "Consultant marked this step as needing client input."

            try:
                upsert_confirmation_item(
                    project_id=UUID(project_id),
                    key=f"vp:step{step_index}:manual",
                    payload={
                        "kind": "vp",
                        "title": f"Confirm: {label}",
                        "why": why,
                        "ask": ask,
                        "priority": "medium",
                        "suggested_method": "meeting",
                        "status": "open",
                        "target_table": "vp_steps",
                        "target_id": str(step_id),
                    }
                )
                logger.info(f"Created confirmation item for VP step {step_id}")
            except Exception as conf_err:
                logger.warning(f"Failed to create confirmation item: {conf_err}")

        # Refresh readiness cache when entity changes
        try:
            from app.core.readiness_cache import refresh_cached_readiness
            project_id = UUID(updated_step["project_id"])
            refresh_cached_readiness(project_id)
        except Exception as cache_err:
            logger.warning(f"Failed to refresh readiness cache: {cache_err}")

        return updated_step

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Failed to update status for VP step {step_id}: {e}")
        raise


def patch_vp_step_enrichment(
    step_id: UUID,
    enrichment: dict[str, Any],
    model: str | None = None,
    prompt_version: str | None = None,
    schema_version: str | None = None,
) -> dict[str, Any]:
    """
    Patch the enrichment column of a VP step with enrichment data.

    Args:
        step_id: VP step UUID
        enrichment: The enrichment data to store
        model: Optional model name used for enrichment
        prompt_version: Optional prompt version used
        schema_version: Optional schema version used

    Returns:
        Updated VP step dict

    Raises:
        ValueError: If step not found
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        # Prepare update payload
        update_data = {
            "enrichment": enrichment,
            "enrichment_updated_at": "now()",
        }

        if model:
            update_data["enrichment_model"] = model
        if prompt_version:
            update_data["enrichment_prompt_version"] = prompt_version
        if schema_version:
            update_data["enrichment_schema_version"] = schema_version

        response = supabase.table("vp_steps").update(update_data).eq("id", str(step_id)).execute()

        if not response.data:
            raise ValueError(f"VP step not found: {step_id}")

        updated_step = response.data[0]
        logger.info(f"Updated enrichment for VP step {step_id}")

        return updated_step

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Failed to patch enrichment for VP step {step_id}: {e}")
        raise


def get_vp_step(step_id: UUID) -> dict[str, Any]:
    """
    Get VP step by ID.

    Args:
        step_id: VP step UUID

    Returns:
        VP step dict with all fields

    Raises:
        ValueError: If VP step not found
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("vp_steps")
            .select("*")
            .eq("id", str(step_id))
            .maybe_single()
            .execute()
        )

        if not response.data:
            raise ValueError(f"VP step {step_id} not found")

        return response.data

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Failed to get VP step {step_id}: {e}")
        raise


def update_vp_step(
    step_id: UUID,
    updates: dict[str, Any],
    run_id: UUID | None = None,
    source_signal_id: UUID | None = None,
    trigger_event: str = "manual_update",
) -> dict[str, Any]:
    """
    Update VP step fields.

    This function is used by the A-Team agent to apply surgical patches
    to VP steps. It updates only the specified fields.

    Args:
        step_id: VP step UUID to update
        updates: Dict of field → new value
        run_id: Optional run ID for tracking
        source_signal_id: Optional signal that triggered this update
        trigger_event: What triggered this update (default: manual_update)

    Returns:
        Updated VP step dict

    Raises:
        ValueError: If VP step not found
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        # Get current state BEFORE update for change tracking
        old_step = get_vp_step(step_id)

        # Add updated_at timestamp
        update_data = {**updates, "updated_at": "now()"}

        response = (
            supabase.table("vp_steps")
            .update(update_data)
            .eq("id", str(step_id))
            .execute()
        )

        if not response.data:
            raise ValueError(f"Failed to update VP step {step_id}")

        updated_step = response.data[0]
        logger.info(
            f"Updated VP step {step_id}",
            extra={"step_id": str(step_id), "fields_updated": list(updates.keys())},
        )

        # Track change (non-blocking)
        try:
            from app.core.change_tracking import track_entity_change
            track_entity_change(
                project_id=UUID(old_step["project_id"]),
                entity_type="vp_step",
                entity_id=step_id,
                entity_label=f"Step {old_step.get('step_index', '?')}: {old_step.get('label', 'Untitled')}",
                old_entity=old_step,
                new_entity=updated_step,
                trigger_event=trigger_event,
                source_signal_id=source_signal_id,
                run_id=run_id,
                created_by="system",
            )
        except Exception as track_err:
            logger.warning(f"Failed to track VP step change: {track_err}")

        # Refresh readiness cache when entity changes
        try:
            from app.core.readiness_cache import refresh_cached_readiness
            project_id = UUID(updated_step["project_id"])
            refresh_cached_readiness(project_id)
        except Exception as cache_err:
            logger.warning(f"Failed to refresh readiness cache: {cache_err}")

        return updated_step

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Failed to update VP step {step_id}: {e}")
        raise

