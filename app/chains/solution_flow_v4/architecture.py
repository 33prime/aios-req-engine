# ruff: noqa: E501 — prompt text blocks have natural line lengths
"""Phase 2: Flow Architecture — Sonnet plans the step structure.

Like the prototype's Coherence Agent: Sonnet THINKS about architecture,
doesn't write details. It decides:
- How many steps, in what order
- Which workflows merge into which steps
- Where AI plays a role
- How data flows across the journey
- What horizons each step belongs to

Enriched with Phase 1 insights:
- Hidden connections inform step grouping (merge related workflows)
- Tension points become explicit open_questions per step
- Missing capabilities become new steps
- Value unlock chain informs ordering and horizon assignment
- Narrative themes shape the flow thesis

Single Sonnet call, cached. ~5s, ~$0.08.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-6"

# Tool schema for flow architecture output
ARCHITECTURE_TOOL = {
    "name": "submit_flow_architecture",
    "description": "Submit the solution flow architecture: thesis, persona journeys, and step skeletons.",
    "input_schema": {
        "type": "object",
        "properties": {
            "flow_thesis": {
                "type": "string",
                "description": "2-3 sentence overview of why this flow sequence solves the core problem",
            },
            "persona_journeys": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "persona_name": {"type": "string"},
                        "journey_arc": {
                            "type": "string",
                            "description": "enters at step X, peaks at Y, exits at Z",
                        },
                    },
                    "required": ["persona_name", "journey_arc"],
                },
            },
            "step_skeletons": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "phase": {
                            "type": "string",
                            "enum": ["entry", "core_experience", "output", "admin"],
                        },
                        "goal_sentence": {
                            "type": "string",
                            "description": "One clear sentence: what outcome must be achieved",
                        },
                        "actors": {"type": "array", "items": {"type": "string"}},
                        "linked_workflow_ids": {"type": "array", "items": {"type": "string"}},
                        "linked_feature_ids": {"type": "array", "items": {"type": "string"}},
                        "linked_data_entity_ids": {"type": "array", "items": {"type": "string"}},
                        "horizon": {"type": "string", "enum": ["H1", "H2", "H3"]},
                        "data_inputs": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "What this step needs from previous steps",
                        },
                        "data_outputs": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "What this step produces for subsequent steps",
                        },
                        "ai_role": {
                            "type": "string",
                            "description": "What AI does in this step, or null if no AI",
                        },
                        "complexity": {
                            "type": "string",
                            "enum": ["simple", "moderate", "rich"],
                            "description": "How much detail this step needs",
                        },
                        "tension_notes": {
                            "type": "string",
                            "description": "Any tensions or disagreements that affect this step",
                        },
                        "insight_notes": {
                            "type": "string",
                            "description": "Intelligence insights relevant to this step",
                        },
                    },
                    "required": [
                        "title",
                        "phase",
                        "goal_sentence",
                        "actors",
                        "linked_workflow_ids",
                        "linked_feature_ids",
                        "horizon",
                        "data_inputs",
                        "data_outputs",
                        "complexity",
                    ],
                },
                "minItems": 4,
                "maxItems": 18,
            },
            "data_thread": {
                "type": "string",
                "description": "How data flows across the entire journey — the golden thread",
            },
            "unlock_sequence": {
                "type": "string",
                "description": "Which steps unlock value for which horizon",
            },
        },
        "required": ["flow_thesis", "step_skeletons", "data_thread"],
    },
}

ARCHITECTURE_SYSTEM_PROMPT = """You are a senior product architect designing the Solution Flow for a software solution. You plan the STRUCTURE — you don't write details yet.

## What a Solution Flow Is

A sequential journey through the application from the user's perspective. Each step answers:
1. What goal must be achieved here? (not "what screen" — what outcome)
2. Who does it? (which personas)
3. What data flows in and out? (inputs from prior steps, outputs for next steps)

## Phases (MUST be ordered in this sequence)

- **entry**: Onboarding, setup, initial configuration — how users enter
- **core_experience**: Primary value-delivering interactions — the magic
- **output**: Reports, exports, deliverables — tangible outcomes
- **admin**: Configuration, settings, management — supporting operations

## Your Job

Given the project BRD and intelligence insights, design step SKELETONS:
- How many steps (6-16 depending on project complexity)
- Which workflows merge into which steps
- Where data flows between steps
- Which horizons each step belongs to
- Where AI plays a role
- What complexity level each step needs (simple/moderate/rich)

## Rules

1. Each future-state workflow should map to 1-3 steps
2. MERGE related workflows when they share data entities or serve the same persona journey
3. Order steps by PERSONA JOURNEY, not just by phase
4. If intelligence insights reveal missing capabilities, create steps for them
5. If tension points exist, note them on the relevant step
6. The data_thread should explain the golden thread connecting all steps
7. Each step's goal_sentence should be actionable: "Identify which..." not "View the..."
8. Link to actual entity IDs from the project context — don't invent IDs
9. Assign horizons based on feature priority and unlock intelligence:
   - H1: must_have features, core capabilities
   - H2: should_have features, enhancement capabilities
   - H3: could_have features, future vision
"""


async def plan_architecture(
    brd_text: str,
    insights: dict[str, Any],
    confirmed_steps: list[dict],
    metadata: dict[str, Any],
    project_id: UUID,
) -> dict[str, Any]:
    """Phase 2: Sonnet plans the flow structure.

    Args:
        brd_text: Core BRD context (~6K tokens)
        insights: Phase 1 insight synthesis output
        confirmed_steps: Steps that must be preserved
        metadata: Entity counts for dynamic targeting
        project_id: For usage logging

    Returns:
        Dict with flow_thesis, persona_journeys, step_skeletons,
        data_thread, unlock_sequence.
    """
    from anthropic import (
        APIConnectionError,
        APITimeoutError,
        AsyncAnthropic,
        InternalServerError,
        RateLimitError,
    )

    from app.core.config import Settings

    settings = Settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Dynamic step targeting
    future_wf_count = metadata.get("future_workflow_count", 3)
    target_min = max(6, future_wf_count * 2)
    target_max = min(16, target_min + 4)

    system_blocks = [
        {
            "type": "text",
            "text": ARCHITECTURE_SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": f"<project_context>\n{brd_text[:20000]}\n</project_context>",
            "cache_control": {"type": "ephemeral"},
        },
    ]

    # Build user prompt with insights
    insights_section = _format_insights_for_architecture(insights)
    confirmed_section = _format_confirmed_constraints(confirmed_steps)

    user_prompt = f"""Design the Solution Flow architecture for this project.

## Complexity Signal
{metadata.get("workflow_count", 0)} workflows ({future_wf_count} future-state), {metadata.get("feature_count", 0)} features, {metadata.get("persona_count", 0)} personas.
Target: {target_min}-{target_max} steps.

{insights_section}

{confirmed_section}

## Instructions
- Plan {target_min}-{target_max} step skeletons
- Link steps to actual IDs from the project context
- Explain the data thread connecting all steps
- Note any tension points or intelligence insights on relevant steps
- Assign horizons (H1/H2/H3) based on feature priority and value sequence"""

    try:
        t0 = time.monotonic()
        async with client.messages.stream(
            model=_MODEL,
            max_tokens=8000,
            system=system_blocks,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=0,
            tools=[ARCHITECTURE_TOOL],
            tool_choice={"type": "tool", "name": "submit_flow_architecture"},
        ) as stream:
            response = await stream.get_final_message()
        elapsed_ms = int((time.monotonic() - t0) * 1000)

        for block in response.content:
            if block.type == "tool_use" and block.name == "submit_flow_architecture":
                result = block.input

                # Guard: arrays sometimes returned as JSON strings
                skeletons = result.get("step_skeletons", [])
                if isinstance(skeletons, str):
                    try:
                        skeletons = json.loads(skeletons)
                        result["step_skeletons"] = skeletons
                    except (json.JSONDecodeError, TypeError):
                        skeletons = []

                skeletons = [s for s in skeletons if isinstance(s, dict)]
                result["step_skeletons"] = skeletons

                cache_read = getattr(response.usage, "cache_read_input_tokens", 0) or 0
                logger.info(
                    f"Phase 2 architecture in {elapsed_ms}ms: "
                    f"{len(skeletons)} steps planned "
                    f"(in={response.usage.input_tokens}, out={response.usage.output_tokens}, "
                    f"cache_read={cache_read})"
                )

                try:
                    _log_usage(
                        project_id, "solution_flow_architecture", _MODEL, response, elapsed_ms
                    )
                except Exception:
                    pass

                return result

        logger.warning("No tool_use block in architecture response")
        return {"step_skeletons": [], "flow_thesis": "", "data_thread": ""}

    except (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError) as e:
        logger.error(f"Architecture planning failed: {e}")
        return {"step_skeletons": [], "flow_thesis": "", "data_thread": ""}


def _format_insights_for_architecture(insights: dict[str, Any]) -> str:
    """Format Phase 1 insights as guidance for the architect."""
    if not insights or not any(
        insights.get(k)
        for k in (
            "hidden_connections",
            "tension_points",
            "missing_capabilities",
            "narrative_themes",
        )
    ):
        return ""

    parts = ["## Intelligence Insights (from Phase 1 analysis)"]

    connections = insights.get("hidden_connections", [])
    if connections:
        parts.append("\nHidden connections (consider merging related workflows):")
        for c in connections[:5]:
            parts.append(f"  - {c}")

    tensions = insights.get("tension_points", [])
    if tensions:
        parts.append("\nTension points (surface as open_questions on relevant steps):")
        for t in tensions[:5]:
            if isinstance(t, dict):
                parts.append(f"  - {t.get('description', str(t))}")
            else:
                parts.append(f"  - {t}")

    missing = insights.get("missing_capabilities", [])
    if missing:
        parts.append("\nMissing capabilities (create steps for these):")
        for m in missing[:5]:
            parts.append(f"  - {m}")

    blind_spots = insights.get("persona_blind_spots", [])
    if blind_spots:
        parts.append("\nPersona blind spots:")
        for b in blind_spots[:3]:
            parts.append(f"  - {b}")

    themes = insights.get("narrative_themes", [])
    if themes:
        parts.append("\nNarrative themes (shape the flow thesis):")
        for t in themes[:3]:
            parts.append(f"  - {t}")

    recommendations = insights.get("flow_recommendations", [])
    if recommendations:
        parts.append("\nFlow recommendations:")
        for r in recommendations[:3]:
            parts.append(f"  - {r}")

    chain = insights.get("value_unlock_chain", "")
    if chain:
        parts.append(f"\nValue unlock chain: {chain[:200]}")

    return "\n".join(parts)


def _format_confirmed_constraints(confirmed_steps: list[dict]) -> str:
    """Format confirmed steps as hard constraints."""
    if not confirmed_steps:
        return ""

    parts = ["## CONFIRMED STEPS (preserve exactly — do not include in your output)"]
    for step in confirmed_steps:
        parts.append(
            f'- [{step.get("phase")}] "{step.get("title")}" '
            f"(index:{step.get('step_index')}) — {step.get('goal', '')[:80]}"
        )
    parts.append("\nDesign new steps AROUND these confirmed ones.")
    return "\n".join(parts)


def _log_usage(project_id: UUID, action: str, model: str, response: Any, elapsed_ms: int) -> None:
    """Log LLM usage."""
    from app.db.supabase_client import get_supabase

    try:
        get_supabase().table("usage_events").insert(
            {
                "project_id": str(project_id),
                "action": action,
                "model": model,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "cache_read_tokens": getattr(response.usage, "cache_read_input_tokens", 0) or 0,
                "cache_create_tokens": getattr(response.usage, "cache_creation_input_tokens", 0)
                or 0,
                "latency_ms": elapsed_ms,
            }
        ).execute()
    except Exception:
        pass
