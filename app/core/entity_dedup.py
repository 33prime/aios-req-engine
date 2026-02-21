"""3-tier entity deduplication gate for the V2 signal pipeline.

Sits between extraction (step 4) and scoring (step 5). Only processes
`create` patches — merge/update/stale/delete pass through unchanged.

Dedup tiers:
  1. Exact normalized name match → convert to merge
  2. RapidFuzz token_set_ratio above threshold → convert to merge
  3. Ambiguous zone → check entity embedding cosine similarity → merge if above threshold
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from uuid import UUID

from app.core.schemas_entity_patch import EntityPatch

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DedupThresholds:
    """Per-type dedup thresholds."""
    fuzzy_merge: float       # token_set_ratio above this → auto-merge
    fuzzy_ambiguous: float   # between ambiguous and merge → check embeddings
    embedding_merge: float   # cosine sim above this → merge (tier 3)


# Per-type dedup configuration
DEDUP_CONFIG: dict[str, DedupThresholds] = {
    "feature": DedupThresholds(0.85, 0.50, 0.90),
    "constraint": DedupThresholds(0.80, 0.45, 0.88),
    "data_entity": DedupThresholds(0.85, 0.50, 0.90),
    "competitor": DedupThresholds(0.80, 0.55, 0.0),      # No embedding check (names too short)
    "workflow": DedupThresholds(0.85, 0.50, 0.90),
    "business_driver": DedupThresholds(0.90, 0.60, 0.92),  # Tight — generic descriptions merge wrongly
    "stakeholder": DedupThresholds(0.80, 0.45, 0.0),     # No embedding check
    "persona": DedupThresholds(0.85, 0.50, 0.0),         # Names only
    "vp_step": DedupThresholds(0.85, 0.50, 0.90),
    "workflow_step": DedupThresholds(0.85, 0.50, 0.90),
    "prd_section": DedupThresholds(0.85, 0.50, 0.90),
}

# Business driver descriptions that are too generic to merge on
GENERIC_DESCRIPTIONS = {
    "increase revenue", "reduce costs", "improve efficiency",
    "enhance customer experience", "drive growth", "increase productivity",
    "improve quality", "reduce risk", "increase market share",
}


def _normalize_name(name: str) -> str:
    """Normalize entity name for comparison."""
    return re.sub(r"[^a-z0-9 ]", "", name.lower()).strip()


def _get_entity_name(entity: dict) -> str:
    """Extract display name from entity dict."""
    return entity.get("name") or entity.get("label") or entity.get("title") or entity.get("description", "")


async def dedup_create_patches(
    patches: list[EntityPatch],
    entity_inventory: dict[str, list[dict]],
    project_id: UUID,
) -> list[EntityPatch]:
    """Run 3-tier dedup on create patches. Non-create patches pass through unchanged.

    Args:
        patches: All patches from extraction
        entity_inventory: Context snapshot's entity_inventory (type → list[entity_dict])
        project_id: Project UUID (for embedding lookups)

    Returns:
        Deduped patch list (creates may be converted to merges)
    """
    result: list[EntityPatch] = []
    dedup_stats = {"exact": 0, "fuzzy": 0, "embedding": 0, "passed": 0}

    for patch in patches:
        if patch.operation != "create":
            result.append(patch)
            continue

        entity_type = patch.entity_type
        config = DEDUP_CONFIG.get(entity_type)
        if not config:
            result.append(patch)
            continue

        patch_name = patch.payload.get("name") or patch.payload.get("label") or patch.payload.get("title") or ""
        if not patch_name:
            result.append(patch)
            continue

        normalized_name = _normalize_name(patch_name)
        existing_entities = entity_inventory.get(entity_type, [])

        # Business driver guard: don't merge generic descriptions
        if entity_type == "business_driver":
            desc = (patch.payload.get("description") or "").lower().strip()
            if len(desc) < 20 or desc in GENERIC_DESCRIPTIONS:
                result.append(patch)
                dedup_stats["passed"] += 1
                continue

        # Tier 1: Exact normalized name match
        matched_entity = None
        for entity in existing_entities:
            existing_name = _get_entity_name(entity)
            if _normalize_name(existing_name) == normalized_name:
                matched_entity = entity
                break

        if matched_entity:
            merged = _convert_create_to_merge(patch, str(matched_entity["id"]), 1.0, "exact_name")
            result.append(merged)
            dedup_stats["exact"] += 1
            continue

        # Tier 2: Fuzzy name matching
        best_score = 0.0
        best_match = None
        try:
            from rapidfuzz import fuzz
            for entity in existing_entities:
                existing_name = _get_entity_name(entity)
                if not existing_name:
                    continue
                score = fuzz.token_set_ratio(patch_name.lower(), existing_name.lower()) / 100.0
                if score > best_score:
                    best_score = score
                    best_match = entity
        except ImportError:
            logger.debug("rapidfuzz not installed, skipping fuzzy dedup")
            result.append(patch)
            dedup_stats["passed"] += 1
            continue

        if best_score >= config.fuzzy_merge and best_match:
            merged = _convert_create_to_merge(patch, str(best_match["id"]), best_score, "fuzzy_name")
            result.append(merged)
            dedup_stats["fuzzy"] += 1
            continue

        # Tier 3: Embedding similarity (only if in ambiguous zone and embeddings available)
        if best_score >= config.fuzzy_ambiguous and config.embedding_merge > 0 and best_match:
            try:
                embedding_sim = await _check_embedding_similarity(
                    patch, best_match, entity_type, project_id
                )
                if embedding_sim is not None and embedding_sim >= config.embedding_merge:
                    merged = _convert_create_to_merge(
                        patch, str(best_match["id"]), embedding_sim, "embedding"
                    )
                    result.append(merged)
                    dedup_stats["embedding"] += 1
                    continue
            except Exception as e:
                logger.debug(f"Embedding dedup check failed: {e}")

        result.append(patch)
        dedup_stats["passed"] += 1

    total_creates = sum(1 for p in patches if p.operation == "create")
    total_deduped = dedup_stats["exact"] + dedup_stats["fuzzy"] + dedup_stats["embedding"]
    if total_deduped > 0:
        logger.info(
            f"Dedup: {total_deduped}/{total_creates} creates converted to merges "
            f"(exact={dedup_stats['exact']}, fuzzy={dedup_stats['fuzzy']}, "
            f"embedding={dedup_stats['embedding']})"
        )

    return result


async def _check_embedding_similarity(
    patch: EntityPatch,
    existing_entity: dict,
    entity_type: str,
    project_id: UUID,
) -> float | None:
    """Check cosine similarity between patch content and existing entity embedding.

    Returns similarity score or None if embeddings unavailable.
    """
    from app.core.embeddings import embed_texts
    from app.db.entity_embeddings import EMBED_TEXT_BUILDERS

    builder = EMBED_TEXT_BUILDERS.get(entity_type)
    if not builder:
        return None

    # Build text for the new patch
    patch_text = builder(patch.payload)
    if not patch_text or len(patch_text.strip()) < 10:
        return None

    # Check if existing entity has embedding
    existing_embedding = existing_entity.get("embedding")
    if not existing_embedding:
        return None

    # Embed the patch text
    embeddings = embed_texts([patch_text.strip()])
    if not embeddings:
        return None

    # Compute cosine similarity
    import math
    a, b = embeddings[0], existing_embedding
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return None

    return dot / (norm_a * norm_b)


def _convert_create_to_merge(
    patch: EntityPatch,
    matched_entity_id: str,
    score: float,
    strategy: str,
) -> EntityPatch:
    """Convert a create patch to a merge patch targeting an existing entity."""
    logger.info(
        f"Dedup: converting create→merge for {patch.entity_type} "
        f"'{patch.payload.get('name', patch.payload.get('label', '?'))}' "
        f"→ {matched_entity_id} (score={score:.2f}, strategy={strategy})"
    )
    return EntityPatch(
        operation="merge",
        entity_type=patch.entity_type,
        target_entity_id=matched_entity_id,
        payload=patch.payload,
        evidence=patch.evidence,
        confidence=patch.confidence,
        confidence_reasoning=f"{patch.confidence_reasoning or ''} [dedup: {strategy} match score={score:.2f}]".strip(),
        source_authority=patch.source_authority,
        mention_count=patch.mention_count,
        belief_impact=patch.belief_impact,
        answers_question=patch.answers_question,
    )
