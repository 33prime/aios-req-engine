"""CRUD operations for Solution Surfaces.

Solution surfaces are first-class entities in the convergence map.
Each surface represents a user-facing screen/view that serves one
or more outcomes. Surfaces link to outcomes, features, workflows,
and to each other via evolution chains (H1 → H2 → H3).

Cascade: when linked entities change, surfaces are marked stale
via entity_dependencies and the mark_dependents_stale() trigger.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

Horizon = Literal["h1", "h2", "h3"]
ConfirmationStatus = Literal[
    "ai_generated", "needs_confirmation",
    "confirmed_consultant", "confirmed_client", "needs_review",
]


# =============================================================================
# Core CRUD
# =============================================================================


def list_surfaces(
    project_id: UUID,
    horizon: Horizon | None = None,
    include_stale: bool = True,
) -> list[dict[str, Any]]:
    """List all surfaces for a project, ordered by horizon then sort_order."""
    sb = get_supabase()
    query = sb.table("solution_surfaces").select("*").eq("project_id", str(project_id))
    if horizon:
        query = query.eq("horizon", horizon)
    if not include_stale:
        query = query.eq("is_stale", False)
    response = query.order("sort_order").execute()
    return response.data or []


def get_surface(surface_id: UUID) -> dict[str, Any] | None:
    """Get a single surface by ID."""
    sb = get_supabase()
    response = (
        sb.table("solution_surfaces")
        .select("*")
        .eq("id", str(surface_id))
        .maybe_single()
        .execute()
    )
    return response.data


def create_surface(
    project_id: UUID,
    title: str,
    *,
    description: str = "",
    route: str | None = None,
    horizon: Horizon = "h1",
    evolves_from_id: str | None = None,
    convergence_insight: str | None = None,
    roadmap_insight: str | None = None,
    how_served: dict[str, str] | None = None,
    experience: dict[str, Any] | None = None,
    linked_outcome_ids: list[str] | None = None,
    linked_feature_ids: list[str] | None = None,
    linked_workflow_ids: list[str] | None = None,
    position_x: float = 0,
    position_y: float = 0,
    sort_order: int = 0,
) -> dict[str, Any]:
    """Create a new solution surface."""
    sb = get_supabase()

    payload: dict[str, Any] = {
        "project_id": str(project_id),
        "title": title,
        "description": description,
        "horizon": horizon,
        "position_x": position_x,
        "position_y": position_y,
        "sort_order": sort_order,
        "linked_outcome_ids": linked_outcome_ids or [],
        "linked_feature_ids": linked_feature_ids or [],
        "linked_workflow_ids": linked_workflow_ids or [],
        "how_served": how_served or {},
        "experience": experience or {},
    }
    if route:
        payload["route"] = route
    if evolves_from_id:
        payload["evolves_from_id"] = evolves_from_id
    if convergence_insight:
        payload["convergence_insight"] = convergence_insight
    if roadmap_insight:
        payload["roadmap_insight"] = roadmap_insight

    # Compute convergence
    oc_ids = linked_outcome_ids or []
    payload["convergence_score"] = len(oc_ids)
    payload["is_cross_persona"] = _check_cross_persona(project_id, oc_ids)

    response = sb.table("solution_surfaces").insert(payload).execute()
    surface = response.data[0]
    logger.info(f"Created surface: {title} ({horizon}) for project {project_id}")
    return surface


def update_surface(
    surface_id: UUID,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Update a surface. Recomputes convergence if outcome links changed."""
    sb = get_supabase()

    # If outcome links changed, recompute convergence
    if "linked_outcome_ids" in updates:
        surface = get_surface(surface_id)
        if surface:
            oc_ids = updates["linked_outcome_ids"]
            updates["convergence_score"] = len(oc_ids)
            updates["is_cross_persona"] = _check_cross_persona(
                UUID(surface["project_id"]), oc_ids
            )

    response = (
        sb.table("solution_surfaces")
        .update(updates)
        .eq("id", str(surface_id))
        .execute()
    )
    return response.data[0] if response.data else {}


def delete_surface(surface_id: UUID) -> bool:
    """Delete a surface. Cascade will handle clearing evolution pointers."""
    sb = get_supabase()
    sb.table("solution_surfaces").delete().eq("id", str(surface_id)).execute()
    logger.info(f"Deleted surface {surface_id}")
    return True


def clear_staleness(surface_id: UUID) -> dict[str, Any]:
    """Mark a surface as fresh (after consultant reviews changes)."""
    return update_surface(surface_id, {
        "is_stale": False,
        "stale_reason": None,
        "stale_since": None,
    })


# =============================================================================
# Convergence & Evolution
# =============================================================================


def get_evolution_chain(surface_id: UUID) -> dict[str, list[dict]]:
    """Trace the full evolution chain (ancestors + descendants).

    Returns: {"ancestors": [...], "descendants": [...]}
    """
    sb = get_supabase()
    surface = get_surface(surface_id)
    if not surface:
        return {"ancestors": [], "descendants": []}

    # Trace backward
    ancestors: list[dict] = []
    cur = surface
    while cur and cur.get("evolves_from_id"):
        parent = get_surface(UUID(cur["evolves_from_id"]))
        if not parent or parent["id"] in [a["id"] for a in ancestors]:
            break
        ancestors.append(parent)
        cur = parent

    # Trace forward (all descendants recursively)
    descendants: list[dict] = []
    project_id = surface["project_id"]
    all_surfaces = list_surfaces(UUID(project_id))
    _id = str(surface_id)

    def find_children(parent_id: str) -> None:
        for s in all_surfaces:
            if s.get("evolves_from_id") == parent_id and s["id"] not in [d["id"] for d in descendants]:
                descendants.append(s)
                find_children(s["id"])

    find_children(_id)

    return {"ancestors": list(reversed(ancestors)), "descendants": descendants}


def get_surface_with_context(surface_id: UUID) -> dict[str, Any] | None:
    """Get a surface with its full context: linked outcomes, evolution chain."""
    surface = get_surface(surface_id)
    if not surface:
        return None

    # Linked outcomes details
    linked_outcomes = []
    if surface.get("linked_outcome_ids"):
        sb = get_supabase()
        for oid in surface["linked_outcome_ids"]:
            resp = sb.table("outcomes").select(
                "id, title, description, strength_score, horizon, status"
            ).eq("id", oid).maybe_single().execute()
            if resp.data:
                linked_outcomes.append(resp.data)

    # Evolution chain
    chain = get_evolution_chain(surface_id)

    return {
        **surface,
        "linked_outcomes_detail": linked_outcomes,
        "evolution_chain": chain,
    }


def recompute_all_convergence(project_id: UUID) -> int:
    """Recompute convergence scores for all surfaces in a project.

    Call after bulk outcome changes or generation.
    Returns number of surfaces updated.
    """
    surfaces = list_surfaces(project_id)
    updated = 0
    for s in surfaces:
        oc_ids = s.get("linked_outcome_ids", [])
        new_score = len(oc_ids)
        new_xp = _check_cross_persona(project_id, oc_ids)
        if new_score != s.get("convergence_score") or new_xp != s.get("is_cross_persona"):
            update_surface(UUID(s["id"]), {
                "convergence_score": new_score,
                "is_cross_persona": new_xp,
            })
            updated += 1
    return updated


# =============================================================================
# Dependency Registration
# =============================================================================


def register_surface_dependencies(surface_id: UUID) -> int:
    """Register this surface's entity dependencies for cascade tracking.

    Creates links: surface → outcome, surface → feature, surface → workflow.
    Uses existing entity_dependencies infrastructure.
    """
    from app.db.entity_dependencies import register_dependency

    surface = get_surface(surface_id)
    if not surface:
        return 0

    project_id = UUID(surface["project_id"])
    count = 0

    # Surface depends on each linked outcome
    for oid in surface.get("linked_outcome_ids", []):
        register_dependency(
            project_id=project_id,
            source_type="solution_surface",
            source_id=surface_id,
            target_type="outcome",
            target_id=UUID(oid),
            dependency_type="serves",
            strength=1.0,
            source="structural",
        )
        count += 1

    # Surface depends on each linked feature
    for fid in surface.get("linked_feature_ids", []):
        register_dependency(
            project_id=project_id,
            source_type="solution_surface",
            source_id=surface_id,
            target_type="feature",
            target_id=UUID(fid),
            dependency_type="uses",
            strength=0.8,
            source="structural",
        )
        count += 1

    # Surface depends on each linked workflow
    for wid in surface.get("linked_workflow_ids", []):
        register_dependency(
            project_id=project_id,
            source_type="solution_surface",
            source_id=surface_id,
            target_type="workflow",
            target_id=UUID(wid),
            dependency_type="uses",
            strength=0.7,
            source="structural",
        )
        count += 1

    # If evolves_from, register dependency on parent surface
    if surface.get("evolves_from_id"):
        register_dependency(
            project_id=project_id,
            source_type="solution_surface",
            source_id=surface_id,
            target_type="solution_surface",
            target_id=UUID(surface["evolves_from_id"]),
            dependency_type="derived_from",
            strength=1.0,
            source="structural",
        )
        count += 1

    logger.info(f"Registered {count} dependencies for surface {surface_id}")
    return count


# =============================================================================
# Helpers
# =============================================================================


def _check_cross_persona(project_id: UUID, outcome_ids: list[str]) -> bool:
    """Check if outcomes span multiple actors (cross-persona convergence)."""
    if len(outcome_ids) < 2:
        return False
    sb = get_supabase()
    actors = set()
    for oid in outcome_ids:
        # Get actor outcomes for this outcome
        resp = sb.table("outcome_actors").select("persona_name").eq(
            "outcome_id", oid
        ).execute()
        for row in resp.data or []:
            actors.add(row["persona_name"])
    return len(actors) >= 2
