"""Structured intent classification for chat messages.

Two-layer: regex patterns (~0ms, ~70% coverage) + page context fallback.
Extracts structured signals for cognitive frame selection.
"""

import re
from dataclasses import dataclass, field

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ChatIntent:
    """Classified intent of a chat message."""

    type: str  # search | create | update | delete | discuss | plan | review | flow | collaborate
    topics: list[str] = field(default_factory=list)
    entity_refs: int = 0
    complexity: str = "simple"  # simple | moderate | strategic


# ── Pattern Definitions ────────────────────────────────────────────

_INTENT_PATTERNS: list[tuple[str, re.Pattern]] = [
    (
        "search",
        re.compile(
            r"\b(find|search|look\s+up|show\s+me|where|what\s+do\s+we\s+know|"
            r"what\s+did\s+they\s+say|evidence|quote)\b",
            re.I,
        ),
    ),
    (
        "create",
        re.compile(
            r"\b(create|add|new|make|build|generate|draft|write)\b",
            re.I,
        ),
    ),
    (
        "update",
        re.compile(
            r"\b(update|change|modify|rename|set|edit|fix|adjust|move)\b",
            re.I,
        ),
    ),
    (
        "delete",
        re.compile(
            r"\b(delete|remove|drop|get\s+rid\s+of|consolidate|reduce|merge)\b",
            re.I,
        ),
    ),
    (
        "review",
        re.compile(
            r"\b(review|check|audit|compare|assess|evaluate|how\s+are\s+we|"
            r"what\s+needs|status|health)\b",
            re.I,
        ),
    ),
    (
        "plan",
        re.compile(
            r"\b(plan|strategy|roadmap|next\s+steps|prioritize|focus\s+on|"
            r"what\s+should|recommend)\b",
            re.I,
        ),
    ),
    (
        "collaborate",
        re.compile(
            r"\b(email|schedule|meeting|send|share|client|portal|push|escalate)\b",
            re.I,
        ),
    ),
    (
        "flow",
        re.compile(
            r"\b(step|flow|goal|actor|guardrail|behavior|output|refine)\b",
            re.I,
        ),
    ),
]

# Entity-related nouns for topic extraction
_ENTITY_NOUNS = re.compile(
    r"\b(feature|persona|workflow|stakeholder|constraint|driver|pain\s+point|"
    r"goal|kpi|data\s+entity|unlock|business\s+driver|requirement)\b",
    re.I,
)


# ── Classifier ─────────────────────────────────────────────────────


def classify_intent(message: str, page_context: str | None = None) -> ChatIntent:
    """Classify chat message intent with structured signals.

    Two-layer:
    1. Regex patterns (~0ms, handles ~70% of messages)
    2. Page context fallback for the remaining ~30%
    """
    # Layer 1: Regex pattern matching
    intent_type = _match_intent_type(message)

    # Layer 2: Page context override
    if page_context == "brd:solution-flow" and intent_type == "discuss":
        intent_type = "flow"
    elif page_context == "collaborate" and intent_type == "discuss":
        intent_type = "collaborate"

    # Extract topics
    topics = _extract_topics(message)

    # Complexity assessment
    word_count = len(message.split())
    if word_count < 10:
        complexity = "simple"
    elif len(topics) <= 2:
        complexity = "moderate"
    else:
        complexity = "strategic"

    return ChatIntent(
        type=intent_type,
        topics=topics,
        entity_refs=len(topics),
        complexity=complexity,
    )


def _match_intent_type(message: str) -> str:
    """Match message against intent patterns. Returns first match or 'discuss'."""
    for intent_type, pattern in _INTENT_PATTERNS:
        if pattern.search(message):
            return intent_type
    return "discuss"


def _extract_topics(message: str) -> list[str]:
    """Extract entity-related topic keywords from message."""
    matches = _ENTITY_NOUNS.findall(message)
    # Deduplicate while preserving order
    seen: set[str] = set()
    topics: list[str] = []
    for m in matches:
        lower = m.lower().strip()
        if lower not in seen:
            seen.add(lower)
            topics.append(lower)
    return topics
