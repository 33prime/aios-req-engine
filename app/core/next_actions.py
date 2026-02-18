"""Compute next best actions from BRD state. Pure logic, no LLM.

Legacy wrapper — delegates to the unified action engine v2.
Preserves the exact same return shape for backward compatibility.
"""

import logging

from app.core.action_engine import compute_actions_from_inputs as _engine_from_inputs

logger = logging.getLogger(__name__)


def compute_next_actions(
    brd_data: dict,
    stakeholders: list,
    completeness: dict | None = None,
) -> list[dict]:
    """Compute top 3 highest-impact recommended actions from BRD state.

    Legacy entry point — builds inputs dict from BRD data and delegates
    to the v2 engine's sync path.
    """
    requirements = brd_data.get("requirements", {})
    business_context = brd_data.get("business_context", {})

    # Build inputs dict that compute_actions_from_inputs expects
    inputs: dict = {
        "has_vision": bool(business_context.get("vision")),
        "kpi_count": len(business_context.get("success_metrics", [])),
        "workflow_count": len(brd_data.get("workflow_pairs", [])),
    }

    actions = _engine_from_inputs(inputs)
    return [a.to_legacy_dict() for a in actions[:3]]


def compute_next_actions_from_inputs(inputs: dict) -> list[dict]:
    """Compute top actions from pre-aggregated SQL inputs (lightweight).

    Args:
        inputs: Dict from get_batch_next_action_inputs RPC containing counts and flags.

    Returns:
        Top 3 actions sorted by impact_score (legacy dict shape).
    """
    unified_actions = _engine_from_inputs(inputs)
    return [a.to_legacy_dict() for a in unified_actions[:3]]
