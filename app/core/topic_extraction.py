"""Topic Extraction for Entity-Stakeholder Matching.

Extracts topic keywords from entities (features, personas, VP steps) for
matching with stakeholder domain expertise and topic mentions.

Used by the "Who Would Know" confirmation suggestion feature.
"""

import re
from typing import Any


# Common stop words to filter out
STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "shall", "can", "need", "dare",
    "and", "or", "but", "if", "then", "else", "when", "where", "why",
    "how", "what", "which", "who", "whom", "this", "that", "these",
    "those", "am", "is", "are", "was", "were", "be", "been", "being",
    "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
    "into", "through", "during", "before", "after", "above", "below",
    "between", "under", "again", "further", "once", "here", "there",
    "all", "each", "few", "more", "most", "other", "some", "such",
    "no", "not", "only", "own", "same", "so", "than", "too", "very",
    "just", "also", "now", "user", "users", "system", "feature",
    "ability", "able", "want", "needs", "should", "must", "allow",
    "allows", "enable", "enables", "provide", "provides", "support",
    "supports", "include", "includes", "using", "used", "use",
}

# Technical domain keywords to prioritize
DOMAIN_KEYWORDS = {
    # Security & Auth
    "authentication", "auth", "sso", "saml", "oauth", "login", "security",
    "mfa", "2fa", "password", "credentials", "encryption", "permissions",
    "access", "authorization", "rbac", "role", "roles",
    # Compliance
    "compliance", "hipaa", "gdpr", "sox", "pci", "audit", "regulation",
    "privacy", "data-protection", "retention",
    # Infrastructure
    "api", "integration", "webhook", "rest", "graphql", "database", "sql",
    "cloud", "aws", "azure", "gcp", "infrastructure", "deployment", "ci/cd",
    "kubernetes", "docker", "microservices", "serverless",
    # Analytics & Data
    "analytics", "reporting", "dashboard", "metrics", "kpi", "data",
    "export", "import", "csv", "excel", "visualization", "charts",
    # UX/UI
    "mobile", "desktop", "responsive", "accessibility", "a11y", "ux", "ui",
    "design", "interface", "navigation", "usability",
    # Business
    "workflow", "automation", "notification", "email", "invoice", "billing",
    "payment", "subscription", "pricing", "budget", "cost", "roi",
    # Performance
    "performance", "speed", "latency", "scalability", "reliability",
    "uptime", "availability", "caching", "optimization",
}


def extract_topics_from_text(text: str, max_topics: int = 10) -> list[str]:
    """
    Extract topic keywords from text.

    Args:
        text: Text to extract topics from
        max_topics: Maximum number of topics to return

    Returns:
        List of topic keywords, prioritized by relevance
    """
    if not text:
        return []

    # Normalize text
    text = text.lower()

    # Extract words (including hyphenated terms)
    words = re.findall(r'\b[a-z][a-z0-9-]*[a-z0-9]\b|\b[a-z]\b', text)

    # Score words
    scored_topics = {}

    for word in words:
        if word in STOP_WORDS:
            continue
        if len(word) < 2:
            continue

        # Score based on characteristics
        score = 1

        # Boost domain keywords
        if word in DOMAIN_KEYWORDS:
            score += 5

        # Boost technical-looking terms
        if "-" in word:  # e.g., "single-sign-on"
            score += 2
        if any(c.isdigit() for c in word):  # e.g., "oauth2"
            score += 1

        # Accumulate score for repeated mentions
        scored_topics[word] = scored_topics.get(word, 0) + score

    # Sort by score and return top N
    sorted_topics = sorted(
        scored_topics.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return [topic for topic, _ in sorted_topics[:max_topics]]


def extract_topics_from_entity(
    entity: dict[str, Any],
    entity_type: str,
) -> list[str]:
    """
    Extract topic keywords from an entity (feature, persona, VP step).

    Args:
        entity: Entity dict
        entity_type: Type of entity (feature, persona, vp_step)

    Returns:
        List of topic keywords
    """
    text_parts = []

    if entity_type == "feature":
        # Features: name, description, user_problem, acceptance_criteria
        text_parts.extend([
            entity.get("name", ""),
            entity.get("description", ""),
            entity.get("user_problem", ""),
            entity.get("prd_rationale", ""),
        ])
        # Join acceptance criteria if present
        ac = entity.get("acceptance_criteria", [])
        if isinstance(ac, list):
            text_parts.extend(ac)

    elif entity_type == "persona":
        # Personas: name, description, pain_points, goals
        text_parts.extend([
            entity.get("name", ""),
            entity.get("description", ""),
        ])
        for field in ["pain_points", "goals", "behaviors"]:
            items = entity.get(field, [])
            if isinstance(items, list):
                text_parts.extend(items)

    elif entity_type == "vp_step":
        # VP Steps: action, outcome, value_moment
        text_parts.extend([
            entity.get("action", ""),
            entity.get("outcome", ""),
            entity.get("value_moment", ""),
            entity.get("emotion", ""),
        ])

    else:
        # Generic: try common fields
        for field in ["name", "description", "content", "text", "summary"]:
            if entity.get(field):
                text_parts.append(entity[field])

    # Combine and extract
    combined_text = " ".join(str(p) for p in text_parts if p)
    return extract_topics_from_text(combined_text)


def extract_topics_from_signal_for_stakeholder(
    signal_content: str,
    stakeholder_name: str,
    max_topics: int = 15,
) -> list[str]:
    """
    Extract topics that a specific stakeholder discussed in a signal.

    Looks for content near stakeholder mentions or speaker tags.

    Args:
        signal_content: Full signal content
        stakeholder_name: Name of stakeholder to find
        max_topics: Max topics to extract

    Returns:
        List of topics the stakeholder discussed
    """
    if not signal_content or not stakeholder_name:
        return []

    content_lower = signal_content.lower()
    name_lower = stakeholder_name.lower()

    # Find sections where stakeholder is speaking or mentioned
    relevant_sections = []

    # Pattern 1: Speaker tag format "[Name]:" or "Name:"
    speaker_pattern = re.compile(
        rf'\[?{re.escape(name_lower)}\]?\s*:(.+?)(?=\n\[?\w+\]?\s*:|$)',
        re.IGNORECASE | re.DOTALL
    )
    for match in speaker_pattern.finditer(signal_content):
        relevant_sections.append(match.group(1))

    # Pattern 2: Mentioned in sentence (get surrounding context)
    mention_pattern = re.compile(
        rf'.{{0,200}}{re.escape(name_lower)}.{{0,200}}',
        re.IGNORECASE
    )
    for match in mention_pattern.finditer(signal_content):
        relevant_sections.append(match.group(0))

    # If no specific sections found, fall back to full content
    if not relevant_sections:
        # Just extract from first part of content
        relevant_sections = [signal_content[:2000]]

    combined = " ".join(relevant_sections)
    return extract_topics_from_text(combined, max_topics)


def get_confirmation_gap_topics(
    entity: dict[str, Any],
    entity_type: str,
    gap_description: str | None = None,
) -> list[str]:
    """
    Get topics relevant to a confirmation gap.

    Combines entity topics with any specific gap description.

    Args:
        entity: Entity needing confirmation
        entity_type: Type of entity
        gap_description: Optional specific gap description

    Returns:
        List of topics for stakeholder matching
    """
    topics = extract_topics_from_entity(entity, entity_type)

    if gap_description:
        gap_topics = extract_topics_from_text(gap_description, max_topics=5)
        # Prepend gap topics (higher priority)
        topics = gap_topics + [t for t in topics if t not in gap_topics]

    return topics[:15]
