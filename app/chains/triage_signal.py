"""Signal triage layer for pipeline v2.

Pure heuristic classification — no LLM cost, <100ms.

Determines:
  - Source type (from signal_type metadata + file extension + content patterns)
  - Strategy key (maps to extraction prompt blocks)
  - Source authority (client/consultant/research/prototype)
  - Priority score (higher = more likely to fill gaps)

Usage:
    from app.chains.triage_signal import triage_signal

    result = triage_signal(
        signal_type="document",
        raw_text="Meeting notes from client call...",
        metadata={"authority": "client"},
    )
"""

from __future__ import annotations

import logging
import re
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


# =============================================================================
# Triage result model
# =============================================================================


class TriageResult(BaseModel):
    """Result of signal triage — routing info for the extraction pipeline."""

    source_type: str  # Normalized source type
    strategy: str  # Key into STRATEGY_BLOCKS
    source_authority: str  # client | consultant | research | prototype
    priority_score: float = 0.5  # 0-1, higher = process first
    estimated_entity_count: int = 0
    word_count: int = 0
    reason: str = ""


# =============================================================================
# Source type → strategy mapping
# =============================================================================

SOURCE_STRATEGY_MAP: dict[str, str] = {
    # Documents
    "requirements_doc": "requirements_doc",
    "document": "requirements_doc",
    "pdf": "requirements_doc",
    "doc": "requirements_doc",
    "specification": "requirements_doc",
    "brd": "requirements_doc",
    "prd": "requirements_doc",
    # Meetings
    "transcript": "meeting_transcript",
    "call_transcript": "meeting_transcript",
    "meeting_transcript": "meeting_transcript",
    "meeting_notes": "meeting_notes",
    "notes": "meeting_notes",
    "note": "meeting_notes",
    # Communication
    "chat": "chat_messages",
    "chat_messages": "chat_messages",
    "slack": "chat_messages",
    "workspace_chat": "chat_messages",
    "email": "email",
    # Prototype
    "prototype_review": "prototype_review",
    "prototype_feedback": "prototype_review",
    "prototype": "prototype_review",
    # Research
    "research": "research",
    "competitor_analysis": "research",
    "market_research": "research",
    # Presentation
    "presentation": "presentation",
    "pptx": "presentation",
    "slides": "presentation",
}

# Authority derivation rules
AUTHORITY_MAP: dict[str, str] = {
    "requirements_doc": "client",
    "meeting_transcript": "consultant",
    "meeting_notes": "consultant",
    "chat_messages": "consultant",
    "email": "consultant",
    "prototype_review": "prototype",
    "research": "research",
    "presentation": "client",
    "default": "research",
}


# =============================================================================
# Entity density estimation (lightweight)
# =============================================================================

# Patterns that indicate entity-rich content
FEATURE_PATTERNS = [
    r"\b(?:feature|requirement|capability|function|module)\b",
    r"\b(?:must|shall|should|will)\s+(?:be able to|support|enable|provide|allow)\b",
    r"\b(?:ability to|support for|integration with)\b",
]

PERSONA_PATTERNS = [
    r"\b(?:as a|as an)\s+\w+",
    r"\b(?:user|admin|manager|operator|customer|client|patient)\s+(?:can|will|should|needs?)\b",
]

WORKFLOW_PATTERNS = [
    r"\b(?:step\s+\d|process|workflow|procedure|flow)\b",
    r"\b(?:currently|today|right now)\b.*\b(?:then|next|after)\b",
]


def _estimate_entities(text: str) -> int:
    """Quick entity count estimate from pattern matching."""
    text_lower = text.lower()
    count = 0

    for patterns in [FEATURE_PATTERNS, PERSONA_PATTERNS, WORKFLOW_PATTERNS]:
        for pattern in patterns:
            count += len(re.findall(pattern, text_lower))

    return min(count, 50)  # Cap at 50


# =============================================================================
# Content-based source type detection
# =============================================================================


def _detect_source_type(raw_text: str, signal_type: str, metadata: dict) -> str:
    """Detect source type from content patterns when signal_type is generic."""
    text_lower = raw_text[:2000].lower()

    # Check metadata first
    if metadata.get("source_type"):
        return str(metadata["source_type"])

    # File extension hints
    filename = metadata.get("filename", "")
    if filename:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext in ("pdf", "docx", "doc"):
            return "document"
        elif ext in ("pptx", "ppt"):
            return "presentation"
        elif ext == "txt" and len(raw_text) > 3000:
            return "document"

    # Content pattern detection
    transcript_markers = ["speaker:", "interviewer:", "participant:", "[00:", ">>"]
    if any(marker in text_lower for marker in transcript_markers):
        return "meeting_transcript"

    email_markers = ["from:", "to:", "subject:", "sent:", "cc:"]
    if sum(1 for m in email_markers if m in text_lower) >= 2:
        return "email"

    meeting_note_markers = ["action items", "attendees", "agenda", "minutes", "key decisions"]
    if sum(1 for m in meeting_note_markers if m in text_lower) >= 2:
        return "meeting_notes"

    if any(phrase in text_lower for phrase in ["prototype", "review session", "verdict", "aligned", "needs adjustment"]):
        return "prototype_review"

    # Length-based fallback
    if len(raw_text) > 3000:
        return "document"

    return signal_type or "default"


# =============================================================================
# Priority scoring
# =============================================================================


def _compute_priority(
    source_type: str,
    word_count: int,
    entity_estimate: int,
    authority: str,
) -> float:
    """Compute processing priority (0-1). Higher = process sooner."""
    score = 0.0

    # Authority weight (client signals are highest priority)
    authority_weights = {"client": 0.3, "consultant": 0.2, "prototype": 0.15, "research": 0.05}
    score += authority_weights.get(authority, 0.05)

    # Content richness
    if word_count > 2000:
        score += 0.2
    elif word_count > 500:
        score += 0.1

    # Entity density
    if entity_estimate > 10:
        score += 0.3
    elif entity_estimate > 5:
        score += 0.2
    elif entity_estimate > 2:
        score += 0.1

    # Source type weight
    type_weights = {
        "requirements_doc": 0.2,
        "meeting_transcript": 0.15,
        "prototype_review": 0.1,
        "email": 0.05,
        "chat_messages": 0.0,
    }
    score += type_weights.get(SOURCE_STRATEGY_MAP.get(source_type, "default"), 0.05)

    return min(score, 1.0)


# =============================================================================
# Main triage function
# =============================================================================


def triage_signal(
    signal_type: str,
    raw_text: str,
    metadata: dict[str, Any] | None = None,
) -> TriageResult:
    """Triage a signal for v2 pipeline routing.

    Pure heuristic — no LLM call, <100ms.

    Args:
        signal_type: Signal type from DB
        raw_text: Signal content
        metadata: Signal metadata dict

    Returns:
        TriageResult with strategy, authority, priority
    """
    metadata = metadata or {}

    # Detect source type
    source_type = _detect_source_type(raw_text, signal_type, metadata)

    # Map to strategy
    source_lower = source_type.lower().replace(" ", "_").replace("-", "_")
    strategy = SOURCE_STRATEGY_MAP.get(source_lower, "default")

    # Derive authority
    authority = metadata.get("authority", AUTHORITY_MAP.get(strategy, "research"))

    # Estimate content richness
    word_count = len(raw_text.split())
    entity_estimate = _estimate_entities(raw_text)

    # Compute priority
    priority = _compute_priority(source_type, word_count, entity_estimate, authority)

    # Build reason
    reasons = []
    if authority == "client":
        reasons.append("client-sourced")
    if entity_estimate > 5:
        reasons.append(f"~{entity_estimate} entities detected")
    if word_count > 2000:
        reasons.append(f"substantial ({word_count} words)")
    reason = "; ".join(reasons) if reasons else f"{source_type} signal"

    result = TriageResult(
        source_type=source_type,
        strategy=strategy,
        source_authority=authority,
        priority_score=round(priority, 3),
        estimated_entity_count=entity_estimate,
        word_count=word_count,
        reason=reason,
    )

    logger.info(
        f"Triaged signal: {source_type} → {strategy} (authority={authority}, priority={priority:.2f})",
        extra={"source_type": source_type, "strategy": strategy, "priority": priority},
    )

    return result
