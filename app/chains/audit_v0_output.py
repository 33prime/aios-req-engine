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
