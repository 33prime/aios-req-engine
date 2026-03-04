"""Canonical slug generation — single source of truth for feature/step slugs."""

import re


def canonical_slug(name: str) -> str:
    """Convert a name to a canonical kebab-case slug.

    Replaces all non-alphanumeric characters with hyphens, lowercases,
    and strips leading/trailing hyphens.
    """
    s = re.sub(r"[^a-z0-9]+", "-", name.lower().strip())
    return s.strip("-") or "unnamed"
