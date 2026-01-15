"""Hard caps for readiness scoring.

Caps are non-negotiable limits that override the weighted score
when critical prerequisites are missing.

Philosophy: Some things are so important that their absence
should dramatically limit the readiness score, regardless of
how well other areas are doing.
"""

from dataclasses import dataclass

from app.core.readiness.types import CapApplied


@dataclass
class Cap:
    """Definition of a hard cap rule."""

    id: str
    limit: int  # Maximum score when this cap applies
    reason: str
    check: callable  # Function that returns True if cap should apply


# =============================================================================
# Cap Definitions
# =============================================================================

CAPS = [
    Cap(
        id="no_value_path",
        limit=50,
        reason="Cannot be prototype-ready without a Value Path",
        check=lambda ctx: len(ctx["vp_steps"]) == 0,
    ),
    Cap(
        id="no_client_input",
        limit=70,
        reason="Need client validation via signals or meetings",
        check=lambda ctx: (
            len(ctx["client_signals"]) == 0 and len(ctx["completed_meetings"]) == 0
        ),
    ),
    Cap(
        id="zero_confirmations",
        limit=60,
        reason="No entities have been reviewed by a human",
        check=lambda ctx: ctx["confirmed_count"] == 0 and ctx["total_count"] > 0,
    ),
    Cap(
        id="no_wow_moment",
        limit=75,
        reason="Value path lacks a compelling value climax",
        check=lambda ctx: ctx["wow_score"] < 50 and len(ctx["vp_steps"]) > 0,
    ),
]


def apply_caps(
    raw_score: float,
    vp_steps: list[dict],
    client_signals: list[dict],
    completed_meetings: list[dict],
    confirmed_count: int,
    total_count: int,
    wow_score: float,
) -> tuple[float, list[CapApplied]]:
    """
    Apply hard caps to the raw score.

    Args:
        raw_score: The weighted score before caps
        vp_steps: List of VP step dicts
        client_signals: List of signals from client
        completed_meetings: List of completed meetings
        confirmed_count: Number of confirmed entities
        total_count: Total number of entities
        wow_score: Score for the wow_moment factor (0-100)

    Returns:
        Tuple of (final_score, list of caps that were applied)
    """
    # Build context for cap checks
    ctx = {
        "vp_steps": vp_steps,
        "client_signals": client_signals,
        "completed_meetings": completed_meetings,
        "confirmed_count": confirmed_count,
        "total_count": total_count,
        "wow_score": wow_score,
    }

    caps_applied: list[CapApplied] = []
    final_score = raw_score

    # Check each cap
    for cap in CAPS:
        if cap.check(ctx):
            if final_score > cap.limit:
                caps_applied.append(
                    CapApplied(
                        cap_id=cap.id,
                        limit=cap.limit,
                        reason=cap.reason,
                    )
                )
                final_score = min(final_score, cap.limit)

    # Sort caps by limit (most restrictive first)
    caps_applied.sort(key=lambda c: c.limit)

    return final_score, caps_applied
