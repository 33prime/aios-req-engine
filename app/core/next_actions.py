"""Compute next best actions from BRD state. Pure logic, no LLM.

Legacy wrapper — delegates to the unified action engine for new action types,
while preserving the exact same return shape for backward compatibility.
"""

import logging

from app.core.action_engine import (
    ROLE_DOMAINS,
    _compute_brd_gap_actions,
    compute_actions_from_inputs as _engine_from_inputs,
)

logger = logging.getLogger(__name__)

# Re-export for any imports that depend on this module
CRITICAL_ROLES = [
    "CFO", "Finance Director",
    "CTO", "Tech Lead",
    "Operations Manager", "COO",
    "Compliance Officer",
    "Product Owner",
]


def compute_next_actions(
    brd_data: dict,
    stakeholders: list,
    completeness: dict | None = None,
) -> list[dict]:
    """Compute top 3 highest-impact recommended actions from BRD state.

    Args:
        brd_data: Full BRD workspace data dict
        stakeholders: List of stakeholder dicts
        completeness: Completeness scoring data (optional)

    Returns:
        Top 3 actions sorted by impact_score (legacy dict shape)
    """
    actions = _compute_brd_gap_actions(brd_data, stakeholders, completeness)
    actions.sort(key=lambda a: a.impact_score, reverse=True)
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


def _role_domain(role: str) -> str:
    """Map role to knowledge domain description."""
    return ROLE_DOMAINS.get(role, "domain-specific decisions")
