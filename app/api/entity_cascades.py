"""API endpoints for entity cascade processing and impact analysis."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class ImpactAnalysisRequest(BaseModel):
    """Request for impact analysis."""

    entity_type: str = Field(..., description="Type of entity (persona, feature, vp_step)")
    entity_id: str = Field(..., description="UUID of the entity")
    proposed_change: str | None = Field(None, description="Description of proposed change")


class ImpactItem(BaseModel):
    """A single impact item."""

    entity_type: str
    entity_id: str
    entity_name: str | None
    reason: str
    depth: int = 1


class ImpactAnalysisResponse(BaseModel):
    """Response for impact analysis."""

    entity_type: str
    entity_id: str
    entity_name: str | None
    total_affected: int
    recommendation: str
    direct_impacts: list[ImpactItem]
    indirect_impacts: list[ImpactItem]


class StaleEntitiesResponse(BaseModel):
    """Response for stale entities query."""

    personas: list[dict]
    features: list[dict]
    vp_steps: list[dict]
    data_entities: list[dict] = []
    strategic_context: list[dict]
    total_stale: int


class RefreshEntityRequest(BaseModel):
    """Request to refresh a stale entity."""

    entity_type: str = Field(..., description="Type of entity to refresh")
    entity_id: str = Field(..., description="UUID of the entity")


class RefreshEntityResponse(BaseModel):
    """Response for entity refresh."""

    entity_type: str
    entity_id: str
    status: str
    message: str


class ProcessCascadesResponse(BaseModel):
    """Response for cascade processing."""

    changes_processed: int
    entities_marked_stale: int
    errors: list[str]


class RebuildDependenciesResponse(BaseModel):
    """Response for dependency graph rebuild."""

    features_processed: int
    vp_steps_processed: int
    dependencies_created: int
    errors: list[str]


class DependencyGraphResponse(BaseModel):
    """Response for dependency graph query."""

    total_count: int
    dependencies: list[dict]


class FeatureImpactResponse(BaseModel):
    """Response for feature cascade impact analysis."""

    feature: dict
    affected_vp_steps: list[dict]
    affected_personas: list[dict]
    total_vp_steps: int
    total_personas: int
    affected_vp_count: int
    affected_persona_count: int
    impact_percentage: float
    suggest_bulk_rebuild: bool


class PersonaImpactResponse(BaseModel):
    """Response for persona cascade impact analysis."""

    persona: dict
    affected_features: list[dict]
    affected_vp_steps: list[dict]
    total_features: int
    total_vp_steps: int
    total_personas: int
    affected_feature_count: int
    affected_vp_count: int
    impact_percentage: float
    suggest_bulk_rebuild: bool


class DeleteFeatureResponse(BaseModel):
    """Response for feature deletion."""

    deleted: bool
    feature_id: str
    feature_name: str
    cleaned_personas: list[dict]
    cleaned_persona_count: int


class DeletePersonaResponse(BaseModel):
    """Response for persona deletion."""

    deleted: bool
    persona_id: str
    persona_name: str
    cleaned_features: list[dict]
    cleaned_feature_count: int


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/projects/{project_id}/impact-analysis", response_model=ImpactAnalysisResponse)
async def analyze_impact(
    project_id: UUID = Path(..., description="Project UUID"),
    request: ImpactAnalysisRequest = ...,
) -> ImpactAnalysisResponse:
    """
    Analyze the impact of changing an entity.

    Shows which other entities would be affected (marked stale) if this
    entity is modified.

    Args:
        project_id: Project UUID
        request: Entity type and ID to analyze

    Returns:
        Impact analysis with direct and indirect impacts
    """
    try:
        from app.chains.impact_analysis import analyze_change_impact

        result = analyze_change_impact(
            project_id=project_id,
            entity_type=request.entity_type,
            entity_id=UUID(request.entity_id),
            proposed_change=request.proposed_change,
        )

        return ImpactAnalysisResponse(
            entity_type=result.entity_type,
            entity_id=result.entity_id,
            entity_name=result.entity_name,
            total_affected=result.total_affected,
            recommendation=result.recommendation,
            direct_impacts=[
                ImpactItem(
                    entity_type=i.entity_type,
                    entity_id=i.entity_id,
                    entity_name=i.entity_name,
                    reason=i.reason,
                    depth=1,
                )
                for i in result.direct_impacts
            ],
            indirect_impacts=[
                ImpactItem(
                    entity_type=i.entity_type,
                    entity_id=i.entity_id,
                    entity_name=i.entity_name,
                    reason=i.reason,
                    depth=len(i.path),
                )
                for i in result.indirect_impacts
            ],
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error analyzing impact: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/stale-entities", response_model=StaleEntitiesResponse)
async def get_stale_entities(
    project_id: UUID = Path(..., description="Project UUID"),
    entity_type: str | None = Query(None, description="Filter by entity type"),
) -> StaleEntitiesResponse:
    """
    Get all stale entities for a project.

    Stale entities are those that may need regeneration because their
    dependencies have changed.

    Args:
        project_id: Project UUID
        entity_type: Optional filter (persona, feature, vp_step, strategic_context)

    Returns:
        Stale entities grouped by type
    """
    try:
        from app.db.entity_dependencies import get_stale_entities

        result = get_stale_entities(project_id)

        # Filter if requested
        if entity_type:
            type_map = {
                "persona": "personas",
                "feature": "features",
                "vp_step": "vp_steps",
                "strategic_context": "strategic_context",
            }
            key = type_map.get(entity_type)
            if key:
                filtered_result = {
                    "personas": [],
                    "features": [],
                    "vp_steps": [],
                    "strategic_context": [],
                }
                filtered_result[key] = result.get(key, [])
                filtered_result["total_stale"] = len(filtered_result[key])
                result = filtered_result

        return StaleEntitiesResponse(
            personas=result.get("personas", []),
            features=result.get("features", []),
            vp_steps=result.get("vp_steps", []),
            strategic_context=result.get("strategic_context", []),
            total_stale=result.get("total_stale", 0),
        )

    except Exception as e:
        logger.error(f"Error getting stale entities: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/refresh-entity", response_model=RefreshEntityResponse)
async def refresh_stale_entity(
    project_id: UUID = Path(..., description="Project UUID"),
    request: RefreshEntityRequest = ...,
) -> RefreshEntityResponse:
    """
    Refresh (regenerate) a stale entity.

    This will re-enrich or regenerate the entity based on its current
    dependencies, then clear its staleness flag.

    Args:
        project_id: Project UUID
        request: Entity type and ID to refresh

    Returns:
        Refresh result with status
    """
    try:
        from app.chains.impact_analysis import refresh_stale_entity

        result = refresh_stale_entity(
            project_id=project_id,
            entity_type=request.entity_type,
            entity_id=UUID(request.entity_id),
        )

        if result["status"] == "refreshed":
            message = f"Successfully refreshed {request.entity_type}"
        elif result["status"] == "no_changes":
            message = f"No changes needed for {request.entity_type}"
        elif result["status"] == "error":
            message = f"Failed to refresh: {result.get('error', 'Unknown error')}"
        else:
            message = f"Refresh status: {result['status']}"

        return RefreshEntityResponse(
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            status=result["status"],
            message=message,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error refreshing entity: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/process-cascades", response_model=ProcessCascadesResponse)
async def process_cascades(
    project_id: UUID = Path(..., description="Project UUID"),
    auto_only: bool = Query(True, description="Only process auto cascades"),
) -> ProcessCascadesResponse:
    """
    Process pending entity change cascades.

    This processes the change queue and propagates staleness to dependent
    entities. Usually runs automatically but can be triggered manually.

    Args:
        project_id: Project UUID
        auto_only: If True, only process auto cascade types

    Returns:
        Processing statistics
    """
    try:
        from app.chains.entity_cascade import process_entity_changes

        stats = process_entity_changes(project_id, auto_only=auto_only)

        return ProcessCascadesResponse(
            changes_processed=stats["changes_processed"],
            entities_marked_stale=stats["entities_marked_stale"],
            errors=stats.get("errors", []),
        )

    except Exception as e:
        logger.error(f"Error processing cascades: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/rebuild-dependencies", response_model=RebuildDependenciesResponse)
async def rebuild_dependencies(
    project_id: UUID = Path(..., description="Project UUID"),
) -> RebuildDependenciesResponse:
    """
    Rebuild the entity dependency graph for a project.

    Scans all features and VP steps and rebuilds their dependency
    relationships. Use when dependencies seem out of sync or after
    bulk data imports.

    Args:
        project_id: Project UUID

    Returns:
        Rebuild statistics
    """
    try:
        from app.db.entity_dependencies import rebuild_dependencies_for_project

        stats = rebuild_dependencies_for_project(project_id)

        return RebuildDependenciesResponse(
            features_processed=stats["features_processed"],
            vp_steps_processed=stats["vp_steps_processed"],
            dependencies_created=stats["dependencies_created"],
            errors=stats.get("errors", []),
        )

    except Exception as e:
        logger.error(f"Error rebuilding dependencies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/dependency-graph", response_model=DependencyGraphResponse)
async def get_dependency_graph(
    project_id: UUID = Path(..., description="Project UUID"),
) -> DependencyGraphResponse:
    """
    Get the full dependency graph for a project.

    Returns all registered entity dependencies, showing how entities
    are connected.

    Args:
        project_id: Project UUID

    Returns:
        Dependency graph data
    """
    try:
        from app.db.entity_dependencies import get_dependency_graph

        result = get_dependency_graph(project_id)

        return DependencyGraphResponse(
            total_count=result["total_count"],
            dependencies=result["dependencies"],
        )

    except Exception as e:
        logger.error(f"Error getting dependency graph: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Feature/Persona Delete Cascade Endpoints
# =============================================================================


@router.get("/features/{feature_id}/impact", response_model=FeatureImpactResponse)
async def get_feature_impact(
    feature_id: UUID = Path(..., description="Feature UUID"),
) -> FeatureImpactResponse:
    """
    Get cascade impact analysis for deleting a feature.

    Shows what VP steps and personas would be affected if this feature
    is deleted. Includes recommendation for bulk rebuild if impact > 50%.

    Args:
        feature_id: Feature UUID

    Returns:
        Impact analysis with affected entities and recommendation
    """
    try:
        from app.db.cascade import get_feature_cascade_impact

        result = get_feature_cascade_impact(feature_id)

        return FeatureImpactResponse(
            feature=result["feature"],
            affected_vp_steps=result["affected_vp_steps"],
            affected_personas=result["affected_personas"],
            total_vp_steps=result["total_vp_steps"],
            total_personas=result["total_personas"],
            affected_vp_count=result["affected_vp_count"],
            affected_persona_count=result["affected_persona_count"],
            impact_percentage=result["impact_percentage"],
            suggest_bulk_rebuild=result["suggest_bulk_rebuild"],
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting feature impact: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/features/{feature_id}", response_model=DeleteFeatureResponse)
async def delete_feature(
    feature_id: UUID = Path(..., description="Feature UUID"),
    cleanup_references: bool = Query(True, description="Clean up references in personas"),
) -> DeleteFeatureResponse:
    """
    Delete a feature with cascade cleanup.

    Hard delete - the feature is permanently removed.
    By default, also cleans up references to this feature in personas.

    Args:
        feature_id: Feature UUID
        cleanup_references: Whether to remove references from personas (default True)

    Returns:
        Deletion result with cleaned up entities
    """
    try:
        from app.db.cascade import delete_feature_with_cascade

        result = delete_feature_with_cascade(
            feature_id=feature_id,
            cleanup_references=cleanup_references,
        )

        return DeleteFeatureResponse(
            deleted=result["deleted"],
            feature_id=result["feature_id"],
            feature_name=result["feature_name"],
            cleaned_personas=result["cleaned_personas"],
            cleaned_persona_count=result["cleaned_persona_count"],
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting feature: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/personas/{persona_id}/impact", response_model=PersonaImpactResponse)
async def get_persona_impact(
    persona_id: UUID = Path(..., description="Persona UUID"),
) -> PersonaImpactResponse:
    """
    Get cascade impact analysis for deleting a persona.

    Shows what features and VP steps would be affected if this persona
    is deleted. Includes recommendation for bulk rebuild if impact > 50%.

    Args:
        persona_id: Persona UUID

    Returns:
        Impact analysis with affected entities and recommendation
    """
    try:
        from app.db.cascade import get_persona_cascade_impact

        result = get_persona_cascade_impact(persona_id)

        return PersonaImpactResponse(
            persona=result["persona"],
            affected_features=result["affected_features"],
            affected_vp_steps=result["affected_vp_steps"],
            total_features=result["total_features"],
            total_vp_steps=result["total_vp_steps"],
            total_personas=result["total_personas"],
            affected_feature_count=result["affected_feature_count"],
            affected_vp_count=result["affected_vp_count"],
            impact_percentage=result["impact_percentage"],
            suggest_bulk_rebuild=result["suggest_bulk_rebuild"],
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting persona impact: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/personas/{persona_id}", response_model=DeletePersonaResponse)
async def delete_persona(
    persona_id: UUID = Path(..., description="Persona UUID"),
    cleanup_references: bool = Query(True, description="Clean up references in features"),
) -> DeletePersonaResponse:
    """
    Delete a persona with cascade cleanup.

    Hard delete - the persona is permanently removed.
    By default, also cleans up references to this persona in features.

    Args:
        persona_id: Persona UUID
        cleanup_references: Whether to remove references from features (default True)

    Returns:
        Deletion result with cleaned up entities
    """
    try:
        from app.db.cascade import delete_persona_with_cascade

        result = delete_persona_with_cascade(
            persona_id=persona_id,
            cleanup_references=cleanup_references,
        )

        return DeletePersonaResponse(
            deleted=result["deleted"],
            persona_id=result["persona_id"],
            persona_name=result["persona_name"],
            cleaned_features=result["cleaned_features"],
            cleaned_feature_count=result["cleaned_feature_count"],
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting persona: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
