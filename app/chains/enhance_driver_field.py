"""AI-assisted field rewriting for business drivers using evidence context.

CONTEXT STRATEGY: Graph neighborhood + manual DB (user-facing, quality-critical).

This chain uses get_entity_neighborhood() to pull the 1-hop graph around the driver —
co-occurring entities via shared signal chunks, plus actual evidence chunk text. This
gives the LLM far richer grounding than the driver's own JSONB evidence array alone.

See docs/context/retrieval-rules.md for when to use graph/retrieval/manual patterns.
"""

import logging
from uuid import UUID

from anthropic import Anthropic

from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

_MODEL = "claude-haiku-4-5-20251001"
_MAX_TOKENS = 500

_SYSTEM = """You are refining a business driver field for a requirements document.
Use the evidence and connections provided to write a clear, specific, well-grounded version.
Be concise but thorough. Cite concrete data from the evidence when available.
IMPORTANT: If the field is 'title', it MUST be 10 words or fewer — a punchy summary.
Return ONLY the rewritten field text — no preamble, no explanation, no quotes."""


def enhance_driver_field(
    project_id: str,
    driver_id: str,
    field_name: str,
    mode: str,
    user_notes: str | None = None,
) -> str:
    """Generate an AI-enhanced version of a business driver field.

    Args:
        project_id: Project UUID
        driver_id: Business driver UUID
        field_name: Which field to enhance (description, title, success_criteria, etc.)
        mode: 'rewrite' or 'notes'
        user_notes: Consultant's direction (only for 'notes' mode)

    Returns:
        The AI-generated suggestion text.
    """
    # Load driver with all context
    client = get_supabase()
    result = client.table("business_drivers").select("*").eq("id", driver_id).single().execute()
    driver = result.data
    if not driver:
        raise ValueError(f"Driver {driver_id} not found")

    driver_type = driver.get("driver_type", "unknown")
    current_value = driver.get(field_name, "") or ""

    # ── Graph neighborhood: pull co-occurring entities + evidence chunks ──
    # This is the key context upgrade — the graph finds related entities the
    # driver's own linked_*_ids may have missed, plus raw signal chunk text
    # that's richer than the truncated evidence excerpts in the JSONB array.
    graph_context = _build_graph_context(driver_id, project_id)

    # ── Driver's own fields ──
    context_parts = [f"Driver type: {driver_type}"]
    context_parts.append(f"Description: {driver.get('description', '')}")

    if driver.get("title"):
        context_parts.append(f"Title: {driver['title']}")

    # Type-specific fields
    if driver_type == "pain":
        for f in ["severity", "business_impact", "affected_users", "current_workaround", "frequency"]:
            if driver.get(f):
                context_parts.append(f"{f.replace('_', ' ').title()}: {driver[f]}")
    elif driver_type == "goal":
        for f in ["success_criteria", "owner", "goal_timeframe", "dependencies"]:
            if driver.get(f):
                context_parts.append(f"{f.replace('_', ' ').title()}: {driver[f]}")
    elif driver_type == "kpi":
        for f in ["baseline_value", "target_value", "measurement_method", "tracking_frequency"]:
            if driver.get(f):
                context_parts.append(f"{f.replace('_', ' ').title()}: {driver[f]}")

    # ── Evidence from JSONB (driver's own excerpts) ──
    evidence = driver.get("evidence") or []
    if isinstance(evidence, list) and evidence:
        context_parts.append("\nEvidence sources:")
        for i, ev in enumerate(evidence[:8], 1):
            excerpt = ev.get("excerpt", "")
            source_type = ev.get("source_type", "")
            rationale = ev.get("rationale", "")
            context_parts.append(f"  [{i}] ({source_type}) \"{excerpt}\"")
            if rationale:
                context_parts.append(f"      Rationale: {rationale}")

    # ── Graph evidence chunks (raw signal text, often richer) ──
    if graph_context.get("evidence_chunks"):
        context_parts.append("\nRaw signal excerpts (from source documents):")
        for i, chunk in enumerate(graph_context["evidence_chunks"][:6], 1):
            content = chunk.get("content", "")[:500]
            meta = chunk.get("metadata") or {}
            speaker = meta.get("speaker_name", "")
            speaker_str = f" — {speaker}" if speaker else ""
            context_parts.append(f"  [{i}] \"{content}\"{speaker_str}")

    # ── Linked entities (explicit + graph-discovered) ──
    linked_feature_ids = driver.get("linked_feature_ids") or []
    if linked_feature_ids:
        try:
            feat_result = client.table("features").select("name").in_("id", [str(fid) for fid in linked_feature_ids[:5]]).execute()
            names = [f["name"] for f in (feat_result.data or [])]
            if names:
                context_parts.append(f"\nLinked features: {', '.join(names)}")
        except Exception:
            pass

    linked_persona_ids = driver.get("linked_persona_ids") or []
    if linked_persona_ids:
        try:
            persona_result = client.table("personas").select("name, role").in_("id", [str(pid) for pid in linked_persona_ids[:5]]).execute()
            names = [f"{p['name']} ({p.get('role', '')})" for p in (persona_result.data or [])]
            if names:
                context_parts.append(f"Linked personas: {', '.join(names)}")
        except Exception:
            pass

    # ── Graph-discovered related entities (co-occurrence) ──
    if graph_context.get("related"):
        related_strs = []
        for rel in graph_context["related"][:8]:
            etype = rel.get("entity_type", "")
            ename = rel.get("entity_name", "")
            shared = rel.get("shared_chunks", 0)
            if ename:
                related_strs.append(f"{etype}: {ename} ({shared} shared signals)")
        if related_strs:
            context_parts.append(f"\nRelated entities (discovered via signal co-occurrence):")
            for r in related_strs:
                context_parts.append(f"  - {r}")

    context_block = "\n".join(context_parts)

    # Build the user prompt
    if mode == "notes" and user_notes:
        user_prompt = (
            f"Rewrite the '{field_name}' field for this business {driver_type}, "
            f"incorporating the consultant's direction: {user_notes}\n"
            f"Also weave in evidence where relevant.\n\n"
            f"Current value: {current_value}\n\n"
            f"Context:\n{context_block}"
        )
    else:
        user_prompt = (
            f"Rewrite the '{field_name}' field for this business {driver_type}, "
            f"incorporating all available evidence. Be specific and cite concrete data.\n\n"
            f"Current value: {current_value}\n\n"
            f"Context:\n{context_block}"
        )

    # Call Haiku
    anthropic = Anthropic()
    response = anthropic.messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        system=_SYSTEM,
        messages=[{"role": "user", "content": user_prompt}],
    )

    suggestion = response.content[0].text.strip()
    logger.info(
        "Enhanced driver field %s.%s (mode=%s, graph_chunks=%d, graph_related=%d, tokens=%d/%d)",
        driver_id[:8], field_name, mode,
        len(graph_context.get("evidence_chunks", [])),
        len(graph_context.get("related", [])),
        response.usage.input_tokens, response.usage.output_tokens,
    )

    return suggestion


def _build_graph_context(driver_id: str, project_id: str) -> dict:
    """Pull entity neighborhood from the graph — evidence chunks + co-occurring entities.

    This is ~50ms of pure SQL (free, no LLM calls). Always use this for user-facing
    chains that rewrite or generate content — the graph finds connections the explicit
    linked_*_ids arrays miss.
    """
    try:
        from app.db.graph_queries import get_entity_neighborhood

        neighborhood = get_entity_neighborhood(
            entity_id=UUID(driver_id),
            entity_type="business_driver",
            project_id=UUID(project_id),
            max_related=10,
        )
        return {
            "evidence_chunks": neighborhood.get("evidence_chunks", []),
            "related": neighborhood.get("related", []),
        }
    except Exception as e:
        logger.warning("Graph neighborhood lookup failed for driver %s: %s", driver_id[:8], e)
        return {"evidence_chunks": [], "related": []}
