"""Database operations for Discovery Prep bundles."""

import json
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from dateutil import parser as dateutil_parser

from app.core.logging import get_logger
from app.core.schemas_discovery_prep import (
    DiscoveryPrepBundle,
    DiscoveryPrepBundleCreate,
    DocRecommendation,
    PrepQuestion,
    PrepStatus,
)
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse datetime string handling various ISO formats including timezone-aware strings."""
    if not value:
        return None
    try:
        return dateutil_parser.isoparse(value)
    except (ValueError, TypeError):
        return None


async def get_bundle(project_id: UUID) -> Optional[DiscoveryPrepBundle]:
    """Get the discovery prep bundle for a project."""
    supabase = get_supabase()

    result = (
        supabase.table("discovery_prep_bundles")
        .select("*")
        .eq("project_id", str(project_id))
        .limit(1)
        .execute()
    )

    if not result.data or len(result.data) == 0:
        return None

    return _parse_bundle(result.data[0])


async def create_or_update_bundle(
    project_id: UUID,
    agenda_summary: str,
    agenda_bullets: list[str],
    questions: list[PrepQuestion],
    documents: list[DocRecommendation],
) -> DiscoveryPrepBundle:
    """Create or update a discovery prep bundle."""
    supabase = get_supabase()

    # Serialize questions and documents to JSON
    questions_json = [
        {
            "id": str(q.id),
            "question": q.question,
            "best_answered_by": q.best_answered_by,
            "why_important": q.why_important,
            "confirmed": q.confirmed,
            "client_answer": q.client_answer,
            "answered_at": q.answered_at.isoformat() if q.answered_at else None,
        }
        for q in questions
    ]

    documents_json = [
        {
            "id": str(d.id),
            "document_name": d.document_name,
            "priority": d.priority.value if hasattr(d.priority, "value") else d.priority,
            "why_important": d.why_important,
            "confirmed": d.confirmed,
            "uploaded_file_id": str(d.uploaded_file_id) if d.uploaded_file_id else None,
            "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
        }
        for d in documents
    ]

    data = {
        "project_id": str(project_id),
        "agenda_summary": agenda_summary,
        "agenda_bullets": agenda_bullets,
        "questions": questions_json,
        "documents": documents_json,
        "status": PrepStatus.DRAFT.value,
        "generated_at": datetime.utcnow().isoformat(),
    }

    result = (
        supabase.table("discovery_prep_bundles")
        .upsert(data, on_conflict="project_id")
        .execute()
    )

    if not result.data:
        raise Exception("Failed to create/update bundle")

    return _parse_bundle(result.data[0])


async def update_question(
    project_id: UUID,
    question_id: UUID,
    confirmed: Optional[bool] = None,
    question: Optional[str] = None,
    best_answered_by: Optional[str] = None,
    why_important: Optional[str] = None,
) -> Optional[DiscoveryPrepBundle]:
    """Update a specific question in the bundle."""
    bundle = await get_bundle(project_id)
    if not bundle:
        return None

    # Find and update the question
    updated = False
    for q in bundle.questions:
        if q.id == question_id:
            if confirmed is not None:
                q.confirmed = confirmed
            if question is not None:
                q.question = question
            if best_answered_by is not None:
                q.best_answered_by = best_answered_by
            if why_important is not None:
                q.why_important = why_important
            updated = True
            break

    if not updated:
        return None

    # Save updated bundle
    return await create_or_update_bundle(
        project_id=project_id,
        agenda_summary=bundle.agenda_summary or "",
        agenda_bullets=bundle.agenda_bullets,
        questions=bundle.questions,
        documents=bundle.documents,
    )


async def update_document(
    project_id: UUID,
    document_id: UUID,
    confirmed: Optional[bool] = None,
    document_name: Optional[str] = None,
    priority: Optional[str] = None,
    why_important: Optional[str] = None,
) -> Optional[DiscoveryPrepBundle]:
    """Update a specific document recommendation in the bundle."""
    bundle = await get_bundle(project_id)
    if not bundle:
        return None

    # Find and update the document
    updated = False
    for d in bundle.documents:
        if d.id == document_id:
            if confirmed is not None:
                d.confirmed = confirmed
            if document_name is not None:
                d.document_name = document_name
            if priority is not None:
                from app.core.schemas_discovery_prep import DocPriority
                d.priority = DocPriority(priority)
            if why_important is not None:
                d.why_important = why_important
            updated = True
            break

    if not updated:
        return None

    # Save updated bundle
    return await create_or_update_bundle(
        project_id=project_id,
        agenda_summary=bundle.agenda_summary or "",
        agenda_bullets=bundle.agenda_bullets,
        questions=bundle.questions,
        documents=bundle.documents,
    )


async def update_bundle_status(
    project_id: UUID,
    status: PrepStatus,
    sent_at: Optional[datetime] = None,
) -> Optional[DiscoveryPrepBundle]:
    """Update the bundle status."""
    supabase = get_supabase()

    update_data = {"status": status.value}
    if sent_at:
        update_data["sent_to_portal_at"] = sent_at.isoformat()

    result = (
        supabase.table("discovery_prep_bundles")
        .update(update_data)
        .eq("project_id", str(project_id))
        .execute()
    )

    if not result.data:
        return None

    return _parse_bundle(result.data[0])


async def delete_bundle(project_id: UUID) -> bool:
    """Delete a discovery prep bundle."""
    supabase = get_supabase()

    result = (
        supabase.table("discovery_prep_bundles")
        .delete()
        .eq("project_id", str(project_id))
        .execute()
    )

    return len(result.data) > 0 if result.data else False


def _parse_bundle(data: dict) -> DiscoveryPrepBundle:
    """Parse database row into DiscoveryPrepBundle."""
    from app.core.schemas_discovery_prep import DocPriority

    # Parse questions
    questions_data = data.get("questions") or []
    questions = []
    for q in questions_data:
        questions.append(
            PrepQuestion(
                id=UUID(q["id"]) if q.get("id") else uuid4(),
                question=q["question"],
                best_answered_by=q.get("best_answered_by", "You"),
                why_important=q.get("why_important", ""),
                confirmed=q.get("confirmed", False),
                client_answer=q.get("client_answer"),
                answered_at=_parse_datetime(q.get("answered_at")),
            )
        )

    # Parse documents
    documents_data = data.get("documents") or []
    documents = []
    for d in documents_data:
        documents.append(
            DocRecommendation(
                id=UUID(d["id"]) if d.get("id") else uuid4(),
                document_name=d["document_name"],
                priority=DocPriority(d.get("priority", "medium")),
                why_important=d.get("why_important", ""),
                confirmed=d.get("confirmed", False),
                uploaded_file_id=UUID(d["uploaded_file_id"]) if d.get("uploaded_file_id") else None,
                uploaded_at=_parse_datetime(d.get("uploaded_at")),
            )
        )

    return DiscoveryPrepBundle(
        id=UUID(data["id"]),
        project_id=UUID(data["project_id"]),
        agenda_summary=data.get("agenda_summary"),
        agenda_bullets=data.get("agenda_bullets") or [],
        questions=questions,
        documents=documents,
        status=PrepStatus(data.get("status", "draft")),
        sent_to_portal_at=_parse_datetime(data.get("sent_to_portal_at")),
        generated_at=_parse_datetime(data.get("generated_at")) or datetime.utcnow(),
        updated_at=_parse_datetime(data.get("updated_at")) or datetime.utcnow(),
    )
