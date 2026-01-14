"""Simple in-memory rate limiter for API endpoints."""

import time
from collections import defaultdict
from typing import Dict, Tuple
from uuid import UUID

from fastapi import HTTPException

from app.core.logging import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """
    Simple token bucket rate limiter.

    Tracks requests per key (e.g., project_id) and enforces limits.
    Uses in-memory storage - for production, consider Redis.
    """

    def __init__(self, requests_per_minute: int = 10, burst_size: int = 15):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Sustained rate limit
            burst_size: Maximum burst size
        """
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.refill_rate = requests_per_minute / 60.0  # tokens per second

        # Storage: key -> (tokens, last_refill_time)
        self._buckets: Dict[str, Tuple[float, float]] = defaultdict(lambda: (burst_size, time.time()))

        # Track request counts for metrics
        self._request_counts: Dict[str, int] = defaultdict(int)

    def _refill_bucket(self, key: str) -> None:
        """
        Refill tokens in bucket based on elapsed time.

        Args:
            key: Rate limit key (e.g., project_id)
        """
        current_tokens, last_refill = self._buckets[key]
        now = time.time()

        # Calculate tokens to add
        elapsed = now - last_refill
        tokens_to_add = elapsed * self.refill_rate

        # Cap at burst size
        new_tokens = min(self.burst_size, current_tokens + tokens_to_add)

        self._buckets[key] = (new_tokens, now)

    def check_limit(self, key: str, cost: float = 1.0) -> bool:
        """
        Check if request is allowed under rate limit.

        Args:
            key: Rate limit key (e.g., project_id)
            cost: Token cost for this request (default 1.0)

        Returns:
            True if allowed, False if rate limited

        Raises:
            HTTPException: 429 if rate limited
        """
        # Refill bucket
        self._refill_bucket(key)

        current_tokens, last_refill = self._buckets[key]

        # Check if enough tokens
        if current_tokens >= cost:
            # Consume tokens
            self._buckets[key] = (current_tokens - cost, last_refill)
            self._request_counts[key] += 1
            return True
        else:
            # Rate limited
            retry_after = int((cost - current_tokens) / self.refill_rate) + 1

            logger.warning(
                f"Rate limit exceeded for key: {key}, "
                f"tokens: {current_tokens:.2f}/{self.burst_size}, "
                f"retry after: {retry_after}s"
            )

            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )

    def get_stats(self, key: str) -> Dict[str, any]:
        """
        Get rate limit stats for a key.

        Args:
            key: Rate limit key

        Returns:
            Dictionary with stats
        """
        self._refill_bucket(key)
        current_tokens, _ = self._buckets[key]

        return {
            "tokens_remaining": int(current_tokens),
            "burst_size": self.burst_size,
            "requests_per_minute": self.requests_per_minute,
            "total_requests": self._request_counts.get(key, 0),
        }

    def reset(self, key: str) -> None:
        """
        Reset rate limit for a key.

        Args:
            key: Rate limit key
        """
        if key in self._buckets:
            del self._buckets[key]
        if key in self._request_counts:
            del self._request_counts[key]

        logger.info(f"Rate limit reset for key: {key}")


# Global rate limiter instances
chat_rate_limiter = RateLimiter(
    requests_per_minute=10,  # 10 requests per minute per project
    burst_size=15,  # Allow bursts up to 15 requests
)


def check_chat_rate_limit(project_id: UUID) -> None:
    """
    Check rate limit for chat endpoint.

    Args:
        project_id: Project UUID

    Raises:
        HTTPException: 429 if rate limited
    """
    key = f"chat:{str(project_id)}"
    chat_rate_limiter.check_limit(key)


def get_chat_rate_limit_stats(project_id: UUID) -> Dict[str, any]:
    """
    Get rate limit stats for chat endpoint.

    Args:
        project_id: Project UUID

    Returns:
        Rate limit stats
    """
    key = f"chat:{str(project_id)}"
    return chat_rate_limiter.get_stats(key)
