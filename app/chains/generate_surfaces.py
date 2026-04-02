"""Generate Solution Surfaces from the entity graph.

Surfaces are the convergence map — user-facing screens that serve
outcomes. This chain reads outcomes, features, workflows, actors,
and constraints to produce surfaces across H1/H2/H3 horizons.

Each surface includes:
- Which outcomes it serves and how
- Experience definition (layout, elements, tone)
- Evolution lineage (what it evolves from/into)
- Roadmap insight (H2/H3: how we get here)
- Convergence insight (multi-outcome surfaces)

Usage:
    from app.chains.generate_surfaces import generate_solution_surfaces

    result = await generate_solution_surfaces(
        project_id=project_id,
        force=False,
    )
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any
from uuid import UUID

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-6"


# =============================================================================
# Tool schema (forced structured output)
# =============================================================================

SURFACE_TOOL = {
    "name": "submit_surfaces",
    "description": "Submit the generated solution surfaces.",
    "input_schema": {
        "type": "object",
        "required": ["surfaces"],
        "properties": {
            "surfaces": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "title", "description", "route", "horizon",
                        "outcome_ids", "how_served", "experience",
                    ],
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Surface name, e.g. 'Self-Service Onboarding'",
                        },
                        "description": {
                            "type": "string",
                            "description": "One sentence describing what this surface does and why.",
                        },
                        "route": {
                            "type": "string",
                            "description": "URL path, e.g. '/onboarding'",
                        },
                        "horizon": {
                            "type": "string",
                            "enum": ["h1", "h2", "h3"],
                        },
                        "outcome_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "IDs of outcomes this surface serves.",
                        },
                        "how_served": {
                            "type": "object",
                            "description": "Map of outcome_id → explanation of how this surface serves that outcome.",
                            "additionalProperties": {"type": "string"},
                        },
                        "evolves_from_title": {
                            "type": "string",
                            "description": "Title of the surface this evolves from (for H2/H3). Must match an H1/H2 surface title exactly.",
                        },
                        "convergence_insight": {
                            "type": "string",
                            "description": "For multi-outcome surfaces: why this convergence matters. Omit for single-outcome surfaces.",
                        },
                        "roadmap_insight": {
                            "type": "string",
                            "description": "For H2/H3: narrative explaining the path from Now to this surface. What triggers it, what data is needed, what has to be true.",
                        },
                        "feature_names": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Names of features/capabilities that power this surface.",
                        },
                        "workflow_names": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Names of workflows that flow through this surface.",
                        },
                        "experience": {
                            "type": "object",
                            "required": ["narr", "layout", "elements", "interaction", "tone", "reference"],
                            "properties": {
                                "narr": {
                                    "type": "string",
                                    "description": "2-3 sentences describing what it feels like to use this surface. Written for a consultant, not a developer. First person perspective of the user.",
                                },
                                "layout": {
                                    "type": "string",
                                    "description": "Layout archetype, e.g. 'Guided wizard flow', 'Dashboard with detail panels'",
                                },
                                "elements": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Key UI elements, 3-6 items, e.g. 'Progress stepper', 'Data input cards'",
                                },
                                "interaction": {
                                    "type": "string",
                                    "description": "How it feels to use: 'Sequential, confidence-building', 'Scan, prioritize, act'",
                                },
                                "tone": {
                                    "type": "string",
                                    "description": "Emotional tone with a tagline: 'Warm and orienting — Let\\'s figure out where you are'",
                                },
                                "reference": {
                                    "type": "string",
                                    "description": "Familiar product analogy: 'Typeform meets Stripe onboarding'",
                                },
                            },
                        },
                    },
                },
            },
        },
    },
}


# =============================================================================
# Prompt
# =============================================================================

SYSTEM_PROMPT = """You are a senior solutions architect designing the convergence map for a platform.

Your job is to determine the minimum set of user-facing screens (surfaces) that serve all outcomes.
The best surfaces serve MULTIPLE outcomes simultaneously — that's convergence.

Design principles:
1. MAXIMIZE CONVERGENCE. If one screen can serve 3 outcomes, that's better than 3 screens serving 1 each.
2. Cross-persona convergence is the highest value — one surface serving outcomes for different actors.
3. Every H1 outcome MUST have at least one surface.
4. H2 surfaces evolve from H1 surfaces — they extend what's already built, not replace it.
5. H3 surfaces are the vision — they require H2 to be stable before they're viable.
6. Experience descriptions are for consultants, not developers. Use business language. Describe feelings, not code.
7. Roadmap insights for H2/H3 should explain the trigger ("what signals that it's time to build this") and the dependency ("what has to be true first").
8. Keep it tight. 6-8 H1 surfaces, 3-5 H2 surfaces, 2-4 H3 surfaces.

Write as a consultant who deeply understands the client's business. No jargon. No generic descriptions."""


def _build_user_prompt(
    project_name: str,
    project_type: str,
    macro_outcome: str,
    outcomes: list[dict],
    features: list[dict],
    workflows: list[dict],
    actors: list[dict],
    constraints: list[dict],
) -> str:
    """Build the user prompt from entity data."""
    parts = [
        f"Project: {project_name} (type: {project_type})",
    ]
    if macro_outcome:
        parts.append(f"Macro Outcome: {macro_outcome}")

    parts.append("\n## Outcomes")
    for o in outcomes:
        actors_str = ", ".join(a.get("persona_name", "?") for a in (o.get("actors") or []))
        parts.append(
            f"- [{o.get('horizon','h1').upper()}] ID:{o['id']} | {o['title']} "
            f"(strength: {o.get('strength_score',0)}, actors: {actors_str})"
        )

    if features:
        parts.append("\n## Features / Capabilities")
        for f in features:
            parts.append(f"- {f.get('name','?')}")

    if workflows:
        parts.append("\n## Workflows")
        for w in workflows:
            steps = w.get("steps") or []
            step_count = len(steps) if isinstance(steps, list) else w.get("step_count", 0)
            parts.append(f"- {w.get('name','?')} ({step_count} steps, {w.get('state_type','current')})")

    if actors:
        parts.append("\n## Actors")
        for a in actors:
            goals = ", ".join((a.get("goals") or [])[:3])
            parts.append(f"- {a.get('name','?')} ({a.get('role','')}): {goals}")

    if constraints:
        parts.append("\n## Constraints")
        for c in constraints:
            parts.append(f"- {c.get('title','?')}")

    parts.append(
        "\n\nGenerate the solution surfaces. Every H1 outcome must be served. "
        "Maximize convergence. Include experience definitions for ALL surfaces. "
        "H2 surfaces must reference which H1 surface they evolve from (by title). "
        "H3 surfaces must reference which H2 surface they evolve from."
    )

    return "\n".join(parts)


# =============================================================================
# Generation
# =============================================================================


async def generate_solution_surfaces(
    project_id: UUID,
    force: bool = False,
) -> dict[str, Any]:
    """Generate solution surfaces from the entity graph."""
    from anthropic import AsyncAnthropic
    from app.db.supabase_client import get_supabase
    from app.db.surfaces import (
        list_surfaces, create_surface, register_surface_dependencies,
    )
    from app.db.outcomes import list_outcomes

    settings = get_settings()
    sb = get_supabase()
    start = time.time()

    # Check existing surfaces
    existing = list_surfaces(project_id)
    if existing and not force:
        return {
            "skipped": True,
            "reason": f"Already have {len(existing)} surfaces. Pass force=true to regenerate.",
            "surfaces": existing,
        }

    # Load project context
    project = sb.table("projects").select("*").eq("id", str(project_id)).single().execute().data
    project_name = project.get("name", "")
    project_type = project.get("project_type", "new_product")
    macro_outcome = project.get("macro_outcome") or ""

    # Load outcomes with actors
    outcomes_raw = list_outcomes(project_id)
    outcomes_data = []
    for o in outcomes_raw:
        actors_resp = sb.table("outcome_actors").select("*").eq(
            "outcome_id", str(o["id"])
        ).execute()
        o["actors"] = actors_resp.data or []
        outcomes_data.append(o)

    if not outcomes_data:
        return {"skipped": True, "reason": "No outcomes to generate surfaces from."}

    # Load supporting entities
    features = sb.table("features").select("name").eq(
        "project_id", str(project_id)
    ).execute().data or []
    workflows = sb.table("workflows").select(
        "name, state_type"
    ).eq("project_id", str(project_id)).execute().data or []
    personas = sb.table("personas").select(
        "name, role, goals"
    ).eq("project_id", str(project_id)).execute().data or []
    constraints = sb.table("constraints").select(
        "title"
    ).eq("project_id", str(project_id)).execute().data or []

    # Build prompt
    user_msg = _build_user_prompt(
        project_name, project_type, macro_outcome,
        outcomes_data, features, workflows, personas, constraints,
    )

    # Call LLM with forced tool use
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = await client.messages.create(
        model=_MODEL,
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        tools=[SURFACE_TOOL],
        tool_choice={"type": "tool", "name": "submit_surfaces"},
        messages=[{"role": "user", "content": user_msg}],
    )

    # Extract tool result
    tool_block = next(
        (b for b in response.content if b.type == "tool_use"),
        None,
    )
    if not tool_block:
        return {"error": "No tool response from LLM", "surfaces_created": 0}

    generated = tool_block.input.get("surfaces", [])
    logger.info(f"LLM generated {len(generated)} surfaces")

    # Delete existing surfaces if force
    if existing and force:
        for s in existing:
            sb.table("solution_surfaces").delete().eq("id", s["id"]).execute()
        logger.info(f"Deleted {len(existing)} existing surfaces")

    # Build outcome ID lookup
    oc_id_map = {o["id"]: o for o in outcomes_data}

    # Build feature name → id lookup
    all_features = sb.table("features").select("id, name").eq(
        "project_id", str(project_id)
    ).execute().data or []
    feature_name_map = {f["name"].lower(): f["id"] for f in all_features}

    # Build workflow name → id lookup
    all_workflows = sb.table("workflows").select("id, name").eq(
        "project_id", str(project_id)
    ).execute().data or []
    workflow_name_map = {w["name"].lower(): w["id"] for w in all_workflows}

    # First pass: create all surfaces (need IDs before we can set evolves_from)
    created_surfaces: list[dict] = []
    title_to_id: dict[str, str] = {}

    for idx, s in enumerate(generated):
        # Resolve feature IDs
        feature_ids = []
        for fn in s.get("feature_names", []):
            fid = feature_name_map.get(fn.lower())
            if fid:
                feature_ids.append(fid)

        # Resolve workflow IDs
        workflow_ids = []
        for wn in s.get("workflow_names", []):
            wid = workflow_name_map.get(wn.lower())
            if wid:
                workflow_ids.append(wid)

        # Validate outcome IDs
        valid_oc_ids = [oid for oid in s.get("outcome_ids", []) if oid in oc_id_map]

        surface = create_surface(
            project_id=project_id,
            title=s["title"],
            description=s.get("description", ""),
            route=s.get("route"),
            horizon=s.get("horizon", "h1"),
            convergence_insight=s.get("convergence_insight"),
            roadmap_insight=s.get("roadmap_insight"),
            how_served=s.get("how_served", {}),
            experience=s.get("experience", {}),
            linked_outcome_ids=valid_oc_ids,
            linked_feature_ids=feature_ids,
            linked_workflow_ids=workflow_ids,
            sort_order=idx,
        )
        created_surfaces.append(surface)
        title_to_id[s["title"].lower().strip()] = surface["id"]

    # Second pass: set evolves_from pointers
    for s_data, surface in zip(generated, created_surfaces):
        evolves_title = s_data.get("evolves_from_title")
        if evolves_title:
            parent_id = title_to_id.get(evolves_title.lower().strip())
            if parent_id:
                sb.table("solution_surfaces").update({
                    "evolves_from_id": parent_id,
                }).eq("id", surface["id"]).execute()

    # Third pass: register dependencies for cascade tracking
    for surface in created_surfaces:
        register_surface_dependencies(UUID(surface["id"]))

    # Register outcome_entity_links (surface_of)
    from app.db.outcomes import create_outcome_entity_link
    for surface in created_surfaces:
        for oid in surface.get("linked_outcome_ids", []):
            try:
                create_outcome_entity_link(
                    outcome_id=UUID(oid),
                    entity_id=UUID(surface["id"]),
                    entity_type="solution_surface",
                    link_type="surface_of",
                    how_served=surface.get("how_served", {}).get(oid, ""),
                )
            except Exception:
                pass  # Duplicate link is fine

    duration = int((time.time() - start) * 1000)
    logger.info(
        f"Generated {len(created_surfaces)} surfaces in {duration}ms"
    )

    return {
        "surfaces_created": len(created_surfaces),
        "surfaces": created_surfaces,
        "duration_ms": duration,
        "model": _MODEL,
    }


# =============================================================================
# Experience generation (single surface)
# =============================================================================


async def generate_surface_experience(
    project_id: UUID,
    surface_id: UUID,
) -> dict[str, Any]:
    """Generate or regenerate the experience definition for a single surface."""
    from anthropic import AsyncAnthropic
    from app.db.surfaces import get_surface_with_context, update_surface

    settings = get_settings()
    surface = get_surface_with_context(surface_id)
    if not surface:
        return {"error": "Surface not found"}

    outcomes_text = "\n".join(
        f"- {o['title']} (strength: {o.get('strength_score',0)})"
        for o in surface.get("linked_outcomes_detail", [])
    )

    prompt = f"""Generate the experience definition for this solution surface.

Surface: {surface['title']}
Description: {surface.get('description', '')}
Route: {surface.get('route', '')}
Horizon: {surface.get('horizon', 'h1')}

Outcomes this surface serves:
{outcomes_text}

Write the experience definition as if briefing a consultant who will present this to a client.
Use business language, not technical jargon. Describe the feeling of using it.

Return a JSON object with these fields:
- narr: 2-3 sentences, first-person perspective of the user, what it feels like
- layout: layout archetype (e.g. "Guided wizard flow", "Dashboard with detail panels")
- elements: array of 3-6 key UI elements (e.g. "Progress stepper", "Data input cards")
- interaction: how it feels to use (e.g. "Sequential, confidence-building")
- tone: emotional tone with tagline (e.g. "Warm and orienting — Let's figure out where you are")
- reference: familiar product analogy (e.g. "Typeform meets Stripe onboarding")

Return ONLY valid JSON, no markdown fences."""

    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = await client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        import re
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

    experience = json.loads(raw)
    updated = update_surface(surface_id, {"experience": experience})

    return {"surface_id": str(surface_id), "experience": experience}
