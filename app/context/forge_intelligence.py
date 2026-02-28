"""Forge intelligence loader — cached module matches for prompt compiler.

Runs as part of assemble_chat_context() parallel tasks. Loads persisted
Forge matches for the project and formats them for prompt inclusion.
"""

from __future__ import annotations

import asyncio

from app.core.logging import get_logger

logger = get_logger(__name__)


async def load_forge_intelligence(project_id: str, phase: str) -> dict:
    """Load Forge module intelligence for prompt compiler.

    Returns dict with:
    - matched_modules: [{feature_name, module_name, category, stage_decisions}]
    - decision_slots: [{module, decision_key, question, impact}] filtered to phase
    - horizon_suggestions: {feature_id: "H1"} from co-occurrence
    - summary: human-readable summary line
    """
    from app.db.supabase_client import get_supabase

    # Map AIOS page_context phases to Forge stage names
    stage = _phase_to_stage(phase)

    def _query():
        try:
            sb = get_supabase()
            return (
                sb.table("forge_module_matches")
                .select("*")
                .eq("project_id", project_id)
                .execute()
            ).data or []
        except Exception:
            return []

    try:
        matches = await asyncio.to_thread(_query)
    except Exception:
        return {}

    if not matches:
        return {}

    # Load feature names for context
    feature_names = await _load_feature_names(project_id, matches)

    matched_modules: list[dict] = []
    decision_slots: list[dict] = []
    horizon_suggestions: dict[str, str] = {}

    for m in matches:
        feature_name = feature_names.get(m.get("feature_id", ""), "Unknown")
        matched_modules.append({
            "feature_name": feature_name,
            "module_name": m.get("module_slug", ""),
            "category": "",  # not stored in DB match row
            "match_score": m.get("match_score", 0),
        })

        # Extract decisions from resolved_decisions JSONB
        for decision in m.get("resolved_decisions") or []:
            d_stage = decision.get("stage", "all")
            if d_stage in (stage, "all"):
                decision_slots.append({
                    "module": m.get("module_slug", ""),
                    "decision_key": decision.get("key", ""),
                    "question": decision.get("question", ""),
                    "impact": decision.get("impact", ""),
                })

        # Horizon suggestions
        h_suggestion = m.get("horizon_suggestion")
        if h_suggestion and m.get("feature_id"):
            horizon_suggestions[m["feature_id"]] = h_suggestion

    module_names = [mm["module_name"] for mm in matched_modules[:3]]
    summary = (
        f"{len(matched_modules)} features match Forge modules"
        f" ({', '.join(module_names)})"
        if matched_modules
        else ""
    )

    return {
        "matched_modules": matched_modules,
        "decision_slots": decision_slots,
        "horizon_suggestions": horizon_suggestions,
        "summary": summary,
    }


async def _load_feature_names(
    project_id: str, matches: list[dict]
) -> dict[str, str]:
    """Load feature names for matched feature IDs."""
    from app.db.supabase_client import get_supabase

    feature_ids = [m["feature_id"] for m in matches if m.get("feature_id")]
    if not feature_ids:
        return {}

    def _query():
        try:
            sb = get_supabase()
            return (
                sb.table("features")
                .select("id, name")
                .in_("id", feature_ids)
                .execute()
            ).data or []
        except Exception:
            return []

    try:
        rows = await asyncio.to_thread(_query)
        return {r["id"]: r.get("name", "") for r in rows}
    except Exception:
        return {}


def _phase_to_stage(phase: str) -> str:
    """Map AIOS page_context / phase to Forge decision stage."""
    if not phase:
        return "all"
    if phase.startswith("brd"):
        return "brd"
    if "solution" in phase or "flow" in phase:
        return "solution_flow"
    if "prototype" in phase or "proto" in phase:
        return "prototype"
    return "all"
