"""LLM client utilities for LangChain integration."""

import json
import re
from typing import TypeVar

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.core.config import get_settings

T = TypeVar("T", bound=BaseModel)


def get_llm(model: str | None = None, temperature: float = 0.1) -> ChatOpenAI:
    """
    Get configured LLM instance for LangChain chains.

    Args:
        model: Model name override (defaults to config setting)
        temperature: Temperature for generation (default 0.1)

    Returns:
        ChatOpenAI instance configured with API key and model
    """
    settings = get_settings()

    # Use provided model or fall back to config default
    model_name = model or settings.OPENAI_MODEL

    return ChatOpenAI(
        api_key=settings.OPENAI_API_KEY,
        model=model_name,
        temperature=temperature,
    )


def _strip_llm_fences(raw_output: str) -> str:
    """Strip markdown code fences from LLM output.

    Handles: ```json ... ```, ``` ... ```, leading/trailing whitespace.
    """
    cleaned = raw_output.strip()

    # Extract JSON from markdown code fences
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", cleaned, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()

    # Fallback: strip leading/trailing fences without regex
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


def parse_llm_json(raw_output: str, model: type[T]) -> T:
    """
    Parse LLM output as JSON and validate against a Pydantic model.

    Handles common LLM response quirks:
    - Markdown code fences (```json ... ```)
    - Leading/trailing whitespace
    - Multiple JSON blocks (takes the first)

    Args:
        raw_output: Raw string from LLM response
        model: Pydantic model class to validate against

    Returns:
        Validated Pydantic model instance

    Raises:
        json.JSONDecodeError: If JSON parsing fails after cleanup
        pydantic.ValidationError: If parsed JSON doesn't match schema
    """
    cleaned = _strip_llm_fences(raw_output)
    parsed = json.loads(cleaned)
    return model.model_validate(parsed)


def parse_llm_json_dict(raw_output: str) -> dict:
    """
    Parse LLM output as JSON, returning a raw dict.

    Use this when you need to inject extra fields before Pydantic validation.
    For direct-to-model parsing, use parse_llm_json() instead.

    Args:
        raw_output: Raw string from LLM response

    Returns:
        Parsed dict from JSON

    Raises:
        json.JSONDecodeError: If JSON parsing fails after cleanup
    """
    cleaned = _strip_llm_fences(raw_output)
    return json.loads(cleaned)
