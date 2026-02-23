"""Extract EntityPatch[] from signal content using Sonnet with 3-layer context.

This is the core extraction chain for Signal Pipeline v2. It replaces
the flat extract_facts chain with context-aware extraction that produces
surgical EntityPatch objects for all 11 BRD entity types.

The system prompt contains 3 injected layers:
  1. Entity inventory (IDs, names, statuses)
  2. Memory beliefs + insights + open questions
  3. Gap summary + extraction rules

Uses Anthropic tool_use for forced structured output (eliminates JSON parse
failures) and retries with exponential backoff on transient API errors.

Usage:
    from app.chains.extract_entity_patches import extract_entity_patches

    patches = await extract_entity_patches(
        signal_text=text,
        signal_type="requirements_doc",
        context_snapshot=snapshot,
        chunk_ids=["chunk-1", "chunk-2"],
    )
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from pydantic import ValidationError

from app.core.schemas_entity_patch import (
    BeliefImpact,
    EntityPatch,
    EntityPatchList,
    EvidenceRef,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Retry settings
# =============================================================================

_MAX_RETRIES = 2
_INITIAL_DELAY = 1.0


# =============================================================================
# Tool schema for forced structured output
# =============================================================================

EXTRACTION_TOOL = {
    "name": "submit_entity_patches",
    "description": "Submit the extracted entity patches from the signal.",
    "input_schema": {
        "type": "object",
        "properties": {
            "patches": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "operation": {
                            "type": "string",
                            "enum": ["create", "merge", "update", "stale", "delete"],
                        },
                        "entity_type": {
                            "type": "string",
                            "enum": [
                                "feature", "persona", "stakeholder", "workflow",
                                "workflow_step", "data_entity", "business_driver",
                                "constraint", "competitor", "vision",
                            ],
                        },
                        "target_entity_id": {
                            "type": "string",
                            "description": "Full UUID of existing entity for merge/update/stale/delete",
                        },
                        "payload": {"type": "object"},
                        "evidence": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "chunk_id": {"type": "string"},
                                    "quote": {"type": "string"},
                                    "page_or_section": {"type": "string"},
                                },
                                "required": ["quote"],
                            },
                        },
                        "confidence": {
                            "type": "string",
                            "enum": ["very_high", "high", "medium", "low"],
                        },
                        "confidence_reasoning": {"type": "string"},
                        "source_authority": {
                            "type": "string",
                            "enum": ["client", "consultant", "research", "prototype"],
                        },
                        "mention_count": {"type": "integer"},
                        "belief_impact": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "belief_summary": {"type": "string"},
                                    "impact": {
                                        "type": "string",
                                        "enum": ["supports", "contradicts", "refines"],
                                    },
                                    "new_evidence": {"type": "string"},
                                },
                            },
                        },
                        "answers_question": {"type": "string"},
                    },
                    "required": ["operation", "entity_type", "payload", "confidence"],
                },
            },
        },
        "required": ["patches"],
    },
}


# =============================================================================
# System prompt template
# =============================================================================

EXTRACTION_SYSTEM_PROMPT_STATIC = """You are a senior requirements analyst extracting structured entity patches from project signals.

Your output is EntityPatch[] — surgical create/merge/update operations targeting specific BRD entities.

## RULES
1. Reference existing entity IDs for merge/update operations — NEVER create duplicates.
2. CRITICAL: Use the COMPLETE entity ID from the inventory (full UUID, e.g. "aeb74d67-0bee-4eaa-b25c-6957a724b484"). Never truncate IDs.
3. For each patch, note if it supports or contradicts a memory belief.
4. Flag any answers to open questions.
5. Prioritize extraction of entities that fill the identified gaps.
6. Every patch MUST have evidence quotes from the source text.
7. Set confidence based on: explicit statement (high) vs implied/inferred (medium) vs ambiguous (low).

## ENTITY TYPES & FIELDS

### feature
create: {{name, overview, priority_group (must_have|should_have|could_have|out_of_scope), category, is_mvp}}
merge/update: any subset of above fields

### persona
create: {{name, role, goals (list), pain_points (list)}}
merge/update: append to goals/pain_points, update role

### stakeholder
create: {{name, first_name, last_name, role, stakeholder_type (champion|sponsor|blocker|influencer|end_user), influence_level (high|medium|low), domain_expertise}}
merge/update: any subset

### workflow
create: {{name, description}}
merge/update: description update

### workflow_step
create: {{label, description, workflow_name, state_type (current|future), time_minutes, pain_description, benefit_description, automation_level (manual|semi_automated|fully_automated), operation_type}}
merge/update: any subset
NOTE: Current-state steps should default to "manual". Future-state steps should default to "semi_automated" or "fully_automated" — only use "manual" for future steps that truly remain manual.

### data_entity
create: {{name, entity_category (domain|reference|transactional|analytical), fields (list of {{name, type, required, description}})}}
merge/update: append fields, update category

### business_driver
create: {{title (10 words max — punchy summary), description, driver_type (pain|goal|kpi), business_impact, affected_users, measurement, baseline_value, target_value}}
merge/update: any subset

### constraint
create: {{title, constraint_type (technical|compliance|business|integration), description}}
merge/update: update description

### competitor
create: {{name, reference_type (competitor|design_inspiration|feature_inspiration), relevance_description}}
merge/update: update relevance

### vision
update: {{statement}} — single vision statement for the project

## CONFIDENCE LEVELS
- very_high: Explicit, unambiguous statement with specific details
- high: Clear requirement but may lack some specifics
- medium: Implied or inferred from context
- low: Ambiguous, could be interpreted differently

## OPERATIONS
- create: New entity not matching any existing
- merge: Add evidence/data to existing entity (use target_entity_id from inventory)
- update: Change specific fields on existing entity (use target_entity_id)
- stale: New signal contradicts existing entity
- delete: Signal explicitly removes/cancels something

## KEY EXTRACTION RULES
- Business requirements (BRs) = BOTH a feature AND a workflow_step
- Named processes = workflow with multiple steps (3-8 per process)
- Current vs future: "Today we..." → current steps, "System will..." → future steps
- Stakeholders are INDIVIDUAL PEOPLE only, never organizations
- Data entities are domain objects (Patient, Invoice, Order), not generic "data"
- Business drivers: ONE entity per distinct pain/goal/KPI. If the same pain is discussed from different angles, that's one business_driver with richer evidence, not multiple. Phase milestones (Phase 1, Phase 2, Phase 3) can be separate goal entities.
- Competitors: Extract ALL named products, tools, or platforms (even if just mentioned in passing) as competitor entities. Include generic AI tools (ChatGPT, Jasper, etc.) and design inspirations (Canva, etc.).
- Workflows MUST include a parent workflow entity (create) plus its workflow_steps. Never create orphaned workflow_steps without a workflow_name that ties them to a parent.
- Feature granularity: Sub-capabilities of a larger feature should be merge patches on the parent, not separate creates. E.g., "Image Selection" and "Image Regeneration" are not separate features — they're aspects of the visual generation feature.
"""

EXTRACTION_CONTEXT_TEMPLATE = """{strategy_block}

## CONTEXT

{entity_inventory}

{memory}

{gaps}"""


# =============================================================================
# Strategy blocks per source type
# =============================================================================

STRATEGY_BLOCKS = {
    "requirements_doc": """## SOURCE-SPECIFIC: Requirements Document
- Extract ALL named processes as workflows with 3-8 steps each
- Every business requirement becomes BOTH a feature AND a workflow_step
- High entity volume expected — be comprehensive
- Default source_authority: check triage metadata, usually "client"
""",
    "meeting_transcript": """## SOURCE-SPECIFIC: Meeting Transcript
- Map speakers to stakeholders where possible
- Extract decisions and action items as business_drivers or features
- Conversation context matters — same topic discussed = merge, not create
- Default source_authority: "consultant" unless client speaker identified
""",
    "meeting_notes": """## SOURCE-SPECIFIC: Meeting Notes
- Lightweight extraction — focus on decisions and key facts
- High consultant authority
- Default source_authority: "consultant"
""",
    "chat_messages": """## SOURCE-SPECIFIC: Chat Messages
- Micro-extraction — only explicit requirements or decisions
- Ignore casual conversation, greetings, clarifying questions
- Default source_authority: "consultant"
""",
    "email": """## SOURCE-SPECIFIC: Email Thread
- Parse sender/recipients for stakeholder identification
- Decisions and approvals are high-confidence
- Default source_authority: based on sender
""",
    "prototype_review": """## SOURCE-SPECIFIC: Prototype Review
- Feature confirmations/rejections from review verdicts
- Client ratings = confirmed_client authority
- New UI requirements from feedback
- Default source_authority: "prototype"
""",
    "research": """## SOURCE-SPECIFIC: Research/Discovery
- Competitor intel and market data
- Never confirmed_client — always ai_generated
- Default source_authority: "research"
""",
    "presentation": """## SOURCE-SPECIFIC: Presentation (PPTX)
- Slide-by-slide structure — each slide may cover different entities
- Executive narrative — extract vision, goals, KPIs
- Default source_authority: based on presenter
""",
    "document": """## SOURCE-SPECIFIC: Document (Requirements / Discovery Notes)
- Extract ALL named processes as workflows with 3-8 steps each
- Every workflow MUST include the parent workflow entity AND its steps
- Capture ALL named products, tools, and platforms as competitors
- Business drivers should be consolidated — one entity per distinct pain/goal/kpi, not one per mention
- High entity volume expected — be thorough across all entity types
- Default source_authority: "consultant"
""",
    "default": """## SOURCE-SPECIFIC: General Signal
- Extract all recognizable requirements and entities
- Use medium confidence for inferred items
- Default source_authority: "research"
""",
}


# =============================================================================
# Main extraction function
# =============================================================================


async def extract_entity_patches(
    signal_text: str,
    signal_type: str,
    context_snapshot: Any,  # ContextSnapshot from context_snapshot.py
    chunk_ids: list[str] | None = None,
    source_authority: str = "research",
    signal_id: str | None = None,
    run_id: str | None = None,
    extraction_log: Any | None = None,  # ExtractionLog instance
) -> EntityPatchList:
    """Extract EntityPatch[] from signal text using Sonnet with 3-layer context.

    Args:
        signal_text: Raw signal content (may be truncated)
        signal_type: Source type key for strategy selection
        context_snapshot: ContextSnapshot with 3 pre-rendered prompt layers
        chunk_ids: Chunk IDs for evidence references
        source_authority: Default authority for patches
        signal_id: Signal UUID for tracking
        run_id: Run UUID for tracking

    Returns:
        EntityPatchList with parsed patches
    """
    start = time.time()

    # Build system prompt with 3-layer context (static part cached, dynamic part not)
    strategy_key = signal_type if signal_type in STRATEGY_BLOCKS else "default"
    strategy_block = STRATEGY_BLOCKS[strategy_key]

    dynamic_context = EXTRACTION_CONTEXT_TEMPLATE.format(
        strategy_block=strategy_block,
        entity_inventory=getattr(context_snapshot, "entity_inventory_prompt", "No entity inventory available."),
        memory=getattr(context_snapshot, "memory_prompt", "No memory available."),
        gaps=getattr(context_snapshot, "gaps_prompt", "No gap analysis available."),
    )

    system_blocks = [
        {
            "type": "text",
            "text": EXTRACTION_SYSTEM_PROMPT_STATIC,
            "cache_control": {"type": "ephemeral"},
        },
    ]

    # Layer 4: Extraction briefing (Haiku-synthesized guidance)
    briefing_text = getattr(context_snapshot, "extraction_briefing_prompt", "")
    if briefing_text:
        system_blocks.append({
            "type": "text",
            "text": briefing_text,
            "cache_control": {"type": "ephemeral"},
        })

    system_blocks.append({
        "type": "text",
        "text": dynamic_context,
    })

    user_prompt = f"""## Signal Content ({signal_type})

{signal_text[:12000]}

## Task
Extract all EntityPatch objects from this signal. Use the submit_entity_patches tool."""

    # Call LLM
    try:
        patch_dicts = await _call_extraction_llm(system_blocks, user_prompt)

        # Log single-chunk result before validation
        if extraction_log is not None:
            extraction_log.log_chunk_result(
                chunk_id=chunk_ids[0] if chunk_ids else "single",
                chunk_index=0,
                section_title=None,
                char_count=len(signal_text),
                raw_patches=patch_dicts,
            )

        patches = _validate_patches(patch_dicts, chunk_ids, source_authority)
    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        patches = []

    duration_ms = int((time.time() - start) * 1000)

    return EntityPatchList(
        patches=patches,
        signal_id=signal_id,
        run_id=run_id,
        extraction_model="claude-sonnet-4-6",
        extraction_duration_ms=duration_ms,
    )


# =============================================================================
# LLM call with tool_use + retry
# =============================================================================


async def _call_extraction_llm(system_blocks: list[dict], user_prompt: str) -> list[dict]:
    """Call Sonnet for extraction using tool_use for structured output.

    Uses Anthropic tool_use with forced tool_choice to guarantee structured
    JSON output matching the EXTRACTION_TOOL schema. Retries up to
    _MAX_RETRIES times with exponential backoff on transient API errors.

    Args:
        system_blocks: List of content blocks (with cache_control on static part).
        user_prompt: User message with signal content.

    Returns:
        List of raw patch dicts (schema-validated by Anthropic API).
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

    last_error: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=16000,
                system=system_blocks,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=0.1,
                tools=[EXTRACTION_TOOL],
                tool_choice={"type": "tool", "name": "submit_entity_patches"},
            )

            # Warn if response was truncated — patches will be incomplete/empty
            if response.stop_reason == "max_tokens":
                logger.warning(
                    f"Extraction response truncated (max_tokens). "
                    f"Output tokens used: {response.usage.output_tokens}. "
                    f"Patches may be incomplete."
                )

            # Extract tool input from response
            for block in response.content:
                if block.type == "tool_use":
                    data = block.input
                    patches_raw = data.get("patches", [])
                    # Handle case where API returns patches as a JSON string
                    if isinstance(patches_raw, str):
                        try:
                            patches_raw = json.loads(patches_raw)
                        except json.JSONDecodeError:
                            logger.error("Failed to parse patches string as JSON")
                            patches_raw = []
                    return patches_raw

            # Fallback: parse text if no tool_use block (shouldn't happen)
            logger.warning("No tool_use block in extraction response, falling back to text")
            for block in response.content:
                if hasattr(block, "text"):
                    return _parse_text_fallback(block.text)
            return []

        except (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError) as e:
            last_error = e
            if attempt < _MAX_RETRIES:
                delay = _INITIAL_DELAY * (2 ** attempt)
                logger.warning(
                    f"Extraction LLM attempt {attempt + 1}/{_MAX_RETRIES + 1} failed "
                    f"({type(e).__name__}), retrying in {delay}s"
                )
                await asyncio.sleep(delay)
            else:
                raise

    raise last_error  # unreachable but satisfies type checker


# =============================================================================
# Parse + validate
# =============================================================================


def _parse_text_fallback(raw: str) -> list[dict]:
    """Parse JSON from raw text output. Fallback only — tool_use is the primary path."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Text fallback JSON parse failed: {e}")
        return []

    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "patches" in data:
        return data["patches"]
    return [data] if isinstance(data, dict) else []


def _validate_patches(
    patch_dicts: list[dict],
    chunk_ids: list[str] | None,
    default_authority: str,
) -> list[EntityPatch]:
    """Validate raw patch dicts into EntityPatch objects."""
    patches = []
    for item in patch_dicts:
        try:
            # Normalize evidence chunk_ids if not provided by LLM
            evidence = item.get("evidence", [])
            if evidence and chunk_ids:
                for ev in evidence:
                    if not ev.get("chunk_id") or ev["chunk_id"] == "...":
                        ev["chunk_id"] = chunk_ids[0] if chunk_ids else "unknown"

            # Default source_authority
            if not item.get("source_authority"):
                item["source_authority"] = default_authority

            patch = EntityPatch(**item)
            patches.append(patch)
        except (ValidationError, Exception) as e:
            logger.warning(f"Failed to validate patch: {e}")
            logger.debug(f"Raw patch: {item}")

    return patches


# =============================================================================
# Parallel chunk extraction (map-reduce)
# =============================================================================

CHUNK_SYSTEM_PROMPT = """You are extracting structured entity patches from ONE SECTION of a larger document.

Focus on entities clearly present in THIS chunk. Another pass will merge duplicates across chunks.

IMPORTANT per-chunk rules:
- Extract ALL named products, tools, platforms as competitors — even brief mentions
- Create workflow entities WITH their steps (use workflow_name on steps to link them)
- Business drivers: one entity per distinct pain/goal/KPI — don't split the same concept into multiple entities
- If this chunk discusses an existing feature from the inventory, use merge/update, not create

If a section title is provided, use it as page_or_section in evidence references."""

_CHUNK_MODEL = "claude-haiku-4-5-20251001"


async def _extract_single_chunk(
    chunk_content: str,
    chunk_id: str,
    chunk_index: int,
    section_title: str | None,
    signal_type: str,
    context_snapshot: Any,
    source_authority: str,
    client: Any,  # AsyncAnthropic
) -> list[dict]:
    """Extract patches from a single chunk using Haiku.

    Args:
        chunk_content: Raw text of this chunk
        chunk_id: UUID of the chunk for evidence refs
        chunk_index: Position in the document
        section_title: Section heading (if available)
        signal_type: Source type for strategy selection
        context_snapshot: ContextSnapshot with entity inventory
        source_authority: Default authority
        client: Shared AsyncAnthropic client

    Returns:
        List of raw patch dicts from this chunk
    """
    strategy_key = signal_type if signal_type in STRATEGY_BLOCKS else "default"
    strategy_block = STRATEGY_BLOCKS[strategy_key]

    dynamic_context = EXTRACTION_CONTEXT_TEMPLATE.format(
        strategy_block=strategy_block,
        entity_inventory=getattr(context_snapshot, "entity_inventory_prompt", "No entity inventory available."),
        memory=getattr(context_snapshot, "memory_prompt", "No memory available."),
        gaps=getattr(context_snapshot, "gaps_prompt", "No gap analysis available."),
    )

    system_blocks = [
        {
            "type": "text",
            "text": EXTRACTION_SYSTEM_PROMPT_STATIC,
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": CHUNK_SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        },
    ]

    # Layer 4: Extraction briefing (same across all chunks → cached)
    briefing_text = getattr(context_snapshot, "extraction_briefing_prompt", "")
    if briefing_text:
        system_blocks.append({
            "type": "text",
            "text": briefing_text,
            "cache_control": {"type": "ephemeral"},
        })

    system_blocks.append({
        "type": "text",
        "text": dynamic_context,
        "cache_control": {"type": "ephemeral"},
    })

    section_ctx = f" (Section: {section_title})" if section_title else ""
    user_prompt = f"""## Document Chunk {chunk_index + 1}{section_ctx}

{chunk_content}

## Task
Extract all EntityPatch objects from this chunk. Use the submit_entity_patches tool."""

    from anthropic import (
        APIConnectionError,
        APITimeoutError,
        InternalServerError,
        RateLimitError,
    )

    last_error: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = await client.messages.create(
                model=_CHUNK_MODEL,
                max_tokens=8000,
                system=system_blocks,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=0.1,
                tools=[EXTRACTION_TOOL],
                tool_choice={"type": "tool", "name": "submit_entity_patches"},
            )

            if response.stop_reason == "max_tokens":
                logger.warning(
                    f"Chunk {chunk_index} extraction truncated (max_tokens). "
                    f"Output tokens: {response.usage.output_tokens}"
                )

            for block in response.content:
                if block.type == "tool_use":
                    patches_raw = block.input.get("patches", [])
                    # Handle API returning patches as JSON string
                    if isinstance(patches_raw, str):
                        try:
                            patches_raw = json.loads(patches_raw)
                        except json.JSONDecodeError:
                            logger.error(f"Chunk {chunk_index}: failed to parse patches string")
                            patches_raw = []
                    # Inject chunk_id into evidence refs
                    for patch in patches_raw:
                        for ev in patch.get("evidence", []):
                            if not ev.get("chunk_id") or ev["chunk_id"] == "...":
                                ev["chunk_id"] = chunk_id
                    return patches_raw

            logger.warning(f"Chunk {chunk_index}: no tool_use block in response")
            return []

        except (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError) as e:
            last_error = e
            if attempt < _MAX_RETRIES:
                delay = _INITIAL_DELAY * (2 ** attempt)
                logger.warning(
                    f"Chunk {chunk_index} attempt {attempt + 1}/{_MAX_RETRIES + 1} failed "
                    f"({type(e).__name__}), retrying in {delay}s"
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"Chunk {chunk_index} extraction failed after retries: {last_error}")
                return []

    return []


def _merge_duplicate_patches(
    patches: list[EntityPatch],
) -> tuple[list[EntityPatch], list[dict]]:
    """Merge duplicate create patches that refer to the same entity across chunks.

    Groups create patches by (entity_type, normalized_name) and merges duplicates:
    - Keeps the patch with highest confidence
    - Merges evidence lists from all duplicates
    - Sums mention_counts
    - Merges belief_impacts

    Non-create patches (merge/update/stale/delete) are kept as-is since they
    reference target_entity_id.

    Returns:
        Tuple of (merged patches, merge decisions for logging)
    """
    CONFIDENCE_ORDER = {"very_high": 4, "high": 3, "medium": 2, "low": 1, "conflict": 0}

    creates: dict[tuple[str, str], list[EntityPatch]] = {}
    non_creates: list[EntityPatch] = []

    for patch in patches:
        if patch.operation != "create":
            non_creates.append(patch)
            continue

        # Normalize name for dedup
        name = (
            patch.payload.get("name")
            or patch.payload.get("label")
            or patch.payload.get("title")
            or ""
        )
        # For business_drivers, build a more stable key from driver_type + description
        if not name and patch.entity_type == "business_driver":
            driver_type = patch.payload.get("driver_type", "")
            desc = patch.payload.get("description", "")[:50]
            name = f"{driver_type}:{desc}" if desc else ""
        elif not name:
            name = patch.payload.get("description", "")[:60]
        key = (patch.entity_type, name.lower().strip() if name else "")

        if not key[1]:
            # Can't deduplicate without a name — keep as-is
            non_creates.append(patch)
            continue

        creates.setdefault(key, []).append(patch)

    merged: list[EntityPatch] = []
    merge_decisions: list[dict] = []
    for (_etype, _name), group in creates.items():
        if len(group) == 1:
            merged.append(group[0])
            continue

        # Sort by confidence descending, pick best as base
        group.sort(key=lambda p: CONFIDENCE_ORDER.get(p.confidence, 0), reverse=True)
        best = group[0]

        # Merge evidence, mention_counts, belief_impacts from others
        all_evidence = list(best.evidence)
        total_mentions = best.mention_count
        all_beliefs = list(best.belief_impact)
        seen_quotes = {e.quote for e in all_evidence}

        for other in group[1:]:
            for ev in other.evidence:
                if ev.quote not in seen_quotes:
                    all_evidence.append(ev)
                    seen_quotes.add(ev.quote)
            total_mentions += other.mention_count
            all_beliefs.extend(other.belief_impact)

        merged.append(EntityPatch(
            operation=best.operation,
            entity_type=best.entity_type,
            target_entity_id=best.target_entity_id,
            payload=best.payload,
            evidence=all_evidence,
            confidence=best.confidence,
            confidence_reasoning=best.confidence_reasoning,
            belief_impact=all_beliefs,
            answers_question=best.answers_question,
            source_authority=best.source_authority,
            mention_count=total_mentions,
        ))

        merge_decisions.append({
            "name": _name,
            "entity_type": _etype,
            "duplicates_merged": len(group),
            "kept_confidence": best.confidence,
            "evidence_combined": len(all_evidence),
        })

        logger.debug(
            f"Merged {len(group)} duplicate '{_name}' ({_etype}) patches into one"
        )

    return merged + non_creates, merge_decisions


async def extract_patches_parallel(
    chunks: list[dict],
    signal_type: str,
    context_snapshot: Any,
    source_authority: str = "research",
    signal_id: str | None = None,
    run_id: str | None = None,
    extraction_log: Any | None = None,  # ExtractionLog instance
) -> EntityPatchList:
    """Extract patches from multiple chunks in parallel using Haiku.

    Fans out one Haiku call per chunk, merges and deduplicates results.

    Args:
        chunks: List of chunk dicts from list_signal_chunks()
        signal_type: Source type for strategy selection
        context_snapshot: ContextSnapshot with entity inventory
        source_authority: Default authority for patches
        signal_id: Signal UUID for tracking
        run_id: Run UUID for tracking

    Returns:
        EntityPatchList with merged, deduplicated patches
    """
    from anthropic import AsyncAnthropic

    from app.core.config import Settings

    start = time.time()
    settings = Settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Fan out parallel extraction
    tasks = [
        _extract_single_chunk(
            chunk_content=chunk.get("content", ""),
            chunk_id=str(chunk.get("id", "")),
            chunk_index=chunk.get("chunk_index", i),
            section_title=(chunk.get("metadata") or {}).get("section_title"),
            signal_type=signal_type,
            context_snapshot=context_snapshot,
            source_authority=source_authority,
            client=client,
        )
        for i, chunk in enumerate(chunks)
    ]

    logger.info(
        f"[parallel] Extracting from {len(tasks)} chunks using {_CHUNK_MODEL}",
        extra={"signal_id": signal_id},
    )

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Collect all raw patches, skipping exceptions
    all_patch_dicts: list[dict] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"[parallel] Chunk {i} raised: {result}")
            continue

        # Log per-chunk raw results
        if extraction_log is not None:
            chunk = chunks[i]
            extraction_log.log_chunk_result(
                chunk_id=str(chunk.get("id", "")),
                chunk_index=chunk.get("chunk_index", i),
                section_title=(chunk.get("metadata") or {}).get("section_title"),
                char_count=len(chunk.get("content", "")),
                raw_patches=result,
            )

        all_patch_dicts.extend(result)

    logger.info(
        f"[parallel] Collected {len(all_patch_dicts)} raw patches from {len(chunks)} chunks",
        extra={"signal_id": signal_id},
    )

    # Validate into EntityPatch objects
    # Pass chunk_ids=None since chunk_ids are already injected per-chunk
    patches = _validate_patches(all_patch_dicts, chunk_ids=None, default_authority=source_authority)

    # Deduplicate creates across chunks
    before_count = len(patches)
    patches, merge_decisions = _merge_duplicate_patches(patches)

    if extraction_log is not None:
        extraction_log.log_chunk_merge(before_count, patches, merge_decisions)

    # Consolidate semantically duplicate creates (LLM pass)
    try:
        from app.chains.consolidate_patches import consolidate_create_patches

        before_consolidation = len(patches)
        patches, consolidation_decisions = await consolidate_create_patches(patches)
        if extraction_log is not None:
            extraction_log.log_consolidation(before_consolidation, patches, consolidation_decisions)
        if consolidation_decisions:
            logger.info(
                f"[parallel] Consolidated {before_consolidation - len(patches)} duplicate creates"
            )
    except Exception as e:
        logger.warning(f"[parallel] Consolidation failed (continuing): {e}")

    duration_ms = int((time.time() - start) * 1000)

    logger.info(
        f"[parallel] Final: {len(patches)} patches after merge ({duration_ms}ms)",
        extra={"signal_id": signal_id},
    )

    return EntityPatchList(
        patches=patches,
        signal_id=signal_id,
        run_id=run_id,
        extraction_model=_CHUNK_MODEL,
        extraction_duration_ms=duration_ms,
    )
