"""State builder agent input preparation utilities."""

from typing import Any
from uuid import UUID

from app.core.embeddings import embed_texts
from app.core.logging import get_logger
from app.db.facts import list_latest_extracted_facts
from app.db.phase0 import search_signal_chunks

logger = get_logger(__name__)

# Fixed query list for deterministic retrieval
STATE_BUILDER_QUERIES = [
    "personas roles stakeholders",
    "features must have MVP",
    "happy path workflow steps",
    "constraints boundaries security AI",
    "kpis success metrics timeline",
]


def get_latest_facts_digest(project_id: UUID, limit: int = 6) -> str:
    """
    Create a compact digest of extracted facts for the state builder prompt.

    Args:
        project_id: Project UUID
        limit: Maximum number of fact extraction runs to include

    Returns:
        Compact text summary of facts
    """
    facts_rows = list_latest_extracted_facts(project_id, limit=limit)

    if not facts_rows:
        return "No extracted facts available."

    lines = ["## Extracted Facts Summary\n"]

    for row in facts_rows:
        facts_json = row.get("facts", {})
        summary = facts_json.get("summary", "")
        facts_list = facts_json.get("facts", [])

        # Add summary if present
        if summary:
            lines.append(f"Summary: {summary}\n")

        # Add fact titles grouped by type
        if facts_list:
            lines.append("Facts:\n")
            for fact in facts_list:
                fact_type = fact.get("fact_type", "unknown")
                title = fact.get("title", "")
                confidence = fact.get("confidence", "")
                lines.append(f"  - [{fact_type}] {title} (confidence: {confidence})\n")

        # Add open questions
        questions = facts_json.get("open_questions", [])
        if questions:
            lines.append("\nOpen Questions:\n")
            for q in questions[:5]:  # Cap at 5 questions
                question_text = q.get("question", "")
                lines.append(f"  ? {question_text}\n")

        # Add contradictions
        contradictions = facts_json.get("contradictions", [])
        if contradictions:
            lines.append("\nContradictions:\n")
            for c in contradictions[:5]:  # Cap at 5
                desc = c.get("description", "")
                severity = c.get("severity", "")
                lines.append(f"  ! [{severity}] {desc}\n")

        lines.append("\n")

    return "".join(lines)


def retrieve_project_chunks(
    project_id: UUID,
    queries: list[str],
    top_k: int,
    max_total: int,
) -> list[dict[str, Any]]:
    """
    Retrieve relevant chunks for a project using multiple queries.

    Args:
        project_id: Project UUID
        queries: List of query strings to search
        top_k: Number of chunks to retrieve per query
        max_total: Maximum total chunks to return after deduplication

    Returns:
        List of unique chunks with deduplication by chunk_id
    """
    seen_chunk_ids: set[str] = set()
    all_chunks: list[dict[str, Any]] = []

    for query in queries:
        # Embed the query text
        query_embeddings = embed_texts([query])
        query_embedding = query_embeddings[0]

        # Search for similar chunks
        results = search_signal_chunks(
            query_embedding=query_embedding,
            match_count=top_k,
            project_id=project_id,
        )

        # Deduplicate by chunk_id
        for chunk in results:
            chunk_id = chunk.get("chunk_id", "")
            if chunk_id and chunk_id not in seen_chunk_ids:
                seen_chunk_ids.add(chunk_id)
                all_chunks.append(chunk)

        # Early exit if we have enough chunks
        if len(all_chunks) >= max_total:
            break

    # Cap at max total
    all_chunks = all_chunks[:max_total]

    logger.info(
        f"Retrieved {len(all_chunks)} unique chunks for state building",
        extra={"project_id": str(project_id), "query_count": len(queries)},
    )

    return all_chunks


def build_state_prompt(
    facts_digest: str,
    chunks: list[dict[str, Any]],
) -> str:
    """
    Build the user prompt for state building.

    Args:
        facts_digest: Compact summary of extracted facts
        chunks: List of chunk dicts with chunk_id, content, signal_metadata, chunk_metadata

    Returns:
        Formatted prompt string for state builder LLM
    """
    lines = [
        "You are a product requirements architect building a structured PRD and Value Path.",
        "Your task is to synthesize extracted facts and signal chunks into:",
        "1. PRD sections (personas, key_features, happy_path, constraints, etc.)",
        "2. Value Path workflow steps",
        "3. Key Features list",
        "",
        "## Authority Model",
        "- Chunks with authority='client' represent direct client input (ground truth).",
        "- Chunks with authority='research' are market research context (not binding).",
        "- When synthesizing, prioritize client authority over research.",
        "",
        "## Instructions",
        "- Create at least 3 PRD sections (personas, key_features, happy_path are required).",
        "- Create at least 3 Value Path steps describing the user workflow.",
        "- Extract ALL Key Features explicitly mentioned in the transcript/facts - create a separate feature for each distinct capability mentioned.",
        "- Do NOT consolidate similar features - each should be separate (e.g., 'HubSpot integration' and 'telemetry events' are different features).",
        "- Create as many features as are mentioned - there is no upper limit.",
        "- SPECIFICALLY extract these features mentioned in the transcript:",
        "  * Typeform/Interact ingestion + conversion to project",
        "  * HubSpot integration (contact/deal + enterprise tagging)",
        "  * Data room: upload requests, checklists, due dates, reminders",
        "  * In-app document viewer",
        "  * Survey builder + skip logic + CSV import + completion tracking",
        "  * Report assembly: section templates + findings tray + snippet library + variable injection",
        "  * Stage tracker + task flags",
        "  * Kanban 'Next 90 Days' output",
        "  * Audit log + timeline feed",
        "  * Telemetry events",
        "  * Authentication modes + magic link flows",
        "  * NDA / acknowledgement gate for data room uploads",
        "  * ClickUp integration (or export)",
        "  * Outbound email sending + timeline logging",
        "  * CSV import of employees + department mapping",
        "  * SMS reminders channel",
        "  * Risks & Dependencies subsection",
        "- For each feature mentioned, create a separate feature entry with proper MVP flags and confidence levels.",
        "- Every item should reference evidence (chunk_ids) when possible.",
        "- Use status='draft' for all items (never confirmed_client).",
        "- If something is uncertain, add it to client_needs or needed arrays.",
        "- Be specific and actionable - avoid vague statements.",
        "- IMPORTANT: Do not miss any features explicitly mentioned in the transcript or facts.",
        "",
        facts_digest,
        "",
        "## Retrieved Chunks",
        "",
    ]

    for chunk in chunks:
        chunk_id = chunk.get("chunk_id", "unknown")
        content = chunk.get("content", "")
        signal_metadata = chunk.get("signal_metadata", {})
        chunk_metadata = chunk.get("chunk_metadata", {})
        authority = signal_metadata.get("authority", "client")
        section = chunk_metadata.get("section", "")

        # Build chunk header
        header_parts = [f"chunk_id={chunk_id}"]
        if authority:
            header_parts.append(f"authority={authority}")
        if section:
            header_parts.append(f"section={section}")

        lines.append(f"[{' '.join(header_parts)}]")
        lines.append(content[:900])  # Cap content per chunk
        lines.append("")

    return "\n".join(lines)

