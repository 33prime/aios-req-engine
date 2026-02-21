"""Format retrieval results for LLM context injection.

Three styles:
  - chat: Numbered evidence items with source metadata. For chat responses.
  - generation: Grouped by entity type, full descriptions. For solution flow, unlocks.
  - analysis: Grouped by supporting vs contradicting. For briefing, gap intel.

Always truncates from lowest-ranked results first. Preserves chunk_ids for evidence refs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.retrieval import RetrievalResult


def format_retrieval_for_context(
    result: RetrievalResult,
    max_tokens: int = 3000,
    style: str = "chat",
) -> str:
    """Format retrieval results for LLM context injection.

    Args:
        result: RetrievalResult from retrieve()
        max_tokens: Approximate max output size in tokens (~4 chars/token)
        style: "chat" | "generation" | "analysis"

    Returns:
        Formatted string ready for injection into system/user prompts
    """
    max_chars = max_tokens * 4

    if style == "chat":
        return _format_chat(result, max_chars)
    elif style == "generation":
        return _format_generation(result, max_chars)
    elif style == "analysis":
        return _format_analysis(result, max_chars)
    else:
        return _format_chat(result, max_chars)


def _format_chat(result: RetrievalResult, max_chars: int) -> str:
    """Numbered evidence items with source metadata and speaker info."""
    sections: list[str] = []
    chars_used = 0

    if result.chunks:
        evidence_lines: list[str] = []
        for i, chunk in enumerate(result.chunks):
            content = (chunk.get("content") or "")[:500]
            meta = chunk.get("metadata", {}) or {}
            meta_tags = meta.get("meta_tags", {})

            # Build source line
            source_parts = []
            if chunk.get("section_path"):
                source_parts.append(chunk["section_path"])
            if chunk.get("page_number"):
                source_parts.append(f"p.{chunk['page_number']}")
            speakers = meta_tags.get("speaker_roles", {})
            if speakers:
                source_parts.append(f"speakers: {', '.join(speakers.keys())}")

            source = f" [{', '.join(source_parts)}]" if source_parts else ""
            line = f"{i+1}. {content}{source}"

            if chars_used + len(line) > max_chars:
                break
            evidence_lines.append(line)
            chars_used += len(line)

        if evidence_lines:
            sections.append("## Relevant Evidence\n" + "\n".join(evidence_lines))

    if result.entities and chars_used < max_chars:
        entity_lines: list[str] = []
        for entity in result.entities:
            name = entity.get("entity_name", "")
            etype = entity.get("entity_type", "")
            sim = entity.get("similarity")
            sim_str = f" ({sim:.0%})" if sim else ""
            line = f"- {etype}: {name}{sim_str}"
            if chars_used + len(line) > max_chars:
                break
            entity_lines.append(line)
            chars_used += len(line)

        if entity_lines:
            sections.append("## Related Entities\n" + "\n".join(entity_lines))

    if result.beliefs and chars_used < max_chars:
        belief_lines: list[str] = []
        for belief in result.beliefs:
            summary = belief.get("summary", "")
            confidence = belief.get("confidence", 0)
            line = f"- [{confidence:.0%}] {summary}"
            if chars_used + len(line) > max_chars:
                break
            belief_lines.append(line)
            chars_used += len(line)

        if belief_lines:
            sections.append("## Memory Beliefs\n" + "\n".join(belief_lines))

    return "\n\n".join(sections) if sections else ""


def _format_generation(result: RetrievalResult, max_chars: int) -> str:
    """Grouped by entity type with full descriptions. For solution flow, unlocks."""
    sections: list[str] = []
    chars_used = 0

    # Group entities by type
    if result.entities:
        by_type: dict[str, list[dict]] = {}
        for entity in result.entities:
            etype = entity.get("entity_type", "other")
            by_type.setdefault(etype, []).append(entity)

        for etype, entities in by_type.items():
            group_lines = [f"### {etype.replace('_', ' ').title()}s"]
            for entity in entities:
                name = entity.get("entity_name", "")
                line = f"- {name}"
                if chars_used + len(line) > max_chars:
                    break
                group_lines.append(line)
                chars_used += len(line)

            if len(group_lines) > 1:
                sections.append("\n".join(group_lines))

    # Add supporting evidence
    if result.chunks and chars_used < max_chars:
        evidence_lines = ["### Supporting Evidence"]
        for chunk in result.chunks:
            content = (chunk.get("content") or "")[:400]
            if chars_used + len(content) + 10 > max_chars:
                break
            evidence_lines.append(f"- {content}")
            chars_used += len(content) + 10

        if len(evidence_lines) > 1:
            sections.append("\n".join(evidence_lines))

    # Add beliefs
    if result.beliefs and chars_used < max_chars:
        belief_lines = ["### Known Beliefs"]
        for belief in result.beliefs:
            summary = belief.get("summary", "")
            confidence = belief.get("confidence", 0)
            line = f"- [{confidence:.0%}] {summary}"
            if chars_used + len(line) > max_chars:
                break
            belief_lines.append(line)
            chars_used += len(line)

        if len(belief_lines) > 1:
            sections.append("\n".join(belief_lines))

    return "\n\n".join(sections) if sections else ""


def _format_analysis(result: RetrievalResult, max_chars: int) -> str:
    """Grouped by supporting vs contradicting. For briefing, gap intel."""
    sections: list[str] = []
    chars_used = 0

    # Split beliefs by support/contradict
    supporting: list[dict] = []
    contradicting: list[dict] = []
    neutral: list[dict] = []

    for belief in result.beliefs:
        rel = belief.get("relationship", "neutral")
        if rel == "supports":
            supporting.append(belief)
        elif rel == "contradicts":
            contradicting.append(belief)
        else:
            neutral.append(belief)

    if supporting:
        lines = ["### Supporting Evidence"]
        for b in supporting:
            line = f"- [{b.get('confidence', 0):.0%}] {b.get('summary', '')}"
            if chars_used + len(line) > max_chars:
                break
            lines.append(line)
            chars_used += len(line)
        sections.append("\n".join(lines))

    if contradicting:
        lines = ["### Contradicting Evidence"]
        for b in contradicting:
            line = f"- [{b.get('confidence', 0):.0%}] {b.get('summary', '')}"
            if chars_used + len(line) > max_chars:
                break
            lines.append(line)
            chars_used += len(line)
        sections.append("\n".join(lines))

    if neutral:
        lines = ["### Related Beliefs"]
        for b in neutral:
            line = f"- [{b.get('confidence', 0):.0%}] {b.get('summary', '')}"
            if chars_used + len(line) > max_chars:
                break
            lines.append(line)
            chars_used += len(line)
        sections.append("\n".join(lines))

    # Add evidence chunks
    if result.chunks and chars_used < max_chars:
        evidence_lines = ["### Signal Evidence"]
        for chunk in result.chunks:
            content = (chunk.get("content") or "")[:400]
            meta_tags = (chunk.get("metadata") or {}).get("meta_tags", {})
            decision = " [DECISION]" if meta_tags.get("decision_made") else ""
            confidence = meta_tags.get("confidence_signals", [])
            conf_str = f" ({confidence[0]})" if confidence else ""

            line = f"- {content}{decision}{conf_str}"
            if chars_used + len(line) > max_chars:
                break
            evidence_lines.append(line)
            chars_used += len(line)

        if len(evidence_lines) > 1:
            sections.append("\n".join(evidence_lines))

    return "\n\n".join(sections) if sections else ""
