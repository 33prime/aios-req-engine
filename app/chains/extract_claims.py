"""Claim extraction chain for surgical updates.

Extracts atomic, routed claims from signals that map to specific entities.

Phase 1: Surgical Updates for Features
"""

from typing import Any
from uuid import UUID

from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.core.llm import get_llm
from app.core.logging import get_logger
from app.core.schemas_claims import Claim, CanonicalIndex

logger = get_logger(__name__)


CLAIM_EXTRACTION_SYSTEM_PROMPT = """You are a precision requirements analyst extracting atomic claims from user signals.

Your task is to identify specific, actionable claims about product entities and route them correctly.

# Input
- Signal text (from meeting transcript, email, document, etc.)
- Canonical index of existing entities (features, personas, PRD sections, VP steps)

# Your Job
Extract atomic claims that:
1. Are specific and actionable (not vague observations)
2. Map to a specific entity and field
3. Can be verified with evidence from the signal
4. Are routed to the correct existing entity (or propose a new one)

# Claim Types
- **update**: Modify existing entity field (e.g., add acceptance criteria to Feature X)
- **propose_new_object**: Suggests creating a new entity (e.g., new persona, new feature)

# Polarity
- **supports**: Adds new information that doesn't conflict
- **contradicts**: Conflicts with existing data (requires review)
- **refines**: Improves/clarifies existing data without contradiction

# Entity Routing
- Match claims to existing entities by name, role, or context
- If no match found and claim suggests new entity → action: "propose_new_object"
- Be conservative: only route to entity if confidence > 0.7

# Output Format
Return JSON array of claims:
```json
[
  {
    "claim": "Survey Builder needs data validation for text inputs",
    "target": {"type": "feature", "id": "<feature-uuid>", "field": "acceptance_criteria"},
    "polarity": "supports",
    "confidence": 0.9,
    "evidence": {
      "chunk_id": "<chunk-uuid>",
      "signal_id": "<signal-uuid>",
      "excerpt": "We need to validate that survey text answers aren't empty...",
      "rationale": "Explicit requirement stated by client"
    },
    "action": "update",
    "rationale": "Adding new acceptance criterion for validation"
  }
]
```

# Critical Rules
- Extract ONLY claims with clear evidence from the signal
- Route to existing entities when possible (check names carefully)
- Propose new entities ONLY when signal explicitly describes something new
- Set confidence based on clarity of signal + routing certainty
- Each claim must be atomic (one change to one field)
"""


CLAIM_EXTRACTION_USER_PROMPT = """# Signal Content
{signal_text}

# Canonical Index
## Features
{features_list}

## Personas
{personas_list}

## Value Path Steps
{vp_steps_list}

# Task
Extract all atomic claims from this signal that map to existing entities or propose new ones.
Focus on actionable updates to features, personas, or VP steps.

Return JSON array of claims."""


def extract_claims_from_signal(
    signal: dict[str, Any],
    canonical_index: CanonicalIndex,
    run_id: UUID,
) -> list[Claim]:
    """Extract atomic claims from a signal using the canonical index for routing.

    Args:
        signal: Signal dict with id, raw_text, signal_type, etc.
        canonical_index: Index of all entities for routing
        run_id: Run tracking UUID

    Returns:
        List of extracted claims with routing and evidence

    Raises:
        Exception: If LLM call fails
    """
    signal_id = signal["id"]
    signal_text = signal["raw_text"]
    signal_type = signal.get("signal_type", "note")

    logger.info(
        f"Extracting claims from signal {signal_id} ({signal_type})",
        extra={"run_id": str(run_id), "signal_id": signal_id},
    )

    # Format canonical index for prompt
    features_list = _format_entities_for_prompt(canonical_index.features)
    personas_list = _format_entities_for_prompt(canonical_index.personas)
    vp_steps_list = _format_entities_for_prompt(canonical_index.vp_steps)

    # Build prompt
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=CLAIM_EXTRACTION_SYSTEM_PROMPT),
        ("user", CLAIM_EXTRACTION_USER_PROMPT),
    ])

    # Create chain
    llm = get_llm(model="gpt-4o", temperature=0.1)
    parser = JsonOutputParser()
    chain = prompt | llm | parser

    try:
        # Invoke LLM
        result = chain.invoke({
            "signal_text": signal_text,
            "features_list": features_list,
            "personas_list": personas_list,
            "vp_steps_list": vp_steps_list,
        })

        # Parse claims
        claims = []
        for claim_dict in result:
            # Add signal metadata to evidence
            if "evidence" in claim_dict and isinstance(claim_dict["evidence"], dict):
                claim_dict["evidence"]["signal_id"] = signal_id
                claim_dict["evidence"]["signal_type"] = signal_type

            # Parse into Claim model
            claim = Claim(**claim_dict)
            claims.append(claim)

        logger.info(
            f"Extracted {len(claims)} claims from signal {signal_id}",
            extra={
                "run_id": str(run_id),
                "signal_id": signal_id,
                "claims_count": len(claims),
            },
        )

        return claims

    except Exception as e:
        logger.error(
            f"Failed to extract claims from signal {signal_id}: {e}",
            extra={"run_id": str(run_id), "signal_id": signal_id},
        )
        raise


def _format_entities_for_prompt(entities: list[Any]) -> str:
    """Format entity list for LLM prompt.

    Args:
        entities: List of CanonicalEntity objects

    Returns:
        Formatted string for prompt
    """
    if not entities:
        return "(none)"

    lines = []
    for entity in entities:
        context_snippet = f" - {entity.context[:100]}" if entity.context else ""
        slug_info = f" (slug: {entity.slug})" if entity.slug else ""
        confirmation_badge = (
            f" [{entity.confirmation_status}]"
            if entity.confirmation_status != "ai_generated"
            else ""
        )

        lines.append(
            f"- ID: {entity.id} | Name: {entity.name}{slug_info}{confirmation_badge}{context_snippet}"
        )

    return "\n".join(lines)
