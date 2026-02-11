"""API endpoints for confirmation items management."""

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query
from openai import OpenAI
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.core.config import get_settings
from app.core.schemas_confirmations import (
    ConfirmationItemOut,
    ConfirmationStatusUpdate,
    ListConfirmationsResponse,
)
from app.db.confirmations import (
    get_confirmation_item,
    list_confirmation_items,
    set_confirmation_status,
)
from app.db import stakeholders as stakeholders_db
from app.core.topic_extraction import extract_topics_from_entity, get_confirmation_gap_topics

logger = get_logger(__name__)

router = APIRouter()


@router.get("/confirmations", response_model=ListConfirmationsResponse)
async def list_confirmations(
    project_id: UUID = Query(..., description="Project UUID"),
    status: str | None = Query(None, description="Optional status filter"),
) -> ListConfirmationsResponse:
    """
    List confirmation items for a project.

    Args:
        project_id: Project UUID
        status: Optional status filter (open, queued, resolved, dismissed)

    Returns:
        ListConfirmationsResponse with confirmation items

    Raises:
        HTTPException 500: If database operation fails
    """
    try:
        logger.info(
            f"Listing confirmations for project {project_id}",
            extra={"project_id": str(project_id), "status": status},
        )

        items = list_confirmation_items(project_id, status=status)

        # Convert to Pydantic models, skipping invalid items
        confirmations = []
        for item in items:
            try:
                confirmations.append(ConfirmationItemOut(**item))
            except Exception as validation_error:
                logger.warning(
                    f"Skipping invalid confirmation {item.get('id')}: {validation_error}",
                    extra={"project_id": str(project_id), "confirmation_id": item.get("id")},
                )
                continue

        return ListConfirmationsResponse(
            confirmations=confirmations,
            total=len(confirmations),
        )

    except Exception as e:
        error_msg = f"Failed to list confirmations: {str(e)}"
        logger.error(error_msg, extra={"project_id": str(project_id)})
        raise HTTPException(status_code=500, detail=error_msg) from e


@router.get("/confirmations/summary")
async def get_confirmations_summary(
    project_id: UUID = Query(..., description="Project UUID"),
) -> dict[str, Any]:
    """
    Get summary of confirmations with AI recommendation for outreach approach.

    Returns counts, groupings, and recommendation for email vs meeting.
    """
    try:
        confirmations = list_confirmation_items(project_id, status="open")

        if not confirmations:
            return {
                "total": 0,
                "by_method": {"email": 0, "meeting": 0},
                "by_priority": {"high": 0, "medium": 0, "low": 0},
                "by_kind": {},
                "recommendation": "No open confirmations",
            }

        # Count by method
        email_count = sum(1 for c in confirmations if c.get("suggested_method") == "email")
        meeting_count = sum(1 for c in confirmations if c.get("suggested_method") == "meeting")

        # Count by priority
        high = sum(1 for c in confirmations if c.get("priority") == "high")
        medium = sum(1 for c in confirmations if c.get("priority") == "medium")
        low = sum(1 for c in confirmations if c.get("priority") == "low")

        # Group by kind
        by_kind: dict[str, list[dict]] = {}
        for c in confirmations:
            kind = c.get("kind", "other")
            if kind not in by_kind:
                by_kind[kind] = []
            by_kind[kind].append({
                "id": c["id"],
                "title": c.get("title"),
                "priority": c.get("priority"),
                "suggested_method": c.get("suggested_method"),
            })

        # Generate recommendation
        if meeting_count >= 3 or high >= 2:
            recommendation = f"Schedule a {meeting_count * 5 + 10}-minute client call to cover {meeting_count} complex items. {email_count} simple items can go via email."
        elif len(confirmations) <= 3 and meeting_count == 0:
            recommendation = f"Send a quick email to resolve {len(confirmations)} simple questions."
        elif meeting_count > 0 and email_count > 0:
            recommendation = f"Split approach: Email for {email_count} simple items, then schedule call for {meeting_count} complex topics."
        else:
            recommendation = f"Review {len(confirmations)} items and decide on email vs meeting approach."

        return {
            "total": len(confirmations),
            "by_method": {"email": email_count, "meeting": meeting_count},
            "by_priority": {"high": high, "medium": medium, "low": low},
            "by_kind": by_kind,
            "recommendation": recommendation,
        }

    except Exception as e:
        logger.error(f"Failed to get confirmations summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/confirmations/{confirmation_id}", response_model=ConfirmationItemOut)
async def get_confirmation(
    confirmation_id: UUID = Path(..., description="Confirmation item UUID"),
) -> ConfirmationItemOut:
    """
    Get a single confirmation item by ID.

    Args:
        confirmation_id: Confirmation item UUID

    Returns:
        ConfirmationItemOut

    Raises:
        HTTPException 404: If confirmation not found
        HTTPException 500: If database operation fails
    """
    try:
        logger.info(
            f"Getting confirmation {confirmation_id}",
            extra={"confirmation_id": str(confirmation_id)},
        )

        item = get_confirmation_item(confirmation_id)

        if not item:
            raise HTTPException(
                status_code=404,
                detail=f"Confirmation item {confirmation_id} not found",
            )

        return ConfirmationItemOut(**item)

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Failed to get confirmation: {str(e)}"
        logger.error(error_msg, extra={"confirmation_id": str(confirmation_id)})
        raise HTTPException(status_code=500, detail=error_msg) from e


@router.patch("/confirmations/{confirmation_id}/status", response_model=ConfirmationItemOut)
async def update_confirmation_status(
    confirmation_id: UUID = Path(..., description="Confirmation item UUID"),
    request: ConfirmationStatusUpdate = ...,
) -> ConfirmationItemOut:
    """
    Update the status of a confirmation item.

    Args:
        confirmation_id: Confirmation item UUID
        request: ConfirmationStatusUpdate with new status and optional resolution evidence

    Returns:
        Updated ConfirmationItemOut

    Raises:
        HTTPException 404: If confirmation not found
        HTTPException 500: If database operation fails
    """
    try:
        logger.info(
            f"Updating confirmation {confirmation_id} to status {request.status}",
            extra={"confirmation_id": str(confirmation_id), "status": request.status},
        )

        # Convert resolution_evidence to dict if present
        resolution_evidence_dict = None
        if request.resolution_evidence:
            resolution_evidence_dict = request.resolution_evidence.model_dump()

        updated_item = set_confirmation_status(
            confirmation_id=confirmation_id,
            status=request.status,
            resolution_evidence=resolution_evidence_dict,
        )

        return ConfirmationItemOut(**updated_item)

    except ValueError as e:
        # Likely means confirmation not found
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        error_msg = f"Failed to update confirmation status: {str(e)}"
        logger.error(error_msg, extra={"confirmation_id": str(confirmation_id)})
        raise HTTPException(status_code=500, detail=error_msg) from e


# ============================================================================
# Batch Confirmation
# ============================================================================


class BatchConfirmRequest(BaseModel):
    """Request to batch-confirm entities."""
    project_id: UUID = Field(..., description="Project UUID")
    entity_type: str = Field(..., description="Entity type: feature, persona, vp_step, business_driver, constraint")
    entity_ids: list[str] = Field(..., description="List of entity IDs to confirm")
    confirmation_status: str = Field(
        default="confirmed_consultant",
        description="Status to set (confirmed_consultant or confirmed_client)",
    )


class BatchConfirmResponse(BaseModel):
    """Response from batch confirmation."""
    updated_count: int
    entity_type: str
    confirmation_status: str


ENTITY_TABLE_MAP = {
    "feature": "features",
    "persona": "personas",
    "vp_step": "vp_steps",
    "business_driver": "business_drivers",
    "constraint": "constraints",
    "stakeholder": "stakeholders",
}


@router.post("/confirmations/batch", response_model=BatchConfirmResponse)
async def batch_confirm_entities(request: BatchConfirmRequest) -> BatchConfirmResponse:
    """
    Batch confirm multiple entities of the same type.

    Updates the confirmation_status of all specified entities.
    Used by the BRD Canvas "Confirm All" action.
    """
    from app.db.supabase_client import get_supabase

    valid_statuses = {"confirmed_consultant", "confirmed_client", "ai_generated", "needs_client"}
    if request.confirmation_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid confirmation_status. Must be one of: {', '.join(sorted(valid_statuses))}",
        )

    table_name = ENTITY_TABLE_MAP.get(request.entity_type)
    if not table_name:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entity_type. Must be one of: {', '.join(sorted(ENTITY_TABLE_MAP.keys()))}",
        )

    if not request.entity_ids:
        return BatchConfirmResponse(
            updated_count=0,
            entity_type=request.entity_type,
            confirmation_status=request.confirmation_status,
        )

    try:
        supabase = get_supabase()
        updated_count = 0

        for entity_id in request.entity_ids:
            try:
                result = supabase.table(table_name).update({
                    "confirmation_status": request.confirmation_status,
                    "updated_at": "now()",
                }).eq("id", entity_id).eq("project_id", str(request.project_id)).execute()

                if result.data:
                    updated_count += 1
            except Exception as e:
                logger.warning(
                    f"Failed to update {request.entity_type} {entity_id}: {e}",
                    extra={"entity_id": entity_id},
                )

        logger.info(
            f"Batch confirmed {updated_count}/{len(request.entity_ids)} {request.entity_type}s",
            extra={
                "project_id": str(request.project_id),
                "entity_type": request.entity_type,
                "count": updated_count,
            },
        )

        return BatchConfirmResponse(
            updated_count=updated_count,
            entity_type=request.entity_type,
            confirmation_status=request.confirmation_status,
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Failed to batch confirm entities: {str(e)}"
        logger.error(error_msg, extra={"project_id": str(request.project_id)})
        raise HTTPException(status_code=500, detail=error_msg) from e


# ============================================================================
# Email and Meeting Agenda Generation
# ============================================================================


class GenerateEmailRequest(BaseModel):
    """Request to generate email draft for confirmations."""

    project_id: UUID = Field(..., description="Project UUID")
    confirmation_ids: list[str] = Field(
        default=[],
        description="Specific confirmation IDs to include (empty = all open email-suitable)",
    )
    client_name: str = Field(default="", description="Client name for greeting")
    project_name: str = Field(default="", description="Project name for context")


class GenerateEmailResponse(BaseModel):
    """Response with generated email draft."""

    subject: str
    body: str
    confirmation_count: int
    confirmations_included: list[str]


class GenerateMeetingAgendaRequest(BaseModel):
    """Request to generate meeting agenda for confirmations."""

    project_id: UUID = Field(..., description="Project UUID")
    confirmation_ids: list[str] = Field(
        default=[],
        description="Specific confirmation IDs to include (empty = all open meeting-suitable)",
    )
    client_name: str = Field(default="", description="Client name for greeting")
    project_name: str = Field(default="", description="Project name for context")
    meeting_duration: int = Field(default=30, description="Meeting duration in minutes")


class GenerateMeetingAgendaResponse(BaseModel):
    """Response with generated meeting agenda."""

    title: str
    duration_estimate: str
    agenda: list[dict[str, Any]]
    pre_read: str
    confirmation_count: int
    confirmations_included: list[str]


EMAIL_GENERATION_PROMPT = """You are drafting a professional email to a client to gather information for their software project.

**Project:** {project_name}
**Client:** {client_name}

**Questions to include:**
{questions_text}

**Instructions:**
- Write a friendly, professional email
- Be concise - busy clients appreciate brevity
- Frame everything as QUESTIONS to the client, not requests to "review" anything
- The client will NOT see any platform or system - they only receive this email
- Group related questions together
- Number the questions for easy reference
- Make questions clear and answerable via email reply
- Make it easy to respond (e.g., "You can reply inline or schedule a quick call")
- End with a clear call to action

Return JSON with:
- "subject": Email subject line
- "body": Full email body (use \\n for newlines)
"""


MEETING_AGENDA_PROMPT = """You are creating a meeting agenda to discuss open questions with a client about their software project.

**Project:** {project_name}
**Client:** {client_name}
**Target Duration:** {duration} minutes

**Topics to cover:**
{questions_text}

**Instructions:**
- Create a structured agenda with time allocations
- Frame topics as QUESTIONS or DISCUSSIONS, not requests to "review" anything
- The client will NOT see any platform or system - this is a verbal discussion
- Group related topics together
- Start with quick wins, end with complex discussions
- Include a brief pre-read summary for the client (context only, no platform references)
- Be realistic about time - complex topics need more time

Return JSON with:
- "title": Meeting title
- "duration_estimate": Realistic duration estimate (e.g., "25-30 minutes")
- "agenda": Array of agenda items, each with:
  - "topic": Topic title (phrase as a question or discussion point)
  - "description": Brief description of what to discuss
  - "time_minutes": Allocated minutes
  - "confirmation_ids": Array of confirmation IDs covered
- "pre_read": Brief summary client should read before meeting (2-3 sentences, no platform references)
"""


@router.post("/confirmations/generate-email", response_model=GenerateEmailResponse)
async def generate_email_draft(request: GenerateEmailRequest) -> GenerateEmailResponse:
    """
    Generate an optimized email draft to gather client confirmations.

    Groups related questions and optimizes for clarity and response rate.

    Args:
        request: GenerateEmailRequest with project_id and optional confirmation_ids

    Returns:
        GenerateEmailResponse with subject and body
    """
    settings = get_settings()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    try:
        # Get confirmations to include
        if request.confirmation_ids:
            # Get specific confirmations
            confirmations = []
            for cid in request.confirmation_ids:
                item = get_confirmation_item(UUID(cid))
                if item:
                    confirmations.append(item)
        else:
            # Get all open confirmations suitable for email
            all_confirmations = list_confirmation_items(request.project_id, status="open")
            confirmations = [
                c for c in all_confirmations
                if c.get("suggested_method") == "email"
            ]

        if not confirmations:
            raise HTTPException(
                status_code=400,
                detail="No confirmations found suitable for email",
            )

        # Build questions text
        questions_text = "\n".join([
            f"{i+1}. **{c.get('title', 'Question')}**\n   - Why: {c.get('why', 'N/A')}\n   - Ask: {c.get('ask', 'N/A')}\n   - Priority: {c.get('priority', 'medium')}"
            for i, c in enumerate(confirmations)
        ])

        prompt = EMAIL_GENERATION_PROMPT.format(
            project_name=request.project_name or "your project",
            client_name=request.client_name or "there",
            questions_text=questions_text,
        )

        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL_MINI,
            temperature=0.7,
            max_tokens=1500,
            messages=[
                {"role": "system", "content": "You are a professional consultant drafting client communications. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
        )

        raw = response.choices[0].message.content.strip()

        # Strip markdown if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()

        result = json.loads(raw)

        return GenerateEmailResponse(
            subject=result.get("subject", "Questions for your project"),
            body=result.get("body", "").replace("\\n", "\n"),
            confirmation_count=len(confirmations),
            confirmations_included=[c["id"] for c in confirmations],
        )

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse email generation JSON: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate email") from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Email generation failed: {str(e)}") from e


@router.post("/confirmations/generate-meeting-agenda", response_model=GenerateMeetingAgendaResponse)
async def generate_meeting_agenda(request: GenerateMeetingAgendaRequest) -> GenerateMeetingAgendaResponse:
    """
    Generate a structured meeting agenda for client confirmations.

    Groups topics by theme and allocates time based on complexity.

    Args:
        request: GenerateMeetingAgendaRequest with project_id and optional confirmation_ids

    Returns:
        GenerateMeetingAgendaResponse with structured agenda
    """
    settings = get_settings()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    try:
        # Get confirmations to include
        if request.confirmation_ids:
            # Get specific confirmations
            confirmations = []
            for cid in request.confirmation_ids:
                item = get_confirmation_item(UUID(cid))
                if item:
                    confirmations.append(item)
        else:
            # Get all open confirmations suitable for meeting
            all_confirmations = list_confirmation_items(request.project_id, status="open")
            confirmations = [
                c for c in all_confirmations
                if c.get("suggested_method") == "meeting"
            ]

        if not confirmations:
            raise HTTPException(
                status_code=400,
                detail="No confirmations found suitable for meeting",
            )

        # Build questions text with IDs for reference
        questions_text = "\n".join([
            f"- **{c.get('title', 'Topic')}** (ID: {c['id']})\n  Why: {c.get('why', 'N/A')}\n  Ask: {c.get('ask', 'N/A')}\n  Priority: {c.get('priority', 'medium')}\n  Complexity: {c.get('created_from', {}).get('confidence', 'unknown')}"
            for c in confirmations
        ])

        prompt = MEETING_AGENDA_PROMPT.format(
            project_name=request.project_name or "the project",
            client_name=request.client_name or "the client",
            duration=request.meeting_duration,
            questions_text=questions_text,
        )

        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL_MINI,
            temperature=0.7,
            max_tokens=2000,
            messages=[
                {"role": "system", "content": "You are a professional consultant creating meeting agendas. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
        )

        raw = response.choices[0].message.content.strip()

        # Strip markdown if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()

        result = json.loads(raw)

        return GenerateMeetingAgendaResponse(
            title=result.get("title", f"Project Discussion: {request.project_name}"),
            duration_estimate=result.get("duration_estimate", f"{request.meeting_duration} minutes"),
            agenda=result.get("agenda", []),
            pre_read=result.get("pre_read", ""),
            confirmation_count=len(confirmations),
            confirmations_included=[c["id"] for c in confirmations],
        )

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse meeting agenda JSON: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate meeting agenda") from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Meeting agenda generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Meeting agenda generation failed: {str(e)}") from e


# ============================================================================
# Who Would Know - Entity-Specific Stakeholder Suggestions
# ============================================================================


class EntityWhoWouldKnowRequest(BaseModel):
    """Request for entity-specific stakeholder suggestions."""

    project_id: UUID = Field(..., description="Project UUID")
    entity_type: str = Field(..., description="Entity type: feature, persona, vp_step")
    entity_id: UUID = Field(..., description="Entity UUID")
    gap_description: str | None = Field(None, description="Optional specific gap description")


class StakeholderSuggestionOut(BaseModel):
    """A suggested stakeholder who might know about the entity."""

    stakeholder_id: UUID
    stakeholder_name: str
    role: str | None
    match_score: int
    reasons: list[str]
    is_primary_contact: bool
    suggestion_text: str | None
    topic_matches: list[str] = Field(default_factory=list, description="Topics that matched")


class EntityWhoWouldKnowResponse(BaseModel):
    """Response for entity-specific stakeholder suggestions."""

    entity_id: UUID
    entity_type: str
    entity_name: str | None
    topics_extracted: list[str]
    suggestions: list[StakeholderSuggestionOut]
    total_suggestions: int


@router.post("/confirmations/who-would-know", response_model=EntityWhoWouldKnowResponse)
async def entity_who_would_know(
    request: EntityWhoWouldKnowRequest,
) -> EntityWhoWouldKnowResponse:
    """
    Find stakeholders who might know about a specific entity needing confirmation.

    This is the "Who Would Know" feature. Given an entity (feature, persona, or VP step),
    it extracts topics from the entity and matches them against stakeholder expertise
    and topic mentions.

    Args:
        request: EntityWhoWouldKnowRequest with entity details

    Returns:
        EntityWhoWouldKnowResponse with suggested stakeholders and reasoning
    """
    from app.db.supabase_client import get_supabase

    try:
        supabase = get_supabase()

        # Fetch the entity based on type
        entity_name = None
        if request.entity_type == "feature":
            entity_result = (
                supabase.table("features")
                .select("*")
                .eq("id", str(request.entity_id))
                .eq("project_id", str(request.project_id))
                .maybe_single()
                .execute()
            )
            entity = entity_result.data
            entity_name = entity.get("name") if entity else None

        elif request.entity_type == "persona":
            entity_result = (
                supabase.table("personas")
                .select("*")
                .eq("id", str(request.entity_id))
                .eq("project_id", str(request.project_id))
                .maybe_single()
                .execute()
            )
            entity = entity_result.data
            entity_name = entity.get("name") if entity else None

        elif request.entity_type == "vp_step":
            entity_result = (
                supabase.table("vp_steps")
                .select("*")
                .eq("id", str(request.entity_id))
                .eq("project_id", str(request.project_id))
                .maybe_single()
                .execute()
            )
            entity = entity_result.data
            entity_name = entity.get("action") if entity else None

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported entity type: {request.entity_type}",
            )

        if not entity:
            raise HTTPException(
                status_code=404,
                detail=f"{request.entity_type} not found: {request.entity_id}",
            )

        # Extract topics from the entity
        topics = get_confirmation_gap_topics(
            entity=entity,
            entity_type=request.entity_type,
            gap_description=request.gap_description,
        )

        logger.info(
            f"Extracted {len(topics)} topics from {request.entity_type} {request.entity_id}",
            extra={
                "project_id": str(request.project_id),
                "entity_type": request.entity_type,
                "entity_id": str(request.entity_id),
                "topics": topics[:5],
            },
        )

        # Find matching stakeholders
        suggestions = stakeholders_db.suggest_stakeholders_for_confirmation(
            project_id=request.project_id,
            entity_type=request.entity_type,
            entity_topics=topics,
            gap_description=request.gap_description,
        )

        # Build response
        suggestion_outs = []
        for s in suggestions:
            suggestion_outs.append(StakeholderSuggestionOut(
                stakeholder_id=UUID(s["stakeholder_id"]),
                stakeholder_name=s["stakeholder_name"],
                role=s.get("role"),
                match_score=s.get("match_score", 0),
                reasons=s.get("reasons", []),
                is_primary_contact=s.get("is_primary_contact", False),
                suggestion_text=s.get("suggestion_text"),
                topic_matches=[
                    r.split(":")[1] if ":" in r else r
                    for r in s.get("reasons", [])
                    if "mentioned" in r or "expertise" in r
                ],
            ))

        return EntityWhoWouldKnowResponse(
            entity_id=request.entity_id,
            entity_type=request.entity_type,
            entity_name=entity_name,
            topics_extracted=topics,
            suggestions=suggestion_outs,
            total_suggestions=len(suggestion_outs),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Who would know failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e

