"""Haiku-powered discovery probe generation and belief classification.

Sub-phase 3 of the Discovery Protocol. Generates clarifying probes for
North Star categories where ambiguity is highest. Also includes the
Haiku fallback for classifying beliefs without a mapped belief_domain.

~200ms per call. Follows classify_gap_knowledge.py pattern.
"""

import hashlib
import json
import time

from app.core.config import get_settings
from app.core.llm_usage import log_llm_usage
from app.core.logging import get_logger
from app.core.schemas_briefing import GapCluster
from app.core.schemas_discovery import (
    AmbiguityScore,
    DiscoveryProbe,
    NorthStarCategory,
)

logger = get_logger(__name__)

HAIKU_MODEL = "claude-haiku-4-5-20251001"

# Minimum ambiguity to generate probes for a category
PROBE_AMBIGUITY_THRESHOLD = 0.4

# =============================================================================
# Probe Generation
# =============================================================================

PROBE_SYSTEM = """You are a Discovery Protocol engine for a requirements consultant.
Generate clarifying probes — questions the consultant should ask their client.

## Rules
- Each probe targets a specific North Star category where ambiguity is highest.
- Probes MUST reference existing beliefs or gaps — never invent new assertions.
- Frame as opportunities ("Confirming X would unlock..."), not deficiencies.
- Context: 1-2 sentences explaining why this matters.
- Question: The specific clarifying question to ask.
- Why: One sentence on why we're asking this.
- Max 5 probes total.

## North Star Categories
- organizational_impact: What organizational outcome does this project serve?
- human_behavioral_goal: What human behavior should change as a result?
- success_metrics: How will success be measured?
- cultural_constraints: What organizational norms or policies constrain the solution?

Return valid JSON array only. No markdown fences."""

PROBE_USER = """Generate discovery probes based on these ambiguity scores and beliefs.

## Ambiguity Scores
{scores_json}

## High-Ambiguity Beliefs (lowest confidence per category)
{beliefs_json}

## Related Gap Themes
{gaps_json}

Return ONLY a JSON array:
[
  {{
    "category": "organizational_impact|human_behavioral_goal|success_metrics|cultural_constraints",
    "context": "1-2 sentences: why this matters",
    "question": "The clarifying question",
    "why": "Why we're asking this",
    "linked_belief_ids": ["id1", "id2"],
    "linked_gap_cluster_ids": ["cid1"]
  }}
]"""


async def generate_discovery_probes(
    ambiguity_scores: dict[str, AmbiguityScore],
    beliefs: dict[str, list[dict]],
    gap_clusters: list[GapCluster],
    project_id: str | None = None,
) -> list[DiscoveryProbe]:
    """Generate 3-5 discovery probes via Haiku.

    Only generates probes for categories with ambiguity > PROBE_AMBIGUITY_THRESHOLD.
    """
    # Filter to high-ambiguity categories
    high_ambiguity = {
        k: v for k, v in ambiguity_scores.items()
        if v.score > PROBE_AMBIGUITY_THRESHOLD
    }
    if not high_ambiguity:
        logger.info("Discovery Protocol: all categories below ambiguity threshold, no probes needed")
        return []

    from anthropic import AsyncAnthropic

    # Build compact score summary
    scores_compact = [
        {
            "category": s.category.value,
            "ambiguity": round(s.score, 2),
            "belief_count": s.belief_count,
            "avg_confidence": round(s.avg_confidence, 2),
            "contradiction_rate": round(s.contradiction_rate, 2),
        }
        for s in high_ambiguity.values()
    ]

    # Top 5 lowest-confidence beliefs per high-ambiguity category
    beliefs_compact = []
    for cat_value in high_ambiguity:
        cat_beliefs = beliefs.get(cat_value, [])
        sorted_beliefs = sorted(cat_beliefs, key=lambda b: b.get("confidence", 0.5))
        for b in sorted_beliefs[:5]:
            beliefs_compact.append({
                "id": b["id"],
                "category": cat_value,
                "summary": (b.get("summary") or b.get("content", ""))[:120],
                "confidence": b.get("confidence", 0.5),
            })

    # Gap cluster themes
    gaps_compact = [
        {"cluster_id": c.cluster_id, "theme": c.theme, "total_gaps": c.total_gaps}
        for c in gap_clusters[:8]
    ]

    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    user_message = PROBE_USER.format(
        scores_json=json.dumps(scores_compact, indent=2),
        beliefs_json=json.dumps(beliefs_compact, indent=2),
        gaps_json=json.dumps(gaps_compact, indent=2),
    )

    try:
        start = time.time()
        response = await client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=1024,
            temperature=0.3,
            system=[
                {
                    "type": "text",
                    "text": PROBE_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_message}],
        )
        duration_ms = int((time.time() - start) * 1000)

        usage = response.usage
        cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
        cache_create = getattr(usage, "cache_creation_input_tokens", 0) or 0

        log_llm_usage(
            workflow="discovery_protocol",
            model=HAIKU_MODEL,
            provider="anthropic",
            tokens_input=usage.input_tokens,
            tokens_output=usage.output_tokens,
            duration_ms=duration_ms,
            chain="generate_discovery_probes",
            project_id=project_id,
            tokens_cache_read=cache_read,
            tokens_cache_create=cache_create,
        )

        # Parse response
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        probes_raw = json.loads(text)
        if isinstance(probes_raw, str):
            # Anthropic string bug guard
            probes_raw = json.loads(probes_raw)

        probes: list[DiscoveryProbe] = []
        for p in probes_raw[:5]:
            try:
                cat = NorthStarCategory(p["category"])
            except (ValueError, KeyError):
                continue

            probe_hash = hashlib.md5(
                (p.get("question", "") + cat.value).encode()
            ).hexdigest()[:12]

            probes.append(DiscoveryProbe(
                probe_id=f"probe:{probe_hash}",
                category=cat,
                context=p.get("context", ""),
                question=p.get("question", ""),
                why=p.get("why", ""),
                linked_belief_ids=p.get("linked_belief_ids", []),
                linked_gap_cluster_ids=p.get("linked_gap_cluster_ids", []),
                priority=high_ambiguity.get(cat.value, AmbiguityScore(
                    category=cat, score=0.5, belief_count=0,
                    avg_confidence=0.0, contradiction_rate=0.0,
                    coverage_sparsity=0.0, gap_density=0.0,
                )).score,
            ))

        logger.info(
            f"Discovery probes: {len(probes)} generated ({duration_ms}ms)"
        )
        return probes

    except Exception as e:
        logger.warning(f"Discovery probe generation failed (non-fatal): {e}")
        return []


# =============================================================================
# Belief Classification Fallback
# =============================================================================

CLASSIFY_SYSTEM = """You classify project beliefs into North Star categories.

## Categories
- organizational_impact: Business outcomes, revenue, ROI, cost savings, strategic goals
- human_behavioral_goal: User behavior changes, adoption, workflow improvements, usability
- success_metrics: KPIs, measurements, performance indicators, analytics targets
- cultural_constraints: Compliance, policy, governance, security, organizational norms

## Rules
- One category per belief. Pick the BEST fit.
- If a belief doesn't fit any category, use "none".
- Return valid JSON array only. No markdown fences."""

CLASSIFY_USER = """Classify these beliefs:

{beliefs_json}

Return ONLY a JSON array:
[{{"id": "...", "category": "organizational_impact|human_behavioral_goal|success_metrics|cultural_constraints|none"}}]"""


async def classify_belief_categories(beliefs: list[dict]) -> dict[str, str]:
    """Single Haiku call to categorize beliefs without belief_domain.

    Returns: {belief_id: category_value}
    """
    if not beliefs:
        return {}

    from anthropic import AsyncAnthropic

    compact = [
        {
            "id": b["id"],
            "text": (b.get("summary") or b.get("content", ""))[:150],
        }
        for b in beliefs[:30]  # Cap at 30 to keep token usage reasonable
    ]

    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    user_message = CLASSIFY_USER.format(beliefs_json=json.dumps(compact, indent=2))

    try:
        start = time.time()
        response = await client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=512,
            temperature=0.2,
            system=[
                {
                    "type": "text",
                    "text": CLASSIFY_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_message}],
        )
        duration_ms = int((time.time() - start) * 1000)

        usage = response.usage
        log_llm_usage(
            workflow="discovery_protocol",
            model=HAIKU_MODEL,
            provider="anthropic",
            tokens_input=usage.input_tokens,
            tokens_output=usage.output_tokens,
            duration_ms=duration_ms,
            chain="classify_belief_categories",
        )

        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        classifications = json.loads(text)
        if isinstance(classifications, str):
            classifications = json.loads(classifications)

        result = {}
        for c in classifications:
            cat = c.get("category", "none")
            if cat != "none":
                result[c["id"]] = cat

        logger.info(f"Belief classification: {len(result)}/{len(beliefs)} categorized ({duration_ms}ms)")
        return result

    except Exception as e:
        logger.warning(f"Belief classification failed: {e}")
        return {}
