"""LLM chain for reconciling canonical state with new signals."""

import json
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.reconcile_inputs import build_reconcile_prompt
from app.core.schemas_reconcile import ReconcileOutput

logger = get_logger(__name__)


# System prompt for reconciliation
# ruff: noqa: E501
SYSTEM_PROMPT = """You are a requirements reconciliation AI. Your task is to update canonical project state based on new client signals.

You MUST output ONLY valid JSON matching this exact schema:

{
  "summary": "string - brief summary of reconciliation changes",
  "prd_section_patches": [
    {
      "slug": "string - section slug (software_summary|personas|key_features|happy_path|constraints|...)",
      "set_fields": {"field_name": "value", ...} or null,
      "set_status": "draft|needs_confirmation|confirmed_consultant|confirmed_client" or null,
      "add_client_needs": [
        {
          "key": "string - stable key",
          "title": "string",
          "why": "string",
          "ask": "string",
          "priority": "low|medium|high",
          "suggested_method": "email|meeting",
          "evidence": [{"chunk_id": "uuid", "excerpt": "string", "rationale": "string"}]
        }
      ],
      "evidence": [{"chunk_id": "uuid", "excerpt": "string", "rationale": "string"}]
    }
  ],
  "vp_step_patches": [
    {
      "step_index": 1,
      "set": {"label": "...", "description": "...", ...} or null,
      "set_status": "draft|needs_confirmation|confirmed_consultant|confirmed_client" or null,
      "add_needed": [
        {
          "key": "string",
          "title": "string",
          "why": "string",
          "ask": "string",
          "priority": "low|medium|high",
          "suggested_method": "email|meeting",
          "evidence": [...]
        }
      ],
      "evidence": [...]
    }
  ],
  "feature_ops": [
    {
      "op": "upsert|deprecate",
      "name": "string - feature name",
      "category": "string",
      "is_mvp": true|false,
      "confidence": "low|medium|high",
      "set_status": "draft|needs_confirmation|confirmed_consultant|confirmed_client",
      "evidence": [...],
      "reason": "string - why this operation"
    }
  ],
  "confirmation_items": [
    {
      "key": "string - stable unique key",
      "kind": "prd|vp|feature|insight|gate",
      "title": "string",
      "why": "string",
      "ask": "string",
      "priority": "low|medium|high",
      "suggested_method": "email|meeting",
      "evidence": [...],
      "target_table": "string or null",
      "target_id": "string or null"
    }
  ]
}

CRITICAL RULES:
1. Output ONLY the JSON object, no markdown, no explanation, no preamble.
2. NEVER set status to "confirmed_client" automatically - only consultant can do that.
3. If new input conflicts with existing canonical, create confirmation item + set_status="needs_confirmation".
4. If input is additive and non-controversial, you may patch canonical but keep status="draft".
5. Every confirmation item must be answerable (clear ask).
6. Include evidence references (chunk_id + excerpt + rationale) when possible.
7. Evidence excerpts must be verbatim from chunks (max 280 chars).
8. If no changes are needed, return empty arrays with a summary explaining why."""


FIX_SCHEMA_PROMPT = """The previous output was invalid. Here is the error:

{error}

Here is your previous output:

{previous_output}

Please fix the output to match the required JSON schema exactly. Output ONLY valid JSON, no explanation."""


def reconcile_state(
    *,
    canonical_snapshot: dict[str, Any],
    delta_digest: dict[str, Any],
    retrieved_chunks: list[dict[str, Any]],
    settings: Settings,
    model_override: str | None = None,
) -> ReconcileOutput:
    """
    Reconcile canonical state with new signals using OpenAI.

    Args:
        canonical_snapshot: Current canonical state (prd_sections, vp_steps, features)
        delta_digest: New inputs (extracted_facts, insights)
        retrieved_chunks: Supporting context chunks
        settings: Application settings
        model_override: Optional model name to use instead of settings.STATE_MODEL

    Returns:
        ReconcileOutput with validated reconciliation results

    Raises:
        ValueError: If model output cannot be validated after retry
    """
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    user_prompt = build_reconcile_prompt(canonical_snapshot, delta_digest, retrieved_chunks)

    # Use override if provided, else fall back to settings
    model = model_override or settings.STATE_MODEL

    logger.info(
        f"Calling {model} for state reconciliation",
        extra={
            "prd_sections_count": len(canonical_snapshot.get("prd_sections", [])),
            "vp_steps_count": len(canonical_snapshot.get("vp_steps", [])),
            "features_count": len(canonical_snapshot.get("features", [])),
            "facts_count": delta_digest.get("facts_count", 0),
            "insights_count": delta_digest.get("insights_count", 0),
            "chunks_count": len(retrieved_chunks),
        },
    )

    # First attempt
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        max_tokens=16384,
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
            f"First reconciliation attempt failed validation: {error_msg}",
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
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": raw_output},
            {"role": "user", "content": fix_prompt},
        ],
    )

    retry_output = retry_response.choices[0].message.content or ""

    try:
        result = _parse_and_validate(retry_output)
        logger.info("Retry succeeded")
        return result
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(f"Retry also failed validation: {e}")
        # Do NOT leak raw model output in exception
        raise ValueError("Model output could not be validated to schema") from e


def _parse_and_validate(raw_output: str) -> ReconcileOutput:
    """
    Parse JSON string and validate against schema.

    Args:
        raw_output: Raw string from LLM

    Returns:
        Validated ReconcileOutput

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
    return ReconcileOutput.model_validate(parsed)

