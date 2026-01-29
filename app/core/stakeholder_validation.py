"""Validation utilities for stakeholder extraction."""

import re

from app.core.logging import get_logger

logger = get_logger(__name__)

# Patterns that indicate NOT a person
ORGANIZATION_PATTERNS = [
    r'\b(team|department|group|committee|board|division|unit|office)\b',
    r'\b(inc|llc|corp|ltd|co\.|company|corporation)\b',
    r'\b(the\s+\w+\s+team)\b',
    r'^(engineering|sales|marketing|product|design|hr|finance|legal|ops|operations)$',
]

# Patterns that indicate likely a person (Title Case names)
PERSON_PATTERNS = [
    r'^[A-Z][a-z]+\s+[A-Z][a-z]+',  # "John Smith"
    r'^[A-Z][a-z]+\s+[A-Z]\.?\s+[A-Z][a-z]+',  # "John D. Smith"
    r'^(Dr|Mr|Mrs|Ms|Prof)\.?\s+',  # Title prefix
]


def is_likely_person(name: str) -> bool:
    """
    Check if a name is likely a person (not an organization).

    Returns True if likely a person, False if likely an organization.
    """
    if not name or len(name.strip()) < 2:
        return False

    name_lower = name.lower().strip()
    name_original = name.strip()

    # Check for organization patterns
    for pattern in ORGANIZATION_PATTERNS:
        if re.search(pattern, name_lower, re.IGNORECASE):
            logger.debug(f"Rejected '{name}' as organization (matched: {pattern})")
            return False

    # Check for person patterns
    for pattern in PERSON_PATTERNS:
        if re.search(pattern, name_original):
            return True

    # Heuristic: Names with 2-4 words, each capitalized, are likely people
    words = name_original.split()
    if 2 <= len(words) <= 4:
        if all(word[0].isupper() for word in words if word):
            return True

    # Single word starting with capital might be a name, but uncertain
    if len(words) == 1 and name_original[0].isupper():
        return True  # Allow but could be flagged for review

    return False


def filter_people_only(stakeholders: list[dict]) -> list[dict]:
    """
    Filter a list of stakeholder dicts to only include people.

    Args:
        stakeholders: List of stakeholder extraction results

    Returns:
        Filtered list containing only likely people
    """
    filtered = []
    for sh in stakeholders:
        name = sh.get("name", "")
        if is_likely_person(name):
            filtered.append(sh)
        else:
            logger.info(f"Filtered out non-person stakeholder: '{name}'")

    return filtered
