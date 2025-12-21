"""Features database operations."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def bulk_replace_features(
    project_id: UUID,
    features: list[dict[str, Any]],
) -> int:
    """
    Replace all features for a project with a new batch.

    This is a bulk operation that:
    1. Deletes all existing features for the project
    2. Inserts the new feature batch

    Args:
        project_id: Project UUID
        features: List of feature dicts (name, category, is_mvp, confidence, status, evidence)

    Returns:
        Number of features inserted

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        # Step 1: Delete existing features
        supabase.table("features").delete().eq("project_id", str(project_id)).execute()

        logger.info(
            f"Deleted existing features for project {project_id}",
            extra={"project_id": str(project_id)},
        )

        # Step 2: Insert new features (if any)
        if not features:
            return 0

        # Add project_id to each feature
        rows = []
        for feature in features:
            rows.append({
                "project_id": str(project_id),
                **feature,
            })

        response = supabase.table("features").insert(rows).execute()

        inserted_count = len(response.data) if response.data else 0
        logger.info(
            f"Inserted {inserted_count} features for project {project_id}",
            extra={"project_id": str(project_id), "count": inserted_count},
        )
        return inserted_count

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

