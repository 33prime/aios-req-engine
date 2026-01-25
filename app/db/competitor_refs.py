"""CRUD operations for competitor_references entity."""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from app.core.logging import get_logger
from app.core.state_snapshot import invalidate_snapshot
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

ReferenceType = Literal["competitor", "design_inspiration", "feature_inspiration"]
ConfirmationStatus = Literal["ai_generated", "confirmed_consultant", "needs_client", "confirmed_client"]


def list_competitor_refs(
    project_id: UUID,
    reference_type: ReferenceType | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    List competitor references for a project.

    Args:
        project_id: Project UUID
        reference_type: Filter by type
        limit: Maximum number to return

    Returns:
        List of competitor reference dicts
    """
    supabase = get_supabase()

    query = (
        supabase.table("competitor_references")
        .select("*")
        .eq("project_id", str(project_id))
    )

    if reference_type:
        query = query.eq("reference_type", reference_type)

    response = query.order("created_at", desc=True).limit(limit).execute()
    return response.data or []


def get_competitor_ref(ref_id: UUID) -> dict[str, Any] | None:
    """
    Get a specific competitor reference by ID.

    Args:
        ref_id: Competitor reference UUID

    Returns:
        Competitor reference dict or None
    """
    supabase = get_supabase()

    response = (
        supabase.table("competitor_references")
        .select("*")
        .eq("id", str(ref_id))
        .maybe_single()
        .execute()
    )

    return response.data


def create_competitor_ref(
    project_id: UUID,
    reference_type: ReferenceType,
    name: str,
    url: str | None = None,
    category: str | None = None,
    strengths: list[str] | None = None,
    weaknesses: list[str] | None = None,
    features_to_study: list[str] | None = None,
    research_notes: str | None = None,
    screenshots: list[str] | None = None,
    source_signal_id: UUID | None = None,
    revision_id: UUID | None = None,
) -> dict[str, Any]:
    """
    Create a new competitor reference.

    Args:
        project_id: Project UUID
        reference_type: Type (competitor, design_inspiration, feature_inspiration)
        name: Name of the reference
        url: URL to the reference
        category: Category (Direct competitor, Adjacent, Design reference)
        strengths: List of strengths
        weaknesses: List of weaknesses
        features_to_study: Features to study
        research_notes: Detailed research notes
        screenshots: List of screenshot URLs
        source_signal_id: Signal this was extracted from
        revision_id: Revision tracking ID

    Returns:
        Created competitor reference dict
    """
    supabase = get_supabase()

    data: dict[str, Any] = {
        "project_id": str(project_id),
        "reference_type": reference_type,
        "name": name,
    }

    if url is not None:
        data["url"] = url
    if category is not None:
        data["category"] = category
    if strengths is not None:
        data["strengths"] = strengths
    if weaknesses is not None:
        data["weaknesses"] = weaknesses
    if features_to_study is not None:
        data["features_to_study"] = features_to_study
    if research_notes is not None:
        data["research_notes"] = research_notes
    if screenshots is not None:
        data["screenshots"] = screenshots
    if source_signal_id is not None:
        data["source_signal_id"] = str(source_signal_id)
    if revision_id is not None:
        data["revision_id"] = str(revision_id)

    response = supabase.table("competitor_references").insert(data).execute()

    # Invalidate state snapshot
    invalidate_snapshot(project_id)

    logger.info(f"Created {reference_type} reference '{name}' for project {project_id}")
    return response.data[0] if response.data else data


def update_competitor_ref(
    ref_id: UUID,
    project_id: UUID,
    **updates: Any,
) -> dict[str, Any] | None:
    """
    Update a competitor reference.

    Args:
        ref_id: Competitor reference UUID
        project_id: Project UUID (for snapshot invalidation)
        **updates: Fields to update

    Returns:
        Updated competitor reference dict or None
    """
    supabase = get_supabase()

    # Clean up None values and convert UUIDs
    clean_updates = {}
    for k, v in updates.items():
        if v is not None:
            if isinstance(v, UUID):
                clean_updates[k] = str(v)
            else:
                clean_updates[k] = v

    if not clean_updates:
        return get_competitor_ref(ref_id)

    response = (
        supabase.table("competitor_references")
        .update(clean_updates)
        .eq("id", str(ref_id))
        .execute()
    )

    # Invalidate state snapshot
    invalidate_snapshot(project_id)

    return response.data[0] if response.data else None


def delete_competitor_ref(ref_id: UUID, project_id: UUID) -> bool:
    """
    Delete a competitor reference.

    Args:
        ref_id: Competitor reference UUID
        project_id: Project UUID (for snapshot invalidation)

    Returns:
        True if deleted, False if not found
    """
    supabase = get_supabase()

    response = (
        supabase.table("competitor_references")
        .delete()
        .eq("id", str(ref_id))
        .execute()
    )

    # Invalidate state snapshot
    invalidate_snapshot(project_id)

    return bool(response.data)


# ============================================================================
# Confirmation Status Functions
# ============================================================================


def update_competitor_ref_status(
    ref_id: UUID,
    project_id: UUID,
    status: ConfirmationStatus,
    confirmed_by: UUID | None = None,
) -> dict[str, Any] | None:
    """
    Update confirmation status for a competitor reference.

    Args:
        ref_id: Competitor reference UUID
        project_id: Project UUID (for snapshot invalidation)
        status: New confirmation status
        confirmed_by: User UUID who confirmed

    Returns:
        Updated competitor reference dict or None
    """
    supabase = get_supabase()

    updates = {
        "confirmation_status": status,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
    }
    if confirmed_by:
        updates["confirmed_by"] = str(confirmed_by)

    response = (
        supabase.table("competitor_references")
        .update(updates)
        .eq("id", str(ref_id))
        .execute()
    )

    # Invalidate state snapshot
    invalidate_snapshot(project_id)

    return response.data[0] if response.data else None


def update_competitor_ref_field_status(
    ref_id: UUID,
    project_id: UUID,
    field: str,
    status: ConfirmationStatus,
) -> dict[str, Any] | None:
    """
    Update field-level confirmation status for a competitor reference.

    Args:
        ref_id: Competitor reference UUID
        project_id: Project UUID (for snapshot invalidation)
        field: Field name to update
        status: New confirmation status for the field

    Returns:
        Updated competitor reference dict or None
    """
    # Get current confirmed_fields
    ref = get_competitor_ref(ref_id)
    if not ref:
        return None

    confirmed_fields = ref.get("confirmed_fields", {}) or {}
    confirmed_fields[field] = status

    return update_competitor_ref(
        ref_id,
        project_id,
        confirmed_fields=confirmed_fields,
    )


def find_similar_competitor(
    project_id: UUID,
    name: str,
    reference_type: ReferenceType | None = None,
    threshold: float = 0.8,
) -> dict[str, Any] | None:
    """
    Find a similar competitor reference by name (upgraded for Task #13).

    Args:
        project_id: Project UUID
        name: Name to match
        reference_type: Optional filter by type
        threshold: Similarity threshold (0-1)

    Returns:
        Most similar competitor or None if below threshold
    """
    from app.core.similarity import SimilarityMatcher, ThresholdConfig

    refs = list_competitor_refs(project_id, reference_type=reference_type)

    if not refs:
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
        corpus=refs,
        text_field="name",
        id_field="id",
    )

    if result.is_match:
        logger.debug(
            f"Found similar competitor: {result.matched_item.get('name')} "
            f"(score: {result.score:.2f}, strategy: {result.strategy.value})"
        )
        return result.matched_item

    return None


# ============================================================================
# Smart Upsert with Evidence Merging (Task #10)
# ============================================================================


def smart_upsert_competitor_ref(
    project_id: UUID,
    reference_type: ReferenceType,
    name: str,
    new_evidence: list[dict[str, Any]],
    source_signal_id: UUID,
    created_by: str = "system",
    similarity_threshold: float = 0.75,
    # Optional core fields
    url: str | None = None,
    category: str | None = None,
    strengths: list[str] | None = None,
    weaknesses: list[str] | None = None,
    features_to_study: list[str] | None = None,
    research_notes: str | None = None,
    screenshots: list[str] | None = None,
    # Enrichment fields (for competitors)
    market_position: str | None = None,
    pricing_model: str | None = None,
    target_audience: str | None = None,
    key_differentiator: str | None = None,
    feature_comparison: dict[str, Any] | None = None,
    funding_stage: str | None = None,
    estimated_users: str | None = None,
    founded_year: int | None = None,
    employee_count: str | None = None,
) -> tuple[UUID, Literal["created", "updated", "merged"]]:
    """
    Smart upsert for competitor references with evidence merging.

    Args:
        project_id: Project UUID
        reference_type: Type (competitor, design_inspiration, feature_inspiration)
        name: Name of the reference
        new_evidence: New evidence to add/merge
        source_signal_id: Signal this extraction came from
        created_by: Who created this
        similarity_threshold: Threshold for finding similar refs
        ... (other optional fields)

    Returns:
        Tuple of (ref_id, action) where action is "created", "updated", or "merged"
    """
    supabase = get_supabase()

    similar = find_similar_competitor(
        project_id=project_id,
        name=name,
        reference_type=reference_type,
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
        revision_type: Literal["created", "enriched", "updated"],
        changes: dict[str, dict[str, Any]],
        revision_number: int,
    ):
        supabase.table("enrichment_revisions").insert({
            "project_id": str(project_id),
            "entity_type": "competitor_reference",
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
        ref_id = UUID(similar["id"])
        confirmation_status = similar.get("confirmation_status", "ai_generated")
        current_version = similar.get("version", 1)

        if confirmation_status in ("confirmed_consultant", "confirmed_client"):
            # MERGE EVIDENCE ONLY
            logger.info(
                f"Merging evidence for confirmed {reference_type} ref {ref_id} "
                f"(status: {confirmation_status})"
            )

            existing_evidence = similar.get("evidence", []) or []
            merged_evidence = merge_evidence_arrays(existing_evidence, new_evidence)

            existing_signal_ids = similar.get("source_signal_ids", []) or []
            if str(source_signal_id) not in [str(sid) for sid in existing_signal_ids]:
                existing_signal_ids.append(str(source_signal_id))

            supabase.table("competitor_references").update({
                "evidence": merged_evidence,
                "source_signal_ids": existing_signal_ids,
                "version": current_version + 1,
            }).eq("id", str(ref_id)).execute()

            track_change(
                entity_id=ref_id,
                revision_type="updated",
                changes={"evidence": {"old": len(existing_evidence), "new": len(merged_evidence)}},
                revision_number=current_version + 1,
            )

            invalidate_snapshot(project_id)
            return (ref_id, "merged")

        else:
            # UPDATE FIELDS + MERGE EVIDENCE
            logger.info(
                f"Updating ai_generated {reference_type} ref {ref_id}"
            )

            existing_evidence = similar.get("evidence", []) or []
            merged_evidence = merge_evidence_arrays(existing_evidence, new_evidence)

            existing_signal_ids = similar.get("source_signal_ids", []) or []
            if str(source_signal_id) not in [str(sid) for sid in existing_signal_ids]:
                existing_signal_ids.append(str(source_signal_id))

            updates: dict[str, Any] = {
                "name": name,
                "evidence": merged_evidence,
                "source_signal_ids": existing_signal_ids,
                "version": current_version + 1,
                "created_by": created_by,
            }

            # Add optional fields if provided
            if url is not None:
                updates["url"] = url
            if category is not None:
                updates["category"] = category
            if strengths is not None:
                updates["strengths"] = strengths
            if weaknesses is not None:
                updates["weaknesses"] = weaknesses
            if features_to_study is not None:
                updates["features_to_study"] = features_to_study
            if research_notes is not None:
                updates["research_notes"] = research_notes
            if screenshots is not None:
                updates["screenshots"] = screenshots

            # Enrichment fields (mostly for competitors)
            if market_position is not None:
                updates["market_position"] = market_position
            if pricing_model is not None:
                updates["pricing_model"] = pricing_model
            if target_audience is not None:
                updates["target_audience"] = target_audience
            if key_differentiator is not None:
                updates["key_differentiator"] = key_differentiator
            if feature_comparison is not None:
                updates["feature_comparison"] = feature_comparison
            if funding_stage is not None:
                updates["funding_stage"] = funding_stage
            if estimated_users is not None:
                updates["estimated_users"] = estimated_users
            if founded_year is not None:
                updates["founded_year"] = founded_year
            if employee_count is not None:
                updates["employee_count"] = employee_count

            supabase.table("competitor_references").update(updates).eq("id", str(ref_id)).execute()

            changes = {}
            for key, new_val in updates.items():
                if key not in ("evidence", "source_signal_ids", "version"):
                    old_val = similar.get(key)
                    if old_val != new_val:
                        changes[key] = {"old": old_val, "new": new_val}

            track_change(
                entity_id=ref_id,
                revision_type="enriched",
                changes=changes,
                revision_number=current_version + 1,
            )

            invalidate_snapshot(project_id)
            return (ref_id, "updated")

    else:
        # CREATE NEW
        logger.info(f"Creating new {reference_type} reference '{name}' for project {project_id}")

        data: dict[str, Any] = {
            "project_id": str(project_id),
            "reference_type": reference_type,
            "name": name,
            "evidence": new_evidence,
            "source_signal_ids": [str(source_signal_id)],
            "version": 1,
            "created_by": created_by,
        }

        # Add optional fields
        if url is not None:
            data["url"] = url
        if category is not None:
            data["category"] = category
        if strengths is not None:
            data["strengths"] = strengths
        if weaknesses is not None:
            data["weaknesses"] = weaknesses
        if features_to_study is not None:
            data["features_to_study"] = features_to_study
        if research_notes is not None:
            data["research_notes"] = research_notes
        if screenshots is not None:
            data["screenshots"] = screenshots

        # Enrichment fields
        if market_position is not None:
            data["market_position"] = market_position
        if pricing_model is not None:
            data["pricing_model"] = pricing_model
        if target_audience is not None:
            data["target_audience"] = target_audience
        if key_differentiator is not None:
            data["key_differentiator"] = key_differentiator
        if feature_comparison is not None:
            data["feature_comparison"] = feature_comparison
        if funding_stage is not None:
            data["funding_stage"] = funding_stage
        if estimated_users is not None:
            data["estimated_users"] = estimated_users
        if founded_year is not None:
            data["founded_year"] = founded_year
        if employee_count is not None:
            data["employee_count"] = employee_count

        response = supabase.table("competitor_references").insert(data).execute()
        created_ref = response.data[0] if response.data else data
        ref_id = UUID(created_ref["id"])

        track_change(
            entity_id=ref_id,
            revision_type="created",
            changes={},
            revision_number=1,
        )

        invalidate_snapshot(project_id)
        return (ref_id, "created")
