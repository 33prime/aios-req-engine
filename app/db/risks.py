"""CRUD operations for risks entity."""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from app.core.logging import get_logger
from app.core.state_snapshot import invalidate_snapshot
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

RiskType = Literal["technical", "business", "market", "team", "timeline", "budget", "compliance", "security", "operational", "strategic"]
RiskSeverity = Literal["critical", "high", "medium", "low"]
RiskLikelihood = Literal["very_high", "high", "medium", "low", "very_low"]
RiskStatus = Literal["identified", "active", "mitigated", "resolved", "accepted"]
ConfirmationStatus = Literal["ai_generated", "confirmed_consultant", "needs_client", "confirmed_client"]


def list_risks(
    project_id: UUID,
    risk_type: RiskType | None = None,
    status: RiskStatus | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    List risks for a project.

    Args:
        project_id: Project UUID
        risk_type: Filter by risk type
        status: Filter by status
        limit: Maximum number to return

    Returns:
        List of risk dicts
    """
    supabase = get_supabase()

    query = (
        supabase.table("risks")
        .select("*")
        .eq("project_id", str(project_id))
    )

    if risk_type:
        query = query.eq("risk_type", risk_type)
    if status:
        query = query.eq("status", status)

    response = query.order("severity").order("created_at", desc=True).limit(limit).execute()
    return response.data or []


def get_risk(risk_id: UUID) -> dict[str, Any] | None:
    """
    Get a specific risk by ID.

    Args:
        risk_id: Risk UUID

    Returns:
        Risk dict or None
    """
    supabase = get_supabase()

    response = (
        supabase.table("risks")
        .select("*")
        .eq("id", str(risk_id))
        .maybe_single()
        .execute()
    )

    return response.data


def create_risk(
    project_id: UUID,
    title: str,
    description: str,
    risk_type: RiskType,
    severity: RiskSeverity,
    likelihood: RiskLikelihood = "medium",
    status: RiskStatus = "active",
    impact: str | None = None,
    mitigation_strategy: str | None = None,
    owner: str | None = None,
    detection_signals: list[str] | None = None,
    probability_percentage: int | None = None,
    estimated_cost: str | None = None,
    mitigation_cost: str | None = None,
    source_signal_id: UUID | None = None,
) -> dict[str, Any]:
    """
    Create a new risk.

    Args:
        project_id: Project UUID
        title: Short risk title
        description: Detailed description
        risk_type: Type of risk
        severity: Impact severity
        likelihood: Probability
        status: Current status
        impact: Detailed impact description
        mitigation_strategy: How to prevent/reduce
        owner: Who owns mitigation
        detection_signals: Early warning signs
        probability_percentage: Numeric probability (0-100)
        estimated_cost: Financial impact estimate
        mitigation_cost: Cost to mitigate
        source_signal_id: Signal this was extracted from

    Returns:
        Created risk dict
    """
    supabase = get_supabase()

    data: dict[str, Any] = {
        "project_id": str(project_id),
        "title": title,
        "description": description,
        "risk_type": risk_type,
        "severity": severity,
        "likelihood": likelihood,
        "status": status,
    }

    if impact is not None:
        data["impact"] = impact
    if mitigation_strategy is not None:
        data["mitigation_strategy"] = mitigation_strategy
    if owner is not None:
        data["owner"] = owner
    if detection_signals is not None:
        data["detection_signals"] = detection_signals
    if probability_percentage is not None:
        data["probability_percentage"] = probability_percentage
    if estimated_cost is not None:
        data["estimated_cost"] = estimated_cost
    if mitigation_cost is not None:
        data["mitigation_cost"] = mitigation_cost
    if source_signal_id is not None:
        data["source_signal_ids"] = [str(source_signal_id)]

    response = supabase.table("risks").insert(data).execute()

    # Invalidate state snapshot
    invalidate_snapshot(project_id)

    logger.info(f"Created {risk_type} risk '{title}' for project {project_id}")
    return response.data[0] if response.data else data


def update_risk(
    risk_id: UUID,
    project_id: UUID,
    **updates: Any,
) -> dict[str, Any] | None:
    """
    Update a risk.

    Args:
        risk_id: Risk UUID
        project_id: Project UUID (for snapshot invalidation)
        **updates: Fields to update

    Returns:
        Updated risk dict or None
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
        return get_risk(risk_id)

    response = (
        supabase.table("risks")
        .update(clean_updates)
        .eq("id", str(risk_id))
        .execute()
    )

    # Invalidate state snapshot
    invalidate_snapshot(project_id)

    return response.data[0] if response.data else None


def delete_risk(risk_id: UUID, project_id: UUID) -> bool:
    """
    Delete a risk.

    Args:
        risk_id: Risk UUID
        project_id: Project UUID (for snapshot invalidation)

    Returns:
        True if deleted, False if not found
    """
    supabase = get_supabase()

    response = (
        supabase.table("risks")
        .delete()
        .eq("id", str(risk_id))
        .execute()
    )

    # Invalidate state snapshot
    invalidate_snapshot(project_id)

    return bool(response.data)


def update_risk_status(
    risk_id: UUID,
    project_id: UUID,
    status: RiskStatus,
) -> dict[str, Any] | None:
    """
    Update status for a risk.

    Args:
        risk_id: Risk UUID
        project_id: Project UUID
        status: New status

    Returns:
        Updated risk dict or None
    """
    return update_risk(risk_id, project_id, status=status)


def update_risk_confirmation_status(
    risk_id: UUID,
    project_id: UUID,
    status: ConfirmationStatus,
    confirmed_by: UUID | None = None,
) -> dict[str, Any] | None:
    """
    Update confirmation status for a risk.

    Args:
        risk_id: Risk UUID
        project_id: Project UUID
        status: New confirmation status
        confirmed_by: User UUID who confirmed

    Returns:
        Updated risk dict or None
    """
    supabase = get_supabase()

    updates = {
        "confirmation_status": status,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
    }
    if confirmed_by:
        updates["confirmed_by"] = str(confirmed_by)

    response = (
        supabase.table("risks")
        .update(updates)
        .eq("id", str(risk_id))
        .execute()
    )

    # Invalidate state snapshot
    invalidate_snapshot(project_id)

    return response.data[0] if response.data else None


def get_risks_by_severity(
    project_id: UUID,
    severity: RiskSeverity,
    active_only: bool = True,
) -> list[dict[str, Any]]:
    """
    Get risks filtered by severity.

    Args:
        project_id: Project UUID
        severity: Severity level
        active_only: If True, only return identified/active risks

    Returns:
        List of risk dicts
    """
    supabase = get_supabase()

    query = (
        supabase.table("risks")
        .select("*")
        .eq("project_id", str(project_id))
        .eq("severity", severity)
    )

    if active_only:
        query = query.in_("status", ["identified", "active"])

    response = query.order("created_at", desc=True).execute()
    return response.data or []


def get_critical_risks(project_id: UUID) -> list[dict[str, Any]]:
    """
    Get all critical risks for a project.

    Args:
        project_id: Project UUID

    Returns:
        List of critical risk dicts
    """
    return get_risks_by_severity(project_id, "critical", active_only=True)


def find_similar_risk(
    project_id: UUID,
    title: str,
    risk_type: RiskType | None = None,
    threshold: float = 0.8,
) -> dict[str, Any] | None:
    """
    Find a similar risk by title (upgraded for Task #13).

    Args:
        project_id: Project UUID
        title: Title to match
        risk_type: Optional filter by type
        threshold: Similarity threshold (0-1)

    Returns:
        Most similar risk or None if below threshold
    """
    from app.core.similarity import SimilarityMatcher, ThresholdConfig

    risks = list_risks(project_id, risk_type=risk_type)

    if not risks:
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
        candidate=title,
        corpus=risks,
        text_field="title",
        id_field="id",
    )

    if result.is_match:
        logger.debug(
            f"Found similar risk: {result.matched_item.get('title')} "
            f"(score: {result.score:.2f}, strategy: {result.strategy.value})"
        )
        return result.matched_item

    return None


# ============================================================================
# Smart Upsert with Evidence Merging (Task #12)
# ============================================================================


def smart_upsert_risk(
    project_id: UUID,
    title: str,
    description: str,
    risk_type: RiskType,
    severity: RiskSeverity,
    new_evidence: list[dict[str, Any]],
    source_signal_id: UUID,
    created_by: str = "system",
    similarity_threshold: float = 0.75,
    # Optional fields
    likelihood: RiskLikelihood = "medium",
    status: RiskStatus = "active",
    impact: str | None = None,
    mitigation_strategy: str | None = None,
    owner: str | None = None,
    detection_signals: list[str] | None = None,
    probability_percentage: int | None = None,
    estimated_cost: str | None = None,
    mitigation_cost: str | None = None,
) -> tuple[UUID, Literal["created", "updated", "merged"]]:
    """
    Smart upsert for risks with evidence merging.

    Args:
        project_id: Project UUID
        title: Short risk title
        description: Detailed description
        risk_type: Type of risk
        severity: Impact severity
        new_evidence: New evidence to add/merge
        source_signal_id: Signal this extraction came from
        created_by: Who created this
        similarity_threshold: Threshold for finding similar risks
        ... (other optional fields)

    Returns:
        Tuple of (risk_id, action) where action is "created", "updated", or "merged"
    """
    supabase = get_supabase()

    similar = find_similar_risk(
        project_id=project_id,
        title=title,
        risk_type=risk_type,
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
            "entity_type": "risk",
            "entity_id": str(entity_id),
            "entity_label": title[:100],
            "revision_type": revision_type,
            "changes": changes,
            "source_signal_id": str(source_signal_id),
            "revision_number": revision_number,
            "diff_summary": f"Updated from signal {str(source_signal_id)[:8]}",
            "created_by": created_by,
        }).execute()

    if similar:
        risk_id = UUID(similar["id"])
        confirmation_status = similar.get("confirmation_status", "ai_generated")
        current_version = similar.get("version", 1)

        if confirmation_status in ("confirmed_consultant", "confirmed_client"):
            # MERGE EVIDENCE ONLY
            logger.info(
                f"Merging evidence for confirmed {risk_type} risk {risk_id} "
                f"(status: {confirmation_status})"
            )

            existing_evidence = similar.get("evidence", []) or []
            merged_evidence = merge_evidence_arrays(existing_evidence, new_evidence)

            existing_signal_ids = similar.get("source_signal_ids", []) or []
            if str(source_signal_id) not in [str(sid) for sid in existing_signal_ids]:
                existing_signal_ids.append(str(source_signal_id))

            supabase.table("risks").update({
                "evidence": merged_evidence,
                "source_signal_ids": existing_signal_ids,
                "version": current_version + 1,
            }).eq("id", str(risk_id)).execute()

            track_change(
                entity_id=risk_id,
                revision_type="updated",
                changes={"evidence": {"old": len(existing_evidence), "new": len(merged_evidence)}},
                revision_number=current_version + 1,
            )

            invalidate_snapshot(project_id)
            return (risk_id, "merged")

        else:
            # UPDATE FIELDS + MERGE EVIDENCE
            logger.info(
                f"Updating ai_generated {risk_type} risk {risk_id}"
            )

            existing_evidence = similar.get("evidence", []) or []
            merged_evidence = merge_evidence_arrays(existing_evidence, new_evidence)

            existing_signal_ids = similar.get("source_signal_ids", []) or []
            if str(source_signal_id) not in [str(sid) for sid in existing_signal_ids]:
                existing_signal_ids.append(str(source_signal_id))

            updates: dict[str, Any] = {
                "title": title,
                "description": description,
                "risk_type": risk_type,
                "severity": severity,
                "likelihood": likelihood,
                "evidence": merged_evidence,
                "source_signal_ids": existing_signal_ids,
                "version": current_version + 1,
                "created_by": created_by,
            }

            # Add optional fields if provided
            if status != similar.get("status"):
                updates["status"] = status
            if impact is not None:
                updates["impact"] = impact
            if mitigation_strategy is not None:
                updates["mitigation_strategy"] = mitigation_strategy
            if owner is not None:
                updates["owner"] = owner
            if detection_signals is not None:
                updates["detection_signals"] = detection_signals
            if probability_percentage is not None:
                updates["probability_percentage"] = probability_percentage
            if estimated_cost is not None:
                updates["estimated_cost"] = estimated_cost
            if mitigation_cost is not None:
                updates["mitigation_cost"] = mitigation_cost

            supabase.table("risks").update(updates).eq("id", str(risk_id)).execute()

            changes = {}
            for key, new_val in updates.items():
                if key not in ("evidence", "source_signal_ids", "version"):
                    old_val = similar.get(key)
                    if old_val != new_val:
                        changes[key] = {"old": old_val, "new": new_val}

            track_change(
                entity_id=risk_id,
                revision_type="enriched",
                changes=changes,
                revision_number=current_version + 1,
            )

            invalidate_snapshot(project_id)
            return (risk_id, "updated")

    else:
        # CREATE NEW
        logger.info(f"Creating new {risk_type} risk '{title}' for project {project_id}")

        data: dict[str, Any] = {
            "project_id": str(project_id),
            "title": title,
            "description": description,
            "risk_type": risk_type,
            "severity": severity,
            "likelihood": likelihood,
            "status": status,
            "evidence": new_evidence,
            "source_signal_ids": [str(source_signal_id)],
            "version": 1,
            "created_by": created_by,
        }

        # Add optional fields
        if impact is not None:
            data["impact"] = impact
        if mitigation_strategy is not None:
            data["mitigation_strategy"] = mitigation_strategy
        if owner is not None:
            data["owner"] = owner
        if detection_signals is not None:
            data["detection_signals"] = detection_signals
        if probability_percentage is not None:
            data["probability_percentage"] = probability_percentage
        if estimated_cost is not None:
            data["estimated_cost"] = estimated_cost
        if mitigation_cost is not None:
            data["mitigation_cost"] = mitigation_cost

        response = supabase.table("risks").insert(data).execute()
        created_risk = response.data[0] if response.data else data
        risk_id = UUID(created_risk["id"])

        track_change(
            entity_id=risk_id,
            revision_type="created",
            changes={},
            revision_number=1,
        )

        invalidate_snapshot(project_id)
        return (risk_id, "created")
