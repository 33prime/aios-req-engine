"""Extract EntityPatch[] from signal content using Sonnet with 3-layer context.

This is the core extraction chain for Signal Pipeline v2. It replaces
the flat extract_facts chain with context-aware extraction that produces
surgical EntityPatch objects for all 11 BRD entity types.

The system prompt contains 3 injected layers:
  1. Entity inventory (IDs, names, statuses)
  2. Memory beliefs + insights + open questions
  3. Gap summary + extraction rules

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
# System prompt template
# =============================================================================

EXTRACTION_SYSTEM_PROMPT = """You are a senior requirements analyst extracting structured entity patches from project signals.

Your output is EntityPatch[] — surgical create/merge/update operations targeting specific BRD entities.

## RULES
1. Reference existing entity IDs for merge/update operations — NEVER create duplicates.
2. For each patch, note if it supports or contradicts a memory belief.
3. Flag any answers to open questions.
4. Prioritize extraction of entities that fill the identified gaps.
5. Every patch MUST have evidence quotes from the source text.
6. Set confidence based on: explicit statement (high) vs implied/inferred (medium) vs ambiguous (low).

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
create: {{name, constraint_type (technical|compliance|business|integration), description}}
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

{gaps}

## OUTPUT FORMAT
Return a JSON array of EntityPatch objects:
```json
[
  {{
    "operation": "create|merge|update|stale|delete",
    "entity_type": "feature|persona|stakeholder|workflow|workflow_step|data_entity|business_driver|constraint|competitor|vision",
    "target_entity_id": "existing-id or null for create",
    "payload": {{}},
    "evidence": [{{"chunk_id": "...", "quote": "exact text from source", "page_or_section": "optional"}}],
    "confidence": "very_high|high|medium|low",
    "confidence_reasoning": "why this confidence level",
    "source_authority": "client|consultant|research|prototype",
    "mention_count": 1,
    "belief_impact": [{{"belief_summary": "...", "impact": "supports|contradicts|refines", "new_evidence": "..."}}],
    "answers_question": "open-question-id or null"
  }}
]
```"""


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
Extract all EntityPatch objects from this signal. Return JSON array only."""

    # Call LLM
    try:
        raw_output = await _call_extraction_llm(system_prompt, user_prompt)
        patches = _parse_patches(raw_output, chunk_ids, source_authority)
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
# LLM call
# =============================================================================


async def _call_extraction_llm(system_prompt: str, user_prompt: str) -> str:
    """Call Sonnet for extraction. Returns raw JSON string."""
    from anthropic import AsyncAnthropic

    from app.core.config import Settings

    settings = Settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    response = await client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=8000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        temperature=0.1,
    )

    return response.content[0].text


# =============================================================================
# Parse + validate
# =============================================================================


def _parse_patches(
    raw_output: str,
    chunk_ids: list[str] | None,
    default_authority: str,
) -> list[EntityPatch]:
    """Parse LLM output into validated EntityPatch list."""
    # Extract JSON from potential markdown code blocks
    text = raw_output.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (```json and ```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse failed: {e}")
        logger.debug(f"Raw output: {text[:500]}")
        return []

    if not isinstance(data, list):
        # Maybe wrapped in an object
        if isinstance(data, dict) and "patches" in data:
            data = data["patches"]
        else:
            data = [data]

    patches = []
    for item in data:
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
            logger.warning(f"Failed to parse patch: {e}")
            logger.debug(f"Raw patch: {item}")

    return patches
