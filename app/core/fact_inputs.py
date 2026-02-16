"""Chunk selection and prompt building for fact extraction."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.core.state_snapshot import get_state_snapshot

logger = get_logger(__name__)


def truncate_at_sentence_boundary(content: str, max_chars: int) -> str:
    """
    Truncate content at a sentence boundary near max_chars.

    Preserves semantic meaning by avoiding mid-sentence cuts.

    Args:
        content: Text to truncate
        max_chars: Maximum character limit

    Returns:
        Truncated text at sentence boundary
    """
    if len(content) <= max_chars:
        return content

    truncated = content[:max_chars]

    # Look for sentence-ending punctuation followed by space or newline
    for sep in ['. ', '.\n', '!\n', '! ', '?\n', '? ']:
        last_sep = truncated.rfind(sep)
        if last_sep > max_chars * 0.6:  # At least 60% of content preserved
            return truncated[:last_sep + 1].strip()

    # Fallback: Look for any sentence-ending punctuation
    for punct in '.!?':
        last_punct = truncated.rfind(punct)
        if last_punct > max_chars * 0.7:
            return truncated[:last_punct + 1].strip()

    # Last resort: Find last space to avoid cutting words
    last_space = truncated.rfind(' ')
    if last_space > max_chars * 0.8:
        return truncated[:last_space].strip()

    # If all else fails, return the truncated content
    return truncated.strip()


def select_chunks_for_facts(
    chunks: list[dict[str, Any]],
    max_chunks: int,
    max_chars_per_chunk: int,
) -> list[dict[str, Any]]:
    """
    Select and truncate chunks for fact extraction.

    Deterministic selection:
    - Takes chunks in ascending chunk_index order
    - Truncates each chunk's content to max_chars_per_chunk
    - Stops at max_chunks

    Args:
        chunks: List of chunk dicts (must include 'content' and 'chunk_index')
        max_chunks: Maximum number of chunks to return
        max_chars_per_chunk: Maximum characters per chunk content

    Returns:
        List of chunk dicts with truncated content
    """
    # Sort by chunk_index to ensure deterministic order
    sorted_chunks = sorted(chunks, key=lambda c: c.get("chunk_index", 0))

    selected: list[dict[str, Any]] = []
    for chunk in sorted_chunks[:max_chunks]:
        # Shallow copy to avoid mutating original
        truncated = dict(chunk)
        content = truncated.get("content", "")
        if len(content) > max_chars_per_chunk:
            # Use sentence-boundary aware truncation instead of hard cut
            truncated["content"] = truncate_at_sentence_boundary(content, max_chars_per_chunk)
        selected.append(truncated)

    return selected


def build_facts_prompt(
    signal: dict[str, Any],
    selected_chunks: list[dict[str, Any]],
    project_context: dict[str, Any] | None = None,
) -> str:
    """
    Build the user prompt for fact extraction.

    Args:
        signal: Signal dict with project_id, signal_type, source, id
        selected_chunks: List of selected chunk dicts
        project_context: Optional project context with name, domain, existing entities, state_snapshot

    Returns:
        Formatted prompt string for the LLM
    """
    lines: list[str] = []

    # State snapshot - comprehensive project context (~500 tokens)
    if project_context and project_context.get("state_snapshot"):
        lines.append("=== EXISTING PROJECT STATE ===")
        lines.append(project_context["state_snapshot"])
        lines.append("")
        lines.append("=== EXTRACTION GUIDANCE ===")
        lines.append("When you find information in the signal:")
        lines.append("1. If it describes a NEW capability not listed above → create FEATURE fact")
        lines.append("2. If it adds NEW DETAILS to an existing feature → create FEATURE fact (will be merged)")
        lines.append("3. Extract ALL workflow steps. Group by workflow_name. Use CURRENT_PROCESS/FUTURE_PROCESS fact types.")
        lines.append("4. If existing workflows shown above, use SAME workflow_name to extend them.")
        lines.append("5. Extract ALL business drivers (pains, goals, KPIs)")
        lines.append("6. Extract ALL personas/user types mentioned")
        lines.append("7. Extract ALL data entities (domain objects: records, documents, forms)")
        lines.append("")
        lines.append("DO NOT skip extraction just because something similar exists.")
        lines.append("The consolidation step handles merging - extract EVERYTHING mentioned.")
        lines.append("")

    # Fallback project context if no state snapshot
    elif project_context:
        lines.append("=== EXISTING PROJECT STATE ===")
        if project_context.get("name"):
            lines.append(f"Project: {project_context['name']}")
        if project_context.get("domain"):
            lines.append(f"Domain: {project_context['domain']}")
        if project_context.get("description"):
            lines.append(f"Description: {project_context['description'][:200]}")
        lines.append("")

        # Show existing features with details
        existing_features = project_context.get("existing_features", [])
        if existing_features:
            lines.append(f"EXISTING FEATURES ({len(existing_features)} total):")
            for f in existing_features[:15]:
                name = f.get("name", f.get("title", "?"))
                desc = f.get("description", "")[:80] if f.get("description") else ""
                lines.append(f"  - {name}" + (f": {desc}..." if desc else ""))
            lines.append("")

        # Show existing personas
        existing_personas = project_context.get("existing_personas", [])
        if existing_personas:
            lines.append(f"EXISTING PERSONAS ({len(existing_personas)} total):")
            for p in existing_personas[:10]:
                name = p.get("name", p.get("slug", "?"))
                role = p.get("role", "")
                lines.append(f"  - {name}" + (f" ({role})" if role else ""))
            lines.append("")

        lines.append("=== EXTRACTION GUIDANCE ===")
        lines.append("When you find information in the signal:")
        lines.append("1. If it describes a NEW feature not listed above → create FEATURE fact")
        lines.append("2. If it adds NEW DETAILS to an existing feature → create FEATURE fact with same name")
        lines.append("3. If it describes a NEW persona/user type → create PERSONA fact")
        lines.append("4. If it adds details to existing persona → create PERSONA fact with same name")
        lines.append("5. Extract ALL workflow steps as VP_STEP facts")
        lines.append("6. Extract ALL business drivers (pains, goals, KPIs)")
        lines.append("")
        lines.append("DO NOT skip extraction just because something similar exists.")
        lines.append("The consolidation step will handle merging - your job is to extract EVERYTHING.")
        lines.append("")

    # Signal header
    lines.append("=== SIGNAL CONTEXT ===")
    lines.append(f"project_id: {signal.get('project_id', 'unknown')}")
    lines.append(f"signal_type: {signal.get('signal_type', 'unknown')}")
    lines.append(f"source: {signal.get('source', 'unknown')}")
    lines.append(f"signal_id: {signal.get('id', 'unknown')}")
    lines.append("")

    # Instructions
    lines.append("=== INSTRUCTIONS ===")
    lines.append("Extract structured facts from the chunks below.")
    lines.append("Output ONLY valid JSON matching the ExtractFactsOutput schema.")
    lines.append("")
    lines.append("Rules:")
    lines.append("- evidence.chunk_id MUST be one of the chunk_ids provided below")
    lines.append(
        "- evidence.excerpt MUST be copied verbatim from the chunk content (max 1000 chars)"
    )
    lines.append("- Every fact and contradiction MUST have at least one evidence reference")
    lines.append("- Be precise and avoid speculation")
    lines.append("")

    # Chunk IDs for reference
    chunk_ids = [str(c.get("id", "")) for c in selected_chunks]
    lines.append("Available chunk_ids: " + ", ".join(chunk_ids))
    lines.append("")

    # Chunks
    lines.append("=== CHUNKS ===")
    for chunk in selected_chunks:
        chunk_id = chunk.get("id", "")
        idx = chunk.get("chunk_index", 0)
        start = chunk.get("start_char", 0)
        end = chunk.get("end_char", 0)
        content = chunk.get("content", "")

        lines.append(f"[chunk_id={chunk_id} idx={idx} start={start} end={end}]")
        lines.append(content)
        lines.append("")

    return "\n".join(lines)


def get_project_context_for_extraction(project_id: UUID) -> dict[str, Any]:
    """
    Fetch project context for use in extraction prompts.

    Uses the state snapshot for comprehensive, cached context.
    Falls back to manual entity fetching if snapshot unavailable.

    Args:
        project_id: Project UUID

    Returns:
        Dict with state_snapshot (preferred) or project name, domain, existing_features, existing_personas
    """
    from app.db.supabase_client import get_supabase

    context: dict[str, Any] = {}

    # Try to get state snapshot first (preferred - comprehensive ~500 token context)
    try:
        state_snapshot = get_state_snapshot(project_id)
        if state_snapshot:
            context["state_snapshot"] = state_snapshot
            logger.debug(f"Using state snapshot for extraction context ({len(state_snapshot)} chars)")
            return context
    except Exception as e:
        logger.warning(f"Failed to get state snapshot, falling back to manual context: {e}")

    # Fallback: Manual context building
    supabase = get_supabase()

    try:
        # Get project info
        proj_resp = (
            supabase.table("projects")
            .select("name, description, metadata")
            .eq("id", str(project_id))
            .single()
            .execute()
        )
        if proj_resp.data:
            context["name"] = proj_resp.data.get("name")
            context["description"] = proj_resp.data.get("description")
            meta = proj_resp.data.get("metadata") or {}
            context["domain"] = meta.get("domain") or meta.get("industry")

    except Exception as e:
        logger.warning(f"Failed to fetch project info: {e}")

    try:
        # Get existing features (limit to 10 for context)
        feat_resp = (
            supabase.table("features")
            .select("id, name, description")
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
            .limit(15)
            .execute()
        )
        context["existing_features"] = feat_resp.data or []

    except Exception as e:
        logger.warning(f"Failed to fetch features: {e}")
        context["existing_features"] = []

    try:
        # Get existing personas (limit to 5 for context)
        persona_resp = (
            supabase.table("personas")
            .select("id, slug, name, role")
            .eq("project_id", str(project_id))
            .limit(10)
            .execute()
        )
        context["existing_personas"] = persona_resp.data or []

    except Exception as e:
        logger.warning(f"Failed to fetch personas: {e}")
        context["existing_personas"] = []

    return context
