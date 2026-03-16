# ruff: noqa: E501 — prompt text blocks have natural line lengths
"""Phase 3: Parallel Haiku Step Builders — One focused call per step.

Like the prototype's Haiku builders: each step gets its own call with ONLY
the context it needs (its skeleton, linked entities, neighboring step data).

Benefits over v3's single-call approach:
- Each step gets focused context (~1-2K tokens vs 30K)
- Haiku is 10x cheaper than Sonnet for bounded tasks
- Parallel execution: 8-12 steps in ~2-3s wall time
- Better mock data quality — persona-specific, entity-grounded

System prompt is cached across all parallel calls.
~$0.006/step, ~$0.06 total.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any
from uuid import UUID

from app.chains.solution_flow_v4.intelligence import FlowIntelligenceContext

logger = logging.getLogger(__name__)

_MODEL = "claude-haiku-4-5-20251001"

# Tool schema for per-step detail
STEP_DETAIL_TOOL = {
    "name": "submit_step_detail",
    "description": "Submit detailed information for one solution flow step.",
    "input_schema": {
        "type": "object",
        "properties": {
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
            "mock_data_narrative": {
                "type": "string",
                "description": "A story: 'Sarah opens her screen and sees...' using specific names and data from the project",
            },
            "implied_pattern": {
                "type": "string",
                "description": "Suggested UI approach: form, table, dashboard, card list, wizard, etc.",
            },
            "success_criteria": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2-4 measurable criteria defining success for this step",
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
            },
            "goals_addressed": {
                "type": "array",
                "items": {"type": "string"},
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
            "ai_config": {
                "type": "object",
                "properties": {
                    "role": {"type": "string", "description": "What the AI does — the intelligence layer for this step"},
                    "agent_name": {"type": "string", "description": "Short memorable name, e.g. 'Market Sizer', 'Revenue Forecaster', 'Pipeline Watcher'"},
                    "agent_type": {
                        "type": "string",
                        "enum": ["classifier", "matcher", "predictor", "watcher", "generator", "processor"],
                        "description": "classifier=sorts/labels, matcher=connects/recommends, predictor=forecasts, watcher=monitors/alerts, generator=creates/compiles, processor=transforms/validates",
                    },
                    "behaviors": {"type": "array", "items": {"type": "string"}, "description": "3-5 specific AI behaviors"},
                    "guardrails": {"type": "array", "items": {"type": "string"}},
                    "confidence_display": {
                        "type": "string",
                        "enum": ["hidden", "subtle", "prominent"],
                    },
                    "fallback": {"type": "string"},
                    "data_requirements": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "source": {"type": "string"},
                                "volume": {"type": "string"},
                                "quality_needed": {"type": "string", "enum": ["minimal", "good", "high", "critical"]},
                            },
                            "required": ["source"],
                        },
                    },
                    "automation_estimate": {"type": "integer", "description": "% automated 0-100. Data processing 80-95%, creative/judgment 30-60%"},
                    "learning_trajectory": {"type": "string", "description": "How the agent improves over time"},
                    "human_touchpoints": {"type": "array", "items": {"type": "string"}, "description": "Moments requiring human judgment"},
                },
                "required": ["role", "agent_name", "agent_type", "behaviors", "automation_estimate"],
            },
        },
        "required": [
            "information_fields",
            "mock_data_narrative",
            "implied_pattern",
            "success_criteria",
            "ai_config",
        ],
    },
}

BUILDER_SYSTEM_PROMPT = """You are a product detail builder creating the DETAILED content for one solution flow step. You receive the step's skeleton and its focused context — only the entities linked to THIS step.

## Your Job
Fill in the details for this single step:
1. **information_fields**: What data is captured, displayed, or computed. Use REALISTIC mock values with specific names, numbers, dates from the context.
2. **mock_data_narrative**: A story using a specific persona: "Sarah opens her inventory screen and sees 247 items awaiting classification..."
3. **implied_pattern**: What UI pattern fits (form, table, dashboard, wizard, card list, split-pane, etc.)
4. **success_criteria**: 2-4 measurable, user-observable criteria
5. **pain_points_addressed**: Which pain points this step alleviates
6. **goals_addressed**: Which goals this step advances
7. **open_questions**: What needs client clarification
8. **ai_config** (REQUIRED): EVERY step has an AI intelligence layer. Name the agent distinctly (e.g. 'Onboarding Guide', 'Market Sizer', 'Pipeline Watcher'). Classify its type (classifier/matcher/predictor/watcher/generator/processor). Set automation_estimate: data processing 80-95%, creative/judgment 30-60%. Even simple steps have smart defaults, validation, or pattern recognition.

## Rules
- Confidence levels: "known" = in BRD data, "inferred" = logically derived, "guess" = reasonable assumption, "unknown" = needs client input
- Use SPECIFIC data from the context: real persona names, real entity fields, real workflow step labels
- The mock_data_narrative should be 3-5 sentences, reading like a user story
- If there are tension points noted, convert them to open_questions
- If insight notes reference missing or uncertain data, set confidence to "guess" or "unknown"
"""


async def build_step_details(
    skeletons: list[dict[str, Any]],
    ctx: FlowIntelligenceContext,
    insights: dict[str, Any],
    project_id: UUID,
) -> list[dict[str, Any]]:
    """Phase 3: Parallel Haiku calls, one per step skeleton.

    Each step gets focused context: its skeleton + only linked entities.

    Returns list of step detail dicts in same order as skeletons.
    """
    from anthropic import AsyncAnthropic

    from app.core.config import Settings

    settings = Settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Build entity lookup maps
    persona_map = {p["id"]: p for p in ctx.personas}
    persona_by_name = {p.get("name", "").lower(): p for p in ctx.personas}
    workflow_map = {w["id"]: w for w in ctx.workflows}
    feature_map = {f["id"]: f for f in ctx.features}
    data_entity_map = {d["id"]: d for d in ctx.data_entities}
    confidence_map = insights.get("confidence_map", {})

    # Shared system prompt (cached across all parallel calls)
    system_blocks = [
        {
            "type": "text",
            "text": BUILDER_SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        },
    ]

    async def _build_one(idx: int, skeleton: dict) -> dict[str, Any]:
        """Build details for one step."""
        # Assemble focused context for this step
        step_context = _assemble_step_context(
            skeleton,
            idx,
            skeletons,
            persona_map,
            persona_by_name,
            workflow_map,
            feature_map,
            data_entity_map,
            ctx,
            confidence_map,
        )

        user_prompt = f"""Build detailed content for this solution flow step.

<step_skeleton>
Title: {skeleton.get("title", "")}
Phase: {skeleton.get("phase", "")}
Goal: {skeleton.get("goal_sentence", "")}
Actors: {", ".join(skeleton.get("actors", []))}
Data inputs: {", ".join(skeleton.get("data_inputs", []))}
Data outputs: {", ".join(skeleton.get("data_outputs", []))}
AI role: {skeleton.get("ai_role", "none")}
Complexity: {skeleton.get("complexity", "moderate")}
Tension notes: {skeleton.get("tension_notes", "none")}
Insight notes: {skeleton.get("insight_notes", "none")}
</step_skeleton>

<step_context>
{step_context}
</step_context>

Generate the detailed information_fields, mock_data_narrative, implied_pattern, success_criteria, ai_config (with agent_name, agent_type, automation_estimate), and open_questions for this step. The AI role from the skeleton should inform your ai_config — give the agent a memorable name and classify its type."""

        try:
            response = await client.messages.create(
                model=_MODEL,
                max_tokens=3000,
                system=system_blocks,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=0,
                tools=[STEP_DETAIL_TOOL],
                tool_choice={"type": "tool", "name": "submit_step_detail"},
            )

            for block in response.content:
                if block.type == "tool_use" and block.name == "submit_step_detail":
                    detail = block.input

                    # Merge skeleton with detail
                    merged = {**skeleton, **detail}
                    # Rename goal_sentence → goal
                    if "goal_sentence" in merged and "goal" not in merged:
                        merged["goal"] = merged.pop("goal_sentence")

                    return merged

            logger.warning(f"No tool_use for step {idx} '{skeleton.get('title')}'")
            return _skeleton_to_fallback(skeleton)

        except Exception as e:
            logger.warning(f"Builder failed for step {idx} '{skeleton.get('title')}': {e}")
            return _skeleton_to_fallback(skeleton)

    # Run all builders in parallel
    t0 = time.monotonic()
    results = await asyncio.gather(
        *[_build_one(i, skel) for i, skel in enumerate(skeletons)],
        return_exceptions=True,
    )
    elapsed = time.monotonic() - t0

    # Process results
    details: list[dict[str, Any]] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning(f"Builder {i} raised: {result}")
            details.append(_skeleton_to_fallback(skeletons[i]))
        else:
            details.append(result)

    logger.info(
        f"Phase 3 builders: {len(details)} steps built in {elapsed:.1f}s "
        f"({len([d for d in details if d.get('information_fields')])} with full detail)"
    )

    try:
        _log_usage_batch(project_id, "solution_flow_builders", _MODEL, len(skeletons), elapsed)
    except Exception:
        pass

    return details


def _assemble_step_context(
    skeleton: dict,
    step_idx: int,
    all_skeletons: list[dict],
    persona_map: dict,
    persona_by_name: dict,
    workflow_map: dict,
    feature_map: dict,
    data_entity_map: dict,
    ctx: FlowIntelligenceContext,
    confidence_map: dict,
) -> str:
    """Build focused context for one step — only entities linked to THIS step."""
    parts: list[str] = []

    # Linked personas (from actors)
    actors = skeleton.get("actors", [])
    relevant_personas = []
    for actor in actors:
        # Try name match
        p = persona_by_name.get(actor.lower())
        if p:
            relevant_personas.append(p)

    if relevant_personas:
        parts.append("Personas:")
        for p in relevant_personas:
            parts.append(f"  {p.get('name', '?')} — {p.get('role', '?')}")
            goals = p.get("goals") or []
            if isinstance(goals, list) and goals:
                parts.append(f"  Goals: {', '.join(str(g) for g in goals[:3])}")
            pains = p.get("pain_points") or []
            if isinstance(pains, list) and pains:
                parts.append(f"  Pains: {', '.join(str(pp) for pp in pains[:3])}")

    # Linked workflows
    wf_ids = skeleton.get("linked_workflow_ids", [])
    for wf_id in wf_ids:
        wf = workflow_map.get(wf_id)
        if wf:
            parts.append(f"\nWorkflow: {wf.get('name', '?')}")
            if wf.get("description"):
                parts.append(f"  {wf['description'][:200]}")
            for step in wf.get("steps", [])[:8]:
                parts.append(f"  - {step.get('label', '?')}: {step.get('description', '')[:80]}")

    # Linked features
    feat_ids = skeleton.get("linked_feature_ids", [])
    if feat_ids:
        parts.append("\nFeatures:")
        for fid in feat_ids:
            f = feature_map.get(fid)
            if f:
                conf = confidence_map.get(fid, {})
                conf_label = f" [{conf.get('level', '')}]" if conf else ""
                parts.append(f"  - {f.get('name', '?')}{conf_label}")
                if f.get("overview"):
                    parts.append(f"    {f['overview'][:120]}")

    # Linked data entities
    de_ids = skeleton.get("linked_data_entity_ids", [])
    if de_ids:
        parts.append("\nData entities:")
        for de_id in de_ids:
            de = data_entity_map.get(de_id)
            if de:
                parts.append(f"  - {de.get('name', '?')}")
                fields = de.get("fields") or []
                if fields and isinstance(fields, list):
                    field_names = [
                        fi.get("name", "?") if isinstance(fi, dict) else str(fi)
                        for fi in fields[:6]
                    ]
                    parts.append(f"    Fields: {', '.join(field_names)}")

    # Neighboring step data (for data flow continuity)
    if step_idx > 0:
        prev = all_skeletons[step_idx - 1]
        parts.append(f"\nPrevious step outputs: {', '.join(prev.get('data_outputs', ['none']))}")
    if step_idx < len(all_skeletons) - 1:
        nxt = all_skeletons[step_idx + 1]
        parts.append(f"Next step expects: {', '.join(nxt.get('data_inputs', ['none']))}")

    # Relevant drivers
    if ctx.drivers:
        relevant_pains = [d for d in ctx.pain_points if d.get("id")][:3]
        relevant_goals = [d for d in ctx.goals if d.get("id")][:3]
        if relevant_pains or relevant_goals:
            parts.append("\nBusiness drivers:")
            for d in relevant_pains[:2]:
                parts.append(f"  [pain] {d.get('description', d.get('title', '?'))[:100]}")
            for d in relevant_goals[:2]:
                parts.append(f"  [goal] {d.get('description', d.get('title', '?'))[:100]}")

    return "\n".join(parts) if parts else "No specific context for this step."


def _skeleton_to_fallback(skeleton: dict) -> dict[str, Any]:
    """Convert skeleton to a minimal step when builder fails."""
    return {
        **skeleton,
        "goal": skeleton.get("goal_sentence", skeleton.get("goal", "")),
        "information_fields": [],
        "mock_data_narrative": f"The {', '.join(skeleton.get('actors', ['user']))} completes {skeleton.get('title', 'this step')}.",
        "implied_pattern": "form",
        "success_criteria": [f"{skeleton.get('title', 'Step')} completes successfully"],
        "open_questions": [],
    }


def _log_usage_batch(project_id: UUID, action: str, model: str, count: int, elapsed: float) -> None:
    """Log batch usage."""
    from app.db.supabase_client import get_supabase

    try:
        get_supabase().table("usage_events").insert(
            {
                "project_id": str(project_id),
                "action": action,
                "model": model,
                "input_tokens": 0,  # Batch — individual tokens not tracked
                "output_tokens": 0,
                "latency_ms": int(elapsed * 1000),
                "metadata": json.dumps({"step_count": count}),
            }
        ).execute()
    except Exception:
        pass
