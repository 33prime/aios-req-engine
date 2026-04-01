"""Shared context loading for stakeholder enrichment chains.

Loads stakeholder data, signals, and evidence ONCE
and shares across all chain invocations.
"""

from dataclasses import dataclass, field
from uuid import UUID

from app.core.logging import get_logger
from app.db.stakeholders import get_stakeholder
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


@dataclass
class StakeholderContext:
    """Pre-loaded stakeholder data shared across enrichment chains."""

    stakeholder_id: UUID
    project_id: UUID
    stakeholder: dict
    evidence_text: str = ""
    other_stakeholders: list[dict] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.stakeholder.get("name", "Unknown")

    @property
    def role(self) -> str:
        return self.stakeholder.get("role") or "Unknown"

    @property
    def stakeholder_type(self) -> str:
        return self.stakeholder.get("stakeholder_type") or "end_user"

    @property
    def is_key_person(self) -> bool:
        """Champions, sponsors, and blockers get full enrichment."""
        return self.stakeholder_type in (
            "champion", "sponsor", "blocker",
        )


def load_stakeholder_context(
    stakeholder_id: UUID,
    project_id: UUID,
) -> StakeholderContext:
    """Load stakeholder + context for enrichment chains."""
    stakeholder = get_stakeholder(stakeholder_id)
    if not stakeholder:
        raise ValueError(f"Stakeholder {stakeholder_id} not found")

    sb = get_supabase()

    # Build evidence text from multiple sources
    parts = []
    parts.append(f"Name: {stakeholder.get('name', '?')}")
    parts.append(f"Role: {stakeholder.get('role', 'Unknown')}")
    parts.append(f"Type: {stakeholder.get('stakeholder_type', 'Unknown')}")
    parts.append(
        f"Influence: {stakeholder.get('influence_level', 'Unknown')}",
    )

    if stakeholder.get("email"):
        parts.append(f"Email: {stakeholder['email']}")
    if stakeholder.get("organization"):
        parts.append(f"Organization: {stakeholder['organization']}")
    if stakeholder.get("notes"):
        parts.append(f"Notes: {stakeholder['notes'][:500]}")

    for field_name in ("priorities", "concerns"):
        vals = stakeholder.get(field_name) or []
        if isinstance(vals, str):
            vals = [vals]
        if vals:
            label = field_name.capitalize()
            parts.append(f"{label}: {', '.join(vals[:5])}")

    # Load evidence snippets
    evidence = stakeholder.get("evidence") or []
    for ev in evidence[:5]:
        if isinstance(ev, dict) and ev.get("text"):
            parts.append(f"Evidence: {ev['text'][:400]}")

    # Load signal chunks from source signals
    source_ids = stakeholder.get("source_signal_ids") or []
    for sid in source_ids[:5]:
        try:
            chunks = (
                sb.table("signal_chunks")
                .select("content")
                .eq("signal_id", str(sid))
                .limit(3)
                .execute()
            )
            for chunk in (chunks.data or [])[:3]:
                content = chunk.get("content", "")[:600]
                if content:
                    parts.append(f"Signal excerpt: {content}")
        except Exception:
            pass

    # Load recent signals mentioning this person
    name = stakeholder.get("name", "")
    if name:
        try:
            signals = (
                sb.table("signals")
                .select("raw_text, signal_type, source_label")
                .eq("project_id", str(project_id))
                .order("created_at", desc=True)
                .limit(5)
                .execute()
            )
            for sig in signals.data or []:
                raw = sig.get("raw_text") or ""
                if name.lower() in raw.lower():
                    parts.append(
                        f"Signal ({sig.get('signal_type', '?')}): "
                        f"{raw[:600]}"
                    )
        except Exception:
            pass

    # Load other stakeholders for relationship resolution
    other = []
    try:
        all_sh = (
            sb.table("stakeholders")
            .select(
                "id, name, role, stakeholder_type, influence_level",
            )
            .eq("project_id", str(project_id))
            .execute()
        )
        other = [
            s for s in (all_sh.data or [])
            if s["id"] != str(stakeholder_id)
        ]
    except Exception:
        pass

    return StakeholderContext(
        stakeholder_id=stakeholder_id,
        project_id=project_id,
        stakeholder=stakeholder,
        evidence_text="\n".join(parts),
        other_stakeholders=other,
    )
