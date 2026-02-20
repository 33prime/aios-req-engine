"""Chain for AI-driven refinement of a single solution flow step."""

from __future__ import annotations

from typing import Any

from anthropic import AsyncAnthropic

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.solution_flow import get_flow_step, update_flow_step
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

_SUBMIT_TOOL = {
    "name": "submit_step_changes",
    "description": "Submit the refined fields for this solution flow step. Only include fields you want to change.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "goal": {"type": "string"},
            "phase": {"type": "string", "enum": ["entry", "core_experience", "output", "admin"]},
            "actors": {"type": "array", "items": {"type": "string"}},
            "mock_data_narrative": {"type": "string"},
            "implied_pattern": {"type": "string"},
            "information_fields": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "type": {"type": "string", "enum": ["captured", "displayed", "computed"]},
                        "mock_value": {"type": "string"},
                        "confidence": {"type": "string", "enum": ["known", "inferred", "guess", "unknown"]},
                    },
                    "required": ["name", "type", "mock_value", "confidence"],
                },
            },
            "open_questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "context": {"type": "string"},
                        "status": {"type": "string", "enum": ["open", "resolved", "escalated"]},
                        "resolved_answer": {"type": "string"},
                    },
                    "required": ["question"],
                },
            },
        },
    },
}

# Fields that should not be overwritten if confirmed by client/consultant
_PROTECTED_STATUSES = {"confirmed_client", "confirmed_consultant"}


def _resolve_entity_names(ids: list[str], table: str, name_field: str = "name") -> list[str]:
    """Batch-resolve entity IDs to names."""
    if not ids:
        return []
    supabase = get_supabase()
    try:
        result = (
            supabase.table(table)
            .select(f"id, {name_field}")
            .in_("id", ids)
            .execute()
        )
        lookup = {r["id"]: r.get(name_field, "?") for r in (result.data or [])}
        return [lookup.get(i, i[:8]) for i in ids]
    except Exception:
        return [i[:8] for i in ids]


async def refine_solution_flow_step(
    project_id: str, step_id: str, instruction: str
) -> dict[str, Any]:
    """Refine a solution flow step using AI based on an instruction.

    1. Loads step detail + resolves linked entity names
    2. Builds focused prompt
    3. Calls Sonnet with forced tool_use
    4. Respects confirmation status (skip confirmed fields)
    5. Applies changes

    Returns dict with success, step_id, changes_summary, updated_fields.
    """
    from uuid import UUID

    step = get_flow_step(UUID(step_id))
    if not step:
        return {"error": f"Step not found: {step_id}"}

    # Resolve linked entity names
    feature_names = _resolve_entity_names(
        step.get("linked_feature_ids") or [], "features"
    )
    workflow_names = _resolve_entity_names(
        step.get("linked_workflow_ids") or [], "workflows"
    )
    data_entity_names = _resolve_entity_names(
        step.get("linked_data_entity_ids") or [], "data_entities"
    )

    # Build step context
    linked_parts = []
    if feature_names:
        linked_parts.append(f"Linked features: {', '.join(feature_names)}")
    if workflow_names:
        linked_parts.append(f"Linked workflows: {', '.join(workflow_names)}")
    if data_entity_names:
        linked_parts.append(f"Linked data entities: {', '.join(data_entity_names)}")
    linked_str = "\n".join(linked_parts) if linked_parts else "No linked entities."

    info_fields_str = ""
    for f in step.get("information_fields") or []:
        if isinstance(f, dict):
            info_fields_str += f"\n  - {f.get('name', '?')} ({f.get('type', '?')}, confidence: {f.get('confidence', '?')}): {f.get('mock_value', '')}"

    open_qs_str = ""
    for q in step.get("open_questions") or []:
        if isinstance(q, dict):
            status = q.get("status", "open")
            open_qs_str += f"\n  - [{status}] {q.get('question', '?')}"

    prompt = f"""You are refining a single solution flow step. Return ONLY the fields that should change using the submit_step_changes tool.

## Current Step
- Title: {step.get('title', '?')}
- Goal: {step.get('goal', '?')}
- Phase: {step.get('phase', '?')}
- Actors: {', '.join(step.get('actors') or [])}
- Implied Pattern: {step.get('implied_pattern') or 'None'}
- Mock Data Narrative: {step.get('mock_data_narrative') or 'None'}

## Information Fields{info_fields_str or ' None'}

## Open Questions{open_qs_str or ' None'}

## Linked Entities
{linked_str}

## Instruction
{instruction}

Rules:
- Only return fields that need to change based on the instruction.
- Preserve existing open questions and information fields unless the instruction specifically asks to change them.
- If adding new information fields, include the full set (existing + new).
- Keep responses focused and minimal."""

    try:
        client = AsyncAnthropic(api_key=get_settings().ANTHROPIC_API_KEY)
        response = await client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4000,
            temperature=0.2,
            tools=[_SUBMIT_TOOL],
            tool_choice={"type": "tool", "name": "submit_step_changes"},
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        logger.error(f"Refinement LLM call failed: {e}")
        return {"error": f"LLM call failed: {e}"}

    # Extract tool use result
    changes: dict[str, Any] = {}
    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_step_changes":
            changes = block.input
            break

    if not changes:
        return {"error": "No changes proposed by the model"}

    # Respect confirmation status — skip changes to confirmed steps
    conf_status = step.get("confirmation_status")
    if conf_status in _PROTECTED_STATUSES:
        logger.info(
            f"Step {step_id} is {conf_status} — skipping refinement"
        )
        return {
            "success": False,
            "step_id": step_id,
            "message": f"Step is {conf_status} and cannot be refined by AI.",
            "updated_fields": [],
        }

    # Apply changes
    try:
        update_flow_step(UUID(step_id), changes)
    except Exception as e:
        return {"error": f"Failed to apply changes: {e}"}

    updated_fields = list(changes.keys())
    # Build human-readable summary
    summary_parts = []
    if "title" in changes:
        summary_parts.append(f"title → '{changes['title']}'")
    if "goal" in changes:
        summary_parts.append("updated goal")
    if "actors" in changes:
        summary_parts.append(f"actors → {changes['actors']}")
    if "information_fields" in changes:
        summary_parts.append(f"{len(changes['information_fields'])} info fields")
    if "open_questions" in changes:
        summary_parts.append(f"{len(changes['open_questions'])} questions")
    if "phase" in changes:
        summary_parts.append(f"phase → {changes['phase']}")
    if "implied_pattern" in changes:
        summary_parts.append(f"pattern → {changes['implied_pattern']}")
    if "mock_data_narrative" in changes:
        summary_parts.append("updated preview narrative")

    changes_summary = "; ".join(summary_parts) if summary_parts else "minor adjustments"

    return {
        "success": True,
        "step_id": step_id,
        "changes_summary": changes_summary,
        "updated_fields": updated_fields,
    }
