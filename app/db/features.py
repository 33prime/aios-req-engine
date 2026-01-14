"""Features database operations."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.core.similarity import SimilarityMatcher, find_matching_feature
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


# Confirmation statuses that count as "confirmed" (protected from bulk replace)
CONFIRMED_STATUSES = {"confirmed_client", "confirmed_consultant"}

# Shared matcher instance for features
_feature_matcher = SimilarityMatcher(entity_type="feature")


def _is_similar_to_any(feature_name: str, confirmed_features: list[dict]) -> tuple[bool, dict | None]:
    """
    Check if a feature name is similar to any confirmed feature using multi-strategy matching.

    Returns (is_similar, matched_feature or None)
    """
    result = find_matching_feature(feature_name, confirmed_features)

    if result.is_match:
        logger.info(
            f"Feature '{feature_name}' matches confirmed '{result.matched_item.get('name')}' "
            f"(score: {result.score:.2f}, method: {result.strategy.value})"
        )
        return True, result.matched_item

    return False, None


def bulk_replace_features(
    project_id: UUID,
    features: list[dict[str, Any]],
) -> tuple[int, list[dict[str, Any]]]:
    """
    Smart replace features for a project - preserves confirmed features.

    Logic:
    1. If NO confirmed features exist → full bulk replace (delete all, insert new)
    2. If confirmed features exist → preserve them, only replace ai_generated ones
    3. Returns list of preserved confirmed features for conflict detection

    Args:
        project_id: Project UUID
        features: List of feature dicts (name, category, is_mvp, confidence, status, evidence)

    Returns:
        Tuple of (inserted_count, preserved_features)
        - inserted_count: Number of new features inserted
        - preserved_features: List of confirmed features that were preserved

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    # Valid columns for features table
    # Includes all enrichment columns from migrations 0008, 0015, 0016, 0031
    VALID_FEATURE_COLUMNS = {
        # Core fields (0006)
        "name",
        "category",
        "is_mvp",
        "confidence",
        "status",
        "evidence",
        # Enrichment details (0008)
        "details",
        # Lifecycle tracking (0015)
        "lifecycle_stage",
        # Confirmation status (0016/0020)
        "confirmation_status",
        # Feature enrichment (0031)
        "overview",
        "target_personas",
        "user_actions",
        "system_behaviors",
        "ui_requirements",
        "rules",
        "integrations",
        "enrichment_status",
    }

    try:
        # Step 1: Check for existing confirmed features
        existing_response = (
            supabase.table("features")
            .select("*")
            .eq("project_id", str(project_id))
            .execute()
        )
        existing_features = existing_response.data or []

        # Separate confirmed vs ai_generated
        confirmed_features = [
            f for f in existing_features
            if f.get("confirmation_status") in CONFIRMED_STATUSES
        ]
        ai_generated_features = [
            f for f in existing_features
            if f.get("confirmation_status") not in CONFIRMED_STATUSES
        ]

        # Step 2: Delete based on whether confirmed features exist
        if confirmed_features:
            # Smart merge: Only delete ai_generated features
            ai_generated_ids = [f["id"] for f in ai_generated_features]
            if ai_generated_ids:
                supabase.table("features").delete().in_("id", ai_generated_ids).execute()
                logger.info(
                    f"Deleted {len(ai_generated_ids)} ai_generated features, preserved {len(confirmed_features)} confirmed features",
                    extra={"project_id": str(project_id)},
                )
            else:
                logger.info(
                    f"No ai_generated features to delete, preserved {len(confirmed_features)} confirmed features",
                    extra={"project_id": str(project_id)},
                )
        else:
            # No confirmed features - full bulk replace
            supabase.table("features").delete().eq("project_id", str(project_id)).execute()
            logger.info(
                f"Full bulk replace - deleted all existing features for project {project_id}",
                extra={"project_id": str(project_id)},
            )

        # Step 3: Insert new features (if any), filtering out duplicates of confirmed features
        if not features:
            return (0, confirmed_features)

        rows = []
        merged_evidence = []  # Track features where we merged evidence

        for feature in features:
            feature_name = feature.get("name", "")

            # Check if this feature is similar to any confirmed feature
            if confirmed_features:
                is_similar, matched = _is_similar_to_any(feature_name, confirmed_features)
                if is_similar and matched:
                    # Instead of skipping, MERGE the new evidence into the confirmed feature
                    new_evidence = feature.get("evidence", [])
                    if new_evidence:
                        matched_id = matched.get("id")
                        existing_evidence = matched.get("evidence", []) or []

                        # Deduplicate evidence by chunk_id
                        existing_chunk_ids = {
                            e.get("chunk_id") for e in existing_evidence if e.get("chunk_id")
                        }
                        unique_new_evidence = [
                            e for e in new_evidence
                            if e.get("chunk_id") and e.get("chunk_id") not in existing_chunk_ids
                        ]

                        if unique_new_evidence:
                            # Append new evidence to the confirmed feature
                            combined_evidence = existing_evidence + unique_new_evidence
                            try:
                                supabase.table("features").update({
                                    "evidence": combined_evidence,
                                    "updated_at": "now()",
                                }).eq("id", matched_id).execute()

                                merged_evidence.append({
                                    "new_name": feature_name,
                                    "matched_name": matched.get("name"),
                                    "matched_id": matched_id,
                                    "evidence_added": len(unique_new_evidence),
                                })
                                logger.info(
                                    f"Merged {len(unique_new_evidence)} new evidence items into confirmed feature '{matched.get('name')}'",
                                    extra={"feature_id": matched_id, "new_feature_name": feature_name},
                                )
                            except Exception as merge_err:
                                logger.warning(f"Failed to merge evidence into feature {matched_id}: {merge_err}")
                    continue  # Don't create duplicate - evidence was merged

            # Filter to only include valid database columns
            filtered_feature = {k: v for k, v in feature.items() if k in VALID_FEATURE_COLUMNS}
            rows.append({
                "project_id": str(project_id),
                **filtered_feature,
            })

        if merged_evidence:
            logger.info(
                f"Merged evidence into {len(merged_evidence)} confirmed features",
                extra={
                    "project_id": str(project_id),
                    "merged": merged_evidence,
                },
            )

        if not rows:
            logger.info(
                f"No new features to insert after filtering duplicates",
                extra={"project_id": str(project_id)},
            )
            return (0, confirmed_features)

        response = supabase.table("features").insert(rows).execute()

        inserted_count = len(response.data) if response.data else 0
        logger.info(
            f"Inserted {inserted_count} new features for project {project_id}",
            extra={"project_id": str(project_id), "count": inserted_count},
        )

        # Record impact tracking for inserted features with evidence
        if response.data:
            try:
                from app.db.signals import record_chunk_impacts

                for feature_data in response.data:
                    if "evidence" in feature_data and feature_data["evidence"]:
                        chunk_ids = [
                            e.get("chunk_id")
                            for e in feature_data["evidence"]
                            if e.get("chunk_id")
                        ]
                        if chunk_ids:
                            record_chunk_impacts(
                                chunk_ids=chunk_ids,
                                entity_type="feature",
                                entity_id=UUID(feature_data["id"]),
                                usage_context="evidence",
                            )
            except Exception as e:
                logger.warning(
                    f"Failed to record impact for features: {e}",
                    extra={"project_id": str(project_id)},
                )

            # Track creation of new features (non-blocking)
            try:
                from app.core.change_tracking import track_bulk_changes
                track_bulk_changes(
                    project_id=project_id,
                    entity_type="feature",
                    created_entities=response.data,
                    trigger_event="bulk_replace",
                    created_by="build_state",
                    label_field="name",
                )
            except Exception as e:
                logger.warning(
                    f"Failed to track feature creations: {e}",
                    extra={"project_id": str(project_id)},
                )

        return (inserted_count, confirmed_features)

    except Exception as e:
        logger.error(f"Failed to replace features for project {project_id}: {e}")
        raise


def list_features(project_id: UUID) -> list[dict[str, Any]]:
    """
    List all features for a project.

    Args:
        project_id: Project UUID

    Returns:
        List of feature dicts ordered by created_at desc

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("features")
            .select("*")
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(f"Failed to list features for project {project_id}: {e}")
        raise


def patch_feature_details(
    feature_id: UUID,
    details: dict[str, Any],
    model: str | None = None,
    prompt_version: str | None = None,
    schema_version: str | None = None,
) -> dict[str, Any]:
    """
    Patch the details column of a feature with enrichment data.

    Args:
        feature_id: Feature UUID
        details: The enrichment details to store
        model: Optional model name used for enrichment
        prompt_version: Optional prompt version used
        schema_version: Optional schema version used

    Returns:
        Updated feature dict

    Raises:
        ValueError: If feature not found
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        # Prepare update payload
        update_data = {
            "details": details,
            "details_updated_at": "now()",
        }

        if model:
            update_data["details_model"] = model
        if prompt_version:
            update_data["details_prompt_version"] = prompt_version
        if schema_version:
            update_data["details_schema_version"] = schema_version

        response = supabase.table("features").update(update_data).eq("id", str(feature_id)).execute()

        if not response.data:
            raise ValueError(f"Feature not found: {feature_id}")

        updated_feature = response.data[0]
        logger.info(f"Updated details for feature {feature_id}")

        return updated_feature

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Failed to patch details for feature {feature_id}: {e}")
        raise


def list_features_needing_enrichment(
    project_id: UUID,
    only_mvp: bool = False,
    max_age_days: int | None = None,
) -> list[dict[str, Any]]:
    """
    List features that could benefit from enrichment.

    Args:
        project_id: Project UUID
        only_mvp: Whether to only return MVP features
        max_age_days: Only return features not enriched in this many days (None = all)

    Returns:
        List of features that could be enriched

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        query = supabase.table("features").select("*").eq("project_id", str(project_id))

        # Filter MVP if requested
        if only_mvp:
            query = query.eq("is_mvp", True)

        # Order by those not recently enriched first
        query = query.order("details_updated_at", nulls_first=True, desc=False)

        response = query.execute()

        features = response.data or []

        # Filter by max_age_days if specified
        if max_age_days is not None:
            # This would require more complex filtering in Python
            # For now, return all and let the caller filter
            pass

        logger.info(f"Found {len(features)} features for potential enrichment")

        return features

    except Exception as e:
        logger.error(f"Failed to list features needing enrichment for project {project_id}: {e}")
        raise


def update_feature_lifecycle(
    feature_id: UUID,
    lifecycle_stage: str,
    confirmed_evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Update the lifecycle stage of a feature.

    Args:
        feature_id: Feature UUID
        lifecycle_stage: New lifecycle stage (discovered, refined, confirmed)
        confirmed_evidence: Optional evidence when confirming feature

    Returns:
        Updated feature dict

    Raises:
        ValueError: If feature not found or invalid stage
        Exception: If database operation fails
    """
    supabase = get_supabase()

    # Validate lifecycle stage
    valid_stages = ["discovered", "refined", "confirmed"]
    if lifecycle_stage not in valid_stages:
        raise ValueError(f"Invalid lifecycle stage: {lifecycle_stage}. Must be one of {valid_stages}")

    try:
        update_data = {"lifecycle_stage": lifecycle_stage}

        # If confirming, add evidence and timestamp
        if lifecycle_stage == "confirmed":
            update_data["confirmed_evidence"] = confirmed_evidence or []
            update_data["confirmation_date"] = "now()"

        response = (
            supabase.table("features")
            .update(update_data)
            .eq("id", str(feature_id))
            .execute()
        )

        if not response.data:
            raise ValueError(f"Feature not found: {feature_id}")

        updated_feature = response.data[0]
        logger.info(
            f"Updated feature {feature_id} to lifecycle stage {lifecycle_stage}",
            extra={"feature_id": str(feature_id), "lifecycle_stage": lifecycle_stage},
        )

        return updated_feature

    except ValueError:
        raise
    except Exception as e:
        logger.error(
            f"Failed to update lifecycle for feature {feature_id}: {e}",
            extra={"feature_id": str(feature_id)},
        )
        raise


def list_features_by_lifecycle(
    project_id: UUID,
    lifecycle_stage: str | None = None,
) -> list[dict[str, Any]]:
    """
    List features filtered by lifecycle stage.

    Args:
        project_id: Project UUID
        lifecycle_stage: Optional stage filter (discovered, refined, confirmed)

    Returns:
        List of features ordered by created_at desc

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        query = (
            supabase.table("features")
            .select("*")
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
        )

        if lifecycle_stage:
            query = query.eq("lifecycle_stage", lifecycle_stage)

        response = query.execute()

        features = response.data or []
        logger.info(
            f"Found {len(features)} features with lifecycle stage {lifecycle_stage or 'all'}",
            extra={"project_id": str(project_id), "lifecycle_stage": lifecycle_stage},
        )

        return features

    except Exception as e:
        logger.error(
            f"Failed to list features by lifecycle for project {project_id}: {e}",
            extra={"project_id": str(project_id)},
        )
        raise


def get_feature(feature_id: UUID) -> dict[str, Any]:
    """
    Get feature by ID.

    Args:
        feature_id: Feature UUID

    Returns:
        Feature dict with all fields

    Raises:
        ValueError: If feature not found
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("features")
            .select("*")
            .eq("id", str(feature_id))
            .maybe_single()
            .execute()
        )

        if not response.data:
            raise ValueError(f"Feature {feature_id} not found")

        return response.data

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Failed to get feature {feature_id}: {e}")
        raise


def update_feature_status(
    feature_id: UUID,
    status: str,
) -> dict[str, Any]:
    """
    Update the confirmation status of a feature.

    Args:
        feature_id: Feature UUID
        status: New confirmation status (ai_generated, confirmed_consultant, needs_client, confirmed_client)

    Returns:
        Updated feature dict

    Raises:
        ValueError: If feature not found
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        # Update BOTH status and confirmation_status columns
        response = (
            supabase.table("features")
            .update({
                "status": status,
                "confirmation_status": status,  # This was missing - causing persistence bug
                "updated_at": "now()"
            })
            .eq("id", str(feature_id))
            .execute()
        )

        if not response.data:
            raise ValueError(f"Feature not found: {feature_id}")

        updated_feature = response.data[0]
        logger.info(
            f"Updated feature {feature_id} status to {status}",
            extra={"feature_id": str(feature_id), "status": status},
        )

        return updated_feature

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Failed to update feature {feature_id} status: {e}")
        raise


def update_feature(
    feature_id: UUID,
    updates: dict[str, Any],
    run_id: UUID | None = None,
    source_signal_id: UUID | None = None,
    trigger_event: str = "manual_update",
) -> dict[str, Any]:
    """
    Update feature fields.

    This function is used by the A-Team agent to apply surgical patches
    to features. It updates only the specified fields.

    Args:
        feature_id: Feature UUID to update
        updates: Dict of field → new value
        run_id: Optional run ID for tracking
        source_signal_id: Optional signal that triggered this update
        trigger_event: What triggered this update (default: manual_update)

    Returns:
        Updated feature dict

    Raises:
        ValueError: If feature not found
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        # Get current state BEFORE update for change tracking
        old_feature = get_feature(feature_id)

        # Add updated_at timestamp
        update_data = {**updates, "updated_at": "now()"}

        response = (
            supabase.table("features")
            .update(update_data)
            .eq("id", str(feature_id))
            .execute()
        )

        if not response.data:
            raise ValueError(f"Failed to update feature {feature_id}")

        updated_feature = response.data[0]
        logger.info(
            f"Updated feature {feature_id}",
            extra={"feature_id": str(feature_id), "fields_updated": list(updates.keys())},
        )

        # Track change (non-blocking)
        try:
            from app.core.change_tracking import track_entity_change
            track_entity_change(
                project_id=UUID(old_feature["project_id"]),
                entity_type="feature",
                entity_id=feature_id,
                entity_label=old_feature.get("name", str(feature_id)),
                old_entity=old_feature,
                new_entity=updated_feature,
                trigger_event=trigger_event,
                source_signal_id=source_signal_id,
                run_id=run_id,
                created_by="system",
            )
        except Exception as track_err:
            logger.warning(f"Failed to track feature change: {track_err}")

        return updated_feature

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Failed to update feature {feature_id}: {e}")
        raise


def update_feature_enrichment(
    feature_id: UUID,
    overview: str,
    target_personas: list[dict[str, Any]],
    user_actions: list[str],
    system_behaviors: list[str],
    ui_requirements: list[str],
    rules: list[str],
    integrations: list[str],
) -> dict[str, Any]:
    """
    Update a feature with v2 enrichment data.

    Args:
        feature_id: Feature UUID to update
        overview: Business-friendly description
        target_personas: List of {persona_id, persona_name, role, context}
        user_actions: Step-by-step user actions
        system_behaviors: Behind-the-scenes system behaviors
        ui_requirements: What the user sees
        rules: Simple business rules
        integrations: External system names

    Returns:
        Updated feature dict

    Raises:
        ValueError: If feature not found
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        update_data = {
            "overview": overview,
            "target_personas": target_personas,
            "user_actions": user_actions,
            "system_behaviors": system_behaviors,
            "ui_requirements": ui_requirements,
            "rules": rules,
            "integrations": integrations,
            "enrichment_status": "enriched",
            "enriched_at": "now()",
            "updated_at": "now()",
        }

        response = (
            supabase.table("features")
            .update(update_data)
            .eq("id", str(feature_id))
            .execute()
        )

        if not response.data:
            raise ValueError(f"Feature not found: {feature_id}")

        updated_feature = response.data[0]
        logger.info(
            f"Enriched feature {feature_id}",
            extra={"feature_id": str(feature_id)},
        )

        return updated_feature

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Failed to enrich feature {feature_id}: {e}")
        raise


def list_features_for_enrichment(
    project_id: UUID,
    only_unenriched: bool = True,
) -> list[dict[str, Any]]:
    """
    List features eligible for v2 enrichment.

    Args:
        project_id: Project UUID
        only_unenriched: If True, only return features with enrichment_status='none'

    Returns:
        List of feature dicts

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        query = (
            supabase.table("features")
            .select("*")
            .eq("project_id", str(project_id))
            .order("is_mvp", desc=True)  # MVP features first
            .order("created_at", desc=True)
        )

        if only_unenriched:
            query = query.eq("enrichment_status", "none")

        response = query.execute()

        features = response.data or []
        logger.info(
            f"Found {len(features)} features for enrichment",
            extra={"project_id": str(project_id), "only_unenriched": only_unenriched},
        )

        return features

    except Exception as e:
        logger.error(f"Failed to list features for enrichment: {e}")
        raise

