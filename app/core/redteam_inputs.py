"""Red-team agent input preparation utilities."""

from typing import Any


def compact_facts_for_prompt(facts_rows: list[dict[str, Any]], max_chars: int = 2000) -> str:
    """
    Create a compact digest of extracted facts for the red-team prompt.

    Args:
        facts_rows: List of extracted_facts rows from database
        max_chars: Maximum characters for the digest

    Returns:
        Compact text summary of facts
    """
    if not facts_rows:
        return "No extracted facts available."

    lines = ["## Extracted Facts Summary\n"]
    current_len = len(lines[0])

    for row in facts_rows:
        facts_json = row.get("facts", {})
        summary = facts_json.get("summary", "")
        facts_list = facts_json.get("facts", [])

        # Add summary if present
        if summary:
            if len(summary) > 200:
                line = f"Summary: {summary[:200]}...\n"
            else:
                line = f"Summary: {summary}\n"
            if current_len + len(line) > max_chars:
                break
            lines.append(line)
            current_len += len(line)

        # Add fact titles
        for fact in facts_list:
            fact_type = fact.get("fact_type", "unknown")
            title = fact.get("title", "")
            confidence = fact.get("confidence", "")

            line = f"- [{fact_type}] {title} (confidence: {confidence})\n"
            if current_len + len(line) > max_chars:
                lines.append("... (truncated)")
                return "".join(lines)
            lines.append(line)
            current_len += len(line)

        # Add open questions
        questions = facts_json.get("open_questions", [])
        if questions:
            lines.append("\nOpen Questions:\n")
            for q in questions[:3]:  # Cap at 3 questions
                question_text = q.get("question", "")
                line = f"  ? {question_text}\n"
                if current_len + len(line) > max_chars:
                    break
                lines.append(line)
                current_len += len(line)

        # Add contradictions
        contradictions = facts_json.get("contradictions", [])
        if contradictions:
            lines.append("\nContradictions:\n")
            for c in contradictions[:3]:  # Cap at 3
                desc = c.get("description", "")
                line = f"  ! {desc}\n"
                if current_len + len(line) > max_chars:
                    break
                lines.append(line)
                current_len += len(line)

    return "".join(lines)


def build_redteam_prompt(
    facts_digest: str,
    chunks: list[dict[str, Any]],
) -> str:
    """
    Build the user prompt for red-team analysis.

    Args:
        facts_digest: Compact summary of extracted facts
        chunks: List of chunk dicts with id, content, metadata

    Returns:
        Formatted prompt string for red-team LLM
    """
    lines = [
        "You are a critical red-team analyst reviewing requirements for a software project.",
        "Your task is to identify logical flaws, UX issues, security gaps, data problems,",
        "reporting holes, scope risks, and operational concerns.",
        "",
        "## Authority Model",
        "- Chunks with authority='client' represent direct client input (ground truth).",
        "- Chunks with authority='research' are market research context (not binding).",
        "- When you find contradictions, client authority takes precedence.",
        "",
        "## Instructions",
        "- Focus on actionable insights that would improve the requirements.",
        "- Every insight MUST include at least one evidence reference.",
        "- Be specific about what is wrong and why it matters.",
        "- Suggest whether the issue can be fixed internally or needs client confirmation.",
        "",
        facts_digest,
        "",
        "## Retrieved Chunks",
        "",
    ]

    for chunk in chunks:
        chunk_id = chunk.get("id", "unknown")
        content = chunk.get("content", "")
        metadata = chunk.get("metadata", {})
        authority = metadata.get("authority", "client")
        section = metadata.get("section", "")

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
