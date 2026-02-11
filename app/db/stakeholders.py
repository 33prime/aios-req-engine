"""Database operations for stakeholders table."""

from datetime import datetime, timezone
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def list_stakeholders(project_id: UUID) -> list[dict]:
    """
    List all stakeholders for a project.

    Args:
        project_id: Project UUID

    Returns:
        List of stakeholder dicts
    """
    supabase = get_supabase()

    response = (
        supabase.table("stakeholders")
        .select("*")
        .eq("project_id", str(project_id))
        .order("created_at", desc=False)
        .execute()
    )

    return response.data


def list_stakeholders_by_type(
    project_id: UUID,
    stakeholder_type: str,
) -> list[dict]:
    """
    List stakeholders of a specific type for a project.

    Args:
        project_id: Project UUID
        stakeholder_type: Type (champion, sponsor, blocker, influencer, end_user)

    Returns:
        List of stakeholder dicts
    """
    supabase = get_supabase()

    response = (
        supabase.table("stakeholders")
        .select("*")
        .eq("project_id", str(project_id))
        .eq("stakeholder_type", stakeholder_type)
        .order("influence_level", desc=True)
        .execute()
    )

    return response.data


def get_stakeholder(stakeholder_id: UUID) -> dict | None:
    """
    Get a single stakeholder by ID.

    Args:
        stakeholder_id: Stakeholder UUID

    Returns:
        Stakeholder dict or None if not found
    """
    supabase = get_supabase()

    response = (
        supabase.table("stakeholders")
        .select("*")
        .eq("id", str(stakeholder_id))
        .maybe_single()
        .execute()
    )

    return response.data


def create_stakeholder(
    project_id: UUID,
    name: str,
    stakeholder_type: str,
    email: str | None = None,
    role: str | None = None,
    organization: str | None = None,
    influence_level: str = "medium",
    priorities: list[str] | None = None,
    concerns: list[str] | None = None,
    notes: str | None = None,
    linked_persona_id: UUID | None = None,
    evidence: list | None = None,
    confirmation_status: str = "ai_generated",
    first_name: str | None = None,
    last_name: str | None = None,
) -> dict:
    """
    Create a new stakeholder.

    Args:
        project_id: Project UUID
        name: Stakeholder name
        stakeholder_type: Type (champion, sponsor, blocker, influencer, end_user)
        email: Contact email
        role: Job title/role
        organization: Company/department
        influence_level: Influence level (high, medium, low)
        priorities: What matters to them
        concerns: Their worries/objections
        notes: Additional notes
        linked_persona_id: Optional linked persona UUID
        evidence: List of evidence dicts
        confirmation_status: Confirmation status

    Returns:
        Created stakeholder dict
    """
    supabase = get_supabase()

    stakeholder_data = {
        "project_id": str(project_id),
        "name": name,
        "stakeholder_type": stakeholder_type,
        "role": role,
        "organization": organization,
        "influence_level": influence_level,
        "priorities": priorities or [],
        "concerns": concerns or [],
        "notes": notes,
        "linked_persona_id": str(linked_persona_id) if linked_persona_id else None,
        "evidence": evidence or [],
        "confirmation_status": confirmation_status,
    }
    # Only add email if provided (column may not exist in older schemas)
    if email:
        stakeholder_data["email"] = email
    if first_name is not None:
        stakeholder_data["first_name"] = first_name
    if last_name is not None:
        stakeholder_data["last_name"] = last_name

    response = (
        supabase.table("stakeholders")
        .insert(stakeholder_data)
        .execute()
    )

    logger.info(
        f"Created stakeholder '{name}' ({stakeholder_type}) for project {project_id}",
        extra={"project_id": str(project_id), "stakeholder_type": stakeholder_type},
    )

    return response.data[0]


def update_stakeholder(
    stakeholder_id: UUID,
    updates: dict,
) -> dict:
    """
    Update a stakeholder.

    Args:
        stakeholder_id: Stakeholder UUID
        updates: Dict of fields to update

    Returns:
        Updated stakeholder dict
    """
    supabase = get_supabase()

    # Convert UUID fields to strings if present
    if "linked_persona_id" in updates and updates["linked_persona_id"]:
        updates["linked_persona_id"] = str(updates["linked_persona_id"])

    # Add updated_at timestamp
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    response = (
        supabase.table("stakeholders")
        .update(updates)
        .eq("id", str(stakeholder_id))
        .execute()
    )

    if not response.data:
        raise ValueError(f"Stakeholder not found: {stakeholder_id}")

    logger.info(
        f"Updated stakeholder {stakeholder_id}",
        extra={"stakeholder_id": str(stakeholder_id), "fields": list(updates.keys())},
    )

    return response.data[0]


def update_stakeholder_status(
    stakeholder_id: UUID,
    status: str,
    confirmed_by: UUID | None = None,
) -> dict:
    """
    Update confirmation status for a stakeholder.

    Args:
        stakeholder_id: Stakeholder UUID
        status: New confirmation status
        confirmed_by: User UUID who confirmed

    Returns:
        Updated stakeholder dict
    """
    updates = {
        "confirmation_status": status,
        "confirmed_by": str(confirmed_by) if confirmed_by else None,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
    }

    return update_stakeholder(stakeholder_id, updates)


def delete_stakeholder(stakeholder_id: UUID) -> bool:
    """
    Delete a stakeholder.

    Args:
        stakeholder_id: Stakeholder UUID

    Returns:
        True if deleted successfully
    """
    supabase = get_supabase()

    response = (
        supabase.table("stakeholders")
        .delete()
        .eq("id", str(stakeholder_id))
        .execute()
    )

    logger.info(
        f"Deleted stakeholder {stakeholder_id}",
        extra={"stakeholder_id": str(stakeholder_id)},
    )

    return True


def upsert_stakeholder(
    project_id: UUID,
    name: str,
    stakeholder_type: str,
    email: str | None = None,
    role: str | None = None,
    organization: str | None = None,
    influence_level: str = "medium",
    priorities: list[str] | None = None,
    concerns: list[str] | None = None,
    notes: str | None = None,
    linked_persona_id: UUID | None = None,
    evidence: list | None = None,
    confirmation_status: str = "ai_generated",
) -> dict:
    """
    Upsert a stakeholder (insert or update by project_id + name + stakeholder_type).

    If a stakeholder with the same name and type exists, update it.
    Otherwise, create a new one.

    Args:
        Same as create_stakeholder

    Returns:
        Created or updated stakeholder dict
    """
    supabase = get_supabase()

    # Check if stakeholder exists
    existing = (
        supabase.table("stakeholders")
        .select("id")
        .eq("project_id", str(project_id))
        .eq("name", name)
        .eq("stakeholder_type", stakeholder_type)
        .maybe_single()
        .execute()
    )

    if existing.data:
        # Update existing
        updates = {
            "role": role,
            "organization": organization,
            "influence_level": influence_level,
            "priorities": priorities or [],
            "concerns": concerns or [],
            "notes": notes,
            "linked_persona_id": str(linked_persona_id) if linked_persona_id else None,
            "evidence": evidence or [],
            "confirmation_status": confirmation_status,
        }
        # Only add email if provided (column may not exist in older schemas)
        if email:
            updates["email"] = email
        return update_stakeholder(UUID(existing.data["id"]), updates)
    else:
        # Create new
        return create_stakeholder(
            project_id=project_id,
            name=name,
            stakeholder_type=stakeholder_type,
            email=email,
            role=role,
            organization=organization,
            influence_level=influence_level,
            priorities=priorities,
            concerns=concerns,
            notes=notes,
            linked_persona_id=linked_persona_id,
            evidence=evidence,
            confirmation_status=confirmation_status,
        )


def get_stakeholders_grouped(project_id: UUID) -> dict[str, list[dict]]:
    """
    Get stakeholders grouped by type.

    Args:
        project_id: Project UUID

    Returns:
        Dict mapping stakeholder_type to list of stakeholders
    """
    stakeholders = list_stakeholders(project_id)

    grouped = {
        "champion": [],
        "sponsor": [],
        "blocker": [],
        "influencer": [],
        "end_user": [],
    }

    for sh in stakeholders:
        sh_type = sh.get("stakeholder_type", "influencer")
        if sh_type in grouped:
            grouped[sh_type].append(sh)

    return grouped


def get_high_influence_stakeholders(project_id: UUID) -> list[dict]:
    """
    Get all high-influence stakeholders for a project.

    Args:
        project_id: Project UUID

    Returns:
        List of high-influence stakeholder dicts
    """
    supabase = get_supabase()

    response = (
        supabase.table("stakeholders")
        .select("*")
        .eq("project_id", str(project_id))
        .eq("influence_level", "high")
        .order("stakeholder_type")
        .execute()
    )

    return response.data


def link_stakeholder_to_persona(
    stakeholder_id: UUID,
    persona_id: UUID,
) -> dict:
    """
    Link a stakeholder to a persona.

    Args:
        stakeholder_id: Stakeholder UUID
        persona_id: Persona UUID to link

    Returns:
        Updated stakeholder dict
    """
    return update_stakeholder(stakeholder_id, {"linked_persona_id": str(persona_id)})


def unlink_stakeholder_from_persona(stakeholder_id: UUID) -> dict:
    """
    Remove persona link from a stakeholder.

    Args:
        stakeholder_id: Stakeholder UUID

    Returns:
        Updated stakeholder dict
    """
    supabase = get_supabase()

    response = (
        supabase.table("stakeholders")
        .update({
            "linked_persona_id": None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", str(stakeholder_id))
        .execute()
    )

    if not response.data:
        raise ValueError(f"Stakeholder not found: {stakeholder_id}")

    return response.data[0]


def add_stakeholder_concern(
    stakeholder_id: UUID,
    concern: str,
) -> dict:
    """
    Add a concern to a stakeholder.

    Args:
        stakeholder_id: Stakeholder UUID
        concern: Concern text to add

    Returns:
        Updated stakeholder dict
    """
    stakeholder = get_stakeholder(stakeholder_id)
    if not stakeholder:
        raise ValueError(f"Stakeholder not found: {stakeholder_id}")

    concerns = stakeholder.get("concerns", []) or []
    if concern not in concerns:
        concerns.append(concern)

    return update_stakeholder(stakeholder_id, {"concerns": concerns})


def add_stakeholder_priority(
    stakeholder_id: UUID,
    priority: str,
) -> dict:
    """
    Add a priority to a stakeholder.

    Args:
        stakeholder_id: Stakeholder UUID
        priority: Priority text to add

    Returns:
        Updated stakeholder dict
    """
    stakeholder = get_stakeholder(stakeholder_id)
    if not stakeholder:
        raise ValueError(f"Stakeholder not found: {stakeholder_id}")

    priorities = stakeholder.get("priorities", []) or []
    if priority not in priorities:
        priorities.append(priority)

    return update_stakeholder(stakeholder_id, {"priorities": priorities})


# ============================================================================
# New functions for signal pipeline integration
# ============================================================================


def set_primary_contact(
    project_id: UUID,
    stakeholder_id: UUID,
) -> dict:
    """
    Set a stakeholder as primary contact, unsetting any existing primary.

    Args:
        project_id: Project UUID
        stakeholder_id: Stakeholder UUID to make primary

    Returns:
        Updated stakeholder dict
    """
    supabase = get_supabase()

    # Unset existing primary contacts
    supabase.table("stakeholders").update(
        {"is_primary_contact": False}
    ).eq("project_id", str(project_id)).eq("is_primary_contact", True).execute()

    # Set new primary
    response = (
        supabase.table("stakeholders")
        .update({
            "is_primary_contact": True,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", str(stakeholder_id))
        .execute()
    )

    if not response.data:
        raise ValueError(f"Stakeholder not found: {stakeholder_id}")

    logger.info(f"Set stakeholder {stakeholder_id} as primary contact for project {project_id}")
    return response.data[0]


def get_primary_contacts(project_id: UUID) -> list[dict]:
    """
    Get primary contact(s) for a project.

    Args:
        project_id: Project UUID

    Returns:
        List of primary contact stakeholder dicts
    """
    supabase = get_supabase()

    response = (
        supabase.table("stakeholders")
        .select("*")
        .eq("project_id", str(project_id))
        .eq("is_primary_contact", True)
        .execute()
    )

    return response.data


def update_domain_expertise(
    stakeholder_id: UUID,
    expertise_areas: list[str],
    append: bool = True,
) -> dict:
    """
    Update domain expertise for a stakeholder.

    Args:
        stakeholder_id: Stakeholder UUID
        expertise_areas: List of expertise areas to add
        append: If True, append to existing. If False, replace.

    Returns:
        Updated stakeholder dict
    """
    stakeholder = get_stakeholder(stakeholder_id)
    if not stakeholder:
        raise ValueError(f"Stakeholder not found: {stakeholder_id}")

    if append:
        existing = stakeholder.get("domain_expertise", []) or []
        # Add new areas, avoiding duplicates
        expertise_areas = list(set(existing + expertise_areas))

    return update_stakeholder(stakeholder_id, {"domain_expertise": expertise_areas})


def update_topic_mentions(
    stakeholder_id: UUID,
    topics: list[str],
) -> dict:
    """
    Increment topic mention counts for a stakeholder.

    Args:
        stakeholder_id: Stakeholder UUID
        topics: List of topics mentioned

    Returns:
        Updated stakeholder dict
    """
    stakeholder = get_stakeholder(stakeholder_id)
    if not stakeholder:
        raise ValueError(f"Stakeholder not found: {stakeholder_id}")

    topic_mentions = stakeholder.get("topic_mentions", {}) or {}

    for topic in topics:
        topic_lower = topic.lower().strip()
        if topic_lower:
            topic_mentions[topic_lower] = topic_mentions.get(topic_lower, 0) + 1

    return update_stakeholder(stakeholder_id, {"topic_mentions": topic_mentions})


def add_mentioned_in_signal(
    stakeholder_id: UUID,
    signal_id: UUID,
) -> dict:
    """
    Add a signal to the stakeholder's mentioned_in_signals array.

    Args:
        stakeholder_id: Stakeholder UUID
        signal_id: Signal UUID where they were mentioned

    Returns:
        Updated stakeholder dict
    """
    stakeholder = get_stakeholder(stakeholder_id)
    if not stakeholder:
        raise ValueError(f"Stakeholder not found: {stakeholder_id}")

    mentioned_in = stakeholder.get("mentioned_in_signals", []) or []
    signal_str = str(signal_id)
    if signal_str not in mentioned_in:
        mentioned_in.append(signal_str)

    return update_stakeholder(stakeholder_id, {"mentioned_in_signals": mentioned_in})


def find_stakeholders_by_expertise(
    project_id: UUID,
    topics: list[str],
    limit: int = 5,
) -> list[dict]:
    """
    Find stakeholders who might know about given topics.

    Matches by:
    1. Domain expertise overlap
    2. Topic mention frequency

    Args:
        project_id: Project UUID
        topics: Topics to match
        limit: Max stakeholders to return

    Returns:
        List of stakeholder dicts with match scores, sorted by relevance
    """
    supabase = get_supabase()

    # Get all stakeholders for project
    response = (
        supabase.table("stakeholders")
        .select("*")
        .eq("project_id", str(project_id))
        .execute()
    )

    stakeholders = response.data or []
    topics_lower = [t.lower().strip() for t in topics if t]

    scored_stakeholders = []
    for sh in stakeholders:
        score = 0
        matches = []

        # Check domain expertise
        expertise = sh.get("domain_expertise", []) or []
        for topic in topics_lower:
            for exp in expertise:
                if topic in exp.lower() or exp.lower() in topic:
                    score += 10
                    matches.append(f"expertise:{exp}")

        # Check topic mentions
        topic_mentions = sh.get("topic_mentions", {}) or {}
        for topic in topics_lower:
            if topic in topic_mentions:
                mention_count = topic_mentions[topic]
                score += mention_count * 2
                matches.append(f"mentioned:{topic}({mention_count}x)")

        # Check role relevance (simple keyword match)
        role = (sh.get("role") or "").lower()
        for topic in topics_lower:
            if topic in role:
                score += 5
                matches.append(f"role:{role}")

        if score > 0:
            scored_stakeholders.append({
                **sh,
                "_match_score": score,
                "_match_reasons": matches,
            })

    # Sort by score descending
    scored_stakeholders.sort(key=lambda x: x["_match_score"], reverse=True)

    return scored_stakeholders[:limit]


def create_stakeholder_from_signal(
    project_id: UUID,
    name: str,
    role: str | None = None,
    email: str | None = None,
    domain_expertise: list[str] | None = None,
    source_type: str = "mentioned",
    extracted_from_signal_id: UUID | None = None,
    is_direct_participant: bool = False,
) -> dict:
    """
    Create a stakeholder extracted from a signal.

    Args:
        project_id: Project UUID
        name: Stakeholder name
        role: Job title/role
        email: Email address
        domain_expertise: Areas of expertise
        source_type: 'direct_participant' or 'mentioned'
        extracted_from_signal_id: Signal that identified this stakeholder
        is_direct_participant: If True, set status to 'confirmed'

    Returns:
        Created stakeholder dict
    """
    supabase = get_supabase()

    # Determine confirmation status based on source type
    if is_direct_participant:
        confirmation_status = "confirmed_consultant"
        source_type = "direct_participant"
    else:
        confirmation_status = "ai_generated"
        source_type = source_type or "mentioned"

    # Check for existing stakeholder with same name
    existing = (
        supabase.table("stakeholders")
        .select("id")
        .eq("project_id", str(project_id))
        .ilike("name", name)
        .maybe_single()
        .execute()
    )

    if existing.data:
        # Update existing stakeholder
        updates = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if role:
            updates["role"] = role
        if email:
            updates["email"] = email
        if domain_expertise:
            sh = get_stakeholder(UUID(existing.data["id"]))
            existing_expertise = sh.get("domain_expertise", []) or []
            updates["domain_expertise"] = list(set(existing_expertise + domain_expertise))
        if extracted_from_signal_id:
            sh = get_stakeholder(UUID(existing.data["id"]))
            mentioned_in = sh.get("mentioned_in_signals", []) or []
            if str(extracted_from_signal_id) not in mentioned_in:
                mentioned_in.append(str(extracted_from_signal_id))
            updates["mentioned_in_signals"] = mentioned_in

        return update_stakeholder(UUID(existing.data["id"]), updates)

    # Create new stakeholder
    stakeholder_data = {
        "project_id": str(project_id),
        "name": name,
        "role": role,
        "email": email,
        "domain_expertise": domain_expertise or [],
        "source_type": source_type,
        "confirmation_status": confirmation_status,
        "extracted_from_signal_id": str(extracted_from_signal_id) if extracted_from_signal_id else None,
        "mentioned_in_signals": [str(extracted_from_signal_id)] if extracted_from_signal_id else [],
        "stakeholder_type": "influencer",  # Default type
        "influence_level": "medium",
    }

    response = supabase.table("stakeholders").insert(stakeholder_data).execute()

    if not response or not response.data:
        logger.error(
            f"Failed to create stakeholder '{name}': no data returned",
            extra={"project_id": str(project_id), "stakeholder_data": stakeholder_data},
        )
        raise ValueError(f"Failed to create stakeholder '{name}'")

    logger.info(
        f"Created stakeholder '{name}' from signal for project {project_id}",
        extra={
            "project_id": str(project_id),
            "source_type": source_type,
            "signal_id": str(extracted_from_signal_id) if extracted_from_signal_id else None,
        },
    )

    return response.data[0]


def suggest_stakeholders_for_confirmation(
    project_id: UUID,
    entity_type: str,
    entity_topics: list[str],
    gap_description: str | None = None,
) -> list[dict]:
    """
    Suggest stakeholders who could help confirm an entity.

    This is the "Who Would Know" feature.

    Args:
        project_id: Project UUID
        entity_type: Type of entity needing confirmation
        entity_topics: Topics/keywords from the entity
        gap_description: Optional description of what needs confirmation

    Returns:
        List of suggested stakeholders with reasoning
    """
    # Find stakeholders by expertise match
    matches = find_stakeholders_by_expertise(project_id, entity_topics, limit=3)

    suggestions = []
    for sh in matches:
        suggestion = {
            "stakeholder_id": sh["id"],
            "stakeholder_name": sh["name"],
            "role": sh.get("role"),
            "match_score": sh.get("_match_score", 0),
            "reasons": sh.get("_match_reasons", []),
            "is_primary_contact": sh.get("is_primary_contact", False),
        }

        # Build human-readable suggestion
        reasons = sh.get("_match_reasons", [])
        if reasons:
            suggestion["suggestion_text"] = f"{sh['name']}"
            if sh.get("role"):
                suggestion["suggestion_text"] += f" ({sh['role']})"
            suggestion["suggestion_text"] += f" - {', '.join(reasons[:2])}"

        suggestions.append(suggestion)

    return suggestions


# ============================================================================
# User Linking Functions
# ============================================================================


def link_stakeholder_to_user(
    stakeholder_id: UUID,
    user_id: UUID,
) -> dict:
    """
    Link a stakeholder to a user account.

    Args:
        stakeholder_id: Stakeholder UUID
        user_id: User UUID to link

    Returns:
        Updated stakeholder dict
    """
    return update_stakeholder(stakeholder_id, {"linked_user_id": str(user_id)})


def link_stakeholder_to_project_member(
    stakeholder_id: UUID,
    project_member_id: UUID,
) -> dict:
    """
    Link a stakeholder to a project member.

    Args:
        stakeholder_id: Stakeholder UUID
        project_member_id: Project member UUID to link

    Returns:
        Updated stakeholder dict
    """
    return update_stakeholder(stakeholder_id, {"linked_project_member_id": str(project_member_id)})


def find_stakeholder_by_email(
    project_id: UUID,
    email: str,
) -> dict | None:
    """
    Find a stakeholder by email address.

    Args:
        project_id: Project UUID
        email: Email to search for

    Returns:
        Stakeholder dict or None if not found
    """
    supabase = get_supabase()

    response = (
        supabase.table("stakeholders")
        .select("*")
        .eq("project_id", str(project_id))
        .ilike("email", email)
        .maybe_single()
        .execute()
    )

    return response.data


def auto_link_project_members_to_stakeholders(project_id: UUID) -> int:
    """
    Automatically link project members to stakeholders by email match.

    Args:
        project_id: Project UUID

    Returns:
        Number of stakeholders linked
    """
    supabase = get_supabase()

    # Get all stakeholders with emails
    stakeholders = (
        supabase.table("stakeholders")
        .select("id, email")
        .eq("project_id", str(project_id))
        .not_.is_("email", "null")
        .is_("linked_user_id", "null")
        .execute()
    ).data or []

    if not stakeholders:
        return 0

    # Get project members with emails
    # Use explicit FK relationship since project_members has two FKs to users (user_id, invited_by)
    project_members = (
        supabase.table("project_members")
        .select("id, user_id, users!project_members_user_id_fkey(email)")
        .eq("project_id", str(project_id))
        .execute()
    ).data or []

    # Build email to member map
    email_to_member = {}
    for pm in project_members:
        user_info = pm.get("users")
        if user_info and user_info.get("email"):
            email_to_member[user_info["email"].lower()] = {
                "user_id": pm.get("user_id"),
                "project_member_id": pm.get("id"),
            }

    # Link stakeholders
    linked_count = 0
    for sh in stakeholders:
        email = sh.get("email", "").lower()
        if email and email in email_to_member:
            member_info = email_to_member[email]
            update_stakeholder(
                UUID(sh["id"]),
                {
                    "linked_user_id": member_info["user_id"],
                    "linked_project_member_id": member_info["project_member_id"],
                }
            )
            linked_count += 1
            logger.info(f"Linked stakeholder {sh['id']} to user {member_info['user_id']}")

    return linked_count


def find_similar_stakeholder(
    project_id: UUID,
    name: str,
    email: str | None = None,
    stakeholder_type: str | None = None,
    threshold: float = 0.8,
) -> dict | None:
    """
    Find a similar stakeholder by name or email (upgraded for Task #13).

    Args:
        project_id: Project UUID
        name: Name to match
        email: Optional email to match (takes priority)
        stakeholder_type: Optional filter by type
        threshold: Similarity threshold

    Returns:
        Most similar stakeholder or None
    """
    from app.core.similarity import SimilarityMatcher, ThresholdConfig
    from app.core.state_snapshot import invalidate_snapshot

    # First try email match (exact)
    if email:
        by_email = find_stakeholder_by_email(project_id, email)
        if by_email:
            return by_email

    # Then use multi-strategy name matching
    supabase = get_supabase()

    query = (
        supabase.table("stakeholders")
        .select("*")
        .eq("project_id", str(project_id))
    )

    if stakeholder_type:
        query = query.eq("stakeholder_type", stakeholder_type)

    response = query.execute()
    stakeholders = response.data or []

    if not stakeholders:
        return None

    matcher = SimilarityMatcher(
        thresholds=ThresholdConfig(
            exact=0.95,
            token_set=threshold,
            partial=threshold * 1.05,
            key_terms=threshold * 0.75,
        )
    )

    result = matcher.find_best_match(
        candidate=name,
        corpus=stakeholders,
        text_field="name",
        id_field="id",
    )

    if result.is_match:
        logger.debug(
            f"Found similar stakeholder: {result.matched_item.get('name')} "
            f"(score: {result.score:.2f}, strategy: {result.strategy.value})"
        )
        return result.matched_item

    return None


# ============================================================================
# Smart Upsert with Evidence Merging (Task #11)
# ============================================================================


def smart_upsert_stakeholder(
    project_id: UUID,
    name: str,
    stakeholder_type: str,
    new_evidence: list[dict],
    source_signal_id: UUID,
    created_by: str = "system",
    similarity_threshold: float = 0.75,
    # Optional core fields
    email: str | None = None,
    role: str | None = None,
    organization: str | None = None,
    influence_level: str = "medium",
    priorities: list[str] | None = None,
    concerns: list[str] | None = None,
    notes: str | None = None,
    linked_persona_id: UUID | None = None,
    # Enrichment fields
    engagement_level: str | None = None,
    communication_preferences: dict | None = None,
    last_interaction_date: str | None = None,
    preferred_channel: str | None = None,
    decision_authority: str | None = None,
    approval_required_for: list[str] | None = None,
    veto_power_over: list[str] | None = None,
    engagement_strategy: str | None = None,
    risk_if_disengaged: str | None = None,
    win_conditions: list[str] | None = None,
    key_concerns: list[str] | None = None,
    reports_to_id: UUID | None = None,
    allies: list[UUID] | None = None,
    potential_blockers: list[UUID] | None = None,
) -> tuple[UUID, str]:
    """
    Smart upsert for stakeholders with evidence merging.

    Args:
        project_id: Project UUID
        name: Stakeholder name
        stakeholder_type: Type (champion, sponsor, blocker, influencer, end_user)
        new_evidence: New evidence to add/merge
        source_signal_id: Signal this extraction came from
        created_by: Who created this
        similarity_threshold: Threshold for finding similar stakeholders
        ... (other optional fields)

    Returns:
        Tuple of (stakeholder_id, action) where action is "created", "updated", or "merged"
    """
    from app.core.state_snapshot import invalidate_snapshot

    supabase = get_supabase()

    similar = find_similar_stakeholder(
        project_id=project_id,
        name=name,
        email=email,
        stakeholder_type=stakeholder_type,
        threshold=similarity_threshold,
    )

    def merge_evidence_arrays(existing: list, new: list) -> list:
        evidence_map = {}
        for ev in existing:
            key = f"{ev.get('signal_id')}:{ev.get('chunk_id', '')}"
            evidence_map[key] = ev
        for ev in new:
            key = f"{ev.get('signal_id')}:{ev.get('chunk_id', '')}"
            if key not in evidence_map:
                evidence_map[key] = ev
        return list(evidence_map.values())

    def track_change(
        entity_id: UUID,
        revision_type: str,
        changes: dict,
        revision_number: int,
    ):
        supabase.table("enrichment_revisions").insert({
            "project_id": str(project_id),
            "entity_type": "stakeholder",
            "entity_id": str(entity_id),
            "entity_label": name[:100],
            "revision_type": revision_type,
            "changes": changes,
            "source_signal_id": str(source_signal_id),
            "revision_number": revision_number,
            "diff_summary": f"Updated from signal {str(source_signal_id)[:8]}",
            "created_by": created_by,
        }).execute()

    if similar:
        stakeholder_id = UUID(similar["id"])
        confirmation_status = similar.get("confirmation_status", "ai_generated")
        current_version = similar.get("version", 1)

        if confirmation_status in ("confirmed_consultant", "confirmed_client"):
            # MERGE EVIDENCE ONLY
            logger.info(
                f"Merging evidence for confirmed {stakeholder_type} stakeholder {stakeholder_id}"
            )

            existing_evidence = similar.get("evidence", []) or []
            merged_evidence = merge_evidence_arrays(existing_evidence, new_evidence)

            existing_signal_ids = similar.get("source_signal_ids", []) or []
            if str(source_signal_id) not in [str(sid) for sid in existing_signal_ids]:
                existing_signal_ids.append(str(source_signal_id))

            supabase.table("stakeholders").update({
                "evidence": merged_evidence,
                "source_signal_ids": existing_signal_ids,
                "version": current_version + 1,
            }).eq("id", str(stakeholder_id)).execute()

            track_change(
                entity_id=stakeholder_id,
                revision_type="updated",
                changes={"evidence": {"old": len(existing_evidence), "new": len(merged_evidence)}},
                revision_number=current_version + 1,
            )

            invalidate_snapshot(project_id)
            return (stakeholder_id, "merged")

        else:
            # UPDATE FIELDS + MERGE EVIDENCE
            logger.info(
                f"Updating ai_generated {stakeholder_type} stakeholder {stakeholder_id}"
            )

            existing_evidence = similar.get("evidence", []) or []
            merged_evidence = merge_evidence_arrays(existing_evidence, new_evidence)

            existing_signal_ids = similar.get("source_signal_ids", []) or []
            if str(source_signal_id) not in [str(sid) for sid in existing_signal_ids]:
                existing_signal_ids.append(str(source_signal_id))

            updates = {
                "name": name,
                "stakeholder_type": stakeholder_type,
                "evidence": merged_evidence,
                "source_signal_ids": existing_signal_ids,
                "version": current_version + 1,
                "created_by": created_by,
            }

            # Add optional fields if provided
            if email is not None:
                updates["email"] = email
            if role is not None:
                updates["role"] = role
            if organization is not None:
                updates["organization"] = organization
            if influence_level != similar.get("influence_level"):
                updates["influence_level"] = influence_level
            if priorities is not None:
                updates["priorities"] = priorities
            if concerns is not None:
                updates["concerns"] = concerns
            if notes is not None:
                updates["notes"] = notes
            if linked_persona_id is not None:
                updates["linked_persona_id"] = str(linked_persona_id)

            # Enrichment fields
            if engagement_level is not None:
                updates["engagement_level"] = engagement_level
            if communication_preferences is not None:
                updates["communication_preferences"] = communication_preferences
            if last_interaction_date is not None:
                updates["last_interaction_date"] = last_interaction_date
            if preferred_channel is not None:
                updates["preferred_channel"] = preferred_channel
            if decision_authority is not None:
                updates["decision_authority"] = decision_authority
            if approval_required_for is not None:
                updates["approval_required_for"] = approval_required_for
            if veto_power_over is not None:
                updates["veto_power_over"] = veto_power_over
            if engagement_strategy is not None:
                updates["engagement_strategy"] = engagement_strategy
            if risk_if_disengaged is not None:
                updates["risk_if_disengaged"] = risk_if_disengaged
            if win_conditions is not None:
                updates["win_conditions"] = win_conditions
            if key_concerns is not None:
                updates["key_concerns"] = key_concerns
            if reports_to_id is not None:
                updates["reports_to_id"] = str(reports_to_id)
            if allies is not None:
                updates["allies"] = [str(a) for a in allies]
            if potential_blockers is not None:
                updates["potential_blockers"] = [str(pb) for pb in potential_blockers]

            supabase.table("stakeholders").update(updates).eq("id", str(stakeholder_id)).execute()

            changes = {}
            for key, new_val in updates.items():
                if key not in ("evidence", "source_signal_ids", "version"):
                    old_val = similar.get(key)
                    if old_val != new_val:
                        changes[key] = {"old": old_val, "new": new_val}

            track_change(
                entity_id=stakeholder_id,
                revision_type="enriched",
                changes=changes,
                revision_number=current_version + 1,
            )

            invalidate_snapshot(project_id)
            return (stakeholder_id, "updated")

    else:
        # CREATE NEW
        logger.info(f"Creating new {stakeholder_type} stakeholder '{name}' for project {project_id}")

        data = {
            "project_id": str(project_id),
            "name": name,
            "stakeholder_type": stakeholder_type,
            "influence_level": influence_level,
            "evidence": new_evidence,
            "source_signal_ids": [str(source_signal_id)],
            "version": 1,
            "created_by": created_by,
            "priorities": priorities or [],
            "concerns": concerns or [],
        }

        # Add optional fields
        if email is not None:
            data["email"] = email
        if role is not None:
            data["role"] = role
        if organization is not None:
            data["organization"] = organization
        if notes is not None:
            data["notes"] = notes
        if linked_persona_id is not None:
            data["linked_persona_id"] = str(linked_persona_id)

        # Enrichment fields
        if engagement_level is not None:
            data["engagement_level"] = engagement_level
        if communication_preferences is not None:
            data["communication_preferences"] = communication_preferences
        if last_interaction_date is not None:
            data["last_interaction_date"] = last_interaction_date
        if preferred_channel is not None:
            data["preferred_channel"] = preferred_channel
        if decision_authority is not None:
            data["decision_authority"] = decision_authority
        if approval_required_for is not None:
            data["approval_required_for"] = approval_required_for
        if veto_power_over is not None:
            data["veto_power_over"] = veto_power_over
        if engagement_strategy is not None:
            data["engagement_strategy"] = engagement_strategy
        if risk_if_disengaged is not None:
            data["risk_if_disengaged"] = risk_if_disengaged
        if win_conditions is not None:
            data["win_conditions"] = win_conditions
        if key_concerns is not None:
            data["key_concerns"] = key_concerns
        if reports_to_id is not None:
            data["reports_to_id"] = str(reports_to_id)
        if allies is not None:
            data["allies"] = [str(a) for a in allies]
        if potential_blockers is not None:
            data["potential_blockers"] = [str(pb) for pb in potential_blockers]

        response = supabase.table("stakeholders").insert(data).execute()
        created_stakeholder = response.data[0] if response.data else data
        stakeholder_id = UUID(created_stakeholder["id"]) if response.data else UUID(data["id"])

        track_change(
            entity_id=stakeholder_id,
            revision_type="created",
            changes={},
            revision_number=1,
        )

        invalidate_snapshot(project_id)
        return (stakeholder_id, "created")
