"""Thread-safe TTL cache for shared enrichment context.

When multiple enrichment graphs run in parallel, they independently call
get_state_snapshot(), list_latest_extracted_facts(), and list_confirmation_items()
with identical parameters. This cache eliminates redundant DB reads.
"""

import threading
from time import monotonic
from typing import Any
from uuid import UUID

_lock = threading.Lock()
_cache: dict[str, tuple[Any, float]] = {}
_TTL_SECONDS = 30


def _get_or_compute(key: str, compute_fn) -> Any:
    """Get from cache or compute and cache the result."""
    now = monotonic()
    with _lock:
        if key in _cache:
            value, ts = _cache[key]
            if now - ts < _TTL_SECONDS:
                return value

    # Compute outside the lock to avoid blocking
    result = compute_fn()

    with _lock:
        _cache[key] = (result, monotonic())
    return result


def cached_state_snapshot(project_id: UUID) -> str:
    """Thread-safe cached get_state_snapshot."""
    from app.core.state_snapshot import get_state_snapshot

    return _get_or_compute(
        f"snapshot:{project_id}",
        lambda: get_state_snapshot(project_id),
    )


def cached_extracted_facts(project_id: UUID, limit: int = 10) -> list:
    """Thread-safe cached list_latest_extracted_facts."""
    from app.db.facts import list_latest_extracted_facts

    return _get_or_compute(
        f"facts:{project_id}:{limit}",
        lambda: list_latest_extracted_facts(project_id, limit=limit),
    )


def cached_confirmation_items(project_id: UUID) -> list:
    """Thread-safe cached list_confirmation_items."""
    from app.db.confirmations import list_confirmation_items

    return _get_or_compute(
        f"confirmations:{project_id}",
        lambda: list_confirmation_items(project_id),
    )


def invalidate_project(project_id: UUID) -> None:
    """Clear all cached entries for a project."""
    prefix = str(project_id)
    with _lock:
        keys_to_remove = [k for k in _cache if prefix in k]
        for k in keys_to_remove:
            del _cache[k]
