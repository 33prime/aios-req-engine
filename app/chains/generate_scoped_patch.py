"""Scoped patch generator for surgical updates.

Generates constrained patches that can ONLY modify specific fields of specific entities.

Phase 1: Surgical Updates for Features
"""

from typing import Any
from uuid import UUID

from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.core.llm import get_llm
from app.core.logging import get_logger
from app.core.schemas_claims import Claim, ScopedPatch, ChangeClassification
from app.core.change_classifier import classify_change

logger = get_logger(__name__)


SCOPED_PATCH_SYSTEM_PROMPT = """You are a precision PRD patch generator with STRICT CONSTRAINTS.

# CRITICAL RULES
1. You may ONLY edit the entity specified: {entity_type} "{entity_name}" (ID: {entity_id})
2. You may ONLY modify these fields: {allowed_fields}
3. DO NOT create new entities
4. DO NOT edit other entities
5. DO NOT modify fields not in the allowed list
6. DO NOT hallucinate data - use only information from claims and current entity

# Your Task
Given claims about this entity, generate a JSON patch that:
- Merges claim information into the allowed fields
- Preserves existing confirmed data
- Is conservative and precise
- Includes evidence for each change

# Output Format
Return JSON with field updates:
```json
{
  "field_name": {
    "new_value": [...],
    "change_summary": "Added 2 acceptance criteria based on client call",
    "evidence_used": [
      {"chunk_id": "...", "excerpt": "...", "rationale": "..."}
    ]
  }
}
```

# Field Update Strategies

**For lists (e.g., acceptance_criteria, goals)**:
- Append new items if not duplicates
- Preserve all existing items unless claim explicitly contradicts
- Example: If current has [A, B] and claim adds C → result is [A, B, C]

**For text fields (e.g., description, role)**:
- Refine/enhance existing text
- Don't remove information unless claim contradicts
- Merge new details naturally

**For JSONB (e.g., demographics, psychographics)**:
- Merge new keys
- Update existing keys only if claim provides better data
- Don't delete keys unless claim explicitly says to

# Safety
- If claim contradicts existing data → note in change_summary but still apply (classifier will escalate)
- If unsure → be conservative, change less
- Document all changes clearly in change_summary
"""


SCOPED_PATCH_USER_PROMPT = """# Entity To Update
Type: {entity_type}
ID: {entity_id}
Name: {entity_name}
Confirmation Status: {confirmation_status}

# Current Entity State
{current_entity}

# Allowed Fields (YOU MAY ONLY MODIFY THESE)
{allowed_fields}

# Claims To Apply
{claims}

# Task
Generate a JSON patch that applies these claims to the allowed fields ONLY.
Be precise, conservative, and document your changes.

Return JSON patch."""


def generate_scoped_patch(
    entity_type: str,
    entity: dict[str, Any],
    claims: list[Claim],
    allowed_fields: list[str],
    run_id: UUID,
) -> ScopedPatch:
    """Generate a scoped patch for a single entity.

    Args:
        entity_type: Type of entity (feature, persona, prd_section, vp_step)
        entity: Current entity dict (must have id, name, and fields to update)
        claims: List of claims to apply to this entity
        allowed_fields: List of field names that can be modified
        run_id: Run tracking UUID

    Returns:
        ScopedPatch with changes, classification, and evidence

    Raises:
        Exception: If LLM call fails or entity missing required fields
    """
    entity_id = UUID(entity["id"])
    entity_name = entity.get("name") or entity.get("label") or "Unknown"
    confirmation_status = entity.get("confirmation_status", "ai_generated")

    logger.info(
        f"Generating scoped patch for {entity_type} '{entity_name}'",
        extra={
            "run_id": str(run_id),
            "entity_id": str(entity_id),
            "claims_count": len(claims),
            "allowed_fields": allowed_fields,
        },
    )

    # Format current entity for prompt
    current_entity_str = _format_entity_for_prompt(entity, allowed_fields)

    # Format claims for prompt
    claims_str = "\n".join([
        f"{i+1}. [{c.polarity}] {c.claim}\n"
        f"   Field: {c.target.field}\n"
        f"   Confidence: {c.confidence:.2f}\n"
        f"   Evidence: {c.evidence.get('excerpt', '')[:200]}\n"
        f"   Rationale: {c.rationale}"
        for i, c in enumerate(claims)
    ])

    # Build prompt
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(
            content=SCOPED_PATCH_SYSTEM_PROMPT.format(
                entity_type=entity_type,
                entity_name=entity_name,
                entity_id=entity_id,
                allowed_fields=", ".join(allowed_fields),
            )
        ),
        ("user", SCOPED_PATCH_USER_PROMPT),
    ])

    # Create chain
    llm = get_llm(model="gpt-4o", temperature=0.1)
    parser = JsonOutputParser()
    chain = prompt | llm | parser

    try:
        # Invoke LLM
        patch_result = chain.invoke({
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "entity_name": entity_name,
            "confirmation_status": confirmation_status,
            "current_entity": current_entity_str,
            "allowed_fields": ", ".join(allowed_fields),
            "claims": claims_str,
        })

        # Parse patch and classify each field change
        changes: dict[str, Any] = {}
        change_summaries: list[str] = []
        all_evidence: list[dict[str, Any]] = []

        for field_name, field_update in patch_result.items():
            if field_name not in allowed_fields:
                logger.warning(
                    f"LLM tried to modify disallowed field '{field_name}', skipping",
                    extra={"entity_name": entity_name},
                )
                continue

            new_value = field_update.get("new_value")
            change_summary = field_update.get("change_summary", "")
            evidence_used = field_update.get("evidence_used", [])

            # Store change
            changes[field_name] = new_value
            change_summaries.append(f"{field_name}: {change_summary}")
            all_evidence.extend(evidence_used)

        # Overall change summary
        overall_summary = "; ".join(change_summaries) if change_summaries else "No changes"

        # Classify the overall patch
        # For simplicity, use the first changed field for classification
        # In practice, you might classify each field separately
        old_values = {field: entity.get(field) for field in changes.keys()}
        classification = _classify_patch_changes(
            old_values,
            changes,
            entity_type,
            entity_name,
            entity,
            claims,
            run_id,
        )

        # Build ScopedPatch
        patch = ScopedPatch(
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            allowed_fields=allowed_fields,
            changes=changes,
            change_summary=overall_summary,
            evidence=all_evidence,
            classification=classification,
            claims=claims,
        )

        logger.info(
            f"Generated patch for {entity_type} '{entity_name}': {len(changes)} field(s) modified",
            extra={
                "run_id": str(run_id),
                "entity_id": str(entity_id),
                "auto_apply_ok": classification.auto_apply_ok,
            },
        )

        return patch

    except Exception as e:
        logger.error(
            f"Failed to generate patch for {entity_type} '{entity_name}': {e}",
            extra={"run_id": str(run_id), "entity_id": str(entity_id)},
        )
        raise


def _format_entity_for_prompt(entity: dict[str, Any], allowed_fields: list[str]) -> str:
    """Format entity for LLM prompt, showing only allowed fields."""
    lines = []
    for field in allowed_fields:
        value = entity.get(field)
        if value is not None:
            # Truncate long values
            value_str = str(value)
            if len(value_str) > 500:
                value_str = value_str[:500] + "... (truncated)"
            lines.append(f"{field}: {value_str}")
        else:
            lines.append(f"{field}: (empty)")

    return "\n".join(lines)


def _classify_patch_changes(
    old_values: dict[str, Any],
    new_values: dict[str, Any],
    entity_type: str,
    entity_name: str,
    entity: dict[str, Any],
    claims: list[Claim],
    run_id: UUID,
) -> ChangeClassification:
    """Classify the changes in a patch.

    For multi-field patches, uses the most conservative classification.
    """
    classifications: list[ChangeClassification] = []

    for field_name in new_values.keys():
        old_value = old_values.get(field_name)
        new_value = new_values[field_name]

        # Classify this field change
        classification = classify_change(
            old_value=old_value,
            new_value=new_value,
            field_name=field_name,
            entity_type=entity_type,
            entity_name=entity_name,
            entity_metadata=entity,
            claims=claims,
            run_id=run_id,
        )
        classifications.append(classification)

    # Use most conservative classification (prefer escalate over auto-apply)
    if any(not c.auto_apply_ok for c in classifications):
        # Find the most severe escalation
        escalations = [c for c in classifications if not c.auto_apply_ok]
        return max(escalations, key=lambda c: _severity_rank(c.severity))
    else:
        # All auto-apply OK, return the highest severity one
        return max(classifications, key=lambda c: _severity_rank(c.severity))


def _severity_rank(severity: str) -> int:
    """Rank severity for comparison."""
    ranks = {"minor": 1, "moderate": 2, "major": 3}
    return ranks.get(severity, 0)
