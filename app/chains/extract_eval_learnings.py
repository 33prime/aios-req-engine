"""Extract generalizable learnings from successful eval runs.

Compares the original prompt vs refined prompt to identify
patterns that led to improvement. Uses Haiku for cost efficiency.
"""

import json
from typing import Any

from anthropic import Anthropic

from app.core.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are analyzing a prototype prompt refinement cycle to extract generalizable learnings.

Compare the original prompt (which scored lower) with the version that passed eval. \
Identify patterns that are NOT project-specific — they should help future prototypes \
across different projects.

For each learning, provide:
- category: feature_coverage | structure | mock_data | flow | feature_id | general
- learning: A concise, actionable instruction (1-2 sentences)
- dimension: Which eval dimension this learning addresses
- gap_pattern: A normalized pattern name (e.g., "missing_handoff_template", "vague_feature_ids")

Output ONLY valid JSON:
{
  "learnings": [
    {
      "category": "...",
      "learning": "...",
      "dimension": "...",
      "gap_pattern": "..."
    }
  ]
}

Rules:
- Extract 2-5 learnings maximum
- Each must be generalizable (not project-specific)
- Focus on WHAT changed between versions that led to improvement
- Prefer specific, actionable instructions over vague advice
"""


def extract_eval_learnings(
    client: Anthropic,
    original_prompt: str,
    refined_prompt: str | None,
    gaps: list[dict[str, Any]],
    deterministic_scores: dict[str, Any],
    llm_scores: dict[str, float],
    model: str = "claude-haiku-4-5-20251001",
) -> list[dict[str, Any]]:
    """Extract generalizable learnings from an eval cycle.

    Args:
        client: Anthropic client instance
        original_prompt: The initial prompt text
        refined_prompt: The refined prompt that scored better (None if v1 accepted)
        gaps: Gap records from eval runs
        deterministic_scores: Final deterministic scores
        llm_scores: Final LLM-judged scores
        model: Model to use (Haiku for cost efficiency)

    Returns:
        List of learning dicts ready for DB insertion
    """
    if not refined_prompt:
        # V1 was accepted — extract learnings from what worked well
        user_text = f"""## Prompt That Passed Eval (v1 — accepted first try)
{original_prompt[:4000]}

## Final Scores
Deterministic: {json.dumps(deterministic_scores, indent=2)}
LLM: {json.dumps(llm_scores, indent=2)}

This prompt was accepted on the first try. What patterns made it successful?
Extract learnings that could help future prompts achieve similar first-pass acceptance.
"""
    else:
        # Compare original vs refined
        gap_text = "\n".join(
            f"- [{g.get('severity', 'medium')}] {g.get('dimension', '?')}: {g.get('description', '')}"
            for g in gaps[:10]
        )

        user_text = f"""## Original Prompt (scored lower)
{original_prompt[:3000]}

## Refined Prompt (passed eval)
{refined_prompt[:3000]}

## Gaps That Were Fixed
{gap_text}

## Final Scores
Deterministic: {json.dumps(deterministic_scores, indent=2)}
LLM: {json.dumps(llm_scores, indent=2)}

What changes between original and refined prompt led to the improvement?
"""

    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_text}],
    )

    response_text = response.content[0].text.strip()
    if response_text.startswith("```json"):
        response_text = response_text[len("```json"):]
    if response_text.startswith("```"):
        response_text = response_text[len("```"):]
    if response_text.endswith("```"):
        response_text = response_text[:-len("```")]

    parsed = json.loads(response_text.strip())
    learnings = parsed.get("learnings", [])

    logger.info(f"Extracted {len(learnings)} learnings from eval cycle")
    return learnings
