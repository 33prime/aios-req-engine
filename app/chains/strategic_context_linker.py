"""Strategic context linker - connect strategic context to source entities."""

from datetime import datetime, timezone
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def link_risk_to_features(
    project_id: UUID,
    risk_index: int,
    feature_ids: list[UUID],
) -> dict:
    """
    Link a risk in strategic context to specific features.

    Args:
        project_id: Project UUID
        risk_index: Index of the risk in the risks array
        feature_ids: List of feature UUIDs to link

    Returns:
        Updated strategic context dict
    """
    from app.db.strategic_context import get_strategic_context

    context = get_strategic_context(project_id)
    if not context:
        raise ValueError(f"Strategic context not found for project {project_id}")

    risks = context.get("risks") or []
    if risk_index < 0 or risk_index >= len(risks):
        raise ValueError(f"Invalid risk index: {risk_index}")

    # Update the risk with linked feature IDs
    risks[risk_index]["linked_feature_ids"] = [str(fid) for fid in feature_ids]

    # Save back to database
    supabase = get_supabase()
    response = (
        supabase.table("strategic_context")
        .update({
            "risks": risks,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", context["id"])
        .execute()
    )

    logger.info(
        f"Linked risk {risk_index} to {len(feature_ids)} features",
        extra={"project_id": str(project_id)},
    )

    return response.data[0] if response.data else context


def link_success_metric_to_vp_steps(
    project_id: UUID,
    metric_index: int,
    vp_step_ids: list[UUID],
) -> dict:
    """
    Link a success metric in strategic context to specific VP steps.

    Args:
        project_id: Project UUID
        metric_index: Index of the metric in success_metrics array
        vp_step_ids: List of VP step UUIDs to link

    Returns:
        Updated strategic context dict
    """
    from app.db.strategic_context import get_strategic_context

    context = get_strategic_context(project_id)
    if not context:
        raise ValueError(f"Strategic context not found for project {project_id}")

    metrics = context.get("success_metrics") or []
    if metric_index < 0 or metric_index >= len(metrics):
        raise ValueError(f"Invalid metric index: {metric_index}")

    # Update the metric with linked VP step IDs
    metrics[metric_index]["linked_vp_step_ids"] = [str(sid) for sid in vp_step_ids]

    # Save back to database
    supabase = get_supabase()
    response = (
        supabase.table("strategic_context")
        .update({
            "success_metrics": metrics,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", context["id"])
        .execute()
    )

    logger.info(
        f"Linked success metric {metric_index} to {len(vp_step_ids)} VP steps",
        extra={"project_id": str(project_id)},
    )

    return response.data[0] if response.data else context


def link_stakeholder_to_persona(
    project_id: UUID,
    stakeholder_id: UUID,
    persona_id: UUID,
) -> dict:
    """
    Link a stakeholder to a persona.

    Args:
        project_id: Project UUID
        stakeholder_id: Stakeholder UUID
        persona_id: Persona UUID to link

    Returns:
        Updated stakeholder dict
    """
    from app.db.stakeholders import update_stakeholder

    result = update_stakeholder(
        stakeholder_id,
        {"linked_persona_id": str(persona_id)},
    )

    # Also register in dependency graph
    from app.db.entity_dependencies import register_dependency

    register_dependency(
        project_id=project_id,
        source_type="stakeholder",
        source_id=stakeholder_id,
        target_type="persona",
        target_id=persona_id,
        dependency_type="informed_by",
    )

    logger.info(
        f"Linked stakeholder {stakeholder_id} to persona {persona_id}",
        extra={"project_id": str(project_id)},
    )

    return result


def track_source_entities(
    project_id: UUID,
    source_entities: dict,
) -> dict:
    """
    Update the source_entities field on strategic context.

    Args:
        project_id: Project UUID
        source_entities: Dict with:
            - personas: [{id, name, contribution}]
            - features: [{id, name, contribution}]
            - vp_steps: [{id, label, contribution}]

    Returns:
        Updated strategic context dict
    """
    from app.db.strategic_context import get_strategic_context

    context = get_strategic_context(project_id)
    if not context:
        raise ValueError(f"Strategic context not found for project {project_id}")

    supabase = get_supabase()
    response = (
        supabase.table("strategic_context")
        .update({
            "source_entities": source_entities,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", context["id"])
        .execute()
    )

    # Register dependencies for each source entity
    from app.db.entity_dependencies import register_dependency

    context_id = UUID(context["id"])

    for persona in source_entities.get("personas", []):
        if persona.get("id"):
            register_dependency(
                project_id=project_id,
                source_type="strategic_context",
                source_id=context_id,
                target_type="persona",
                target_id=UUID(persona["id"]),
                dependency_type="informed_by",
            )

    for feature in source_entities.get("features", []):
        if feature.get("id"):
            register_dependency(
                project_id=project_id,
                source_type="strategic_context",
                source_id=context_id,
                target_type="feature",
                target_id=UUID(feature["id"]),
                dependency_type="informed_by",
            )

    for step in source_entities.get("vp_steps", []):
        if step.get("id"):
            register_dependency(
                project_id=project_id,
                source_type="strategic_context",
                source_id=context_id,
                target_type="vp_step",
                target_id=UUID(step["id"]),
                dependency_type="informed_by",
            )

    logger.info(
        f"Tracked {len(source_entities.get('personas', []))} personas, "
        f"{len(source_entities.get('features', []))} features, "
        f"{len(source_entities.get('vp_steps', []))} VP steps as sources",
        extra={"project_id": str(project_id)},
    )

    return response.data[0] if response.data else context


def get_strategic_context_sources(project_id: UUID) -> dict:
    """
    Get which entities informed the strategic context.

    Returns:
        Dict with source entities and their contributions
    """
    from app.db.strategic_context import get_strategic_context

    context = get_strategic_context(project_id)
    if not context:
        return {"personas": [], "features": [], "vp_steps": [], "found": False}

    source_entities = context.get("source_entities") or {}

    return {
        "personas": source_entities.get("personas", []),
        "features": source_entities.get("features", []),
        "vp_steps": source_entities.get("vp_steps", []),
        "found": True,
    }


def get_linked_features_for_risk(
    project_id: UUID,
    risk_index: int,
) -> list[dict]:
    """
    Get the features linked to a specific risk.

    Args:
        project_id: Project UUID
        risk_index: Index of the risk

    Returns:
        List of feature dicts
    """
    from app.db.features import get_feature
    from app.db.strategic_context import get_strategic_context

    context = get_strategic_context(project_id)
    if not context:
        return []

    risks = context.get("risks") or []
    if risk_index < 0 or risk_index >= len(risks):
        return []

    risk = risks[risk_index]
    linked_ids = risk.get("linked_feature_ids") or []

    features = []
    for fid in linked_ids:
        feature = get_feature(UUID(fid))
        if feature:
            features.append(feature)

    return features


def get_linked_vp_steps_for_metric(
    project_id: UUID,
    metric_index: int,
) -> list[dict]:
    """
    Get the VP steps linked to a specific success metric.

    Args:
        project_id: Project UUID
        metric_index: Index of the metric

    Returns:
        List of VP step dicts
    """
    from app.db.strategic_context import get_strategic_context
    from app.db.vp_steps import get_vp_step

    context = get_strategic_context(project_id)
    if not context:
        return []

    metrics = context.get("success_metrics") or []
    if metric_index < 0 or metric_index >= len(metrics):
        return []

    metric = metrics[metric_index]
    linked_ids = metric.get("linked_vp_step_ids") or []

    steps = []
    for sid in linked_ids:
        step = get_vp_step(UUID(sid))
        if step:
            steps.append(step)

    return steps


def auto_link_strategic_context(project_id: UUID) -> dict:
    """
    Automatically link strategic context elements to relevant entities.

    Uses heuristics to match:
    - Risks with technical/business category -> features
    - Success metrics mentioning features -> VP steps using those features
    - Stakeholders -> personas with matching roles

    Returns:
        Dict with counts of auto-linked items
    """
    from app.db.features import list_features
    from app.db.personas import list_personas
    from app.db.stakeholders import list_stakeholders
    from app.db.strategic_context import get_strategic_context
    from app.db.vp_steps import list_vp_steps

    context = get_strategic_context(project_id)
    if not context:
        return {"error": "No strategic context found"}

    features = list_features(project_id)
    personas = list_personas(project_id)
    vp_steps = list_vp_steps(project_id)
    stakeholders = list_stakeholders(project_id)

    stats = {
        "risks_linked": 0,
        "metrics_linked": 0,
        "stakeholders_linked": 0,
    }

    # Create lookup maps
    feature_names = {f["name"].lower(): f["id"] for f in features}
    persona_names = {p["name"].lower(): p["id"] for p in personas}

    # Auto-link risks to features (match feature names in risk description)
    risks = context.get("risks") or []
    for i, risk in enumerate(risks):
        desc = (risk.get("description") or "").lower()
        matched_features = []
        for fname, fid in feature_names.items():
            if fname in desc:
                matched_features.append(fid)

        if matched_features and not risk.get("linked_feature_ids"):
            link_risk_to_features(project_id, i, [UUID(fid) for fid in matched_features])
            stats["risks_linked"] += 1

    # Auto-link success metrics to VP steps
    # Match metrics that mention features to VP steps using those features
    metrics = context.get("success_metrics") or []
    for i, metric in enumerate(metrics):
        metric_text = (metric.get("metric") or "").lower()
        matched_steps = []

        for step in vp_steps:
            features_used = step.get("features_used") or []
            for fu in features_used:
                fname = fu.get("feature_name", "").lower() if isinstance(fu, dict) else ""
                if fname and fname in metric_text:
                    matched_steps.append(step["id"])
                    break

        if matched_steps and not metric.get("linked_vp_step_ids"):
            link_success_metric_to_vp_steps(project_id, i, [UUID(sid) for sid in matched_steps])
            stats["metrics_linked"] += 1

    # Auto-link stakeholders to personas
    for stakeholder in stakeholders:
        if stakeholder.get("linked_persona_id"):
            continue  # Already linked

        sh_name = stakeholder.get("name", "").lower()
        sh_role = (stakeholder.get("role") or "").lower()

        for pname, pid in persona_names.items():
            # Match by name similarity or role
            if pname in sh_name or sh_name in pname:
                link_stakeholder_to_persona(project_id, UUID(stakeholder["id"]), UUID(pid))
                stats["stakeholders_linked"] += 1
                break

    logger.info(
        f"Auto-linked: {stats['risks_linked']} risks, "
        f"{stats['metrics_linked']} metrics, {stats['stakeholders_linked']} stakeholders",
        extra={"project_id": str(project_id)},
    )

    return stats
