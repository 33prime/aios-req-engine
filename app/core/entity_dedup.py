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
from typing import Any
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
    "feature": DedupThresholds(0.82, 0.45, 0.88),        # Lowered from (0.85, 0.50, 0.90) — catch near-match features
    "constraint": DedupThresholds(0.80, 0.45, 0.88),
    "data_entity": DedupThresholds(0.85, 0.50, 0.90),
    "competitor": DedupThresholds(0.80, 0.55, 0.0),      # No embedding check (names too short)
    "workflow": DedupThresholds(0.85, 0.50, 0.90),
    "business_driver": DedupThresholds(0.82, 0.50, 0.88),  # Description-based — lowered now that generic guard catches false positives
    "stakeholder": DedupThresholds(0.80, 0.45, 0.0),     # No embedding check
    "persona": DedupThresholds(0.85, 0.50, 0.0),         # Names only
    "vp_step": DedupThresholds(0.85, 0.50, 0.90),
    "workflow_step": DedupThresholds(0.78, 0.45, 0.88),   # Lowered from (0.85, 0.50, 0.90) — catch near-match steps
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
    extraction_log: Any | None = None,  # ExtractionLog instance
    pulse_health_map: dict | None = None,  # EntityHealth dict from pulse for threshold tuning
) -> list[EntityPatch]:
    """Run 3-tier dedup on create patches. Non-create patches pass through unchanged.

    Args:
        patches: All patches from extraction
        entity_inventory: Context snapshot's entity_inventory (type → list[entity_dict])
        project_id: Project UUID (for embedding lookups)
        extraction_log: Optional ExtractionLog to record dedup decisions
        pulse_health_map: Optional health map from pulse for dynamic threshold tuning

    Returns:
        Deduped patch list (creates may be converted to merges)
    """
    # Build effective thresholds with pulse-based adjustments
    effective_config = dict(DEDUP_CONFIG)
    if pulse_health_map:
        try:
            from app.core.pulse_dynamics import suggest_dedup_adjustments
            adjustments = suggest_dedup_adjustments(pulse_health_map)
            for entity_type, adj in adjustments.items():
                base = DEDUP_CONFIG.get(entity_type)
                if base and "fuzzy_merge_delta" in adj:
                    delta = adj["fuzzy_merge_delta"]
                    effective_config[entity_type] = DedupThresholds(
                        fuzzy_merge=max(0.5, min(0.95, base.fuzzy_merge + delta)),
                        fuzzy_ambiguous=base.fuzzy_ambiguous,
                        embedding_merge=base.embedding_merge,
                    )
        except Exception as e:
            logger.debug(f"Pulse dedup adjustments skipped: {e}")

    result: list[EntityPatch] = []
    dedup_decisions: list[dict] = []
    dedup_stats = {"exact": 0, "fuzzy": 0, "embedding": 0, "passed": 0}

    for patch in patches:
        if patch.operation != "create":
            result.append(patch)
            continue

        entity_type = patch.entity_type
        config = effective_config.get(entity_type)
        if not config:
            result.append(patch)
            continue

        patch_name = patch.payload.get("name") or patch.payload.get("label") or patch.payload.get("title") or ""

        # Business drivers have no name — use description as comparison key
        if not patch_name and entity_type == "business_driver":
            patch_name = (patch.payload.get("description") or "")[:80]

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
            dedup_decisions.append({
                "patch_name": patch_name,
                "entity_type": entity_type,
                "strategy": "exact_name",
                "matched_entity_id": str(matched_entity["id"]),
                "matched_entity_name": _get_entity_name(matched_entity),
                "score": 1.0,
                "action": "convert_to_merge",
            })
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
            dedup_decisions.append({
                "patch_name": patch_name,
                "entity_type": entity_type,
                "strategy": "passed",
                "matched_entity_id": None,
                "matched_entity_name": None,
                "score": 0.0,
                "action": "keep_as_create",
            })
            continue

        if best_score >= config.fuzzy_merge and best_match:
            merged = _convert_create_to_merge(patch, str(best_match["id"]), best_score, "fuzzy_name")
            result.append(merged)
            dedup_stats["fuzzy"] += 1
            dedup_decisions.append({
                "patch_name": patch_name,
                "entity_type": entity_type,
                "strategy": "fuzzy_name",
                "matched_entity_id": str(best_match["id"]),
                "matched_entity_name": _get_entity_name(best_match),
                "score": best_score,
                "action": "convert_to_merge",
            })
            continue

        # Tier 3: Embedding similarity via DB vector search
        if best_score >= config.fuzzy_ambiguous and config.embedding_merge > 0:
            try:
                emb_result = await _check_embedding_similarity(
                    patch, entity_type, project_id
                )
                if emb_result is not None:
                    emb_sim, emb_entity_id, emb_entity_name = emb_result
                    if emb_sim >= config.embedding_merge:
                        merged = _convert_create_to_merge(
                            patch, emb_entity_id, emb_sim, "embedding"
                        )
                        result.append(merged)
                        dedup_stats["embedding"] += 1
                        dedup_decisions.append({
                            "patch_name": patch_name,
                            "entity_type": entity_type,
                            "strategy": "embedding",
                            "matched_entity_id": emb_entity_id,
                            "matched_entity_name": emb_entity_name,
                            "score": emb_sim,
                            "action": "convert_to_merge",
                        })
                        continue
            except Exception as e:
                logger.warning(f"Embedding dedup check failed for {entity_type}: {e}")

        result.append(patch)
        dedup_stats["passed"] += 1
        dedup_decisions.append({
            "patch_name": patch_name,
            "entity_type": entity_type,
            "strategy": "passed",
            "matched_entity_id": None,
            "matched_entity_name": _get_entity_name(best_match) if best_match else None,
            "score": best_score,
            "action": "keep_as_create",
        })

    total_creates = sum(1 for p in patches if p.operation == "create")
    total_deduped = dedup_stats["exact"] + dedup_stats["fuzzy"] + dedup_stats["embedding"]
    if total_deduped > 0:
        logger.info(
            f"Dedup: {total_deduped}/{total_creates} creates converted to merges "
            f"(exact={dedup_stats['exact']}, fuzzy={dedup_stats['fuzzy']}, "
            f"embedding={dedup_stats['embedding']})"
        )

    if extraction_log is not None:
        extraction_log.log_entity_dedup(result, dedup_decisions)

    return result


async def _check_embedding_similarity(
    patch: EntityPatch,
    entity_type: str,
    project_id: UUID,
) -> tuple[float, str, str] | None:
    """Find the most similar existing entity via DB vector search.

    Embeds the patch text and queries the match_entities RPC for the
    nearest neighbor of the same entity_type.

    Returns:
        (similarity, entity_id, display_text) or None if no match found.
    """
    from app.core.embeddings import embed_texts
    from app.db.entity_embeddings import EMBED_TEXT_BUILDERS
    from app.db.supabase_client import get_supabase

    builder = EMBED_TEXT_BUILDERS.get(entity_type)
    if not builder:
        return None

    # Build text for the new patch
    patch_text = builder(patch.payload)
    if not patch_text or len(patch_text.strip()) < 10:
        return None

    # Embed the patch text
    embeddings = embed_texts([patch_text.strip()])
    if not embeddings:
        return None

    # Query DB for nearest neighbors via match_entities RPC
    sb = get_supabase()
    result = sb.rpc("match_entities", {
        "query_embedding": embeddings[0],
        "filter_project_id": str(project_id),
        "match_count": 5,
        "filter_entity_types": [entity_type],
    }).execute()

    if not result.data:
        return None

    # Return best match (already filtered by entity_type in RPC)
    for row in result.data:
        if row.get("entity_type") == entity_type:
            sim = float(row["similarity"])
            entity_id = str(row["entity_id"])
            display_text = row.get("entity_name", "")
            logger.debug(
                f"Embedding dedup: {entity_type} '{patch_text[:50]}' "
                f"→ '{display_text[:50]}' (sim={sim:.3f})"
            )
            return (sim, entity_id, display_text)

    return None


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
