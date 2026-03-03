"""Post-call learning loop — goal-vs-got diff and deal readiness delta."""

import json
from uuid import UUID

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def compute_goal_diff(recording_id: UUID) -> None:
    """Evaluate call goals against analysis results.

    For each goal in the strategy brief, determines if it was achieved,
    partially achieved, or missed based on the analysis output.
    """
    from app.db.call_intelligence import get_analysis
    from app.db.call_strategy import get_brief_for_recording, update_strategy_brief

    brief = get_brief_for_recording(recording_id)
    if not brief:
        logger.debug(f"No strategy brief for recording {recording_id}")
        return

    goals = brief.get("call_goals") or []
    if not goals:
        return

    analysis = get_analysis(recording_id)
    if not analysis:
        logger.debug(f"No analysis for recording {recording_id}")
        return

    summary = analysis.get("executive_summary", "")
    custom = analysis.get("custom_dimensions", {})

    # Build analysis context for the LLM
    analysis_context = f"Executive Summary: {summary}\n"
    if custom.get("consultant_summary"):
        analysis_context += f"Consultant Summary: {custom['consultant_summary']}\n"

    try:
        goal_results = await _evaluate_goals(goals, analysis_context)
        update_strategy_brief(UUID(brief["id"]), {"goal_results": goal_results})
        logger.info(f"Goal diff computed for recording {recording_id}: {len(goal_results)} goals")
    except Exception as e:
        logger.warning(f"Goal diff evaluation failed: {e}")


async def _evaluate_goals(goals: list[dict], analysis_context: str) -> list[dict]:
    """Use LLM to evaluate each goal against the analysis."""
    try:
        from anthropic import Anthropic

        settings = get_settings()
        if not settings.ANTHROPIC_API_KEY:
            return _fallback_evaluate(goals)

        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        goals_text = json.dumps(goals, indent=2)

        prompt = f"""Evaluate each call goal against the analysis results.

## Call Goals
{goals_text}

## Analysis Results
{analysis_context}

For each goal, return a JSON array of objects with:
- "goal": the original goal text
- "achieved": one of "yes", "partial", "no", "unknown"
- "evidence": brief evidence from the analysis
- "gaps_remaining": array of remaining gaps (strings)

Return ONLY valid JSON — no markdown fences."""

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]

        results = json.loads(text.strip())
        return results if isinstance(results, list) else []

    except Exception as e:
        logger.warning(f"LLM goal evaluation failed: {e}")
        return _fallback_evaluate(goals)


def _fallback_evaluate(goals: list[dict]) -> list[dict]:
    """Fallback: mark all goals as unknown without LLM."""
    return [
        {
            "goal": g.get("goal", ""),
            "achieved": "unknown",
            "evidence": "Analysis completed but goal evaluation requires manual review",
            "gaps_remaining": [],
        }
        for g in goals
    ]


async def compute_readiness_delta(recording_id: UUID) -> None:
    """Compute deal readiness before/after delta.

    Compares the pre-call readiness snapshot in the strategy brief
    with a fresh readiness computation using current project state.
    """
    from app.db.call_intelligence import get_call_recording
    from app.db.call_strategy import get_brief_for_recording, update_strategy_brief
    from app.db.supabase_client import get_supabase

    brief = get_brief_for_recording(recording_id)
    if not brief:
        return

    before_snapshot = brief.get("deal_readiness_snapshot", {})
    before_score = before_snapshot.get("score", 0)

    recording = get_call_recording(recording_id)
    if not recording:
        return

    project_id = UUID(recording["project_id"])

    try:
        from app.core.deal_readiness import compute_deal_readiness
        from app.db.memory_graph import get_graph_stats

        sb = get_supabase()
        stats = get_graph_stats(project_id)

        # Load current client data
        client_data = {}
        try:
            client = (
                sb.table("client_profiles")
                .select("*")
                .eq("project_id", str(project_id))
                .limit(1)
                .execute()
            )
            if client.data:
                client_data = client.data[0]
        except Exception:
            pass

        vision = None
        try:
            proj = (
                sb.table("projects")
                .select("vision")
                .eq("id", str(project_id))
                .single()
                .execute()
            )
            vision = proj.data.get("vision") if proj.data else None
        except Exception:
            pass

        stakeholders = []
        try:
            sh = (
                sb.table("stakeholders")
                .select("id, name, stakeholder_type, influence_level, role")
                .eq("project_id", str(project_id))
                .execute()
            )
            stakeholders = sh.data or []
        except Exception:
            pass

        components, after_score = compute_deal_readiness(
            project_id, stakeholders, stats, vision, client_data, sb
        )

        # Build component deltas
        before_components = {c["name"]: c["score"] for c in before_snapshot.get("components", [])}
        component_deltas = [
            {
                "name": c.name,
                "before": before_components.get(c.name, 0),
                "after": c.score,
            }
            for c in components
        ]

        delta = {
            "before_score": before_score,
            "after_score": round(after_score, 1),
            "component_deltas": component_deltas,
        }

        update_strategy_brief(UUID(brief["id"]), {"readiness_delta": delta})
        logger.info(
            f"Readiness delta computed for recording {recording_id}: "
            f"{before_score} → {round(after_score, 1)}"
        )

    except Exception as e:
        logger.warning(f"Readiness delta computation failed: {e}")
