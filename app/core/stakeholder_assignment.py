"""AIOS Stakeholder Assignment Recommendation Engine.

Scores stakeholders for entity assignments based on:
- Topic match (+40) — entity content keywords vs TOPIC_ROLE_MAP
- Expertise overlap (+30) — domain_expertise vs entity topics
- Influence level (+20/10/5) — high/medium/low
- Stakeholder type bonus (+10) — decision_maker or primary_contact

Uses existing find_stakeholders_by_expertise() and TOPIC_ROLE_MAP.
"""

from uuid import UUID

from app.agents.stakeholder_suggester import TOPIC_ROLE_MAP
from app.core.logging import get_logger
from app.db.stakeholder_assignments import (
    bulk_create_assignments,
    list_assignments,
)
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

# Entity types that support validation assignments
ASSIGNABLE_ENTITY_TYPES = [
    "workflow",
    "business_driver",
    "feature",
    "persona",
    "vp_step",
    "prototype_epic",
]

# Influence level scores
INFLUENCE_SCORES = {"high": 20, "medium": 10, "low": 5}

# Stakeholder types that get a bonus
TYPE_BONUS = {"decision_maker": 10, "primary_contact": 10}


def _extract_topics(entity_content: str) -> list[str]:
    """Extract matching topics from entity text content."""
    text_lower = entity_content.lower()
    matched = []
    for topic in TOPIC_ROLE_MAP:
        if topic in text_lower:
            matched.append(topic)
    return matched


def _score_stakeholder(stakeholder: dict, topics: list[str]) -> tuple[int, str]:
    """Score a single stakeholder for relevance to topics.

    Returns (score, reason).
    """
    score = 0
    reasons = []

    # Topic match — check if stakeholder's role matches TOPIC_ROLE_MAP roles
    role = (stakeholder.get("role") or "").lower()
    for topic in topics:
        topic_roles = TOPIC_ROLE_MAP.get(topic, [])
        for expected_role in topic_roles:
            if expected_role.lower() in role or role in expected_role.lower():
                score += 40
                reasons.append(f"Role matches {topic}")
                break

    # Expertise overlap — check domain_expertise against topics
    expertise = stakeholder.get("domain_expertise") or []
    for exp in expertise:
        exp_lower = exp.lower()
        for topic in topics:
            if topic in exp_lower or exp_lower in topic:
                score += 30
                reasons.append(f"Expertise in {exp}")
                break

    # Topic mention frequency — bonus for prior discussion
    topic_mentions = stakeholder.get("topic_mentions") or {}
    for topic in topics:
        count = topic_mentions.get(topic, 0)
        if count > 0:
            score += min(count * 5, 20)
            reasons.append(f"Mentioned {topic} {count}x")

    # Influence level
    influence = (stakeholder.get("influence_level") or "medium").lower()
    score += INFLUENCE_SCORES.get(influence, 5)

    # Stakeholder type bonus
    stype = (stakeholder.get("stakeholder_type") or "").lower()
    score += TYPE_BONUS.get(stype, 0)

    reason = "; ".join(reasons[:3]) if reasons else "General stakeholder"
    return score, reason


def recommend_assignments(
    project_id: UUID,
    entity_type: str,
    entity_id: str,
    entity_content: str,
    top_n: int = 3,
) -> list[dict]:
    """Score stakeholders for one entity, return top N recommendations.

    Returns list of dicts ready for bulk_create_assignments.
    """
    client = get_supabase()
    result = (
        client.table("stakeholders")
        .select("*")
        .eq("project_id", str(project_id))
        .execute()
    )
    stakeholders = result.data or []
    if not stakeholders:
        return []

    topics = _extract_topics(entity_content)
    if not topics:
        # Fall back to using entity_type as topic
        topics = [entity_type.replace("_", " ")]

    scored = []
    for sh in stakeholders:
        score, reason = _score_stakeholder(sh, topics)
        if score > 0:
            scored.append((sh, score, reason))

    scored.sort(key=lambda x: x[1], reverse=True)

    assignments = []
    for sh, score, reason in scored[:top_n]:
        priority = 1 if score >= 60 else 2 if score >= 30 else 3
        assignments.append({
            "project_id": str(project_id),
            "stakeholder_id": sh["id"],
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "assignment_type": "validate",
            "source": "ai",
            "priority": priority,
            "reason": reason,
        })

    return assignments


def bulk_recommend_assignments(
    project_id: UUID,
    entity_types: list[str] | None = None,
) -> int:
    """Generate assignments for all unassigned entities in a project.

    Returns number of assignments created.
    """
    types = entity_types or ASSIGNABLE_ENTITY_TYPES
    client = get_supabase()

    # Get existing assignments to skip already-assigned entities
    existing = list_assignments(project_id)
    assigned_keys = {
        (a["entity_type"], a["entity_id"]) for a in existing
    }

    all_assignments = []

    for etype in types:
        entities = _load_entities(client, project_id, etype)
        for entity in entities:
            eid = str(entity["id"])
            if (etype, eid) in assigned_keys:
                continue
            content = _entity_to_text(entity, etype)
            recs = recommend_assignments(project_id, etype, eid, content)
            all_assignments.extend(recs)

    if all_assignments:
        created = bulk_create_assignments(all_assignments)
        logger.info(
            f"Created {len(created)} assignments for project {project_id}"
        )
        return len(created)
    return 0


def _load_entities(client, project_id: UUID, entity_type: str) -> list[dict]:
    """Load entities of a given type for a project."""
    table_map = {
        "workflow": "workflows",
        "business_driver": "business_drivers",
        "feature": "features",
        "persona": "personas",
        "vp_step": "vp_steps",
        "prototype_epic": "prototype_epic_confirmations",
    }
    table = table_map.get(entity_type)
    if not table:
        return []

    try:
        result = (
            client.table(table)
            .select("*")
            .eq("project_id", str(project_id))
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.warning(f"Failed to load {entity_type}: {e}")
        return []


def _entity_to_text(entity: dict, entity_type: str) -> str:
    """Convert an entity to searchable text for topic matching."""
    parts = []
    for field in ["name", "title", "description", "summary", "overview", "content"]:
        val = entity.get(field)
        if val:
            parts.append(str(val))
    if not parts:
        parts.append(entity_type.replace("_", " "))
    return " ".join(parts)


def get_user_stakeholder(project_id: UUID, user_id: UUID) -> dict | None:
    """Get the stakeholder linked to a user in a project."""
    client = get_supabase()
    result = (
        client.table("stakeholders")
        .select("*")
        .eq("project_id", str(project_id))
        .eq("user_id", str(user_id))
        .maybe_single()
        .execute()
    )
    return result.data
