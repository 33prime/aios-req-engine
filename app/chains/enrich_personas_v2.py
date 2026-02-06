"""Consultant-friendly persona enrichment chain (v2).

This chain enriches personas with:
- Detailed overview of who they are
- Key workflows showing how they use features together
"""

import json
from typing import Any
from uuid import UUID

from openai import OpenAI
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.schemas_enrichment_v2 import EnrichPersonasV2Output, PersonaEnrichmentV2
from app.db.features import list_features
from app.db.personas import list_personas_for_enrichment, update_persona_enrichment

logger = get_logger(__name__)


# System prompt for persona enrichment
# ruff: noqa: E501
SYSTEM_PROMPT = """You are a requirements consultant helping document user personas for a software project. Your task is to enrich persona profiles with detailed workflows showing how they use the product.

You will receive:
1. Persona information (name, role, goals, pain points)
2. A list of features available in the product
3. Context about the project

Your job is to:
1. Write a detailed overview of who this persona is (their background, motivations, daily work)
2. Identify key workflows - sequences of features this persona uses together to accomplish their goals

You MUST output ONLY valid JSON matching this exact schema:

{
  "project_id": "uuid",
  "personas": [
    {
      "persona_id": "uuid",
      "persona_name": "string",
      "overview": "Detailed description of who this persona is, their background, what they care about, and their daily challenges (3-5 sentences)",
      "key_workflows": [
        {
          "name": "Workflow name (e.g., 'Morning Client Review')",
          "description": "Brief description of what this workflow accomplishes",
          "steps": [
            "Step 1: Opens the dashboard",
            "Step 2: Reviews overnight notifications",
            "Step 3: ...",
          ],
          "features_used": ["Dashboard", "Notifications", "Client List"]
        }
      ]
    }
  ],
  "schema_version": "persona_enrichment_v2"
}

CRITICAL RULES:
1. Output ONLY the JSON object, no markdown, no explanation, no preamble.
2. Write in plain consultant language - describe workflows as a day-in-the-life narrative.
3. Each workflow should represent a real use case (e.g., "End of Day Reporting", "Onboarding New Client").
4. Steps should be concrete actions, not technical descriptions.
5. Features_used should only include features from the provided list.
6. Create 2-4 workflows per persona based on their goals.
7. Overview should paint a picture of who this person is beyond just their title.
8. Base enrichment on the provided context - don't invent product features."""


def _build_persona_enrichment_prompt(
    project_id: UUID,
    personas: list[dict[str, Any]],
    features: list[dict[str, Any]],
) -> str:
    """
    Build the prompt for persona enrichment.

    Args:
        project_id: Project UUID
        personas: Personas to enrich
        features: All features for the project

    Returns:
        Complete prompt for the LLM
    """
    prompt_parts = [
        "# Persona Enrichment Task",
        "",
        "Enrich the following personas with detailed overviews and key workflows.",
        "",
    ]

    # Add personas to enrich
    prompt_parts.append("## Personas to Enrich")
    for i, persona in enumerate(personas, 1):
        prompt_parts.append(f"{i}. **{persona.get('name', 'Unknown')}**")
        prompt_parts.append(f"   ID: {persona.get('id')}")
        if persona.get('role'):
            prompt_parts.append(f"   Role: {persona.get('role')}")
        if persona.get('description'):
            prompt_parts.append(f"   Description: {persona.get('description')}")
        if persona.get('goals'):
            goals = persona.get('goals', [])
            if goals:
                prompt_parts.append(f"   Goals: {', '.join(goals[:5])}")
        if persona.get('pain_points'):
            pains = persona.get('pain_points', [])
            if pains:
                prompt_parts.append(f"   Pain Points: {', '.join(pains[:5])}")
        prompt_parts.append("")

    # Add available features
    if features:
        prompt_parts.append("## Available Features")
        prompt_parts.append("These are the features this persona might use in their workflows:")
        for feature in features:
            name = feature.get('name', 'Unknown')
            category = feature.get('category', '')
            is_mvp = feature.get('is_mvp', False)
            mvp_label = " [MVP]" if is_mvp else ""
            cat_label = f" ({category})" if category else ""
            prompt_parts.append(f"- {name}{cat_label}{mvp_label}")
        prompt_parts.append("")

    # Instructions
    prompt_parts.extend([
        "## Instructions",
        f"- Project ID: {project_id}",
        "- Create a detailed overview for each persona (3-5 sentences)",
        "- Identify 2-4 key workflows per persona",
        "- Each workflow should:",
        "  - Have a descriptive name (e.g., 'Weekly Report Generation')",
        "  - Include 3-6 concrete steps",
        "  - List the features used (must be from the Available Features list)",
        "- Base workflows on the persona's goals and pain points",
        "",
        "Output ONLY valid JSON matching the required schema.",
    ])

    return "\n".join(prompt_parts)


def enrich_personas_v2(
    project_id: UUID,
    persona_ids: list[UUID] | None = None,
    model_override: str | None = None,
) -> EnrichPersonasV2Output:
    """
    Enrich personas with detailed overviews and key workflows.

    Args:
        project_id: Project UUID
        persona_ids: Optional specific persona IDs to enrich (default: all unenriched)
        model_override: Optional model name override

    Returns:
        EnrichPersonasV2Output with enriched personas

    Raises:
        ValueError: If no personas to enrich or validation fails
    """
    settings = get_settings()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # Get personas to enrich
    if persona_ids:
        from app.db.personas import list_personas
        all_personas = list_personas(project_id)
        personas = [p for p in all_personas if UUID(p["id"]) in persona_ids]
    else:
        personas = list_personas_for_enrichment(project_id, only_unenriched=True)

    if not personas:
        raise ValueError("No personas to enrich")

    logger.info(
        f"Enriching {len(personas)} personas for project {project_id}",
        extra={"project_id": str(project_id), "persona_count": len(personas)},
    )

    # Get all features for workflow matching
    features = list_features(project_id)

    # Build prompt
    prompt = _build_persona_enrichment_prompt(
        project_id=project_id,
        personas=personas[:5],  # Limit batch size
        features=features,
    )

    # Call LLM
    model = model_override or settings.FEATURES_ENRICH_MODEL
    logger.info(f"Calling {model} for persona enrichment v2")

    response = client.chat.completions.create(
        model=model,
        temperature=0.3,
        max_tokens=6144,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )

    raw_output = response.choices[0].message.content or ""

    # Parse and validate output
    try:
        result = _parse_and_validate(raw_output, project_id)
    except (json.JSONDecodeError, ValidationError) as e:
        logger.warning(f"First attempt failed: {e}")

        # Retry with fix prompt
        fix_prompt = f"""The previous output was invalid. Error: {e}

Please fix and output ONLY valid JSON matching the schema. No markdown, no explanation."""

        retry_response = client.chat.completions.create(
            model=model,
            temperature=0,
            max_tokens=6144,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": raw_output},
                {"role": "user", "content": fix_prompt},
            ],
        )

        retry_output = retry_response.choices[0].message.content or ""
        result = _parse_and_validate(retry_output, project_id)

    logger.info(
        f"Successfully enriched {len(result.personas)} personas",
        extra={"project_id": str(project_id)},
    )

    return result


def _parse_and_validate(raw_output: str, project_id: UUID) -> EnrichPersonasV2Output:
    """Parse and validate LLM output."""
    from app.core.llm import parse_llm_json_dict
    parsed = parse_llm_json_dict(raw_output)
    parsed["project_id"] = str(project_id)
    return EnrichPersonasV2Output.model_validate(parsed)


def apply_persona_enrichment(enrichment: PersonaEnrichmentV2) -> dict[str, Any]:
    """
    Apply enrichment to a persona in the database.

    Args:
        enrichment: PersonaEnrichmentV2 with enriched data

    Returns:
        Updated persona dict
    """
    return update_persona_enrichment(
        persona_id=UUID(enrichment.persona_id),
        overview=enrichment.overview,
        key_workflows=[wf.model_dump() for wf in enrichment.key_workflows],
    )


def enrich_and_save_personas(
    project_id: UUID,
    persona_ids: list[UUID] | None = None,
) -> dict[str, Any]:
    """
    Enrich personas and save to database.

    Args:
        project_id: Project UUID
        persona_ids: Optional specific persona IDs

    Returns:
        Summary dict with counts and enriched persona names
    """
    from app.chains.update_vp_step import queue_change

    # Run enrichment
    result = enrich_personas_v2(
        project_id=project_id,
        persona_ids=persona_ids,
    )

    # Save each enriched persona
    enriched_names = []
    for persona_enrichment in result.personas:
        try:
            apply_persona_enrichment(persona_enrichment)
            enriched_names.append(persona_enrichment.persona_name)
            logger.info(f"Saved enrichment for persona: {persona_enrichment.persona_name}")

            # Queue VP change for this persona enrichment
            try:
                queue_change(
                    project_id=project_id,
                    change_type="persona_enriched",
                    entity_type="persona",
                    entity_id=UUID(persona_enrichment.persona_id),
                    entity_name=persona_enrichment.persona_name,
                    change_details={
                        "enrichment_type": "v2",
                        "workflow_count": len(persona_enrichment.key_workflows),
                        "has_overview": bool(persona_enrichment.overview),
                    },
                )
            except Exception as queue_err:
                logger.warning(f"Failed to queue VP change for persona {persona_enrichment.persona_name}: {queue_err}")
        except Exception as e:
            logger.error(f"Failed to save enrichment for {persona_enrichment.persona_name}: {e}")

    return {
        "enriched_count": len(enriched_names),
        "enriched_personas": enriched_names,
        "project_id": str(project_id),
    }
