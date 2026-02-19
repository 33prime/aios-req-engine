"""Centralized LLM usage logger for token/cost tracking."""

import logging
from uuid import UUID

from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

# Pricing per 1M tokens: (input, output)
MODEL_PRICING: dict[str, tuple[float, float]] = {
    # Anthropic
    "claude-opus-4-6": (15.0, 75.0),
    "claude-opus-4-5-20251101": (15.0, 75.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-sonnet-4-5-20250929": (3.0, 15.0),
    "claude-sonnet-4-20250514": (3.0, 15.0),
    "claude-haiku-4-5-20251001": (0.80, 4.0),
    "claude-3-5-haiku-20241022": (0.80, 4.0),
    "claude-3-5-sonnet-20241022": (3.0, 15.0),
    # OpenAI
    "gpt-4o": (2.50, 10.0),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4o-mini": (0.15, 0.60),
    # Perplexity
    "sonar-pro": (5.0, 15.0),
}


def _estimate_cost(
    model: str,
    tokens_input: int,
    tokens_output: int,
    tokens_cache_read: int = 0,
) -> float:
    """Estimate cost in USD based on model pricing."""
    pricing = MODEL_PRICING.get(model)
    if not pricing:
        # Try prefix match for model variants
        for key, val in MODEL_PRICING.items():
            if model.startswith(key.rsplit("-", 1)[0]):
                pricing = val
                break
    if not pricing:
        logger.warning(f"No pricing found for model '{model}', using $0")
        return 0.0

    input_rate, output_rate = pricing
    # Cache reads are typically 90% cheaper
    cache_discount = 0.1
    effective_input = (tokens_input - tokens_cache_read) + (tokens_cache_read * cache_discount)
    cost = (effective_input * input_rate / 1_000_000) + (tokens_output * output_rate / 1_000_000)
    return round(cost, 6)


def log_llm_usage(
    workflow: str,
    model: str,
    provider: str,
    tokens_input: int,
    tokens_output: int,
    duration_ms: int = 0,
    user_id: UUID | str | None = None,
    project_id: UUID | str | None = None,
    job_id: UUID | str | None = None,
    chain: str | None = None,
    tokens_cache_read: int = 0,
    tokens_cache_create: int = 0,
) -> None:
    """Log an LLM call to the usage tracking table. Fire-and-forget."""
    try:
        estimated_cost = _estimate_cost(model, tokens_input, tokens_output, tokens_cache_read)

        row = {
            "workflow": workflow,
            "model": model,
            "provider": provider,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "tokens_cache_read": tokens_cache_read,
            "tokens_cache_create": tokens_cache_create,
            "estimated_cost_usd": estimated_cost,
            "duration_ms": duration_ms,
        }

        if user_id:
            row["user_id"] = str(user_id)
        if project_id:
            row["project_id"] = str(project_id)
        if job_id:
            row["job_id"] = str(job_id)
        if chain:
            row["chain"] = chain

        client = get_supabase()
        client.table("llm_usage_log").insert(row).execute()

        logger.debug(
            f"LLM usage logged: {workflow}/{chain or '-'} "
            f"model={model} tokens={tokens_input}+{tokens_output} "
            f"cost=${estimated_cost:.4f}"
        )
    except Exception as e:
        # Never fail the main operation due to logging
        logger.error(f"Failed to log LLM usage: {e}")
