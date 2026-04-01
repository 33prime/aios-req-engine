"""Intelligence discovery feedback: capabilities reveal new outcome connections.

When a capability is confirmed, check if it could serve outcomes it's not
currently linked to. This is the "intelligence layer as discovery tool" concept.

Usage:
    from app.services.intelligence_discovery import discover_outcome_connections

    suggestions = await discover_outcome_connections(project_id, capability_id)
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


async def discover_outcome_connections(
    project_id: UUID,
    capability_id: UUID,
) -> list[dict[str, Any]]:
    """Check if a capability could serve outcomes it's not currently linked to.

    Returns list of suggested connections:
    [{outcome_id, outcome_title, similarity, suggestion_text}]
    """
    from app.db.outcomes import list_outcomes
    from app.db.supabase_client import get_supabase

    sb = get_supabase()

    # Get the capability
    cap_resp = (
        sb.table("outcome_capabilities")
        .select("*")
        .eq("id", str(capability_id))
        .maybe_single()
        .execute()
    )
    if not cap_resp.data:
        return []

    cap = cap_resp.data
    current_outcome_id = cap.get("outcome_id")

    # Get capability embedding
    cap_ev = (
        sb.table("entity_vectors")
        .select("embedding")
        .eq("entity_id", str(capability_id))
        .eq("entity_type", "outcome_capability")
        .eq("vector_type", "identity")
        .maybe_single()
        .execute()
    )

    if not cap_ev.data:
        # No embedding yet — can't do similarity search
        return []

    cap_embedding = cap_ev.data["embedding"]

    # Get all outcomes for the project
    outcomes = list_outcomes(project_id)
    if not outcomes:
        return []

    # Get outcome embeddings
    outcome_ids = [str(o["id"]) for o in outcomes]
    oc_evs = (
        sb.table("entity_vectors")
        .select("entity_id, embedding")
        .in_("entity_id", outcome_ids)
        .eq("entity_type", "outcome")
        .eq("vector_type", "identity")
        .execute()
    )

    outcome_embeddings = {r["entity_id"]: r["embedding"] for r in (oc_evs.data or [])}

    # Compare capability against all outcomes
    from app.core.embeddings import cosine_similarity

    suggestions = []
    for outcome in outcomes:
        oid = str(outcome["id"])

        # Skip the outcome it's already linked to
        if oid == str(current_outcome_id):
            continue

        outcome_emb = outcome_embeddings.get(oid)
        if not outcome_emb:
            continue

        sim = cosine_similarity(cap_embedding, outcome_emb)
        if sim > 0.7:
            suggestions.append({
                "outcome_id": oid,
                "outcome_title": outcome["title"],
                "similarity": round(sim, 3),
                "suggestion_text": (
                    f"'{cap['name']}' was built for "
                    f"\"{outcomes[0]['title'][:40]}\" but could also serve "
                    f"\"{outcome['title'][:40]}\" (similarity: {sim:.0%})"
                ),
                "capability_name": cap["name"],
                "capability_quadrant": cap["quadrant"],
            })

    # Sort by similarity descending
    suggestions.sort(key=lambda s: s["similarity"], reverse=True)

    if suggestions:
        logger.info(
            f"Intelligence discovery: capability {cap['name']} "
            f"has {len(suggestions)} cross-outcome connections"
        )

    return suggestions


async def run_discovery_after_confirm(
    project_id: UUID,
    capability_id: UUID,
) -> list[dict[str, Any]]:
    """Post-confirmation hook: discover connections and create suggested links.

    Called after a capability is confirmed. Finds cross-outcome connections
    and creates suggested outcome_entity_links for consultant review.
    """
    suggestions = await discover_outcome_connections(project_id, capability_id)

    if not suggestions:
        return []

    from app.db.outcomes import create_outcome_entity_link

    created_links = []
    for suggestion in suggestions:
        try:
            link = create_outcome_entity_link(
                outcome_id=UUID(suggestion["outcome_id"]),
                entity_id=str(capability_id),
                entity_type="outcome_capability",
                link_type="enables",
                how_served=suggestion["suggestion_text"],
                confidence="ai_generated",
            )
            if link:
                created_links.append(link)
        except Exception:
            pass

    if created_links:
        logger.info(
            f"Created {len(created_links)} cross-outcome links "
            f"for capability {capability_id}"
        )

    return created_links
