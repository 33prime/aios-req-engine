"""Red-team LLM chain for insight extraction."""

import json
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.redteam_inputs import build_redteam_prompt
from app.core.schemas_redteam import RedTeamOutput

logger = get_logger(__name__)


SYSTEM_PROMPT = """You are a critical red-team analyst for software requirements.
Your task is to identify issues, risks, and gaps in the requirements.

You MUST output ONLY valid JSON matching this exact schema:
```json
{
  "insights": [
    {
      "severity": "minor|important|critical",
      "category": "logic|ux|security|data|reporting|scope|ops",
      "title": "string - short title",
      "finding": "string - what is wrong",
      "why": "string - why it matters",
      "suggested_action": "apply_internally|needs_confirmation",
      "targets": [
        {
          "kind": "requirement|fact|signal|chunk|general",
          "id": "string or null",
          "label": "string - human readable label"
        }
      ],
      "evidence": [
        {
          "chunk_id": "uuid - from provided chunks",
          "excerpt": "string - direct quote, max 280 chars",
          "rationale": "string - why this is evidence"
        }
      ]
    }
  ]
}
```

Rules:
- Every insight MUST have at least one evidence reference.
- Evidence chunk_id MUST be from the provided chunks.
- Evidence excerpt MUST be a direct quote from the chunk content.
- Focus on actionable issues, not minor stylistic concerns.
- Authority model: client authority = ground truth, research = context only.
- If you find no issues, return {"insights": []}.
"""

FIX_SCHEMA_PROMPT = """The previous output failed schema validation.
Error details:
{error}

Original invalid output:
{previous_output}

Please fix the output to match the required JSON schema exactly. Output ONLY valid JSON."""


def _parse_and_validate(output: str) -> RedTeamOutput:
    """Parse JSON output and validate against schema."""
    data = json.loads(output)
    return RedTeamOutput.model_validate(data)


def run_redteam_chain(
    *,
    facts_digest: str,
    chunks: list[dict[str, Any]],
    settings: Settings,
    model_override: str | None = None,
) -> RedTeamOutput:
    """
    Run red-team analysis using OpenAI.

    Args:
        facts_digest: Compact summary of extracted facts
        chunks: List of chunk dicts for context
        settings: Application settings
        model_override: Optional model name override

    Returns:
        RedTeamOutput with validated insights

    Raises:
        ValueError: If model output cannot be validated after retry
    """
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    user_prompt = build_redteam_prompt(facts_digest, chunks)
    model_to_use = model_override or settings.REDTEAM_MODEL

    logger.info(
        f"Calling {model_to_use} for red-team analysis",
        extra={"chunk_count": len(chunks)},
    )

    # First attempt
    response = client.chat.completions.create(
        model=model_to_use,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw_output = response.choices[0].message.content or ""

    try:
        return _parse_and_validate(raw_output)
    except (json.JSONDecodeError, ValidationError) as e:
        error_msg = str(e)
        logger.warning(f"First red-team attempt failed validation: {error_msg}")

    # One retry with fix-to-schema prompt
    logger.info("Attempting retry with fix-to-schema prompt")

    fix_prompt = FIX_SCHEMA_PROMPT.format(error=error_msg, previous_output=raw_output)

    retry_response = client.chat.completions.create(
        model=model_to_use,
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
        logger.info("Red-team retry succeeded")
        return result
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(f"Second red-team attempt failed validation: {e}")
        raise ValueError("Model output could not be validated to schema") from e
