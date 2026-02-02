"""Refine a v0 prompt based on audit gaps.

Takes the original prompt and audit results to produce an improved prompt
that addresses specific gaps identified during audit.
"""

import json

from anthropic import Anthropic

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.schemas_prototypes import PromptAuditResult

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are refining a v0.dev prototype prompt based on audit feedback. The original prompt \
produced a prototype that had specific gaps. Your job is to rewrite the prompt to fix \
those gaps while keeping everything that worked.

Rules:
1. Keep all content from the original prompt that scored well
2. Add explicit instructions for each gap identified
3. Be MORE specific about requirements that were missed
4. Add examples where the original was too vague
5. Reinforce data-feature-id requirements if feature_id_score was low
6. Add HANDOFF.md template if structure_score was low

Output ONLY the refined prompt text (not JSON, just the prompt string).
"""


def refine_v0_prompt(
    original_prompt: str,
    audit: PromptAuditResult,
    settings: Settings,
    model_override: str | None = None,
) -> str:
    """Generate a refined v0 prompt from audit gaps.

    Args:
        original_prompt: The original v0 prompt
        audit: Audit results with scores and gaps
        settings: App settings
        model_override: Optional model override

    Returns:
        Refined prompt string
    """
    model = model_override or settings.PROTOTYPE_ANALYSIS_MODEL
    logger.info(f"Refining v0 prompt using {model}, original score: {audit.overall_score:.2f}")

    user_message = f"""## Original Prompt
{original_prompt}

## Audit Results
Overall Score: {audit.overall_score:.2f}
Feature Coverage: {audit.feature_coverage_score:.2f}
Structure: {audit.structure_score:.2f}
Mock Data: {audit.mock_data_score:.2f}
Flow: {audit.flow_score:.2f}
Feature IDs: {audit.feature_id_score:.2f}

## Specific Gaps
{json.dumps([g.model_dump() for g in audit.gaps], indent=2)}

## Recommendations
{json.dumps(audit.recommendations, indent=2)}

Please produce the refined prompt.
"""

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    refined = response.content[0].text
    logger.info(f"Refined prompt: {len(refined)} chars (original: {len(original_prompt)} chars)")
    return refined
