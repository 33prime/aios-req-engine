"""Speaker resolution — fuzzy matching transcript speaker names to project stakeholders.

Uses meta-tag speaker_roles from chunks to identify who spoke, then matches
against the project's stakeholder list using 3 tiers:
  1. Exact first_name or last_name match
  2. Fuzzy name match (token_set_ratio > 0.75)
  3. Initial + last_name match ("B. Wilson" → "Brandon Wilson")
"""

from __future__ import annotations

import logging
import re
from uuid import UUID

from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)


def resolve_speakers_for_signal(
    project_id: UUID,
    signal_id: UUID,
    chunks: list[dict],
) -> dict[str, UUID]:
    """Resolve speaker names from chunk meta-tags to stakeholder UUIDs.

    Args:
        project_id: Project UUID
        signal_id: Signal UUID (for logging)
        chunks: List of chunk dicts with metadata.meta_tags.speaker_roles

    Returns:
        Dict mapping speaker name → stakeholder UUID
    """
    # Collect all speaker names from chunks
    all_speakers: set[str] = set()
    for chunk in chunks:
        meta_tags = (chunk.get("metadata") or {}).get("meta_tags", {})
        speaker_roles = meta_tags.get("speaker_roles", {})
        all_speakers.update(speaker_roles.keys())

    if not all_speakers:
        return {}

    # Load project stakeholders
    sb = get_supabase()
    try:
        resp = (
            sb.table("stakeholders")
            .select("id, name, role, organization")
            .eq("project_id", str(project_id))
            .eq("is_stale", False)
            .execute()
        )
        stakeholders = resp.data or []
    except Exception as e:
        logger.debug(f"Stakeholder loading failed for speaker resolution: {e}")
        return {}

    if not stakeholders:
        return {}

    resolved: dict[str, UUID] = {}

    for speaker in all_speakers:
        match = _match_speaker_to_stakeholder(speaker, stakeholders)
        if match:
            resolved[speaker] = UUID(match["id"])

    if resolved:
        logger.info(
            f"Resolved {len(resolved)}/{len(all_speakers)} speakers for signal {signal_id}: "
            f"{list(resolved.keys())}"
        )

    return resolved


def _match_speaker_to_stakeholder(
    speaker: str,
    stakeholders: list[dict],
) -> dict | None:
    """Match a speaker name to a stakeholder using 3 tiers."""
    speaker_clean = speaker.strip()
    if not speaker_clean:
        return None

    speaker_lower = speaker_clean.lower()
    speaker_parts = speaker_lower.split()

    # Tier 1: Exact first_name or last_name match
    for sh in stakeholders:
        sh_name = (sh.get("name") or "").strip()
        if not sh_name:
            continue

        sh_parts = sh_name.lower().split()
        # Exact full name match
        if speaker_lower == sh_name.lower():
            return sh
        # First name match (if speaker is single word)
        if len(speaker_parts) == 1 and sh_parts and speaker_parts[0] == sh_parts[0]:
            return sh
        # Last name match (if speaker is single word and stakeholder has 2+ name parts)
        if len(speaker_parts) == 1 and len(sh_parts) >= 2 and speaker_parts[0] == sh_parts[-1]:
            return sh

    # Tier 2: Fuzzy name match
    try:
        from rapidfuzz import fuzz

        best_score = 0.0
        best_match = None
        for sh in stakeholders:
            sh_name = (sh.get("name") or "").strip()
            if not sh_name:
                continue
            score = fuzz.token_set_ratio(speaker_lower, sh_name.lower()) / 100.0
            if score > best_score:
                best_score = score
                best_match = sh

        if best_score >= 0.75 and best_match:
            return best_match
    except ImportError:
        pass

    # Tier 3: Initial + last_name match ("B. Wilson" → "Brandon Wilson")
    initial_match = re.match(r"^([A-Z])\.?\s+(\S+)$", speaker_clean)
    if initial_match:
        initial = initial_match.group(1).lower()
        last = initial_match.group(2).lower()
        for sh in stakeholders:
            sh_name = (sh.get("name") or "").strip()
            sh_parts = sh_name.lower().split()
            if len(sh_parts) >= 2 and sh_parts[0].startswith(initial) and sh_parts[-1] == last:
                return sh

    return None
