"""Cascade impact analysis and delete operations."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


# Threshold for suggesting bulk rebuild instead of cascade cleanup
BULK_REBUILD_THRESHOLD = 0.5  # 50%


def get_feature_cascade_impact(feature_id: UUID) -> dict[str, Any]:
    """
    Calculate the cascade impact of deleting a feature.

    Returns affected:
    - VP steps that reference this feature
    - Personas that have this feature in related_features
    - Total entity counts for threshold calculation

    Args:
        feature_id: Feature UUID

    Returns:
        Dict with impact analysis including:
        - feature: The feature being deleted
        - affected_vp_steps: List of VP steps referencing this feature
        - affected_personas: List of personas with this feature
        - total_vp_steps: Total VP steps in project
        - total_personas: Total personas in project
        - impact_percentage: Percentage of entities affected
        - suggest_bulk_rebuild: True if impact exceeds threshold
    """
    supabase = get_supabase()

    try:
        # Get the feature
        feature_response = (
            supabase.table("features")
            .select("*")
            .eq("id", str(feature_id))
            .maybe_single()
            .execute()
        )

        if not feature_response.data:
            raise ValueError(f"Feature not found: {feature_id}")

        feature = feature_response.data
        project_id = feature["project_id"]
        feature_name = feature.get("name", "Unknown")

        # Get all VP steps for project
        vp_response = (
            supabase.table("vp_steps")
            .select("id, step_index, label, needed, description")
            .eq("project_id", project_id)
            .execute()
        )
        all_vp_steps = vp_response.data or []

        # Get all personas for project
        personas_response = (
            supabase.table("personas")
            .select("id, name, slug, related_features, goals")
            .eq("project_id", project_id)
            .execute()
        )
        all_personas = personas_response.data or []

        # Find affected VP steps (those that mention feature name in description/needed)
        affected_vp_steps = []
        feature_name_lower = feature_name.lower()

        for step in all_vp_steps:
            is_affected = False

            # Check description
            description = (step.get("description") or "").lower()
            if feature_name_lower in description:
                is_affected = True

            # Check needed items
            needed = step.get("needed") or []
            for needed_item in needed:
                if isinstance(needed_item, dict):
                    ask = (needed_item.get("ask") or "").lower()
                    why = (needed_item.get("why") or "").lower()
                    if feature_name_lower in ask or feature_name_lower in why:
                        is_affected = True
                        break

            if is_affected:
                affected_vp_steps.append({
                    "id": step["id"],
                    "step_index": step["step_index"],
                    "label": step.get("label", f"Step {step['step_index']}"),
                })

        # Find affected personas (those with this feature in related_features)
        affected_personas = []
        for persona in all_personas:
            related = persona.get("related_features") or []
            if str(feature_id) in [str(r) for r in related]:
                affected_personas.append({
                    "id": persona["id"],
                    "name": persona.get("name", "Unknown"),
                    "slug": persona.get("slug"),
                })

        # Also check target_personas on the feature itself
        target_personas = feature.get("target_personas") or []
        for tp in target_personas:
            if isinstance(tp, dict):
                persona_id = tp.get("persona_id")
                if persona_id and persona_id not in [p["id"] for p in affected_personas]:
                    # Find the persona
                    for persona in all_personas:
                        if persona["id"] == persona_id:
                            affected_personas.append({
                                "id": persona["id"],
                                "name": persona.get("name", "Unknown"),
                                "slug": persona.get("slug"),
                            })
                            break

        # Calculate impact percentage
        total_entities = len(all_vp_steps) + len(all_personas)
        affected_entities = len(affected_vp_steps) + len(affected_personas)
        impact_percentage = affected_entities / total_entities if total_entities > 0 else 0

        return {
            "feature": {
                "id": str(feature_id),
                "name": feature_name,
                "category": feature.get("category"),
                "is_mvp": feature.get("is_mvp"),
            },
            "affected_vp_steps": affected_vp_steps,
            "affected_personas": affected_personas,
            "total_vp_steps": len(all_vp_steps),
            "total_personas": len(all_personas),
            "affected_vp_count": len(affected_vp_steps),
            "affected_persona_count": len(affected_personas),
            "impact_percentage": round(impact_percentage * 100, 1),
            "suggest_bulk_rebuild": impact_percentage >= BULK_REBUILD_THRESHOLD,
        }

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Failed to calculate cascade impact for feature {feature_id}: {e}")
        raise


def delete_feature_with_cascade(
    feature_id: UUID,
    cleanup_references: bool = True,
) -> dict[str, Any]:
    """
    Delete a feature and optionally clean up references.

    Hard delete - the feature is permanently removed.

    If cleanup_references is True:
    - Remove feature from personas' related_features arrays
    - Leave VP steps intact (they just lose the implicit link)

    Args:
        feature_id: Feature UUID
        cleanup_references: Whether to clean up references (default True)

    Returns:
        Dict with deletion results
    """
    supabase = get_supabase()

    try:
        # Get feature first (for logging and cleanup)
        feature_response = (
            supabase.table("features")
            .select("*")
            .eq("id", str(feature_id))
            .maybe_single()
            .execute()
        )

        if not feature_response.data:
            raise ValueError(f"Feature not found: {feature_id}")

        feature = feature_response.data
        project_id = feature["project_id"]
        feature_name = feature.get("name", "Unknown")

        cleaned_personas = []

        if cleanup_references:
            # Find and update personas that reference this feature
            personas_response = (
                supabase.table("personas")
                .select("id, name, related_features")
                .eq("project_id", project_id)
                .execute()
            )

            for persona in (personas_response.data or []):
                related = persona.get("related_features") or []
                if str(feature_id) in [str(r) for r in related]:
                    # Remove the feature from related_features
                    new_related = [r for r in related if str(r) != str(feature_id)]
                    supabase.table("personas").update({
                        "related_features": new_related,
                        "updated_at": "now()",
                    }).eq("id", persona["id"]).execute()

                    cleaned_personas.append({
                        "id": persona["id"],
                        "name": persona.get("name"),
                    })

        # Delete the feature
        supabase.table("features").delete().eq("id", str(feature_id)).execute()

        logger.info(
            f"Deleted feature {feature_id} ({feature_name})",
            extra={
                "feature_id": str(feature_id),
                "feature_name": feature_name,
                "cleaned_personas": len(cleaned_personas),
            }
        )

        # Track deletion in revisions
        try:
            from app.core.change_tracking import track_entity_change
            track_entity_change(
                project_id=UUID(project_id),
                entity_type="feature",
                entity_id=feature_id,
                entity_label=feature_name,
                old_entity=feature,
                new_entity=None,  # Deleted
                trigger_event="deleted",
                created_by="user",
            )
        except Exception as track_err:
            logger.warning(f"Failed to track feature deletion: {track_err}")

        return {
            "deleted": True,
            "feature_id": str(feature_id),
            "feature_name": feature_name,
            "cleaned_personas": cleaned_personas,
            "cleaned_persona_count": len(cleaned_personas),
        }

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Failed to delete feature {feature_id}: {e}")
        raise


def get_persona_cascade_impact(persona_id: UUID) -> dict[str, Any]:
    """
    Calculate the cascade impact of deleting a persona.

    Returns affected:
    - Features that have this persona in target_personas
    - VP steps that reference this persona
    - Total entity counts for threshold calculation

    Args:
        persona_id: Persona UUID

    Returns:
        Dict with impact analysis
    """
    supabase = get_supabase()

    try:
        # Get the persona
        persona_response = (
            supabase.table("personas")
            .select("*")
            .eq("id", str(persona_id))
            .maybe_single()
            .execute()
        )

        if not persona_response.data:
            raise ValueError(f"Persona not found: {persona_id}")

        persona = persona_response.data
        project_id = persona["project_id"]
        persona_name = persona.get("name", "Unknown")

        # Get all features for project
        features_response = (
            supabase.table("features")
            .select("id, name, category, target_personas")
            .eq("project_id", project_id)
            .execute()
        )
        all_features = features_response.data or []

        # Get all VP steps for project
        vp_response = (
            supabase.table("vp_steps")
            .select("id, step_index, label, description")
            .eq("project_id", project_id)
            .execute()
        )
        all_vp_steps = vp_response.data or []

        # Get all personas
        all_personas_response = (
            supabase.table("personas")
            .select("id")
            .eq("project_id", project_id)
            .execute()
        )
        total_personas = len(all_personas_response.data or [])

        # Find affected features (those with this persona in target_personas)
        affected_features = []
        for feature in all_features:
            target_personas = feature.get("target_personas") or []
            for tp in target_personas:
                if isinstance(tp, dict) and tp.get("persona_id") == str(persona_id):
                    affected_features.append({
                        "id": feature["id"],
                        "name": feature.get("name", "Unknown"),
                        "category": feature.get("category"),
                    })
                    break

        # Find affected VP steps (those that mention persona name)
        affected_vp_steps = []
        persona_name_lower = persona_name.lower()

        for step in all_vp_steps:
            description = (step.get("description") or "").lower()
            label = (step.get("label") or "").lower()

            if persona_name_lower in description or persona_name_lower in label:
                affected_vp_steps.append({
                    "id": step["id"],
                    "step_index": step["step_index"],
                    "label": step.get("label", f"Step {step['step_index']}"),
                })

        # Calculate impact percentage
        total_entities = len(all_features) + len(all_vp_steps)
        affected_entities = len(affected_features) + len(affected_vp_steps)
        impact_percentage = affected_entities / total_entities if total_entities > 0 else 0

        return {
            "persona": {
                "id": str(persona_id),
                "name": persona_name,
                "slug": persona.get("slug"),
                "role": persona.get("role"),
            },
            "affected_features": affected_features,
            "affected_vp_steps": affected_vp_steps,
            "total_features": len(all_features),
            "total_vp_steps": len(all_vp_steps),
            "total_personas": total_personas,
            "affected_feature_count": len(affected_features),
            "affected_vp_count": len(affected_vp_steps),
            "impact_percentage": round(impact_percentage * 100, 1),
            "suggest_bulk_rebuild": impact_percentage >= BULK_REBUILD_THRESHOLD,
        }

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Failed to calculate cascade impact for persona {persona_id}: {e}")
        raise


def delete_persona_with_cascade(
    persona_id: UUID,
    cleanup_references: bool = True,
) -> dict[str, Any]:
    """
    Delete a persona and optionally clean up references.

    Hard delete - the persona is permanently removed.

    If cleanup_references is True:
    - Remove persona from features' target_personas arrays
    - Leave VP steps intact (they just lose the implicit link)

    Args:
        persona_id: Persona UUID
        cleanup_references: Whether to clean up references (default True)

    Returns:
        Dict with deletion results
    """
    supabase = get_supabase()

    try:
        # Get persona first
        persona_response = (
            supabase.table("personas")
            .select("*")
            .eq("id", str(persona_id))
            .maybe_single()
            .execute()
        )

        if not persona_response.data:
            raise ValueError(f"Persona not found: {persona_id}")

        persona = persona_response.data
        project_id = persona["project_id"]
        persona_name = persona.get("name", "Unknown")

        cleaned_features = []

        if cleanup_references:
            # Find and update features that reference this persona
            features_response = (
                supabase.table("features")
                .select("id, name, target_personas")
                .eq("project_id", project_id)
                .execute()
            )

            for feature in (features_response.data or []):
                target_personas = feature.get("target_personas") or []
                matching = [tp for tp in target_personas if isinstance(tp, dict) and tp.get("persona_id") == str(persona_id)]

                if matching:
                    # Remove the persona from target_personas
                    new_target = [tp for tp in target_personas if not (isinstance(tp, dict) and tp.get("persona_id") == str(persona_id))]
                    supabase.table("features").update({
                        "target_personas": new_target,
                        "updated_at": "now()",
                    }).eq("id", feature["id"]).execute()

                    cleaned_features.append({
                        "id": feature["id"],
                        "name": feature.get("name"),
                    })

        # Delete the persona
        supabase.table("personas").delete().eq("id", str(persona_id)).execute()

        logger.info(
            f"Deleted persona {persona_id} ({persona_name})",
            extra={
                "persona_id": str(persona_id),
                "persona_name": persona_name,
                "cleaned_features": len(cleaned_features),
            }
        )

        # Track deletion in revisions
        try:
            from app.core.change_tracking import track_entity_change
            track_entity_change(
                project_id=UUID(project_id),
                entity_type="persona",
                entity_id=persona_id,
                entity_label=persona_name,
                old_entity=persona,
                new_entity=None,  # Deleted
                trigger_event="deleted",
                created_by="user",
            )
        except Exception as track_err:
            logger.warning(f"Failed to track persona deletion: {track_err}")

        return {
            "deleted": True,
            "persona_id": str(persona_id),
            "persona_name": persona_name,
            "cleaned_features": cleaned_features,
            "cleaned_feature_count": len(cleaned_features),
        }

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Failed to delete persona {persona_id}: {e}")
        raise
