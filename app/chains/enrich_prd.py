"""LLM chain for enriching PRD sections."""

import json
from typing import Any
from uuid import UUID

from openai import OpenAI
from pydantic import ValidationError

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.prd_enrich_inputs import build_prd_enrich_prompt, get_prd_enrich_context
from app.core.schemas_prd_enrich import EnrichPRDSectionOutput

logger = get_logger(__name__)


# System prompt for PRD section enrichment
# ruff: noqa: E501
SYSTEM_PROMPT = """You are a PRD enrichment AI. Your task is to analyze a PRD section and provide structured enrichment details based on project context.

You MUST output ONLY valid JSON matching this exact schema:

{
  "section_id": "uuid",
  "slug": "string",
  "enhanced_fields": {
    "content": "enhanced long-form text content",
    "description": "enhanced description if applicable",
    "other_field": "other enhanced field content"
  },
  "proposed_client_needs": [
    {
      "key": "string - stable key",
      "title": "string",
      "why": "string",
      "ask": "string",
      "priority": "low|medium|high",
      "suggested_method": "email|meeting",
      "evidence": [{"chunk_id": "uuid", "excerpt": "string (<=280 chars)", "rationale": "string"}]
    }
  ],
  "evidence": [
    {"chunk_id": "uuid", "excerpt": "string (<=280 chars)", "rationale": "string"}
  ],
  "summary": "string - brief summary of enrichment changes",
  "schema_version": "prd_enrichment_v1"
}

CRITICAL RULES:
1. Output ONLY the JSON object, no markdown, no explanation, no preamble.
2. enhanced_fields should improve and expand the section's text content with more detail and clarity.
3. proposed_client_needs should only be added if there are genuine gaps in understanding that need client clarification.
4. Every piece of evidence must have chunk_id, excerpt (<=280 chars), rationale.
5. Excerpts must be verbatim from provided chunks.
6. Do NOT change section status or any canonical fields.
7. If no improvements are needed, return minimal enhancements with appropriate summary."""

FIX_SCHEMA_PROMPT = """The previous output was invalid. Here is the error:

{error}

Here is your previous output:

{previous_output}

Please fix the output to match the required JSON schema exactly. Output ONLY valid JSON, no explanation."""


def enrich_prd_section(
    *,
    project_id: UUID,
    section: dict[str, Any],
    context: dict[str, Any],
    settings: Settings,
    model_override: str | None = None,
) -> EnrichPRDSectionOutput:
    """
    Enrich a single PRD section with structured details using OpenAI.

    Args:
        project_id: Project UUID
        section: PRD section dict to enrich
        context: Enrichment context (canonical_prd, facts, confirmations, chunks)
        settings: Application settings
        model_override: Optional model name to use instead of settings.PRD_ENRICH_MODEL

    Returns:
        EnrichPRDSectionOutput with validated enrichment results

    Raises:
        ValueError: If model output cannot be validated after retry
    """
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    section_id = section["id"]
    section_slug = section.get("slug", "unknown")

    logger.info(
        f"Enriching PRD section {section_slug}",
        extra={
            "project_id": str(project_id),
            "section_id": str(section_id),
            "section_slug": section_slug,
        },
    )

    # Build prompt
    prompt = build_prd_enrich_prompt(
        section=section,
        canonical_prd=context["canonical_prd"],
        facts=context["facts"],
        confirmations=context["confirmations"],
        chunks=context["chunks"],
        include_research=context.get("include_research", False),
    )

    # Use override if provided, else fall back to settings
    model = model_override or settings.PRD_ENRICH_MODEL

    logger.info(f"Calling {model} for PRD section enrichment")

    # First attempt
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )

    raw_output = response.choices[0].message.content or ""

    # Try to parse and validate
    try:
        return _parse_and_validate(raw_output, project_id, section_id, section_slug)
    except (json.JSONDecodeError, ValidationError) as e:
        error_msg = str(e)
        logger.warning(
            f"First PRD enrichment attempt failed validation: {error_msg}",
            extra={"section_id": str(section_id)},
        )

    # One retry with fix-to-schema prompt
    logger.info("Attempting retry with fix-to-schema prompt")

    fix_prompt = FIX_SCHEMA_PROMPT.format(error=error_msg, previous_output=raw_output)

    retry_response = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": raw_output},
            {"role": "user", "content": fix_prompt},
        ],
    )

    retry_output = retry_response.choices[0].message.content or ""

    try:
        result = _parse_and_validate(retry_output, project_id, section_id, section_slug)
        logger.info("Retry succeeded", extra={"section_id": str(section_id)})
        return result
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(
            f"Retry also failed validation: {e}",
            extra={"section_id": str(section_id)},
        )
        # Do NOT leak raw model output in exception
        raise ValueError("Model output could not be validated to schema") from e


def _parse_and_validate(
    raw_output: str, project_id: UUID, section_id: UUID, section_slug: str
) -> EnrichPRDSectionOutput:
    """
    Parse JSON string and validate against schema.

    Args:
        raw_output: Raw string from LLM
        project_id: Project UUID
        section_id: Section UUID
        section_slug: Section slug

    Returns:
        Validated EnrichPRDSectionOutput

    Raises:
        json.JSONDecodeError: If JSON parsing fails
        ValidationError: If Pydantic validation fails
    """
    # Strip markdown code blocks if present
    cleaned = raw_output.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    parsed = json.loads(cleaned)

    # Add required fields that LLM doesn't provide
    parsed["section_id"] = str(section_id)
    parsed["slug"] = section_slug

    return EnrichPRDSectionOutput.model_validate(parsed)
