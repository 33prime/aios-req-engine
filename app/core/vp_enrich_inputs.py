"""Input preparation for VP step enrichment."""

from typing import Any
from uuid import UUID

from app.core.embeddings import embed_texts
from app.core.logging import get_logger
from app.core.state_snapshot import get_state_snapshot
from app.db.confirmations import list_confirmation_items
from app.db.facts import list_latest_extracted_facts
from app.db.phase0 import search_signal_chunks
from app.db.vp import list_vp_steps

logger = get_logger(__name__)


def select_chunks_for_vp_enrich(
    chunks: list[dict[str, Any]], max_chunks: int, max_chars_per_chunk: int
) -> list[dict[str, Any]]:
    """
    Select and truncate chunks for VP enrichment context.

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
        if "content" in chunk and len(chunk["content"]) > max_chars_per_chunk:
            chunk["content"] = chunk["content"][:max_chars_per_chunk] + "..."
        # Also add snippet field for compatibility
        chunk["snippet"] = chunk.get("content", "")

    return selected


def retrieve_supporting_chunks(
    project_id: UUID,
    queries: list[str],
    top_k_per_query: int,
    max_total: int,
    include_research: bool = False,
) -> list[dict[str, Any]]:
    """
    Retrieve supporting chunks for VP enrichment context.

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
        f"Retrieved {len(unique_chunks)} unique chunks for VP enrichment (from {len(all_chunks)} total)",
        extra={"project_id": str(project_id), "query_count": len(queries)},
    )

    # Debug: Log chunk metadata structure and content
    if unique_chunks:
        sample_chunk = unique_chunks[0]
        logger.info(
            f"Sample chunk metadata: signal_metadata keys: {list(sample_chunk.get('signal_metadata', {}).keys())}",
            extra={"project_id": str(project_id)},
        )
        logger.info(
            f"Sample chunk signal_metadata: {sample_chunk.get('signal_metadata')}",
            extra={"project_id": str(project_id)},
        )
        logger.info(
            f"Sample chunk content preview: {sample_chunk.get('content', '')[:100]}...",
            extra={"project_id": str(project_id)},
        )
    else:
        logger.warning(
            f"No chunks retrieved for VP enrichment - checking why",
            extra={"project_id": str(project_id), "include_research": include_research},
        )

    return unique_chunks


def build_vp_enrich_prompt(
    step: dict[str, Any],
    canonical_vp: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    confirmations: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    include_research: bool,
    state_snapshot: str | None = None,
) -> str:
    """
    Build the prompt for VP step enrichment.

    Args:
        step: VP step dict to enrich
        canonical_vp: All VP steps for context
        facts: Latest extracted facts
        confirmations: Open/resolved confirmations for context
        chunks: Supporting context chunks
        include_research: Whether research was included
        state_snapshot: Optional pre-built state snapshot for project context

    Returns:
        Complete prompt for the LLM
    """
    step_index = step.get("step_index", "?")
    step_label = step.get("label", "Unknown Step")
    step_description = step.get("description", "No description available")
    step_ui_overview = step.get("ui_overview", "")
    step_value_created = step.get("value_created", "")
    step_kpi_impact = step.get("kpi_impact", "")

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
        f"# Value Path Step Enrichment Task",
        f"",
        f"**Step to enrich:** Step {step_index} - {step_label}",
        f"**Current Description:** {step_description}",
        f"**UI Overview:** {step_ui_overview}",
        f"**Value Created:** {step_value_created}",
        f"**KPI Impact:** {step_kpi_impact}",
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

    # Add context from other VP steps
    other_steps = [s for s in canonical_vp if s["id"] != step["id"]]
    if other_steps:
        prompt_parts.extend([
            f"## Related Value Path Steps",
            f"Context from other steps in this value path:",
        ])
        for other in other_steps[:3]:  # Limit to 3 related steps
            other_desc = other.get("description", "")
            if other_desc:
                truncated = other_desc[:150] + "..." if len(other_desc) > 150 else other_desc
                prompt_parts.append(f"- **Step {other.get('step_index', '?')}: {other.get('label', 'Unknown')}**: {truncated}")
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
            snippet = chunk.get("content", "")
            chunk_id = chunk.get("chunk_id", "unknown")

            # Extract metadata from signal_metadata
            signal_metadata = chunk.get("signal_metadata", {})
            source_type = signal_metadata.get("signal_type", "unknown")
            authority = signal_metadata.get("authority", "unknown")
            created_at = signal_metadata.get("created_at", "")[:10]  # Date only

            prompt_parts.append(f"{i}. [ID:{chunk_id}] [{source_type}/{authority}/{created_at}] {snippet}")
        prompt_parts.append("")

    # Add step-specific instructions based on typical VP step types
    step_instructions = get_step_specific_instructions(step_label, step_description)
    if step_instructions:
        prompt_parts.extend([
            f"## Step-Specific Instructions",
            step_instructions,
            f"",
        ])

    # Add output instructions
    prompt_parts.extend([
        f"## Enrichment Instructions",
        f"Analyze this Value Path step and provide enrichment details. Focus on:",
        f"",
        f"1. **Enhanced Fields**: Improve description, UI overview, value created, KPI impact, and experiments",
        f"2. **Proposed Needs**: Suggest additional needed items if gaps are identified",
        f"",
        f"**IMPORTANT RULES:**",
        f"- Do NOT change the step's status or any canonical fields",
        f"- Enhanced fields should improve clarity and add implementation details",
        f"- Proposed needs should only be added if there are genuine gaps in understanding",
        f"- Every proposal MUST include evidence references (chunk_id + excerpt + rationale)",
        f"- chunk_id MUST be copied exactly from the [ID:uuid] prefix in Supporting Context above",
        f"- DO NOT fabricate or make up chunk_ids - only use the exact UUIDs provided",
        f"- If no chunks support a section, use an empty evidence array []",
        f"- Excerpts must be verbatim from the provided chunks (max 280 chars)",
        f"- If no improvements are needed, return minimal enhancements",
        f"",
        f"## Output Format",
        f"Output ONLY valid JSON matching the required schema. No markdown, no explanation.",
    ])

    return "\n".join(prompt_parts)


def get_step_specific_instructions(step_label: str, step_description: str) -> str:
    """Get step-specific enrichment instructions based on step content."""
    label_lower = step_label.lower()
    desc_lower = step_description.lower()

    # Try to infer step type from label and description
    if any(keyword in label_lower or keyword in desc_lower for keyword in ["onboard", "setup", "register", "sign up"]):
        return """
        For onboarding/setup steps, focus on:
        - Making the registration process clearer and more user-friendly
        - Adding details about data collection and validation
        - Including user verification and account setup flows
        - Clarifying what information is required and why
        """
    elif any(keyword in label_lower or keyword in desc_lower for keyword in ["dashboard", "overview", "home"]):
        return """
        For dashboard/overview steps, focus on:
        - Making the information architecture clearer
        - Adding details about key metrics and KPIs displayed
        - Including user customization options
        - Clarifying how users navigate to different features
        """
    elif any(keyword in label_lower or keyword in desc_lower for keyword in ["configure", "setup", "customize"]):
        return """
        For configuration/customization steps, focus on:
        - Making setup workflows more detailed
        - Adding information about configuration options
        - Including validation and error handling
        - Clarifying business rules and constraints
        """
    elif any(keyword in label_lower or keyword in desc_lower for keyword in ["report", "export", "download"]):
        return """
        For reporting/export steps, focus on:
        - Making data formats and options clearer
        - Adding details about report generation and delivery
        - Including scheduling and automation features
        - Clarifying data privacy and security considerations
        """
    else:
        return """
        For this step, focus on:
        - Improving clarity of user actions and system responses
        - Adding implementation details and edge cases
        - Including success metrics and validation criteria
        - Ensuring consistency with other value path steps
        """


def get_vp_enrich_context(
    project_id: UUID,
    step_ids: list[UUID] | None = None,
    include_research: bool = False,
    top_k_context: int = 24,
) -> dict[str, Any]:
    """
    Get all context needed for VP enrichment.

    Args:
        project_id: Project UUID
        step_ids: Optional specific steps to enrich
        include_research: Whether to include research context
        top_k_context: Number of context chunks to retrieve

    Returns:
        Dict with steps, facts, confirmations, chunks, and state_snapshot
    """
    logger.info(
        f"Gathering VP enrichment context for project {project_id}",
        extra={"project_id": str(project_id)},
    )

    # Get state snapshot for comprehensive project context (~500-750 tokens)
    state_snapshot = get_state_snapshot(project_id)
    logger.info(f"Got state snapshot ({len(state_snapshot)} chars)")

    # Get VP steps to enrich
    all_steps = list_vp_steps(project_id)
    if step_ids:
        steps = [s for s in all_steps if s["id"] in step_ids]
    else:
        steps = all_steps

    logger.info(f"Selected {len(steps)} VP steps for enrichment")

    # Get latest facts for context (insights system removed)
    facts = list_latest_extracted_facts(project_id, limit=8)
    insights: list = []  # Insights system removed

    # Get confirmations for context
    confirmations = list_confirmation_items(project_id)

    # Generate queries for vector search based on VP workflow
    queries = [
        "What are the detailed user workflows and value paths?",
        "What are the step-by-step user journeys?",
        "What are the user interface and interaction details?",
        "What value is created at each step of the workflow?",
        "What KPIs and metrics are tracked for user flows?",
        "What are the success criteria for each workflow step?",
        "What experiments and optimizations are needed?",
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
        "steps": steps,
        "canonical_vp": all_steps,
        "facts": facts,
        "insights": insights,
        "confirmations": confirmations,
        "chunks": chunks,
        "state_snapshot": state_snapshot,
        "include_research": include_research,
    }

    logger.info(
        f"Gathered VP enrichment context: {len(steps)} steps, "
        f"{len(facts)} facts, {len(confirmations)} confirmations, {len(chunks)} chunks, state_snapshot included",
        extra={"project_id": str(project_id)},
    )

    return context
