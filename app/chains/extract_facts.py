"""LLM chain for extracting structured facts from signal chunks."""

import json
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from app.core.config import Settings
from app.core.fact_inputs import build_facts_prompt
from app.core.logging import get_logger
from app.core.schemas_facts import ExtractFactsOutput

logger = get_logger(__name__)


# System prompt for fact extraction
# ruff: noqa: E501
SYSTEM_PROMPT = """You are a requirements analyst AI. Your task is to extract structured facts from client signals.

You MUST output ONLY valid JSON matching this exact schema:

{
  "summary": "string - brief summary of what was extracted",
  "facts": [
    {
      "fact_type": "feature|constraint|persona|kpi|process|data_requirement|integration|risk|assumption",
      "title": "string - short title",
      "detail": "string - detailed description",
      "confidence": "low|medium|high",
      "evidence": [
        {
          "chunk_id": "uuid - must be from provided chunk_ids",
          "excerpt": "string - verbatim text from chunk (max 280 chars)",
          "rationale": "string - why this supports the fact"
        }
      ]
    }
  ],
  "open_questions": [
    {
      "question": "string",
      "why_it_matters": "string",
      "suggested_owner": "client|consultant|unknown",
      "evidence": []
    }
  ],
  "contradictions": [
    {
      "description": "string",
      "sides": ["string", "string"],
      "severity": "minor|important|critical",
      "evidence": [...]
    }
  ]
}

CRITICAL RULES:
1. Output ONLY the JSON object, no markdown, no explanation, no preamble.
2. Every fact MUST have at least one evidence reference.
3. Every contradiction MUST have at least one evidence reference.
4. evidence.chunk_id MUST be one of the chunk_ids provided in the user message.
5. evidence.excerpt MUST be copied verbatim from the chunk (max 280 characters).
6. Be precise - only extract facts clearly stated or strongly implied in the text.
7. If you cannot extract any facts, return an empty facts array with an explanatory summary."""


FIX_SCHEMA_PROMPT = """The previous output was invalid. Here is the error:

{error}

Here is your previous output:

{previous_output}

Please fix the output to match the required JSON schema exactly. Output ONLY valid JSON, no explanation."""


def extract_facts_from_chunks(
    *,
    signal: dict[str, Any],
    chunks: list[dict[str, Any]],
    settings: Settings,
    model_override: str | None = None,
) -> ExtractFactsOutput:
    """
    Extract structured facts from signal chunks using OpenAI.

    Args:
        signal: Signal dict with id, project_id, signal_type, source
        chunks: List of selected chunk dicts
        settings: Application settings
        model_override: Optional model name to use instead of settings.FACTS_MODEL

    Returns:
        ExtractFactsOutput with validated extraction results

    Raises:
        ValueError: If model output cannot be validated after retry
    """
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    user_prompt = build_facts_prompt(signal, chunks)

    # Use override if provided, else fall back to settings
    model = model_override or settings.FACTS_MODEL

    logger.info(
        f"Calling {model} for fact extraction",
        extra={"signal_id": str(signal.get("id")), "chunk_count": len(chunks)},
    )

    # First attempt
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw_output = response.choices[0].message.content or ""

    # Try to parse and validate
    try:
        return _parse_and_validate(raw_output)
    except (json.JSONDecodeError, ValidationError) as e:
        error_msg = str(e)
        logger.warning(
            f"First extraction attempt failed validation: {error_msg}",
            extra={"signal_id": str(signal.get("id"))},
        )

    # One retry with fix-to-schema prompt
    logger.info(
        "Attempting retry with fix-to-schema prompt",
        extra={"signal_id": str(signal.get("id"))},
    )

    fix_prompt = FIX_SCHEMA_PROMPT.format(error=error_msg, previous_output=raw_output)

    retry_response = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": raw_output},
            {"role": "user", "content": fix_prompt},
        ],
    )

    retry_output = retry_response.choices[0].message.content or ""

    try:
        result = _parse_and_validate(retry_output)
        logger.info(
            "Retry succeeded",
            extra={"signal_id": str(signal.get("id"))},
        )
        return result
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(
            f"Retry also failed validation: {e}",
            extra={"signal_id": str(signal.get("id"))},
        )
        # Do NOT leak raw model output in exception
        raise ValueError("Model output could not be validated to schema") from e


def _parse_and_validate(raw_output: str) -> ExtractFactsOutput:
    """
    Parse JSON string and validate against schema.

    Args:
        raw_output: Raw string from LLM

    Returns:
        Validated ExtractFactsOutput

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

    logger.debug(
        f"Parsing LLM output (length: {len(cleaned)})",
        extra={"output_preview": cleaned[:500] + "..." if len(cleaned) > 500 else cleaned},
    )

    try:
        parsed = json.loads(cleaned)
        logger.debug("JSON parsing succeeded")
        return ExtractFactsOutput.model_validate(parsed)
    except json.JSONDecodeError as e:
        logger.warning(
            f"JSON parsing failed: {e}",
            extra={"raw_output": raw_output, "cleaned_output": cleaned},
        )
        raise
    except ValidationError as e:
        logger.warning(
            f"Pydantic validation failed: {e}",
            extra={"parsed_json": json.loads(cleaned) if cleaned else None},
        )
        raise
