"""LLM chain for building canonical state from facts and chunks."""

import json
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.schemas_state import BuildStateOutput
from app.core.state_inputs import build_state_prompt

logger = get_logger(__name__)


# System prompt for state building
# ruff: noqa: E501
SYSTEM_PROMPT = """You are a product requirements architect AI. Your task is to build structured PRD sections, Value Path steps, and Features from extracted facts and signal chunks.

You MUST output ONLY valid JSON matching this exact schema:

{
  "prd_sections": [
    {
      "slug": "string - section identifier (e.g., software_summary, personas, key_features, happy_path, constraints)",
      "label": "string - human-readable label",
      "required": boolean - true for software_summary/personas/key_features/happy_path,
      "status": "draft",
      "fields": {
        "content": "string - main section content",
        ... other section-specific fields
      },
      "client_needs": [
        {
          "key": "string - unique key",
          "title": "string - what is needed",
          "why": "string - why it matters",
          "ask": "string - specific question to ask client"
        }
      ],
      "sources": [],
      "evidence": [
        {
          "chunk_id": "uuid - must be from provided chunk_ids",
          "excerpt": "string - verbatim text from chunk (max 280 chars)",
          "rationale": "string - why this supports the section"
        }
      ]
    }
  ],
  "vp_steps": [
    {
      "step_index": number - step number (1, 2, 3...),
      "label": "string - step label (e.g., Step 1 — ...)",
      "status": "draft",
      "description": "string - what happens in this step",
      "user_benefit_pain": "string - user benefit or pain addressed",
      "ui_overview": "string - UI elements involved",
      "value_created": "string - value created by this step",
      "kpi_impact": "string - KPI impact",
      "needed": [
        {
          "key": "string - unique key",
          "title": "string - what is needed",
          "why": "string - why it matters",
          "ask": "string - specific question"
        }
      ],
      "sources": [],
      "evidence": [...]
    }
  ],
  "features": [
    {
      "name": "string - feature name",
      "category": "string - feature category (e.g., Core, Security, Integration, UX)",
      "is_mvp": boolean - true if MVP feature,
      "confidence": "low|medium|high",
      "status": "draft",
      "evidence": [...]
    }
  ]
}

CRITICAL RULES:
1. Output ONLY the JSON object, no markdown, no explanation, no preamble.
2. Create at least 4 PRD sections (software_summary, personas, key_features, happy_path are required).
3. Create at least 3 Value Path steps describing the user workflow.
4. Create at least 5 Key Features with appropriate categories.
5. All items MUST have status="draft" (never confirmed_client).
6. Set required=true for software_summary, personas, key_features, and happy_path sections.
7. evidence.chunk_id MUST be one of the chunk_ids provided in the user message.
8. evidence.excerpt MUST be copied verbatim from the chunk (max 280 characters).
9. If something is uncertain, add it to client_needs or needed arrays instead of making assumptions.
10. Be specific and actionable - avoid vague statements.
11. Prioritize chunks with authority='client' over authority='research'.
12. software_summary section should contain a brief overview of the software (2-3 paragraphs): what the software is and what problem it solves, key capabilities and features (high-level), and target users and their primary use cases.
13. Generate constraints section if technical, security, or business constraints are mentioned in the facts."""


FIX_SCHEMA_PROMPT = """The previous output was invalid. Here is the error:

{error}

Here is your previous output:

{previous_output}

Please fix the output to match the required JSON schema exactly. Output ONLY valid JSON, no explanation."""


def run_build_state_chain(
    *,
    facts_digest: str,
    chunks: list[dict[str, Any]],
    settings: Settings,
    model_override: str | None = None,
) -> BuildStateOutput:
    """
    Run the state builder LLM chain.

    Args:
        facts_digest: Compact summary of extracted facts
        chunks: List of chunk dicts with chunk_id, content, metadata
        settings: Application settings
        model_override: Optional model override

    Returns:
        BuildStateOutput with prd_sections, vp_steps, and features

    Raises:
        ValueError: If LLM output cannot be parsed after retry
    """
    model = model_override or settings.STATE_BUILDER_MODEL
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # Build user prompt
    user_prompt = build_state_prompt(facts_digest, chunks)

    logger.info(
        f"Calling {model} for state building",
        extra={
            "model": model,
            "chunks_count": len(chunks),
        },
    )

    # First attempt
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
        )

        output_text = response.choices[0].message.content or ""
        return _parse_and_validate(output_text)

    except (json.JSONDecodeError, ValidationError) as e:
        logger.warning(f"First attempt failed, retrying with fix prompt: {e}")

        # Retry with fix prompt
        try:
            fix_response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                    {"role": "assistant", "content": output_text},
                    {
                        "role": "user",
                        "content": FIX_SCHEMA_PROMPT.format(
                            error=str(e),
                            previous_output=output_text[:1000],
                        ),
                    },
                ],
                temperature=0.1,
            )

            fixed_output = fix_response.choices[0].message.content or ""
            return _parse_and_validate(fixed_output)

        except (json.JSONDecodeError, ValidationError) as retry_error:
            logger.error(f"Retry also failed: {retry_error}")
            raise ValueError(f"Failed to parse state builder output after retry: {retry_error}") from retry_error


def _parse_and_validate(output: str) -> BuildStateOutput:
    """Parse and validate LLM output."""
    # Strip markdown code blocks if present
    output = output.strip()
    if output.startswith("```"):
        lines = output.split("\n")
        output = "\n".join(lines[1:-1]) if len(lines) > 2 else output

    data = json.loads(output)
    return BuildStateOutput.model_validate(data)

