"""Solution flow tool implementations."""

from typing import Any, Dict
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def _match_question(questions: list, params: Dict[str, Any]) -> tuple[int | None, dict | None]:
    """Match a question by index (preferred), exact text, or fuzzy text.

    Returns (index, question_dict) or (None, None) if not found.
    """
    question_index = params.get("question_index")
    question_text = params.get("question_text", "")

    # Primary: match by index
    if question_index is not None:
        if 0 <= question_index < len(questions):
            q = questions[question_index]
            if isinstance(q, dict):
                return question_index, q
        return None, None

    # Fallback: exact text match
    if question_text:
        for i, q in enumerate(questions):
            if isinstance(q, dict) and q.get("question") == question_text:
                return i, q

        # Fuzzy fallback: case-insensitive, whitespace-normalized
        normalized_target = " ".join(question_text.lower().split())
        for i, q in enumerate(questions):
            if isinstance(q, dict):
                normalized_q = " ".join((q.get("question") or "").lower().split())
                if normalized_q == normalized_target:
                    return i, q

    return None, None


async def _update_solution_flow_step(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Update fields on a solution flow step."""
    from app.db.solution_flow import get_flow_step, update_flow_step

    step_id = params.pop("step_id", None)
    if not step_id:
        return {"error": "step_id is required"}
    try:
        # Capture before-state for diff
        before = get_flow_step(UUID(step_id))
        result = update_flow_step(UUID(step_id), params)

        # Build field-level diff
        changes = {}
        if before:
            for field in params:
                old_val = before.get(field)
                new_val = result.get(field)
                if old_val != new_val:
                    changes[field] = {"old": old_val, "new": new_val}

        # Record revision
        try:
            from app.db.revisions_enrichment import insert_enrichment_revision
            insert_enrichment_revision(
                project_id=project_id,
                entity_type="solution_flow_step",
                entity_id=UUID(step_id),
                entity_label=result.get("title", ""),
                revision_type="updated",
                trigger_event="chat_tool",
                changes=changes,
                diff_summary=f"Updated {', '.join(params.keys())}",
                created_by="chat_assistant",
            )
        except Exception:
            pass  # Don't fail the update if revision recording fails

        # Cross-step cascade: if substantial fields changed, flag other steps
        substantial_fields = {"goal", "information_fields", "actors"}
        if substantial_fields & set(params.keys()):
            try:
                linked_ids = []
                for key in ("linked_feature_ids", "linked_workflow_ids", "linked_data_entity_ids"):
                    linked_ids.extend(result.get(key) or [])
                if linked_ids:
                    from app.db.solution_flow import flag_steps_with_updates
                    flag_steps_with_updates(project_id, linked_ids)
            except Exception:
                pass  # Don't fail the update

        # Re-fetch full step data for optimistic update
        step_data = get_flow_step(UUID(step_id))
        return {
            "success": True,
            "step_id": step_id,
            "updated_fields": list(params.keys()),
            "step_data": step_data,
        }
    except Exception as e:
        return {"error": str(e)}


async def _add_solution_flow_step(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Add a new step to the solution flow."""
    from app.db.solution_flow import create_flow_step, get_or_create_flow

    try:
        flow = get_or_create_flow(project_id)
        result = create_flow_step(UUID(flow["id"]), project_id, params)
        return {
            "success": True,
            "step_id": result["id"],
            "title": result.get("title"),
            "step_index": result.get("step_index"),
        }
    except Exception as e:
        return {"error": str(e)}


async def _remove_solution_flow_step(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Remove a step from the solution flow."""
    from app.db.solution_flow import delete_flow_step, get_flow_step

    step_id = params.get("step_id")
    if not step_id:
        return {"error": "step_id is required"}
    try:
        step = get_flow_step(UUID(step_id))
        title = step.get("title", "") if step else ""
        delete_flow_step(UUID(step_id))
        return {
            "success": True,
            "removed_title": title,
        }
    except Exception as e:
        return {"error": str(e)}


async def _reorder_solution_flow_steps(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Reorder steps in the solution flow."""
    from app.db.solution_flow import get_or_create_flow, reorder_flow_steps

    step_ids = params.get("step_ids", [])
    if not step_ids:
        return {"error": "step_ids is required"}
    try:
        flow = get_or_create_flow(project_id)
        result = reorder_flow_steps(UUID(flow["id"]), step_ids)
        return {
            "success": True,
            "step_count": len(result),
        }
    except Exception as e:
        return {"error": str(e)}


async def _resolve_solution_flow_question(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve an open question on a solution flow step."""
    from app.db.solution_flow import get_flow_step, update_flow_step

    step_id = params.get("step_id")
    answer = params.get("answer", "")

    if not step_id or not answer:
        return {"error": "step_id and answer are required"}

    try:
        step = get_flow_step(UUID(step_id))
        if not step:
            return {"error": "Step not found"}

        questions = step.get("open_questions") or []
        idx, matched_q = _match_question(questions, params)

        if idx is None or matched_q is None:
            return {"error": "Question not found — check question_index or question_text"}

        matched_q["status"] = "resolved"
        matched_q["resolved_answer"] = answer
        question_text = matched_q.get("question", "")

        update_flow_step(UUID(step_id), {"open_questions": questions})

        # Record revision
        try:
            from app.db.revisions_enrichment import insert_enrichment_revision
            insert_enrichment_revision(
                project_id=project_id,
                entity_type="solution_flow_step",
                entity_id=UUID(step_id),
                entity_label=step.get("title", ""),
                revision_type="updated",
                trigger_event="question_resolved",
                changes={"question_resolved": {"question": question_text, "answer": answer}},
                diff_summary=f"Resolved: {question_text[:80]}",
                created_by="chat_assistant",
            )
        except Exception:
            pass

        # Re-fetch full step data for optimistic update
        step_data = get_flow_step(UUID(step_id))
        return {
            "success": True,
            "answer": answer,
            "question_text": question_text,
            "step_data": step_data,
        }
    except Exception as e:
        return {"error": str(e)}


async def _escalate_to_client(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Escalate an open question to the client by creating a pending item."""
    from app.db.solution_flow import get_flow_step, update_flow_step

    step_id = params.get("step_id")
    suggested_stakeholder = params.get("suggested_stakeholder")
    reason = params.get("reason")

    if not step_id:
        return {"error": "step_id is required"}

    try:
        step = get_flow_step(UUID(step_id))
        if not step:
            return {"error": "Step not found"}

        # Find and update the question status to escalated
        questions = step.get("open_questions") or []
        idx, matched_q = _match_question(questions, params)

        if idx is None or matched_q is None:
            return {"error": "Question not found — check question_index or question_text"}

        matched_q["status"] = "escalated"
        matched_q["escalated_to"] = suggested_stakeholder or "client"
        question_text = matched_q.get("question", "")

        update_flow_step(UUID(step_id), {"open_questions": questions})

        # Create pending item
        supabase = get_supabase()
        pending_row = {
            "project_id": str(project_id),
            "item_type": "open_question",
            "source": "solution_flow",
            "entity_id": step_id,
            "title": question_text,
            "why_needed": reason or f"Escalated from solution flow step: {step.get('title', '')}",
            "priority": "high",
        }
        result = supabase.table("pending_items").insert(pending_row).execute()
        pending_item_id = result.data[0]["id"] if result.data else None

        # Record revision
        try:
            from app.db.revisions_enrichment import insert_enrichment_revision
            insert_enrichment_revision(
                project_id=project_id,
                entity_type="solution_flow_step",
                entity_id=UUID(step_id),
                entity_label=step.get("title", ""),
                revision_type="updated",
                trigger_event="question_escalated",
                changes={"question_escalated": {"question": question_text, "escalated_to": suggested_stakeholder or "client"}},
                diff_summary=f"Escalated to {suggested_stakeholder or 'client'}: {question_text[:60]}",
                created_by="chat_assistant",
            )
        except Exception:
            pass

        # Re-fetch full step data for optimistic update
        step_data = get_flow_step(UUID(step_id))
        return {
            "success": True,
            "question": question_text,
            "escalated_to": suggested_stakeholder or "client",
            "pending_item_id": pending_item_id,
            "step_data": step_data,
        }
    except Exception as e:
        return {"error": str(e)}


async def _refine_solution_flow_step(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Refine a solution flow step using AI."""
    from app.chains.refine_solution_flow_step import refine_solution_flow_step

    step_id = params.get("step_id")
    instruction = params.get("instruction", "")

    if not step_id or not instruction:
        return {"error": "step_id and instruction are required"}

    return await refine_solution_flow_step(str(project_id), step_id, instruction)
