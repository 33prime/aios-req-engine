"""Signal classification for routing to appropriate processing pipelines.

Classifies signals as 'lightweight' or 'heavyweight' based on:
- Source type (transcript, document, email, chat)
- Content length
- Estimated entity density

Heavyweight signals trigger the bulk processing pipeline.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Literal

from app.core.logging import get_logger

logger = get_logger(__name__)


class SignalPowerLevel(str, Enum):
    """Signal power level for pipeline routing."""
    LIGHTWEIGHT = "lightweight"
    HEAVYWEIGHT = "heavyweight"


@dataclass
class SignalClassification:
    """Result of signal classification."""

    power_level: SignalPowerLevel
    power_score: float  # 0.0 - 1.0
    reason: str
    estimated_entity_count: int
    recommended_pipeline: str

    # Breakdown of scoring factors
    source_weight: float
    length_score: float
    density_score: float


# Source type weights (higher = more likely heavyweight)
SOURCE_WEIGHTS = {
    "transcript": 1.0,
    "call_transcript": 1.0,
    "meeting_transcript": 1.0,
    "document": 0.9,
    "pdf": 0.9,
    "doc": 0.9,
    "email": 0.5,
    "long_email": 0.7,
    "chat": 0.2,
    "note": 0.3,
    "slack": 0.3,
}

# Thresholds
HEAVYWEIGHT_THRESHOLD = 0.6  # Power score >= this = heavyweight
LENGTH_HEAVYWEIGHT_CHARS = 2000  # Content longer than this contributes to heavyweight
ENTITY_HEAVYWEIGHT_COUNT = 5  # More entities than this contributes to heavyweight


def classify_signal(
    source_type: str,
    content: str,
    metadata: dict | None = None,
) -> SignalClassification:
    """
    Classify a signal for processing pipeline routing.

    Args:
        source_type: Type of signal (transcript, email, document, chat, etc.)
        content: Signal content text
        metadata: Optional metadata (may contain hints like word count, duration)

    Returns:
        SignalClassification with power level and scoring details
    """
    metadata = metadata or {}

    # 1. Source type weight
    source_type_lower = source_type.lower().replace(" ", "_").replace("-", "_")
    source_weight = SOURCE_WEIGHTS.get(source_type_lower, 0.4)

    # Upgrade email to long_email if content is substantial
    if "email" in source_type_lower and len(content) > 2000:
        source_weight = SOURCE_WEIGHTS.get("long_email", 0.7)

    # 2. Content length score (0.0 - 1.0)
    content_length = len(content)
    if content_length < 500:
        length_score = 0.1
    elif content_length < 1000:
        length_score = 0.3
    elif content_length < 2000:
        length_score = 0.5
    elif content_length < 5000:
        length_score = 0.7
    elif content_length < 10000:
        length_score = 0.85
    else:
        length_score = 1.0

    # 3. Entity density score
    entity_count = estimate_entity_density(content)
    if entity_count <= 2:
        density_score = 0.2
    elif entity_count <= 5:
        density_score = 0.4
    elif entity_count <= 10:
        density_score = 0.6
    elif entity_count <= 20:
        density_score = 0.8
    else:
        density_score = 1.0

    # 4. Calculate weighted power score
    # Source type is most important, followed by density, then length
    power_score = (
        source_weight * 0.4 +
        density_score * 0.35 +
        length_score * 0.25
    )

    # 5. Determine power level
    if power_score >= HEAVYWEIGHT_THRESHOLD:
        power_level = SignalPowerLevel.HEAVYWEIGHT
        recommended_pipeline = "bulk_processing"
    else:
        power_level = SignalPowerLevel.LIGHTWEIGHT
        recommended_pipeline = "standard_processing"

    # 6. Build reason string
    reasons = []
    if source_weight >= 0.8:
        reasons.append(f"high-value source ({source_type})")
    if entity_count >= ENTITY_HEAVYWEIGHT_COUNT:
        reasons.append(f"{entity_count} entities detected")
    if content_length >= LENGTH_HEAVYWEIGHT_CHARS:
        reasons.append(f"substantial content ({content_length} chars)")

    if not reasons:
        if power_level == SignalPowerLevel.LIGHTWEIGHT:
            reasons.append("standard signal characteristics")
        else:
            reasons.append("combined factors exceed threshold")

    reason = "; ".join(reasons)

    classification = SignalClassification(
        power_level=power_level,
        power_score=round(power_score, 3),
        reason=reason,
        estimated_entity_count=entity_count,
        recommended_pipeline=recommended_pipeline,
        source_weight=round(source_weight, 2),
        length_score=round(length_score, 2),
        density_score=round(density_score, 2),
    )

    logger.info(
        f"Classified signal as {power_level.value} (score: {power_score:.2f})",
        extra={
            "source_type": source_type,
            "power_level": power_level.value,
            "power_score": power_score,
            "entity_count": entity_count,
            "content_length": content_length,
        },
    )

    return classification


def estimate_entity_density(content: str) -> int:
    """
    Quick estimation of entity count without full LLM extraction.

    Looks for patterns that indicate features, personas, or stakeholders:
    - Feature-like phrases ("ability to", "support for", "enable")
    - Person names (capitalized words in certain patterns)
    - Technical terms
    - Action items

    Args:
        content: Text content to scan

    Returns:
        Estimated count of entities mentioned
    """
    entities = set()
    content_lower = content.lower()

    # 1. Feature-like patterns
    feature_patterns = [
        r'\b(?:ability|feature|capability|function|support)\s+(?:to|for)\s+([a-z\s]{5,30})',
        r'\b(?:enable|allow|provide|offer)\s+([a-z\s]{5,30})',
        r'\b(?:integration with|connect to|sync with)\s+([A-Za-z\s]{3,20})',
        r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:feature|module|system)',
    ]

    for pattern in feature_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            if isinstance(match, str) and len(match.strip()) > 3:
                entities.add(f"feature:{match.strip()[:30]}")

    # 2. Person names (Title Case words that look like names)
    # Pattern: First Last or First Middle Last
    name_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b'
    potential_names = re.findall(name_pattern, content)

    # Filter out common non-names
    non_names = {
        'The', 'This', 'That', 'These', 'Those', 'What', 'When', 'Where',
        'Which', 'Who', 'How', 'Why', 'Monday', 'Tuesday', 'Wednesday',
        'Thursday', 'Friday', 'Saturday', 'Sunday', 'January', 'February',
        'March', 'April', 'May', 'June', 'July', 'August', 'September',
        'October', 'November', 'December', 'New York', 'San Francisco',
        'Los Angeles', 'Value Path', 'Product Manager', 'Project Manager',
    }

    for name in potential_names:
        if name not in non_names and len(name) > 4:
            # Additional heuristic: names usually have 2-3 parts
            parts = name.split()
            if 2 <= len(parts) <= 3:
                entities.add(f"person:{name}")

    # 3. Role mentions (often indicate stakeholders)
    role_patterns = [
        r'\b(CEO|CTO|CFO|COO|CMO|VP|Director|Manager|Lead|Head)\b',
        r'\b([A-Z][a-z]+)\s+(Manager|Director|Lead|Head|Officer)\b',
    ]

    for pattern in role_patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            if isinstance(match, tuple):
                role = " ".join(match)
            else:
                role = match
            entities.add(f"role:{role}")

    # 4. Technical/product terms (often features or integrations)
    tech_patterns = [
        r'\b(API|SDK|SSO|OAuth|SAML|JWT|REST|GraphQL)\b',
        r'\b([A-Z][a-z]+(?:Hub|Force|Suite|Cloud|Base|Kit|Flow))\b',
        r'\b(Salesforce|HubSpot|Slack|Jira|Asana|Notion|Figma|GitHub)\b',
    ]

    for pattern in tech_patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            entities.add(f"tech:{match}")

    # 5. Action items / requirements (often map to features)
    action_patterns = [
        r'\b(?:need to|must|should|will)\s+([a-z\s]{5,25})\b',
        r'\b(?:requirement|req):\s*([^\n]{5,50})',
    ]

    for pattern in action_patterns:
        matches = re.findall(pattern, content_lower)
        for match in matches[:10]:  # Limit to avoid over-counting
            if len(match.strip()) > 5:
                entities.add(f"action:{match.strip()[:25]}")

    # 6. User types / personas
    persona_patterns = [
        r'\b(admin|administrator|user|customer|client|patient|student|teacher|employee|manager)\s+(?:can|will|should|needs?)\b',
        r'\b(?:as a|as an)\s+([a-z\s]{3,20}),?\s+I\b',
    ]

    for pattern in persona_patterns:
        matches = re.findall(pattern, content_lower)
        for match in matches:
            entities.add(f"persona:{match}")

    return len(entities)


def should_use_bulk_pipeline(classification: SignalClassification) -> bool:
    """
    Simple helper to check if bulk pipeline should be used.

    Args:
        classification: Signal classification result

    Returns:
        True if bulk pipeline recommended
    """
    return classification.power_level == SignalPowerLevel.HEAVYWEIGHT


def get_processing_recommendation(classification: SignalClassification) -> dict:
    """
    Get detailed processing recommendations based on classification.

    Args:
        classification: Signal classification result

    Returns:
        Dict with processing recommendations
    """
    if classification.power_level == SignalPowerLevel.HEAVYWEIGHT:
        return {
            "pipeline": "bulk",
            "steps": [
                "parallel_extraction",  # Run all extraction agents in parallel
                "consolidation",        # Merge and dedupe
                "validation",           # Research sanity check
                "bulk_proposal",        # Single proposal for all changes
            ],
            "expected_entities": classification.estimated_entity_count,
            "requires_review": True,
            "auto_apply": False,
        }
    else:
        return {
            "pipeline": "standard",
            "steps": [
                "fact_extraction",      # Standard fact extraction
                "incremental_update",   # Individual patches if needed
            ],
            "expected_entities": classification.estimated_entity_count,
            "requires_review": False,
            "auto_apply": classification.estimated_entity_count <= 2,
        }
