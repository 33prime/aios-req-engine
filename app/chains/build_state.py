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
SYSTEM_PROMPT = """You are a product requirements architect AI. Your task is to build structured Value Path steps, Features, and Personas from extracted facts and signal chunks.

You MUST output ONLY valid JSON matching this exact schema:

{
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
  ],
  "personas": [
    {
      "slug": "string - stable identifier (e.g., 'sales-representative')",
      "name": "string - persona name (e.g., 'Sales Representative')",
      "role": "string - role/title",
      "demographics": {"age_range": "string", "location": "string", ...},
      "psychographics": {"tech_savviness": "string", "motivations": "string", ...},
      "goals": ["string - persona goal 1", "string - goal 2", ...],
      "pain_points": ["string - pain point 1", "string - pain point 2", ...],
      "description": "string - brief persona description"
    }
  ]
}

CRITICAL RULES:
1. Output ONLY the JSON object, no markdown, no explanation, no preamble.
2. The JSON MUST have 3 top-level keys: "vp_steps", "features", and "personas" (all required).
3. Create at least 7 Value Path steps describing the user workflow.
4. Create at least 8 Key Features with appropriate categories.
5. Create at least 2 Persona entities with structured data (slug, name, role, demographics, psychographics, goals, pain_points, description).
6. NEVER omit the "personas" array - it is REQUIRED and must have at least 2 items.
7. All items MUST have status="draft" (never confirmed_client).
8. Each vp_step and feature should have evidence entries with chunk_ids when relevant content exists in the provided chunks.
9. evidence.chunk_id MUST be one of the chunk_ids provided in the user message.
10. evidence.excerpt MUST be copied verbatim from the chunk (max 280 characters).
11. If something is uncertain, add it to needed arrays instead of making assumptions.
12. Be specific and actionable - avoid vague statements.
13. Prioritize chunks with authority='client' over authority='research'.
14. Persona slugs should be lowercase-hyphenated (e.g., 'sales-representative', 'sales-manager').
15. Demographics and psychographics should include relevant attributes like age range, tech savviness, motivations, etc.
16. Persona goals and pain_points should be specific to their role and how they interact with the software."""


FIX_SCHEMA_PROMPT = """The previous output was invalid. Here is the error:

{error}

Here is your previous output:

{previous_output}

CRITICAL FIX REQUIRED:
- Your JSON is MISSING the "personas" field. You MUST include it.
- The "personas" field must be an array with at least 2 persona objects.
- Each persona must have: slug, name, role, demographics, psychographics, goals, pain_points, description.
- Example persona structure:
  {{
    "slug": "sales-manager",
    "name": "Sales Manager",
    "role": "Sales team leader",
    "demographics": {{"age_range": "30-45", "location": "USA"}},
    "psychographics": {{"tech_savviness": "medium", "motivations": "efficiency"}},
    "goals": ["Close deals faster", "Track team performance"],
    "pain_points": ["Manual data entry", "Lack of visibility"],
    "description": "Manages sales team and oversees deal pipeline"
  }}

Please fix the output to match the required JSON schema exactly. Output ONLY valid JSON with ALL required fields including personas, no explanation."""


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
            max_tokens=16384,  # Increased for larger outputs with 7+ VP steps, 8+ features, personas
        )

        # Log usage
        from app.core.llm_usage import log_llm_usage
        log_llm_usage(
            workflow="build_state", model=response.model, provider="openai",
            tokens_input=response.usage.prompt_tokens, tokens_output=response.usage.completion_tokens,
        )

        output_text = response.choices[0].message.content or ""

        # Log if output was truncated
        finish_reason = response.choices[0].finish_reason
        if finish_reason == "length":
            logger.warning(
                "LLM output was truncated due to token limit. Increase max_tokens.",
                extra={"finish_reason": finish_reason, "output_length": len(output_text)},
            )

        # Log a sample of the output for debugging
        logger.info(
            f"LLM output preview (first 500 chars): {output_text[:500]}...",
            extra={"output_length": len(output_text), "finish_reason": finish_reason},
        )

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
                max_tokens=16384,  # Increased for larger outputs with 7+ VP steps, 8+ features, personas
            )

            fixed_output = fix_response.choices[0].message.content or ""

            # Log retry output
            logger.info(
                f"Retry output preview (first 500 chars): {fixed_output[:500]}...",
                extra={"output_length": len(fixed_output)},
            )

            return _parse_and_validate(fixed_output)

        except (json.JSONDecodeError, ValidationError) as retry_error:
            logger.error(f"Retry also failed: {retry_error}")
            raise ValueError(f"Failed to parse state builder output after retry: {retry_error}") from retry_error


def _parse_and_validate(output: str) -> BuildStateOutput:
    """Parse and validate LLM output."""
    from app.core.llm import parse_llm_json
    return parse_llm_json(output, BuildStateOutput)

