"""Consultant-friendly feature enrichment chain (v2).

This chain enriches features with structured mini-spec details that are
easy to understand by non-technical consultants.
"""

import json
from typing import Any
from uuid import UUID

from openai import OpenAI
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.embeddings import embed_texts
from app.core.logging import get_logger
from app.core.schemas_enrichment_v2 import EnrichFeaturesV2Output, FeatureEnrichmentV2
from app.db.facts import list_latest_extracted_facts
from app.db.features import list_features_for_enrichment, update_feature_enrichment
from app.db.personas import list_personas
from app.db.phase0 import search_signal_chunks

logger = get_logger(__name__)


# System prompt for consultant-friendly feature enrichment
# ruff: noqa: E501
SYSTEM_PROMPT = """You are a requirements consultant helping document software features for a project. Your task is to enrich feature descriptions with structured, consultant-friendly details.

You will receive:
1. A feature name and description
2. A list of personas who might use this feature
3. Context from project signals (transcripts, emails, notes)
4. Previously extracted facts about the project

Your job is to create a "mini-spec" for the feature that is:
- Written in plain language (no technical jargon)
- Easy for non-technical consultants to understand
- Based on evidence from the provided context
- Structured for easy review and handoff

You MUST output ONLY valid JSON matching this exact schema:

{
  "project_id": "uuid",
  "features": [
    {
      "feature_id": "uuid",
      "feature_name": "string",
      "overview": "Business-friendly description of what this feature does and why it matters (2-4 sentences)",
      "target_personas": [
        {
          "persona_id": "uuid or null if not matched",
          "persona_name": "Name of the persona",
          "role": "primary|secondary",
          "context": "How/why this persona uses the feature (1-2 sentences)"
        }
      ],
      "user_actions": [
        "Step-by-step actions the user takes (e.g., 'Taps Start Survey button')"
      ],
      "system_behaviors": [
        "What happens behind the scenes (e.g., 'Starts audio recording')"
      ],
      "ui_requirements": [
        "What the user sees (e.g., 'One question at a time', 'Large Next button')"
      ],
      "rules": [
        "Simple business rules (e.g., 'Cannot start without client name')"
      ],
      "integrations": [
        "External system names only (e.g., 'HubSpot', 'Stripe', 'OpenAI')"
      ]
    }
  ],
  "schema_version": "feature_enrichment_v2"
}

CRITICAL RULES:
1. Output ONLY the JSON object, no markdown, no explanation, no preamble.
2. Write in plain consultant language - avoid technical terms like "API", "endpoint", "middleware", "schema".
3. User actions should describe WHAT the user does, not HOW the system implements it.
4. System behaviors should be high-level descriptions, not technical implementation details.
5. UI requirements describe what the user sees and interacts with.
6. Rules are simple business constraints, not technical validation logic.
7. Integrations are simple system names like "HubSpot" not "HubSpot CRM API v3".
8. Match personas by name/role when possible; leave persona_id null if no clear match.
9. If a section has no relevant information, use an empty array [].
10. Base enrichment on the provided context - don't invent details."""


def _retrieve_feature_context(
    project_id: UUID,
    feature_name: str,
    include_research: bool = False,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    """
    Retrieve relevant context chunks for a feature.

    Args:
        project_id: Project UUID
        feature_name: Feature name for search query
        include_research: Whether to include research signals
        top_k: Number of chunks to retrieve

    Returns:
        List of relevant chunks
    """
    # Generate queries based on feature name
    queries = [
        f"What are the requirements for {feature_name}?",
        f"How does {feature_name} work?",
        f"Who uses {feature_name}?",
    ]

    all_chunks = []
    for query in queries:
        query_embedding = embed_texts([query])[0]
        chunks = search_signal_chunks(
            query_embedding=query_embedding,
            match_count=top_k // len(queries) + 1,
            project_id=project_id,
        )

        # Filter by signal type if not including research
        if not include_research:
            chunks = [
                c for c in chunks
                if c.get("signal_metadata", {}).get("signal_type", "") in
                ["client_email", "transcripts", "file_text", "notes"]
            ]

        all_chunks.extend(chunks)

    # Dedupe by chunk_id
    seen = set()
    unique_chunks = []
    for chunk in all_chunks:
        chunk_id = chunk.get("chunk_id")
        if chunk_id and chunk_id not in seen:
            seen.add(chunk_id)
            unique_chunks.append(chunk)
            if len(unique_chunks) >= top_k:
                break

    return unique_chunks


def _build_enrichment_prompt(
    project_id: UUID,
    features: list[dict[str, Any]],
    personas: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
) -> str:
    """
    Build the prompt for feature enrichment.

    Args:
        project_id: Project UUID
        features: Features to enrich
        personas: All personas for the project
        facts: Recent extracted facts
        chunks: Supporting context chunks

    Returns:
        Complete prompt for the LLM
    """
    prompt_parts = [
        "# Feature Enrichment Task",
        "",
        "Enrich the following features with structured mini-spec details.",
        "",
    ]

    # Add features to enrich
    prompt_parts.append("## Features to Enrich")
    for i, feature in enumerate(features, 1):
        prompt_parts.append(f"{i}. **{feature.get('name', 'Unknown')}**")
        prompt_parts.append(f"   ID: {feature.get('id')}")
        prompt_parts.append(f"   Category: {feature.get('category', 'General')}")
        prompt_parts.append(f"   MVP: {'Yes' if feature.get('is_mvp') else 'No'}")
        if feature.get('description'):
            prompt_parts.append(f"   Description: {feature.get('description')}")
        prompt_parts.append("")

    # Add personas for matching
    if personas:
        prompt_parts.append("## Available Personas")
        prompt_parts.append("Match features to these personas when relevant:")
        for persona in personas:
            prompt_parts.append(f"- **{persona.get('name', 'Unknown')}** (ID: {persona.get('id')})")
            if persona.get('role'):
                prompt_parts.append(f"  Role: {persona.get('role')}")
            if persona.get('description'):
                prompt_parts.append(f"  Description: {persona.get('description')[:200]}")
        prompt_parts.append("")

    # Add facts for context
    if facts:
        prompt_parts.append("## Extracted Facts")
        prompt_parts.append("Recent facts about this project:")
        for fact in facts[:10]:
            summary = fact.get("summary", "")
            if summary:
                prompt_parts.append(f"- {summary}")
        prompt_parts.append("")

    # Add supporting context
    if chunks:
        prompt_parts.append("## Supporting Context")
        prompt_parts.append("Relevant excerpts from project signals:")
        for i, chunk in enumerate(chunks[:15], 1):
            snippet = chunk.get("snippet", "")[:500]
            source_type = chunk.get("signal_metadata", {}).get("signal_type", "unknown")
            prompt_parts.append(f"{i}. [{source_type}] {snippet}")
        prompt_parts.append("")

    # Instructions
    prompt_parts.extend([
        "## Instructions",
        f"- Project ID: {project_id}",
        "- Enrich each feature with the structured fields",
        "- Write in plain consultant language",
        "- Match personas based on who would realistically use each feature",
        "- Use 'primary' role for the main user, 'secondary' for occasional users",
        "- Base enrichment on the provided context - don't invent details",
        "",
        "Output ONLY valid JSON matching the required schema.",
    ])

    return "\n".join(prompt_parts)


def enrich_features_v2(
    project_id: UUID,
    feature_ids: list[UUID] | None = None,
    include_research: bool = False,
    model_override: str | None = None,
) -> EnrichFeaturesV2Output:
    """
    Enrich features with consultant-friendly mini-spec details.

    Args:
        project_id: Project UUID
        feature_ids: Optional specific feature IDs to enrich (default: all unenriched)
        include_research: Whether to include research signals in context
        model_override: Optional model name override

    Returns:
        EnrichFeaturesV2Output with enriched features

    Raises:
        ValueError: If no features to enrich or validation fails
    """
    settings = get_settings()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # Get features to enrich
    if feature_ids:
        # Get specific features
        from app.db.features import list_features
        all_features = list_features(project_id)
        features = [f for f in all_features if UUID(f["id"]) in feature_ids]
    else:
        # Get all unenriched features
        features = list_features_for_enrichment(project_id, only_unenriched=True)

    if not features:
        raise ValueError("No features to enrich")

    logger.info(
        f"Enriching {len(features)} features for project {project_id}",
        extra={"project_id": str(project_id), "feature_count": len(features)},
    )

    # Get personas for matching
    personas = list_personas(project_id)

    # Get facts for context
    facts = list_latest_extracted_facts(project_id, limit=15)

    # Retrieve context chunks for all features
    all_chunks = []
    for feature in features[:5]:  # Limit to 5 features per batch
        chunks = _retrieve_feature_context(
            project_id=project_id,
            feature_name=feature.get("name", ""),
            include_research=include_research,
            top_k=8,
        )
        all_chunks.extend(chunks)

    # Dedupe chunks
    seen = set()
    unique_chunks = []
    for chunk in all_chunks:
        chunk_id = chunk.get("chunk_id")
        if chunk_id and chunk_id not in seen:
            seen.add(chunk_id)
            unique_chunks.append(chunk)

    # Build prompt
    prompt = _build_enrichment_prompt(
        project_id=project_id,
        features=features[:5],  # Limit batch size
        personas=personas,
        facts=facts,
        chunks=unique_chunks[:20],  # Limit context size
    )

    # Call LLM
    model = model_override or settings.FEATURES_ENRICH_MODEL
    logger.info(f"Calling {model} for feature enrichment v2")

    response = client.chat.completions.create(
        model=model,
        temperature=0.2,
        max_tokens=8192,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )

    # Log usage
    from app.core.llm_usage import log_llm_usage
    log_llm_usage(
        workflow="enrich_features", model=response.model, provider="openai",
        tokens_input=response.usage.prompt_tokens, tokens_output=response.usage.completion_tokens,
        project_id=project_id,
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
            max_tokens=8192,
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
        f"Successfully enriched {len(result.features)} features",
        extra={"project_id": str(project_id)},
    )

    return result


def _parse_and_validate(raw_output: str, project_id: UUID) -> EnrichFeaturesV2Output:
    """Parse and validate LLM output."""
    from app.core.llm import parse_llm_json_dict
    parsed = parse_llm_json_dict(raw_output)
    parsed["project_id"] = str(project_id)
    return EnrichFeaturesV2Output.model_validate(parsed)


def apply_feature_enrichment(enrichment: FeatureEnrichmentV2) -> dict[str, Any]:
    """
    Apply enrichment to a feature in the database.

    Args:
        enrichment: FeatureEnrichmentV2 with enriched data

    Returns:
        Updated feature dict
    """
    return update_feature_enrichment(
        feature_id=UUID(enrichment.feature_id),
        overview=enrichment.overview,
        target_personas=[tp.model_dump() for tp in enrichment.target_personas],
        user_actions=enrichment.user_actions,
        system_behaviors=enrichment.system_behaviors,
        ui_requirements=enrichment.ui_requirements,
        rules=enrichment.rules,
        integrations=enrichment.integrations,
    )


def enrich_and_save_features(
    project_id: UUID,
    feature_ids: list[UUID] | None = None,
    include_research: bool = False,
) -> dict[str, Any]:
    """
    Enrich features and save to database.

    Args:
        project_id: Project UUID
        feature_ids: Optional specific feature IDs
        include_research: Whether to include research in context

    Returns:
        Summary dict with counts and enriched feature names
    """
    from app.chains.update_vp_step import queue_change

    # Run enrichment
    result = enrich_features_v2(
        project_id=project_id,
        feature_ids=feature_ids,
        include_research=include_research,
    )

    # Save each enriched feature
    enriched_names = []
    for feature_enrichment in result.features:
        try:
            apply_feature_enrichment(feature_enrichment)
            enriched_names.append(feature_enrichment.feature_name)
            logger.info(f"Saved enrichment for feature: {feature_enrichment.feature_name}")

            # Queue VP change for this feature enrichment
            try:
                queue_change(
                    project_id=project_id,
                    change_type="feature_enriched",
                    entity_type="feature",
                    entity_id=UUID(feature_enrichment.feature_id),
                    entity_name=feature_enrichment.feature_name,
                    change_details={
                        "enrichment_type": "v2",
                        "has_target_personas": len(feature_enrichment.target_personas) > 0,
                        "has_user_actions": len(feature_enrichment.user_actions) > 0,
                        "has_system_behaviors": len(feature_enrichment.system_behaviors) > 0,
                    },
                )
            except Exception as queue_err:
                logger.warning(f"Failed to queue VP change for feature {feature_enrichment.feature_name}: {queue_err}")
        except Exception as e:
            logger.error(f"Failed to save enrichment for {feature_enrichment.feature_name}: {e}")

    return {
        "enriched_count": len(enriched_names),
        "enriched_features": enriched_names,
        "project_id": str(project_id),
    }
