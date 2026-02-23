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
            "success_criteria": {
                "type": "array",
                "items": {"type": "string"},
                "description": "What makes this step successful (measurable outcomes)",
            },
            "pain_points_addressed": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "persona": {"type": "string"},
                    },
                    "required": ["text"],
                },
                "description": "Pain points this step solves, with optional persona attribution",
            },
            "goals_addressed": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Business goals this step contributes to",
            },
            "ai_config": {
                "type": "object",
                "properties": {
                    "role": {"type": "string", "description": "What the AI does — shown as DATA IN"},
                    "behaviors": {"type": "array", "items": {"type": "string"}, "description": "Specific AI behaviors — shown as WHAT THE AI DOES"},
                    "guardrails": {"type": "array", "items": {"type": "string"}, "description": "Constraints/limits — shown as GUARDRAILS"},
                    "confidence_display": {"type": "string", "enum": ["hidden", "subtle", "prominent"], "description": "How confidence is shown to user — part of WHAT COMES OUT"},
                    "fallback": {"type": "string", "description": "What happens when AI fails — part of WHAT COMES OUT"},
                },
                "description": "AI behavior configuration. Has 4 visual sections: DATA IN (role), WHAT THE AI DOES (behaviors), GUARDRAILS (guardrails), WHAT COMES OUT (confidence_display + fallback). Preserve all sections when updating.",
            },
        },
    },
}

_FIELD_DISPLAY_NAMES: dict[str, str] = {
    "ai_config": "AI flow",
    "goal": "goal",
    "title": "title",
    "actors": "actors",
    "phase": "phase",
    "information_fields": "information fields",
    "open_questions": "open questions",
    "implied_pattern": "implied pattern",
    "success_criteria": "success criteria",
    "pain_points_addressed": "pain points",
    "goals_addressed": "goals",
    "mock_data_narrative": "experience narrative",
}


def _friendly_refine_summary(changes: dict[str, Any]) -> str:
    """Human-readable diff summary for AI refinement."""
    fields = [_FIELD_DISPLAY_NAMES.get(k, k.replace("_", " ")) for k in changes]
    if len(fields) == 1:
        return f"AI refined {fields[0]}"
    if len(fields) == 2:
        return f"AI refined {fields[0]} and {fields[1]}"
    return f"AI refined {', '.join(fields[:-1])}, and {fields[-1]}"


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

    # Build ai_config context
    ai_config = step.get("ai_config")
    ai_config_str = "None"
    if isinstance(ai_config, dict) and any(ai_config.values()):
        ai_parts = []
        role = ai_config.get("role") or ai_config.get("ai_role")
        if role:
            ai_parts.append(f"  DATA IN (role): {role}")
        if ai_config.get("behaviors"):
            ai_parts.append("  WHAT THE AI DOES (behaviors):")
            for b in ai_config["behaviors"]:
                ai_parts.append(f"    - {b}")
        if ai_config.get("guardrails"):
            ai_parts.append("  GUARDRAILS:")
            for g in ai_config["guardrails"]:
                ai_parts.append(f"    - {g}")
        if ai_config.get("confidence_display"):
            ai_parts.append(f"  WHAT COMES OUT — confidence display: {ai_config['confidence_display']}")
        if ai_config.get("fallback"):
            ai_parts.append(f"  WHAT COMES OUT — fallback: {ai_config['fallback']}")
        if ai_parts:
            ai_config_str = "\n".join(ai_parts)

    # Build success tab context
    success_parts = []
    criteria = step.get("success_criteria") or []
    if criteria:
        success_parts.append("Success Criteria: " + "; ".join(criteria))
    pps = step.get("pain_points_addressed") or []
    if pps:
        pp_strs = []
        for pp in pps:
            if isinstance(pp, dict):
                pp_strs.append(pp.get("text", "?") + (f" ({pp.get('persona')})" if pp.get("persona") else ""))
            else:
                pp_strs.append(str(pp))
        success_parts.append("Pain Points: " + "; ".join(pp_strs))
    goals = step.get("goals_addressed") or []
    if goals:
        success_parts.append("Goals Addressed: " + "; ".join(goals))
    success_str = "\n".join(success_parts) if success_parts else "None"

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

## AI Configuration
{ai_config_str}

## Success & Outcomes
{success_str}

## Linked Entities
{linked_str}

## Instruction
{instruction}

Rules:
- Only return fields that need to change based on the instruction.
- Preserve existing open questions and information fields unless the instruction specifically asks to change them.
- If adding new information fields, include the full set (existing + new).
- For ai_config: it has 4 visual sections (DATA IN, WHAT THE AI DOES, GUARDRAILS, WHAT COMES OUT). When updating, ALWAYS include ALL existing sections plus your changes — do NOT drop sections the user didn't mention.
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

    # Record revision
    try:
        from app.db.revisions_enrichment import insert_enrichment_revision
        # Build field-level diff
        change_diff = {}
        for field in changes:
            old_val = step.get(field)
            new_val = changes[field]
            if old_val != new_val:
                change_diff[field] = {"old": old_val, "new": new_val}
        insert_enrichment_revision(
            project_id=UUID(project_id),
            entity_type="solution_flow_step",
            entity_id=UUID(step_id),
            entity_label=step.get("title", ""),
            revision_type="updated",
            trigger_event="refine_chat_tool",
            changes=change_diff,
            diff_summary=_friendly_refine_summary(changes),
            created_by="chat_assistant",
        )
    except Exception:
        pass

    # Re-fetch full step data for optimistic update
    step_data = get_flow_step(UUID(step_id))

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
    if "success_criteria" in changes:
        summary_parts.append(f"{len(changes['success_criteria'])} success criteria")
    if "pain_points_addressed" in changes:
        summary_parts.append(f"{len(changes['pain_points_addressed'])} pain points")
    if "goals_addressed" in changes:
        summary_parts.append(f"{len(changes['goals_addressed'])} goals")
    if "ai_config" in changes:
        ai = changes["ai_config"]
        ai_sub = []
        if isinstance(ai, dict):
            if ai.get("behaviors"):
                ai_sub.append("behaviors")
            if ai.get("guardrails"):
                ai_sub.append("guardrails")
            if ai.get("confidence_display") or ai.get("fallback"):
                ai_sub.append("output")
        summary_parts.append(f"AI flow ({', '.join(ai_sub)})" if ai_sub else "AI flow")

    changes_summary = "; ".join(summary_parts) if summary_parts else "minor adjustments"

    return {
        "success": True,
        "step_id": step_id,
        "changes_summary": changes_summary,
        "updated_fields": updated_fields,
        "step_data": step_data,
    }
