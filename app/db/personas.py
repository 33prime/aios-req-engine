"""Database operations for personas table."""

from uuid import UUID

from app.core.logging import get_logger
from app.core.similarity import SimilarityMatcher, find_matching_persona
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

# Shared matcher instance for personas
_persona_matcher = SimilarityMatcher(entity_type="persona")


def list_personas(project_id: UUID) -> list[dict]:
    """
    List all personas for a project.

    Args:
        project_id: Project UUID

    Returns:
        List of persona dicts with all fields
    """
    supabase = get_supabase()

    response = (
        supabase.table("personas")
        .select("*")
        .eq("project_id", str(project_id))
        .order("created_at", desc=False)
        .execute()
    )

    return response.data


def get_persona(persona_id: UUID) -> dict | None:
    """
    Get a single persona by ID.

    Args:
        persona_id: Persona UUID

    Returns:
        Persona dict or None if not found
    """
    supabase = get_supabase()

    response = (
        supabase.table("personas")
        .select("*")
        .eq("id", str(persona_id))
        .maybe_single()
        .execute()
    )

    return response.data


def get_persona_by_slug(project_id: UUID, slug: str) -> dict | None:
    """
    Get a persona by project_id and slug.

    Args:
        project_id: Project UUID
        slug: Persona slug (stable identifier)

    Returns:
        Persona dict or None if not found
    """
    supabase = get_supabase()

    response = (
        supabase.table("personas")
        .select("*")
        .eq("project_id", str(project_id))
        .eq("slug", slug)
        .maybe_single()
        .execute()
    )

    return response.data


def create_persona(
    project_id: UUID,
    slug: str,
    name: str,
    role: str | None = None,
    demographics: dict | None = None,
    psychographics: dict | None = None,
    goals: list[str] | None = None,
    pain_points: list[str] | None = None,
    description: str | None = None,
    related_features: list[UUID] | None = None,
    related_vp_steps: list[UUID] | None = None,
    confirmation_status: str = "ai_generated",
) -> dict:
    """
    Create a new persona.

    Args:
        project_id: Project UUID
        slug: Stable identifier (e.g., "sarah-chen-pm")
        name: Display name (e.g., "Sarah Chen")
        role: Persona role/title
        demographics: Demographics dict
        psychographics: Psychographics dict
        goals: List of persona goals
        pain_points: List of pain points
        description: Optional description
        related_features: List of feature UUIDs
        related_vp_steps: List of VP step UUIDs
        confirmation_status: Confirmation status (default: ai_generated)

    Returns:
        Created persona dict
    """
    supabase = get_supabase()

    persona_data = {
        "project_id": str(project_id),
        "slug": slug,
        "name": name,
        "role": role,
        "demographics": demographics or {},
        "psychographics": psychographics or {},
        "goals": goals or [],
        "pain_points": pain_points or [],
        "description": description,
        "related_features": [str(fid) for fid in (related_features or [])],
        "related_vp_steps": [str(vid) for vid in (related_vp_steps or [])],
        "confirmation_status": confirmation_status,
    }

    response = (
        supabase.table("personas")
        .insert(persona_data)
        .execute()
    )

    created_persona = response.data[0]

    # Track creation (non-blocking)
    try:
        from app.core.change_tracking import track_entity_change
        track_entity_change(
            project_id=project_id,
            entity_type="persona",
            entity_id=UUID(created_persona["id"]),
            entity_label=name,
            old_entity=None,  # Created
            new_entity=created_persona,
            trigger_event="created",
            created_by="system",
        )
    except Exception as track_err:
        logger.warning(f"Failed to track persona creation: {track_err}")

    return created_persona


def update_persona(
    persona_id: UUID,
    updates: dict,
    run_id: UUID | None = None,
    source_signal_id: UUID | None = None,
    trigger_event: str = "manual_update",
) -> dict:
    """
    Update a persona.

    Args:
        persona_id: Persona UUID
        updates: Dict of fields to update
        run_id: Optional run ID for tracking
        source_signal_id: Optional signal that triggered this update
        trigger_event: What triggered this update (default: manual_update)

    Returns:
        Updated persona dict
    """
    supabase = get_supabase()

    # Get current state BEFORE update for change tracking
    old_persona = get_persona(persona_id)

    # Convert UUID fields to strings if present
    if "related_features" in updates:
        updates["related_features"] = [str(fid) for fid in updates["related_features"]]
    if "related_vp_steps" in updates:
        updates["related_vp_steps"] = [str(vid) for vid in updates["related_vp_steps"]]

    # Add updated_at timestamp
    updates["updated_at"] = "now()"

    response = (
        supabase.table("personas")
        .update(updates)
        .eq("id", str(persona_id))
        .execute()
    )

    updated_persona = response.data[0]

    # Track change (non-blocking)
    if old_persona:
        try:
            from app.core.change_tracking import track_entity_change
            track_entity_change(
                project_id=UUID(old_persona["project_id"]),
                entity_type="persona",
                entity_id=persona_id,
                entity_label=old_persona.get("name", str(persona_id)),
                old_entity=old_persona,
                new_entity=updated_persona,
                trigger_event=trigger_event,
                source_signal_id=source_signal_id,
                run_id=run_id,
                created_by="system",
            )
        except Exception as track_err:
            logger.warning(f"Failed to track persona change: {track_err}")

    return updated_persona


def delete_persona(persona_id: UUID) -> None:
    """
    Delete a persona.

    Args:
        persona_id: Persona UUID
    """
    supabase = get_supabase()

    supabase.table("personas").delete().eq("id", str(persona_id)).execute()


def upsert_persona(
    project_id: UUID,
    slug: str,
    name: str,
    role: str | None = None,
    demographics: dict | None = None,
    psychographics: dict | None = None,
    goals: list[str] | None = None,
    pain_points: list[str] | None = None,
    description: str | None = None,
    related_features: list[UUID] | None = None,
    related_vp_steps: list[UUID] | None = None,
    confirmation_status: str = "ai_generated",
) -> dict:
    """
    Upsert a persona (insert or update by project_id + slug).

    Smart merge logic:
    - If a persona with this slug exists and is confirmed, skip the update
    - If a persona with a similar name exists and is confirmed, skip (even if different slug)
    - Otherwise, upsert normally

    Args:
        Same as create_persona

    Returns:
        Created or updated persona dict
    """
    supabase = get_supabase()

    # Check for existing personas - both by slug and by similar name
    existing_response = (
        supabase.table("personas")
        .select("*")
        .eq("project_id", str(project_id))
        .execute()
    )
    existing_personas = existing_response.data or []

    # Confirmed statuses
    CONFIRMED_STATUSES = {"confirmed_client", "confirmed_consultant"}

    # Check if there's a confirmed persona with this exact slug
    for existing in existing_personas:
        if existing.get("slug") == slug:
            if existing.get("confirmation_status") in CONFIRMED_STATUSES:
                logger.info(
                    f"Skipping upsert for persona '{name}' - confirmed persona exists with slug '{slug}'",
                    extra={"project_id": str(project_id), "persona_id": existing.get("id")},
                )
                return existing  # Return the existing confirmed persona

    # Check for confirmed personas with similar names using centralized matcher
    confirmed_personas = [
        p for p in existing_personas
        if p.get("confirmation_status") in CONFIRMED_STATUSES
    ]

    if confirmed_personas:
        result = find_matching_persona(name, confirmed_personas)

        if result.is_match:
            logger.info(
                f"Skipping upsert for persona '{name}' - similar to confirmed '{result.matched_item.get('name')}' "
                f"(score: {result.score:.2f}, method: {result.strategy.value})",
                extra={"project_id": str(project_id), "persona_id": result.matched_id},
            )
            return result.matched_item  # Return the existing confirmed persona

    # No confirmed persona blocking this - proceed with upsert
    # Check if this persona already exists (for tracking change type)
    existing_by_slug = next((p for p in existing_personas if p.get("slug") == slug), None)
    is_update = existing_by_slug is not None

    persona_data = {
        "project_id": str(project_id),
        "slug": slug,
        "name": name,
        "role": role,
        "demographics": demographics or {},
        "psychographics": psychographics or {},
        "goals": goals or [],
        "pain_points": pain_points or [],
        "description": description,
        "related_features": [str(fid) for fid in (related_features or [])],
        "related_vp_steps": [str(vid) for vid in (related_vp_steps or [])],
        "confirmation_status": confirmation_status,
    }

    # If updating an existing persona, reset enrichment status so it gets re-enriched
    if is_update:
        persona_data["enrichment_status"] = "none"
        persona_data["enriched_at"] = None

    response = (
        supabase.table("personas")
        .upsert(persona_data, on_conflict="project_id,slug")
        .execute()
    )

    upserted_persona = response.data[0]

    # Track change (non-blocking)
    if is_update:
        try:
            from app.core.change_tracking import track_entity_change
            track_entity_change(
                project_id=project_id,
                entity_type="persona",
                entity_id=UUID(upserted_persona["id"]),
                entity_label=name,
                old_entity=existing_by_slug,
                new_entity=upserted_persona,
                trigger_event="proposal_applied",
                created_by="system",
            )
        except Exception as track_err:
            logger.warning(f"Failed to track persona upsert: {track_err}")

    return upserted_persona


def update_confirmation_status(
    persona_id: UUID,
    status: str,
    confirmed_by: UUID | None = None,
) -> dict:
    """
    Update confirmation status for a persona.

    Args:
        persona_id: Persona UUID
        status: New confirmation status
        confirmed_by: User UUID who confirmed

    Returns:
        Updated persona dict
    """
    supabase = get_supabase()

    from datetime import datetime, timezone

    updates = {
        "confirmation_status": status,
        "confirmed_by": str(confirmed_by) if confirmed_by else None,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
    }

    response = (
        supabase.table("personas")
        .update(updates)
        .eq("id", str(persona_id))
        .execute()
    )

    return response.data[0]


# ============================================================================
# Coverage and Health Score Functions
# ============================================================================


def calculate_persona_coverage(persona_id: UUID) -> float:
    """
    Calculate coverage score for a persona.

    Coverage = (goals with addressing features / total goals) * 100

    A goal is "addressed" if there's a feature that:
    - Is explicitly linked to the persona via related_features
    - OR has keyword overlap with the goal text

    Args:
        persona_id: Persona UUID

    Returns:
        Coverage score from 0.0 to 100.0
    """
    supabase = get_supabase()

    try:
        # Get persona
        persona = get_persona(persona_id)
        if not persona:
            return 0.0

        goals = persona.get("goals", []) or []
        if not goals:
            return 100.0  # No goals = fully covered

        project_id = persona["project_id"]
        related_feature_ids = set(persona.get("related_features", []) or [])

        # Get all features for project
        features_response = (
            supabase.table("features")
            .select("id, name, details")
            .eq("project_id", str(project_id))
            .execute()
        )
        features = features_response.data or []

        # Build feature text index for keyword matching
        feature_texts = []
        for f in features:
            # Extract description from details JSON if present
            details = f.get("details") or {}
            description = details.get("summary", "") if isinstance(details, dict) else ""
            text = f"{f.get('name', '')} {description}".lower()
            feature_texts.append({
                "id": f["id"],
                "text": text,
                "is_related": f["id"] in related_feature_ids,
            })

        # Count addressed goals
        addressed_count = 0

        for goal in goals:
            goal_lower = goal.lower() if isinstance(goal, str) else ""
            goal_words = set(w for w in goal_lower.split() if len(w) > 3)

            # Remove stopwords
            stopwords = {"the", "and", "for", "with", "that", "this", "from", "have", "will", "when"}
            goal_words -= stopwords

            is_addressed = False

            for feat in feature_texts:
                # Check if feature is explicitly related
                if feat["is_related"]:
                    is_addressed = True
                    break

                # Check keyword overlap (need at least 2 matching words)
                if goal_words:
                    matches = sum(1 for w in goal_words if w in feat["text"])
                    if matches >= 2 or (matches >= 1 and len(goal_words) <= 2):
                        is_addressed = True
                        break

            if is_addressed:
                addressed_count += 1

        coverage = (addressed_count / len(goals)) * 100.0
        return round(coverage, 1)

    except Exception as e:
        logger.error(f"Error calculating persona coverage: {e}", exc_info=True)
        return 0.0


def calculate_persona_health(persona_id: UUID) -> float:
    """
    Calculate health score for a persona.

    Health degrades based on time since last update:
    - First 7 days: 100% (fresh)
    - After 7 days: degrades 10% per week
    - Minimum: 20%

    Formula: max(20, 100 - ((days_since_update - 7) / 7) * 10)

    Args:
        persona_id: Persona UUID

    Returns:
        Health score from 20.0 to 100.0
    """
    supabase = get_supabase()

    try:
        from datetime import datetime, timezone

        # Get persona
        persona = get_persona(persona_id)
        if not persona:
            return 100.0

        # Get updated_at timestamp
        updated_at_str = persona.get("updated_at")
        if not updated_at_str:
            # Use created_at as fallback
            updated_at_str = persona.get("created_at")

        if not updated_at_str:
            return 100.0

        # Parse timestamp
        if isinstance(updated_at_str, str):
            # Handle ISO format with timezone
            updated_at_str = updated_at_str.replace("Z", "+00:00")
            updated_at = datetime.fromisoformat(updated_at_str)
        else:
            updated_at = updated_at_str

        # Ensure timezone aware
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)

        # Calculate days since update
        now = datetime.now(timezone.utc)
        days_since_update = (now - updated_at).days

        # Apply health formula
        if days_since_update <= 7:
            health = 100.0
        else:
            weeks_stale = (days_since_update - 7) / 7
            health = max(20.0, 100.0 - (weeks_stale * 10))

        return round(health, 1)

    except Exception as e:
        logger.error(f"Error calculating persona health: {e}", exc_info=True)
        return 100.0


def update_persona_scores(persona_id: UUID) -> dict | None:
    """
    Update coverage and health scores for a single persona.

    Args:
        persona_id: Persona UUID

    Returns:
        Updated persona dict or None
    """
    supabase = get_supabase()

    try:
        coverage = calculate_persona_coverage(persona_id)
        health = calculate_persona_health(persona_id)

        response = (
            supabase.table("personas")
            .update({
                "coverage_score": coverage,
                "health_score": health,
            })
            .eq("id", str(persona_id))
            .execute()
        )

        if response.data:
            logger.info(
                f"Updated persona {persona_id} scores: coverage={coverage}%, health={health}%",
                extra={"persona_id": str(persona_id)},
            )
            return response.data[0]

        return None

    except Exception as e:
        logger.error(f"Error updating persona scores: {e}", exc_info=True)
        return None


def update_all_persona_scores(project_id: UUID) -> list[dict]:
    """
    Update coverage and health scores for all personas in a project.

    Args:
        project_id: Project UUID

    Returns:
        List of updated persona dicts
    """
    supabase = get_supabase()
    updated = []

    try:
        # Get all personas for project
        personas = list_personas(project_id)

        for persona in personas:
            persona_id = UUID(persona["id"])
            coverage = calculate_persona_coverage(persona_id)
            health = calculate_persona_health(persona_id)

            response = (
                supabase.table("personas")
                .update({
                    "coverage_score": coverage,
                    "health_score": health,
                })
                .eq("id", str(persona_id))
                .execute()
            )

            if response.data:
                updated.append(response.data[0])

        logger.info(
            f"Updated scores for {len(updated)} personas in project {project_id}",
            extra={"project_id": str(project_id), "count": len(updated)},
        )

        return updated

    except Exception as e:
        logger.error(f"Error updating all persona scores: {e}", exc_info=True)
        return updated


def get_personas_with_scores(project_id: UUID) -> list[dict]:
    """
    List all personas for a project with calculated scores.

    This recalculates scores on-the-fly if they're not set.

    Args:
        project_id: Project UUID

    Returns:
        List of persona dicts with coverage_score and health_score
    """
    try:
        personas = list_personas(project_id)

        for persona in personas:
            persona_id = UUID(persona["id"])

            # Calculate scores if not set
            if persona.get("coverage_score") is None:
                persona["coverage_score"] = calculate_persona_coverage(persona_id)

            if persona.get("health_score") is None:
                persona["health_score"] = calculate_persona_health(persona_id)

        return personas

    except Exception as e:
        logger.error(f"Error getting personas with scores: {e}", exc_info=True)
        return []


def get_unhealthy_personas(project_id: UUID, threshold: float = 50.0) -> list[dict]:
    """
    Get personas with health score below threshold.

    Args:
        project_id: Project UUID
        threshold: Health score threshold (default 50%)

    Returns:
        List of unhealthy persona dicts
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("personas")
            .select("*")
            .eq("project_id", str(project_id))
            .lt("health_score", threshold)
            .order("health_score")
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(f"Error getting unhealthy personas: {e}", exc_info=True)
        return []


def get_low_coverage_personas(project_id: UUID, threshold: float = 50.0) -> list[dict]:
    """
    Get personas with coverage score below threshold.

    Args:
        project_id: Project UUID
        threshold: Coverage score threshold (default 50%)

    Returns:
        List of low-coverage persona dicts
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("personas")
            .select("*")
            .eq("project_id", str(project_id))
            .lt("coverage_score", threshold)
            .order("coverage_score")
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(f"Error getting low coverage personas: {e}", exc_info=True)
        return []


def update_persona_enrichment(
    persona_id: UUID,
    overview: str,
    key_workflows: list[dict],
) -> dict:
    """
    Update a persona with v2 enrichment data.

    Args:
        persona_id: Persona UUID
        overview: Detailed description of who this persona is
        key_workflows: List of {name, description, steps, features_used}

    Returns:
        Updated persona dict

    Raises:
        ValueError: If persona not found
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        update_data = {
            "overview": overview,
            "key_workflows": key_workflows,
            "enrichment_status": "enriched",
            "enriched_at": "now()",
            "updated_at": "now()",
        }

        response = (
            supabase.table("personas")
            .update(update_data)
            .eq("id", str(persona_id))
            .execute()
        )

        if not response.data:
            raise ValueError(f"Persona not found: {persona_id}")

        updated_persona = response.data[0]
        logger.info(
            f"Enriched persona {persona_id}",
            extra={"persona_id": str(persona_id)},
        )

        return updated_persona

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Failed to enrich persona {persona_id}: {e}")
        raise


def list_personas_for_enrichment(
    project_id: UUID,
    only_unenriched: bool = True,
) -> list[dict]:
    """
    List personas eligible for v2 enrichment.

    Args:
        project_id: Project UUID
        only_unenriched: If True, only return personas with enrichment_status='none'

    Returns:
        List of persona dicts

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        query = (
            supabase.table("personas")
            .select("*")
            .eq("project_id", str(project_id))
            .order("created_at", desc=False)
        )

        if only_unenriched:
            query = query.eq("enrichment_status", "none")

        response = query.execute()

        personas = response.data or []
        logger.info(
            f"Found {len(personas)} personas for enrichment",
            extra={"project_id": str(project_id), "only_unenriched": only_unenriched},
        )

        return personas

    except Exception as e:
        logger.error(f"Failed to list personas for enrichment: {e}")
        raise


def get_persona_feature_coverage(persona_id: UUID) -> dict:
    """
    Get detailed feature coverage breakdown for a persona.

    Returns which goals are addressed and which have gaps.

    Args:
        persona_id: Persona UUID

    Returns:
        Dict with addressed_goals, unaddressed_goals, and feature_matches
    """
    supabase = get_supabase()

    try:
        persona = get_persona(persona_id)
        if not persona:
            return {"addressed_goals": [], "unaddressed_goals": [], "feature_matches": []}

        goals = persona.get("goals", []) or []
        if not goals:
            return {"addressed_goals": [], "unaddressed_goals": [], "feature_matches": []}

        project_id = persona["project_id"]
        related_feature_ids = set(persona.get("related_features", []) or [])

        # Get all features for project
        features_response = (
            supabase.table("features")
            .select("id, name, details")
            .eq("project_id", str(project_id))
            .execute()
        )
        features = features_response.data or []

        addressed_goals = []
        unaddressed_goals = []
        feature_matches = []

        for goal in goals:
            goal_lower = goal.lower() if isinstance(goal, str) else ""
            goal_words = set(w for w in goal_lower.split() if len(w) > 3)
            stopwords = {"the", "and", "for", "with", "that", "this", "from", "have", "will", "when"}
            goal_words -= stopwords

            matching_features = []

            for feat in features:
                details = feat.get("details") or {}
                description = details.get("summary", "") if isinstance(details, dict) else ""
                feat_text = f"{feat.get('name', '')} {description}".lower()
                is_related = feat["id"] in related_feature_ids

                if is_related:
                    matching_features.append({
                        "id": feat["id"],
                        "name": feat.get("name"),
                        "match_type": "explicit",
                    })
                elif goal_words:
                    matches = sum(1 for w in goal_words if w in feat_text)
                    if matches >= 2 or (matches >= 1 and len(goal_words) <= 2):
                        matching_features.append({
                            "id": feat["id"],
                            "name": feat.get("name"),
                            "match_type": "keyword",
                        })

            if matching_features:
                addressed_goals.append(goal)
                feature_matches.append({
                    "goal": goal,
                    "features": matching_features,
                })
            else:
                unaddressed_goals.append(goal)

        return {
            "addressed_goals": addressed_goals,
            "unaddressed_goals": unaddressed_goals,
            "feature_matches": feature_matches,
            "coverage_score": round(len(addressed_goals) / len(goals) * 100, 1) if goals else 100.0,
        }

    except Exception as e:
        logger.error(f"Error getting persona feature coverage: {e}", exc_info=True)
        return {"addressed_goals": [], "unaddressed_goals": [], "feature_matches": []}
