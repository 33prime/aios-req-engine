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

EXTRACTION_SYSTEM_PROMPT = """You are a senior requirements analyst extracting structured entity patches from project signals.

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
create: {{label, description, workflow_name, state_type (current|future), time_minutes, pain_description, benefit_description, automation_level (manual|semi_automated|automated), operation_type}}
merge/update: any subset

### data_entity
create: {{name, entity_category (domain|reference|transactional|analytical), fields (list of {{name, type, required, description}})}}
merge/update: append fields, update category

### business_driver
create: {{description, driver_type (pain|goal|kpi), business_impact, affected_users, measurement, baseline_value, target_value}}
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

{strategy_block}

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

    # Build system prompt with 3-layer context
    strategy_key = signal_type if signal_type in STRATEGY_BLOCKS else "default"
    strategy_block = STRATEGY_BLOCKS[strategy_key]

    system_prompt = EXTRACTION_SYSTEM_PROMPT.format(
        strategy_block=strategy_block,
        entity_inventory=getattr(context_snapshot, "entity_inventory_prompt", "No entity inventory available."),
        memory=getattr(context_snapshot, "memory_prompt", "No memory available."),
        gaps=getattr(context_snapshot, "gaps_prompt", "No gap analysis available."),
    )

    user_prompt = f"""## Signal Content ({signal_type})

{signal_text[:12000]}

## Task
Extract all EntityPatch objects from this signal. Use the submit_entity_patches tool."""

    # Call LLM
    try:
        patch_dicts = await _call_extraction_llm(system_prompt, user_prompt)
        patches = _validate_patches(patch_dicts, chunk_ids, source_authority)
    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        patches = []

    duration_ms = int((time.time() - start) * 1000)

    return EntityPatchList(
        patches=patches,
        signal_id=signal_id,
        run_id=run_id,
        extraction_model="claude-sonnet-4-5-20250929",
        extraction_duration_ms=duration_ms,
    )


# =============================================================================
# LLM call with tool_use + retry
# =============================================================================


async def _call_extraction_llm(system_prompt: str, user_prompt: str) -> list[dict]:
    """Call Sonnet for extraction using tool_use for structured output.

    Uses Anthropic tool_use with forced tool_choice to guarantee structured
    JSON output matching the EXTRACTION_TOOL schema. Retries up to
    _MAX_RETRIES times with exponential backoff on transient API errors.

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
                model="claude-sonnet-4-5-20250929",
                max_tokens=8000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=0.1,
                tools=[EXTRACTION_TOOL],
                tool_choice={"type": "tool", "name": "submit_entity_patches"},
            )

            # Extract tool input from response
            for block in response.content:
                if block.type == "tool_use":
                    data = block.input
                    return data.get("patches", [])

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
