"""Semantic intent classification using embeddings.

Replaces keyword-based intent detection with embedding similarity
for more robust and accurate classification.
"""

from functools import lru_cache

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.context.models import IntentClassification
from app.core.embeddings import embed_texts
from app.core.logging import get_logger

logger = get_logger(__name__)


# Intent categories with example phrases (exemplars)
INTENT_EXEMPLARS: dict[str, list[str]] = {
    "proposal": [
        "Add a new feature for user authentication",
        "Create a dark mode toggle",
        "I want to propose a new capability",
        "Can you suggest some features?",
        "Generate features for the checkout flow",
        "Add batch of features for notifications",
        "Create multiple features for the dashboard",
    ],
    "insights": [
        "What issues do we have?",
        "Show me the gaps in the PRD",
        "Are there any problems we should address?",
        "List the insights from the red team",
        "What patches are available?",
        "Show me what needs fixing",
        "What improvements have been identified?",
    ],
    "research": [
        "Search for competitor information",
        "Find evidence for this feature",
        "What does the research say about user preferences?",
        "Look up market data on this topic",
        "Find studies related to our approach",
        "What evidence supports this decision?",
    ],
    "status": [
        "What's the current state of the project?",
        "Give me a summary of where we are",
        "How much progress have we made?",
        "What's the overview of this PRD?",
        "Show me the project status",
        "What needs attention right now?",
    ],
    "analysis": [
        "Analyze the gaps in our features",
        "Assess if we're ready to build",
        "Evaluate the current PRD completeness",
        "Check the readiness score",
        "Review the value path coverage",
        "How well are our features validated?",
    ],
    "prd": [
        "Update the software summary section",
        "What's in the PRD requirements?",
        "Show me the constraints section",
        "Edit the happy path description",
        "What does the PRD say about personas?",
    ],
    "features": [
        "Tell me about the current features",
        "Which features are marked as MVP?",
        "Show me the feature list",
        "What features do we have so far?",
        "List all the confirmed features",
    ],
    "value_path": [
        "What are the value path steps?",
        "Show me the user journey",
        "Update the value path",
        "What steps are in the value path?",
        "Add a new step to the value path",
    ],
    "personas": [
        "Who are the target personas?",
        "Tell me about our user personas",
        "Add a new persona",
        "Update the persona details",
        "What personas do we have?",
    ],
    "confirmation": [
        "What needs client confirmation?",
        "Show me pending confirmations",
        "Create a confirmation item for this",
        "What questions do we need answered?",
    ],
    "query": [
        "What is this feature about?",
        "How does this work?",
        "Why did we make that decision?",
        "Explain the architecture",
        "Tell me more about this",
        "I have a question about the project",
    ],
}

# Entity focus patterns
ENTITY_PATTERNS: dict[str, list[str]] = {
    "feature": ["feature", "capability", "functionality", "mvp feature"],
    "prd": ["prd", "section", "requirement", "document", "specification"],
    "vp": ["value path", "step", "journey", "flow", "vp step"],
    "persona": ["persona", "user", "target user", "customer segment"],
    "insight": ["insight", "issue", "gap", "problem", "patch"],
    "research": ["research", "evidence", "study", "data", "market"],
}

# Batch operation indicators
BATCH_INDICATORS = [
    "multiple", "several", "batch", "all", "many", "bunch",
    "generate", "create multiple", "add several", "propose batch",
]

# Cached embeddings for exemplars
_exemplar_embeddings: dict[str, np.ndarray] | None = None


def _get_exemplar_embeddings() -> dict[str, np.ndarray]:
    """Get or compute cached embeddings for intent exemplars."""
    global _exemplar_embeddings

    if _exemplar_embeddings is not None:
        return _exemplar_embeddings

    logger.info("Computing intent exemplar embeddings...")
    _exemplar_embeddings = {}

    for intent, phrases in INTENT_EXEMPLARS.items():
        embeddings = embed_texts(phrases)
        # Store as numpy array for similarity computation
        _exemplar_embeddings[intent] = np.array(embeddings)

    logger.info(f"Cached embeddings for {len(_exemplar_embeddings)} intents")
    return _exemplar_embeddings


async def classify_intent(
    message: str,
    project_context: dict | None = None,
    threshold: float = 0.5,
) -> IntentClassification:
    """
    Classify user message intent using semantic similarity.

    Args:
        message: User's message text
        project_context: Optional project context for additional signals
        threshold: Minimum similarity score to consider a match

    Returns:
        IntentClassification with primary intent and confidence
    """
    if not message or not message.strip():
        return IntentClassification(
            primary="query",
            confidence=0.5,
            entity_focus=None,
            batch_likely=False,
        )

    # Get message embedding
    message_embedding = np.array(embed_texts([message])[0]).reshape(1, -1)

    # Get exemplar embeddings
    exemplar_embeddings = _get_exemplar_embeddings()

    # Compute similarity to each intent
    intent_scores: dict[str, float] = {}
    for intent, exemplar_matrix in exemplar_embeddings.items():
        # Compute cosine similarity to all exemplars for this intent
        similarities = cosine_similarity(message_embedding, exemplar_matrix)[0]
        # Use max similarity (best matching exemplar)
        intent_scores[intent] = float(np.max(similarities))

    # Sort by score
    sorted_intents = sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)

    # Get primary intent
    primary_intent, primary_score = sorted_intents[0]

    # Get secondary intents (above threshold, not primary)
    secondary_intents = [
        intent for intent, score in sorted_intents[1:4]
        if score >= threshold
    ]

    # Detect entity focus
    entity_focus = _detect_entity_focus(message)

    # Detect batch operation
    batch_likely = _detect_batch_operation(message)

    # Adjust confidence based on message characteristics
    confidence = _adjust_confidence(primary_score, message)

    return IntentClassification(
        primary=primary_intent,
        confidence=confidence,
        entity_focus=entity_focus,
        batch_likely=batch_likely,
        secondary_intents=secondary_intents,
    )


def _detect_entity_focus(message: str) -> str | None:
    """Detect which entity type the message focuses on."""
    message_lower = message.lower()

    for entity_type, patterns in ENTITY_PATTERNS.items():
        for pattern in patterns:
            if pattern in message_lower:
                return entity_type

    return None


def _detect_batch_operation(message: str) -> bool:
    """Detect if the message suggests a batch operation."""
    message_lower = message.lower()

    for indicator in BATCH_INDICATORS:
        if indicator in message_lower:
            return True

    return False


def _adjust_confidence(base_score: float, message: str) -> float:
    """Adjust confidence based on message characteristics."""
    confidence = base_score

    # Short messages tend to be ambiguous
    word_count = len(message.split())
    if word_count < 4:
        confidence *= 0.85

    # Very long messages might have multiple intents
    if word_count > 30:
        confidence *= 0.9

    # Questions are often clearer
    if "?" in message:
        confidence = min(1.0, confidence * 1.05)

    return round(min(1.0, confidence), 3)


# Fallback to keyword-based classification
def classify_intent_fallback(message: str) -> IntentClassification:
    """
    Fallback keyword-based classification when embeddings unavailable.

    This mirrors the original detect_intent logic from chat_context.py
    """
    message_lower = message.lower()

    # Keyword patterns (simplified from original)
    patterns = {
        "proposal": ["add", "create", "new", "propose", "suggest", "generate", "batch"],
        "insights": ["insight", "issue", "gap", "problem", "patch", "fix", "improvement"],
        "research": ["research", "evidence", "competitor", "market", "study", "data"],
        "status": ["status", "summary", "overview", "what's", "show me", "attention"],
        "analysis": ["analyze", "assess", "evaluate", "review", "check", "readiness", "gaps"],
        "prd": ["prd", "requirement", "section", "specification"],
        "query": ["what", "how", "why", "when", "where", "explain", "tell me"],
    }

    # Score each intent
    scores: dict[str, int] = {intent: 0 for intent in patterns}
    for intent, keywords in patterns.items():
        for keyword in keywords:
            if keyword in message_lower:
                scores[intent] += 1

    # Find best match
    best_intent = max(scores, key=lambda k: scores[k])
    best_score = scores[best_intent]

    # Calculate confidence
    if best_score == 0:
        confidence = 0.4
        best_intent = "query"
    elif best_score == 1:
        confidence = 0.6
    else:
        confidence = min(0.9, 0.6 + (best_score * 0.1))

    return IntentClassification(
        primary=best_intent,
        confidence=confidence,
        entity_focus=_detect_entity_focus(message),
        batch_likely=_detect_batch_operation(message),
        secondary_intents=[],
    )


def clear_embedding_cache():
    """Clear the cached exemplar embeddings."""
    global _exemplar_embeddings
    _exemplar_embeddings = None
    logger.info("Intent exemplar embeddings cache cleared")
