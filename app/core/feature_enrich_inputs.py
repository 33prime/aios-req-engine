"""Input preparation for feature enrichment."""

from typing import Any
from uuid import UUID

from app.core.embeddings import embed_texts
from app.core.logging import get_logger
from app.core.state_snapshot import get_state_snapshot
from app.db.confirmations import list_confirmation_items
from app.db.facts import list_latest_extracted_facts
from app.db.features import list_features
from app.db.phase0 import search_signal_chunks

logger = get_logger(__name__)


def select_chunks_for_feature_enrich(
    chunks: list[dict[str, Any]], max_chunks: int, max_chars_per_chunk: int
) -> list[dict[str, Any]]:
    """
    Select and truncate chunks for feature enrichment context.

    Args:
        chunks: Raw chunks from vector search
        max_chunks: Maximum number of chunks to include
        max_chars_per_chunk: Maximum characters per chunk snippet

    Returns:
        Selected and truncated chunks
    """
    selected = chunks[:max_chunks]

    # Truncate chunk content to max_chars_per_chunk
    for chunk in selected:
        if "snippet" in chunk and len(chunk["snippet"]) > max_chars_per_chunk:
            chunk["snippet"] = chunk["snippet"][:max_chars_per_chunk] + "..."

    return selected


def retrieve_supporting_chunks(
    project_id: UUID,
    queries: list[str],
    top_k_per_query: int,
    max_total: int,
    include_research: bool = False,
) -> list[dict[str, Any]]:
    """
    Retrieve supporting chunks for feature enrichment context.

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
            # Only include client signals when research is disabled
            filtered_chunks = []
            for chunk in chunks:
                # Get signal_type from signal_metadata (returned by match_signal_chunks RPC)
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
        f"Retrieved {len(unique_chunks)} unique chunks for enrichment",
        extra={"project_id": str(project_id), "query_count": len(queries)},
    )

    return unique_chunks


def build_feature_enrich_prompt(
    project_id: UUID,
    feature: dict[str, Any],
    facts: list[dict[str, Any]],
    confirmations: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    include_research: bool,
    state_snapshot: str | None = None,
) -> str:
    """
    Build the prompt for feature enrichment.

    Args:
        project_id: Project UUID
        feature: Feature dict to enrich
        facts: Latest extracted facts
        confirmations: Open/resolved confirmations for context
        chunks: Supporting context chunks
        include_research: Whether research was included
        state_snapshot: Optional pre-built state snapshot for project context

    Returns:
        Complete prompt for the LLM
    """
    feature_name = feature.get("name", "Unknown Feature")
    feature_category = feature.get("category", "General")
    is_mvp = feature.get("is_mvp", False)
    current_description = feature.get("description", "No description available")

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
        f"# Feature Enrichment Task",
        f"",
        f"**Feature to enrich:** {feature_name}",
        f"**Category:** {feature_category}",
        f"**MVP Status:** {'Yes' if is_mvp else 'No'}",
        f"**Current Description:** {current_description}",
        f"",
    ])

    # Add resolved decisions from confirmations
    resolved_decisions = [
        c for c in confirmations
        if c.get("status") in ["resolved", "confirmed_client", "confirmed_consultant"]
    ]
    if resolved_decisions:
        prompt_parts.extend([
            f"## Resolved Decisions (Reference Only)",
            f"These decisions have already been confirmed - use them for context but do not re-question:",
        ])
        for decision in resolved_decisions[:5]:  # Limit to 5 most recent
            prompt_parts.append(f"- **{decision.get('title', 'Unknown')}**: {decision.get('why', '')}")
        prompt_parts.append("")

    # Add extracted facts
    if facts:
        prompt_parts.extend([
            f"## Extracted Facts",
            f"Recent facts extracted from signals:",
        ])
        for fact in facts[:10]:  # Limit to 10 facts
            summary = fact.get("summary", "")
            if summary:
                prompt_parts.append(f"- {summary}")
        prompt_parts.append("")

    # Add context chunks
    if chunks:
        prompt_parts.extend([
            f"## Supporting Context",
            f"Relevant excerpts from project signals{' (including research)' if include_research else ''}:",
            f"",
            f"Each chunk has a chunk_id in [ID:uuid] format that you MUST use when referencing evidence.",
            f"",
        ])
        for i, chunk in enumerate(chunks[:20], 1):  # Limit to 20 chunks
            chunk_id = chunk.get("chunk_id", "")
            snippet = chunk.get("snippet", "")
            source_type = chunk.get("signal_type", "unknown")
            authority = chunk.get("authority", "unknown")
            created_at = chunk.get("created_at", "")[:10]  # Date only

            prompt_parts.append(f"{i}. [ID:{chunk_id}] [{source_type}/{authority}/{created_at}] {snippet}")
        prompt_parts.append("")

    # Add output instructions
    prompt_parts.extend([
        f"## Enrichment Instructions",
        f"Analyze this feature and provide structured enrichment details. Focus on:",
        f"",
        f"1. **Summary**: Concise description of the feature's purpose and scope",
        f"2. **Data Requirements**: Entities and fields this feature needs",
        f"3. **Business Rules**: Logic and validation rules",
        f"4. **Acceptance Criteria**: What must be true for this feature to be complete",
        f"5. **Dependencies**: Other features, systems, or processes required",
        f"6. **Integrations**: External systems this feature connects to",
        f"7. **Telemetry Events**: Events this feature should emit for monitoring",
        f"8. **Risks**: Potential issues and their mitigations",
        f"",
        f"**IMPORTANT RULES:**",
        f"- Every item MUST include evidence references (chunk_id + excerpt + rationale)",
        f"- chunk_id MUST be an exact UUID copied from the [ID:uuid] prefix in Supporting Context above",
        f"- DO NOT make up or fabricate chunk_ids - only use the exact UUIDs provided",
        f"- If no chunks support a section, use an empty evidence array []",
        f"- Excerpts must be verbatim from the provided chunks (max 280 chars)",
        f"- Empty arrays are allowed if no evidence exists for a section",
        f"- Do not make assumptions - base everything on provided context",
        f"- If information is unclear, add to open_questions instead of guessing",
        f"",
        f"## Output Format",
        f"Output ONLY valid JSON matching the required schema. No markdown, no explanation.",
    ])

    return "\n".join(prompt_parts)


def get_feature_enrich_context(
    project_id: UUID,
    feature_ids: list[UUID] | None = None,
    only_mvp: bool = False,
    include_research: bool = False,
    top_k_context: int = 24,
) -> dict[str, Any]:
    """
    Get all context needed for feature enrichment.

    Args:
        project_id: Project UUID
        feature_ids: Optional specific features to enrich
        only_mvp: Whether to only enrich MVP features
        include_research: Whether to include research in context
        top_k_context: Number of context chunks to retrieve

    Returns:
        Dict with features, facts, confirmations, chunks, and state_snapshot
    """
    logger.info(
        f"Gathering enrichment context for project {project_id}",
        extra={"project_id": str(project_id)},
    )

    # Get state snapshot for comprehensive project context (~500-750 tokens)
    # This includes: identity, strategic context (drivers), product state, market context
    state_snapshot = get_state_snapshot(project_id)
    logger.info(f"Got state snapshot ({len(state_snapshot)} chars)")

    # Get features to enrich
    all_features = list_features(project_id)
    if feature_ids:
        features = [f for f in all_features if f["id"] in feature_ids]
    else:
        features = all_features

    if only_mvp:
        features = [f for f in features if f.get("is_mvp", False)]

    logger.info(f"Selected {len(features)} features for enrichment")

    # Get latest facts for context (insights system removed)
    facts = list_latest_extracted_facts(project_id, limit=10)
    insights: list = []  # Insights system removed

    # Get confirmations for context
    confirmations = list_confirmation_items(project_id)

    # Generate queries for vector search
    queries = [
        "What are the detailed requirements and specifications for features?",
        "What data entities and fields are needed for features?",
        "What business rules and validation logic apply to features?",
        "What integrations and dependencies do features have?",
        "What are the success metrics and telemetry for features?",
        "What risks and challenges are associated with features?",
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
        "features": features,
        "facts": facts,
        "insights": insights,
        "confirmations": confirmations,
        "chunks": chunks,
        "state_snapshot": state_snapshot,
        "include_research": include_research,
    }

    logger.info(
        f"Gathered enrichment context: {len(features)} features, {len(facts)} facts, "
        f"{len(confirmations)} confirmations, {len(chunks)} chunks, state_snapshot included",
        extra={"project_id": str(project_id)},
    )

    return context
