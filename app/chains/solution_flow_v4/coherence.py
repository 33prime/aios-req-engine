# ruff: noqa: E501 — prompt text blocks have natural line lengths
"""Phase 4: Coherence QA + Insight Weave — Cross-step validation.

Like the prototype's Finisher: Sonnet reviews the complete flow for:
1. Data continuity — step 3 uses what step 2 produces?
2. Mock data consistency — same persona names across steps
3. Coverage gaps — any future-state workflow unmapped?
4. Duplicate coverage — two steps solving same problem?
5. Confidence calibration — "known" fields actually in BRD?
6. Persona journey completeness — each persona has entry→exit?
7. Horizon coherence — H2/H3 steps don't depend on unbuilt H2/H3
8. Insight weaving — Phase 1 insights surfaced in relevant steps

Single Sonnet call. ~4s, ~$0.06.
Can be SKIPPED if all steps pass deterministic validation.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-6"

QA_TOOL = {
    "name": "submit_qa_results",
    "description": "Submit coherence QA results: patches, quality score, and issues.",
    "input_schema": {
        "type": "object",
        "properties": {
            "quality_score": {
                "type": "number",
                "description": "Overall quality score 0-100",
            },
            "patches": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "step_index": {"type": "integer"},
                        "field": {
                            "type": "string",
                            "description": "Field to patch: mock_data_narrative, success_criteria, open_questions, etc.",
                        },
                        "action": {"type": "string", "enum": ["replace", "append", "remove"]},
                        "value": {"description": "New value for the field"},
                    },
                    "required": ["step_index", "field", "action", "value"],
                },
                "description": "Field-level corrections to apply",
            },
            "issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "string", "enum": ["critical", "warning", "info"]},
                        "step_index": {
                            "type": "integer",
                            "description": "Which step, or -1 for flow-level",
                        },
                        "issue": {"type": "string"},
                    },
                    "required": ["severity", "issue"],
                },
            },
            "summary_patch": {
                "type": "string",
                "description": "Improved flow summary incorporating insights, or empty string to keep current",
            },
        },
        "required": ["quality_score", "patches", "issues"],
    },
}

QA_SYSTEM_PROMPT = """You are a quality analyst reviewing a complete Solution Flow for coherence, data continuity, and coverage.

## Your Checks

1. **Data continuity**: Does step N+1's input match step N's output? Flag breaks.
2. **Mock data consistency**: Same persona names and data values across steps? Flag mismatches.
3. **Coverage**: Every future-state workflow mapped to at least one step? Flag orphans.
4. **No duplicates**: Two steps solving the same problem? Flag.
5. **Confidence calibration**: Fields marked "known" actually in BRD data? Downgrade if not.
6. **Persona journeys**: Each persona enters and exits the flow? Flag missing arcs.
7. **Horizon coherence**: H2/H3 steps don't require capabilities from other H2/H3 steps?
8. **Insight integration**: Are key tensions surfaced as open_questions? Are narrative themes reflected in the flow thesis?

## Patching Rules

- Only patch what's clearly wrong — don't rewrite working content
- Patches must target a specific step_index and field
- Use "append" to add missing open_questions
- Use "replace" for wrong mock values or missing data flow
- Use "remove" only for duplicate or irrelevant content
- summary_patch: Improve the flow summary if it doesn't reflect intelligence insights

## Quality Score Guide
- 90-100: Exceptional — data flows, coverage complete, insights woven in
- 80-89: Good — minor data flow gaps, mostly coherent
- 70-79: Acceptable — some coverage gaps or data continuity issues
- 60-69: Needs work — significant gaps, inconsistencies
- <60: Poor — missing data flows, duplicate coverage, broken journeys
"""


async def run_coherence_qa(
    steps: list[dict[str, Any]],
    flow_thesis: str,
    insights: dict[str, Any],
    workflow_names: list[str],
    persona_names: list[str],
    project_id: UUID,
) -> dict[str, Any]:
    """Phase 4: Sonnet QA pass over the complete flow.

    Returns dict with quality_score, patches, issues, summary_patch.
    """
    from anthropic import (
        APIConnectionError,
        APITimeoutError,
        AsyncAnthropic,
        InternalServerError,
        RateLimitError,
    )

    from app.core.config import Settings

    # Run deterministic checks first
    det_issues = _deterministic_checks(steps, workflow_names, persona_names)

    # If deterministic checks find nothing, skip LLM QA for cost savings
    if not det_issues:
        logger.info("Phase 4: Deterministic checks clean — skipping LLM QA")
        return {
            "quality_score": 85,
            "patches": [],
            "issues": [],
            "summary_patch": "",
        }

    settings = Settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Compact flow representation for QA
    flow_text = _format_flow_for_qa(steps, flow_thesis, insights)

    system_blocks = [
        {
            "type": "text",
            "text": QA_SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        },
    ]

    user_prompt = f"""Review this complete Solution Flow for coherence.

<flow>
{flow_text[:16000]}
</flow>

<reference>
Future-state workflows: {", ".join(workflow_names[:10])}
Personas: {", ".join(persona_names[:8])}
</reference>

<deterministic_issues>
{json.dumps(det_issues, indent=2)[:2000]}
</deterministic_issues>

Identify issues, suggest patches, and score the quality."""

    try:
        t0 = time.monotonic()
        response = await client.messages.create(
            model=_MODEL,
            max_tokens=6000,
            system=system_blocks,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=0,
            tools=[QA_TOOL],
            tool_choice={"type": "tool", "name": "submit_qa_results"},
        )
        elapsed_ms = int((time.monotonic() - t0) * 1000)

        for block in response.content:
            if block.type == "tool_use" and block.name == "submit_qa_results":
                result = block.input

                patches = result.get("patches", [])
                issues = result.get("issues", [])
                score = result.get("quality_score", 0)

                logger.info(
                    f"Phase 4 QA in {elapsed_ms}ms: score={score}, "
                    f"{len(patches)} patches, {len(issues)} issues"
                )

                try:
                    _log_usage(project_id, "solution_flow_qa", _MODEL, response, elapsed_ms)
                except Exception:
                    pass

                return result

        logger.warning("No tool_use in QA response")
        return {"quality_score": 70, "patches": [], "issues": det_issues, "summary_patch": ""}

    except (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError) as e:
        logger.warning(f"QA failed (non-fatal): {e}")
        return {"quality_score": 70, "patches": [], "issues": det_issues, "summary_patch": ""}


def apply_qa_patches(
    steps: list[dict[str, Any]],
    qa_result: dict[str, Any],
) -> list[dict[str, Any]]:
    """Apply QA patches to step list."""
    patches = qa_result.get("patches", [])
    if not patches:
        return steps

    applied = 0
    for patch in patches:
        idx = patch.get("step_index")
        field = patch.get("field")
        action = patch.get("action", "replace")
        value = patch.get("value")

        if idx is None or field is None or idx < 0 or idx >= len(steps):
            continue

        step = steps[idx]

        if action == "replace":
            step[field] = value
            applied += 1
        elif action == "append":
            existing = step.get(field, [])
            if isinstance(existing, list):
                if isinstance(value, list):
                    existing.extend(value)
                else:
                    existing.append(value)
                step[field] = existing
                applied += 1
        elif action == "remove":
            if field in step:
                del step[field]
                applied += 1

    if applied:
        logger.info(f"Applied {applied}/{len(patches)} QA patches")

    return steps


# =============================================================================
# Deterministic Checks (free, fast, always run)
# =============================================================================


def _deterministic_checks(
    steps: list[dict[str, Any]],
    workflow_names: list[str],
    persona_names: list[str],
) -> list[dict[str, Any]]:
    """Run fast deterministic checks on the flow."""
    issues: list[dict[str, Any]] = []

    # 1. Phase ordering
    phase_order = {"entry": 0, "core_experience": 1, "output": 2, "admin": 3}
    last_phase_idx = -1
    for i, step in enumerate(steps):
        phase = step.get("phase", "core_experience")
        phase_idx = phase_order.get(phase, 1)
        if phase_idx < last_phase_idx:
            issues.append(
                {
                    "severity": "warning",
                    "step_index": i,
                    "issue": f"Phase ordering: '{phase}' after '{steps[i - 1].get('phase')}' — should be entry→core→output→admin",
                }
            )
        last_phase_idx = phase_idx

    # 2. Data flow gaps
    for i in range(1, len(steps)):
        prev_outputs = set(steps[i - 1].get("data_outputs", []))
        curr_inputs = set(steps[i].get("data_inputs", []))
        if curr_inputs and not curr_inputs & prev_outputs:
            issues.append(
                {
                    "severity": "info",
                    "step_index": i,
                    "issue": f"Possible data gap: step expects {list(curr_inputs)[:3]} but prev step outputs {list(prev_outputs)[:3]}",
                }
            )

    # 3. Empty steps
    for i, step in enumerate(steps):
        if not step.get("information_fields"):
            issues.append(
                {
                    "severity": "warning",
                    "step_index": i,
                    "issue": "Step has no information_fields",
                }
            )
        if not step.get("mock_data_narrative"):
            issues.append(
                {
                    "severity": "warning",
                    "step_index": i,
                    "issue": "Step has no mock_data_narrative",
                }
            )

    # 4. Workflow coverage
    linked_wf_ids = set()
    for step in steps:
        linked_wf_ids.update(step.get("linked_workflow_ids", []))

    # We can't check exhaustive coverage without IDs, but check if any step has no workflow link
    orphan_steps = [i for i, s in enumerate(steps) if not s.get("linked_workflow_ids")]
    if len(orphan_steps) > len(steps) // 3:
        issues.append(
            {
                "severity": "warning",
                "step_index": -1,
                "issue": f"{len(orphan_steps)}/{len(steps)} steps have no linked workflows",
            }
        )

    return issues


def _format_flow_for_qa(
    steps: list[dict[str, Any]],
    flow_thesis: str,
    insights: dict[str, Any],
) -> str:
    """Compact flow representation for QA review."""
    parts = [f"Flow thesis: {flow_thesis}"]

    for i, step in enumerate(steps):
        parts.append(f"\n--- Step {i}: {step.get('title', '?')} [{step.get('phase', '?')}] ---")
        parts.append(f"Goal: {step.get('goal', step.get('goal_sentence', ''))[:150]}")
        parts.append(f"Actors: {', '.join(step.get('actors', []))}")
        parts.append(f"Data in: {', '.join(step.get('data_inputs', []))}")
        parts.append(f"Data out: {', '.join(step.get('data_outputs', []))}")

        fields = step.get("information_fields", [])
        if fields:
            parts.append(
                f"Fields ({len(fields)}): {', '.join(f.get('name', '?') for f in fields[:6])}"
            )

        narrative = step.get("mock_data_narrative", "")
        if narrative:
            parts.append(f"Narrative: {narrative[:200]}...")

        questions = step.get("open_questions", [])
        if questions:
            parts.append(f"Open questions: {len(questions)}")

    # Intelligence context for insight weaving check
    if insights:
        tensions = insights.get("tension_points", [])
        if tensions:
            parts.append(f"\n--- Unaddressed tensions: {len(tensions)} ---")
            for t in tensions[:3]:
                desc = t.get("description", str(t)) if isinstance(t, dict) else str(t)
                parts.append(f"  - {desc[:100]}")

        missing = insights.get("missing_capabilities", [])
        if missing:
            parts.append(f"\n--- Missing capabilities: {len(missing)} ---")
            for m in missing[:3]:
                parts.append(f"  - {m[:100]}")

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
