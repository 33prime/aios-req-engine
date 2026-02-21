"""Generate Solution Flow steps from project BRD data — v2.

4-stage parallel pipeline:
  Stage 0: Snapshot — readiness gate, context assembly, confirmed step preservation
  Stage 1: Decompose (Haiku) — plan phases + preserve confirmed step slots
  Stage 2: Parallel Generate (Sonnet x 3-4) — per-phase step generation
  Stage 3: Stitch + Validate (Haiku) — cross-phase ordering + validation

Architecture principles:
- Confirmed steps are NEVER deleted — preserved across regeneration
- needs_review steps treated as soft constraints (preserve intent)
- Resolved Q&A from existing steps feed as project knowledge
- Per-phase retrieval enrichment for better evidence grounding
- Non-destructive persistence: only ai_generated/needs_review steps are replaced
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2
_INITIAL_DELAY = 1.0


# =============================================================================
# Tool schemas for structured output
# =============================================================================

PHASE_PLAN_TOOL = {
    "name": "submit_phase_plan",
    "description": "Submit the decomposition of the solution flow into phases.",
    "input_schema": {
        "type": "object",
        "properties": {
            "phases": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "phase": {
                            "type": "string",
                            "enum": ["entry", "core_experience", "output", "admin"],
                        },
                        "target_step_count": {"type": "integer", "minimum": 1, "maximum": 6},
                        "focus": {"type": "string"},
                        "relevant_workflow_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "relevant_feature_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["phase", "target_step_count", "focus"],
                },
                "minItems": 2,
                "maxItems": 4,
            },
            "preserved_step_indices": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Indices where confirmed steps should sit in the final ordering",
            },
            "total_target": {"type": "integer", "minimum": 3, "maximum": 20},
        },
        "required": ["phases", "total_target"],
    },
}

PHASE_STEPS_TOOL = {
    "name": "submit_phase_steps",
    "description": "Submit generated steps for a specific phase.",
    "input_schema": {
        "type": "object",
        "properties": {
            "steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "goal": {"type": "string"},
                        "phase": {
                            "type": "string",
                            "enum": ["entry", "core_experience", "output", "admin"],
                        },
                        "actors": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "information_fields": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "type": {
                                        "type": "string",
                                        "enum": ["captured", "displayed", "computed"],
                                    },
                                    "mock_value": {"type": "string"},
                                    "confidence": {
                                        "type": "string",
                                        "enum": ["known", "inferred", "guess", "unknown"],
                                    },
                                },
                                "required": ["name", "type", "mock_value", "confidence"],
                            },
                        },
                        "mock_data_narrative": {"type": "string"},
                        "open_questions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "question": {"type": "string"},
                                    "context": {"type": "string"},
                                },
                                "required": ["question"],
                            },
                        },
                        "implied_pattern": {"type": "string"},
                        "linked_workflow_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "linked_feature_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "linked_data_entity_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": [
                        "title", "goal", "phase", "actors",
                        "information_fields", "mock_data_narrative",
                        "implied_pattern",
                    ],
                },
                "minItems": 1,
                "maxItems": 8,
            },
            "phase_notes": {
                "type": "string",
                "description": "Cross-phase dependencies or data flow notes",
            },
        },
        "required": ["steps"],
    },
}

STITCH_TOOL = {
    "name": "submit_stitch_result",
    "description": "Submit the final validated ordering and summary.",
    "input_schema": {
        "type": "object",
        "properties": {
            "ordered_titles": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Step titles in final order",
            },
            "summary": {
                "type": "string",
                "description": "2-3 sentence overview of the solution flow",
            },
            "data_flow_notes": {
                "type": "string",
                "description": "Cross-step data flow and dependency notes",
            },
        },
        "required": ["ordered_titles", "summary"],
    },
}


# =============================================================================
# System prompts
# =============================================================================

SYSTEM_PROMPT = """You are a senior product consultant transforming flat BRD data (workflows, features, data entities, personas) into a goal-oriented Solution Flow.

## What a Solution Flow Is

A Solution Flow is a sequential journey through the application from the user's perspective. Each step answers:
1. **What goal must be achieved here?** (not "what screen" — what outcome)
2. **What information is needed?** (captured from user, displayed from system, computed)
3. **What does it look like with real data?** (mock data narrative)

## Phases

Steps belong to one of four phases:
- **entry**: Onboarding, registration, initial setup — how users enter the system
- **core_experience**: The primary value-delivering interactions — where the magic happens
- **output**: Reports, exports, deliverables — tangible outcomes users take away
- **admin**: Configuration, settings, management — supporting operations

## Rules

1. Each step must have a clear, actionable goal — NOT "view dashboard" but "identify which accounts need attention today"
2. Information fields must have realistic mock values — use specific names, numbers, dates from the project context
3. Confidence levels matter: "known" = explicitly in BRD data, "inferred" = logically derived, "guess" = reasonable assumption, "unknown" = needs client input
4. Mark open questions for anything that needs client clarification — these become action items
5. Link steps to the workflows, features, and data entities they synthesize — use the actual IDs from the context
6. The implied_pattern should suggest a UI approach (form, table, dashboard, card list, wizard, etc.)
7. Order steps in a natural user journey — entry first, then core experience, then output, admin last
8. The mock_data_narrative should read like a user story: "Sarah opens her booth management screen and sees..."
"""

DECOMPOSE_PROMPT = """Analyze this project data and plan a Solution Flow by decomposing it into phases.

<project_context>
{context}
</project_context>

{confirmed_section}

Plan the phases and how many steps each needs. Target 5-12 total steps.
Consider confirmed step positions — they must stay in place.
"""

PHASE_GENERATION_PROMPT = """Generate steps for the {phase} phase of the Solution Flow.

## YOUR PHASE: {phase}
Generate {target_step_count} steps for the {phase} phase.
Focus: {focus}

<project_context>
{context}
</project_context>

{confirmed_section}

{needs_review_section}

{resolved_qa_section}

{retrieval_section}

Link steps to actual workflow IDs, feature IDs, and data entity IDs from the context.
Each step must have a clear, actionable goal — NOT "view dashboard" but "identify which accounts need attention today".
Mock data narratives should read like user stories with specific names and values.
"""


# =============================================================================
# Context Assembly — Fan-Out + Budget Allocation
# =============================================================================

CONTEXT_BUDGET = {
    "business_context": 800,
    "personas": 1200,
    "workflows": 2500,
    "features": 1500,
    "data_entities": 1000,
    "constraints": 500,
}


async def _load_context(project_id: UUID) -> str:
    """Load project data for context, all queries in parallel."""
    from app.db.supabase_client import get_supabase

    supabase = get_supabase()
    pid = str(project_id)

    def _q_project():
        try:
            r = supabase.table("projects").select(
                "name, vision, project_type"
            ).eq("id", pid).maybe_single().execute()
            return r.data if r else None
        except Exception as e:
            if "204" in str(e):
                return None
            raise

    def _q_personas():
        return supabase.table("personas").select(
            "id, name, role, goals, pain_points"
        ).eq("project_id", pid).execute().data or []

    def _q_workflows():
        wfs = supabase.table("workflows").select(
            "id, name, description, state_type, confirmation_status"
        ).eq("project_id", pid).execute().data or []
        for wf in wfs:
            steps = supabase.table("vp_steps").select(
                "id, step_index, label, description, automation_level, operation_type, time_minutes, pain_description"
            ).eq("workflow_id", wf["id"]).order("step_index").execute().data or []
            wf["steps"] = steps
        return wfs

    def _q_features():
        return supabase.table("features").select(
            "id, name, overview, priority_group, category"
        ).eq("project_id", pid).execute().data or []

    def _q_data_entities():
        return supabase.table("data_entities").select(
            "id, name, description, fields, entity_category"
        ).eq("project_id", pid).execute().data or []

    def _q_constraints():
        return supabase.table("constraints").select(
            "id, title, description, constraint_type"
        ).eq("project_id", pid).execute().data or []

    def _q_drivers():
        return supabase.table("business_drivers").select(
            "id, driver_type, description, severity"
        ).eq("project_id", pid).execute().data or []

    project, personas, workflows, features, data_entities, constraints, drivers = (
        await asyncio.gather(
            asyncio.to_thread(_q_project),
            asyncio.to_thread(_q_personas),
            asyncio.to_thread(_q_workflows),
            asyncio.to_thread(_q_features),
            asyncio.to_thread(_q_data_entities),
            asyncio.to_thread(_q_constraints),
            asyncio.to_thread(_q_drivers),
        )
    )

    sections: list[str] = []

    if project:
        parts = ["<business_context>"]
        if project.get("name"):
            parts.append(f"Project: {project['name']}")
        if project.get("project_type"):
            parts.append(f"Type: {project['project_type']}")
        if project.get("vision"):
            parts.append(f"Vision: {project['vision'][:500]}")
        for d in drivers:
            dtype = d.get("driver_type", "")
            desc = d.get("description", "")[:150]
            parts.append(f"[{dtype}] {desc}")
        parts.append("</business_context>")
        sections.append("\n".join(parts))

    if personas:
        parts = ["<personas>"]
        for p in personas:
            line = f"- {p.get('name', '?')} (id: {p['id']}) — {p.get('role', '?')}"
            goals = p.get("goals") or []
            if isinstance(goals, list) and goals:
                line += f" | Goals: {', '.join(str(g) for g in goals[:3])}"
            pains = p.get("pain_points") or []
            if isinstance(pains, list) and pains:
                line += f" | Pains: {', '.join(str(pp) for pp in pains[:3])}"
            parts.append(line)
        parts.append("</personas>")
        sections.append("\n".join(parts))

    if workflows:
        parts = ["<workflows>"]
        for wf in workflows:
            state = wf.get("state_type", "future")
            conf = wf.get("confirmation_status", "ai_generated")
            parts.append(f"## {wf.get('name', '?')} (id: {wf['id']}, {state}, {conf})")
            if wf.get("description"):
                parts.append(f"  {wf['description'][:200]}")
            for step in wf.get("steps", []):
                auto = step.get("automation_level", "manual")
                parts.append(
                    f"  - Step {step.get('step_index', '?')}: {step.get('label', '?')} "
                    f"(id: {step['id']}) [{step.get('operation_type', '?')}] {auto}"
                )
                if step.get("pain_description"):
                    parts.append(f"    Pain: {step['pain_description'][:100]}")
        parts.append("</workflows>")
        sections.append("\n".join(parts))

    if features:
        parts = ["<features>"]
        for f in features:
            pri = f.get("priority_group", "unset")
            parts.append(f"- {f.get('name', '?')} (id: {f['id']}, {pri})")
            if f.get("overview"):
                parts.append(f"  {f['overview'][:150]}")
        parts.append("</features>")
        sections.append("\n".join(parts))

    if data_entities:
        parts = ["<data_entities>"]
        for de in data_entities:
            parts.append(f"- {de.get('name', '?')} (id: {de['id']}, {de.get('entity_category', '?')})")
            if de.get("description"):
                parts.append(f"  {de['description'][:150]}")
            fields = de.get("fields") or []
            if fields and isinstance(fields, list):
                field_names = [
                    fi.get("name", "?") if isinstance(fi, dict) else str(fi)
                    for fi in fields[:10]
                ]
                parts.append(f"  Fields: {', '.join(field_names)}")
        parts.append("</data_entities>")
        sections.append("\n".join(parts))

    if constraints:
        parts = ["<constraints>"]
        for c in constraints:
            ctype = c.get("constraint_type", "?")
            parts.append(f"- [{ctype}] {c.get('title', c.get('description', '?'))[:100]}")
        parts.append("</constraints>")
        sections.append("\n".join(parts))

    return "\n\n".join(sections) if sections else "No project data available yet."


# =============================================================================
# Stage 0: Snapshot
# =============================================================================


def _snapshot_existing_steps(
    flow_id: UUID,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Snapshot existing steps into confirmed, needs_review, and ai_generated buckets.

    Returns:
        (confirmed_steps, needs_review_steps, ai_generated_steps)
    """
    from app.db.solution_flow import list_flow_steps

    steps = list_flow_steps(flow_id)

    confirmed = []
    needs_review = []
    ai_generated = []

    for step in steps:
        status = step.get("confirmation_status", "ai_generated")
        if status in ("confirmed_consultant", "confirmed_client"):
            confirmed.append(step)
        elif status == "needs_review":
            needs_review.append(step)
        else:
            ai_generated.append(step)

    return confirmed, needs_review, ai_generated


def _collect_resolved_qa(steps: list[dict]) -> str:
    """Collect resolved Q&A from all existing steps as project knowledge."""
    qa_pairs: list[str] = []
    for step in steps:
        for q in step.get("open_questions") or []:
            if isinstance(q, dict) and q.get("status") == "resolved":
                question = q.get("question", "")
                answer = q.get("resolved_answer", "")
                if question and answer:
                    qa_pairs.append(f"Q: {question}\nA: {answer}")

    if not qa_pairs:
        return ""

    return "## Resolved Knowledge\n" + "\n\n".join(qa_pairs[:20])


def _format_confirmed_steps(steps: list[dict]) -> str:
    """Format confirmed steps as constraints for prompts."""
    if not steps:
        return ""

    parts = ["## CONFIRMED STEPS (CONSTRAINTS — preserve exactly, do not modify)"]
    for step in steps:
        parts.append(
            f"- [{step.get('phase')}] \"{step.get('title')}\" "
            f"(index: {step.get('step_index')}) — {step.get('goal', '')[:100]}"
        )
    return "\n".join(parts)


def _format_needs_review_steps(steps: list[dict]) -> str:
    """Format needs_review steps as soft constraints."""
    if not steps:
        return ""

    parts = ["## SOFT CONSTRAINTS (needs_review — preserve intent, may modify details)"]
    for step in steps:
        parts.append(
            f"- [{step.get('phase')}] \"{step.get('title')}\" — {step.get('goal', '')[:100]}"
        )
    return "\n".join(parts)


# =============================================================================
# Stage 1: Decompose (Haiku)
# =============================================================================


async def _decompose_phases(
    context: str,
    confirmed_steps: list[dict],
    needs_review_steps: list[dict],
) -> dict[str, Any]:
    """Haiku-powered phase decomposition. Returns phase plan."""
    from anthropic import AsyncAnthropic

    from app.core.config import Settings

    settings = Settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    confirmed_section = _format_confirmed_steps(confirmed_steps)
    if not confirmed_section:
        confirmed_section = "No confirmed steps to preserve."

    prompt = DECOMPOSE_PROMPT.format(
        context=context[:4000],
        confirmed_section=confirmed_section,
    )

    t0 = time.monotonic()
    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        system=[{"type": "text", "text": SYSTEM_PROMPT}],
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        tools=[PHASE_PLAN_TOOL],
        tool_choice={"type": "tool", "name": "submit_phase_plan"},
    )
    elapsed_ms = int((time.monotonic() - t0) * 1000)

    plan: dict[str, Any] = {}
    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_phase_plan":
            plan = block.input
            break

    if not plan or not plan.get("phases"):
        logger.warning("Decomposition returned no phases, using default plan")
        plan = {
            "phases": [
                {"phase": "entry", "target_step_count": 2, "focus": "User onboarding and setup"},
                {"phase": "core_experience", "target_step_count": 4, "focus": "Primary value-delivering interactions"},
                {"phase": "output", "target_step_count": 2, "focus": "Reports, exports, deliverables"},
            ],
            "total_target": 8,
        }

    logger.info(f"Phase decomposition in {elapsed_ms}ms: {len(plan.get('phases', []))} phases, target={plan.get('total_target')}")

    try:
        _log_usage(None, "solution_flow_decompose", "claude-haiku-4-5-20251001", response, elapsed_ms)
    except Exception:
        pass

    return plan


# =============================================================================
# Stage 2: Parallel Phase Generation (Sonnet)
# =============================================================================


async def _generate_phase_steps(
    phase_config: dict[str, Any],
    context: str,
    confirmed_steps: list[dict],
    needs_review_steps: list[dict],
    resolved_qa: str,
    project_id: UUID,
) -> list[dict]:
    """Generate steps for a single phase using Sonnet."""
    from anthropic import (
        APIConnectionError,
        APITimeoutError,
        AsyncAnthropic,
        InternalServerError,
        RateLimitError,
    )

    from app.core.config import Settings

    phase = phase_config["phase"]
    target_count = phase_config.get("target_step_count", 3)
    focus = phase_config.get("focus", "")

    # Filter confirmed/needs_review steps relevant to this phase
    phase_confirmed = [s for s in confirmed_steps if s.get("phase") == phase]
    phase_needs_review = [s for s in needs_review_steps if s.get("phase") == phase]

    # Per-phase retrieval
    retrieval_section = ""
    try:
        from app.core.retrieval import retrieve
        from app.core.retrieval_format import format_retrieval_for_context

        retrieval_result = await retrieve(
            query=f"{phase} phase: {focus}",
            project_id=str(project_id),
            max_rounds=1,
            entity_types=["workflow", "feature", "constraint", "data_entity"],
            evaluation_criteria=f"Need: {phase} phase requirements and constraints",
            context_hint=f"generating {phase} phase of solution flow",
            skip_reranking=True,
        )
        formatted = format_retrieval_for_context(
            retrieval_result, style="generation", max_tokens=1000
        )
        if formatted:
            retrieval_section = f"## Retrieved Evidence\n{formatted}"
    except Exception:
        pass

    prompt = PHASE_GENERATION_PROMPT.format(
        phase=phase,
        target_step_count=target_count,
        focus=focus,
        context=context[:4000],
        confirmed_section=_format_confirmed_steps(phase_confirmed) or "No confirmed steps in this phase.",
        needs_review_section=_format_needs_review_steps(phase_needs_review) or "",
        resolved_qa_section=resolved_qa[:1000] if resolved_qa else "",
        retrieval_section=retrieval_section,
    )

    settings = Settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    last_error: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            t0 = time.monotonic()
            response = await client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=3000,
                system=[
                    {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}},
                ],
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                tools=[PHASE_STEPS_TOOL],
                tool_choice={"type": "tool", "name": "submit_phase_steps"},
            )
            elapsed_ms = int((time.monotonic() - t0) * 1000)

            for block in response.content:
                if block.type == "tool_use" and block.name == "submit_phase_steps":
                    steps = block.input.get("steps", [])
                    logger.info(
                        f"Phase '{phase}' generated {len(steps)} steps in {elapsed_ms}ms "
                        f"(in={response.usage.input_tokens}, out={response.usage.output_tokens})"
                    )
                    try:
                        _log_usage(
                            project_id, f"solution_flow_phase_{phase}",
                            "claude-sonnet-4-5-20250929", response, elapsed_ms,
                        )
                    except Exception:
                        pass
                    return steps

            logger.warning(f"Phase '{phase}': no tool_use block in response")
            return []

        except (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError) as e:
            last_error = e
            if attempt < _MAX_RETRIES:
                delay = _INITIAL_DELAY * (2 ** attempt)
                logger.warning(f"Phase '{phase}' attempt {attempt + 1} failed: {e}. Retry in {delay}s")
                await asyncio.sleep(delay)
            else:
                logger.error(f"Phase '{phase}' all attempts failed: {e}")

    return []


# =============================================================================
# Stage 3: Stitch + Validate (Haiku)
# =============================================================================


async def _stitch_and_validate(
    all_steps: list[dict],
    confirmed_steps: list[dict],
    context: str,
) -> dict[str, Any]:
    """Haiku-powered cross-phase stitching and validation."""
    from anthropic import AsyncAnthropic

    from app.core.config import Settings

    if not all_steps:
        return {"ordered_titles": [], "summary": "No steps generated.", "data_flow_notes": ""}

    # Build step summary for validation
    step_lines = []
    for i, s in enumerate(all_steps):
        step_lines.append(
            f"{i+1}. [{s.get('phase')}] {s.get('title')}: {s.get('goal', '')[:80]}"
        )

    confirmed_lines = []
    for s in confirmed_steps:
        confirmed_lines.append(
            f"- [{s.get('phase')}] \"{s.get('title')}\" (MUST be preserved)"
        )

    prompt = (
        f"Review and validate these solution flow steps, then order them correctly.\n\n"
        f"Generated Steps:\n" + "\n".join(step_lines) + "\n\n"
    )
    if confirmed_lines:
        prompt += "Confirmed Steps (already preserved, included for context):\n" + "\n".join(confirmed_lines) + "\n\n"
    prompt += (
        f"Context Summary:\n{context[:2000]}\n\n"
        f"Validate:\n"
        f"1) Goals are actionable (not vague)\n"
        f"2) No duplicate steps\n"
        f"3) Phase ordering: entry → core_experience → output → admin\n"
        f"4) At least 3 steps total\n\n"
        f"Return the step titles in correct order plus a 2-3 sentence summary."
    )

    settings = Settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    try:
        t0 = time.monotonic()
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            system=[{"type": "text", "text": "You are validating a solution flow. Order steps logically and provide a concise summary."}],
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            tools=[STITCH_TOOL],
            tool_choice={"type": "tool", "name": "submit_stitch_result"},
        )
        elapsed_ms = int((time.monotonic() - t0) * 1000)

        for block in response.content:
            if block.type == "tool_use" and block.name == "submit_stitch_result":
                result = block.input
                logger.info(f"Stitch validated in {elapsed_ms}ms: {len(result.get('ordered_titles', []))} ordered")
                try:
                    _log_usage(None, "solution_flow_stitch", "claude-haiku-4-5-20251001", response, elapsed_ms)
                except Exception:
                    pass
                return result

    except Exception as e:
        logger.warning(f"Stitch validation failed: {e}. Using generation order.")

    # Fallback: use generation order
    return {
        "ordered_titles": [s.get("title", "") for s in all_steps],
        "summary": "Solution flow generated from project data.",
        "data_flow_notes": "",
    }


# =============================================================================
# Persistence — Non-destructive
# =============================================================================


def _persist_steps(
    flow_id: UUID,
    project_id: UUID,
    new_steps: list[dict],
    confirmed_steps: list[dict],
    stitch_result: dict[str, Any],
    generation_version: int,
) -> list[dict]:
    """Persist generated steps alongside preserved confirmed steps.

    1. Delete only ai_generated and needs_review steps
    2. Keep confirmed steps, update preserved_from_version
    3. Insert new steps with correct step_index around confirmed ones
    4. Embed all new steps
    """
    from app.db.entity_embeddings import embed_entity
    from app.db.solution_flow import create_flow_step, update_flow_step
    from app.db.supabase_client import get_supabase

    supabase = get_supabase()

    # Delete only ai_generated + needs_review steps
    supabase.table("solution_flow_steps").delete().eq(
        "flow_id", str(flow_id)
    ).in_(
        "confirmation_status", ["ai_generated", "needs_review"]
    ).execute()

    # Mark confirmed steps as preserved
    for step in confirmed_steps:
        try:
            update_flow_step(UUID(step["id"]), {
                "preserved_from_version": generation_version - 1,
                "generation_version": generation_version,
            })
        except Exception as e:
            logger.warning(f"Failed to mark preserved step {step['id']}: {e}")

    # Order all steps: use stitch ordering if available
    ordered_titles = stitch_result.get("ordered_titles", [])
    title_order = {title: i for i, title in enumerate(ordered_titles)}

    # Build combined list: confirmed (keep their positions) + new (ordered by stitch)
    all_entries: list[tuple[int, dict, bool]] = []  # (sort_key, step, is_new)

    # Confirmed steps get their existing indices as sort keys
    for step in confirmed_steps:
        sort_key = step.get("step_index", 0)
        # If stitch mentioned this title, use stitch order
        if step.get("title") in title_order:
            sort_key = title_order[step["title"]]
        all_entries.append((sort_key, step, False))

    # New steps: use stitch ordering if available, else append after confirmed
    for step in new_steps:
        if step.get("title") in title_order:
            sort_key = title_order[step["title"]]
        else:
            sort_key = 100 + len(all_entries)  # append at end
        all_entries.append((sort_key, step, True))

    # Sort by key
    all_entries.sort(key=lambda x: x[0])

    # Reindex and persist
    saved_steps: list[dict] = []
    for i, (_, step, is_new) in enumerate(all_entries):
        if is_new:
            step["step_index"] = i
            step.setdefault("open_questions", [])
            for q in step.get("open_questions", []):
                q.setdefault("status", "open")
            step["generation_version"] = generation_version
            try:
                saved = create_flow_step(flow_id, project_id, step)
                saved_steps.append(saved)

                # Embed new step (fire-and-forget)
                try:
                    embed_entity("solution_flow_step", UUID(saved["id"]), saved)
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"Failed to save step {i} '{step.get('title')}': {e}")
        else:
            # Update index on confirmed step
            try:
                update_flow_step(UUID(step["id"]), {"step_index": i})
                saved_steps.append(step)
            except Exception as e:
                logger.warning(f"Failed to reindex confirmed step {step['id']}: {e}")

    return saved_steps


# =============================================================================
# Build background narratives
# =============================================================================


def _build_narratives_for_steps(
    saved_steps: list[dict],
    project_id: UUID,
) -> None:
    """Build background narratives for newly generated steps. Fire-and-forget."""
    try:
        from app.core.solution_flow_narrative import build_step_narrative
        from app.db.solution_flow import update_flow_step

        for step in saved_steps:
            if step.get("confirmation_status") in ("confirmed_consultant", "confirmed_client"):
                continue  # Don't overwrite confirmed step narratives
            try:
                narrative = build_step_narrative(step, project_id)
                if narrative:
                    update_flow_step(UUID(step["id"]), {"background_narrative": narrative})
            except Exception as e:
                logger.debug(f"Narrative build failed for step {step.get('id')}: {e}")
    except Exception as e:
        logger.warning(f"Narrative building failed: {e}")


# =============================================================================
# Main generation function
# =============================================================================


async def generate_solution_flow(
    project_id: UUID, flow_id: UUID
) -> dict[str, Any]:
    """Generate solution flow steps from project BRD data.

    4-stage parallel pipeline:
    - Stage 0: Snapshot existing steps + load context
    - Stage 1: Decompose into phases (Haiku)
    - Stage 2: Generate per-phase steps in parallel (Sonnet)
    - Stage 3: Stitch + validate (Haiku)
    """
    from app.db.solution_flow import update_flow

    # ── Stage 0: Snapshot ────────────────────────────────────────────────────
    # Load context + snapshot existing steps in parallel
    context_task = _load_context(project_id)
    snapshot_task = asyncio.to_thread(
        _snapshot_existing_steps, flow_id
    )

    context_text, (confirmed_steps, needs_review_steps, ai_steps) = await asyncio.gather(
        context_task, snapshot_task
    )

    # Enrich context with retrieval evidence
    try:
        from app.core.retrieval import retrieve
        from app.core.retrieval_format import format_retrieval_for_context

        retrieval_result = await retrieve(
            query="pain points, goals, constraints, and desired outcomes for workflows",
            project_id=str(project_id),
            max_rounds=2,
            entity_types=["workflow", "feature", "constraint", "data_entity"],
            evaluation_criteria="Need: current pain, desired outcome, technical constraints",
            context_hint="generating solution architecture",
            skip_reranking=True,
        )
        retrieval_evidence = format_retrieval_for_context(
            retrieval_result, style="generation", max_tokens=2000
        )
        if retrieval_evidence:
            context_text += f"\n\n## Retrieved Evidence\n{retrieval_evidence}"
    except Exception:
        pass

    # Collect resolved Q&A from ALL existing steps (confirmed + needs_review + ai)
    all_existing = confirmed_steps + needs_review_steps + ai_steps
    resolved_qa = _collect_resolved_qa(all_existing)

    # Calculate generation version
    current_version = max(
        (s.get("generation_version", 1) for s in all_existing),
        default=0,
    )
    new_version = current_version + 1

    logger.info(
        f"Snapshot: {len(confirmed_steps)} confirmed, {len(needs_review_steps)} needs_review, "
        f"{len(ai_steps)} ai_generated. Version {current_version} → {new_version}"
    )

    # ── Stage 1: Decompose ───────────────────────────────────────────────────
    plan = await _decompose_phases(context_text, confirmed_steps, needs_review_steps)

    # ── Stage 2: Parallel Phase Generation ───────────────────────────────────
    phases = plan.get("phases", [])
    phase_tasks = [
        _generate_phase_steps(
            phase_config=phase,
            context=context_text,
            confirmed_steps=confirmed_steps,
            needs_review_steps=needs_review_steps,
            resolved_qa=resolved_qa,
            project_id=project_id,
        )
        for phase in phases
    ]

    phase_results = await asyncio.gather(*phase_tasks, return_exceptions=True)

    # Collect all generated steps, handling errors
    all_generated_steps: list[dict] = []
    for i, result in enumerate(phase_results):
        if isinstance(result, Exception):
            phase_name = phases[i].get("phase", "?") if i < len(phases) else "?"
            logger.error(f"Phase '{phase_name}' generation failed: {result}")
            continue
        if isinstance(result, list):
            all_generated_steps.extend(result)

    if not all_generated_steps and not confirmed_steps:
        return {"error": "No steps generated", "steps": []}

    logger.info(f"Generated {len(all_generated_steps)} new steps across {len(phases)} phases")

    # ── Stage 3: Stitch + Validate ───────────────────────────────────────────
    # Combine confirmed + new for ordering
    combined_for_stitch = [
        {"title": s.get("title"), "phase": s.get("phase"), "goal": s.get("goal")}
        for s in confirmed_steps
    ] + all_generated_steps

    stitch_result = await _stitch_and_validate(
        combined_for_stitch, confirmed_steps, context_text
    )

    # ── Persistence ──────────────────────────────────────────────────────────
    saved_steps = _persist_steps(
        flow_id=flow_id,
        project_id=project_id,
        new_steps=all_generated_steps,
        confirmed_steps=confirmed_steps,
        stitch_result=stitch_result,
        generation_version=new_version,
    )

    # Update flow metadata
    summary = stitch_result.get("summary", "")
    generation_metadata = {
        "version": new_version,
        "phases_requested": len(phases),
        "steps_generated": len(all_generated_steps),
        "steps_preserved": len(confirmed_steps),
        "data_flow_notes": stitch_result.get("data_flow_notes", ""),
    }

    try:
        update_flow(flow_id, {
            "summary": summary,
            "generation_metadata": json.dumps(generation_metadata),
        })
        from app.db.supabase_client import get_supabase
        get_supabase().table("solution_flows").update({
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }).eq("id", str(flow_id)).execute()
    except Exception as e:
        logger.warning(f"Failed to update flow metadata: {e}")

    # Build background narratives (fire-and-forget in thread)
    try:
        import threading
        threading.Thread(
            target=_build_narratives_for_steps,
            args=(saved_steps, project_id),
            daemon=True,
        ).start()
    except Exception:
        pass

    return {
        "flow_id": str(flow_id),
        "summary": summary,
        "steps_generated": len(all_generated_steps),
        "steps_preserved": len(confirmed_steps),
        "steps": saved_steps,
    }


def _log_usage(
    project_id: UUID | None,
    operation: str,
    model: str,
    response: Any,
    elapsed_ms: int,
) -> None:
    """Log LLM usage via centralized logger."""
    from app.core.llm_usage import log_llm_usage

    usage = response.usage
    log_llm_usage(
        workflow="solution_flow",
        chain=operation,
        model=model,
        provider="anthropic",
        tokens_input=usage.input_tokens,
        tokens_output=usage.output_tokens,
        tokens_cache_read=getattr(usage, "cache_read_input_tokens", 0) or 0,
        tokens_cache_create=getattr(usage, "cache_creation_input_tokens", 0) or 0,
        duration_ms=elapsed_ms,
        project_id=project_id,
    )
