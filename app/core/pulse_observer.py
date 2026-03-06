"""Pulse observer — debounced fire-and-forget pulse snapshot recording.

Consumers call `record_pulse_snapshot_debounced()` after events that change
project state (signal processing, batch confirmation, etc.). The debouncer
waits 3 seconds after the last call before computing, preventing rapid-fire
pulse computations from transcript processing.

Usage:
    asyncio.create_task(record_pulse_snapshot_debounced(project_id, trigger="signal_processed"))
"""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

logger = logging.getLogger(__name__)

_DEBOUNCE_SECONDS = 3.0
_pending_projects: dict[str, asyncio.Task] = {}


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


async def record_pulse_snapshot_debounced(
    project_id: UUID, trigger: str = "manual"
) -> None:
    """Debounced pulse recording. Waits 3s after last call before computing.

    Multiple calls within the debounce window are collapsed into a single
    pulse computation, preventing burst processing from transcript extraction.
    """
    pid = str(project_id)

    # Cancel any pending computation
    existing = _pending_projects.get(pid)
    if existing and not existing.done():
        existing.cancel()

    async def _delayed_compute():
        try:
            await asyncio.sleep(_DEBOUNCE_SECONDS)
            await record_pulse_snapshot(project_id, trigger)
        except asyncio.CancelledError:
            pass  # Normal — debounce cancelled by newer call
        except Exception as e:
            logger.warning(f"Debounced pulse failed (non-fatal): {e}")
        finally:
            _pending_projects.pop(pid, None)

    _pending_projects[pid] = asyncio.create_task(_delayed_compute())
