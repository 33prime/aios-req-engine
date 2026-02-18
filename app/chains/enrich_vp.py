"""LLM chain for enriching VP steps."""

import json
from typing import Any
from uuid import UUID

from openai import OpenAI
from pydantic import ValidationError

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.schemas_vp_enrich import EnrichVPStepOutput
from app.core.vp_enrich_inputs import build_vp_enrich_prompt, get_vp_enrich_context

logger = get_logger(__name__)


# System prompt for VP step enrichment
# ruff: noqa: E501
SYSTEM_PROMPT = """You are a Value Path enrichment AI. Your task is to analyze a VP step and provide structured enrichment details based on project context.

You MUST output ONLY valid JSON matching this exact schema:

{
  "step_id": "uuid",
  "step_index": 1,
  "enhanced_fields": {
    "description": "enhanced step description",
    "ui_overview": "enhanced UI overview",
    "value_created": "enhanced value created description",
    "kpi_impact": "enhanced KPI impact description",
    "experiments": "enhanced experiments description"
  },
  "proposed_needs": [
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
  "schema_version": "vp_enrichment_v1"
}

CRITICAL RULES:
1. Output ONLY valid JSON - no markdown code blocks, no explanation, no preamble.
2. chunk_id MUST be an exact UUID copied from the [ID:uuid] prefix in Supporting Context - NEVER fabricate chunk_ids.
3. If no chunks support a section, use an empty evidence array [].
4. enhanced_fields should improve and expand the step's text content with more detail, implementation specifics, and clarity.
5. proposed_needs should only be added if there are genuine gaps in understanding that need clarification.
6. Excerpts must be verbatim quotes from the provided context chunks (max 280 chars).
7. Rationale must explain why this evidence supports your enrichment.
8. Do NOT change step status or any canonical fields.
9. Focus on user experience, implementation details, and success metrics.
10. If no improvements are needed, return minimal enhancements with appropriate summary.
11. Ensure all JSON strings are properly escaped (quotes, newlines, etc.).
"""

FIX_SCHEMA_PROMPT = """The previous output was invalid. Here is the error:

{error}

Here is your previous output:

{previous_output}

CRITICAL FIXES NEEDED:
- Output ONLY valid JSON (no ``` markdown, no explanation)
- Properly escape all quotes and newlines in strings
- Ensure all UUIDs are valid format
- Evidence array can be empty [] if no evidence available
- All object keys must be properly quoted

Please fix and output valid JSON only:"""


def enrich_vp_step(
    *,
    project_id: UUID,
    step: dict[str, Any],
    context: dict[str, Any],
    settings: Settings,
    model_override: str | None = None,
) -> EnrichVPStepOutput:
    """
    Enrich a single VP step with structured details using OpenAI.

    Args:
        project_id: Project UUID
        step: VP step dict to enrich
        context: Enrichment context (canonical_vp, facts, confirmations, chunks)
        settings: Application settings
        model_override: Optional model name to use instead of settings.VP_ENRICH_MODEL

    Returns:
        EnrichVPStepOutput with validated enrichment results

    Raises:
        ValueError: If model output cannot be validated after retry
    """
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    step_id = step["id"]
    step_index = step.get("step_index", 0)

    logger.info(
        f"Enriching VP step {step_index}",
        extra={
            "project_id": str(project_id),
            "step_id": str(step_id),
            "step_index": step_index,
        },
    )

    # Build prompt with full project context
    prompt = build_vp_enrich_prompt(
        step=step,
        canonical_vp=context["canonical_vp"],
        facts=context["facts"],
        confirmations=context["confirmations"],
        chunks=context["chunks"],
        include_research=context.get("include_research", False),
        state_snapshot=context.get("state_snapshot"),
    )

    # Use override if provided, else fall back to settings
    model = model_override or settings.VP_ENRICH_MODEL

    logger.info(f"Calling {model} for VP step enrichment")

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

    # Log usage
    from app.core.llm_usage import log_llm_usage
    log_llm_usage(
        workflow="enrich_vp", model=response.model, provider="openai",
        tokens_input=response.usage.prompt_tokens, tokens_output=response.usage.completion_tokens,
        project_id=project_id,
    )

    raw_output = response.choices[0].message.content or ""

    # Try to parse and validate
    try:
        result = _parse_and_validate(raw_output, project_id, step_id, step_index)
        logger.info(f"Successfully parsed VP enrichment output for step {step_index}")
        logger.info(f"Evidence items: {len(result.evidence)}")
        for i, evidence in enumerate(result.evidence):
            logger.info(f"Evidence {i}: chunk_id={evidence.chunk_id}, excerpt='{evidence.excerpt[:50]}...'")
        return result
    except (json.JSONDecodeError, ValidationError) as e:
        error_msg = str(e)
        logger.warning(
            f"First VP enrichment attempt failed validation: {error_msg}",
            extra={"step_id": str(step_id)},
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
        result = _parse_and_validate(retry_output, project_id, step_id, step_index)
        logger.info("Retry succeeded", extra={"step_id": str(step_id)})
        return result
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(
            f"Retry also failed validation: {e}",
            extra={"step_id": str(step_id)},
        )
        # Do NOT leak raw model output in exception
        raise ValueError("Model output could not be validated to schema") from e


def _parse_and_validate(
    raw_output: str, project_id: UUID, step_id: UUID, step_index: int
) -> EnrichVPStepOutput:
    """Parse JSON string and validate against schema."""
    from app.core.llm import parse_llm_json_dict
    parsed = parse_llm_json_dict(raw_output)
    parsed["step_id"] = str(step_id)
    parsed["step_index"] = step_index
    return EnrichVPStepOutput.model_validate(parsed)
