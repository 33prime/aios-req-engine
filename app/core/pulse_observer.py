"""Pulse observer — fire-and-forget pulse snapshot recording.

Consumers call `record_pulse_snapshot()` after events that change project
state (signal processing, batch confirmation, etc.). Never fatal — all
errors are logged as warnings and swallowed.

Usage:
    asyncio.create_task(record_pulse_snapshot(project_id, trigger="signal_processed"))
"""

from __future__ import annotations

import logging
from uuid import UUID

logger = logging.getLogger(__name__)


async def record_pulse_snapshot(project_id: UUID, trigger: str = "manual") -> None:
    """Compute and persist a pulse snapshot. Never raises."""
    try:
        from app.core.pulse_engine import compute_project_pulse
        from app.db.pulse import save_pulse_snapshot

        pulse = await compute_project_pulse(project_id)
        pulse_dict = pulse.model_dump(mode="json")
        save_pulse_snapshot(project_id, pulse_dict, trigger=trigger)

        logger.debug(
            f"Pulse snapshot recorded for project {project_id} (trigger={trigger})"
        )
    except Exception as e:
        logger.warning(f"Pulse observer failed (non-fatal): {e}")
