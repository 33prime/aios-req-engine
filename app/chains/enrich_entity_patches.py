"""Enrich EntityPatch[] with hypothetical questions, term expansion, canonical format.

This chain runs AFTER extraction and BEFORE dedup in the signal pipeline.
Each entity gets enriched with intent-aware metadata that dramatically
improves dedup resolution and multi-vector embedding quality.

Processes patches in batches of 3-4 same-type entities per Haiku call.
Falls back to raw patches on individual enrichment failure.

Usage:
    from app.chains.enrich_entity_patches import enrich_entity_patches

    enriched = await enrich_entity_patches(
        patches=raw_patches,
        entity_inventory_prompt=snapshot.entity_inventory_prompt,
        project_id=project_id,
    )
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from itertools import islice
from typing import Any
from uuid import UUID

from app.core.schemas_entity_patch import EntityPatch

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

_MAX_RETRIES = 2
_INITIAL_DELAY = 1.0
_BATCH_SIZE = 4  # entities per Haiku call
_MAX_CONCURRENT = 5  # parallel Haiku calls
_MODEL = "claude-haiku-4-5-20251001"


# =============================================================================
# Tool schema for forced structured output
# =============================================================================

ENRICHMENT_TOOL = {
    "name": "submit_enrichments",
    "description": "Submit enrichment data for the entity patches.",
    "input_schema": {
        "type": "object",
        "properties": {
            "enrichments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "patch_index": {
                            "type": "integer",
                            "description": "Index of the patch in the input batch",
                        },
                        "canonical_text": {
                            "type": "string",
                            "description": (
                                "Structured representation of ALL entity fields. "
                                "Format: [ENTITY] name [TYPE] type [STATE] state [CONTEXT] detail"
                            ),
                        },
                        "hypothetical_questions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 4,
                            "maxItems": 8,
                            "description": (
                                "4-8 questions this entity would ANSWER. "
                                "NOT questions about the entity — questions someone would ASK "
                                "if this entity is what they need. Generate from perspectives of "
                                "different roles (technical, business, operational, end-user)."
                            ),
                        },
                        "expanded_terms": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 8,
                            "maxItems": 20,
                            "description": (
                                "10-20 semantically related terms NOT in the raw extraction. "
                                "Industry synonyms, related concepts, upstream/downstream process names."
                            ),
                        },
                        "before_after": {
                            "type": "object",
                            "properties": {
                                "before": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "after": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                            "description": "For workflows/steps: inferred steps before and after.",
                        },
                        "downstream_impacts": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "What other entities/processes/outcomes change if this entity changes.",
                        },
                        "actors": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "For workflows/features: who executes, owns, or is affected.",
                        },
                        "outcome_relevance": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Which known outcomes this entity might serve or block.",
                        },
                    },
                    "required": [
                        "patch_index",
                        "canonical_text",
                        "hypothetical_questions",
                        "expanded_terms",
                    ],
                },
            },
        },
        "required": ["enrichments"],
    },
}


# =============================================================================
# System prompt
# =============================================================================

_SYSTEM_PROMPT_STATIC = """You are an entity enrichment engine for a requirements engineering platform.

For each entity in the batch, produce:

1. canonical_text — A structured representation of ALL entity fields in a consistent format.
   Format: [ENTITY] {name} [TYPE] {entity_type} [STATE] {current state} [CONTEXT] {relevant detail}
   Include every field from the payload. Be thorough — this text is used for embedding and dedup.

2. hypothetical_questions — 4-8 questions this entity would ANSWER.
   NOT questions about the entity. Questions someone would ASK if this entity is the answer.
   Generate from multiple perspectives: technical, business, operational, end-user.
   Example for a workflow: "What causes data entry errors?", "Which process needs automation?"
   Example for a feature: "How do users track inventory?", "What reduces classification time?"

3. expanded_terms — 10-20 semantically related terms NOT present in the entity text.
   Industry-specific synonyms, related concepts, upstream/downstream process names.
   These terms should make this entity findable via queries that don't use its exact vocabulary.

4. before_after — (workflows and steps only) Inferred steps that come before and after.

5. downstream_impacts — What other entities, processes, or outcomes are affected if this entity changes.

6. actors — (workflows and features only) Who executes, owns, or is affected.

7. outcome_relevance — Which of the project's known outcomes might this entity serve or block.

Be specific. Use project context. Don't generate generic filler."""


# =============================================================================
# Core enrichment function
# =============================================================================


async def enrich_entity_patches(
    patches: list[EntityPatch],
    entity_inventory_prompt: str,
    project_id: UUID,
    signal_id: UUID | None = None,
) -> list[EntityPatch]:
    """Enrich entity patches with hypothetical questions, term expansion, canonical text.

    Processes in batches of same-type entities. Falls back to raw patch on failure.

    Args:
        patches: Raw patches from extraction.
        entity_inventory_prompt: Layer 1 from ContextSnapshot.
        project_id: Project UUID.
        signal_id: Source signal UUID (for provenance tracking).

    Returns:
        Same patches with enrichment fields populated where successful.
    """
    if not patches:
        return patches

    start = time.monotonic()

    # Group patches by entity_type for same-type batching
    type_groups: dict[str, list[tuple[int, EntityPatch]]] = {}
    for i, patch in enumerate(patches):
        type_groups.setdefault(patch.entity_type, []).append((i, patch))

    # Build batches of up to _BATCH_SIZE same-type entities
    batches: list[list[tuple[int, EntityPatch]]] = []
    for entity_type, group in type_groups.items():
        it = iter(group)
        while True:
            batch = list(islice(it, _BATCH_SIZE))
            if not batch:
                break
            batches.append(batch)

    # Run batches with concurrency limit
    semaphore = asyncio.Semaphore(_MAX_CONCURRENT)
    enrichment_map: dict[int, dict] = {}  # patch_index → enrichment result
    error_count = 0

    async def process_batch(batch: list[tuple[int, EntityPatch]]) -> None:
        nonlocal error_count
        async with semaphore:
            try:
                results = await _call_enrichment_llm(
                    batch=batch,
                    entity_inventory_prompt=entity_inventory_prompt,
                )
                for result in results:
                    idx = result.get("patch_index")
                    if idx is not None:
                        # Map batch-local index to global patch index
                        global_idx = batch[idx][0] if idx < len(batch) else None
                        if global_idx is not None:
                            enrichment_map[global_idx] = result
            except Exception:
                error_count += len(batch)
                logger.exception(
                    f"Enrichment batch failed ({len(batch)} patches), "
                    f"falling back to raw"
                )

    await asyncio.gather(*[process_batch(b) for b in batches])

    # Apply enrichment results to patches
    enriched_count = 0
    for i, patch in enumerate(patches):
        enrichment = enrichment_map.get(i)
        if enrichment:
            patch.canonical_text = enrichment.get("canonical_text")
            patch.hypothetical_questions = enrichment.get("hypothetical_questions")
            patch.expanded_terms = enrichment.get("expanded_terms")
            patch.enrichment_data = {
                k: v
                for k, v in {
                    "before_after": enrichment.get("before_after"),
                    "downstream_impacts": enrichment.get("downstream_impacts", []),
                    "actors": enrichment.get("actors", []),
                    "outcome_relevance": enrichment.get("outcome_relevance", []),
                }.items()
                if v
            }
            enriched_count += 1

    elapsed_ms = int((time.monotonic() - start) * 1000)
    logger.info(
        f"Enriched {enriched_count}/{len(patches)} patches in {elapsed_ms}ms "
        f"({len(batches)} batches, {error_count} errors)"
    )

    return patches


# =============================================================================
# LLM call — follows exact pattern from extract_entity_patches.py
# =============================================================================


async def _call_enrichment_llm(
    batch: list[tuple[int, EntityPatch]],
    entity_inventory_prompt: str,
) -> list[dict]:
    """Call Haiku to enrich a batch of same-type entities.

    Returns list of enrichment dicts with patch_index fields.
    """
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

    # Build user prompt with batch entities
    entity_type = batch[0][1].entity_type
    entity_descriptions = []
    for batch_idx, (_, patch) in enumerate(batch):
        name = patch.payload.get("name") or patch.payload.get("title") or patch.payload.get("label") or patch.payload.get("description", "")[:60]
        entity_descriptions.append(
            f"### Entity {batch_idx}: {entity_type} — \"{name}\"\n"
            f"Payload: {json.dumps(patch.payload, default=str)[:1500]}\n"
            f"Operation: {patch.operation}\n"
            f"Evidence: {patch.evidence[0].quote[:200] if patch.evidence else 'none'}"
        )

    user_prompt = (
        f"## Entities to Enrich ({entity_type}, batch of {len(batch)})\n\n"
        + "\n\n".join(entity_descriptions)
    )

    # System blocks with caching
    system_blocks = [
        {
            "type": "text",
            "text": _SYSTEM_PROMPT_STATIC,
            "cache_control": {"type": "ephemeral"},
        },
    ]
    if entity_inventory_prompt:
        system_blocks.append({
            "type": "text",
            "text": f"## Project Context\n\n{entity_inventory_prompt[:3000]}",
        })

    last_error: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = await client.messages.create(
                model=_MODEL,
                max_tokens=2000 * len(batch),
                system=system_blocks,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=0.2,
                tools=[ENRICHMENT_TOOL],
                tool_choice={"type": "tool", "name": "submit_enrichments"},
            )

            # Extract tool input
            for block in response.content:
                if block.type == "tool_use":
                    data = block.input
                    enrichments_raw = data.get("enrichments", [])
                    # Handle case where API returns as JSON string
                    if isinstance(enrichments_raw, str):
                        try:
                            enrichments_raw = json.loads(enrichments_raw)
                        except json.JSONDecodeError:
                            logger.error("Failed to parse enrichments string as JSON")
                            enrichments_raw = []
                    return enrichments_raw

            # Fallback: no tool_use block
            logger.warning("No tool_use block in enrichment response")
            return []

        except (
            APIConnectionError,
            APITimeoutError,
            InternalServerError,
            RateLimitError,
        ) as e:
            last_error = e
            if attempt < _MAX_RETRIES:
                delay = _INITIAL_DELAY * (2**attempt)
                logger.warning(
                    f"Enrichment LLM attempt {attempt + 1}/{_MAX_RETRIES + 1} "
                    f"failed ({type(e).__name__}), retrying in {delay}s"
                )
                await asyncio.sleep(delay)
            else:
                raise

    raise last_error  # type: ignore[misc]
