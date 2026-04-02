"""Solution Surfaces API routes.

Endpoints for managing solution surfaces — the convergence map entities
that represent user-facing screens serving one or more outcomes.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/surfaces")


# =============================================================================
# Request schemas
# =============================================================================


class SurfaceCreateRequest(BaseModel):
    title: str
    description: str = ""
    route: str | None = None
    horizon: str = "h1"
    evolves_from_id: str | None = None
    convergence_insight: str | None = None
    roadmap_insight: str | None = None
    how_served: dict[str, str] = Field(default_factory=dict)
    experience: dict[str, Any] = Field(default_factory=dict)
    linked_outcome_ids: list[str] = Field(default_factory=list)
    linked_feature_ids: list[str] = Field(default_factory=list)
    linked_workflow_ids: list[str] = Field(default_factory=list)
    position_x: float = 0
    position_y: float = 0
    sort_order: int = 0


class SurfaceUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    route: str | None = None
    horizon: str | None = None
    evolves_from_id: str | None = None
    convergence_insight: str | None = None
    roadmap_insight: str | None = None
    how_served: dict[str, str] | None = None
    experience: dict[str, Any] | None = None
    linked_outcome_ids: list[str] | None = None
    linked_feature_ids: list[str] | None = None
    linked_workflow_ids: list[str] | None = None
    position_x: float | None = None
    position_y: float | None = None
    sort_order: int | None = None
    confirmation_status: str | None = None


# =============================================================================
# CRUD endpoints
# =============================================================================


@router.get("")
async def list_surfaces(project_id: UUID, horizon: str | None = None):
    """List all solution surfaces for a project."""
    from app.db.surfaces import list_surfaces as db_list

    surfaces = db_list(project_id, horizon=horizon)
    return {"surfaces": surfaces, "count": len(surfaces)}


@router.get("/{surface_id}")
async def get_surface(project_id: UUID, surface_id: UUID):
    """Get a surface with full context (linked outcomes, evolution chain)."""
    from app.db.surfaces import get_surface_with_context

    surface = get_surface_with_context(surface_id)
    if not surface:
        raise HTTPException(status_code=404, detail="Surface not found")
    return surface


@router.post("")
async def create_surface(project_id: UUID, request: SurfaceCreateRequest):
    """Create a new solution surface."""
    from app.db.surfaces import create_surface as db_create, register_surface_dependencies

    surface = db_create(
        project_id=project_id,
        title=request.title,
        description=request.description,
        route=request.route,
        horizon=request.horizon,
        evolves_from_id=request.evolves_from_id,
        convergence_insight=request.convergence_insight,
        roadmap_insight=request.roadmap_insight,
        how_served=request.how_served,
        experience=request.experience,
        linked_outcome_ids=request.linked_outcome_ids,
        linked_feature_ids=request.linked_feature_ids,
        linked_workflow_ids=request.linked_workflow_ids,
        position_x=request.position_x,
        position_y=request.position_y,
        sort_order=request.sort_order,
    )

    # Register in dependency graph for cascade tracking
    register_surface_dependencies(UUID(surface["id"]))

    return surface


@router.patch("/{surface_id}")
async def update_surface(project_id: UUID, surface_id: UUID, request: SurfaceUpdateRequest):
    """Update a solution surface."""
    from app.db.surfaces import update_surface as db_update, register_surface_dependencies

    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    surface = db_update(surface_id, updates)

    # Re-register dependencies if links changed
    if any(k in updates for k in ("linked_outcome_ids", "linked_feature_ids", "linked_workflow_ids", "evolves_from_id")):
        register_surface_dependencies(surface_id)

    return surface


@router.delete("/{surface_id}")
async def delete_surface(project_id: UUID, surface_id: UUID):
    """Delete a solution surface."""
    from app.db.surfaces import delete_surface as db_delete

    db_delete(surface_id)
    return {"deleted": True}


# =============================================================================
# Freshness
# =============================================================================


@router.post("/{surface_id}/refresh")
async def refresh_surface(project_id: UUID, surface_id: UUID):
    """Clear staleness flag after consultant reviews changes."""
    from app.db.surfaces import clear_staleness

    surface = clear_staleness(surface_id)
    return surface


# =============================================================================
# Evolution
# =============================================================================


@router.get("/{surface_id}/evolution")
async def get_evolution_chain(project_id: UUID, surface_id: UUID):
    """Get the full evolution chain for a surface (ancestors + descendants)."""
    from app.db.surfaces import get_evolution_chain as db_chain

    chain = db_chain(surface_id)
    return chain


# =============================================================================
# Cascade impact
# =============================================================================


@router.get("/{surface_id}/impact")
async def get_cascade_impact(project_id: UUID, surface_id: UUID):
    """Analyze what would be affected if this surface changes."""
    from app.db.entity_dependencies import get_impact_analysis

    impact = get_impact_analysis(
        project_id=project_id,
        entity_type="solution_surface",
        entity_id=surface_id,
    )
    return impact


# =============================================================================
# Convergence
# =============================================================================


@router.post("/recompute-convergence")
async def recompute_convergence(project_id: UUID):
    """Recompute convergence scores for all surfaces in a project."""
    from app.db.surfaces import recompute_all_convergence

    updated = recompute_all_convergence(project_id)
    return {"surfaces_updated": updated}


# =============================================================================
# Generation
# =============================================================================


@router.post("/generate")
async def generate_surfaces(project_id: UUID, force: bool = False):
    """Generate solution surfaces from outcomes, features, and workflows.

    Uses the project's entity graph to create a convergence-optimized
    set of surfaces across H1/H2/H3 horizons.
    """
    from app.chains.generate_surfaces import generate_solution_surfaces

    result = await generate_solution_surfaces(
        project_id=project_id,
        force=force,
    )
    return result


@router.post("/{surface_id}/generate-experience")
async def generate_experience(project_id: UUID, surface_id: UUID):
    """Generate the experience definition for a surface using LLM."""
    from app.chains.generate_surfaces import generate_surface_experience

    result = await generate_surface_experience(
        project_id=project_id,
        surface_id=surface_id,
    )
    return result
