"""Async chat routing telemetry — fire-and-forget insert per message.

Never blocks the response pipeline. Logs tier classification, latency,
token counts, cost estimates, and compression ratios.
"""

import asyncio
import time
from decimal import Decimal
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# Haiku 4.5 pricing (per 1M tokens)
_INPUT_COST_PER_M = Decimal("1.00")
_OUTPUT_COST_PER_M = Decimal("5.00")
_CACHE_READ_COST_PER_M = Decimal("0.10")

# Tier mapping from retrieval_strategy + fast_path
_STRATEGY_TO_TIER = {
    "fast_path": 1,
    "none": 2,
    "light": 3,
    "full": 4,
    "full+thinking": 5,
}


def compute_tier(
    retrieval_strategy: str,
    is_fast_path: bool = False,
    has_thinking: bool = False,
) -> int:
    """Map routing state to tier number."""
    if is_fast_path:
        return 1
    if has_thinking:
        return 5
    return _STRATEGY_TO_TIER.get(retrieval_strategy, 3)


def estimate_cost(
    tokens_in: int,
    tokens_out: int,
    cache_read: int = 0,
) -> Decimal:
    """Estimate cost in USD for a single message."""
    input_cost = Decimal(tokens_in - cache_read) * _INPUT_COST_PER_M / 1_000_000
    cache_cost = Decimal(cache_read) * _CACHE_READ_COST_PER_M / 1_000_000
    output_cost = Decimal(tokens_out) * _OUTPUT_COST_PER_M / 1_000_000
    return input_cost + cache_cost + output_cost


async def log_chat_routing(
    supabase: Any,
    project_id: str,
    conversation_id: str | None = None,
    message_id: str | None = None,
    raw_message: str = "",
    classified_tier: int = 3,
    retrieval_strategy: str = "light",
    classifier_source: str = "regex",
    intent_type: str = "discuss",
    complexity: str = "simple",
    latency_ms: int = 0,
    tokens_in: int = 0,
    tokens_out: int = 0,
    estimated_cost: Decimal | None = None,
    compressed_token_count: int | None = None,
    original_token_count: int | None = None,
) -> None:
    """Async insert into chat_routing_log. Fire-and-forget."""
    try:
        row = {
            "project_id": project_id,
            "raw_message": raw_message[:200],
            "classified_tier": classified_tier,
            "retrieval_strategy": retrieval_strategy,
            "classifier_source": classifier_source,
            "intent_type": intent_type,
            "complexity": complexity,
            "latency_ms": latency_ms,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "estimated_cost": str(estimated_cost or Decimal("0")),
        }
        if conversation_id:
            row["conversation_id"] = conversation_id
        if message_id:
            row["message_id"] = message_id
        if compressed_token_count is not None:
            row["compressed_token_count"] = compressed_token_count
        if original_token_count is not None:
            row["original_token_count"] = original_token_count

        await asyncio.to_thread(
            lambda: supabase.table("chat_routing_log").insert(row).execute()
        )
    except Exception as e:
        logger.debug(f"Chat routing log failed (non-fatal): {e}")


class RoutingTimer:
    """Context manager for timing chat routing latency."""

    def __init__(self):
        self.start_time: float = 0
        self.latency_ms: int = 0

    def __enter__(self):
        self.start_time = time.monotonic()
        return self

    def __exit__(self, *args):
        elapsed = time.monotonic() - self.start_time
        self.latency_ms = int(elapsed * 1000)
