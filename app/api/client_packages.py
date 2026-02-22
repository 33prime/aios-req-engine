"""API endpoints for client packages (AI-synthesized questions for clients)."""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.auth_middleware import AuthContext, require_consultant
from app.core.schemas_collaboration import (
    ClientPackage,
    GeneratePackageRequest,
    GeneratePackageResponse,
    PendingItem,
    PendingItemsQueue,
    PhaseProgressResponse,
)
from app.core.phase_state_machine import (
    build_phase_config,
    build_phase_state,
    get_all_phases_status,
    CollaborationPhase,
)
from app.db.supabase_client import get_supabase as get_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collaboration", tags=["collaboration"])


# ============================================================================
# Phase Progress
# ============================================================================


@router.get("/projects/{project_id}/progress", response_model=PhaseProgressResponse)
async def get_phase_progress(
    project_id: UUID,
    auth: AuthContext = Depends(require_consultant),
):
    """
    Get the current phase progress with gates, steps, and pending queue.

    This is the main endpoint for the Collaboration tab.
    """
    client = get_client()

    # Get project and current phase
    project_result = client.table("projects").select(
        "collaboration_phase, portal_enabled"
    ).eq("id", str(project_id)).single().execute()

    if not project_result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    current_phase_str = project_result.data.get("collaboration_phase", "pre_discovery")
    try:
        current_phase = CollaborationPhase(current_phase_str)
    except ValueError:
        current_phase = CollaborationPhase.PRE_DISCOVERY

    portal_enabled = project_result.data.get("portal_enabled", False)

    # Build phase state
    state = await build_phase_state(project_id, current_phase)

    # Build phase config
    phase_config = build_phase_config(current_phase, state)

    # Get all phases status
    phases = get_all_phases_status(current_phase)

    # Get pending items queue
    pending_queue = await get_pending_items_queue(project_id)

    # Get draft/sent packages
    draft_package = await get_package_by_status(project_id, "draft")
    sent_package = await get_package_by_status(project_id, "sent")

    # Get client count
    members_result = client.table("project_members").select("id").eq(
        "project_id", str(project_id)
    ).eq("role", "client").execute()
    clients_count = len(members_result.data)

    # Get last client activity
    # TODO: Implement actual activity tracking
    last_client_activity = None

    return PhaseProgressResponse(
        project_id=project_id,
        current_phase=current_phase,
        phases=phases,
        phase_config=phase_config,
        readiness_score=phase_config.readiness_score,
        readiness_gates=phase_config.gates,
        pending_queue=pending_queue,
        draft_package=draft_package,
        sent_package=sent_package,
        package_responses=None,  # TODO: Add response tracking
        portal_enabled=portal_enabled,
        clients_count=clients_count,
        last_client_activity=last_client_activity,
    )


# ============================================================================
# Pending Items Queue
# ============================================================================


@router.get("/projects/{project_id}/pending-items")
async def list_pending_items(
    project_id: UUID,
    item_type: Optional[str] = None,
    status: str = "pending",
    auth: AuthContext = Depends(require_consultant),
):
    """List pending items for a project."""
    client = get_client()

    query = client.table("pending_items").select("*").eq(
        "project_id", str(project_id)
    ).eq("status", status)

    if item_type:
        query = query.eq("item_type", item_type)

    result = query.order("created_at", desc=True).execute()

    return {"items": result.data, "count": len(result.data)}


@router.post("/projects/{project_id}/pending-items")
async def add_pending_item(
    project_id: UUID,
    item: PendingItem,
    auth: AuthContext = Depends(require_consultant),
):
    """Add an item to the pending queue."""
    client = get_client()

    item_data = {
        "project_id": str(project_id),
        "item_type": item.item_type.value,
        "source": item.source.value,
        "entity_id": str(item.entity_id) if item.entity_id else None,
        "title": item.title,
        "description": item.description,
        "why_needed": item.why_needed,
        "priority": item.priority,
        "added_by": auth.user_id and str(auth.user_id),
    }

    result = client.table("pending_items").insert(item_data).execute()

    return result.data[0]


@router.delete("/pending-items/{item_id}")
async def remove_pending_item(
    item_id: UUID,
    auth: AuthContext = Depends(require_consultant),
):
    """Remove an item from the pending queue."""
    client = get_client()

    result = client.table("pending_items").delete().eq("id", str(item_id)).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Item not found")

    return {"message": "Item removed"}


# ============================================================================
# Package Generation
# ============================================================================


@router.post("/projects/{project_id}/generate-package", response_model=GeneratePackageResponse)
async def generate_package(
    project_id: UUID,
    request: GeneratePackageRequest,
    auth: AuthContext = Depends(require_consultant),
):
    """
    Generate a client package from pending items.

    Uses AI to synthesize minimal, high-impact questions.
    """
    from app.chains.synthesize_client_package import generate_client_package

    client = get_client()

    # Get pending items
    query = client.table("pending_items").select("*").eq(
        "project_id", str(project_id)
    ).eq("status", "pending")

    if request.item_ids:
        query = query.in_("id", [str(i) for i in request.item_ids])

    items_result = query.execute()

    if not items_result.data:
        raise HTTPException(
            status_code=400,
            detail="No pending items to generate package from"
        )

    # Get project context
    project_result = client.table("projects").select(
        "name, description, collaboration_phase"
    ).eq("id", str(project_id)).single().execute()

    project_context = {
        "goal": project_result.data.get("description", "Build a software solution"),
        "industry": "Technology",  # TODO: Get from project
        "existing_context": "Discovery phase",
    }

    phase = project_result.data.get("collaboration_phase", "pre_discovery")

    # Generate package using AI
    package_data = await generate_client_package(
        project_id=project_id,
        pending_items=items_result.data,
        project_context=project_context,
        phase=phase,
        include_asset_suggestions=request.include_asset_suggestions,
        max_questions=request.max_questions,
    )

    # Save package to database
    saved_package = await save_package(project_id, package_data)

    # Update pending items to 'in_package' status
    item_ids = [item["id"] for item in items_result.data]
    client.table("pending_items").update({
        "status": "in_package",
        "package_id": saved_package["id"],
    }).in_("id", item_ids).execute()

    return GeneratePackageResponse(
        package=ClientPackage(**saved_package),
        synthesis_notes=package_data.get("synthesis_notes"),
    )


class UpdatePackageRequest(BaseModel):
    """Request to update a package before sending."""
    questions: Optional[list[dict]] = None
    action_items: Optional[list[dict]] = None


@router.patch("/packages/{package_id}")
async def update_package(
    package_id: UUID,
    request: UpdatePackageRequest,
    auth: AuthContext = Depends(require_consultant),
):
    """Update a draft package (edit questions, action items)."""
    client = get_client()

    # Verify package exists and is draft
    package_result = client.table("client_packages").select("*").eq(
        "id", str(package_id)
    ).single().execute()

    if not package_result.data:
        raise HTTPException(status_code=404, detail="Package not found")

    if package_result.data["status"] != "draft":
        raise HTTPException(status_code=400, detail="Can only edit draft packages")

    # Update questions if provided
    if request.questions is not None:
        # Delete existing and insert new
        client.table("package_questions").delete().eq(
            "package_id", str(package_id)
        ).execute()

        for i, q in enumerate(request.questions):
            client.table("package_questions").insert({
                "package_id": str(package_id),
                "question_text": q["question_text"],
                "hint": q.get("hint"),
                "suggested_answerer": q.get("suggested_answerer"),
                "why_asking": q.get("why_asking"),
                "covers_items": q.get("covers_items", []),
                "covers_summary": q.get("covers_summary"),
                "sequence_order": i,
            }).execute()

        # Update count
        client.table("client_packages").update({
            "questions_count": len(request.questions),
        }).eq("id", str(package_id)).execute()

    # Update action items if provided
    if request.action_items is not None:
        client.table("package_action_items").delete().eq(
            "package_id", str(package_id)
        ).execute()

        for i, item in enumerate(request.action_items):
            client.table("package_action_items").insert({
                "package_id": str(package_id),
                "title": item["title"],
                "description": item.get("description"),
                "item_type": item.get("item_type", "document"),
                "hint": item.get("hint"),
                "why_needed": item.get("why_needed"),
                "covers_items": item.get("covers_items", []),
                "sequence_order": i,
            }).execute()

        client.table("client_packages").update({
            "action_items_count": len(request.action_items),
        }).eq("id", str(package_id)).execute()

    return {"message": "Package updated"}


@router.post("/packages/{package_id}/send")
async def send_package(
    package_id: UUID,
    auth: AuthContext = Depends(require_consultant),
):
    """Send a package to the client portal."""
    client = get_client()

    # Get package
    package_result = client.table("client_packages").select("*").eq(
        "id", str(package_id)
    ).single().execute()

    if not package_result.data:
        raise HTTPException(status_code=404, detail="Package not found")

    if package_result.data["status"] not in ("draft", "ready"):
        raise HTTPException(status_code=400, detail="Package already sent")

    # Update package status
    now = datetime.utcnow().isoformat()
    client.table("client_packages").update({
        "status": "sent",
        "sent_at": now,
    }).eq("id", str(package_id)).execute()

    # Update pending items status
    client.table("pending_items").update({
        "status": "sent",
    }).eq("package_id", str(package_id)).execute()

    # Send email notification to clients (best-effort, don't block on failure)
    project_id = package_result.data.get("project_id")
    if project_id:
        try:
            from app.core.sendgrid_service import send_package_notification
            await send_package_notification(UUID(project_id), str(package_id))
        except Exception as e:
            logger.warning(f"Email notification failed for package {package_id}: {e}")

    return {
        "success": True,
        "package_id": str(package_id),
        "sent_at": now,
    }


@router.get("/packages/{package_id}")
async def get_package(
    package_id: UUID,
    auth: AuthContext = Depends(require_consultant),
):
    """Get a package with all its contents."""
    client = get_client()

    # Get package
    package_result = client.table("client_packages").select("*").eq(
        "id", str(package_id)
    ).single().execute()

    if not package_result.data:
        raise HTTPException(status_code=404, detail="Package not found")

    # Get questions
    questions_result = client.table("package_questions").select("*").eq(
        "package_id", str(package_id)
    ).order("sequence_order").execute()

    # Get action items
    items_result = client.table("package_action_items").select("*").eq(
        "package_id", str(package_id)
    ).order("sequence_order").execute()

    # Get asset suggestions
    assets_result = client.table("package_asset_suggestions").select("*").eq(
        "package_id", str(package_id)
    ).execute()

    package = package_result.data
    package["questions"] = questions_result.data
    package["action_items"] = items_result.data
    package["suggested_assets"] = assets_result.data

    return package


# ============================================================================
# Helper Functions
# ============================================================================


async def get_pending_items_queue(project_id: UUID) -> PendingItemsQueue:
    """Get the pending items queue for a project."""
    client = get_client()

    result = client.table("pending_items").select("*").eq(
        "project_id", str(project_id)
    ).eq("status", "pending").execute()

    items = result.data
    by_type = {}
    for item in items:
        item_type = item.get("item_type", "other")
        by_type[item_type] = by_type.get(item_type, 0) + 1

    return PendingItemsQueue(
        items=[PendingItem(**item) for item in items] if items else [],
        by_type=by_type,
        total_count=len(items),
    )


async def get_package_by_status(project_id: UUID, status: str) -> Optional[ClientPackage]:
    """Get a package by status."""
    client = get_client()

    result = client.table("client_packages").select("*").eq(
        "project_id", str(project_id)
    ).eq("status", status).order("created_at", desc=True).limit(1).execute()

    if not result.data:
        return None

    # Get questions and action items
    package = result.data[0]
    package_id = package["id"]

    questions = client.table("package_questions").select("*").eq(
        "package_id", package_id
    ).order("sequence_order").execute()

    items = client.table("package_action_items").select("*").eq(
        "package_id", package_id
    ).order("sequence_order").execute()

    assets = client.table("package_asset_suggestions").select("*").eq(
        "package_id", package_id
    ).execute()

    package["questions"] = questions.data
    package["action_items"] = items.data
    package["suggested_assets"] = assets.data

    return ClientPackage(**package)


async def save_package(project_id: UUID, package_data: dict) -> dict:
    """Save a generated package to the database."""
    client = get_client()

    # Create package record
    package_record = {
        "project_id": str(project_id),
        "status": "draft",
        "questions_count": len(package_data.get("questions", [])),
        "action_items_count": len(package_data.get("action_items", [])),
        "suggestions_count": len(package_data.get("suggested_assets", [])),
        "source_items_count": package_data.get("source_items_count", 0),
        "synthesis_notes": package_data.get("synthesis_notes"),
    }

    package_result = client.table("client_packages").insert(package_record).execute()
    package = package_result.data[0]
    package_id = package["id"]

    # Save questions
    questions = []
    for q in package_data.get("questions", []):
        q_record = {
            "package_id": package_id,
            "question_text": q["question_text"],
            "hint": q.get("hint"),
            "suggested_answerer": q.get("suggested_answerer"),
            "why_asking": q.get("why_asking"),
            "covers_items": q.get("covers_items", []),
            "covers_summary": q.get("covers_summary"),
            "sequence_order": q.get("sequence_order", 0),
        }
        result = client.table("package_questions").insert(q_record).execute()
        questions.append(result.data[0])

    # Save action items
    action_items = []
    for item in package_data.get("action_items", []):
        item_record = {
            "package_id": package_id,
            "title": item["title"],
            "description": item.get("description"),
            "item_type": item.get("item_type", "document"),
            "hint": item.get("hint"),
            "why_needed": item.get("why_needed"),
            "covers_items": item.get("covers_items", []),
            "sequence_order": item.get("sequence_order", 0),
        }
        result = client.table("package_action_items").insert(item_record).execute()
        action_items.append(result.data[0])

    # Save asset suggestions
    assets = []
    for asset in package_data.get("suggested_assets", []):
        asset_record = {
            "package_id": package_id,
            "category": asset["category"],
            "title": asset["title"],
            "description": asset["description"],
            "why_valuable": asset["why_valuable"],
            "examples": asset.get("examples", []),
            "priority": asset.get("priority", "medium"),
            "phase_relevant": asset.get("phase_relevant", []),
        }
        result = client.table("package_asset_suggestions").insert(asset_record).execute()
        assets.append(result.data[0])

    package["questions"] = questions
    package["action_items"] = action_items
    package["suggested_assets"] = assets

    return package


# ============================================================================
# Portal Endpoints (Client-Facing)
# ============================================================================


class MarkNeedsReviewRequest(BaseModel):
    """Request to mark an entity as needing client review."""
    entity_type: str = Field(..., description="Type: feature, persona, vp_step, goal, kpi, pain_point, competitor, stakeholder, workflow, data_entity, constraint, solution_flow_step")
    entity_id: UUID = Field(..., description="ID of the entity")
    reason: Optional[str] = Field(None, description="Why this needs review")


@router.post("/projects/{project_id}/mark-needs-review")
async def mark_entity_needs_review(
    project_id: UUID,
    request: MarkNeedsReviewRequest,
    auth: AuthContext = Depends(require_consultant),
):
    """
    Mark an entity as needing client review and add it to the pending queue.

    This is called from the "Needs Review" button on features, personas, etc.
    """
    client = get_client()

    # Map entity type to table and fields
    entity_configs = {
        "feature": {"table": "features", "name_field": "name", "desc_field": "overview"},
        "persona": {"table": "personas", "name_field": "name", "desc_field": "role"},
        "vp_step": {"table": "vp_steps", "name_field": "action", "desc_field": "details"},
        "goal": {"table": "business_drivers", "name_field": "description", "desc_field": "measurement", "extra_filter": ("driver_type", "goal")},
        "kpi": {"table": "business_drivers", "name_field": "description", "desc_field": "measurement", "extra_filter": ("driver_type", "kpi")},
        "pain_point": {"table": "business_drivers", "name_field": "description", "desc_field": "measurement", "extra_filter": ("driver_type", "pain")},
        "competitor": {"table": "competitor_references", "name_field": "name", "desc_field": "research_notes"},
        "stakeholder": {"table": "stakeholders", "name_field": "name", "desc_field": "role"},
        "workflow": {"table": "workflows", "name_field": "name", "desc_field": "description"},
        "data_entity": {"table": "data_entities", "name_field": "name", "desc_field": "description"},
        "constraint": {"table": "constraints", "name_field": "title", "desc_field": "description"},
        "solution_flow_step": {"table": "solution_flow_steps", "name_field": "title", "desc_field": "goal"},
    }

    config = entity_configs.get(request.entity_type)
    if not config:
        raise HTTPException(status_code=400, detail=f"Unknown entity type: {request.entity_type}")

    # Get the entity
    query = client.table(config["table"]).select("*").eq(
        "id", str(request.entity_id)
    ).eq("project_id", str(project_id))

    # Business drivers need extra filter on driver_type
    extra_filter = config.get("extra_filter")
    if extra_filter:
        query = query.eq(extra_filter[0], extra_filter[1])

    entity_result = query.single().execute()

    if not entity_result.data:
        raise HTTPException(status_code=404, detail=f"{request.entity_type} not found")

    entity = entity_result.data
    entity_name = entity.get(config["name_field"], "Unknown")
    entity_desc = entity.get(config["desc_field"], "")

    # Update the entity's confirmation_status to needs_client
    client.table(config["table"]).update({
        "confirmation_status": "needs_client",
    }).eq("id", str(request.entity_id)).execute()

    # Check if already in pending queue
    existing = client.table("pending_items").select("id").eq(
        "project_id", str(project_id)
    ).eq("entity_id", str(request.entity_id)).eq("status", "pending").execute()

    if existing.data:
        # Already in queue, just return success
        return {
            "success": True,
            "message": f"{entity_name} already in pending queue",
            "pending_item_id": existing.data[0]["id"],
        }

    # Add to pending items queue
    pending_item = {
        "project_id": str(project_id),
        "item_type": request.entity_type,
        "source": "needs_review",
        "entity_id": str(request.entity_id),
        "title": entity_name,
        "description": entity_desc[:200] if entity_desc else None,
        "why_needed": request.reason or f"Marked for client review",
        "priority": "medium",
        "added_by": str(auth.user_id) if auth.user_id else "consultant",
        "status": "pending",
    }

    result = client.table("pending_items").insert(pending_item).execute()

    return {
        "success": True,
        "message": f"{entity_name} marked for client review",
        "pending_item_id": result.data[0]["id"] if result.data else None,
    }


class QuestionAnswerRequest(BaseModel):
    """Request to answer a package question."""
    answer_text: str = Field(..., description="The client's answer")
    confidence: Optional[str] = Field(None, description="How confident the client is")


class ActionItemResponseRequest(BaseModel):
    """Request to respond to an action item."""
    notes: Optional[str] = Field(None, description="Notes about the response")
    file_ids: Optional[list[str]] = Field(None, description="Uploaded file IDs")


@router.get("/portal/projects/{project_id}/active-package")
async def get_active_portal_package(
    project_id: UUID,
    auth: AuthContext = Depends(require_consultant),  # TODO: Change to require_project_access for client auth
):
    """
    Get the active (sent) package for a project.

    This is the main endpoint for clients to see their questions.
    """
    client = get_client()

    # Get the most recent sent package (status can be sent, partial_response, or complete)
    package_result = client.table("client_packages").select("*").eq(
        "project_id", str(project_id)
    ).in_("status", ["sent", "partial_response", "complete"]).order(
        "sent_at", desc=True
    ).limit(1).execute()

    if not package_result.data:
        return {"package": None, "message": "No active package for this project"}

    package = package_result.data[0]
    package_id = package["id"]

    # Get questions (answers stored directly on question)
    questions = client.table("package_questions").select("*").eq(
        "package_id", package_id
    ).order("sequence_order").execute()

    # Get action items with uploaded files
    action_items = client.table("package_action_items").select("*").eq(
        "package_id", package_id
    ).order("sequence_order").execute()

    # Get uploaded files for action items
    files = client.table("package_uploaded_files").select("*").eq(
        "package_id", package_id
    ).execute()

    # Group files by action item
    files_by_item = {}
    for f in files.data:
        item_id = f.get("action_item_id")
        if item_id:
            if item_id not in files_by_item:
                files_by_item[item_id] = []
            files_by_item[item_id].append(f)

    # Attach files to action items
    for item in action_items.data:
        item["uploaded_files"] = files_by_item.get(item["id"], [])

    # Get asset suggestions
    assets = client.table("package_asset_suggestions").select("*").eq(
        "package_id", package_id
    ).execute()

    # Calculate response progress
    total_questions = len(questions.data)
    answered_questions = sum(1 for q in questions.data if q.get("answer_text"))

    total_items = len(action_items.data)
    completed_items = sum(1 for item in action_items.data if item.get("status") == "complete")

    package["questions"] = questions.data
    package["action_items"] = action_items.data
    package["suggested_assets"] = assets.data
    package["progress"] = {
        "questions_total": total_questions,
        "questions_answered": answered_questions,
        "items_total": total_items,
        "items_completed": completed_items,
        "overall_percent": int(
            ((answered_questions + completed_items) / max(total_questions + total_items, 1)) * 100
        ),
    }

    return {"package": package}


@router.post("/portal/questions/{question_id}/answer")
async def answer_portal_question(
    question_id: UUID,
    request: QuestionAnswerRequest,
    auth: AuthContext = Depends(require_consultant),  # TODO: Change to require_project_access
):
    """Submit an answer to a package question."""
    client = get_client()

    # Verify question exists and get package info
    question = client.table("package_questions").select(
        "*, client_packages(id, project_id, status)"
    ).eq("id", str(question_id)).single().execute()

    if not question.data:
        raise HTTPException(status_code=404, detail="Question not found")

    package_status = question.data["client_packages"]["status"]
    if package_status not in ("sent", "partial_response"):
        raise HTTPException(status_code=400, detail="Package is not accepting responses")

    # Get user name for display
    user_result = client.table("users").select("first_name, last_name").eq(
        "id", str(auth.user_id)
    ).single().execute()
    user_name = None
    if user_result.data:
        first = user_result.data.get("first_name", "")
        last = user_result.data.get("last_name", "")
        user_name = f"{first} {last}".strip() or None

    # Update the question directly with the answer
    result = client.table("package_questions").update({
        "answer_text": request.answer_text,
        "answered_by": str(auth.user_id),
        "answered_by_name": user_name,
        "answered_at": datetime.utcnow().isoformat(),
    }).eq("id", str(question_id)).execute()

    # The trigger will automatically update package status/counts

    return {"success": True, "question": result.data[0] if result.data else None}


@router.post("/portal/action-items/{item_id}/respond")
async def respond_to_action_item(
    item_id: UUID,
    request: ActionItemResponseRequest,
    auth: AuthContext = Depends(require_consultant),  # TODO: Change to require_project_access
):
    """Respond to an action item (notes or file upload tracking)."""
    client = get_client()

    # Verify action item exists
    item = client.table("package_action_items").select(
        "*, client_packages(project_id, status)"
    ).eq("id", str(item_id)).single().execute()

    if not item.data:
        raise HTTPException(status_code=404, detail="Action item not found")

    if item.data["client_packages"]["status"] not in ("sent", "responses_received"):
        raise HTTPException(status_code=400, detail="Package is not accepting responses")

    # Update item with notes
    if request.notes:
        client.table("package_action_items").update({
            "response_notes": request.notes,
            "responded_at": datetime.utcnow().isoformat(),
            "responded_by": str(auth.user_id),
        }).eq("id", str(item_id)).execute()

    # Link uploaded files if provided
    if request.file_ids:
        for file_id in request.file_ids:
            client.table("package_uploaded_files").update({
                "action_item_id": str(item_id),
            }).eq("id", file_id).execute()

    # Update package status
    package_id = item.data["package_id"]
    client.table("client_packages").update({
        "status": "responses_received",
    }).eq("id", package_id).eq("status", "sent").execute()

    return {"success": True}


@router.post("/portal/packages/{package_id}/upload")
async def upload_package_file(
    package_id: UUID,
    action_item_id: Optional[UUID] = None,
    file_name: str = "",
    file_path: str = "",
    file_size: int = 0,
    file_type: str = "",
    auth: AuthContext = Depends(require_consultant),  # TODO: Change to require_project_access
):
    """
    Record a file upload for a package.

    Note: Actual file storage handled separately via Supabase Storage.
    This endpoint records the metadata.
    """
    client = get_client()

    # Verify package exists and accepts uploads
    package = client.table("client_packages").select("status").eq(
        "id", str(package_id)
    ).single().execute()

    if not package.data:
        raise HTTPException(status_code=404, detail="Package not found")

    if package.data["status"] not in ("sent", "responses_received"):
        raise HTTPException(status_code=400, detail="Package is not accepting uploads")

    # Create file record
    file_record = {
        "package_id": str(package_id),
        "action_item_id": str(action_item_id) if action_item_id else None,
        "file_name": file_name,
        "file_path": file_path,
        "file_size": file_size,
        "file_type": file_type,
        "uploaded_by": str(auth.user_id),
    }

    result = client.table("package_uploaded_files").insert(file_record).execute()

    # Update package status
    client.table("client_packages").update({
        "status": "responses_received",
    }).eq("id", str(package_id)).eq("status", "sent").execute()

    return {"success": True, "file": result.data[0] if result.data else None}
