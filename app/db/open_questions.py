"""Database access layer for project open questions."""

import logging
from datetime import datetime, timezone
from uuid import UUID

from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)


def list_open_questions(
    project_id: UUID,
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """List open questions for a project with optional filters."""
    client = get_supabase()
    query = (
        client.table("project_open_questions")
        .select("*")
        .eq("project_id", str(project_id))
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
    )

    if status:
        query = query.eq("status", status)
    if priority:
        query = query.eq("priority", priority)
    if category:
        query = query.eq("category", category)

    result = query.execute()
    return result.data or []


def get_open_question(question_id: UUID) -> dict | None:
    """Get a single open question by ID."""
    client = get_supabase()
    result = (
        client.table("project_open_questions")
        .select("*")
        .eq("id", str(question_id))
        .maybe_single()
        .execute()
    )
    return result.data


def create_open_question(
    project_id: UUID,
    question: str,
    why_it_matters: str | None = None,
    context: str | None = None,
    priority: str = "medium",
    category: str = "general",
    source_type: str = "manual",
    source_id: UUID | None = None,
    source_signal_id: UUID | None = None,
    target_entity_type: str | None = None,
    target_entity_id: UUID | None = None,
    suggested_owner: str | None = None,
) -> dict:
    """Create a new open question."""
    client = get_supabase()
    data = {
        "project_id": str(project_id),
        "question": question,
        "why_it_matters": why_it_matters,
        "context": context,
        "priority": priority,
        "category": category,
        "source_type": source_type,
        "source_id": str(source_id) if source_id else None,
        "source_signal_id": str(source_signal_id) if source_signal_id else None,
        "target_entity_type": target_entity_type,
        "target_entity_id": str(target_entity_id) if target_entity_id else None,
        "suggested_owner": suggested_owner,
    }
    # Remove None values to let DB defaults work
    data = {k: v for k, v in data.items() if v is not None}

    result = client.table("project_open_questions").insert(data).execute()
    return result.data[0] if result.data else {}


def update_open_question(question_id: UUID, updates: dict) -> dict:
    """Update an open question's fields."""
    client = get_supabase()
    # Only allow safe fields
    allowed = {"question", "why_it_matters", "context", "priority", "category",
               "target_entity_type", "target_entity_id", "suggested_owner"}
    safe_updates = {k: v for k, v in updates.items() if k in allowed}

    if not safe_updates:
        return get_open_question(question_id) or {}

    result = (
        client.table("project_open_questions")
        .update(safe_updates)
        .eq("id", str(question_id))
        .execute()
    )
    return result.data[0] if result.data else {}


def answer_question(
    question_id: UUID,
    answer: str,
    answered_by: str = "consultant",
) -> dict:
    """Mark a question as answered."""
    client = get_supabase()
    result = (
        client.table("project_open_questions")
        .update({
            "status": "answered",
            "answer": answer,
            "answered_by": answered_by,
            "answered_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", str(question_id))
        .execute()
    )
    return result.data[0] if result.data else {}


def dismiss_question(question_id: UUID, reason: str | None = None) -> dict:
    """Dismiss an open question."""
    client = get_supabase()
    update = {"status": "dismissed"}
    if reason:
        update["answer"] = f"Dismissed: {reason}"
    result = (
        client.table("project_open_questions")
        .update(update)
        .eq("id", str(question_id))
        .execute()
    )
    return result.data[0] if result.data else {}


def convert_question(
    question_id: UUID,
    converted_to_type: str,
    converted_to_id: UUID,
) -> dict:
    """Convert a question to an entity (feature, decision, constraint, etc.)."""
    client = get_supabase()
    result = (
        client.table("project_open_questions")
        .update({
            "status": "converted",
            "converted_to_type": converted_to_type,
            "converted_to_id": str(converted_to_id),
        })
        .eq("id", str(question_id))
        .execute()
    )
    return result.data[0] if result.data else {}


def get_question_counts(project_id: UUID) -> dict:
    """Get question status counts for a project."""
    client = get_supabase()
    result = (
        client.table("project_open_questions")
        .select("status, priority")
        .eq("project_id", str(project_id))
        .execute()
    )
    rows = result.data or []

    counts = {
        "total": len(rows),
        "open": 0,
        "answered": 0,
        "dismissed": 0,
        "converted": 0,
        "critical_open": 0,
        "high_open": 0,
    }
    for r in rows:
        status = r.get("status", "open")
        counts[status] = counts.get(status, 0) + 1
        if status == "open" and r.get("priority") == "critical":
            counts["critical_open"] += 1
        if status == "open" and r.get("priority") == "high":
            counts["high_open"] += 1

    return counts


def backfill_from_extracted_facts(project_id: UUID) -> int:
    """One-time backfill: extract open questions from extracted_facts JSONB.

    Returns count of questions created.
    """
    client = get_supabase()
    created = 0

    # Get all extracted facts for this project
    result = (
        client.table("extracted_facts")
        .select("id, signal_id, facts")
        .eq("project_id", str(project_id))
        .execute()
    )

    for row in (result.data or []):
        facts_data = row.get("facts") or {}
        if isinstance(facts_data, str):
            import json
            try:
                facts_data = json.loads(facts_data)
            except Exception:
                continue

        questions = facts_data.get("open_questions", [])
        for q in questions:
            if not q.get("question"):
                continue

            # Check for duplicate
            existing = (
                client.table("project_open_questions")
                .select("id")
                .eq("project_id", str(project_id))
                .eq("question", q["question"])
                .maybe_single()
                .execute()
            )
            if existing.data:
                continue

            create_open_question(
                project_id=project_id,
                question=q["question"],
                why_it_matters=q.get("why_it_matters"),
                suggested_owner=q.get("suggested_owner"),
                source_type="fact_extraction",
                source_id=UUID(row["id"]),
                source_signal_id=UUID(row["signal_id"]) if row.get("signal_id") else None,
            )
            created += 1

    logger.info(f"Backfilled {created} open questions for project {project_id}")
    return created
