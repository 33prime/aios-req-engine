"""Change classifier for surgical updates.

Classifies proposed changes as auto-apply vs. escalate based on rules and LLM analysis.

Phase 1: Surgical Updates for Features
"""

from typing import Any
from uuid import UUID

from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.core.llm import get_llm
from app.core.logging import get_logger
from app.core.schemas_claims import ChangeClassification, Claim

logger = get_logger(__name__)


# =========================
# Structural Rules (Fast)
# =========================


def _apply_structural_rules(
    old_value: Any,
    new_value: Any,
    entity_type: str,
    entity_metadata: dict[str, Any],
    claims: list[Claim],
) -> ChangeClassification | None:
    """Apply fast structural rules to classify changes.

    Returns ChangeClassification if rules definitively classify, else None (needs LLM).
    """
    confirmation_status = entity_metadata.get("confirmation_status", "ai_generated")

    # Rule 1: Any change to confirmed_client entity → escalate
    if confirmation_status == "confirmed_client":
        return ChangeClassification(
            change_type="structural",
            severity="major",
            auto_apply_ok=False,
            rationale="Entity has confirmation_status=confirmed_client, requires review for any changes",
            evidence=[claim.evidence for claim in claims],
        )

    # Rule 2: Contradictory claims → escalate
    contradictory_claims = [c for c in claims if c.polarity == "contradicts"]
    if contradictory_claims:
        return ChangeClassification(
            change_type="contradictory",
            severity="major",
            auto_apply_ok=False,
            rationale=f"Contains {len(contradictory_claims)} contradictory claims requiring review",
            evidence=[claim.evidence for claim in contradictory_claims],
        )

    # Rule 3: Removal of existing content → escalate
    if old_value and not new_value:
        return ChangeClassification(
            change_type="removal",
            severity="major",
            auto_apply_ok=False,
            rationale="Removing existing content requires review",
            evidence=[claim.evidence for claim in claims],
        )

    # Rule 4: Low confidence claims (< 0.7) → escalate
    low_confidence_claims = [c for c in claims if c.confidence < 0.7]
    if low_confidence_claims:
        avg_confidence = sum(c.confidence for c in claims) / len(claims)
        return ChangeClassification(
            change_type="refine",
            severity="moderate",
            auto_apply_ok=False,
            rationale=f"Low confidence claims (avg: {avg_confidence:.2f}) require review",
            evidence=[claim.evidence for claim in low_confidence_claims],
        )

    # Rule 5: Pure additive changes with high confidence → auto-apply
    if not old_value and new_value:
        all_high_confidence = all(c.confidence >= 0.8 for c in claims)
        all_supports = all(c.polarity == "supports" for c in claims)
        if all_high_confidence and all_supports:
            return ChangeClassification(
                change_type="additive",
                severity="minor",
                auto_apply_ok=True,
                rationale="Pure additive change with high confidence, safe to auto-apply",
                evidence=[claim.evidence for claim in claims],
            )

    # No rule matched → needs LLM analysis
    return None


# =========================
# LLM Semantic Analysis
# =========================


CHANGE_CLASSIFICATION_SYSTEM_PROMPT = """You are a change safety classifier for PRD updates.

Your task is to determine if a proposed change is safe to auto-apply or should be escalated for review.

# Classification Types
- **additive**: Adding new information (safe if no conflicts)
- **refine**: Improving/clarifying existing information (safe if non-contradictory)
- **contradictory**: Conflicts with existing data (ESCALATE)
- **removal**: Removing existing content (ESCALATE)
- **scope_change**: Changes MVP scope, priorities, or core decisions (ESCALATE)
- **structural**: Major architectural or entity structure changes (ESCALATE)

# Severity Levels
- **minor**: Small clarifications, typo fixes, additive details
- **moderate**: Refinements that change meaning but not fundamentally
- **major**: Scope changes, contradictions, removals

# Auto-Apply Rules
Auto-apply is OK when ALL conditions met:
1. change_type is "additive" or "refine" (not contradictory/removal/scope_change/structural)
2. severity is "minor" or "moderate"
3. No conflicts with existing confirmed data
4. Claims have high confidence (>= 0.8)

Otherwise: Escalate for review.

# Output Format
```json
{
  "change_type": "additive",
  "severity": "minor",
  "auto_apply_ok": true,
  "rationale": "Adding new acceptance criterion with clear evidence, no conflicts"
}
```
"""


CHANGE_CLASSIFICATION_USER_PROMPT = """# Entity
Type: {entity_type}
Name: {entity_name}
Confirmation Status: {confirmation_status}

# Field Being Modified
Field: {field_name}

# Current Value
{old_value}

# Proposed New Value
{new_value}

# Claims Supporting This Change
{claims_summary}

# Task
Classify this change for safety. Can it be auto-applied or should it escalate?

Return JSON classification."""


def classify_change(
    old_value: Any,
    new_value: Any,
    field_name: str,
    entity_type: str,
    entity_name: str,
    entity_metadata: dict[str, Any],
    claims: list[Claim],
    run_id: UUID,
) -> ChangeClassification:
    """Classify a proposed change as auto-apply vs. escalate.

    Uses hybrid approach:
    1. Structural rules (fast) - if definitive, return immediately
    2. LLM semantic analysis (if rules inconclusive)

    Args:
        old_value: Current value of the field
        new_value: Proposed new value
        field_name: Name of field being modified
        entity_type: Type of entity (feature, persona, etc.)
        entity_name: Name of entity for context
        entity_metadata: Entity metadata (confirmation_status, etc.)
        claims: Claims supporting this change
        run_id: Run tracking UUID

    Returns:
        ChangeClassification with auto_apply_ok decision
    """
    logger.debug(
        f"Classifying change to {entity_type}.{field_name}",
        extra={"run_id": str(run_id), "entity_name": entity_name},
    )

    # Step 1: Try structural rules (fast)
    rule_result = _apply_structural_rules(
        old_value, new_value, entity_type, entity_metadata, claims
    )
    if rule_result is not None:
        logger.info(
            f"Change classified by rules: {rule_result.change_type} (auto_apply={rule_result.auto_apply_ok})",
            extra={"run_id": str(run_id), "entity_name": entity_name},
        )
        return rule_result

    # Step 2: Use LLM for semantic analysis
    logger.debug("Rules inconclusive, using LLM for semantic analysis")

    confirmation_status = entity_metadata.get("confirmation_status", "ai_generated")
    claims_summary = "\n".join(
        [
            f"- [{c.polarity}] {c.claim} (confidence: {c.confidence:.2f})"
            for c in claims
        ]
    )

    # Build prompt
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=CHANGE_CLASSIFICATION_SYSTEM_PROMPT),
        ("user", CHANGE_CLASSIFICATION_USER_PROMPT),
    ])

    # Create chain
    llm = get_llm(model="gpt-4o", temperature=0.0)
    parser = JsonOutputParser()
    chain = prompt | llm | parser

    try:
        # Invoke LLM
        result = chain.invoke({
            "entity_type": entity_type,
            "entity_name": entity_name,
            "confirmation_status": confirmation_status,
            "field_name": field_name,
            "old_value": str(old_value) if old_value else "(empty)",
            "new_value": str(new_value) if new_value else "(empty)",
            "claims_summary": claims_summary,
        })

        # Add evidence from claims
        result["evidence"] = [claim.evidence for claim in claims]

        classification = ChangeClassification(**result)

        logger.info(
            f"LLM classified change: {classification.change_type} (auto_apply={classification.auto_apply_ok})",
            extra={"run_id": str(run_id), "entity_name": entity_name},
        )

        return classification

    except Exception as e:
        # On error, escalate for safety
        logger.error(
            f"Failed to classify change, defaulting to escalate: {e}",
            extra={"run_id": str(run_id), "entity_name": entity_name},
        )
        return ChangeClassification(
            change_type="structural",
            severity="major",
            auto_apply_ok=False,
            rationale=f"Classification failed: {str(e)}. Escalating for safety.",
            evidence=[claim.evidence for claim in claims],
        )
