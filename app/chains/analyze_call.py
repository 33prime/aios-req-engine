"""Call transcript analysis chain.

Claude analysis with dimension packs — extracts engagement, feature reactions,
market signals, content nuggets, and competitive intelligence from call transcripts.
"""

import json
from typing import Any

from anthropic import Anthropic

from app.core.config import Settings, get_settings
from app.core.llm_usage import log_llm_usage
from app.core.logging import get_logger
from app.core.schemas_call_intelligence import AnalysisResult

logger = get_logger(__name__)

# ============================================================================
# Dimension packs
# ============================================================================

DIMENSION_PACKS: dict[str, list[str]] = {
    "core": [
        "engagement_score",
        "talk_ratio",
        "engagement_timeline",
        "executive_summary",
    ],
    "research": [
        "feature_insights",
        "call_signals",
        "content_nuggets",
        "competitive_mentions",
    ],
    "consultant": [
        "question_quality",
        "active_listening",
        "discovery_depth",
        "objection_handling",
        "next_steps_clarity",
        "consultant_talk_ratio",
        "consultant_summary",
    ],
}

SYSTEM_PROMPT = """\
You are a senior requirements analyst reviewing a discovery call transcript.

This is DISCOVERY and REQUIREMENTS VALIDATION — NOT sales coaching or QA.
Focus on: client needs, feature reactions, reusable content, competitive landscape.

Analyze the transcript and return a JSON object with ONLY the requested dimensions.

## Dimension definitions

### Core dimensions
- **engagement_score** (float 0-1): Overall client engagement level across the call.
- **talk_ratio** (object): Keys are speaker labels, values are float 0-1 share of talk time. Must sum to ~1.0.
- **engagement_timeline** (array of objects): Each entry has "timestamp_seconds" (int), "topic" (string), "engagement_level" (float 0-1). 3-8 entries capturing key moments.
- **executive_summary** (string): 2-4 sentence summary of the call focused on requirements insights.

### Research dimensions
- **feature_insights** (array of objects): Each has "feature_name" (string), "reaction" (one of: "excited", "interested", "neutral", "confused", "resistant"), "quote" (string, direct quote), "context" (string), "timestamp_seconds" (int or null), "is_aha_moment" (boolean).
- **call_signals** (array of objects): Each has "signal_type" (one of: "pain_point", "goal", "budget_indicator", "timeline", "decision_criteria", "risk_factor"), "title" (string), "description" (string), "intensity" (float 0-1), "quote" (string).
- **content_nuggets** (array of objects): Each has "nugget_type" (one of: "testimonial", "soundbite", "statistic", "use_case", "objection", "vision_statement"), "content" (string), "speaker" (string), "reuse_score" (float 0-1).
- **competitive_mentions** (array of objects): Each has "competitor_name" (string), "sentiment" (one of: "positive", "neutral", "negative"), "context" (string), "quote" (string), "feature_comparison" (string or null).

### Consultant Performance dimensions
- **question_quality** (object): { "score": float 0-1, "open_vs_closed_ratio": float 0-1, "best_question": string, "missed_opportunities": [string] }
- **active_listening** (object): { "score": float 0-1, "paraphrase_count": int, "follow_up_depth": float 0-1, "examples": [string] }
- **discovery_depth** (object): { "score": float 0-1, "surface_questions": int, "deep_questions": int, "reframe_moments": [string] }
- **objection_handling** (object): { "score": float 0-1, "objections_surfaced": int, "objections_addressed": int, "technique_notes": [string] }
- **next_steps_clarity** (object): { "score": float 0-1, "commitments_made": [string], "follow_ups_assigned": [string], "ambiguous_items": [string] }
- **consultant_talk_ratio** (object): { "consultant_share": float 0-1, "ideal_range": "30-40%", "assessment": string }
- **consultant_summary** (string): 2-3 sentence coaching summary with specific improvement suggestions.

## Rules
1. Only include dimensions explicitly requested in the user message.
2. Use direct quotes from the transcript where applicable — do not fabricate.
3. If a dimension has no data (e.g., no competitors mentioned), return an empty array.
4. Return ONLY valid JSON — no markdown fences, no explanation.
5. Feature names should be normalized to match project features when context is provided.
"""


def resolve_dimensions(active_packs: str) -> list[str]:
    """Resolve pack names to a flat list of dimension names.

    Args:
        active_packs: Comma-separated pack names (e.g., "core,research")

    Returns:
        Flat list of dimension names
    """
    dimensions: list[str] = []
    for pack_name in active_packs.split(","):
        pack_name = pack_name.strip()
        if pack_name in DIMENSION_PACKS:
            dimensions.extend(DIMENSION_PACKS[pack_name])
        else:
            logger.warning(f"Unknown dimension pack: {pack_name}")
    return dimensions


def analyze_call_transcript(
    transcript_text: str,
    dimensions: list[str],
    context_blocks: list[dict[str, Any]] | None = None,
    settings: Settings | None = None,
    model_override: str | None = None,
    project_id: str | None = None,
) -> AnalysisResult:
    """
    Analyze a call transcript using Claude.

    Args:
        transcript_text: Full transcript text
        dimensions: List of dimension names to extract
        context_blocks: Optional project context (features, personas, etc.)
        settings: App settings (auto-loaded if None)
        model_override: Override the analysis model
        project_id: For usage logging

    Returns:
        AnalysisResult with extracted dimensions
    """
    if not settings:
        settings = get_settings()

    if not settings.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not configured")

    model = model_override or settings.CALL_ANALYSIS_MODEL
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Build user message
    user_parts: list[str] = []
    user_parts.append(
        f"Analyze the following call transcript for these dimensions: {', '.join(dimensions)}"
    )

    if context_blocks:
        user_parts.append("\n## Project Context")
        for block in context_blocks:
            label = block.get("label", "Context")
            content = block.get("content", "")
            user_parts.append(f"\n### {label}\n{content}")

    user_parts.append(f"\n## Transcript\n{transcript_text}")

    user_message = "\n".join(user_parts)

    # Determine active packs from dimensions
    packs_used = []
    for pack_name, pack_dims in DIMENSION_PACKS.items():
        if any(d in dimensions for d in pack_dims):
            packs_used.append(pack_name)

    logger.info(
        f"Analyzing call transcript: model={model}, "
        f"dimensions={len(dimensions)}, packs={packs_used}"
    )

    response = client.messages.create(
        model=model,
        max_tokens=settings.CALL_ANALYSIS_MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    usage = response.usage
    cache_read = getattr(usage, "cache_read_input_tokens", 0)
    cache_create = getattr(usage, "cache_creation_input_tokens", 0)

    log_llm_usage(
        workflow="analyze_call_transcript",
        model=response.model,
        provider="anthropic",
        tokens_input=usage.input_tokens,
        tokens_output=usage.output_tokens,
        tokens_cache_read=cache_read,
        tokens_cache_create=cache_create,
        project_id=project_id,
    )

    # Parse JSON response
    response_text = response.content[0].text.strip()
    if response_text.startswith("```json"):
        response_text = response_text[len("```json") :]
    if response_text.startswith("```"):
        response_text = response_text[len("```") :]
    if response_text.endswith("```"):
        response_text = response_text[: -len("```")]

    try:
        parsed = json.loads(response_text.strip())
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse call analysis response: {e}")
        parsed = {}

    # Build result
    result = AnalysisResult(
        engagement_score=parsed.get("engagement_score"),
        talk_ratio=parsed.get("talk_ratio", {}),
        engagement_timeline=parsed.get("engagement_timeline", []),
        executive_summary=parsed.get("executive_summary"),
        feature_insights=[fi for fi in parsed.get("feature_insights", [])],
        call_signals=[cs for cs in parsed.get("call_signals", [])],
        content_nuggets=[cn for cn in parsed.get("content_nuggets", [])],
        competitive_mentions=[cm for cm in parsed.get("competitive_mentions", [])],
        custom_dimensions={
            k: v
            for k, v in parsed.items()
            if k
            not in {
                "engagement_score",
                "talk_ratio",
                "engagement_timeline",
                "executive_summary",
                "feature_insights",
                "call_signals",
                "content_nuggets",
                "competitive_mentions",
            }
        },
        dimension_packs_used=packs_used,
        model=response.model,
        tokens_input=usage.input_tokens,
        tokens_output=usage.output_tokens,
    )

    logger.info(
        f"Call analysis complete: "
        f"engagement={result.engagement_score}, "
        f"insights={len(result.feature_insights)}, "
        f"signals={len(result.call_signals)}, "
        f"nuggets={len(result.content_nuggets)}, "
        f"mentions={len(result.competitive_mentions)}"
    )

    return result
