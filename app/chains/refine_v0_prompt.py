"""Refine a v0 prompt based on audit gaps.

Takes the original prompt and audit results to produce an improved prompt
that addresses specific gaps identified during audit.
"""

import json
from typing import Any

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


# =============================================================================
# V2: Prompt-cached variant with version history + learnings
# =============================================================================

REFINE_V2_SYSTEM_PROMPT = """\
You are refining a v0.dev prototype prompt based on eval results. The original prompt \
produced a prototype that scored below the acceptance threshold. Your job is to rewrite \
the prompt to fix gaps while keeping everything that worked.

Rules:
1. Keep all content from the original prompt that scored well
2. Add explicit instructions for each gap identified in the eval
3. Be MORE specific about requirements that were missed
4. Add examples where the original was too vague
5. Reinforce data-feature-id requirements if feature coverage was low
6. Add HANDOFF.md template if structure score was low
7. Apply learnings from previous successful prototypes
8. ANTI-REGRESSION: Do NOT weaken areas that already score well

Output ONLY the refined prompt text (not JSON, just the prompt string).
"""


def refine_v0_prompt_v2(
    client: "Anthropic",
    system_blocks: list[dict[str, Any]],
    context_blocks: list[dict[str, Any]],
    original_prompt: str,
    deterministic_scores: dict[str, Any],
    llm_scores: dict[str, float],
    gaps: list[dict[str, Any]],
    version_history: list[dict[str, Any]],
    active_learnings: list[dict[str, Any]],
    model: str = "claude-sonnet-4-6",
) -> tuple[str, dict[str, int]]:
    """Prompt-cached refinement with full context.

    Args:
        client: Anthropic client instance
        system_blocks: Cached system blocks
        context_blocks: Cached project context blocks
        original_prompt: The current prompt text
        deterministic_scores: Dict of deterministic scores
        llm_scores: Dict of LLM-judged scores
        gaps: List of gap records from eval
        version_history: List of {version_number, score, action} dicts
        active_learnings: List of active prompt learnings
        model: Model to use

    Returns:
        (refined_prompt, usage_dict)
    """
    # Build version history context
    history_text = ""
    if version_history:
        history_lines = []
        for vh in version_history:
            history_lines.append(
                f"v{vh.get('version_number', '?')}: score={vh.get('score', 0):.2f}, "
                f"action={vh.get('action', '?')}"
            )
        history_text = f"\n## Version History\n" + "\n".join(history_lines)

    # Build learnings context
    learnings_text = ""
    if active_learnings:
        learnings_lines = [
            f"- [{l.get('category', 'general')}] {l.get('learning', '')}"
            for l in active_learnings[:10]
        ]
        learnings_text = f"\n## Active Learnings\n" + "\n".join(learnings_lines)

    # Build gaps context
    gap_lines = []
    for g in gaps:
        severity = g.get("severity", "medium")
        dim = g.get("dimension", "unknown")
        gap_lines.append(f"- [{severity.upper()}] {dim}: {g.get('description', '')}")
    gaps_text = "\n".join(gap_lines) if gap_lines else "No specific gaps identified"

    user_text = f"""## Current Prompt
{original_prompt}

## Deterministic Scores
{json.dumps(deterministic_scores, indent=2)}

## LLM Scores
{json.dumps(llm_scores, indent=2)}

## Specific Gaps
{gaps_text}
{history_text}
{learnings_text}

Please produce the refined prompt.
"""

    refine_system = [
        {"type": "text", "text": REFINE_V2_SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}
    ]

    user_content = context_blocks + [{"type": "text", "text": user_text}]

    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=refine_system,
        messages=[{"role": "user", "content": user_content}],
    )

    refined = response.content[0].text
    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "cache_read": getattr(response.usage, "cache_read_input_tokens", 0),
        "cache_create": getattr(response.usage, "cache_creation_input_tokens", 0),
    }

    logger.info(f"V2 refinement: {len(refined)} chars (original: {len(original_prompt)} chars)")
    return refined, usage
