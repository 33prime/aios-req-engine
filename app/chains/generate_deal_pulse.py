"""Generate the Deal Pulse narrative — a 2-3 sentence sales-ready project status.

This is what the consultant repeats verbatim when someone asks "where are we?"
NOT quantitative ("12 features, 3 workflows"). It's a natural, conversational
summary of the current state of requirements discovery.

Uses Haiku 4.5 with project context. Cached in synthesized_memory_cache.
Regenerated when entity changes are detected.
"""

import json
import logging
from datetime import UTC, datetime

from anthropic import Anthropic

from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

_MODEL = "claude-haiku-4-5-20251001"
_MAX_TOKENS = 300

_SYSTEM = """You are a requirements engineering consultant summarizing where a project stands.
Write 2-3 sentences that a consultant can say verbatim when someone asks "where are we?"

Rules:
- Sound natural and conversational, like you're briefing a colleague
- Focus on what's been accomplished, what's clear, and what needs attention next
- Reference specific themes, capabilities, or decisions — NOT counts or percentages
- If things are going well, say so. If there are gaps, name them naturally
- Never use bullet points, headers, or structured formatting
- Keep it under 80 words"""


def generate_deal_pulse(project_id: str) -> str | None:
    """Generate and cache a deal pulse narrative.

    Returns the narrative text, or None if insufficient data.
    """
    client = get_supabase()

    # Gather lightweight project context
    context = _gather_pulse_context(client, project_id)
    if not context:
        return None

    try:
        anthropic = Anthropic()
        response = anthropic.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            system=_SYSTEM,
            messages=[{"role": "user", "content": context}],
        )

        narrative = response.content[0].text.strip()

        # Cache it
        _cache_pulse(client, project_id, narrative)

        logger.info(
            "Deal pulse generated for project %s (tokens=%d/%d)",
            project_id[:8],
            response.usage.input_tokens,
            response.usage.output_tokens,
        )
        return narrative

    except Exception:
        logger.exception("Failed to generate deal pulse for project %s", project_id[:8])
        return None


def get_cached_deal_pulse(project_id: str) -> str | None:
    """Retrieve cached deal pulse from synthesized_memory_cache."""
    try:
        db = get_supabase()
        r = (
            db.table("synthesized_memory_cache")
            .select("content")
            .eq("project_id", project_id)
            .maybe_single()
            .execute()
        )

        if r and r.data and r.data.get("content"):
            val = r.data["content"]
            if isinstance(val, str):
                val = json.loads(val)
            if isinstance(val, dict):
                return val.get("deal_pulse")
    except Exception:
        logger.debug("No cached deal pulse for project %s", project_id[:8])
    return None


def _cache_pulse(client, project_id: str, narrative: str) -> None:
    """Update the deal_pulse key in synthesized_memory_cache."""
    try:
        now = datetime.now(UTC).isoformat()
        existing = (
            client.table("synthesized_memory_cache")
            .select("id, content")
            .eq("project_id", project_id)
            .maybe_single()
            .execute()
        )

        if existing and existing.data:
            content = existing.data.get("content") or {}
            if isinstance(content, str):
                content = json.loads(content)
            content["deal_pulse"] = narrative
            content["deal_pulse_generated_at"] = now
            client.table("synthesized_memory_cache").update(
                {
                    "content": json.dumps(content),
                    "updated_at": now,
                }
            ).eq("id", existing.data["id"]).execute()
        else:
            client.table("synthesized_memory_cache").insert(
                {
                    "project_id": project_id,
                    "content": json.dumps(
                        {
                            "deal_pulse": narrative,
                            "deal_pulse_generated_at": now,
                        }
                    ),
                    "synthesized_at": now,
                }
            ).execute()
    except Exception:
        logger.warning("Failed to cache deal pulse for project %s", project_id[:8])


def _gather_pulse_context(client, project_id: str) -> str | None:
    """Build a concise context string for Haiku."""
    parts = []

    # Project basics
    project = (
        client.table("projects")
        .select("name, vision, stage")
        .eq("id", project_id)
        .maybe_single()
        .execute()
    )
    if not project or not project.data:
        return None

    name = project.data.get("name", "Project")
    vision = project.data.get("vision", "")
    stage = project.data.get("stage", "discovery")
    parts.append(f"Project: {name} (stage: {stage})")
    if vision:
        parts.append(f"Vision: {vision[:200]}")

    # Pain points (titles only)
    pains = (
        client.table("business_drivers")
        .select("title, description, confirmation_status")
        .eq("project_id", project_id)
        .eq("driver_type", "pain")
        .limit(8)
        .execute()
    )
    if pains.data:
        _confirmed = {"confirmed_consultant", "confirmed_client"}
        confirmed = sum(1 for p in pains.data if p.get("confirmation_status") in _confirmed)
        titles = [p.get("title") or p.get("description", "")[:60] for p in pains.data]
        pain_str = "; ".join(titles[:5])
        parts.append(f"Pain points ({len(pains.data)} total, {confirmed} confirmed): {pain_str}")

    # Goals
    goals = (
        client.table("business_drivers")
        .select("title, description, confirmation_status")
        .eq("project_id", project_id)
        .eq("driver_type", "goal")
        .limit(8)
        .execute()
    )
    if goals.data:
        _confirmed = {"confirmed_consultant", "confirmed_client"}
        confirmed = sum(1 for g in goals.data if g.get("confirmation_status") in _confirmed)
        titles = [g.get("title") or g.get("description", "")[:60] for g in goals.data]
        goal_str = "; ".join(titles[:5])
        parts.append(f"Goals ({len(goals.data)} total, {confirmed} confirmed): {goal_str}")

    # Features summary
    features = (
        client.table("features")
        .select("name, priority_group, confirmation_status")
        .eq("project_id", project_id)
        .limit(20)
        .execute()
    )
    if features.data:
        _confirmed = {"confirmed_consultant", "confirmed_client"}
        mvp = [f["name"] for f in features.data if f.get("priority_group") == "must_have"]
        confirmed = sum(1 for f in features.data if f.get("confirmation_status") in _confirmed)
        mvp_str = ", ".join(mvp[:5]) or "none prioritized yet"
        parts.append(
            f"Features: {len(features.data)} identified, "
            f"{confirmed} confirmed. Must-have: {mvp_str}"
        )

    # Workflows
    workflows = (
        client.table("vp_steps")
        .select("label, state_type, confirmation_status")
        .eq("project_id", project_id)
        .limit(15)
        .execute()
    )
    if workflows.data:
        future = [w for w in workflows.data if w.get("state_type") == "future"]
        current = [w for w in workflows.data if w.get("state_type") == "current"]
        parts.append(
            f"Workflows: {len(current)} current-state, {len(future)} future-state steps mapped"
        )

    # Personas
    personas = (
        client.table("personas")
        .select("name, role")
        .eq("project_id", project_id)
        .limit(8)
        .execute()
    )
    if personas.data:
        names = [f"{p['name']} ({p.get('role', '')})" for p in personas.data]
        parts.append(f"Personas: {', '.join(names[:4])}")

    # Stale items
    stale_features = (
        client.table("features")
        .select("name", count="exact")
        .eq("project_id", project_id)
        .eq("is_stale", True)
        .execute()
    )
    stale_count = stale_features.count or 0
    if stale_count > 0:
        parts.append(f"Attention: {stale_count} items may need updating")

    # Solution flow
    flow = (
        client.table("solution_flows")
        .select("title, confirmation_status")
        .eq("project_id", project_id)
        .maybe_single()
        .execute()
    )
    if flow and flow.data:
        flow_title = flow.data.get("title", "Generated")
        flow_status = flow.data.get("confirmation_status", "ai_generated")
        parts.append(f"Solution flow: '{flow_title}' ({flow_status})")

    if len(parts) < 3:
        return None  # Not enough data for a meaningful pulse

    return "\n".join(parts)
