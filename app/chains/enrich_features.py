"""LLM chain for enriching feature details."""

import json
from typing import Any
from uuid import UUID

from openai import OpenAI
from pydantic import ValidationError

from app.core.config import Settings
from app.core.feature_enrich_inputs import build_feature_enrich_prompt, get_feature_enrich_context
from app.core.logging import get_logger
from app.core.schemas_feature_enrich import EnrichFeaturesOutput

logger = get_logger(__name__)


# System prompt for feature enrichment
# ruff: noqa: E501
SYSTEM_PROMPT = """You are a feature enrichment AI. Your task is to analyze a feature and provide structured enrichment details based on project context.

You MUST output ONLY valid JSON matching this exact schema:

{
  "project_id": "uuid",
  "feature_id": "uuid",
  "feature_slug": "string",
  "schema_version": "feature_details_v1",
  "details": {
    "summary": "string - concise description of feature purpose and scope",
    "data_requirements": [
      {
        "entity": "string",
        "fields": ["field1", "field2"],
        "notes": "string or null",
        "evidence": [{"chunk_id": "uuid", "excerpt": "string (<=280 chars)", "rationale": "string"}]
      }
    ],
    "business_rules": [
      {
        "title": "string",
        "rule": "string",
        "verification": "string or null",
        "evidence": [{"chunk_id": "uuid", "excerpt": "string", "rationale": "string"}]
      }
    ],
    "acceptance_criteria": [
      {
        "criterion": "string",
        "evidence": [{"chunk_id": "uuid", "excerpt": "string", "rationale": "string"}]
      }
    ],
    "dependencies": [
      {
        "dependency_type": "feature|external_system|data|process",
        "name": "string",
        "why": "string",
        "evidence": [{"chunk_id": "uuid", "excerpt": "string", "rationale": "string"}]
      }
    ],
    "integrations": [
      {
        "system": "string",
        "direction": "inbound|outbound|bidirectional",
        "data_exchanged": "string",
        "evidence": [{"chunk_id": "uuid", "excerpt": "string", "rationale": "string"}]
      }
    ],
    "telemetry_events": [
      {
        "event_name": "string",
        "when_fired": "string",
        "properties": ["prop1", "prop2"],
        "success_metric": "string or null",
        "evidence": [{"chunk_id": "uuid", "excerpt": "string", "rationale": "string"}]
      }
    ],
    "risks": [
      {
        "title": "string",
        "risk": "string",
        "mitigation": "string",
        "severity": "low|medium|high",
        "evidence": [{"chunk_id": "uuid", "excerpt": "string", "rationale": "string"}]
      }
    ]
  },
  "open_questions": [
    {
      "question": "string",
      "why_it_matters": "string",
      "suggested_owner": "string",
      "evidence": [{"chunk_id": "uuid", "excerpt": "string", "rationale": "string"}]
    }
  ]
}

CRITICAL RULES:
1. Output ONLY the JSON object, no markdown, no explanation, no preamble.
2. chunk_id MUST be an exact UUID copied from the Supporting Context - NEVER fabricate chunk_ids.
3. If no chunks support a section, use an empty evidence array [].
4. Excerpts must be verbatim from provided chunks (<=280 chars).
5. Empty arrays are allowed if no evidence exists, but summary must explain gaps.
6. Do not make assumptions - base everything on provided context.
7. For unclear information, add open_questions instead of guessing.
8. Feature enrichment NEVER changes canonical fields (name, is_mvp, status, etc.).
9. Focus on providing structured details to make features more actionable."""

FIX_SCHEMA_PROMPT = """The previous output was invalid. Here is the error:

{error}

Here is your previous output:

{previous_output}

Please fix the output to match the required JSON schema exactly. Output ONLY valid JSON, no explanation."""


def enrich_feature(
    *,
    project_id: UUID,
    feature: dict[str, Any],
    context: dict[str, Any],
    settings: Settings,
    model_override: str | None = None,
) -> EnrichFeaturesOutput:
    """
    Enrich a single feature with structured details using OpenAI.

    Args:
        project_id: Project UUID
        feature: Feature dict to enrich
        context: Enrichment context (facts, confirmations, chunks)
        settings: Application settings
        model_override: Optional model name to use instead of settings.FEATURES_ENRICH_MODEL

    Returns:
        EnrichFeaturesOutput with validated enrichment results

    Raises:
        ValueError: If model output cannot be validated after retry
    """
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    feature_id = feature["id"]
    feature_slug = feature.get("name", "unknown")

    logger.info(
        f"Enriching feature {feature_slug}",
        extra={
            "project_id": str(project_id),
            "feature_id": str(feature_id),
            "feature_slug": feature_slug,
        },
    )

    # Build prompt with full project context
    prompt = build_feature_enrich_prompt(
        project_id=project_id,
        feature=feature,
        facts=context["facts"],
        confirmations=context["confirmations"],
        chunks=context["chunks"],
        include_research=context.get("include_research", False),
        state_snapshot=context.get("state_snapshot"),
    )

    # Use override if provided, else fall back to settings
    model = model_override or settings.FEATURES_ENRICH_MODEL

    logger.info(f"Calling {model} for feature enrichment")

    # First attempt
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        max_tokens=16384,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )

    raw_output = response.choices[0].message.content or ""

    # Try to parse and validate
    try:
        return _parse_and_validate(raw_output, project_id, feature_id, feature_slug)
    except (json.JSONDecodeError, ValidationError) as e:
        error_msg = str(e)
        logger.warning(
            f"First enrichment attempt failed validation: {error_msg}",
            extra={"feature_id": str(feature_id)},
        )

    # One retry with fix-to-schema prompt
    logger.info("Attempting retry with fix-to-schema prompt")

    fix_prompt = FIX_SCHEMA_PROMPT.format(error=error_msg, previous_output=raw_output)

    retry_response = client.chat.completions.create(
        model=model,
        temperature=0,
        max_tokens=16384,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": raw_output},
            {"role": "user", "content": fix_prompt},
        ],
    )

    retry_output = retry_response.choices[0].message.content or ""

    try:
        result = _parse_and_validate(retry_output, project_id, feature_id, feature_slug)
        logger.info("Retry succeeded", extra={"feature_id": str(feature_id)})
        return result
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(
            f"Retry also failed validation: {e}",
            extra={"feature_id": str(feature_id)},
        )
        # Do NOT leak raw model output in exception
        raise ValueError("Model output could not be validated to schema") from e


def _parse_and_validate(
    raw_output: str, project_id: UUID, feature_id: UUID, feature_slug: str
) -> EnrichFeaturesOutput:
    """Parse JSON string and validate against schema."""
    from app.core.llm import parse_llm_json_dict
    parsed = parse_llm_json_dict(raw_output)
    parsed["project_id"] = str(project_id)
    parsed["feature_id"] = str(feature_id)
    parsed["feature_slug"] = feature_slug
    return EnrichFeaturesOutput.model_validate(parsed)
