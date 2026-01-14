"""Impact analysis - analyze what entities would be affected by changes."""

from dataclasses import dataclass
from uuid import UUID

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ImpactItem:
    """A single impacted entity."""

    entity_type: str
    entity_id: str
    entity_name: str | None
    dependency_type: str
    strength: float
    reason: str
    path: list[str]  # Chain of dependencies leading here


@dataclass
class ImpactAnalysisResult:
    """Result of impact analysis."""

    entity_type: str
    entity_id: str
    entity_name: str | None
    direct_impacts: list[ImpactItem]
    indirect_impacts: list[ImpactItem]
    total_affected: int
    recommendation: str  # auto, review_suggested, high_impact_warning


def get_entity_name(entity_type: str, entity_id: UUID) -> str | None:
    """Get the display name for an entity."""
    try:
        if entity_type == "feature":
            from app.db.features import get_feature

            feature = get_feature(entity_id)
            return feature.get("name") if feature else None

        elif entity_type == "persona":
            from app.db.personas import get_persona

            persona = get_persona(entity_id)
            return persona.get("name") if persona else None

        elif entity_type == "vp_step":
            from app.db.vp import get_vp_step

            step = get_vp_step(entity_id)
            return step.get("label") if step else None

        elif entity_type == "strategic_context":
            return "Strategic Context"

        elif entity_type == "stakeholder":
            from app.db.stakeholders import get_stakeholder

            stakeholder = get_stakeholder(entity_id)
            return stakeholder.get("name") if stakeholder else None

    except Exception:
        pass

    return None


def analyze_change_impact(
    project_id: UUID,
    entity_type: str,
    entity_id: UUID,
    proposed_change: str | None = None,
    max_depth: int = 3,
) -> ImpactAnalysisResult:
    """
    Analyze what entities would be affected if this entity changes.

    Args:
        project_id: Project UUID
        entity_type: Type of entity to analyze
        entity_id: UUID of the entity
        proposed_change: Optional description of the proposed change
        max_depth: Maximum depth to traverse dependencies

    Returns:
        ImpactAnalysisResult with all affected entities and recommendation
    """
    from app.db.entity_dependencies import get_dependents

    entity_name = get_entity_name(entity_type, entity_id)

    direct_impacts: list[ImpactItem] = []
    indirect_impacts: list[ImpactItem] = []
    visited = set()

    def traverse(etype: str, eid: UUID, depth: int, path: list[str]):
        """Recursively traverse dependency graph."""
        if depth > max_depth:
            return

        key = f"{etype}:{eid}"
        if key in visited:
            return
        visited.add(key)

        dependents = get_dependents(project_id, etype, eid)

        for dep in dependents:
            dep_type = dep["source_entity_type"]
            dep_id = dep["source_entity_id"]
            dep_name = get_entity_name(dep_type, UUID(dep_id))

            # Construct reason based on dependency type
            dep_type_map = {
                "uses": f"uses this {etype}",
                "targets": f"targets this {etype}",
                "derived_from": f"derived from this {etype}",
                "informed_by": f"informed by this {etype}",
                "actor_of": f"has this {etype} as actor",
            }
            reason = dep_type_map.get(dep["dependency_type"], f"depends on this {etype}")

            impact = ImpactItem(
                entity_type=dep_type,
                entity_id=dep_id,
                entity_name=dep_name,
                dependency_type=dep["dependency_type"],
                strength=dep["strength"],
                reason=reason,
                path=path + [key],
            )

            if depth == 0:
                direct_impacts.append(impact)
            else:
                indirect_impacts.append(impact)

            # Recurse to find indirect impacts
            traverse(dep_type, UUID(dep_id), depth + 1, path + [key])

    # Start traversal from the target entity
    traverse(entity_type, entity_id, 0, [])

    # Determine recommendation
    total = len(direct_impacts) + len(indirect_impacts)

    if total == 0:
        recommendation = "auto"
    elif total <= 3:
        recommendation = "auto"
    elif total <= 10:
        recommendation = "review_suggested"
    else:
        recommendation = "high_impact_warning"

    # Upgrade to warning if high-strength dependencies are affected
    high_strength_count = sum(
        1 for i in direct_impacts + indirect_impacts if i.strength >= 0.8
    )
    if high_strength_count >= 3 and recommendation != "high_impact_warning":
        recommendation = "review_suggested"

    return ImpactAnalysisResult(
        entity_type=entity_type,
        entity_id=str(entity_id),
        entity_name=entity_name,
        direct_impacts=direct_impacts,
        indirect_impacts=indirect_impacts,
        total_affected=total,
        recommendation=recommendation,
    )


def format_impact_analysis(result: ImpactAnalysisResult) -> str:
    """
    Format impact analysis result as human-readable text.

    Args:
        result: ImpactAnalysisResult to format

    Returns:
        Formatted string for display
    """
    lines = []

    # Header
    entity_desc = f"{result.entity_type}"
    if result.entity_name:
        entity_desc += f" '{result.entity_name}'"
    lines.append(f"Impact Analysis for {entity_desc}")
    lines.append("=" * 50)

    # Summary
    lines.append(f"Total entities affected: {result.total_affected}")
    lines.append(f"Recommendation: {result.recommendation}")
    lines.append("")

    # Direct impacts
    if result.direct_impacts:
        lines.append("Direct Impacts:")
        lines.append("-" * 30)
        for impact in result.direct_impacts:
            name = impact.entity_name or impact.entity_id[:8]
            lines.append(f"  - {impact.entity_type} '{name}': {impact.reason}")
        lines.append("")

    # Indirect impacts
    if result.indirect_impacts:
        lines.append("Indirect Impacts:")
        lines.append("-" * 30)
        for impact in result.indirect_impacts:
            name = impact.entity_name or impact.entity_id[:8]
            depth = len(impact.path)
            lines.append(f"  - {impact.entity_type} '{name}': {impact.reason} (depth: {depth})")
        lines.append("")

    # Recommendations
    lines.append("Recommendation:")
    if result.recommendation == "auto":
        lines.append("  This change has minimal impact and can be applied automatically.")
    elif result.recommendation == "review_suggested":
        lines.append("  This change affects multiple entities. Review the impacts before proceeding.")
    else:
        lines.append("  WARNING: This is a high-impact change affecting many entities.")
        lines.append("  Consider reviewing each affected entity before proceeding.")

    return "\n".join(lines)


def preview_cascade(
    project_id: UUID,
    entity_type: str,
    entity_id: UUID,
) -> list[dict]:
    """
    Preview what would happen if this entity changes.

    Returns a simplified list of affected entities without actually making changes.

    Args:
        project_id: Project UUID
        entity_type: Type of entity
        entity_id: UUID of entity

    Returns:
        List of dicts with type, id, name, and reason for each affected entity
    """
    result = analyze_change_impact(project_id, entity_type, entity_id)

    preview = []

    for impact in result.direct_impacts:
        preview.append({
            "type": impact.entity_type,
            "id": impact.entity_id,
            "name": impact.entity_name,
            "reason": impact.reason,
            "depth": 1,
            "action": "mark_stale",
        })

    for impact in result.indirect_impacts:
        preview.append({
            "type": impact.entity_type,
            "id": impact.entity_id,
            "name": impact.entity_name,
            "reason": impact.reason,
            "depth": len(impact.path),
            "action": "mark_stale",
        })

    return preview


def get_refresh_order(project_id: UUID) -> list[dict]:
    """
    Get the recommended order to refresh stale entities.

    Returns entities in dependency order - refresh dependencies first.

    Args:
        project_id: Project UUID

    Returns:
        List of stale entities in recommended refresh order
    """
    from app.db.entity_dependencies import get_stale_entities

    stale = get_stale_entities(project_id)

    # Order: personas first, then features, then VP steps, then strategic context
    # This ensures dependencies are refreshed before dependents
    order_priority = {
        "persona": 1,
        "feature": 2,
        "vp_step": 3,
        "strategic_context": 4,
    }

    all_stale = []

    for persona in stale.get("personas", []):
        all_stale.append({
            "type": "persona",
            "id": persona["id"],
            "name": persona.get("name"),
            "stale_reason": persona.get("stale_reason"),
            "stale_since": persona.get("stale_since"),
            "priority": order_priority["persona"],
        })

    for feature in stale.get("features", []):
        all_stale.append({
            "type": "feature",
            "id": feature["id"],
            "name": feature.get("name"),
            "stale_reason": feature.get("stale_reason"),
            "stale_since": feature.get("stale_since"),
            "priority": order_priority["feature"],
        })

    for step in stale.get("vp_steps", []):
        all_stale.append({
            "type": "vp_step",
            "id": step["id"],
            "name": step.get("label"),
            "stale_reason": step.get("stale_reason"),
            "stale_since": step.get("stale_since"),
            "priority": order_priority["vp_step"],
        })

    for ctx in stale.get("strategic_context", []):
        all_stale.append({
            "type": "strategic_context",
            "id": ctx["id"],
            "name": "Strategic Context",
            "stale_reason": ctx.get("stale_reason"),
            "stale_since": ctx.get("stale_since"),
            "priority": order_priority["strategic_context"],
        })

    # Sort by priority (lower number = refresh first)
    all_stale.sort(key=lambda x: (x["priority"], x.get("stale_since") or ""))

    return all_stale


def refresh_stale_entity(
    project_id: UUID,
    entity_type: str,
    entity_id: UUID,
) -> dict:
    """
    Refresh a stale entity by re-enriching it.

    Args:
        project_id: Project UUID
        entity_type: Type of entity to refresh
        entity_id: UUID of entity

    Returns:
        Result of the refresh operation
    """
    from app.chains.entity_cascade import clear_staleness

    result = {"entity_type": entity_type, "entity_id": str(entity_id), "status": "unknown"}

    try:
        if entity_type == "feature":
            # For now, just clear staleness - full re-enrichment requires enrich_and_save_features
            # TODO: Add single-feature enrichment when needed
            clear_staleness(entity_type, entity_id)
            result["status"] = "staleness_cleared"
            result["message"] = "Staleness cleared. Run 'enrich_features' to fully re-enrich."

        elif entity_type == "persona":
            # For now, just clear staleness - full re-enrichment requires enrich_and_save_personas
            # TODO: Add single-persona enrichment when needed
            clear_staleness(entity_type, entity_id)
            result["status"] = "staleness_cleared"
            result["message"] = "Staleness cleared. Run 'enrich_personas' to fully re-enrich."

        elif entity_type == "vp_step":
            # For now, just clear staleness - full regeneration requires generate_value_path
            # TODO: Add single-step regeneration when needed
            clear_staleness(entity_type, entity_id)
            result["status"] = "staleness_cleared"
            result["message"] = "Staleness cleared. Run 'generate_value_path' to fully regenerate."

        elif entity_type == "strategic_context":
            # Regenerate strategic context - this function exists
            from app.chains.generate_strategic_context import generate_strategic_context

            generated = generate_strategic_context(project_id)
            if generated:
                clear_staleness(entity_type, entity_id)
                result["status"] = "refreshed"
                result["regenerated"] = True
            else:
                result["status"] = "no_changes"

        else:
            result["status"] = "unsupported_type"
            result["error"] = f"Cannot refresh entity type: {entity_type}"

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        logger.error(f"Failed to refresh {entity_type}:{entity_id}: {e}")

    return result


def batch_refresh_stale(
    project_id: UUID,
    max_entities: int = 10,
) -> dict:
    """
    Refresh multiple stale entities in dependency order.

    Args:
        project_id: Project UUID
        max_entities: Maximum number of entities to refresh

    Returns:
        Dict with results of each refresh
    """
    refresh_order = get_refresh_order(project_id)

    results = {
        "refreshed": 0,
        "errors": 0,
        "skipped": 0,
        "details": [],
    }

    for entity in refresh_order[:max_entities]:
        result = refresh_stale_entity(
            project_id,
            entity["type"],
            UUID(entity["id"]),
        )

        results["details"].append(result)

        if result["status"] == "refreshed":
            results["refreshed"] += 1
        elif result["status"] == "error":
            results["errors"] += 1
        else:
            results["skipped"] += 1

    return results
