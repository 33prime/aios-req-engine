"""Generate chat summary for signal processing results.

After patches are applied, this chain produces a human-readable markdown
summary for the workspace chat. Groups by: auto-applied, flagged, conflicts.

Uses Haiku for speed (~200ms, ~$0.001).
"""

from __future__ import annotations

import logging

from app.core.schemas_entity_patch import EntityPatch, PatchApplicationResult

logger = logging.getLogger(__name__)


async def generate_chat_summary(
    result: PatchApplicationResult,
    patches: list[EntityPatch],
    signal_name: str = "signal",
) -> str:
    """Generate a markdown chat summary of patch application results.

    For the initial implementation, this is a deterministic template-based
    generator. Can be upgraded to Haiku for more natural language later.

    Args:
        result: PatchApplicationResult from patch applicator
        patches: Original EntityPatch list (for escalated context)
        signal_name: Display name of the processed signal

    Returns:
        Markdown string for chat display
    """
    lines: list[str] = []

    lines.append(f"Processed **{signal_name}**.")

    if result.total_applied == 0 and result.total_escalated == 0 and not result.skipped:
        lines.append("\nNo changes detected from this signal.")
        return "\n".join(lines)

    lines.append("")

    # Auto-applied section
    if result.applied:
        # Group by operation
        created = [a for a in result.applied if a.get("operation") == "create"]
        merged = [a for a in result.applied if a.get("operation") == "merge"]
        updated = [a for a in result.applied if a.get("operation") == "update"]
        staled = [a for a in result.applied if a.get("operation") == "stale"]
        deleted = [a for a in result.applied if a.get("operation") == "delete"]

        if created:
            entity_types = set(a.get("entity_type", "") for a in created)
            type_summary = ", ".join(f"{sum(1 for a in created if a.get('entity_type') == t)} {t}s" for t in sorted(entity_types))
            lines.append(f"**New** ({type_summary}):")
            for a in created[:8]:
                name = a.get("name", "unnamed")
                etype = a.get("entity_type", "entity")
                lines.append(f"  - {name} ({etype})")
            if len(created) > 8:
                lines.append(f"  - ... and {len(created) - 8} more")
            lines.append("")

        if merged:
            lines.append(f"**Enriched** ({len(merged)} entities):")
            for a in merged[:5]:
                name = a.get("name", "unnamed")
                fields = a.get("fields_merged", [])
                field_summary = f" — added {', '.join(f for f in fields if f not in ('updated_at', 'evidence', 'source_signal_ids'))}" if fields else ""
                lines.append(f"  - {name}{field_summary}")
            lines.append("")

        if updated:
            lines.append(f"**Updated** ({len(updated)} entities):")
            for a in updated[:5]:
                name = a.get("name", "unnamed")
                fields = a.get("fields_updated", [])
                lines.append(f"  - {name} ({', '.join(fields[:3])})")
            lines.append("")

        if staled:
            lines.append(f"**Flagged stale** ({len(staled)} entities):")
            for a in staled[:3]:
                reason = a.get("stale_reason", "contradicted by new signal")
                lines.append(f"  - {reason}")
            lines.append("")

        if deleted:
            lines.append(f"**Removed** ({len(deleted)} entities):")
            for a in deleted[:3]:
                name = a.get("name", "unnamed")
                lines.append(f"  - {name}")
            lines.append("")

    # Escalated section (needs user input)
    if result.escalated:
        lines.append(f"**Needs your input** ({len(result.escalated)}):")
        for esc in result.escalated[:5]:
            summary = esc.get("patch_summary", "")
            reason = esc.get("reason", "")
            confidence = esc.get("confidence", "")
            lines.append(f"  - {summary}")
            if confidence == "conflict":
                lines.append(f"    *Conflict detected* — {reason}")
            else:
                lines.append(f"    *Low confidence* — {reason}")
        lines.append("")

    # Belief impact summary
    belief_impacts = []
    for patch in patches:
        for bi in patch.belief_impact:
            belief_impacts.append(bi)

    if belief_impacts:
        supports = [bi for bi in belief_impacts if bi.impact == "supports"]
        contradicts = [bi for bi in belief_impacts if bi.impact == "contradicts"]

        if supports:
            lines.append(f"*Strengthened {len(supports)} existing belief(s)*")
        if contradicts:
            lines.append(f"*Contradicted {len(contradicts)} existing belief(s)*")
        lines.append("")

    # Open question resolution
    resolved_questions = [p for p in patches if p.answers_question]
    if resolved_questions:
        lines.append(f"**Answered {len(resolved_questions)} open question(s)**:")
        for p in resolved_questions[:3]:
            lines.append(f"  - {p.answers_question}")
        lines.append("")

    return "\n".join(lines)
