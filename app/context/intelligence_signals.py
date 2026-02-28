"""Intelligence signal loaders — confidence state, horizon state, and warm memory.

Parallel loaders that feed into the prompt compiler's cognitive frame selection.
Includes chat memory tiers: warm (recent conversation summaries) and cold
(project-level memory via MemoryWatcher).
"""

import asyncio
from uuid import UUID

from app.core.logging import get_logger

logger = get_logger(__name__)


# ── Warm Memory (Recent Conversation Summaries) ───────────────────


async def load_warm_memory(
    project_id: UUID | str,
    current_conversation_id: UUID | str | None = None,
) -> str:
    """Load summaries of recent conversations (not the current one).

    Warm memory tier: provides cross-conversation continuity by loading
    the last few conversation summaries for this project.

    Returns formatted string for prompt inclusion, or empty string.
    """
    from app.db.supabase_client import get_supabase

    def _query():
        try:
            supabase = get_supabase()
            pid = str(project_id)

            # Get last 5 conversations for this project, newest first
            query = (
                supabase.table("conversations")
                .select("id, created_at, summary")
                .eq("project_id", pid)
                .order("created_at", desc=True)
                .limit(6)  # extra 1 to account for current
            )
            resp = query.execute()
            conversations = resp.data or []

            if not conversations:
                return ""

            # Filter out current conversation and those without summaries
            cid = str(current_conversation_id) if current_conversation_id else None
            summaries: list[str] = []
            for conv in conversations:
                if conv["id"] == cid:
                    continue
                summary = conv.get("summary")
                if summary and summary.strip():
                    summaries.append(summary.strip())
                if len(summaries) >= 3:
                    break

            if not summaries:
                # Fallback: load last few messages from recent conversations
                # to provide some cross-conversation context
                return _fallback_recent_topics(supabase, pid, cid, conversations)

            return "# Previous Conversations\n" + "\n".join(f"- {s}" for s in summaries)
        except Exception as e:
            logger.debug(f"Warm memory load failed: {e}")
            return ""

    return await asyncio.to_thread(_query)


def _fallback_recent_topics(
    supabase, project_id: str, current_conv_id: str | None, conversations: list
) -> str:
    """Fallback when no conversation summaries exist — extract recent topics."""
    try:
        # Get up to 3 other conversation IDs
        other_ids = [c["id"] for c in conversations if c["id"] != current_conv_id][:3]

        if not other_ids:
            return ""

        # Get last user message from each conversation
        topics: list[str] = []
        for conv_id in other_ids:
            resp = (
                supabase.table("messages")
                .select("content")
                .eq("conversation_id", conv_id)
                .eq("role", "user")
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if resp.data:
                content = resp.data[0].get("content", "")[:100]
                if content:
                    topics.append(content)

        if not topics:
            return ""

        return "# Recent Topics\n" + "\n".join(f"- {t}" for t in topics)
    except Exception:
        return ""


async def load_confidence_state(project_id: UUID | str) -> dict:
    """Load memory landscape for confidence posture selection.

    3 parallel queries:
    - Q1: Low-confidence beliefs (need verification)
    - Q2: Active belief domains (breadth of knowledge)
    - Q3: Recent insights from reflector (strategic patterns)

    Returns dict with low_confidence_beliefs, active_domains, recent_insights.
    """
    from app.db.supabase_client import get_supabase

    supabase = get_supabase()
    pid = str(project_id)

    def _q_low_confidence():
        try:
            resp = (
                supabase.table("memory_nodes")
                .select("summary, confidence, belief_domain")
                .eq("project_id", pid)
                .eq("node_type", "belief")
                .eq("is_active", True)
                .lt("confidence", 0.6)
                .order("confidence")
                .limit(5)
                .execute()
            )
            return [
                {
                    "summary": n.get("summary", ""),
                    "confidence": n.get("confidence", 0),
                    "domain": n.get("belief_domain", ""),
                }
                for n in (resp.data or [])
            ]
        except Exception as e:
            logger.debug(f"Low confidence query failed: {e}")
            return []

    def _q_active_domains():
        try:
            resp = (
                supabase.table("memory_nodes")
                .select("belief_domain")
                .eq("project_id", pid)
                .eq("node_type", "belief")
                .eq("is_active", True)
                .not_.is_("belief_domain", "null")
                .execute()
            )
            domains = {n.get("belief_domain") for n in (resp.data or []) if n.get("belief_domain")}
            return len(domains)
        except Exception as e:
            logger.debug(f"Active domains query failed: {e}")
            return 0

    def _q_recent_insights():
        try:
            resp = (
                supabase.table("memory_nodes")
                .select("summary, insight_type, created_at")
                .eq("project_id", pid)
                .eq("node_type", "insight")
                .eq("is_active", True)
                .order("created_at", desc=True)
                .limit(3)
                .execute()
            )
            return [
                {
                    "summary": n.get("summary", ""),
                    "type": n.get("insight_type", ""),
                }
                for n in (resp.data or [])
            ]
        except Exception as e:
            logger.debug(f"Recent insights query failed: {e}")
            return []

    low_conf, domains, insights = await asyncio.gather(
        asyncio.to_thread(_q_low_confidence),
        asyncio.to_thread(_q_active_domains),
        asyncio.to_thread(_q_recent_insights),
    )

    return {
        "low_confidence_beliefs": low_conf,
        "active_domains": domains,
        "recent_insights": insights,
    }


async def load_horizon_state(project_id: UUID | str) -> dict:
    """Load horizon intelligence for temporal/urgency awareness.

    2 parallel queries + 1 deterministic computation:
    - Q1: Project horizons (is crystallized?)
    - Q2: Blocking horizon outcomes
    - Compute: Compound decisions (~15ms, BFS)

    Returns dict with is_crystallized, blocking_outcomes, blocking_details,
    compound_decisions.
    """
    pid = UUID(str(project_id))

    def _q_horizons():
        try:
            from app.core.horizon_briefing import build_horizon_summary

            return build_horizon_summary(pid)
        except Exception as e:
            logger.debug(f"Horizon summary failed: {e}")
            return None

    def _q_compounds():
        try:
            from app.core.compound_decisions import detect_compound_decisions

            return detect_compound_decisions(pid)
        except Exception as e:
            logger.debug(f"Compound decisions failed: {e}")
            return []

    horizon_summary, compounds = await asyncio.gather(
        asyncio.to_thread(_q_horizons),
        asyncio.to_thread(_q_compounds),
    )

    is_crystallized = horizon_summary is not None
    blocking_outcomes = 0
    blocking_details: list[dict] = []

    if horizon_summary:
        for h in horizon_summary.get("horizons", []):
            ba = h.get("blocking_at_risk", 0)
            blocking_outcomes += ba
            if ba > 0:
                blocking_details.append(
                    {
                        "horizon": f"H{h.get('number', '?')}",
                        "title": h.get("title", ""),
                        "blocking_at_risk": ba,
                    }
                )

    return {
        "is_crystallized": is_crystallized,
        "blocking_outcomes": blocking_outcomes,
        "blocking_details": blocking_details,
        "compound_decisions": len(compounds) if compounds else 0,
        "horizon_summary": horizon_summary,
    }
