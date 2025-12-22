"""Input preparation for PRD section enrichment."""

from typing import Any
from uuid import UUID

from app.core.embeddings import embed_texts
from app.core.logging import get_logger
from app.db.confirmations import list_confirmation_items
from app.db.facts import list_latest_extracted_facts
from app.db.insights import list_latest_insights
from app.db.phase0 import search_signal_chunks
from app.db.prd import list_prd_sections

logger = get_logger(__name__)


def select_chunks_for_prd_enrich(
    chunks: list[dict[str, Any]], max_chunks: int, max_chars_per_chunk: int
) -> list[dict[str, Any]]:
    """
    Select and truncate chunks for PRD enrichment context.

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
    Retrieve supporting chunks for PRD enrichment context.

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
        f"Retrieved {len(unique_chunks)} unique chunks for PRD enrichment (from {len(all_chunks)} total)",
        extra={"project_id": str(project_id), "query_count": len(queries)},
    )

    # Debug: Log chunk metadata structure
    if unique_chunks:
        sample_chunk = unique_chunks[0]
        logger.info(
            f"Sample chunk metadata: signal_metadata keys: {list(sample_chunk.get('signal_metadata', {}).keys())}",
            extra={"project_id": str(project_id)},
        )

    return unique_chunks


def build_prd_enrich_prompt(
    section: dict[str, Any],
    canonical_prd: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    confirmations: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    include_research: bool,
) -> str:
    """
    Build the prompt for PRD section enrichment.

    Args:
        section: PRD section dict to enrich
        canonical_prd: All PRD sections for context
        facts: Latest extracted facts
        confirmations: Open/resolved confirmations for context
        chunks: Supporting context chunks
        include_research: Whether research was included

    Returns:
        Complete prompt for the LLM
    """
    section_slug = section.get("slug", "unknown")
    section_label = section.get("label", "Unknown Section")
    current_fields = section.get("fields", {})
    current_content = current_fields.get("content", "No content available")

    prompt_parts = [
        f"# PRD Section Enrichment Task",
        f"",
        f"**Section to enrich:** {section_label} ({section_slug})",
        f"**Current Content:** {current_content[:500]}{'...' if len(current_content) > 500 else ''}",
        f"",
    ]

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

    # Add context from other PRD sections
    other_sections = [s for s in canonical_prd if s["id"] != section["id"]]
    if other_sections:
        prompt_parts.extend([
            f"## Related PRD Sections",
            f"Context from other sections in this PRD:",
        ])
        for other in other_sections[:3]:  # Limit to 3 related sections
            other_content = other.get("fields", {}).get("content", "")
            if other_content:
                truncated = other_content[:200] + "..." if len(other_content) > 200 else other_content
                prompt_parts.append(f"- **{other.get('label', 'Unknown')}**: {truncated}")
        prompt_parts.append("")

    # Add extracted facts
    if facts:
        prompt_parts.extend([
            f"## Extracted Facts",
            f"Recent facts extracted from signals:",
        ])
        for fact in facts[:8]:  # Limit to 8 facts
            summary = fact.get("summary", "")
            if summary:
                prompt_parts.append(f"- {summary}")
        prompt_parts.append("")

    # Add context chunks
    if chunks:
        prompt_parts.extend([
            f"## Supporting Context",
            f"Relevant excerpts from project signals{' (including research)' if include_research else ''}:",
        ])
        for i, chunk in enumerate(chunks[:15], 1):  # Limit to 15 chunks
            snippet = chunk.get("snippet", "")
            source_type = chunk.get("signal_type", "unknown")
            authority = chunk.get("authority", "unknown")
            created_at = chunk.get("created_at", "")[:10]  # Date only

            prompt_parts.append(f"{i}. [{source_type}/{authority}/{created_at}] {snippet}")
        prompt_parts.append("")

    # Add section-specific instructions based on slug
    section_instructions = get_section_specific_instructions(section_slug)
    if section_instructions:
        prompt_parts.extend([
            f"## Section-Specific Instructions",
            section_instructions,
            f"",
        ])

    # Add output instructions
    prompt_parts.extend([
        f"## Enrichment Instructions",
        f"Analyze this PRD section and provide enrichment details. Focus on:",
        f"",
        f"1. **Enhanced Fields**: Improve and expand text content in the section",
        f"2. **Proposed Client Needs**: Suggest additional client questions if gaps are identified",
        f"",
        f"**IMPORTANT RULES:**",
        f"- Do NOT change the section's status or any canonical fields",
        f"- Enhanced fields should improve clarity and completeness",
        f"- Proposed client needs should only be added if there are genuine gaps in understanding",
        f"- Every proposal MUST include evidence references (chunk_id + excerpt + rationale)",
        f"- Excerpts must be verbatim from the provided chunks (max 280 chars)",
        f"- If no improvements are needed, return minimal enhancements",
        f"",
        f"## Output Format",
        f"Output ONLY valid JSON matching the required schema. No markdown, no explanation.",
    ])

    return "\n".join(prompt_parts)


def get_section_specific_instructions(section_slug: str) -> str:
    """Get section-specific enrichment instructions."""
    instructions = {
        "personas": """
        For Personas sections, focus on:
        - Making personas more detailed and realistic
        - Adding specific behaviors, motivations, and pain points
        - Including demographic and psychographic details
        - Clarifying how personas interact with the product
        """,
        "key_features": """
        For Key Features sections, focus on:
        - Making feature descriptions more comprehensive
        - Adding implementation details and user benefits
        - Clarifying feature interactions and dependencies
        - Including technical constraints or considerations
        """,
        "happy_path": """
        For Happy Path sections, focus on:
        - Making the user journey more detailed and realistic
        - Adding specific user actions and system responses
        - Including decision points and alternative flows
        - Clarifying success metrics and completion criteria
        """,
        "constraints": """
        For Constraints sections, focus on:
        - Making technical and business constraints more specific
        - Adding implementation details and workarounds
        - Including risk assessments and mitigation strategies
        - Clarifying scope boundaries and limitations
        """,
    }

    return instructions.get(section_slug, """
    For this section, focus on:
    - Improving clarity and completeness of content
    - Adding specific details and examples
    - Including relevant context and background
    - Ensuring consistency with other PRD sections
    """)


def get_prd_enrich_context(
    project_id: UUID,
    section_slugs: list[str] | None = None,
    include_research: bool = False,
    top_k_context: int = 24,
) -> dict[str, Any]:
    """
    Get all context needed for PRD enrichment.

    Args:
        project_id: Project UUID
        section_slugs: Optional specific sections to enrich
        include_research: Whether to include research context
        top_k_context: Number of context chunks to retrieve

    Returns:
        Dict with sections, facts, confirmations, and chunks
    """
    logger.info(
        f"Gathering PRD enrichment context for project {project_id}",
        extra={"project_id": str(project_id), "section_slugs": section_slugs, "include_research": include_research},
    )

    # Get PRD sections to enrich
    all_sections = list_prd_sections(project_id)
    if section_slugs:
        sections = [s for s in all_sections if s["slug"] in section_slugs]
    else:
        sections = all_sections

    logger.info(f"Selected {len(sections)} PRD sections for enrichment")

    # Get latest facts and insights for context
    facts = list_latest_extracted_facts(project_id, limit=8)
    insights = list_latest_insights(project_id, limit=15, statuses=["open", "queued", "resolved"])

    # Get confirmations for context
    confirmations = list_confirmation_items(project_id)

    # Generate queries for vector search based on sections being enriched
    queries = [
        "What are the detailed requirements and specifications for PRD sections?",
        "What are the user personas and their needs?",
        "What are the key features and functionality requirements?",
        "What is the user workflow and journey?",
        "What are the business and technical constraints?",
        "What are the success metrics and acceptance criteria?",
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
        "sections": sections,
        "canonical_prd": all_sections,
        "facts": facts,
        "insights": insights,
        "confirmations": confirmations,
        "chunks": chunks,
    }

    logger.info(
        f"Gathered PRD enrichment context: {len(sections)} sections, "
        f"{len(facts)} facts, {len(confirmations)} confirmations, {len(chunks)} chunks",
        extra={"project_id": str(project_id)},
    )

    return context
