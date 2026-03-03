"""Client Portal Validation API endpoints.

Validation queue + verdict submission. Each verdict creates an audit trail
row and fires a signal into the V2 pipeline.
"""

import logging
from datetime import UTC
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth_middleware import require_portal_access
from app.core.schemas_portal import (
    BatchVerdictRequest,
    SubmitVerdictRequest,
    ValidationItem,
    ValidationQueueResponse,
    VerdictResponse,
)
from app.db.stakeholder_assignments import (
    count_assignments_by_status,
    create_verdict,
    get_assignment_for_entity,
    get_verdict_for_entity,
    list_assignments,
    update_assignment_status,
)
from app.db.supabase_client import get_supabase as get_client

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/portal/projects/{project_id}/validation",
    tags=["portal_validation"],
)


# ============================================================================
# Helpers
# ============================================================================


def _get_user_stakeholder(project_id: UUID, user_id: UUID) -> dict | None:
    """Get the stakeholder linked to a user for this project."""
    client = get_client()
    result = (
        client.table("stakeholders")
        .select("*")
        .eq("project_id", str(project_id))
        .eq("user_id", str(user_id))
        .maybe_single()
        .execute()
    )
    return result.data


def _load_entity_details(entity_type: str, entity_id: str) -> dict:
    """Load entity details for display in the validation card."""
    client = get_client()
    table_map = {
        "workflow": "workflows",
        "business_driver": "business_drivers",
        "feature": "features",
        "persona": "personas",
        "vp_step": "vp_steps",
        "prototype_epic": "prototype_epic_confirmations",
    }
    table = table_map.get(entity_type)
    if not table:
        return {}
    try:
        result = (
            client.table(table)
            .select("*")
            .eq("id", entity_id)
            .maybe_single()
            .execute()
        )
        return result.data or {}
    except Exception:
        return {}


def _entity_to_validation_item(
    assignment: dict,
    entity: dict,
    existing_verdict: dict | None,
    is_mine: bool,
) -> ValidationItem:
    """Convert an assignment + entity into a ValidationItem."""
    etype = assignment["entity_type"]

    # Build name and summary based on entity type
    name = entity.get("name") or entity.get("title") or f"{etype} {assignment['entity_id'][:8]}"
    summary = entity.get("description") or entity.get("summary") or entity.get("overview") or ""

    # Type-specific details
    details: dict = {}
    if etype == "workflow":
        details["state_type"] = entity.get("state_type")
        details["frequency_per_week"] = entity.get("frequency_per_week")
        details["hourly_rate"] = entity.get("hourly_rate")
    elif etype == "business_driver":
        details["impact_area"] = entity.get("impact_area")
        details["priority"] = entity.get("priority")
        details["measurement"] = entity.get("measurement_method")
    elif etype == "feature":
        details["target_personas"] = entity.get("target_personas")
        details["enrichment_status"] = entity.get("enrichment_status")
    elif etype == "persona":
        details["goals"] = entity.get("goals")
        details["pain_points"] = entity.get("pain_points")

    return ValidationItem(
        id=assignment["id"],
        entity_type=etype,
        entity_id=assignment["entity_id"],
        name=name,
        summary=summary[:300] if summary else None,
        details=details,
        priority=assignment.get("priority", 3),
        reason=assignment.get("reason"),
        assignment_id=assignment["id"],
        existing_verdict=existing_verdict["verdict"] if existing_verdict else None,
        existing_notes=existing_verdict.get("notes") if existing_verdict else None,
        is_assigned_to_me=is_mine,
    )


async def _create_validation_signal(
    project_id: UUID,
    user_id: UUID,
    entity_type: str,
    entity_id: str,
    verdict: str,
    notes: str | None,
    stakeholder_name: str | None = None,
) -> UUID | None:
    """Create a signal from a validation verdict for V2 processing."""
    try:
        client = get_client()
        signal_id = uuid4()

        verdict_text = f"Stakeholder validation: {verdict}"
        if stakeholder_name:
            verdict_text = f"{stakeholder_name} — {verdict_text}"
        if notes:
            verdict_text += f"\nNotes: {notes}"

        client.table("signals").insert({
            "id": str(signal_id),
            "project_id": str(project_id),
            "signal_type": "stakeholder_validation",
            "source": "client_portal",
            "source_type": "stakeholder_validation",
            "source_label": f"Validation: {entity_type}/{entity_id[:8]} → {verdict}",
            "raw_text": verdict_text,
            "metadata": {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "verdict": verdict,
                "authority": "client",
                "validated_by": str(user_id),
            },
            "run_id": str(uuid4()),
        }).execute()

        # Fire V2 pipeline (non-blocking best-effort)
        try:
            from app.graphs.unified_processor import process_signal_v2
            await process_signal_v2(
                signal_id=signal_id,
                project_id=project_id,
                run_id=uuid4(),
            )
        except Exception as proc_err:
            logger.warning(f"V2 processing failed for verdict signal (non-fatal): {proc_err}")

        return signal_id
    except Exception as e:
        logger.error(f"Failed to create validation signal: {e}")
        return None


def _update_entity_confirmation(entity_type: str, entity_id: str, verdict: str, user_id: UUID):
    """Update the entity's confirmation_status based on verdict."""
    if verdict != "confirmed":
        return

    client = get_client()
    table_map = {
        "workflow": "workflows",
        "business_driver": "business_drivers",
        "feature": "features",
        "persona": "personas",
        "vp_step": "vp_steps",
    }
    table = table_map.get(entity_type)
    if not table:
        return

    try:
        from datetime import datetime
        client.table(table).update({
            "confirmation_status": "confirmed_client",
            "confirmed_at": datetime.now(UTC).isoformat(),
            "confirmed_by": str(user_id),
        }).eq("id", entity_id).execute()
    except Exception as e:
        logger.warning(f"Failed to update entity confirmation (non-fatal): {e}")


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/queue", response_model=ValidationQueueResponse)
async def get_validation_queue(
    project_id: UUID,
    entity_type: str | None = None,
    auth_and_role: tuple = Depends(require_portal_access),
):
    """Get the validation queue.

    Admin sees all items; client_user sees only their assignments.
    """
    auth, portal_role = auth_and_role

    # Get user's stakeholder (if linked)
    stakeholder = _get_user_stakeholder(project_id, auth.user_id)
    stakeholder_id = UUID(stakeholder["id"]) if stakeholder else None

    # Load assignments
    if portal_role == "client_admin":
        assignments = list_assignments(project_id, entity_type=entity_type)
    elif stakeholder_id:
        assignments = list_assignments(
            project_id, stakeholder_id=stakeholder_id, entity_type=entity_type
        )
    else:
        assignments = []

    # Build items with entity details
    items = []
    for assignment in assignments:
        entity = _load_entity_details(assignment["entity_type"], assignment["entity_id"])
        existing_verdict = None
        if stakeholder_id:
            existing_verdict = get_verdict_for_entity(
                assignment["entity_type"], assignment["entity_id"], stakeholder_id
            )
        is_mine = stakeholder_id and assignment["stakeholder_id"] == str(stakeholder_id)
        item = _entity_to_validation_item(assignment, entity, existing_verdict, is_mine)
        items.append(item)

    # Build summary counts
    counts = count_assignments_by_status(project_id)
    by_type = {}
    for et, status_counts in counts.get("by_type", {}).items():
        by_type[et] = status_counts.get("pending", 0)

    return ValidationQueueResponse(
        total_pending=counts["by_status"].get("pending", 0),
        by_type=by_type,
        urgent_count=sum(1 for i in items if i.priority <= 2 and not i.existing_verdict),
        items=items,
    )


@router.get("/queue/{entity_type}", response_model=list[ValidationItem])
async def get_validation_items_by_type(
    project_id: UUID,
    entity_type: str,
    auth_and_role: tuple = Depends(require_portal_access),
):
    """Get validation items for a specific entity type."""
    auth, portal_role = auth_and_role
    stakeholder = _get_user_stakeholder(project_id, auth.user_id)
    stakeholder_id = UUID(stakeholder["id"]) if stakeholder else None

    if portal_role == "client_admin":
        assignments = list_assignments(project_id, entity_type=entity_type)
    elif stakeholder_id:
        assignments = list_assignments(
            project_id, stakeholder_id=stakeholder_id, entity_type=entity_type
        )
    else:
        assignments = []

    items = []
    for assignment in assignments:
        entity = _load_entity_details(assignment["entity_type"], assignment["entity_id"])
        existing_verdict = None
        if stakeholder_id:
            existing_verdict = get_verdict_for_entity(
                assignment["entity_type"], assignment["entity_id"], stakeholder_id
            )
        is_mine = stakeholder_id and assignment["stakeholder_id"] == str(stakeholder_id)
        items.append(_entity_to_validation_item(assignment, entity, existing_verdict, is_mine))

    return items


@router.post("/verdict", response_model=VerdictResponse)
async def submit_verdict(
    project_id: UUID,
    request: SubmitVerdictRequest,
    auth_and_role: tuple = Depends(require_portal_access),
):
    """Submit a validation verdict (confirm/refine/flag).

    Creates audit trail, updates entity confirmation status, creates signal.
    """
    auth, portal_role = auth_and_role

    if request.verdict not in ("confirmed", "refine", "flag"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verdict must be 'confirmed', 'refine', or 'flag'",
        )

    # Get user's stakeholder
    stakeholder = _get_user_stakeholder(project_id, auth.user_id)
    if not stakeholder:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No stakeholder profile linked to your account",
        )
    stakeholder_id = UUID(stakeholder["id"])

    # Find matching assignment (if any)
    assignment = get_assignment_for_entity(
        stakeholder_id, request.entity_type, request.entity_id
    )
    assignment_id = UUID(assignment["id"]) if assignment else None

    # Create signal
    signal_id = await _create_validation_signal(
        project_id=project_id,
        user_id=auth.user_id,
        entity_type=request.entity_type,
        entity_id=request.entity_id,
        verdict=request.verdict,
        notes=request.notes,
        stakeholder_name=stakeholder.get("name"),
    )

    # Create verdict row
    verdict_row = create_verdict(
        project_id=project_id,
        stakeholder_id=stakeholder_id,
        user_id=auth.user_id,
        entity_type=request.entity_type,
        entity_id=request.entity_id,
        verdict=request.verdict,
        notes=request.notes,
        refinement_details=request.refinement_details,
        assignment_id=assignment_id,
        signal_id=signal_id,
    )

    # Update assignment status
    if assignment_id:
        update_assignment_status(assignment_id, "completed")

    # Update entity confirmation status on confirm
    _update_entity_confirmation(
        request.entity_type, request.entity_id, request.verdict, auth.user_id
    )

    # Trigger notifications
    try:
        from app.core.portal_notifications import notify_verdict_submitted
        notify_verdict_submitted(
            project_id=project_id,
            stakeholder_name=stakeholder.get("name", "Unknown"),
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            verdict=request.verdict,
        )
    except Exception as e:
        logger.warning(f"Notification failed (non-fatal): {e}")

    return VerdictResponse(
        verdict_id=UUID(verdict_row["id"]),
        entity_type=request.entity_type,
        entity_id=request.entity_id,
        verdict=request.verdict,
        signal_id=signal_id,
    )


@router.post("/verdict/batch", response_model=list[VerdictResponse])
async def submit_batch_verdicts(
    project_id: UUID,
    request: BatchVerdictRequest,
    auth_and_role: tuple = Depends(require_portal_access),
):
    """Batch confirm multiple entities.

    Creates one bundled signal per batch, individual verdict rows.
    """
    auth, portal_role = auth_and_role

    stakeholder = _get_user_stakeholder(project_id, auth.user_id)
    if not stakeholder:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No stakeholder profile linked to your account",
        )
    stakeholder_id = UUID(stakeholder["id"])

    # Create one bundled signal for the batch
    batch_text = f"Batch validation by {stakeholder.get('name', 'Stakeholder')}:\n"
    for v in request.verdicts:
        batch_text += f"- {v.entity_type}/{v.entity_id[:8]}: {v.verdict}"
        if v.notes:
            batch_text += f" ({v.notes})"
        batch_text += "\n"

    try:
        client = get_client()
        signal_id = uuid4()
        client.table("signals").insert({
            "id": str(signal_id),
            "project_id": str(project_id),
            "signal_type": "stakeholder_validation",
            "source": "client_portal",
            "source_type": "stakeholder_validation",
            "source_label": f"Batch validation: {len(request.verdicts)} items",
            "raw_text": batch_text,
            "metadata": {
                "batch": True,
                "count": len(request.verdicts),
                "authority": "client",
                "validated_by": str(auth.user_id),
            },
            "run_id": str(uuid4()),
        }).execute()

        # Fire V2 pipeline
        try:
            from app.graphs.unified_processor import process_signal_v2
            await process_signal_v2(signal_id=signal_id, project_id=project_id, run_id=uuid4())
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Failed to create batch signal: {e}")
        signal_id = None

    responses = []
    for v in request.verdicts:
        assignment = get_assignment_for_entity(stakeholder_id, v.entity_type, v.entity_id)
        assignment_id = UUID(assignment["id"]) if assignment else None

        verdict_row = create_verdict(
            project_id=project_id,
            stakeholder_id=stakeholder_id,
            user_id=auth.user_id,
            entity_type=v.entity_type,
            entity_id=v.entity_id,
            verdict=v.verdict,
            notes=v.notes,
            refinement_details=v.refinement_details,
            assignment_id=assignment_id,
            signal_id=signal_id,
        )

        if assignment_id:
            update_assignment_status(assignment_id, "completed")

        _update_entity_confirmation(v.entity_type, v.entity_id, v.verdict, auth.user_id)

        responses.append(VerdictResponse(
            verdict_id=UUID(verdict_row["id"]),
            entity_type=v.entity_type,
            entity_id=v.entity_id,
            verdict=v.verdict,
            signal_id=signal_id,
        ))

    return responses
