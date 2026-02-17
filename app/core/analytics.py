"""Server-side PostHog analytics wrapper.

No-op if POSTHOG_API_KEY is not set — safe for dev/test environments.
"""

from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

_posthog_client = None
_initialized = False


def _get_client():
    """Lazy-initialize PostHog client."""
    global _posthog_client, _initialized
    if _initialized:
        return _posthog_client

    _initialized = True
    try:
        from app.core.config import get_settings
        settings = get_settings()
        if not settings.POSTHOG_API_KEY:
            logger.debug("PostHog API key not set — analytics disabled")
            return None

        import posthog
        posthog.api_key = settings.POSTHOG_API_KEY
        posthog.host = settings.POSTHOG_HOST
        _posthog_client = posthog
        logger.info("PostHog analytics initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize PostHog: {e}")

    return _posthog_client


def track_server_event(
    user_id: str,
    event: str,
    properties: dict[str, Any] | None = None,
) -> None:
    """Track a server-side event in PostHog.

    No-op if PostHog is not configured.

    Args:
        user_id: The user ID (UUID string) to associate with the event
        event: Event name (e.g., 'facts_extracted', 'consultant_enriched')
        properties: Optional event properties dict
    """
    client = _get_client()
    if not client:
        return

    try:
        client.capture(
            distinct_id=user_id,
            event=event,
            properties=properties or {},
        )
    except Exception as e:
        logger.warning(f"Failed to track event '{event}': {e}")


def identify_user(
    user_id: str,
    properties: dict[str, Any] | None = None,
) -> None:
    """Identify a user in PostHog with person properties.

    Args:
        user_id: The user ID (UUID string)
        properties: Person properties to set (e.g., email, name, plan)
    """
    client = _get_client()
    if not client:
        return

    try:
        client.identify(
            distinct_id=user_id,
            properties=properties or {},
        )
    except Exception as e:
        logger.warning(f"Failed to identify user '{user_id}': {e}")
