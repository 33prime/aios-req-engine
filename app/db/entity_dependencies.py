"""Database operations for entity dependency graph."""

from datetime import UTC, datetime
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


# Valid entity types
SOURCE_ENTITY_TYPES = {"persona", "feature", "vp_step", "strategic_context", "stakeholder", "data_entity", "business_driver", "unlock"}
TARGET_ENTITY_TYPES = {"persona", "feature", "vp_step", "signal", "research_chunk", "data_entity", "business_driver", "unlock"}
DEPENDENCY_TYPES = {"uses", "targets", "derived_from", "informed_by", "actor_of", "spawns", "enables", "constrains"}


def register_dependency(
    project_id: UUID,
    source_type: str,
    source_id: UUID,
    target_type: str,
    target_id: UUID,
    dependency_type: str,
    strength: float = 1.0,
) -> dict:
    """
    Register a dependency between two entities.

    Args:
        project_id: Project UUID
        source_type: Type of entity that depends on target
        source_id: UUID of source entity
        target_type: Type of entity being depended on
        target_id: UUID of target entity
        dependency_type: Nature of dependency (uses, targets, derived_from, etc.)
        strength: Dependency strength 0-1 (default 1.0)

    Returns:
        Created or updated dependency dict
    """
    if source_type not in SOURCE_ENTITY_TYPES:
        raise ValueError(f"Invalid source_type: {source_type}")
    if target_type not in TARGET_ENTITY_TYPES:
        raise ValueError(f"Invalid target_type: {target_type}")
    if dependency_type not in DEPENDENCY_TYPES:
        raise ValueError(f"Invalid dependency_type: {dependency_type}")
    if not 0 <= strength <= 1:
        raise ValueError(f"Strength must be between 0 and 1, got {strength}")

    supabase = get_supabase()

    # Use upsert to handle both create and update
    data = {
        "project_id": str(project_id),
        "source_entity_type": source_type,
        "source_entity_id": str(source_id),
        "target_entity_type": target_type,
        "target_entity_id": str(target_id),
        "dependency_type": dependency_type,
        "strength": strength,
        "updated_at": datetime.now(UTC).isoformat(),
    }

    response = (
        supabase.table("entity_dependencies")
        .upsert(
            data,
            on_conflict="project_id,source_entity_type,source_entity_id,target_entity_type,target_entity_id,dependency_type",
        )
        .execute()
    )

    logger.info(
        f"Registered dependency: {source_type}:{source_id} -> {target_type}:{target_id} ({dependency_type})",
        extra={"project_id": str(project_id)},
    )

    return response.data[0] if response.data else data


def remove_dependency(
    project_id: UUID,
    source_type: str,
    source_id: UUID,
    target_type: str,
    target_id: UUID,
    dependency_type: str | None = None,
) -> int:
    """
    Remove a dependency between two entities.

    Args:
        project_id: Project UUID
        source_type: Type of source entity
        source_id: UUID of source entity
        target_type: Type of target entity
        target_id: UUID of target entity
        dependency_type: Optional - if provided, only remove this specific type

    Returns:
        Number of dependencies removed
    """
    supabase = get_supabase()

    query = (
        supabase.table("entity_dependencies")
        .delete()
        .eq("project_id", str(project_id))
        .eq("source_entity_type", source_type)
        .eq("source_entity_id", str(source_id))
        .eq("target_entity_type", target_type)
        .eq("target_entity_id", str(target_id))
    )

    if dependency_type:
        query = query.eq("dependency_type", dependency_type)

    response = query.execute()

    count = len(response.data) if response.data else 0
    logger.info(
        f"Removed {count} dependencies: {source_type}:{source_id} -> {target_type}:{target_id}",
        extra={"project_id": str(project_id)},
    )

    return count


def remove_all_source_dependencies(
    project_id: UUID,
    source_type: str,
    source_id: UUID,
) -> int:
    """
    Remove all dependencies where entity is the source.

    Useful when rebuilding dependencies for an entity.

    Args:
        project_id: Project UUID
        source_type: Type of source entity
        source_id: UUID of source entity

    Returns:
        Number of dependencies removed
    """
    supabase = get_supabase()

    response = (
        supabase.table("entity_dependencies")
        .delete()
        .eq("project_id", str(project_id))
        .eq("source_entity_type", source_type)
        .eq("source_entity_id", str(source_id))
        .execute()
    )

    count = len(response.data) if response.data else 0
    logger.info(
        f"Removed {count} source dependencies for {source_type}:{source_id}",
        extra={"project_id": str(project_id)},
    )

    return count


def get_dependents(
    project_id: UUID,
    entity_type: str,
    entity_id: UUID,
) -> list[dict]:
    """
    Get all entities that depend on this one.

    These are the entities that would be affected if this entity changes.

    Args:
        project_id: Project UUID
        entity_type: Type of the entity being queried
        entity_id: UUID of the entity

    Returns:
        List of dependency dicts with source entity info
    """
    supabase = get_supabase()

    response = (
        supabase.table("entity_dependencies")
        .select("*")
        .eq("project_id", str(project_id))
        .eq("target_entity_type", entity_type)
        .eq("target_entity_id", str(entity_id))
        .execute()
    )

    return response.data or []


def get_dependencies(
    project_id: UUID,
    entity_type: str,
    entity_id: UUID,
) -> list[dict]:
    """
    Get all entities this one depends on.

    These are the entities that, if changed, would affect this entity.

    Args:
        project_id: Project UUID
        entity_type: Type of the entity being queried
        entity_id: UUID of the entity

    Returns:
        List of dependency dicts with target entity info
    """
    supabase = get_supabase()

    response = (
        supabase.table("entity_dependencies")
        .select("*")
        .eq("project_id", str(project_id))
        .eq("source_entity_type", entity_type)
        .eq("source_entity_id", str(entity_id))
        .execute()
    )

    return response.data or []


def get_dependency_graph(project_id: UUID) -> dict:
    """
    Get the full dependency graph for a project.

    Returns:
        Dict with:
        - dependencies: list of all dependency edges
        - by_source: dict grouping dependencies by source entity
        - by_target: dict grouping dependencies by target entity
    """
    supabase = get_supabase()

    response = (
        supabase.table("entity_dependencies")
        .select("*")
        .eq("project_id", str(project_id))
        .execute()
    )

    dependencies = response.data or []

    # Group by source
    by_source: dict[str, list[dict]] = {}
    for dep in dependencies:
        key = f"{dep['source_entity_type']}:{dep['source_entity_id']}"
        if key not in by_source:
            by_source[key] = []
        by_source[key].append(dep)

    # Group by target
    by_target: dict[str, list[dict]] = {}
    for dep in dependencies:
        key = f"{dep['target_entity_type']}:{dep['target_entity_id']}"
        if key not in by_target:
            by_target[key] = []
        by_target[key].append(dep)

    return {
        "dependencies": dependencies,
        "by_source": by_source,
        "by_target": by_target,
        "total_count": len(dependencies),
    }


def rebuild_dependencies_for_feature(project_id: UUID, feature_id: UUID) -> dict:
    """
    Rebuild dependencies for a feature based on its current data.

    Extracts dependencies from:
    - target_personas -> persona dependencies
    - evidence -> signal/research dependencies

    Args:
        project_id: Project UUID
        feature_id: Feature UUID

    Returns:
        Dict with counts of dependencies created
    """
    from app.db.features import get_feature

    feature = get_feature(feature_id)
    if not feature:
        raise ValueError(f"Feature not found: {feature_id}")

    # Clear existing source dependencies for this feature
    remove_all_source_dependencies(project_id, "feature", feature_id)

    created = 0

    # Register dependencies on target personas
    target_personas = feature.get("target_personas") or []
    for persona in target_personas:
        persona_id = persona.get("persona_id") if isinstance(persona, dict) else persona
        if persona_id:
            try:
                register_dependency(
                    project_id=project_id,
                    source_type="feature",
                    source_id=feature_id,
                    target_type="persona",
                    target_id=UUID(persona_id) if isinstance(persona_id, str) else persona_id,
                    dependency_type="targets",
                )
                created += 1
            except Exception as e:
                logger.warning(f"Failed to register persona dependency: {e}")

    # Register dependencies on evidence (signals, research)
    evidence = feature.get("evidence") or []
    for ev in evidence:
        chunk_id = ev.get("chunk_id") if isinstance(ev, dict) else None
        source_type_str = ev.get("source_type", "signal") if isinstance(ev, dict) else "signal"
        if chunk_id:
            target_type = "research_chunk" if source_type_str == "research" else "signal"
            try:
                register_dependency(
                    project_id=project_id,
                    source_type="feature",
                    source_id=feature_id,
                    target_type=target_type,
                    target_id=UUID(chunk_id) if isinstance(chunk_id, str) else chunk_id,
                    dependency_type="derived_from",
                )
                created += 1
            except Exception as e:
                logger.warning(f"Failed to register evidence dependency: {e}")

    return {"created": created, "feature_id": str(feature_id)}


def rebuild_dependencies_for_vp_step(project_id: UUID, step_id: UUID) -> dict:
    """
    Rebuild dependencies for a VP step based on its current data.

    Extracts dependencies from:
    - actor_persona_id -> persona dependency
    - features_used -> feature dependencies

    Args:
        project_id: Project UUID
        step_id: VP step UUID

    Returns:
        Dict with counts of dependencies created
    """
    from app.db.vp import get_vp_step

    step = get_vp_step(step_id)
    if not step:
        raise ValueError(f"VP step not found: {step_id}")

    # Clear existing source dependencies for this step
    remove_all_source_dependencies(project_id, "vp_step", step_id)

    created = 0

    # Register dependency on actor persona
    actor_persona_id = step.get("actor_persona_id")
    if actor_persona_id:
        try:
            register_dependency(
                project_id=project_id,
                source_type="vp_step",
                source_id=step_id,
                target_type="persona",
                target_id=UUID(actor_persona_id) if isinstance(actor_persona_id, str) else actor_persona_id,
                dependency_type="actor_of",
            )
            created += 1
        except Exception as e:
            logger.warning(f"Failed to register actor persona dependency: {e}")

    # Register dependencies on features used
    features_used = step.get("features_used") or []
    for feature in features_used:
        feature_id = feature.get("feature_id") if isinstance(feature, dict) else feature
        if feature_id:
            try:
                register_dependency(
                    project_id=project_id,
                    source_type="vp_step",
                    source_id=step_id,
                    target_type="feature",
                    target_id=UUID(feature_id) if isinstance(feature_id, str) else feature_id,
                    dependency_type="uses",
                )
                created += 1
            except Exception as e:
                logger.warning(f"Failed to register feature dependency: {e}")

    return {"created": created, "step_id": str(step_id)}


def rebuild_dependencies_for_data_entity(project_id: UUID, entity_id: UUID) -> dict:
    """
    Rebuild dependencies for a data entity based on its workflow step links.

    Extracts dependencies from:
    - data_entity_workflow_steps junction -> vp_step dependencies (uses)

    Args:
        project_id: Project UUID
        entity_id: Data entity UUID

    Returns:
        Dict with counts of dependencies created
    """
    supabase = get_supabase()

    # Verify entity exists
    entity_result = (
        supabase.table("data_entities")
        .select("id")
        .eq("id", str(entity_id))
        .maybe_single()
        .execute()
    )
    if not entity_result or not entity_result.data:
        raise ValueError(f"Data entity not found: {entity_id}")

    # Clear existing source dependencies for this data entity
    remove_all_source_dependencies(project_id, "data_entity", entity_id)

    created = 0

    # Get workflow step links
    links_result = (
        supabase.table("data_entity_workflow_steps")
        .select("vp_step_id")
        .eq("data_entity_id", str(entity_id))
        .execute()
    )

    for link in links_result.data or []:
        vp_step_id = link.get("vp_step_id")
        if vp_step_id:
            try:
                register_dependency(
                    project_id=project_id,
                    source_type="data_entity",
                    source_id=entity_id,
                    target_type="vp_step",
                    target_id=UUID(vp_step_id) if isinstance(vp_step_id, str) else vp_step_id,
                    dependency_type="uses",
                )
                created += 1
            except Exception as e:
                logger.warning(f"Failed to register data entity dependency: {e}")

    return {"created": created, "entity_id": str(entity_id)}


def rebuild_dependencies_for_project(project_id: UUID) -> dict:
    """
    Rebuild the entire dependency graph for a project.

    Scans all features and VP steps and rebuilds their dependencies.

    Args:
        project_id: Project UUID

    Returns:
        Dict with counts of entities processed and dependencies created
    """
    from app.db.features import list_features
    from app.db.vp import list_vp_steps

    stats = {
        "features_processed": 0,
        "vp_steps_processed": 0,
        "data_entities_processed": 0,
        "dependencies_created": 0,
        "errors": [],
    }

    # Rebuild feature dependencies
    features = list_features(project_id)
    for feature in features:
        try:
            result = rebuild_dependencies_for_feature(project_id, UUID(feature["id"]))
            stats["features_processed"] += 1
            stats["dependencies_created"] += result["created"]
        except Exception as e:
            stats["errors"].append(f"Feature {feature['id']}: {str(e)}")

    # Rebuild VP step dependencies
    steps = list_vp_steps(project_id)
    for step in steps:
        try:
            result = rebuild_dependencies_for_vp_step(project_id, UUID(step["id"]))
            stats["vp_steps_processed"] += 1
            stats["dependencies_created"] += result["created"]
        except Exception as e:
            stats["errors"].append(f"VP Step {step['id']}: {str(e)}")

    # Rebuild data entity dependencies
    supabase = get_supabase()
    try:
        de_result = (
            supabase.table("data_entities")
            .select("id")
            .eq("project_id", str(project_id))
            .execute()
        )
        for de in de_result.data or []:
            try:
                result = rebuild_dependencies_for_data_entity(project_id, UUID(de["id"]))
                stats["data_entities_processed"] += 1
                stats["dependencies_created"] += result["created"]
            except Exception as e:
                stats["errors"].append(f"Data Entity {de['id']}: {str(e)}")
    except Exception as e:
        stats["errors"].append(f"Data entities query: {str(e)}")

    logger.info(
        f"Rebuilt dependency graph: {stats['features_processed']} features, "
        f"{stats['vp_steps_processed']} VP steps, "
        f"{stats['data_entities_processed']} data entities, "
        f"{stats['dependencies_created']} dependencies",
        extra={"project_id": str(project_id)},
    )

    return stats


def get_impact_analysis(
    project_id: UUID,
    entity_type: str,
    entity_id: UUID,
    max_depth: int = 3,
) -> dict:
    """
    Calculate the full impact if this entity changes.

    Performs recursive traversal of dependency graph to find all affected entities.

    Args:
        project_id: Project UUID
        entity_type: Type of entity
        entity_id: Entity UUID
        max_depth: Maximum recursion depth (default 3)

    Returns:
        Dict with:
        - entity: the queried entity info
        - direct_impacts: entities directly depending on this one
        - indirect_impacts: entities affected through chains
        - total_affected: total count of affected entities
        - recommendation: auto|review_suggested|high_impact_warning
    """
    visited = set()
    direct_impacts = []
    indirect_impacts = []

    def traverse(etype: str, eid: UUID, depth: int, path: list[str]):
        if depth > max_depth:
            return
        key = f"{etype}:{eid}"
        if key in visited:
            return
        visited.add(key)

        dependents = get_dependents(project_id, etype, eid)
        for dep in dependents:
            dep_key = f"{dep['source_entity_type']}:{dep['source_entity_id']}"
            impact = {
                "type": dep["source_entity_type"],
                "id": dep["source_entity_id"],
                "dependency_type": dep["dependency_type"],
                "strength": dep["strength"],
                "path": path + [key],
            }

            if depth == 0:
                direct_impacts.append(impact)
            else:
                indirect_impacts.append(impact)

            # Recurse
            traverse(
                dep["source_entity_type"],
                UUID(dep["source_entity_id"]),
                depth + 1,
                path + [key],
            )

    # Start traversal
    traverse(entity_type, entity_id, 0, [])

    # Calculate recommendation
    total = len(direct_impacts) + len(indirect_impacts)
    if total == 0:
        recommendation = "auto"
    elif total <= 3:
        recommendation = "auto"
    elif total <= 10:
        recommendation = "review_suggested"
    else:
        recommendation = "high_impact_warning"

    return {
        "entity": {"type": entity_type, "id": str(entity_id)},
        "direct_impacts": direct_impacts,
        "indirect_impacts": indirect_impacts,
        "total_affected": total,
        "recommendation": recommendation,
    }


def get_stale_entities(project_id: UUID) -> dict:
    """
    Get all stale entities for a project grouped by type.

    Returns:
        Dict mapping entity type to list of stale entities
    """
    supabase = get_supabase()

    result = {
        "features": [],
        "personas": [],
        "vp_steps": [],
        "data_entities": [],
        "strategic_context": [],
    }

    # Query each table for stale entities
    features_response = (
        supabase.table("features")
        .select("id, name, is_stale, stale_reason, stale_since")
        .eq("project_id", str(project_id))
        .eq("is_stale", True)
        .execute()
    )
    result["features"] = features_response.data or []

    personas_response = (
        supabase.table("personas")
        .select("id, name, is_stale, stale_reason, stale_since")
        .eq("project_id", str(project_id))
        .eq("is_stale", True)
        .execute()
    )
    result["personas"] = personas_response.data or []

    vp_steps_response = (
        supabase.table("vp_steps")
        .select("id, label, is_stale, stale_reason, stale_since")
        .eq("project_id", str(project_id))
        .eq("is_stale", True)
        .execute()
    )
    result["vp_steps"] = vp_steps_response.data or []

    try:
        data_entities_response = (
            supabase.table("data_entities")
            .select("id, name, is_stale, stale_reason, stale_since")
            .eq("project_id", str(project_id))
            .eq("is_stale", True)
            .execute()
        )
        result["data_entities"] = data_entities_response.data or []
    except Exception:
        result["data_entities"] = []

    strategic_context_response = (
        supabase.table("strategic_context")
        .select("id, is_stale, stale_reason, stale_since")
        .eq("project_id", str(project_id))
        .eq("is_stale", True)
        .execute()
    )
    result["strategic_context"] = strategic_context_response.data or []

    result["total_stale"] = (
        len(result["features"])
        + len(result["personas"])
        + len(result["vp_steps"])
        + len(result["data_entities"])
        + len(result["strategic_context"])
    )

    return result
