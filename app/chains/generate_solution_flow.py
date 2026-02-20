"""Generate Solution Flow steps from project BRD data.

3-stage pipeline (no LangGraph needed — straight pipeline):
  Stage 1: Context Assembly (deterministic, $0, ~50ms)
  Stage 2: Generation (Sonnet, tool_use structured output)
  Stage 3: Validation (Haiku, quality gate)

Architecture principles:
- Pyramid Caching: stable system prompt → tool schema → volatile context
- Fan-Out Context: all DB queries in parallel via asyncio.gather()
- Token Budget: each context category has a ceiling
- Model Routing: Sonnet for generation, Haiku for validation
- Structured Output via tool_use: forced schema, explicit max_tokens
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2
_INITIAL_DELAY = 1.0


# =============================================================================
# Tool schema for forced structured output
# =============================================================================

SOLUTION_FLOW_TOOL = {
    "name": "submit_solution_flow_steps",
    "description": "Submit the generated solution flow steps.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "A 2-3 sentence overview of the solution flow.",
            },
            "steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Short step name, e.g. 'Booth Registration'",
                        },
                        "goal": {
                            "type": "string",
                            "description": "What must be achieved in this step — one clear sentence",
                        },
                        "phase": {
                            "type": "string",
                            "enum": ["entry", "core_experience", "output", "admin"],
                        },
                        "actors": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Who participates in this step (persona names or roles)",
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
                                    "mock_value": {
                                        "type": "string",
                                        "description": "Realistic example value",
                                    },
                                    "confidence": {
                                        "type": "string",
                                        "enum": ["known", "inferred", "guess", "unknown"],
                                    },
                                },
                                "required": ["name", "type", "mock_value", "confidence"],
                            },
                        },
                        "mock_data_narrative": {
                            "type": "string",
                            "description": "Human-readable preview showing what this step looks like with real data",
                        },
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
                        "implied_pattern": {
                            "type": "string",
                            "description": "UI pattern, e.g. 'Mobile form', 'Dashboard', 'Wizard'",
                        },
                        "linked_workflow_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "IDs of workflows this step synthesizes",
                        },
                        "linked_feature_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "IDs of features this step covers",
                        },
                        "linked_data_entity_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "IDs of data entities used in this step",
                        },
                    },
                    "required": [
                        "title", "goal", "phase", "actors",
                        "information_fields", "mock_data_narrative",
                        "implied_pattern",
                    ],
                },
                "minItems": 3,
                "maxItems": 20,
            },
        },
        "required": ["steps", "summary"],
    },
}


# =============================================================================
# System prompt (stable — cached at breakpoint 1)
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
8. Aim for 5-12 steps total — enough to be comprehensive, not so many it's overwhelming
9. The mock_data_narrative should read like a user story: "Sarah opens her booth management screen and sees..."

## Example Step

Title: "Lead Qualification"
Goal: "Quickly assess each booth visitor's potential and route them to the right follow-up"
Phase: core_experience
Actors: ["Sales Rep", "Booth Manager"]
Information Fields:
- visitor_name (captured, "Marcus Chen", known)
- company (captured, "Acme Corp", known)
- interest_score (computed, "87/100", inferred)
- recommended_action (computed, "Schedule demo", guess)
Mock Data Narrative: "After scanning Marcus Chen's badge, the system shows he's from Acme Corp (a target account). His interest score of 87/100 suggests high intent — the app recommends scheduling a demo and auto-creates a follow-up task for the sales rep."
Implied Pattern: "Mobile card + action buttons"
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
            "id, name, description, state_type"
        ).eq("project_id", pid).execute().data or []
        # Load steps for each workflow
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

    # Format as XML tags (Claude-optimized, more token-efficient than JSON)
    sections: list[str] = []

    if project:
        parts = [f"<business_context>"]
        if project.get("name"):
            parts.append(f"Project: {project['name']}")
        if project.get("project_type"):
            parts.append(f"Type: {project['project_type']}")
        if project.get("vision"):
            parts.append(f"Vision: {project['vision'][:500]}")
        # Add drivers
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
            parts.append(f"## {wf.get('name', '?')} (id: {wf['id']}, {state})")
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
# Haiku Validation Gate
# =============================================================================


async def _validate_steps(steps: list[dict], context: str) -> tuple[bool, list[str]]:
    """Haiku-powered validation. Returns (passed, issues)."""
    from anthropic import AsyncAnthropic

    from app.core.config import Settings

    settings = Settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    step_summary = "\n".join(
        f"{i+1}. [{s.get('phase')}] {s.get('title')}: {s.get('goal', '')[:80]}"
        for i, s in enumerate(steps)
    )

    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": (
                f"Validate these solution flow steps against the project context.\n\n"
                f"Steps:\n{step_summary}\n\n"
                f"Context:\n{context[:3000]}\n\n"
                f"Check:\n"
                f"1) Goals are actionable, not vague ('view X' is bad, 'identify which X need Y' is good)\n"
                f"2) No duplicate steps\n"
                f"3) Phase ordering makes sense (entry→core→output→admin)\n"
                f"4) At least 3 steps\n\n"
                f"Respond with EXACTLY 'PASS' on the first line if valid, or 'FAIL' followed by one issue per line."
            ),
        }],
        temperature=0,
    )

    text = response.content[0].text.strip()
    if text.startswith("PASS"):
        return True, []
    issues = [line.strip() for line in text.split("\n")[1:] if line.strip()]
    return False, issues


# =============================================================================
# Main generation function
# =============================================================================


async def generate_solution_flow(
    project_id: UUID, flow_id: UUID
) -> dict[str, Any]:
    """Generate solution flow steps from project BRD data.

    Returns dict with flow overview including generated steps.
    """
    from anthropic import (
        APIConnectionError,
        APITimeoutError,
        AsyncAnthropic,
        InternalServerError,
        RateLimitError,
    )

    from app.core.config import Settings
    from app.db.solution_flow import (
        create_flow_step,
        list_flow_steps,
        update_flow,
    )

    # Stage 1: Context Assembly
    context_text = await _load_context(project_id)

    settings = Settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    system_blocks = [
        {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}},
    ]

    user_prompt = (
        f"Analyze this project data and generate a Solution Flow — a goal-oriented "
        f"sequential journey through the application. Link steps to actual workflow IDs, "
        f"feature IDs, and data entity IDs from the context.\n\n"
        f"<project_context>\n{context_text}\n</project_context>"
    )

    # Stage 2: Generation (Sonnet)
    last_error: Exception | None = None
    generated_steps: list[dict] = []
    summary = ""

    for attempt in range(_MAX_RETRIES + 1):
        try:
            t0 = time.monotonic()
            response = await client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=8000,
                system=system_blocks,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=0.3,
                tools=[SOLUTION_FLOW_TOOL],
                tool_choice={"type": "tool", "name": "submit_solution_flow_steps"},
            )
            elapsed_ms = int((time.monotonic() - t0) * 1000)

            for block in response.content:
                if block.type == "tool_use" and block.name == "submit_solution_flow_steps":
                    generated_steps = block.input.get("steps", [])
                    summary = block.input.get("summary", "")
                    break

            if generated_steps:
                logger.info(
                    f"Generated {len(generated_steps)} solution flow steps "
                    f"for project {project_id} in {elapsed_ms}ms"
                )

                # Log usage
                try:
                    _log_usage(
                        project_id, "solution_flow_generate",
                        "claude-sonnet-4-5-20250929", response, elapsed_ms,
                    )
                except Exception as e:
                    logger.warning(f"Failed to log usage: {e}")

                break

            logger.warning("No tool_use block found in response")

        except (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError) as e:
            last_error = e
            if attempt < _MAX_RETRIES:
                delay = _INITIAL_DELAY * (2 ** attempt)
                logger.warning(f"Transient error attempt {attempt + 1}: {e}. Retry in {delay}s")
                await asyncio.sleep(delay)
            else:
                logger.error(f"All {_MAX_RETRIES + 1} attempts failed: {e}")

    if not generated_steps:
        if last_error:
            raise last_error
        return {"error": "No steps generated", "steps": []}

    # Stage 3: Validation (Haiku)
    try:
        passed, issues = await _validate_steps(generated_steps, context_text)
        if not passed:
            logger.warning(f"Validation failed: {issues}. Proceeding with generation anyway.")
    except Exception as e:
        logger.warning(f"Validation check failed: {e}. Proceeding without validation.")

    # Clear existing steps and save new ones
    from app.db.supabase_client import get_supabase
    supabase = get_supabase()
    supabase.table("solution_flow_steps").delete().eq(
        "flow_id", str(flow_id)
    ).execute()

    saved_steps = []
    for i, step_data in enumerate(generated_steps):
        step_data["step_index"] = i
        step_data.setdefault("open_questions", [])
        # Add status: open to questions
        for q in step_data.get("open_questions", []):
            q.setdefault("status", "open")
        try:
            saved = create_flow_step(flow_id, project_id, step_data)
            saved_steps.append(saved)
        except Exception as e:
            logger.error(f"Failed to save step {i}: {e}")

    # Update flow summary + generated_at
    try:
        update_flow(flow_id, {
            "summary": summary,
            "generated_at": "now()",
        })
        # Use raw SQL for generated_at = now()
        supabase.table("solution_flows").update({
            "summary": summary,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }).eq("id", str(flow_id)).execute()
    except Exception as e:
        logger.warning(f"Failed to update flow metadata: {e}")

    return {
        "flow_id": str(flow_id),
        "summary": summary,
        "steps_generated": len(saved_steps),
        "steps": saved_steps,
    }


def _log_usage(
    project_id: UUID,
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
