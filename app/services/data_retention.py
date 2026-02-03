"""Data retention service.

Enforces retention policies for communication data:
- Raw email bodies: 0 days (never stored — processed in memory only)
- Sanitized signal text: 90 days → delete signals.raw_text, keep entities
- Recording/transcript URLs: 14 days → null out
- Email routing tokens: 7 days auto-expire → deactivate
- Consent logs: 3 years → archive (no-op for now)
"""

from datetime import UTC, datetime, timedelta

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def enforce_all_retention_policies() -> dict:
    """
    Run all retention policies.

    Called by cron endpoint (super_admin only).

    Returns:
        Dict with counts of records processed per policy
    """
    results = {}

    results["recording_urls_nulled"] = _enforce_recording_retention()
    results["tokens_deactivated"] = _enforce_token_retention()
    results["signals_scrubbed"] = _enforce_signal_retention()

    logger.info(f"Retention enforcement complete: {results}")
    return results


def _enforce_recording_retention() -> int:
    """Null out recording/transcript URLs past retention period."""
    from app.db import meeting_bots as bot_db

    settings = get_settings()
    return bot_db.null_expired_urls(days=settings.RECORDING_RETENTION_DAYS)


def _enforce_token_retention() -> int:
    """Deactivate expired email routing tokens."""
    from app.db import email_routing_tokens as token_db

    return token_db.deactivate_expired_tokens()


def _enforce_signal_retention() -> int:
    """
    Scrub raw_text from email/transcript signals past retention period.

    Keeps extracted entities (features, personas, etc.) but removes the
    original signal text.
    """
    settings = get_settings()
    retention_days = settings.SANITIZED_SOURCE_RETENTION_DAYS

    if retention_days <= 0:
        return 0

    from app.db.supabase_client import get_supabase

    supabase = get_supabase()
    cutoff = (datetime.now(UTC) - timedelta(days=retention_days)).isoformat()

    # Only scrub email and transcript signals
    result = (
        supabase.table("signals")
        .update({"raw_text": "[REDACTED - retention policy]"})
        .in_("signal_type", ["email", "meeting_transcript"])
        .lt("created_at", cutoff)
        .neq("raw_text", "[REDACTED - retention policy]")
        .execute()
    )

    count = len(result.data) if result.data else 0
    if count:
        logger.info(f"Scrubbed raw_text from {count} signals older than {retention_days} days")
    return count
