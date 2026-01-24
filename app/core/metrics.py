"""Performance metrics and timing instrumentation.

Utilities for tracking and logging operation performance.
"""

import time
from contextlib import contextmanager
from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


@contextmanager
def timer(operation_name: str, project_id: Optional[str] = None, log_level: str = "info"):
    """
    Context manager for timing operations.

    Logs operation duration on completion.

    Args:
        operation_name: Name of the operation being timed
        project_id: Optional project UUID for context
        log_level: Log level ("debug", "info", "warning")

    Usage:
        with timer("DI Agent - Fetch state", str(project_id)):
            state = get_state_snapshot(project_id)

    Logs:
        INFO: ⏱️ DI Agent - Fetch state took 245.3ms
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000

        extra = {
            "operation": operation_name,
            "duration_ms": round(elapsed_ms, 1),
        }
        if project_id:
            extra["project_id"] = project_id

        log_msg = f"⏱️ {operation_name} took {elapsed_ms:.1f}ms"

        if log_level == "debug":
            logger.debug(log_msg, extra=extra)
        elif log_level == "warning":
            logger.warning(log_msg, extra=extra)
        else:
            logger.info(log_msg, extra=extra)


class PerformanceTracker:
    """
    Track performance metrics for complex operations.

    Accumulates metrics like DB calls, cache hits/misses, and duration.
    """

    def __init__(self, operation: str, project_id: Optional[str] = None):
        """
        Initialize performance tracker.

        Args:
            operation: Name of the operation being tracked
            project_id: Optional project UUID for context
        """
        self.operation = operation
        self.project_id = project_id
        self.start_time: Optional[float] = None
        self.db_calls = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.llm_calls = 0

    def start(self):
        """Start timing the operation."""
        self.start_time = time.perf_counter()

    def end(self) -> float:
        """
        End timing and log metrics.

        Returns:
            Duration in milliseconds
        """
        if not self.start_time:
            return 0

        elapsed_ms = (time.perf_counter() - self.start_time) * 1000

        extra = {
            "operation": self.operation,
            "duration_ms": round(elapsed_ms, 1),
            "db_calls": self.db_calls,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "llm_calls": self.llm_calls,
        }
        if self.project_id:
            extra["project_id"] = self.project_id

        logger.info(
            f"⏱️ {self.operation}: {elapsed_ms:.1f}ms "
            f"(DB: {self.db_calls}, Cache: {self.cache_hits}H/{self.cache_misses}M, LLM: {self.llm_calls})",
            extra=extra,
        )

        return elapsed_ms

    def record_db_call(self, count: int = 1):
        """
        Record database call(s).

        Args:
            count: Number of DB calls (default 1)
        """
        self.db_calls += count

    def record_cache_hit(self):
        """Record cache hit."""
        self.cache_hits += 1

    def record_cache_miss(self):
        """Record cache miss."""
        self.cache_misses += 1

    def record_llm_call(self):
        """Record LLM API call."""
        self.llm_calls += 1


@contextmanager
def track_performance(operation: str, project_id: Optional[str] = None):
    """
    Context manager for tracking operation performance with detailed metrics.

    Args:
        operation: Name of the operation
        project_id: Optional project UUID for context

    Yields:
        PerformanceTracker instance for recording metrics

    Usage:
        async def invoke_di_agent(project_id: UUID, ...):
            with track_performance("DI Agent Invocation", str(project_id)) as perf:
                # Fetch state
                state = await get_state_snapshot(project_id)
                perf.record_db_call()

                # Check cache
                cached = get_cached_readiness(project_id)
                if cached:
                    perf.record_cache_hit()
                else:
                    perf.record_cache_miss()

                # Call LLM
                response = await call_anthropic(...)
                perf.record_llm_call()

    Logs:
        INFO: ⏱️ DI Agent Invocation: 1245.3ms (DB: 3, Cache: 1H/2M, LLM: 1)
    """
    tracker = PerformanceTracker(operation, project_id)
    tracker.start()
    try:
        yield tracker
    finally:
        tracker.end()
