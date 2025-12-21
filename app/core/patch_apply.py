"""Safe application of reconciliation patches to canonical state."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.core.schemas_reconcile import (
    ConfirmationItemSpec,
    FeatureOp,
    PRDSectionPatch,
    ReconcileOutput,
    VPStepPatch,
)
from app.db.confirmations import upsert_confirmation_item
from app.db.features import bulk_replace_features
from app.db.prd import upsert_prd_section
from app.db.vp import upsert_vp_step

logger = get_logger(__name__)


def apply_prd_patch(
    existing_section: dict[str, Any],
    patch: PRDSectionPatch,
) -> dict[str, Any]:
    """
    Apply a patch to a PRD section.

    Args:
        existing_section: Current section data
        patch: Patch to apply

    Returns:
        Updated section payload for upsert
    """
    payload = {}

    # Preserve existing fields
    if "label" in existing_section:
        payload["label"] = existing_section["label"]
    if "required" in existing_section:
        payload["required"] = existing_section["required"]
    if "status" in existing_section:
        payload["status"] = existing_section["status"]
    if "fields" in existing_section:
        payload["fields"] = existing_section["fields"].copy()
    else:
        payload["fields"] = {}
    if "client_needs" in existing_section:
        payload["client_needs"] = existing_section["client_needs"].copy()
    else:
        payload["client_needs"] = []
    if "sources" in existing_section:
        payload["sources"] = existing_section["sources"].copy()
    else:
        payload["sources"] = []
    if "evidence" in existing_section:
        payload["evidence"] = existing_section["evidence"].copy()
    else:
        payload["evidence"] = []

    # Apply set_fields (partial update to fields JSON)
    if patch.set_fields:
        payload["fields"].update(patch.set_fields)

    # Apply set_status
    if patch.set_status:
        payload["status"] = patch.set_status

    # Add client_needs
    if patch.add_client_needs:
        for need in patch.add_client_needs:
            payload["client_needs"].append(need.model_dump(mode='json'))

    # Add evidence
    if patch.evidence:
        for ev in patch.evidence:
            payload["evidence"].append(ev.model_dump(mode='json'))

    return payload


def apply_vp_patch(
    existing_step: dict[str, Any],
    patch: VPStepPatch,
) -> dict[str, Any]:
    """
    Apply a patch to a Value Path step.

    Args:
        existing_step: Current step data
        patch: Patch to apply

    Returns:
        Updated step payload for upsert
    """
    payload = {}

    # Preserve existing fields
    if "label" in existing_step:
        payload["label"] = existing_step["label"]
    if "status" in existing_step:
        payload["status"] = existing_step["status"]
    if "description" in existing_step:
        payload["description"] = existing_step["description"]
    if "user_benefit_pain" in existing_step:
        payload["user_benefit_pain"] = existing_step["user_benefit_pain"]
    if "ui_overview" in existing_step:
        payload["ui_overview"] = existing_step["ui_overview"]
    if "value_created" in existing_step:
        payload["value_created"] = existing_step["value_created"]
    if "kpi_impact" in existing_step:
        payload["kpi_impact"] = existing_step["kpi_impact"]
    if "needed" in existing_step:
        payload["needed"] = existing_step["needed"].copy()
    else:
        payload["needed"] = []
    if "sources" in existing_step:
        payload["sources"] = existing_step["sources"].copy()
    else:
        payload["sources"] = []
    if "evidence" in existing_step:
        payload["evidence"] = existing_step["evidence"].copy()
    else:
        payload["evidence"] = []

    # Apply set (fields to update)
    if patch.set:
        payload.update(patch.set)

    # Apply set_status
    if patch.set_status:
        payload["status"] = patch.set_status

    # Add needed items
    if patch.add_needed:
        for need in patch.add_needed:
            payload["needed"].append(need.model_dump(mode='json'))

    # Add evidence
    if patch.evidence:
        for ev in patch.evidence:
            payload["evidence"].append(ev.model_dump(mode='json'))

    return payload


def normalize_feature_key(name: str) -> str:
    """
    Normalize a feature name to a stable key.

    Args:
        name: Feature name

    Returns:
        Normalized key (lowercase, spaces to underscores)
    """
    return name.lower().replace(" ", "_").strip()


def apply_feature_ops(
    existing_features: list[dict[str, Any]],
    ops: list[FeatureOp],
) -> list[dict[str, Any]]:
    """
    Apply feature operations to existing features list.

    Args:
        existing_features: Current features list
        ops: List of feature operations (upsert or deprecate)

    Returns:
        New features list after applying operations
    """
    # Build a map of normalized keys to existing features
    feature_map: dict[str, dict[str, Any]] = {}
    for feature in existing_features:
        key = normalize_feature_key(feature["name"])
        feature_map[key] = feature

    # Apply operations
    for op in ops:
        key = normalize_feature_key(op.name)

        if op.op == "upsert":
            # Upsert: add or update feature
            feature_data = {
                "name": op.name,
                "category": op.category,
                "is_mvp": op.is_mvp,
                "confidence": op.confidence,
                "status": op.set_status or "draft",
                "evidence": [ev.model_dump(mode='json') for ev in op.evidence],
            }
            feature_map[key] = feature_data
            logger.info(f"Feature op: upsert {op.name} (reason: {op.reason})")

        elif op.op == "deprecate":
            # Deprecate: remove from map
            if key in feature_map:
                del feature_map[key]
                logger.info(f"Feature op: deprecate {op.name} (reason: {op.reason})")

    # Return as list
    return list(feature_map.values())


def apply_reconcile_patches(
    project_id: UUID,
    reconcile_output: ReconcileOutput,
    canonical_snapshot: dict[str, Any],
    run_id: UUID,
    job_id: UUID | None,
) -> dict[str, int]:
    """
    Apply all patches from reconciliation output to database.

    Args:
        project_id: Project UUID
        reconcile_output: Reconciliation output from LLM
        canonical_snapshot: Current canonical state
        run_id: Run tracking UUID
        job_id: Optional job UUID

    Returns:
        Dict with counts of changes by type
    """
    logger.info(
        f"Applying reconciliation patches for project {project_id}",
        extra={
            "run_id": str(run_id),
            "project_id": str(project_id),
            "prd_patches": len(reconcile_output.prd_section_patches),
            "vp_patches": len(reconcile_output.vp_step_patches),
            "feature_ops": len(reconcile_output.feature_ops),
            "confirmation_items": len(reconcile_output.confirmation_items),
        },
    )

    counts = {
        "prd_sections_updated": 0,
        "vp_steps_updated": 0,
        "features_updated": 0,
        "confirmations_created": 0,
    }

    # Apply PRD section patches
    prd_sections_map = {s["slug"]: s for s in canonical_snapshot["prd_sections"]}
    for patch in reconcile_output.prd_section_patches:
        existing = prd_sections_map.get(patch.slug, {})
        payload = apply_prd_patch(existing, patch)
        upsert_prd_section(project_id, patch.slug, payload)
        counts["prd_sections_updated"] += 1

    # Apply VP step patches
    vp_steps_map = {s["step_index"]: s for s in canonical_snapshot["vp_steps"]}
    for patch in reconcile_output.vp_step_patches:
        existing = vp_steps_map.get(patch.step_index, {})
        payload = apply_vp_patch(existing, patch)
        upsert_vp_step(project_id, patch.step_index, payload)
        counts["vp_steps_updated"] += 1

    # Apply feature operations
    if reconcile_output.feature_ops:
        existing_features = canonical_snapshot["features"]
        new_features = apply_feature_ops(existing_features, reconcile_output.feature_ops)
        bulk_replace_features(project_id, new_features)
        counts["features_updated"] = len(reconcile_output.feature_ops)

    # Create confirmation items
    created_from = {
        "run_id": str(run_id),
        "job_id": str(job_id) if job_id else None,
    }

    for item_spec in reconcile_output.confirmation_items:
        payload = {
            "kind": item_spec.kind,
            "target_table": item_spec.target_table,
            "target_id": item_spec.target_id,
            "title": item_spec.title,
            "why": item_spec.why,
            "ask": item_spec.ask,
            "status": "open",
            "suggested_method": item_spec.suggested_method,
            "priority": item_spec.priority,
            "evidence": [ev.model_dump(mode='json') for ev in item_spec.evidence],
            "created_from": created_from,
        }
        upsert_confirmation_item(project_id, item_spec.key, payload)
        counts["confirmations_created"] += 1

    logger.info(
        f"Applied reconciliation patches: {counts}",
        extra={"run_id": str(run_id), "project_id": str(project_id)},
    )

    return counts

