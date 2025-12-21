"""Research report rendering for section-level chunking."""

import json
from typing import Any

from app.core.schemas_research import ResearchReport


def parse_json_maybe(value: Any) -> Any:
    """
    Parse a value as JSON if it's a string, otherwise return as-is.

    Args:
        value: Any value, possibly a JSON-encoded string

    Returns:
        Parsed JSON if value was a valid JSON string, otherwise original value
    """
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return value
    return value


# Fixed section order for deterministic rendering
SECTION_ORDER = [
    ("summary", "Executive Summary"),
    ("verdict", "Verdict"),
    ("idea_analysis", "Idea Analysis"),
    ("market_pain_points", "Market Pain Points"),
    ("feature_matrix", "Feature Matrix"),
    ("goals_and_benefits", "Goals and Benefits"),
    ("unique_selling_propositions", "Unique Selling Propositions"),
    ("user_personas", "User Personas"),
    ("risks_and_mitigations", "Risks and Mitigations"),
    ("additional_insights", "Additional Insights"),
    ("market_data", "Market Data"),
    ("next_steps", "Next Steps"),
]


def _render_value(value: Any, indent: int = 0) -> str:
    """
    Render a value to readable text format.

    Args:
        value: Any value (str, dict, list, etc.)
        indent: Indentation level

    Returns:
        Formatted text representation
    """
    prefix = "  " * indent

    if value is None:
        return ""

    if isinstance(value, str):
        return f"{prefix}{value}"

    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, dict):
                lines.append(_render_value(item, indent))
            else:
                lines.append(f"{prefix}- {item}")
        return "\n".join(lines)

    if isinstance(value, dict):
        lines = []
        for k, v in value.items():
            if v is None:
                continue
            if isinstance(v, str):
                lines.append(f"{prefix}{k}: {v}")
            elif isinstance(v, (list, dict)):
                lines.append(f"{prefix}{k}:")
                lines.append(_render_value(v, indent + 1))
            else:
                lines.append(f"{prefix}{k}: {v}")
        return "\n".join(lines)

    return f"{prefix}{value}"


def _render_section(section_key: str, section_title: str, value: Any) -> tuple[str, str] | None:
    """
    Render a single section.

    Args:
        section_key: Key for section metadata
        section_title: Human-readable section title
        value: Section content

    Returns:
        Tuple of (section_key, rendered_text) or None if empty
    """
    parsed = parse_json_maybe(value)

    if parsed is None:
        return None

    if isinstance(parsed, str) and not parsed.strip():
        return None

    rendered = _render_value(parsed)
    if not rendered.strip():
        return None

    text = f"## {section_title}\n\n{rendered}"
    return (section_key, text)


def render_research_report(report: ResearchReport) -> tuple[str, list[dict[str, Any]]]:
    """
    Render a research report to full text and section chunks.

    Args:
        report: ResearchReport to render

    Returns:
        Tuple of:
        - full_text: Complete rendered text
        - section_chunks: List of chunk dicts with content, start_char, end_char, metadata
    """
    sections = []
    full_parts = []

    # Add title header if present
    if report.title:
        header = f"# {report.title}\n\n"
        full_parts.append(header)

    current_pos = sum(len(p) for p in full_parts)

    # Render each section in fixed order
    for section_key, section_title in SECTION_ORDER:
        value = getattr(report, section_key, None)
        result = _render_section(section_key, section_title, value)

        if result is None:
            continue

        key, rendered = result
        start_char = current_pos
        end_char = current_pos + len(rendered)

        sections.append(
            {
                "content": rendered,
                "start_char": start_char,
                "end_char": end_char,
                "metadata": {"section": key},
            }
        )

        full_parts.append(rendered + "\n\n")
        current_pos = end_char + 2  # +2 for "\n\n"

    full_text = "".join(full_parts).strip()

    return full_text, sections
