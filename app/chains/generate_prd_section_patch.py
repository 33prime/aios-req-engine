"""PRD section-specific scoped patch generation.

Generates surgical updates for PRD section entities with strict field constraints.

Phase 2: Surgical Updates for All Entity Types
"""

from typing import Any
from uuid import UUID

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel

from app.core.logging import get_logger
from app.core.schemas_claims import Claim, ScopedPatch

logger = get_logger(__name__)

# PRD section allowed fields
PRD_SECTION_ALLOWED_FIELDS = [
    "label",
    "content",
    "enrichment",
]

# High-sensitivity sections that should escalate more conservatively
HIGH_SENSITIVITY_SECTIONS = [
    "software_summary",
    "constraints",
    "mvp_non_mvp",
]


class PrdSectionPatchOutput(BaseModel):
    """Structured output for PRD section patch generation."""

    changes: dict[str, Any]
    change_summary: str
    rationale: str
    fields_modified: list[str]


def generate_prd_section_patch(
    prd_section: dict[str, Any],
    claims: list[Claim],
    run_id: UUID,
) -> ScopedPatch:
    """Generate scoped patch for a PRD section entity.

    STRICT CONSTRAINTS:
    - Can only modify the specified PRD section
    - Can only modify allowed fields (content, enrichment)
    - Special handling for high-sensitivity sections (escalate more)
    - Cannot create new sections or modify other entities

    Args:
        prd_section: Current PRD section data (dict with id, slug, label, content, etc.)
        claims: List of claims targeting this section
        run_id: Run UUID for logging

    Returns:
        ScopedPatch with changes, classification, and evidence

    Raises:
        Exception: If LLM call fails
    """
    section_slug = prd_section.get("slug", "unknown")
    section_label = prd_section.get("label", section_slug)

    logger.info(
        f"Generating PRD section patch for {section_label} (run_id={run_id})",
        extra={
            "section_id": str(prd_section.get("id")),
            "section_slug": section_slug,
            "run_id": str(run_id),
            "claim_count": len(claims),
        },
    )

    # Check if this is a high-sensitivity section
    is_high_sensitivity = section_slug in HIGH_SENSITIVITY_SECTIONS

    # Build LLM prompt
    llm = ChatAnthropic(model="claude-sonnet-4", temperature=0)

    sensitivity_note = ""
    if is_high_sensitivity:
        sensitivity_note = f"""
**⚠️ HIGH SENSITIVITY SECTION**: This is a {section_label} section.
- Be EXTRA conservative with changes
- Only modify if claims are very high confidence
- Prefer additive changes over rewrites
- Flag any contradictions or scope changes
"""

    system_prompt = f"""You are a surgical PRD update system. Your job is to apply precise, scoped changes to a single PRD section.

**STRICT CONSTRAINTS**:
1. You may ONLY modify this section: {section_label} (slug: {section_slug}, ID: {prd_section.get('id')})
2. You may ONLY modify these fields: {', '.join(PRD_SECTION_ALLOWED_FIELDS)}
3. You CANNOT create new sections or modify other sections
4. You CANNOT modify any other entities (features, personas, VP steps)

{sensitivity_note}

**YOUR TASK**:
- Review the claims below
- Merge new information into the existing section content
- Be conservative: only change what is explicitly supported by claims
- Preserve existing confirmed data unless directly contradicted
- For content updates, prefer appending or refining over complete rewrites
- Return ONLY the fields that changed

**OUTPUT FORMAT**:
{{
  "changes": {{
    "field_name": new_value,
    ...
  }},
  "change_summary": "Brief summary of what changed",
  "rationale": "Why these changes are appropriate based on the claims",
  "fields_modified": ["field1", "field2", ...]
}}"""

    # Format claims
    claims_text = "\n\n".join(
        [
            f"**Claim {i+1}**:\n"
            f"- Assertion: {claim.claim}\n"
            f"- Target Field: {claim.target.get('field', 'N/A')}\n"
            f"- Polarity: {claim.polarity}\n"
            f"- Confidence: {claim.confidence}\n"
            f"- Evidence: {claim.evidence.get('excerpt', '')[:200]}..."
            for i, claim in enumerate(claims)
        ]
    )

    # Format current section data
    section_text = f"""**Current PRD Section Data**:
- ID: {prd_section.get('id')}
- Slug: {section_slug}
- Label: {section_label}
- Content: {prd_section.get('content', '')[:500]}{'...' if len(prd_section.get('content', '')) > 500 else ''}
- Enrichment: {str(prd_section.get('enrichment', {}))[:300]}
- Confirmation Status: {prd_section.get('confirmation_status', 'ai_generated')}
"""

    user_prompt = f"""{section_text}

**Claims to Apply**:
{claims_text}

Generate the scoped patch following the constraints above."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    # Call LLM
    parser = JsonOutputParser(pydantic_object=PrdSectionPatchOutput)
    chain = llm | parser
    result = chain.invoke(messages)

    logger.info(
        f"Generated PRD section patch: {result.get('change_summary')}",
        extra={
            "section_id": str(prd_section.get("id")),
            "section_slug": section_slug,
            "run_id": str(run_id),
            "fields_modified": result.get("fields_modified", []),
            "high_sensitivity": is_high_sensitivity,
        },
    )

    # Build ScopedPatch
    # Note: Classification will be done separately by change_classifier
    from app.core.schemas_claims import ChangeClassification

    # For high-sensitivity sections, bias toward escalation
    initial_severity = "moderate" if is_high_sensitivity else "minor"

    patch = ScopedPatch(
        entity_type="prd_section",
        entity_id=prd_section["id"],
        entity_name=section_label,
        allowed_fields=PRD_SECTION_ALLOWED_FIELDS,
        changes=result["changes"],
        change_summary=result["change_summary"],
        classification=ChangeClassification(
            change_type="pending",  # Will be classified later
            severity=initial_severity,
            auto_apply_ok=False,
            rationale=result["rationale"],
        ),
        claims=claims,
        fields_modified=result["fields_modified"],
    )

    return patch
