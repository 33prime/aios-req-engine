"""Shared helpers and constants used across workspace sub-modules."""

from pydantic import BaseModel

from app.core.schemas_brd import EvidenceItem


# ============================================================================
# Shared Helper Functions
# ============================================================================


def _clean_excerpt(text: str, max_length: int = 500) -> str:
    """Clean up an evidence excerpt: trim whitespace, truncate at sentence boundary."""
    text = text.strip()
    if not text:
        return text
    if len(text) <= max_length:
        return text
    # Try to truncate at a sentence boundary
    truncated = text[:max_length]
    # Look for the last sentence-ending punctuation
    for end_char in [". ", ".\n", "? ", "! "]:
        last_idx = truncated.rfind(end_char)
        if last_idx > max_length * 0.4:  # At least 40% of content preserved
            return truncated[: last_idx + 1].rstrip()
    # Fallback: truncate at last space
    last_space = truncated.rfind(" ")
    if last_space > max_length * 0.4:
        return truncated[:last_space].rstrip() + "..."
    return truncated.rstrip() + "..."


def _parse_evidence(raw: list | None) -> list[EvidenceItem]:
    """Parse raw evidence JSON into EvidenceItem models.

    Evidence may be stored with either 'excerpt' (features) or 'text' (drivers)
    as the key for the evidence text.
    """
    if not raw:
        return []
    items = []
    for e in raw:
        if isinstance(e, dict):
            # Evidence fields vary by source: 'excerpt' (project_launch), 'quote' (V2 pipeline), 'text' (legacy)
            excerpt = e.get("excerpt") or e.get("quote") or e.get("text") or ""
            excerpt = _clean_excerpt(excerpt)
            source_type = e.get("source_type") or e.get("fact_type") or ("signal" if e.get("chunk_id") else "inferred")
            rationale = e.get("rationale") or ""
            if not excerpt:
                continue  # Skip empty evidence
            items.append(EvidenceItem(
                chunk_id=e.get("chunk_id"),
                excerpt=excerpt,
                source_type=source_type,
                rationale=rationale,
            ))
    return items


# ============================================================================
# Shared Response Models
# ============================================================================


class ConfidenceGap(BaseModel):
    """A single completeness check item."""
    label: str
    category: str  # identity, detail, relationships, provenance, confirmation
    is_met: bool
    suggestion: str | None = None


# ============================================================================
# Shared Constants
# ============================================================================


# Table → (table_name, name_column) mapping for confidence inspector
CONFIDENCE_TABLE_MAP: dict[str, tuple[str, str]] = {
    "feature": ("features", "name"),
    "persona": ("personas", "name"),
    "vp_step": ("vp_steps", "label"),
    "business_driver": ("business_drivers", "description"),
    "constraint": ("constraints", "title"),
    "data_entity": ("data_entities", "name"),
    "stakeholder": ("stakeholders", "name"),
    "workflow": ("workflows", "name"),
}


# Table name for each entity type (used by batch confirm)
_ENTITY_TABLE_MAP = {
    "feature": "features",
    "persona": "personas",
    "vp_step": "vp_steps",
    "stakeholder": "stakeholders",
    "business_driver": "business_drivers",
    "workflow": "workflows",
    "data_entity": "data_entities",
    "constraint": "constraints",
    "competitor": "competitors",
}


# ============================================================================
# Completeness Computation
# ============================================================================


def _compute_completeness(entity_type: str, entity: dict) -> list[ConfidenceGap]:
    """Compute completeness check items for an entity."""
    checks: list[tuple[str, str, str, bool]] = []  # (label, category, suggestion, is_met)

    if entity_type == "feature":
        checks = [
            ("Has name", "identity", "Add a descriptive name", bool(entity.get("name"))),
            ("Has description", "detail", "Add an overview describing the feature", bool(entity.get("overview"))),
            ("Has acceptance criteria", "detail", "Define acceptance criteria", bool(entity.get("acceptance_criteria"))),
            ("Priority assigned", "detail", "Assign a MoSCoW priority group", bool(entity.get("priority_group"))),
            ("Target personas linked", "relationships", "Link personas who benefit from this feature", len(entity.get("target_personas") or []) > 0),
            ("Has signal evidence", "provenance", "Process a signal that mentions this feature", len(entity.get("evidence") or []) > 0),
            ("Confirmed by consultant or client", "confirmation", "Review and confirm this feature", entity.get("confirmation_status") in ("confirmed_consultant", "confirmed_client")),
            ("Not stale", "confirmation", "Refresh this entity to clear stale status", not entity.get("is_stale")),
        ]
    elif entity_type == "persona":
        checks = [
            ("Has name", "identity", "Add a persona name", bool(entity.get("name"))),
            ("Has role", "identity", "Add the persona's role or title", bool(entity.get("role"))),
            ("Has goals", "detail", "Add goals this persona wants to achieve", len(entity.get("goals") or []) > 0),
            ("Has pain points", "detail", "Add pain points this persona experiences", len(entity.get("pain_points") or []) > 0),
            ("Has description", "detail", "Add a description of this persona", bool(entity.get("description"))),
            ("Has signal evidence", "provenance", "Process a signal that mentions this persona", len(entity.get("evidence") or []) > 0),
            ("Confirmed by consultant or client", "confirmation", "Review and confirm this persona", entity.get("confirmation_status") in ("confirmed_consultant", "confirmed_client")),
            ("Not stale", "confirmation", "Refresh this entity to clear stale status", not entity.get("is_stale")),
        ]
    elif entity_type == "vp_step":
        checks = [
            ("Has label", "identity", "Add a step label", bool(entity.get("label"))),
            ("Has description", "detail", "Add a description of this step", bool(entity.get("description"))),
            ("Actor assigned", "relationships", "Assign a persona to this step", bool(entity.get("actor_persona_id"))),
            ("Has signal evidence", "provenance", "Process a signal that mentions this step", len(entity.get("evidence") or []) > 0),
            ("Confirmed", "confirmation", "Review and confirm this step", entity.get("confirmation_status") in ("confirmed_consultant", "confirmed_client")),
            ("Not stale", "confirmation", "Refresh this entity to clear stale status", not entity.get("is_stale")),
        ]
    elif entity_type == "business_driver":
        checks = [
            ("Has description", "identity", "Add a description", bool(entity.get("description"))),
            ("Has evidence", "provenance", "Process a signal that supports this driver", len(entity.get("evidence") or []) > 0),
            ("Confirmed", "confirmation", "Review and confirm this driver", entity.get("confirmation_status") in ("confirmed_consultant", "confirmed_client")),
        ]
        dtype = entity.get("driver_type")
        if dtype == "pain":
            checks.append(("Has business impact", "detail", "Describe the business impact", bool(entity.get("business_impact"))))
            checks.append(("Has severity", "detail", "Set a severity level", bool(entity.get("severity"))))
        elif dtype == "goal":
            checks.append(("Has success criteria", "detail", "Define success criteria", bool(entity.get("success_criteria"))))
        elif dtype == "kpi":
            checks.append(("Has baseline value", "detail", "Set a baseline measurement", bool(entity.get("baseline_value"))))
            checks.append(("Has target value", "detail", "Set a target value", bool(entity.get("target_value"))))
            checks.append(("Has measurement method", "detail", "Define how to measure this KPI", bool(entity.get("measurement_method"))))
    elif entity_type == "data_entity":
        checks = [
            ("Has name", "identity", "Add a name", bool(entity.get("name"))),
            ("Has description", "detail", "Add a description", bool(entity.get("description"))),
            ("Has fields defined", "detail", "Add field definitions", len(entity.get("fields") or []) > 0),
            ("Has evidence", "provenance", "Process a signal that mentions this entity", len(entity.get("evidence") or []) > 0),
            ("Confirmed", "confirmation", "Review and confirm", entity.get("confirmation_status") in ("confirmed_consultant", "confirmed_client")),
            ("Not stale", "confirmation", "Refresh to clear stale status", not entity.get("is_stale")),
        ]
    elif entity_type == "stakeholder":
        checks = [
            ("Has name", "identity", "Add a name", bool(entity.get("name"))),
            ("Has role", "identity", "Add a role or title", bool(entity.get("role"))),
            ("Has email", "detail", "Add contact email", bool(entity.get("email"))),
            ("Stakeholder type set", "detail", "Set stakeholder type (champion, sponsor, etc.)", bool(entity.get("stakeholder_type"))),
            ("Influence level set", "detail", "Set influence level", bool(entity.get("influence_level"))),
            ("Has evidence", "provenance", "Process a signal that mentions this stakeholder", len(entity.get("evidence") or []) > 0),
            ("Confirmed", "confirmation", "Review and confirm", entity.get("confirmation_status") in ("confirmed_consultant", "confirmed_client")),
        ]
    elif entity_type == "constraint":
        checks = [
            ("Has title", "identity", "Add a title", bool(entity.get("title"))),
            ("Has description", "detail", "Add a description", bool(entity.get("description"))),
            ("Constraint type set", "detail", "Set constraint type", bool(entity.get("constraint_type"))),
            ("Has evidence", "provenance", "Process a signal that mentions this constraint", len(entity.get("evidence") or []) > 0),
            ("Confirmed", "confirmation", "Review and confirm", entity.get("confirmation_status") in ("confirmed_consultant", "confirmed_client")),
        ]
    elif entity_type == "workflow":
        checks = [
            ("Has name", "identity", "Add a name", bool(entity.get("name"))),
            ("Has description", "detail", "Add a description", bool(entity.get("description"))),
            ("Confirmed", "confirmation", "Review and confirm", entity.get("confirmation_status") in ("confirmed_consultant", "confirmed_client")),
        ]

    return [
        ConfidenceGap(label=label, category=cat, is_met=met, suggestion=None if met else sug)
        for label, cat, sug, met in checks
    ]
