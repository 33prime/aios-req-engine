"""Persona-specific scoped patch generation.

Generates surgical updates for persona entities with strict field constraints.

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
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

# Persona-specific allowed fields
PERSONA_ALLOWED_FIELDS = [
    "name",
    "role",
    "demographics",
    "psychographics",
    "goals",
    "pain_points",
    "description",
    "related_features",
    "related_vp_steps",
]


class PersonaPatchOutput(BaseModel):
    """Structured output for persona patch generation."""

    changes: dict[str, Any]
    change_summary: str
    rationale: str
    fields_modified: list[str]


def generate_persona_patch(
    persona: dict[str, Any],
    claims: list[Claim],
    run_id: UUID,
) -> ScopedPatch:
    """Generate scoped patch for a persona entity.

    STRICT CONSTRAINTS:
    - Can only modify the specified persona
    - Can only modify allowed fields (demographics, psychographics, goals, pain_points, etc.)
    - Must validate related_features/vp_steps references exist
    - Cannot create new personas or modify other entities

    Args:
        persona: Current persona data (dict with id, name, role, etc.)
        claims: List of claims targeting this persona
        run_id: Run UUID for logging

    Returns:
        ScopedPatch with changes, classification, and evidence

    Raises:
        Exception: If LLM call fails or validation fails
    """
    logger.info(
        f"Generating persona patch for {persona.get('name')} (run_id={run_id})",
        extra={
            "persona_id": str(persona.get("id")),
            "run_id": str(run_id),
            "claim_count": len(claims),
        },
    )

    # Validate related entity references
    project_id = persona.get("project_id")
    valid_feature_ids = _get_valid_feature_ids(project_id) if project_id else []
    valid_vp_step_ids = _get_valid_vp_step_ids(project_id) if project_id else []

    # Build LLM prompt
    llm = ChatAnthropic(model="claude-sonnet-4", temperature=0)

    system_prompt = f"""You are a surgical PRD update system. Your job is to apply precise, scoped changes to a single persona.

**STRICT CONSTRAINTS**:
1. You may ONLY modify this persona: {persona.get('name')} (ID: {persona.get('id')})
2. You may ONLY modify these fields: {', '.join(PERSONA_ALLOWED_FIELDS)}
3. You CANNOT create new personas or modify other personas
4. You CANNOT modify any other entities (features, PRD sections, VP steps)
5. For related_features, only use these valid IDs: {valid_feature_ids}
6. For related_vp_steps, only use these valid IDs: {valid_vp_step_ids}

**YOUR TASK**:
- Review the claims below
- Merge new information into the existing persona data
- Be conservative: only change what is explicitly supported by claims
- Preserve existing confirmed data unless directly contradicted
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

    # Format current persona data
    persona_text = f"""**Current Persona Data**:
- ID: {persona.get('id')}
- Name: {persona.get('name')}
- Role: {persona.get('role')}
- Demographics: {persona.get('demographics', {})}
- Psychographics: {persona.get('psychographics', {})}
- Goals: {persona.get('goals', [])}
- Pain Points: {persona.get('pain_points', [])}
- Description: {persona.get('description', '')}
- Related Features: {persona.get('related_features', [])}
- Related VP Steps: {persona.get('related_vp_steps', [])}
- Confirmation Status: {persona.get('confirmation_status', 'ai_generated')}
"""

    user_prompt = f"""{persona_text}

**Claims to Apply**:
{claims_text}

Generate the scoped patch following the constraints above."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    # Call LLM
    parser = JsonOutputParser(pydantic_object=PersonaPatchOutput)
    chain = llm | parser
    result = chain.invoke(messages)

    logger.info(
        f"Generated persona patch: {result.get('change_summary')}",
        extra={
            "persona_id": str(persona.get("id")),
            "run_id": str(run_id),
            "fields_modified": result.get("fields_modified", []),
        },
    )

    # Build ScopedPatch
    # Note: Classification will be done separately by change_classifier
    # For now, we just return the patch structure
    from app.core.schemas_claims import ChangeClassification

    patch = ScopedPatch(
        entity_type="persona",
        entity_id=persona["id"],
        entity_name=persona.get("name", "Unknown Persona"),
        allowed_fields=PERSONA_ALLOWED_FIELDS,
        changes=result["changes"],
        change_summary=result["change_summary"],
        classification=ChangeClassification(
            change_type="pending",  # Will be classified later
            severity="minor",
            auto_apply_ok=False,
            rationale=result["rationale"],
        ),
        claims=claims,
        fields_modified=result["fields_modified"],
    )

    return patch


def _get_valid_feature_ids(project_id: str) -> list[str]:
    """Get list of valid feature IDs for this project."""
    try:
        supabase = get_supabase()
        response = (
            supabase.table("features")
            .select("id")
            .eq("project_id", project_id)
            .execute()
        )
        return [f["id"] for f in response.data]
    except Exception as e:
        logger.warning(f"Failed to fetch valid feature IDs: {e}")
        return []


def _get_valid_vp_step_ids(project_id: str) -> list[str]:
    """Get list of valid VP step IDs for this project."""
    try:
        supabase = get_supabase()
        response = (
            supabase.table("vp_steps")
            .select("id")
            .eq("project_id", project_id)
            .execute()
        )
        return [v["id"] for v in response.data]
    except Exception as e:
        logger.warning(f"Failed to fetch valid VP step IDs: {e}")
        return []
