"""Cross-chunk semantic consolidation of create patches.

After per-chunk extraction and exact-name merge, this module runs a single
Haiku call to identify semantically duplicate create patches — particularly
business_drivers and workflow_steps where the same concept is described
differently across document sections.

Usage:
    from app.chains.consolidate_patches import consolidate_create_patches

    patches, decisions = await consolidate_create_patches(all_patches)
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from app.core.schemas_entity_patch import EntityPatch

logger = logging.getLogger(__name__)

# Entity types worth consolidating (high cross-chunk duplication risk)
# NOTE: workflow_steps excluded — sequential steps in a process are distinct entities
# and LLM consolidation frequently collapses them incorrectly.
_CONSOLIDATION_TYPES = {"business_driver"}

_MAX_RETRIES = 2
_INITIAL_DELAY = 1.0

# =============================================================================
# Tool schema
# =============================================================================

CONSOLIDATION_TOOL = {
    "name": "submit_merge_groups",
    "description": "Submit ONLY confirmed duplicate groups. Set confirmed=true for real duplicates, confirmed=false for pairs you analyzed but decided to keep separate.",
    "input_schema": {
        "type": "object",
        "properties": {
            "merge_groups": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "keep_index": {
                            "type": "integer",
                            "description": "Index of the patch to keep (best description)",
                        },
                        "merge_indices": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Indices of patches to fold into the keeper",
                        },
                        "confirmed": {
                            "type": "boolean",
                            "description": "true = these ARE duplicates, merge them. false = analyzed but NOT duplicates, keep separate.",
                        },
                        "reasoning": {"type": "string"},
                    },
                    "required": ["keep_index", "merge_indices", "confirmed", "reasoning"],
                },
            },
        },
        "required": ["merge_groups"],
    },
}

# =============================================================================
# System prompt
# =============================================================================

_SYSTEM_PROMPT = """You are a requirements deduplication engine. You receive business_driver
create patches extracted from different sections of the same document.
Identify groups that describe THE SAME underlying driver and should be merged.

For each candidate pair, set confirmed=true ONLY if they are genuine duplicates.
Set confirmed=false if you analyzed them but they are NOT duplicates.

MERGE CRITERIA (ALL must be true):
1. Same driver_type (pain+pain, goal+goal, kpi+kpi). NEVER merge across types.
2. They describe the EXACT SAME concept restated in different words.
3. A reader would say "these are the same thing" — they are interchangeable.

NEVER merge (set confirmed=false):
- Different driver_types (pain vs goal, even on the same topic)
- A problem and its solution (e.g., "voice capture fails" vs "onboarding enables voice capture")
- A broad category and a specific instance (e.g., "platform optimization" vs "LinkedIn link handling")
- Two different feedback loops or mechanisms
- Phase 1 goal vs Phase 2 goal
- Market context/opportunity vs specific operational pain
- Budget/timeline constraints vs feature goals

Pick keep_index as the patch with the richest, most specific description.
An empty merge_groups array (or all confirmed=false) is valid and often correct."""


# =============================================================================
# Main function
# =============================================================================


async def consolidate_create_patches(
    patches: list[EntityPatch],
) -> tuple[list[EntityPatch], list[dict]]:
    """Consolidate semantically duplicate create patches via a single Haiku call.

    Args:
        patches: All patches (creates + non-creates) after exact-name merge.

    Returns:
        Tuple of (consolidated patches, merge group decisions for logging).
        On failure, returns originals unchanged with empty decisions.
    """
    # Separate creates from non-creates
    creates: list[EntityPatch] = []
    non_creates: list[EntityPatch] = []
    for p in patches:
        if p.operation == "create" and p.entity_type in _CONSOLIDATION_TYPES:
            creates.append(p)
        else:
            non_creates.append(p)

    if len(creates) < 2:
        return patches, []

    # Build compact representations for LLM
    candidates = []
    for i, p in enumerate(creates):
        rep: dict[str, Any] = {
            "index": i,
            "entity_type": p.entity_type,
        }
        if p.entity_type == "business_driver":
            rep["driver_type"] = p.payload.get("driver_type", "")
            rep["description"] = (p.payload.get("description") or "")[:150]
            rep["business_impact"] = (p.payload.get("business_impact") or "")[:100]
        rep["evidence_quote"] = creates[i].evidence[0].quote[:100] if creates[i].evidence else ""
        candidates.append(rep)

    # Call Haiku
    try:
        merge_groups = await _call_consolidation_llm(candidates)
    except Exception as e:
        logger.warning(f"Consolidation LLM call failed (continuing with originals): {e}")
        return patches, []

    if not merge_groups:
        return patches, []

    # Filter to only confirmed merges
    confirmed_groups = [g for g in merge_groups if g.get("confirmed", False) is True]
    rejected_count = len(merge_groups) - len(confirmed_groups)
    if rejected_count:
        logger.info(f"Consolidation: {rejected_count} candidate groups rejected (confirmed=false)")

    if not confirmed_groups:
        return patches, []

    # Apply merge groups
    consolidated, decisions = _apply_merge_groups(creates, non_creates, confirmed_groups)
    return consolidated, decisions


# =============================================================================
# LLM call
# =============================================================================


async def _call_consolidation_llm(candidates: list[dict]) -> list[dict]:
    """Call Haiku to identify semantic merge groups."""
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

    user_prompt = f"""## Create Patches to Consolidate

{json.dumps(candidates, indent=2)}

## Task
Identify groups of patches that describe the same underlying entity and should be merged. Use the submit_merge_groups tool."""

    last_error: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = await client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2000,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=0.0,
                tools=[CONSOLIDATION_TOOL],
                tool_choice={"type": "tool", "name": "submit_merge_groups"},
            )

            for block in response.content:
                if block.type == "tool_use":
                    data = block.input
                    groups = data.get("merge_groups", [])
                    # Handle API returning as JSON string
                    if isinstance(groups, str):
                        try:
                            groups = json.loads(groups)
                        except json.JSONDecodeError:
                            logger.error("Failed to parse merge_groups string as JSON")
                            return []
                    return groups

            logger.warning("No tool_use block in consolidation response")
            return []

        except (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError) as e:
            last_error = e
            if attempt < _MAX_RETRIES:
                delay = _INITIAL_DELAY * (2 ** attempt)
                logger.warning(
                    f"Consolidation attempt {attempt + 1}/{_MAX_RETRIES + 1} failed "
                    f"({type(e).__name__}), retrying in {delay}s"
                )
                await asyncio.sleep(delay)
            else:
                raise

    raise last_error  # unreachable but satisfies type checker


# =============================================================================
# Apply merge groups
# =============================================================================


def _apply_merge_groups(
    creates: list[EntityPatch],
    non_creates: list[EntityPatch],
    merge_groups: list[dict],
) -> tuple[list[EntityPatch], list[dict]]:
    """Apply LLM merge group decisions to create patches.

    For each group: keeps the patch at keep_index, folds evidence/mention_count/
    belief_impacts from merge_indices patches into it, removes merged patches.

    Returns:
        Tuple of (all consolidated patches, decision log entries).
    """
    # Validate: collect all indices used, check bounds and overlaps
    all_used: set[int] = set()
    valid_groups: list[dict] = []

    for group in merge_groups:
        keep = group.get("keep_index")
        merges = group.get("merge_indices", [])

        if keep is None or not merges:
            continue

        indices = {keep} | set(merges)
        # Bounds check
        if any(i < 0 or i >= len(creates) for i in indices):
            logger.warning(f"Consolidation group has out-of-bounds indices: {indices}")
            continue
        # Overlap check
        if indices & all_used:
            logger.warning(f"Consolidation group overlaps with previous: {indices & all_used}")
            continue

        all_used |= indices
        valid_groups.append(group)

    if not valid_groups:
        return creates + non_creates, []

    # Build set of indices to remove
    remove_indices: set[int] = set()
    decisions: list[dict] = []

    for group in valid_groups:
        keep_idx = group["keep_index"]
        merge_idxs = group["merge_indices"]
        keeper = creates[keep_idx]

        # Merge evidence, mention_count, belief_impacts from others
        all_evidence = list(keeper.evidence)
        total_mentions = keeper.mention_count
        all_beliefs = list(keeper.belief_impact)
        seen_quotes = {e.quote for e in all_evidence}

        merged_names = []
        for idx in merge_idxs:
            other = creates[idx]
            for ev in other.evidence:
                if ev.quote not in seen_quotes:
                    all_evidence.append(ev)
                    seen_quotes.add(ev.quote)
            total_mentions += other.mention_count
            all_beliefs.extend(other.belief_impact)
            merged_names.append(
                other.payload.get("description", other.payload.get("label", ""))[:60]
            )
            remove_indices.add(idx)

        # Update keeper in-place via reconstruction
        creates[keep_idx] = EntityPatch(
            operation=keeper.operation,
            entity_type=keeper.entity_type,
            target_entity_id=keeper.target_entity_id,
            payload=keeper.payload,
            evidence=all_evidence,
            confidence=keeper.confidence,
            confidence_reasoning=keeper.confidence_reasoning,
            belief_impact=all_beliefs,
            answers_question=keeper.answers_question,
            source_authority=keeper.source_authority,
            mention_count=total_mentions,
        )

        decisions.append({
            "keep_index": keep_idx,
            "keep_description": (keeper.payload.get("description") or keeper.payload.get("label", ""))[:80],
            "merged_indices": merge_idxs,
            "merged_descriptions": merged_names,
            "reasoning": group.get("reasoning", ""),
            "entity_type": keeper.entity_type,
        })

    # Filter out removed patches
    surviving_creates = [p for i, p in enumerate(creates) if i not in remove_indices]

    logger.info(
        f"Consolidation: {len(creates)} creates → {len(surviving_creates)} "
        f"({len(remove_indices)} merged away in {len(valid_groups)} groups)"
    )

    return surviving_creates + non_creates, decisions
