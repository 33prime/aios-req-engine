"""Outcome tool handlers for the chat assistant.

Supports: create, link, coverage, sharpen, list.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


async def dispatch_outcome(project_id: UUID, params: dict[str, Any]) -> dict[str, Any]:
    """Dispatch outcome tool actions."""
    action = params.get("action", "")

    if action == "create":
        return await _create_outcome(project_id, params)
    elif action == "link":
        return await _link_entity(project_id, params)
    elif action == "coverage":
        return await _get_coverage(project_id)
    elif action == "sharpen":
        return await _sharpen_outcome(project_id, params)
    elif action == "list":
        return await _list_outcomes(project_id)
    else:
        return {"error": f"Unknown outcome action: {action}"}


async def _create_outcome(project_id: UUID, params: dict) -> dict:
    """Create a core outcome with actor outcomes."""
    from app.db.outcomes import create_outcome, create_outcome_actor, embed_outcome

    title = params.get("title", "").strip()
    if not title:
        return {"error": "Outcome title is required"}

    actor_outcomes = params.get("actor_outcomes", [])
    if len(actor_outcomes) < 1:
        return {"error": "At least 1 actor outcome is required (2+ recommended)"}

    # Create the core outcome
    outcome = create_outcome(
        project_id=project_id,
        title=title,
        description=params.get("description", ""),
        horizon=params.get("horizon", "h1"),
        source_type="consultant_created",
        what_helps=params.get("what_helps", []),
    )

    # Create actor outcomes
    created_actors = []
    for actor_data in actor_outcomes:
        # Try to resolve persona_id from name
        persona_id = _resolve_persona_id(project_id, actor_data.get("persona_name", ""))

        actor = create_outcome_actor(
            outcome_id=UUID(outcome["id"]),
            persona_name=actor_data.get("persona_name", ""),
            title=actor_data.get("title", ""),
            before_state=actor_data.get("before_state", ""),
            after_state=actor_data.get("after_state", ""),
            metric=actor_data.get("metric", ""),
            persona_id=persona_id,
        )
        created_actors.append(actor)

    # Embed (fire-and-forget)
    try:
        await embed_outcome(outcome)
    except Exception:
        pass

    # Score (fire-and-forget)
    try:
        from app.chains.score_outcomes import score_and_persist_outcome
        await score_and_persist_outcome(outcome_id=str(outcome["id"]))
    except Exception:
        pass

    return {
        "success": True,
        "outcome_id": outcome["id"],
        "title": outcome["title"],
        "actors_created": len(created_actors),
        "message": f"Created outcome: \"{title}\" with {len(created_actors)} actor outcomes",
    }


async def _link_entity(project_id: UUID, params: dict) -> dict:
    """Link an entity to an outcome."""
    from app.db.outcomes import create_outcome_entity_link

    outcome_id = params.get("outcome_id")
    entity_id = params.get("entity_id")
    entity_type = params.get("entity_type")

    if not outcome_id or not entity_id or not entity_type:
        return {"error": "outcome_id, entity_id, and entity_type are required"}

    link = create_outcome_entity_link(
        outcome_id=UUID(outcome_id),
        entity_id=entity_id,
        entity_type=entity_type,
        link_type=params.get("link_type", "serves"),
    )

    if not link:
        return {"error": "Failed to create link"}

    return {
        "success": True,
        "link_id": link["id"],
        "message": f"Linked {entity_type} to outcome",
    }


async def _get_coverage(project_id: UUID) -> dict:
    """Get intelligence coverage report."""
    from app.db.outcomes import get_outcome_coverage

    coverage = get_outcome_coverage(project_id)
    if not coverage:
        return {"message": "No outcomes found. Create outcomes first."}

    # Summarize for chat
    total = len(coverage)
    fully_covered = sum(1 for c in coverage.values() if c.get("coverage_pct", 0) == 100)
    all_gaps = []
    for c in coverage.values():
        all_gaps.extend(c.get("gaps", []))

    return {
        "total_outcomes": total,
        "fully_covered": fully_covered,
        "gaps": all_gaps[:10],
        "coverage": coverage,
    }


async def _sharpen_outcome(project_id: UUID, params: dict) -> dict:
    """Score an outcome and return sharpen prompts."""
    outcome_id = params.get("outcome_id")
    if not outcome_id:
        return {"error": "outcome_id is required"}

    from app.chains.score_outcomes import score_and_persist_outcome
    from app.db.outcomes import get_outcome_with_actors

    result = await score_and_persist_outcome(outcome_id=outcome_id)
    if not result:
        return {"error": "Outcome not found"}

    # Reload with actors to get sharpen prompts
    outcome = get_outcome_with_actors(UUID(outcome_id))
    actors = outcome.get("actors", []) if outcome else []

    sharpen_prompts = [
        {
            "persona": a.get("persona_name"),
            "prompt": a.get("sharpen_prompt"),
            "strength": a.get("strength_score", 0),
        }
        for a in actors
        if a.get("sharpen_prompt")
    ]

    return {
        "outcome_id": outcome_id,
        "strength_score": result.get("strength_score", 0),
        "strength_dimensions": result.get("strength_dimensions", {}),
        "sharpen_prompts": sharpen_prompts,
    }


async def _list_outcomes(project_id: UUID) -> dict:
    """List all outcomes for the project."""
    from app.db.outcomes import get_outcomes_with_actors

    outcomes = get_outcomes_with_actors(project_id)

    summary = []
    for o in outcomes:
        actors = o.get("actors", [])
        summary.append({
            "id": o["id"],
            "title": o["title"],
            "horizon": o.get("horizon", "h1"),
            "strength": o.get("strength_score", 0),
            "status": o.get("status", "candidate"),
            "actor_count": len(actors),
            "actor_names": [a.get("persona_name", "") for a in actors],
        })

    return {"outcomes": summary, "count": len(summary)}


def _resolve_persona_id(project_id: UUID, persona_name: str) -> UUID | None:
    """Try to resolve a persona name to an ID."""
    if not persona_name:
        return None
    try:
        from app.db.supabase_client import get_supabase
        sb = get_supabase()
        resp = sb.table("personas").select("id, name").eq(
            "project_id", str(project_id)
        ).execute()
        for p in resp.data or []:
            if p.get("name", "").lower() == persona_name.lower():
                return UUID(p["id"])
    except Exception:
        pass
    return None
