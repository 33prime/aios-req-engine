"""Convergence computation: outcome-surface and entity-link convergence.

Two types of convergence:

1. Outcome-Surface: When 2+ outcomes land on the same solution_flow_step,
   generates an insight ("why this matters") and unlock ("what this enables").
   Powers the convergence map visualization.

2. Entity-Link: When an entity has 5+ high-confidence links spanning 3+
   distinct entity types, generates a convergence summary capturing
   cross-cutting patterns. Gets embedded as vector_type='convergence'.

Usage:
    from app.services.convergence import (
        compute_outcome_surface_convergence,
        compute_entity_convergence,
        check_decomposition_threshold,
    )
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)

_MODEL = "claude-haiku-4-5-20251001"
_MAX_RETRIES = 2
_INITIAL_DELAY = 1.0

# Thresholds
_LINK_CONVERGENCE_THRESHOLD = 5   # links needed for convergence computation
_LINK_CONFIDENCE_THRESHOLD = 0.7  # only count semantic + structural (not co-occurrence at 0.5)
_DECOMPOSITION_LINK_THRESHOLD = 10
_DECOMPOSITION_TYPE_THRESHOLD = 3


# =============================================================================
# Outcome-Surface Convergence
# =============================================================================


async def compute_outcome_surface_convergence(
    project_id: UUID,
) -> list[dict[str, Any]]:
    """Compute convergence where 2+ outcomes land on the same solution_flow_step.

    Returns list of convergence records:
    [{
        "step_id": uuid,
        "step_title": str,
        "outcome_count": int,
        "outcomes": [{id, title, persona_names}],
        "is_cross_persona": bool,
        "convergence_insight": str,  # "Why this matters"
        "convergence_unlock": str,   # "What this enables"
    }]
    """
    from app.db.outcomes import get_outcome_entity_links, list_outcomes
    from app.db.supabase_client import get_supabase

    sb = get_supabase()

    # Get all surface_of links
    surface_links = get_outcome_entity_links(link_type="surface_of")
    if not surface_links:
        return []

    # Filter to this project's outcomes
    outcomes = list_outcomes(project_id)
    outcome_ids = {str(o["id"]) for o in outcomes}
    outcome_map = {str(o["id"]): o for o in outcomes}

    project_links = [l for l in surface_links if l["outcome_id"] in outcome_ids]
    if not project_links:
        return []

    # Group by step_id
    by_step: dict[str, list[dict]] = {}
    for link in project_links:
        step_id = link["entity_id"]
        by_step.setdefault(step_id, []).append(link)

    # Find steps with 2+ outcomes
    convergence_steps = {sid: links for sid, links in by_step.items() if len(links) >= 2}
    if not convergence_steps:
        return []

    # Fetch step titles
    step_ids = list(convergence_steps.keys())
    step_resp = sb.table("solution_flow_steps").select("id, title").in_("id", step_ids).execute()
    step_titles = {str(s["id"]): s["title"] for s in (step_resp.data or [])}

    # Fetch actor outcomes for persona tracking
    from app.db.outcomes import list_outcome_actors

    results = []
    for step_id, links in convergence_steps.items():
        outcome_ids_for_step = [l["outcome_id"] for l in links]
        step_outcomes = []
        all_persona_names: set[str] = set()

        for oid in outcome_ids_for_step:
            outcome = outcome_map.get(oid)
            if not outcome:
                continue
            actors = list_outcome_actors(UUID(oid))
            persona_names = [a.get("persona_name", "") for a in actors]
            all_persona_names.update(persona_names)
            step_outcomes.append({
                "id": oid,
                "title": outcome["title"],
                "persona_names": persona_names,
            })

        is_cross_persona = len(all_persona_names) >= 2
        step_title = step_titles.get(step_id, "Unknown")

        # Generate insight + unlock via Haiku
        insight, unlock = await _generate_convergence_text(
            step_title=step_title,
            outcomes=step_outcomes,
            is_cross_persona=is_cross_persona,
        )

        results.append({
            "step_id": step_id,
            "step_title": step_title,
            "outcome_count": len(step_outcomes),
            "outcomes": step_outcomes,
            "is_cross_persona": is_cross_persona,
            "convergence_insight": insight,
            "convergence_unlock": unlock,
        })

    results.sort(key=lambda r: r["outcome_count"], reverse=True)
    logger.info(f"Computed {len(results)} outcome-surface convergence points")
    return results


async def _generate_convergence_text(
    step_title: str,
    outcomes: list[dict],
    is_cross_persona: bool,
) -> tuple[str, str]:
    """Generate convergence insight and unlock text via Haiku."""
    outcome_desc = "\n".join(
        f"- {o['title']} (personas: {', '.join(o.get('persona_names', []))})"
        for o in outcomes
    )

    prompt = (
        f"This screen/page \"{step_title}\" serves {len(outcomes)} outcomes simultaneously:\n\n"
        f"{outcome_desc}\n\n"
        f"{'This is a cross-persona convergence point.' if is_cross_persona else ''}\n\n"
        f"Write two things:\n"
        f"1. INSIGHT (1-2 sentences): Why is it significant that these outcomes converge here? "
        f"What pattern does this reveal?\n"
        f"2. UNLOCK (1 sentence): What does this convergence enable that separate screens couldn't?\n\n"
        f"Be specific to these outcomes. No generic statements."
    )

    try:
        from anthropic import AsyncAnthropic
        from app.core.config import Settings

        settings = Settings()
        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        response = await client.messages.create(
            model=_MODEL,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        text = response.content[0].text if response.content else ""

        # Parse insight and unlock from response
        insight = ""
        unlock = ""
        lines = text.strip().split("\n")
        current = ""
        for line in lines:
            line_lower = line.lower().strip()
            if "insight" in line_lower and ":" in line:
                current = "insight"
                insight = line.split(":", 1)[1].strip()
            elif "unlock" in line_lower and ":" in line:
                current = "unlock"
                unlock = line.split(":", 1)[1].strip()
            elif current == "insight" and line.strip():
                insight += " " + line.strip()
            elif current == "unlock" and line.strip():
                unlock += " " + line.strip()

        return insight.strip(), unlock.strip()

    except Exception as e:
        logger.debug(f"Convergence text generation failed: {e}")
        return (
            f"{len(outcomes)} outcomes converge on this surface.",
            "Combined view eliminates context-switching between separate screens.",
        )


# =============================================================================
# Entity-Link Convergence
# =============================================================================


async def compute_entity_convergence(
    project_id: UUID,
    entity_type: str,
    entity_id: UUID,
) -> dict[str, Any] | None:
    """Compute convergence summary for an entity with 5+ high-confidence links.

    Only counts links with confidence >= 0.7 (semantic + structural).
    Co-occurrence links (confidence 0.5) excluded from threshold count
    but included in the convergence analysis.

    Returns convergence dict or None if threshold not met.
    """
    from app.db.supabase_client import get_supabase

    sb = get_supabase()

    # Get all links for this entity (both directions)
    source_links = (
        sb.table("entity_dependencies")
        .select("target_entity_type, target_entity_id, dependency_type, strength, confidence, source")
        .eq("project_id", str(project_id))
        .eq("source_entity_id", str(entity_id))
        .is_("superseded_by", "null")
        .execute()
    ).data or []

    target_links = (
        sb.table("entity_dependencies")
        .select("source_entity_type, source_entity_id, dependency_type, strength, confidence, source")
        .eq("project_id", str(project_id))
        .eq("target_entity_id", str(entity_id))
        .is_("superseded_by", "null")
        .execute()
    ).data or []

    all_links = source_links + target_links

    # Count high-confidence links
    high_conf_links = [
        l for l in all_links
        if (l.get("confidence") or 0) >= _LINK_CONFIDENCE_THRESHOLD
    ]

    if len(high_conf_links) < _LINK_CONVERGENCE_THRESHOLD:
        return None

    # Get distinct linked entity types
    linked_types: set[str] = set()
    for l in all_links:
        linked_types.add(l.get("target_entity_type") or l.get("source_entity_type", ""))
    linked_types.discard("")

    # Generate convergence summary via Haiku
    summary = await _generate_entity_convergence_text(
        entity_type=entity_type,
        entity_id=entity_id,
        total_links=len(all_links),
        high_conf_links=len(high_conf_links),
        linked_types=linked_types,
        links=all_links[:20],
    )

    # Check decomposition threshold
    decomposition_suggested = (
        len(high_conf_links) >= _DECOMPOSITION_LINK_THRESHOLD
        and len(linked_types) >= _DECOMPOSITION_TYPE_THRESHOLD
    )

    convergence_data = {
        "summary": summary,
        "total_links": len(all_links),
        "high_confidence_links": len(high_conf_links),
        "linked_entity_types": sorted(linked_types),
        "domain_count": len(linked_types),
        "decomposition_suggested": decomposition_suggested,
    }

    # Store on entity
    table_map = {
        "feature": "features",
        "persona": "personas",
        "workflow": "workflows",
        "stakeholder": "stakeholders",
        "business_driver": "business_drivers",
        "data_entity": "data_entities",
        "constraint": "constraints",
        "vp_step": "vp_steps",
    }
    table = table_map.get(entity_type)
    if table:
        try:
            sb.table(table).update({
                "convergence": convergence_data,
                "decomposition_suggested": decomposition_suggested,
            }).eq("id", str(entity_id)).execute()
        except Exception as e:
            logger.debug(f"Failed to store convergence on {entity_type}/{entity_id}: {e}")

    # Embed convergence text
    await _embed_convergence(project_id, entity_type, entity_id, summary)

    logger.info(
        f"Computed convergence for {entity_type}/{entity_id}: "
        f"{len(high_conf_links)} high-conf links, {len(linked_types)} types"
    )

    return convergence_data


async def _generate_entity_convergence_text(
    entity_type: str,
    entity_id: UUID,
    total_links: int,
    high_conf_links: int,
    linked_types: set[str],
    links: list[dict],
) -> str:
    """Generate a convergence summary for a high-link entity."""
    link_desc = "\n".join(
        f"- {l.get('dependency_type', 'related')} → "
        f"{l.get('target_entity_type') or l.get('source_entity_type', '?')}"
        for l in links[:15]
    )

    prompt = (
        f"This {entity_type} has {total_links} connections ({high_conf_links} high-confidence) "
        f"spanning these entity types: {', '.join(sorted(linked_types))}.\n\n"
        f"Link types:\n{link_desc}\n\n"
        f"Write a 2-3 sentence convergence summary:\n"
        f"1. What cross-cutting pattern does this reveal?\n"
        f"2. What would break if this entity failed or changed?\n"
        f"3. What stakeholder domains intersect here?\n\n"
        f"Be specific. This is for a consultant evaluating project risk and priority."
    )

    try:
        from anthropic import AsyncAnthropic
        from app.core.config import Settings

        settings = Settings()
        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        response = await client.messages.create(
            model=_MODEL,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )

        return response.content[0].text.strip() if response.content else ""

    except Exception as e:
        logger.debug(f"Entity convergence text generation failed: {e}")
        return (
            f"This {entity_type} is a convergence node with {total_links} connections "
            f"across {len(linked_types)} domains ({', '.join(sorted(linked_types))})."
        )


async def _embed_convergence(
    project_id: UUID,
    entity_type: str,
    entity_id: UUID,
    summary: str,
) -> None:
    """Embed convergence text as vector_type='convergence' in entity_vectors."""
    if not summary or len(summary.strip()) < 10:
        return

    try:
        from app.core.embeddings import embed_texts_async
        from app.db.supabase_client import get_supabase

        embeddings = await embed_texts_async([summary])
        if not embeddings:
            return

        sb = get_supabase()
        sb.table("entity_vectors").upsert(
            {
                "entity_id": str(entity_id),
                "entity_type": entity_type,
                "project_id": str(project_id),
                "vector_type": "convergence",
                "embedding": embeddings[0],
                "source_text": summary[:500],
                "updated_at": "now()",
            },
            on_conflict="entity_id,entity_type,vector_type",
        ).execute()

    except Exception:
        logger.debug(f"Convergence embedding failed for {entity_type}/{entity_id}", exc_info=True)


# =============================================================================
# Threshold checking (called from patch_applicator)
# =============================================================================


def check_convergence_threshold(
    project_id: UUID,
    entity_type: str,
    entity_id: str,
) -> bool:
    """Check if an entity has crossed the convergence threshold (5+ high-conf links).

    Returns True if convergence should be computed.
    """
    from app.db.supabase_client import get_supabase

    sb = get_supabase()

    try:
        # Count high-confidence links (both directions)
        source_count = (
            sb.table("entity_dependencies")
            .select("id", count="exact")
            .eq("project_id", str(project_id))
            .eq("source_entity_id", entity_id)
            .is_("superseded_by", "null")
            .gte("confidence", _LINK_CONFIDENCE_THRESHOLD)
            .execute()
        ).count or 0

        target_count = (
            sb.table("entity_dependencies")
            .select("id", count="exact")
            .eq("project_id", str(project_id))
            .eq("target_entity_id", entity_id)
            .is_("superseded_by", "null")
            .gte("confidence", _LINK_CONFIDENCE_THRESHOLD)
            .execute()
        ).count or 0

        return (source_count + target_count) >= _LINK_CONVERGENCE_THRESHOLD

    except Exception:
        return False
