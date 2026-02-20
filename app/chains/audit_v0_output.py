"""Audit a v0-generated prototype against the original prompt.

Compares what was requested with what was generated to produce
quality scores and identify gaps.
"""

import json
from typing import Any

from anthropic import Anthropic

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.schemas_prototypes import PromptAuditResult

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are a QA auditor for AI-generated prototypes. Compare the original v0 prompt \
(what was requested) against what was actually generated (HANDOFF.md + file tree + code scan).

Score each dimension from 0.0 to 1.0:

1. feature_coverage_score: What percentage of requested features exist in the code? \
   Check for data-feature-id attributes and component implementations.

2. structure_score: Is HANDOFF.md present and complete? Is the folder structure organized \
   by feature? Are JSDoc annotations present?

3. mock_data_score: Is mock data realistic and does it match the personas from the prompt? \
   Are there named users, scenarios, realistic values?

4. flow_score: Are the user flows from the VP steps navigable? Can you follow the journey \
   through the prototype pages?

5. feature_id_score: What percentage of interactive UI elements have data-feature-id attributes?

Also identify specific gaps (what's missing or wrong) and recommendations for improvement.

Output ONLY valid JSON:
{
  "feature_coverage_score": 0.0-1.0,
  "structure_score": 0.0-1.0,
  "mock_data_score": 0.0-1.0,
  "flow_score": 0.0-1.0,
  "feature_id_score": 0.0-1.0,
  "overall_score": 0.0-1.0,
  "gaps": [{"dimension": "...", "description": "...", "severity": "high|medium|low", "feature_ids": [...]}],
  "recommendations": ["..."]
}
"""


def audit_v0_output(
    original_prompt: str,
    handoff_content: str | None,
    file_tree: list[str],
    feature_scan: dict[str, list[str]],
    expected_features: list[dict[str, Any]],
    settings: Settings,
    model_override: str | None = None,
) -> PromptAuditResult:
    """Audit a v0 output against the original prompt.

    Args:
        original_prompt: The prompt that was sent to v0
        handoff_content: Content of HANDOFF.md (None if missing)
        file_tree: List of file paths in the repo
        feature_scan: Map of feature_id -> list of files containing it
        expected_features: AIOS features that should be in the prototype
        settings: App settings
        model_override: Optional model override

    Returns:
        PromptAuditResult with scores and gaps
    """
    model = model_override or settings.PROTOTYPE_ANALYSIS_MODEL
    logger.info(f"Auditing v0 output using {model}")

    # Build audit context
    expected_ids = {f["id"] for f in expected_features}
    found_ids = set(feature_scan.keys())
    coverage_pct = len(found_ids & expected_ids) / max(len(expected_ids), 1)

    user_message = f"""## Original Prompt (abbreviated)
{original_prompt[:3000]}...

## HANDOFF.md
{"PRESENT" if handoff_content else "MISSING"}
{(handoff_content or "")[:2000]}

## File Tree ({len(file_tree)} files)
{chr(10).join(file_tree[:100])}
{"..." if len(file_tree) > 100 else ""}

## Feature ID Scan
Features expected: {len(expected_ids)}
Features found in code: {len(found_ids)}
Pre-computed coverage: {coverage_pct:.1%}

Found feature IDs and their files:
{json.dumps(dict(list(feature_scan.items())[:30]), indent=2)}

## Expected Features
{json.dumps([{"id": f["id"], "name": f["name"]} for f in expected_features], indent=2, default=str)}
"""

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    response_text = response.content[0].text.strip()
    if response_text.startswith("```json"):
        response_text = response_text[len("```json") :]
    if response_text.startswith("```"):
        response_text = response_text[len("```") :]
    if response_text.endswith("```"):
        response_text = response_text[: -len("```")]
    parsed = json.loads(response_text.strip())
    result = PromptAuditResult(**parsed)

    logger.info(f"Audit complete: overall_score={result.overall_score:.2f}")
    return result


def should_retry(audit: PromptAuditResult) -> str:
    """Determine action based on audit score.

    Returns:
        'accept' if score >= 0.8
        'retry' if 0.5 <= score < 0.8
        'notify' if score < 0.5
    """
    if audit.overall_score >= 0.8:
        return "accept"
    elif audit.overall_score >= 0.5:
        return "retry"
    else:
        return "notify"


# =============================================================================
# Prompt-cached variant for eval pipeline
# =============================================================================

EVAL_SYSTEM_PROMPT = """\
You are a QA auditor for AI-generated prototypes. Compare what was requested \
(the original v0 prompt) against what was generated (HANDOFF.md, file tree, code scan).

You receive deterministic pre-computed scores as additional context. Use these to \
ground your assessment — focus your evaluation on the subjective quality dimensions \
that code analysis cannot capture.

Score each dimension from 0.0 to 1.0:

1. feature_coverage: Do requested features exist in the code?
2. structure: File organization, HANDOFF.md quality, JSDoc presence
3. mock_data: Realistic data matching personas?
4. flow: Are VP step flows navigable?
5. feature_id: Do interactive elements have data-feature-id attributes?

Also identify specific gaps and recommendations.

Output ONLY valid JSON:
{
  "feature_coverage": 0.0-1.0,
  "structure": 0.0-1.0,
  "mock_data": 0.0-1.0,
  "flow": 0.0-1.0,
  "feature_id": 0.0-1.0,
  "overall": 0.0-1.0,
  "gaps": [{"dimension": "...", "description": "...", "severity": "high|medium|low", "feature_ids": [], "gap_pattern": "..."}],
  "recommendations": ["..."]
}
"""


def build_eval_cached_blocks(
    features: list[dict[str, Any]],
    personas: list[dict[str, Any]],
    vp_steps: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build system and project context blocks with cache_control for eval.

    Returns:
        (system_blocks, context_blocks) — both marked for ephemeral caching.
    """
    system_blocks = [
        {"type": "text", "text": EVAL_SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}
    ]

    # Build project context
    features_text = "\n".join(
        f"- {f.get('id', 'no-id')}: {f.get('name', 'unnamed')} — {(f.get('overview') or '')[:120]}"
        for f in features
    )
    personas_text = "\n".join(
        f"- {p.get('name', 'unnamed')}: {', '.join(p.get('goals', [])[:3])}"
        for p in personas
    )
    vp_text = "\n".join(
        f"- Step {s.get('step_index', '?')}: {s.get('label', 'unnamed')} (features: {', '.join(s.get('features_used', [])[:3])})"
        for s in sorted(vp_steps, key=lambda x: x.get("step_index", 0))
    )

    project_context = f"""## Project Features ({len(features)})
{features_text}

## Personas ({len(personas)})
{personas_text}

## User Journey ({len(vp_steps)} steps)
{vp_text}
"""

    context_blocks = [
        {"type": "text", "text": project_context, "cache_control": {"type": "ephemeral"}}
    ]

    return system_blocks, context_blocks


def audit_v0_output_cached(
    client: "Anthropic",
    system_blocks: list[dict[str, Any]],
    context_blocks: list[dict[str, Any]],
    original_prompt: str,
    handoff_content: str | None,
    file_tree: list[str],
    feature_scan: dict[str, list[str]],
    deterministic_scores: dict[str, Any],
    model: str = "claude-sonnet-4-6",
) -> dict[str, Any]:
    """Prompt-cached eval audit using pre-built system/context blocks.

    Returns:
        Dict with scores, gaps, and recommendations.
    """
    # Dynamic user block (not cached — changes every eval)
    user_text = f"""## Original Prompt (abbreviated)
{original_prompt[:3000]}

## HANDOFF.md
{"PRESENT" if handoff_content else "MISSING"}
{(handoff_content or "")[:2000]}

## File Tree ({len(file_tree)} files)
{chr(10).join(file_tree[:80])}
{"..." if len(file_tree) > 80 else ""}

## Feature ID Scan
Features found in code: {len(feature_scan)}
{json.dumps(dict(list(feature_scan.items())[:20]), indent=2)}

## Pre-computed Deterministic Scores
{json.dumps(deterministic_scores, indent=2)}
"""

    user_content = context_blocks + [{"type": "text", "text": user_text}]

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system_blocks,
        messages=[{"role": "user", "content": user_content}],
    )

    response_text = response.content[0].text.strip()
    if response_text.startswith("```json"):
        response_text = response_text[len("```json"):]
    if response_text.startswith("```"):
        response_text = response_text[len("```"):]
    if response_text.endswith("```"):
        response_text = response_text[:-len("```")]

    parsed = json.loads(response_text.strip())

    logger.info(f"Cached audit complete: overall={parsed.get('overall', 0):.2f}")

    return {
        "scores": parsed,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "cache_read": getattr(response.usage, "cache_read_input_tokens", 0),
            "cache_create": getattr(response.usage, "cache_creation_input_tokens", 0),
        },
    }
