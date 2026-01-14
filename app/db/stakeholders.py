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
) -> dict | None:
    """
    Find a similar stakeholder by name or email.

    Args:
        project_id: Project UUID
        name: Name to match
        email: Optional email to match (takes priority)

    Returns:
        Most similar stakeholder or None
    """
    # First try email match
    if email:
        by_email = find_stakeholder_by_email(project_id, email)
        if by_email:
            return by_email

    # Then try name match
    supabase = get_supabase()

    response = (
        supabase.table("stakeholders")
        .select("*")
        .eq("project_id", str(project_id))
        .ilike("name", name)
        .maybe_single()
        .execute()
    )

    if response.data:
        return response.data

    # Try partial name match
    stakeholders = list_stakeholders(project_id)
    name_lower = name.lower().strip()

    for sh in stakeholders:
        sh_name = sh.get("name", "").lower().strip()
        if sh_name and (name_lower in sh_name or sh_name in name_lower):
            return sh

    return None
