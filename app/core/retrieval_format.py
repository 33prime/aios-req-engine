"""Format retrieval results for LLM context injection.

Four styles:
  - chat: Numbered evidence items with source metadata. For chat responses.
  - generation: Grouped by entity type, full descriptions. For solution flow, unlocks.
  - analysis: Grouped by supporting vs contradicting. For briefing, gap intel.
  - graph: Full Tier 2.5 metadata preserved — strength, weight, hop paths,
    certainty, belief confidence, contradiction flags, freshness. For any caller
    that needs the complete graph intelligence picture.

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
        style: "chat" | "generation" | "analysis" | "graph"

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
    elif style == "graph":
        return _format_graph(result, max_chars)
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
            line = f"{i + 1}. {content}{source}"

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

            # Prefer graph signals over raw similarity
            strength = entity.get("strength")
            certainty = entity.get("certainty")
            has_contradictions = entity.get("has_contradictions", False)
            hop = entity.get("hop")
            path = entity.get("path", [])

            if strength or certainty:
                # Graph-expanded entity — show rich metadata
                tags = []
                if strength:
                    tags.append(strength)
                if certainty:
                    tags.append(certainty)
                if has_contradictions:
                    tags.append("contradicted")
                tag_str = ", ".join(tags)
                line = f"- {etype}: {name} ({tag_str})"

                # Show multi-hop path
                if hop and hop >= 2 and path:
                    via = path[0]
                    via_name = via.get("entity_name", "?")
                    via_type = via.get("entity_type", "?")
                    line += f" — via {via_type}: {via_name}"
            else:
                # Direct vector match — show similarity
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


def _format_graph(result: RetrievalResult, max_chars: int) -> str:
    """Graph-aware format preserving all Tier 2.5 metadata.

    Unlike chat/generation/analysis styles, this preserves:
    - Relationship strength + weight
    - Hop distance + intermediary paths
    - Certainty (confirmed/review/inferred/stale)
    - Belief confidence + contradiction flags
    - Temporal freshness
    """
    sections: list[str] = []
    chars_used = 0

    # Related entities with full graph metadata
    if result.entities:
        entity_lines: list[str] = []
        for entity in result.entities:
            etype = entity.get("entity_type", "")
            ename = entity.get("entity_name", "")
            if not ename:
                continue

            # Core graph fields
            strength = entity.get("strength", "")
            certainty = entity.get("certainty", "")
            relationship = entity.get("relationship", "co_occurrence")
            weight = entity.get("weight", 0)
            hop = entity.get("hop", 1)
            freshness = entity.get("freshness", "")

            # Build tag string: [strong, confirmed, belief=0.91]
            tags = []
            if strength:
                tags.append(strength)
            if certainty:
                tags.append(certainty)
            belief_conf = entity.get("belief_confidence")
            if belief_conf is not None:
                tags.append(f"belief={belief_conf}")
            if entity.get("has_contradictions"):
                tags.append("contradictions detected")
            tag_str = ", ".join(tags) if tags else ""

            # Build detail string: (co_occurrence, w=7, fresh=2026-02-25)
            details = [relationship.replace("_", " ")]
            if weight:
                details.append(f"w={weight}")
            if freshness:
                details.append(f"fresh={freshness}")

            # Multi-hop path
            path = entity.get("path", [])
            if hop >= 2 and path:
                via = path[0]
                via_type = via.get("entity_type", "")
                via_name = via.get("entity_name", "")
                details.append(f"via {via_type}:{via_name}")

            detail_str = ", ".join(details)
            line = f"- {etype}: {ename} [{tag_str}] ({detail_str})"

            if chars_used + len(line) > max_chars:
                break
            entity_lines.append(line)
            chars_used += len(line)

        if entity_lines:
            sections.append("## Related Entities\n" + "\n".join(entity_lines))

    # Evidence chunks with decision/confidence metadata
    if result.chunks and chars_used < max_chars:
        evidence_lines: list[str] = []
        for i, chunk in enumerate(result.chunks, 1):
            content = (chunk.get("content") or "")[:500]
            meta = chunk.get("metadata", {}) or {}
            meta_tags = meta.get("meta_tags", {})

            # Build source annotation
            source_parts = []
            if chunk.get("section_path"):
                source_parts.append(chunk["section_path"])
            if chunk.get("page_number"):
                source_parts.append(f"p.{chunk['page_number']}")
            speakers = meta_tags.get("speaker_roles", {})
            if speakers:
                source_parts.append(f"speakers: {', '.join(speakers.keys())}")

            source = f" [{', '.join(source_parts)}]" if source_parts else ""

            # Decision and confidence signals
            decision = ""
            if meta_tags.get("decision_made"):
                decision = " [DECISION]"
            confidence_signals = meta_tags.get("confidence_signals", [])
            conf_str = f" (confidence: {confidence_signals[0]})" if confidence_signals else ""

            line = f'{i}. "{content}"{source}{decision}{conf_str}'
            if chars_used + len(line) > max_chars:
                break
            evidence_lines.append(line)
            chars_used += len(line)

        if evidence_lines:
            sections.append("## Evidence\n" + "\n".join(evidence_lines))

    # Beliefs with contradiction flags
    if result.beliefs and chars_used < max_chars:
        belief_lines: list[str] = []
        for belief in result.beliefs:
            summary = belief.get("summary", "")
            confidence = belief.get("confidence", 0)
            relationship = belief.get("relationship", "")

            # Contradiction detection
            contra = ""
            if relationship == "contradicts":
                contra = " (contradictions detected)"
            elif relationship == "supports":
                contra = f" ({relationship})"

            line = f"- [{confidence:.0%}] {summary}{contra}"
            if chars_used + len(line) > max_chars:
                break
            belief_lines.append(line)
            chars_used += len(line)

        if belief_lines:
            sections.append("## Beliefs\n" + "\n".join(belief_lines))

    return "\n\n".join(sections) if sections else ""
