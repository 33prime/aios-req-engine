"""API endpoints for project open questions lifecycle."""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.core.schemas_open_questions import (
    OpenQuestionAnswer,
    OpenQuestionConvert,
    OpenQuestionCreate,
    OpenQuestionDismiss,
    OpenQuestionResponse,
    OpenQuestionUpdate,
    QuestionCounts,
)
from app.db.open_questions import (
    answer_question as db_answer,
    backfill_from_extracted_facts,
    convert_question as db_convert,
    create_open_question,
    dismiss_question as db_dismiss,
    get_open_question,
    get_question_counts,
    list_open_questions,
    update_open_question,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/projects/{project_id}/questions",
    tags=["open_questions"],
)


@router.get("/", response_model=list[OpenQuestionResponse])
async def list_questions(
    project_id: UUID,
    status: str | None = Query(None, description="Filter by status: open, answered, dismissed, converted"),
    priority: str | None = Query(None, description="Filter by priority: critical, high, medium, low"),
    category: str | None = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    """List open questions for a project with optional filters."""
    try:
        return list_open_questions(
            project_id, status=status, priority=priority,
            category=category, limit=limit, offset=offset,
        )
    except Exception as e:
        logger.exception(f"Failed to list questions for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=OpenQuestionResponse, status_code=201)
async def create_question(project_id: UUID, data: OpenQuestionCreate) -> dict:
    """Create a new open question."""
    try:
        return create_open_question(
            project_id=project_id,
            question=data.question,
            why_it_matters=data.why_it_matters,
            context=data.context,
            priority=data.priority.value,
            category=data.category.value,
            source_type=data.source_type.value,
            source_id=UUID(data.source_id) if data.source_id else None,
            source_signal_id=UUID(data.source_signal_id) if data.source_signal_id else None,
            target_entity_type=data.target_entity_type,
            target_entity_id=UUID(data.target_entity_id) if data.target_entity_id else None,
            suggested_owner=data.suggested_owner,
        )
    except Exception as e:
        logger.exception(f"Failed to create question for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{question_id}", response_model=OpenQuestionResponse)
async def update_question(project_id: UUID, question_id: UUID, data: OpenQuestionUpdate) -> dict:
    """Update an open question."""
    try:
        existing = get_open_question(question_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Question not found")
        if existing["project_id"] != str(project_id):
            raise HTTPException(status_code=404, detail="Question not found in this project")

        updates = data.model_dump(exclude_none=True)
        # Convert enums to values
        for k, v in updates.items():
            if hasattr(v, "value"):
                updates[k] = v.value

        return update_open_question(question_id, updates)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update question {question_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{question_id}/answer", response_model=OpenQuestionResponse)
async def answer_question(project_id: UUID, question_id: UUID, data: OpenQuestionAnswer) -> dict:
    """Answer an open question."""
    try:
        existing = get_open_question(question_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Question not found")
        if existing["project_id"] != str(project_id):
            raise HTTPException(status_code=404, detail="Question not found in this project")

        return db_answer(question_id, data.answer, data.answered_by)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to answer question {question_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{question_id}/dismiss", response_model=OpenQuestionResponse)
async def dismiss_question(project_id: UUID, question_id: UUID, data: OpenQuestionDismiss) -> dict:
    """Dismiss an open question."""
    try:
        existing = get_open_question(question_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Question not found")
        if existing["project_id"] != str(project_id):
            raise HTTPException(status_code=404, detail="Question not found in this project")

        return db_dismiss(question_id, data.reason)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to dismiss question {question_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{question_id}/convert", response_model=OpenQuestionResponse)
async def convert_question(project_id: UUID, question_id: UUID, data: OpenQuestionConvert) -> dict:
    """Convert an open question to an entity (feature, decision, constraint)."""
    try:
        existing = get_open_question(question_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Question not found")
        if existing["project_id"] != str(project_id):
            raise HTTPException(status_code=404, detail="Question not found in this project")

        return db_convert(question_id, data.converted_to_type, UUID(data.converted_to_id))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to convert question {question_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/counts", response_model=QuestionCounts)
async def get_counts(project_id: UUID) -> dict:
    """Get question status counts for a project."""
    try:
        return get_question_counts(project_id)
    except Exception as e:
        logger.exception(f"Failed to get question counts for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backfill")
async def backfill_questions(project_id: UUID) -> dict:
    """One-time backfill of open questions from legacy JSONB sources."""
    try:
        count = backfill_from_extracted_facts(project_id)
        return {"backfilled": count}
    except Exception as e:
        logger.exception(f"Failed to backfill questions for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))
