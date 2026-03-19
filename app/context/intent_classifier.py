"""Structured intent classification for chat messages.

Three-layer: regex patterns (~0ms, ~70% coverage) + page context fallback
+ optional Haiku LLM fallback for ambiguous messages (~200ms, ~30% coverage).
"""

import asyncio
import json
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
    retrieval_strategy: str = "full"  # "none" | "light" | "full"
    classifier_source: str = "regex"  # "regex" | "haiku"


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

# Acknowledgement pattern — instant path, no retrieval needed
_ACK_PATTERN = re.compile(
    r"^(thanks|thank you|ok|okay|got it|yes|no|sure|perfect"
    r"|great|cool|do it|sounds good|👍)\.?!?\s*$",
    re.I,
)

# Entity-related nouns for topic extraction
_ENTITY_NOUNS = re.compile(
    r"\b(feature|persona|workflow|stakeholder|constraint|driver|pain\s+point|"
    r"goal|kpi|data\s+entity|unlock|business\s+driver|requirement)\b",
    re.I,
)

# Pattern: CRUD message that references existing project data
_NEEDS_CONTEXT_PATTERN = re.compile(
    r"\b(from\s+(?:the|our|existing)\s+|based\s+on\s+|"
    r"using\s+(?:the|our)\s+|from\s+(?:evidence|requirements|data|"
    r"what\s+we\s+have|what\s+we.ve\s+captured))\b",
    re.I,
)

# Valid intent types for Haiku validation
_VALID_INTENTS = {
    "search", "create", "update", "delete",
    "discuss", "plan", "review", "flow", "collaborate",
}
_VALID_STRATEGIES = {"none", "light", "full"}

# ── Haiku LLM Classifier ─────────────────────────────────────────

_HAIKU_CLASSIFY_PROMPT = """\
Classify this chat message's intent and retrieval needs.

Message: "{message}"
Page: {page}

Intent types: search, create, update, delete, discuss, plan, review, flow, collaborate
Retrieval: none (acks, CRUD), light (simple questions), full (search, planning)

Return JSON only: {{"intent": "...", "retrieval_strategy": "...", "confidence": 0.0-1.0}}"""

_HAIKU_TIMEOUT_MS = 500


async def classify_with_llm(
    message: str,
    page_context: str | None,
) -> ChatIntent | None:
    """Call Haiku for intent classification. Returns None on timeout/error.

    500ms hard timeout — never blocks the pipeline.
    """
    try:
        from anthropic import AsyncAnthropic

        from app.core.config import get_settings

        settings = get_settings()
        if not settings.ANTHROPIC_API_KEY:
            return None

        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        prompt = _HAIKU_CLASSIFY_PROMPT.format(
            message=message[:200],
            page=page_context or "none",
        )

        response = await asyncio.wait_for(
            client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=50,
                messages=[{"role": "user", "content": prompt}],
            ),
            timeout=_HAIKU_TIMEOUT_MS / 1000,
        )

        text = response.content[0].text.strip()
        # Parse JSON from response (handle markdown fences)
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text)

        intent_type = data.get("intent", "discuss")
        strategy = data.get("retrieval_strategy", "light")

        # Validate
        if intent_type not in _VALID_INTENTS:
            intent_type = "discuss"
        if strategy not in _VALID_STRATEGIES:
            strategy = "light"

        topics = _extract_topics(message)
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
            retrieval_strategy=strategy,
            classifier_source="haiku",
        )
    except TimeoutError:
        logger.debug("Haiku classifier timed out (500ms)")
        return None
    except Exception as e:
        logger.debug(f"Haiku classifier failed: {e}")
        return None


# ── Synchronous Classifier (fast path) ────────────────────────────


def classify_intent(
    message: str, page_context: str | None = None
) -> ChatIntent:
    """Classify chat message intent — synchronous regex-only path.

    For the async hybrid path, use classify_intent_async().
    """
    return _classify_regex(message, page_context)


async def classify_intent_async(
    message: str, page_context: str | None = None
) -> ChatIntent:
    """Classify with regex first, fall back to Haiku for ambiguous cases.

    Hybrid classification:
    1. Regex match → high confidence → return immediately
    2. Regex falls to default ("discuss") → try Haiku (500ms timeout)
    3. Haiku timeout/error → return regex result
    """
    regex_result = _classify_regex(message, page_context)

    # High-confidence regex matches: explicit acks, CRUD commands,
    # clear search keywords — no need for LLM
    if regex_result.type != "discuss" or _ACK_PATTERN.match(message.strip()):
        return regex_result

    # Regex fell through to "discuss" default — ambiguous case.
    # Try Haiku for better classification.
    haiku_result = await classify_with_llm(message, page_context)
    if haiku_result:
        logger.info(
            "Haiku classifier: %s/%s (regex was: discuss/%s)",
            haiku_result.type,
            haiku_result.retrieval_strategy,
            regex_result.retrieval_strategy,
        )
        return haiku_result

    return regex_result


def _classify_regex(
    message: str, page_context: str | None
) -> ChatIntent:
    """Pure regex classification — ~0ms."""
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

    # Retrieval strategy
    retrieval_strategy = _compute_retrieval_strategy(
        message, intent_type, complexity,
    )

    return ChatIntent(
        type=intent_type,
        topics=topics,
        entity_refs=len(topics),
        complexity=complexity,
        retrieval_strategy=retrieval_strategy,
        classifier_source="regex",
    )


def _compute_retrieval_strategy(
    message: str, intent_type: str, complexity: str,
) -> str:
    """Determine retrieval strategy: none, light, or full."""
    # Acks and simple confirmations need no retrieval
    if _ACK_PATTERN.match(message.strip()):
        return "none"

    # Create/update/delete skip retrieval UNLESS message references
    # existing data ("from the evidence", "based on requirements", etc.)
    if intent_type in ("create", "update", "delete"):
        if _NEEDS_CONTEXT_PATTERN.search(message):
            return "light"
        return "none"

    # Simple discuss/review/flow queries use light retrieval
    if intent_type in ("discuss", "review", "flow") and complexity == "simple":
        return "light"

    # Search, plan, collaborate, and strategic queries use full
    if intent_type in ("search", "plan", "collaborate"):
        return "full"
    if complexity == "strategic":
        return "full"

    return "light"


def _match_intent_type(message: str) -> str:
    """Match message against intent patterns. First match or 'discuss'."""
    for intent_type, pattern in _INTENT_PATTERNS:
        if pattern.search(message):
            return intent_type
    return "discuss"


def _extract_topics(message: str) -> list[str]:
    """Extract entity-related topic keywords from message."""
    matches = _ENTITY_NOUNS.findall(message)
    seen: set[str] = set()
    topics: list[str] = []
    for m in matches:
        lower = m.lower().strip()
        if lower not in seen:
            seen.add(lower)
            topics.append(lower)
    return topics
