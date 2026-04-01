"""CRUD operations for the Outcomes system.

Covers: outcomes (core), outcome_actors (per-persona), outcome_entity_links,
and outcome_capabilities (Ways to Achieve).
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

ConfirmationStatus = Literal[
    "ai_generated", "needs_client", "confirmed_consultant", "confirmed_client"
]
OutcomeStatus = Literal["candidate", "confirmed", "validated", "achieved"]
ActorStatus = Literal["not_started", "emerging", "confirmed", "validated"]
LinkType = Literal["serves", "blocks", "enables", "measures", "evidence_for", "surface_of"]
Quadrant = Literal["knowledge", "scoring", "decision", "ai"]
Horizon = Literal["h1", "h2", "h3"]


# =============================================================================
# Core Outcomes
# =============================================================================


def list_outcomes(
    project_id: UUID,
    horizon: Horizon | None = None,
    status: OutcomeStatus | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List outcomes for a project, ordered by display_order."""
    sb = get_supabase()
    query = sb.table("outcomes").select("*").eq("project_id", str(project_id))
    if horizon:
        query = query.eq("horizon", horizon)
    if status:
        query = query.eq("status", status)
    response = query.order("display_order").limit(limit).execute()
    return response.data or []


def get_outcome(outcome_id: UUID) -> dict[str, Any] | None:
    """Get a single outcome by ID."""
    sb = get_supabase()
    response = (
        sb.table("outcomes")
        .select("*")
        .eq("id", str(outcome_id))
        .maybe_single()
        .execute()
    )
    return response.data


def get_outcome_with_actors(outcome_id: UUID) -> dict[str, Any] | None:
    """Get an outcome with its actor outcomes attached."""
    outcome = get_outcome(outcome_id)
    if not outcome:
        return None
    outcome["actors"] = list_outcome_actors(outcome_id)
    return outcome


def get_outcomes_with_actors(project_id: UUID, horizon: Horizon | None = None) -> list[dict[str, Any]]:
    """Get all outcomes for a project, each with actors attached."""
    outcomes = list_outcomes(project_id, horizon=horizon)
    if not outcomes:
        return []

    # Batch-fetch all actors for these outcomes
    outcome_ids = [str(o["id"]) for o in outcomes]
    sb = get_supabase()
    actors_resp = (
        sb.table("outcome_actors")
        .select("*")
        .in_("outcome_id", outcome_ids)
        .order("display_order")
        .execute()
    )
    actors_by_outcome: dict[str, list[dict]] = {}
    for actor in actors_resp.data or []:
        oid = actor["outcome_id"]
        actors_by_outcome.setdefault(oid, []).append(actor)

    for outcome in outcomes:
        outcome["actors"] = actors_by_outcome.get(str(outcome["id"]), [])

    return outcomes


def create_outcome(
    project_id: UUID,
    title: str,
    description: str = "",
    horizon: Horizon = "h1",
    source_type: str = "system_generated",
    what_helps: list[str] | None = None,
    evidence: list[dict] | None = None,
    generation_context: dict | None = None,
    strength_score: int = 0,
    strength_dimensions: dict | None = None,
    enrichment_intel: dict | None = None,
) -> dict[str, Any]:
    """Create a core outcome."""
    sb = get_supabase()

    # Get next display_order
    existing = sb.table("outcomes").select("display_order").eq(
        "project_id", str(project_id)
    ).order("display_order", desc=True).limit(1).execute()
    next_order = (existing.data[0]["display_order"] + 1) if existing.data else 0

    payload = {
        "project_id": str(project_id),
        "title": title,
        "description": description,
        "horizon": horizon,
        "source_type": source_type,
        "what_helps": what_helps or [],
        "evidence": evidence or [],
        "generation_context": generation_context or {},
        "strength_score": strength_score,
        "strength_dimensions": strength_dimensions or {
            "specificity": 0, "scenario": 0, "cost_of_failure": 0, "observable": 0,
        },
        "enrichment_intel": enrichment_intel or {},
        "display_order": next_order,
    }

    response = sb.table("outcomes").insert(payload).execute()
    outcome = response.data[0]
    logger.info(f"Created outcome: {title} (id={outcome['id']})")
    return outcome


def update_outcome(outcome_id: UUID, updates: dict[str, Any]) -> dict[str, Any] | None:
    """Update an outcome. Only updates provided fields."""
    sb = get_supabase()
    allowed = {
        "title", "description", "icon", "horizon", "status", "confirmation_status",
        "strength_score", "strength_dimensions", "what_helps", "evidence",
        "enrichment_intel", "display_order",
    }
    filtered = {k: v for k, v in updates.items() if k in allowed}
    if not filtered:
        return get_outcome(outcome_id)

    filtered["updated_at"] = "now()"
    response = sb.table("outcomes").update(filtered).eq("id", str(outcome_id)).execute()
    return response.data[0] if response.data else None


def confirm_outcome(
    outcome_id: UUID,
    status: ConfirmationStatus = "confirmed_consultant",
) -> dict[str, Any] | None:
    """Confirm an outcome. Updates both confirmation_status and status."""
    sb = get_supabase()
    updates: dict[str, Any] = {
        "confirmation_status": status,
        "updated_at": "now()",
    }
    # Also advance status if it's still candidate
    outcome = get_outcome(outcome_id)
    if outcome and outcome.get("status") == "candidate":
        updates["status"] = "confirmed"

    response = sb.table("outcomes").update(updates).eq("id", str(outcome_id)).execute()
    return response.data[0] if response.data else None


# =============================================================================
# Actor Outcomes
# =============================================================================


def list_outcome_actors(outcome_id: UUID) -> list[dict[str, Any]]:
    """List actor outcomes for a core outcome."""
    sb = get_supabase()
    response = (
        sb.table("outcome_actors")
        .select("*")
        .eq("outcome_id", str(outcome_id))
        .order("display_order")
        .execute()
    )
    return response.data or []


def create_outcome_actor(
    outcome_id: UUID,
    persona_name: str,
    title: str,
    before_state: str = "",
    after_state: str = "",
    metric: str = "",
    persona_id: UUID | None = None,
    strength_score: int = 0,
) -> dict[str, Any]:
    """Create an actor outcome (per-persona state change)."""
    sb = get_supabase()

    # Get next display_order within this outcome
    existing = sb.table("outcome_actors").select("display_order").eq(
        "outcome_id", str(outcome_id)
    ).order("display_order", desc=True).limit(1).execute()
    next_order = (existing.data[0]["display_order"] + 1) if existing.data else 0

    payload = {
        "outcome_id": str(outcome_id),
        "persona_name": persona_name,
        "title": title,
        "before_state": before_state,
        "after_state": after_state,
        "metric": metric,
        "strength_score": strength_score,
        "display_order": next_order,
    }
    if persona_id:
        payload["persona_id"] = str(persona_id)

    response = sb.table("outcome_actors").insert(payload).execute()
    actor = response.data[0]
    logger.info(f"Created actor outcome: {persona_name} — {title} (id={actor['id']})")
    return actor


def update_outcome_actor(actor_id: UUID, updates: dict[str, Any]) -> dict[str, Any] | None:
    """Update an actor outcome."""
    sb = get_supabase()
    allowed = {
        "title", "before_state", "after_state", "metric",
        "strength_score", "status", "sharpen_prompt", "evidence", "display_order",
    }
    filtered = {k: v for k, v in updates.items() if k in allowed}
    if not filtered:
        return None

    filtered["updated_at"] = "now()"
    response = sb.table("outcome_actors").update(filtered).eq("id", str(actor_id)).execute()
    return response.data[0] if response.data else None


def check_auto_confirm_core_outcome(outcome_id: UUID) -> bool:
    """If ALL actor outcomes are confirmed, auto-confirm the core outcome.

    Returns True if auto-confirmation happened.
    """
    actors = list_outcome_actors(outcome_id)
    if not actors:
        return False

    all_confirmed = all(a.get("status") in ("confirmed", "validated") for a in actors)
    if all_confirmed:
        outcome = get_outcome(outcome_id)
        if outcome and outcome.get("status") == "candidate":
            confirm_outcome(outcome_id)
            logger.info(f"Auto-confirmed core outcome {outcome_id} (all actors confirmed)")
            return True
    return False


# =============================================================================
# Outcome-Entity Links
# =============================================================================


def create_outcome_entity_link(
    outcome_id: UUID,
    entity_id: UUID | str,
    entity_type: str,
    link_type: LinkType = "serves",
    how_served: str | None = None,
    confidence: ConfirmationStatus = "ai_generated",
) -> dict[str, Any] | None:
    """Create or update a link between an outcome and an entity."""
    sb = get_supabase()
    payload = {
        "outcome_id": str(outcome_id),
        "entity_id": str(entity_id),
        "entity_type": entity_type,
        "link_type": link_type,
        "confidence": confidence,
    }
    if how_served:
        payload["how_served"] = how_served

    try:
        response = sb.table("outcome_entity_links").upsert(
            payload,
            on_conflict="outcome_id,entity_id,entity_type,link_type",
        ).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.warning(f"Failed to create outcome-entity link: {e}")
        return None


def get_outcome_entity_links(
    outcome_id: UUID | None = None,
    entity_id: UUID | str | None = None,
    entity_type: str | None = None,
    link_type: LinkType | None = None,
) -> list[dict[str, Any]]:
    """Query outcome-entity links with flexible filters."""
    sb = get_supabase()
    query = sb.table("outcome_entity_links").select("*")
    if outcome_id:
        query = query.eq("outcome_id", str(outcome_id))
    if entity_id:
        query = query.eq("entity_id", str(entity_id))
    if entity_type:
        query = query.eq("entity_type", entity_type)
    if link_type:
        query = query.eq("link_type", link_type)

    response = query.execute()
    return response.data or []


def get_surfaces_for_outcome(outcome_id: UUID) -> list[dict[str, Any]]:
    """Get solution_flow_steps that serve this outcome."""
    return get_outcome_entity_links(
        outcome_id=outcome_id, link_type="surface_of"
    )


def get_outcomes_for_entity(
    entity_id: UUID | str, entity_type: str
) -> list[dict[str, Any]]:
    """Get outcomes linked to a specific entity."""
    links = get_outcome_entity_links(entity_id=entity_id, entity_type=entity_type)
    if not links:
        return []

    outcome_ids = list({l["outcome_id"] for l in links})
    sb = get_supabase()
    response = sb.table("outcomes").select("*").in_("id", outcome_ids).execute()
    return response.data or []


# =============================================================================
# Outcome Capabilities (Ways to Achieve)
# =============================================================================


def list_outcome_capabilities(
    outcome_id: UUID | None = None,
    project_id: UUID | None = None,
    quadrant: Quadrant | None = None,
) -> list[dict[str, Any]]:
    """List outcome capabilities with flexible filters."""
    sb = get_supabase()
    query = sb.table("outcome_capabilities").select("*")
    if outcome_id:
        query = query.eq("outcome_id", str(outcome_id))
    if project_id:
        query = query.eq("project_id", str(project_id))
    if quadrant:
        query = query.eq("quadrant", quadrant)

    response = query.order("display_order").execute()
    return response.data or []


def create_outcome_capability(
    project_id: UUID,
    outcome_id: UUID,
    name: str,
    quadrant: Quadrant,
    description: str = "",
    badge: str = "suggested",
    agent_id: UUID | None = None,
) -> dict[str, Any]:
    """Create an outcome capability (Way to Achieve)."""
    sb = get_supabase()

    payload = {
        "project_id": str(project_id),
        "outcome_id": str(outcome_id),
        "name": name,
        "quadrant": quadrant,
        "description": description,
        "badge": badge,
    }
    if agent_id:
        payload["agent_id"] = str(agent_id)

    response = sb.table("outcome_capabilities").insert(payload).execute()
    cap = response.data[0]
    logger.info(f"Created capability: {name} ({quadrant}) for outcome {outcome_id}")

    # Fire-and-forget: embed the capability
    try:
        import asyncio

        # Resolve outcome title for richer embedding
        outcome = get_outcome(outcome_id)
        outcome_title = outcome.get("title", "") if outcome else ""

        asyncio.ensure_future(embed_outcome_capability(cap, outcome_title))
    except Exception:
        pass  # Embedding is non-critical

    return cap


# =============================================================================
# Outcome Coverage (Intelligence Gap Analysis)
# =============================================================================


def get_outcome_coverage(project_id: UUID) -> dict[str, dict]:
    """For each outcome, check which intelligence quadrants have coverage.

    Returns:
        {
            outcome_id: {
                "title": "...",
                "strength_score": 75,
                "knowledge": [items],
                "scoring": [items],
                "decision": [items],
                "ai": [items],
                "gaps": ["No scoring model", ...],
                "coverage_pct": 75,
            }
        }
    """
    outcomes = list_outcomes(project_id)
    if not outcomes:
        return {}

    capabilities = list_outcome_capabilities(project_id=project_id)

    # Group capabilities by outcome
    caps_by_outcome: dict[str, dict[str, list]] = {}
    for cap in capabilities:
        oid = cap["outcome_id"]
        q = cap["quadrant"]
        caps_by_outcome.setdefault(oid, {
            "knowledge": [], "scoring": [], "decision": [], "ai": [],
        })
        caps_by_outcome[oid][q].append(cap)

    result = {}
    for outcome in outcomes:
        oid = str(outcome["id"])
        caps = caps_by_outcome.get(oid, {
            "knowledge": [], "scoring": [], "decision": [], "ai": [],
        })

        gaps = []
        covered = 0
        for q in ("knowledge", "scoring", "decision", "ai"):
            if caps.get(q):
                covered += 1
            else:
                gaps.append(f"No {q.replace('_', ' ')} for {outcome['title'][:40]}")

        result[oid] = {
            "title": outcome["title"],
            "strength_score": outcome.get("strength_score", 0),
            "knowledge": caps.get("knowledge", []),
            "scoring": caps.get("scoring", []),
            "decision": caps.get("decision", []),
            "ai": caps.get("ai", []),
            "gaps": gaps,
            "coverage_pct": int((covered / 4) * 100),
        }

    return result


# =============================================================================
# Macro Outcome (Project-Level)
# =============================================================================


def get_macro_outcome(project_id: UUID) -> dict[str, str | None]:
    """Get the macro outcome and thesis for a project."""
    sb = get_supabase()
    response = (
        sb.table("projects")
        .select("macro_outcome, outcome_thesis")
        .eq("id", str(project_id))
        .single()
        .execute()
    )
    return {
        "macro_outcome": response.data.get("macro_outcome"),
        "outcome_thesis": response.data.get("outcome_thesis"),
    } if response.data else {"macro_outcome": None, "outcome_thesis": None}


def update_macro_outcome(
    project_id: UUID,
    macro_outcome: str | None = None,
    outcome_thesis: str | None = None,
) -> None:
    """Update the macro outcome and/or thesis on the project."""
    sb = get_supabase()
    updates: dict[str, Any] = {}
    if macro_outcome is not None:
        updates["macro_outcome"] = macro_outcome
    if outcome_thesis is not None:
        updates["outcome_thesis"] = outcome_thesis
    if updates:
        sb.table("projects").update(updates).eq("id", str(project_id)).execute()


# =============================================================================
# Outcome Embedding
# =============================================================================


async def embed_outcome(outcome: dict) -> None:
    """Generate and store embedding for an outcome in entity_vectors."""
    from app.core.embeddings import embed_texts_async

    text_parts = [f"Outcome: {outcome['title']}"]
    if outcome.get("description"):
        text_parts.append(outcome["description"])

    enrichment = outcome.get("enrichment_intel") or {}
    questions = enrichment.get("hypothetical_questions", [])
    if questions:
        text_parts.append("Questions this answers:\n" + "\n".join(questions))

    what_helps = outcome.get("what_helps", [])
    if what_helps:
        text_parts.append("What helps:\n" + "\n".join(what_helps))

    text = "\n\n".join([p for p in text_parts if p])
    if len(text.strip()) < 10:
        return

    try:
        embeddings = await embed_texts_async([text])
        if not embeddings:
            return

        sb = get_supabase()
        sb.table("entity_vectors").upsert(
            {
                "entity_id": str(outcome["id"]),
                "entity_type": "outcome",
                "project_id": str(outcome["project_id"]),
                "vector_type": "identity",
                "embedding": embeddings[0],
                "source_text": text[:500],
                "updated_at": "now()",
            },
            on_conflict="entity_id,entity_type,vector_type",
        ).execute()

        logger.debug(f"Embedded outcome {outcome['id']}")
    except Exception:
        logger.exception(f"Failed to embed outcome {outcome['id']}")


async def embed_outcome_capability(capability: dict, outcome_title: str = "") -> None:
    """Generate and store embedding for an outcome capability in entity_vectors."""
    from app.core.embeddings import embed_texts_async

    name = capability.get("name", "")
    quadrant = capability.get("quadrant", "")
    description = capability.get("description", "")

    text = f"{name} ({quadrant}): {description}"
    if outcome_title:
        text += f" — serves outcome: {outcome_title}"

    if len(text.strip()) < 10:
        return

    try:
        embeddings = await embed_texts_async([text])
        if not embeddings:
            return

        sb = get_supabase()
        sb.table("entity_vectors").upsert(
            {
                "entity_id": str(capability["id"]),
                "entity_type": "outcome_capability",
                "project_id": str(capability["project_id"]),
                "vector_type": "identity",
                "embedding": embeddings[0],
                "source_text": text[:500],
                "updated_at": "now()",
            },
            on_conflict="entity_id,entity_type,vector_type",
        ).execute()

        logger.debug(f"Embedded capability {capability['id']}")
    except Exception:
        logger.exception(f"Failed to embed capability {capability['id']}")
