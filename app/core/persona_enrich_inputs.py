"""Input preparation for persona enrichment."""

from typing import Any
from uuid import UUID

from app.core.embeddings import embed_texts
from app.core.logging import get_logger
from app.db.business_drivers import list_business_drivers
from app.db.context_cache import (
    cached_confirmation_items,
    cached_state_snapshot,
)
from app.db.features import list_features
from app.db.personas import list_personas, list_personas_for_enrichment
from app.db.phase0 import search_signal_chunks

logger = get_logger(__name__)


def retrieve_supporting_chunks(
    project_id: UUID,
    queries: list[str],
    top_k_per_query: int,
    max_total: int,
    include_research: bool = False,
) -> list[dict[str, Any]]:
    """
    Retrieve supporting chunks for persona enrichment context.

    Args:
        project_id: Project UUID
        queries: List of query strings for vector search
        top_k_per_query: Number of results per query
        max_total: Maximum total chunks to return
        include_research: Whether to include research signals

    Returns:
        List of supporting chunks with metadata
    """
    all_chunks = []

    for query in queries:
        # Embed the query
        query_embedding = embed_texts([query])[0]

        # Search chunks with project filter
        chunks = search_signal_chunks(
            query_embedding=query_embedding,
            match_count=top_k_per_query,
            project_id=project_id,
        )

        # Filter by signal type based on research inclusion
        if not include_research:
            filtered_chunks = []
            for chunk in chunks:
                signal_metadata = chunk.get("signal_metadata", {})
                signal_type = signal_metadata.get("signal_type", "")
                if signal_type in ["client_email", "transcripts", "file_text", "notes"]:
                    filtered_chunks.append(chunk)
            chunks = filtered_chunks

        all_chunks.extend(chunks)

    # Remove duplicates based on chunk_id and limit total
    seen_ids = set()
    unique_chunks = []
    for chunk in all_chunks:
        chunk_id = chunk.get("chunk_id")
        if chunk_id and chunk_id not in seen_ids:
            seen_ids.add(chunk_id)
            unique_chunks.append(chunk)
            if len(unique_chunks) >= max_total:
                break

    logger.info(
        f"Retrieved {len(unique_chunks)} unique chunks for persona enrichment",
        extra={"project_id": str(project_id), "query_count": len(queries)},
    )

    return unique_chunks


def build_persona_enrich_prompt(
    project_id: UUID,
    persona: dict[str, Any],
    features: list[dict[str, Any]],
    business_drivers: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    include_research: bool,
    state_snapshot: str | None = None,
) -> str:
    """
    Build the prompt for persona enrichment.

    Args:
        project_id: Project UUID
        persona: Persona dict to enrich
        features: All features for workflow context
        business_drivers: Goals, KPIs, pain points for context
        chunks: Supporting context chunks
        include_research: Whether research was included
        state_snapshot: Optional pre-built state snapshot for project context

    Returns:
        Complete prompt for the LLM
    """
    persona_name = persona.get("name", "Unknown")
    persona_role = persona.get("role", "")
    persona_description = persona.get("description", "")
    persona_goals = persona.get("goals", [])
    persona_pain_points = persona.get("pain_points", [])

    prompt_parts = []

    # Add project context first (if available)
    if state_snapshot:
        prompt_parts.extend([
            state_snapshot,
            "",
            "---",
            "",
        ])

    prompt_parts.extend([
        "# Persona Enrichment Task",
        "",
        f"**Persona to enrich:** {persona_name}",
        f"**Role:** {persona_role}" if persona_role else "",
        f"**Description:** {persona_description}" if persona_description else "",
    ])

    if persona_goals:
        goals_str = ", ".join(persona_goals[:5]) if isinstance(persona_goals, list) else str(persona_goals)[:200]
        prompt_parts.append(f"**Goals:** {goals_str}")

    if persona_pain_points:
        pains_str = ", ".join(persona_pain_points[:5]) if isinstance(persona_pain_points, list) else str(persona_pain_points)[:200]
        prompt_parts.append(f"**Pain Points:** {pains_str}")

    prompt_parts.append("")

    # Add business drivers for context
    if business_drivers:
        goals = [d for d in business_drivers if d.get("driver_type") == "goal"]
        kpis = [d for d in business_drivers if d.get("driver_type") == "kpi"]
        pains = [d for d in business_drivers if d.get("driver_type") == "pain"]

        if goals:
            prompt_parts.append("## Business Goals")
            for g in goals[:4]:
                prompt_parts.append(f"- {g.get('description', '')[:100]}")
            prompt_parts.append("")

        if pains:
            prompt_parts.append("## Business Pain Points")
            for p in pains[:4]:
                prompt_parts.append(f"- {p.get('description', '')[:100]}")
            prompt_parts.append("")

        if kpis:
            prompt_parts.append("## Success Metrics")
            for k in kpis[:4]:
                desc = k.get('description', '')[:80]
                measurement = k.get('measurement', '')
                if measurement:
                    desc += f" → {measurement[:40]}"
                prompt_parts.append(f"- {desc}")
            prompt_parts.append("")

    # Add available features for workflow matching
    if features:
        prompt_parts.extend([
            "## Available Features",
            "Features this persona might use in their workflows:",
        ])
        mvp_features = [f for f in features if f.get("is_mvp")]
        other_features = [f for f in features if not f.get("is_mvp")]

        for f in mvp_features[:10]:
            name = f.get("name", "Unknown")
            category = f.get("category", "")
            cat_label = f" ({category})" if category else ""
            prompt_parts.append(f"- [MVP] {name}{cat_label}")

        for f in other_features[:5]:
            name = f.get("name", "Unknown")
            category = f.get("category", "")
            cat_label = f" ({category})" if category else ""
            prompt_parts.append(f"- {name}{cat_label}")

        prompt_parts.append("")

    # Add context chunks
    if chunks:
        prompt_parts.extend([
            "## Supporting Context",
            f"Relevant excerpts from project signals{' (including research)' if include_research else ''}:",
            "",
            "Each chunk has a chunk_id in [ID:uuid] format for evidence references.",
            "",
        ])
        for i, chunk in enumerate(chunks[:15], 1):
            chunk_id = chunk.get("chunk_id", "")
            snippet = chunk.get("content", chunk.get("snippet", ""))[:300]
            signal_metadata = chunk.get("signal_metadata", {})
            source_type = signal_metadata.get("signal_type", "unknown")
            authority = signal_metadata.get("authority", "unknown")

            prompt_parts.append(f"{i}. [ID:{chunk_id}] [{source_type}/{authority}] {snippet}")
        prompt_parts.append("")

    # Add enrichment instructions
    prompt_parts.extend([
        "## Enrichment Instructions",
        "Analyze this persona and provide enrichment details. Focus on:",
        "",
        "1. **Overview**: Detailed description of who this persona is (3-5 sentences)",
        "   - Their background, daily work, motivations",
        "   - What they care about most",
        "   - Their relationship to the product",
        "",
        "2. **Key Workflows**: 2-4 sequences showing how they use features together",
        "   - Name each workflow (e.g., 'Morning Client Review', 'Weekly Reporting')",
        "   - List 3-6 concrete steps per workflow",
        "   - Reference specific features from the Available Features list",
        "",
        "**IMPORTANT RULES:**",
        "- Base workflows on the persona's goals and pain points",
        "- Only reference features that exist in the Available Features list",
        "- Write in plain consultant language, not technical jargon",
        "- If you reference evidence, use the exact chunk_id from [ID:uuid] prefix",
        "",
        "## Output Format",
        "Output ONLY valid JSON matching the required schema. No markdown, no explanation.",
    ])

    return "\n".join([p for p in prompt_parts if p])  # Filter empty strings


def get_persona_enrich_context(
    project_id: UUID,
    persona_ids: list[UUID] | None = None,
    include_research: bool = False,
    top_k_context: int = 24,
) -> dict[str, Any]:
    """
    Get all context needed for persona enrichment.

    Args:
        project_id: Project UUID
        persona_ids: Optional specific personas to enrich
        include_research: Whether to include research context
        top_k_context: Number of context chunks to retrieve

    Returns:
        Dict with personas, features, business_drivers, chunks, and state_snapshot
    """
    logger.info(
        f"Gathering persona enrichment context for project {project_id}",
        extra={"project_id": str(project_id)},
    )

    # Get state snapshot for comprehensive project context (~500-750 tokens)
    state_snapshot = cached_state_snapshot(project_id)
    logger.info(f"Got state snapshot ({len(state_snapshot)} chars)")

    # Get personas to enrich
    if persona_ids:
        all_personas = list_personas(project_id)
        personas = [p for p in all_personas if UUID(p["id"]) in persona_ids]
    else:
        personas = list_personas_for_enrichment(project_id, only_unenriched=True)

    logger.info(f"Selected {len(personas)} personas for enrichment")

    # Get features for workflow context
    features = list_features(project_id)

    # Get business drivers for goal/pain context
    business_drivers = list_business_drivers(project_id)

    # Get confirmations for resolved decisions
    confirmations = cached_confirmation_items(project_id)

    # Generate queries for vector search
    queries = [
        "Who are the target users and what are their roles?",
        "What are the user workflows and daily tasks?",
        "What problems do users face in their current workflow?",
        "How do users interact with the system?",
        "What are the key user goals and objectives?",
        "What features do users need most?",
    ]

    # Retrieve supporting chunks
    top_k_per_query = max(1, top_k_context // len(queries))
    chunks = retrieve_supporting_chunks(
        project_id=project_id,
        queries=queries,
        top_k_per_query=top_k_per_query,
        max_total=top_k_context,
        include_research=include_research,
    )

    context = {
        "personas": personas,
        "features": features,
        "business_drivers": business_drivers,
        "confirmations": confirmations,
        "chunks": chunks,
        "state_snapshot": state_snapshot,
        "include_research": include_research,
    }

    logger.info(
        f"Gathered persona enrichment context: {len(personas)} personas, "
        f"{len(features)} features, {len(business_drivers)} drivers, "
        f"{len(chunks)} chunks, state_snapshot included",
        extra={"project_id": str(project_id)},
    )

    return context
