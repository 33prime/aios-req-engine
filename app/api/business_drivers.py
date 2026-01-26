"""API endpoints for business drivers management (KPIs, Pain Points, Goals)."""

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.db import business_drivers as drivers_db

logger = get_logger(__name__)

router = APIRouter(prefix="/projects/{project_id}/business-drivers")


# ============================================================================
# Pydantic Models
# ============================================================================


class BusinessDriverCreate(BaseModel):
    """Request body for creating a business driver."""

    driver_type: Literal["kpi", "pain", "goal"] = Field(..., description="Driver type")
    description: str = Field(..., min_length=1, description="Driver description")
    category: str | None = Field(None, description="Category/domain (e.g., 'Revenue', 'Efficiency')")
    priority: str = Field("medium", description="Priority: critical, high, medium, low")
    notes: str | None = Field(None, description="Additional notes")

    # KPI fields
    baseline_value: str | None = Field(None, description="KPI baseline (e.g., '100 tickets/day')")
    target_value: str | None = Field(None, description="KPI target (e.g., '60 tickets/day')")
    measurement_method: str | None = Field(None, description="How to measure")
    tracking_frequency: str | None = Field(None, description="How often to track")
    data_source: str | None = Field(None, description="Where data comes from")
    responsible_team: str | None = Field(None, description="Who owns this KPI")

    # Pain fields
    severity: Literal["critical", "high", "medium", "low"] | None = Field(None, description="Pain severity")
    frequency: Literal["constant", "daily", "weekly", "monthly", "rare"] | None = Field(None, description="Pain frequency")
    affected_users: str | None = Field(None, description="Who feels this pain")
    business_impact: str | None = Field(None, description="Impact if not solved")
    current_workaround: str | None = Field(None, description="How they deal with it now")

    # Goal fields
    goal_timeframe: str | None = Field(None, description="When to achieve goal")
    success_criteria: str | None = Field(None, description="What success looks like")
    dependencies: str | None = Field(None, description="What needs to happen first")
    owner: str | None = Field(None, description="Who owns this goal")


class BusinessDriverUpdate(BaseModel):
    """Request body for updating a business driver."""

    description: str | None = None
    category: str | None = None
    priority: str | None = None
    notes: str | None = None

    # KPI fields
    baseline_value: str | None = None
    target_value: str | None = None
    measurement_method: str | None = None
    tracking_frequency: str | None = None
    data_source: str | None = None
    responsible_team: str | None = None

    # Pain fields
    severity: Literal["critical", "high", "medium", "low"] | None = None
    frequency: Literal["constant", "daily", "weekly", "monthly", "rare"] | None = None
    affected_users: str | None = None
    business_impact: str | None = None
    current_workaround: str | None = None

    # Goal fields
    goal_timeframe: str | None = None
    success_criteria: str | None = None
    dependencies: str | None = None
    owner: str | None = None

    # Confirmation
    confirmation_status: str | None = None


class BusinessDriverOut(BaseModel):
    """Response model for a business driver."""

    id: UUID
    project_id: UUID
    driver_type: str
    description: str
    category: str | None = None
    priority: str | int | None = None  # Support both string and int for backward compatibility
    notes: str | None = None
    source_type: str | None = None
    extracted_from_signal_id: UUID | None = None

    # KPI fields
    baseline_value: str | None = None
    target_value: str | None = None
    measurement_method: str | None = None
    tracking_frequency: str | None = None
    data_source: str | None = None
    responsible_team: str | None = None

    # Pain fields
    severity: str | None = None
    frequency: str | None = None
    affected_users: str | None = None
    business_impact: str | None = None
    current_workaround: str | None = None

    # Goal fields
    goal_timeframe: str | None = None
    success_criteria: str | None = None
    dependencies: str | None = None
    owner: str | None = None

    # Tracking fields
    evidence: list[dict[str, Any]] | None = None
    source_signal_ids: list[UUID] | None = None
    version: int | None = None
    created_by: str | None = None
    enrichment_status: str | None = None
    enrichment_attempted_at: str | None = None
    enrichment_error: str | None = None
    confirmation_status: str | None = None

    # Standard fields
    source_type: str | None
    confirmation_status: str | None
    extracted_from_signal_id: UUID | None
    created_at: str
    updated_at: str | None

    class Config:
        from_attributes = True


class BusinessDriverListResponse(BaseModel):
    """Response for listing business drivers."""

    business_drivers: list[BusinessDriverOut]
    total: int
    by_type: dict[str, int]


# ============================================================================
# Endpoints
# ============================================================================


@router.get("", response_model=BusinessDriverListResponse)
async def list_business_drivers(
    project_id: UUID = Path(..., description="Project UUID"),
    driver_type: Literal["kpi", "pain", "goal"] | None = Query(None, description="Filter by type"),
    priority: str | None = Query(None, description="Filter by priority"),
    confirmation_status: str | None = Query(None, description="Filter by confirmation status"),
) -> BusinessDriverListResponse:
    """
    List all business drivers for a project.

    Args:
        project_id: Project UUID
        driver_type: Optional filter by type (kpi, pain, goal)
        priority: Optional filter by priority
        confirmation_status: Optional filter by confirmation status

    Returns:
        List of business drivers with counts by type
    """
    try:
        all_drivers = drivers_db.list_business_drivers(project_id, driver_type=driver_type)

        # Apply additional filters
        if priority:
            all_drivers = [d for d in all_drivers if d.get("priority") == priority]
        if confirmation_status:
            all_drivers = [d for d in all_drivers if d.get("confirmation_status") == confirmation_status]

        # Count by type
        by_type = {"kpi": 0, "pain": 0, "goal": 0}
        for driver in all_drivers:
            driver_type_value = driver.get("driver_type")
            if driver_type_value in by_type:
                by_type[driver_type_value] += 1

        return BusinessDriverListResponse(
            business_drivers=[BusinessDriverOut(**d) for d in all_drivers],
            total=len(all_drivers),
            by_type=by_type,
        )

    except Exception as e:
        logger.error(f"Error listing business drivers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("", response_model=BusinessDriverOut)
async def create_business_driver(
    project_id: UUID = Path(..., description="Project UUID"),
    body: BusinessDriverCreate = ...,
) -> BusinessDriverOut:
    """
    Create a new business driver.

    Args:
        project_id: Project UUID
        body: Business driver data

    Returns:
        Created business driver
    """
    try:
        # Build kwargs from body
        kwargs = {
            "driver_type": body.driver_type,
            "description": body.description,
            "category": body.category,
            "priority": body.priority,
            "notes": body.notes,
            "confirmation_status": "confirmed_consultant",  # Manual creation = confirmed
            "created_by": "consultant",
        }

        # Add type-specific fields if provided
        if body.driver_type == "kpi":
            if body.baseline_value:
                kwargs["baseline_value"] = body.baseline_value
            if body.target_value:
                kwargs["target_value"] = body.target_value
            if body.measurement_method:
                kwargs["measurement_method"] = body.measurement_method
            if body.tracking_frequency:
                kwargs["tracking_frequency"] = body.tracking_frequency
            if body.data_source:
                kwargs["data_source"] = body.data_source
            if body.responsible_team:
                kwargs["responsible_team"] = body.responsible_team
        elif body.driver_type == "pain":
            if body.severity:
                kwargs["severity"] = body.severity
            if body.frequency:
                kwargs["frequency"] = body.frequency
            if body.affected_users:
                kwargs["affected_users"] = body.affected_users
            if body.business_impact:
                kwargs["business_impact"] = body.business_impact
            if body.current_workaround:
                kwargs["current_workaround"] = body.current_workaround
        elif body.driver_type == "goal":
            if body.goal_timeframe:
                kwargs["goal_timeframe"] = body.goal_timeframe
            if body.success_criteria:
                kwargs["success_criteria"] = body.success_criteria
            if body.dependencies:
                kwargs["dependencies"] = body.dependencies
            if body.owner:
                kwargs["owner"] = body.owner

        driver = drivers_db.create_business_driver(project_id=project_id, **kwargs)
        return BusinessDriverOut(**driver)

    except Exception as e:
        logger.error(f"Error creating business driver: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{driver_id}", response_model=BusinessDriverOut)
async def get_business_driver(
    project_id: UUID = Path(..., description="Project UUID"),
    driver_id: UUID = Path(..., description="Business driver UUID"),
) -> BusinessDriverOut:
    """
    Get a single business driver by ID.

    Args:
        project_id: Project UUID
        driver_id: Business driver UUID

    Returns:
        Business driver details
    """
    try:
        driver = drivers_db.get_business_driver(driver_id)

        if not driver:
            raise HTTPException(status_code=404, detail="Business driver not found")

        if str(driver.get("project_id")) != str(project_id):
            raise HTTPException(status_code=404, detail="Business driver not found in this project")

        return BusinessDriverOut(**driver)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting business driver: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/{driver_id}", response_model=BusinessDriverOut)
async def update_business_driver(
    project_id: UUID = Path(..., description="Project UUID"),
    driver_id: UUID = Path(..., description="Business driver UUID"),
    body: BusinessDriverUpdate = ...,
) -> BusinessDriverOut:
    """
    Update a business driver.

    Args:
        project_id: Project UUID
        driver_id: Business driver UUID
        body: Fields to update

    Returns:
        Updated business driver
    """
    try:
        # Verify driver exists and belongs to project
        existing = drivers_db.get_business_driver(driver_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Business driver not found")
        if str(existing.get("project_id")) != str(project_id):
            raise HTTPException(status_code=404, detail="Business driver not found in this project")

        # Build update dict from non-None fields
        updates = {k: v for k, v in body.model_dump().items() if v is not None}

        if not updates:
            return BusinessDriverOut(**existing)

        # Increment version
        updates["version"] = existing.get("version", 1) + 1

        driver = drivers_db.update_business_driver(driver_id, project_id, **updates)
        return BusinessDriverOut(**driver)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating business driver: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{driver_id}")
async def delete_business_driver(
    project_id: UUID = Path(..., description="Project UUID"),
    driver_id: UUID = Path(..., description="Business driver UUID"),
) -> dict[str, Any]:
    """
    Delete a business driver.

    Args:
        project_id: Project UUID
        driver_id: Business driver UUID

    Returns:
        Success message
    """
    try:
        # Verify driver exists and belongs to project
        existing = drivers_db.get_business_driver(driver_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Business driver not found")
        if str(existing.get("project_id")) != str(project_id):
            raise HTTPException(status_code=404, detail="Business driver not found in this project")

        drivers_db.delete_business_driver(driver_id, project_id)
        return {"success": True, "message": "Business driver deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting business driver: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{driver_id}/enrich", response_model=BusinessDriverOut)
async def enrich_business_driver(
    project_id: UUID = Path(..., description="Project UUID"),
    driver_id: UUID = Path(..., description="Business driver UUID"),
    depth: Literal["quick", "standard", "deep"] = Query("standard", description="Enrichment depth"),
) -> BusinessDriverOut:
    """
    Trigger enrichment for a business driver.

    Calls the appropriate enrichment chain based on driver_type:
    - KPI: Extract baseline, target, measurement method, tracking, data source, owner
    - Pain: Extract severity, frequency, affected users, business impact, workaround
    - Goal: Extract timeframe, success criteria, dependencies, owner

    Args:
        project_id: Project UUID
        driver_id: Business driver UUID
        depth: Enrichment depth (quick, standard, deep)

    Returns:
        Updated business driver with enrichment fields
    """
    try:
        # Verify driver exists and belongs to project
        existing = drivers_db.get_business_driver(driver_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Business driver not found")
        if str(existing.get("project_id")) != str(project_id):
            raise HTTPException(status_code=404, detail="Business driver not found in this project")

        driver_type = existing.get("driver_type")
        if not driver_type:
            raise HTTPException(status_code=400, detail="Driver type not set")

        logger.info(
            f"Enriching {driver_type} driver {driver_id}",
            extra={"project_id": str(project_id), "driver_id": str(driver_id), "depth": depth},
        )

        # Call appropriate enrichment chain
        enrichment_result = None
        updated_fields = {}

        if driver_type == "kpi":
            from app.chains.enrich_kpi import enrich_kpi
            enrichment_result = await enrich_kpi(driver_id, project_id, depth)

            if enrichment_result["success"] and enrichment_result["enrichment"]:
                enrichment = enrichment_result["enrichment"]
                if enrichment.baseline_value:
                    updated_fields["baseline_value"] = enrichment.baseline_value
                if enrichment.target_value:
                    updated_fields["target_value"] = enrichment.target_value
                if enrichment.measurement_method:
                    updated_fields["measurement_method"] = enrichment.measurement_method
                if enrichment.tracking_frequency:
                    updated_fields["tracking_frequency"] = enrichment.tracking_frequency
                if enrichment.data_source:
                    updated_fields["data_source"] = enrichment.data_source
                if enrichment.responsible_team:
                    updated_fields["responsible_team"] = enrichment.responsible_team

        elif driver_type == "pain":
            from app.chains.enrich_pain_point import enrich_pain_point
            enrichment_result = await enrich_pain_point(driver_id, project_id, depth)

            if enrichment_result["success"] and enrichment_result["enrichment"]:
                enrichment = enrichment_result["enrichment"]
                if enrichment.severity:
                    updated_fields["severity"] = enrichment.severity
                if enrichment.frequency:
                    updated_fields["frequency"] = enrichment.frequency
                if enrichment.affected_users:
                    updated_fields["affected_users"] = enrichment.affected_users
                if enrichment.business_impact:
                    updated_fields["business_impact"] = enrichment.business_impact
                if enrichment.current_workaround:
                    updated_fields["current_workaround"] = enrichment.current_workaround

        elif driver_type == "goal":
            from app.chains.enrich_goal import enrich_goal
            enrichment_result = await enrich_goal(driver_id, project_id, depth)

            if enrichment_result["success"] and enrichment_result["enrichment"]:
                enrichment = enrichment_result["enrichment"]
                if enrichment.goal_timeframe:
                    updated_fields["goal_timeframe"] = enrichment.goal_timeframe
                if enrichment.success_criteria:
                    updated_fields["success_criteria"] = enrichment.success_criteria
                if enrichment.dependencies:
                    updated_fields["dependencies"] = enrichment.dependencies
                if enrichment.owner:
                    updated_fields["owner"] = enrichment.owner

        else:
            raise HTTPException(status_code=400, detail=f"Unknown driver type: {driver_type}")

        # Update enrichment status
        if enrichment_result and enrichment_result["success"] and updated_fields:
            updated_fields["enrichment_status"] = "enriched"
            updated_fields["enrichment_attempted_at"] = "now()"
            updated_fields["enrichment_error"] = None

            # Update driver
            driver = drivers_db.update_business_driver(driver_id, project_id, **updated_fields)

            # Auto-link to related features after enrichment
            linked_count = drivers_db.auto_link_driver_to_features(driver_id, project_id)

            logger.info(
                f"Enrichment successful for {driver_type} driver {driver_id}, linked to {linked_count} features",
                extra={"updated_fields": list(updated_fields.keys())},
            )

            return BusinessDriverOut(**driver)
        elif enrichment_result and not enrichment_result["success"]:
            # Mark enrichment as attempted but failed
            error_msg = enrichment_result.get("error", "Unknown error")
            drivers_db.update_business_driver(
                driver_id,
                project_id,
                enrichment_status="none",
                enrichment_attempted_at="now()",
                enrichment_error=error_msg,
            )
            raise HTTPException(status_code=500, detail=f"Enrichment failed: {error_msg}")
        else:
            # No enrichment data found
            drivers_db.update_business_driver(
                driver_id,
                project_id,
                enrichment_status="none",
                enrichment_attempted_at="now()",
                enrichment_error="No enrichment data could be extracted from signals",
            )
            raise HTTPException(status_code=404, detail="No enrichment data found in signals")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enriching business driver: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/type/{driver_type}", response_model=BusinessDriverListResponse)
async def get_drivers_by_type(
    project_id: UUID = Path(..., description="Project UUID"),
    driver_type: Literal["kpi", "pain", "goal"] = Path(..., description="Driver type"),
) -> BusinessDriverListResponse:
    """
    Get all business drivers of a specific type.

    Args:
        project_id: Project UUID
        driver_type: Type to filter by (kpi, pain, goal)

    Returns:
        List of drivers of that type
    """
    try:
        result = drivers_db.list_business_drivers(project_id, driver_type=driver_type)
        drivers = result.get("business_drivers", [])

        by_type = {driver_type: len(drivers)}

        return BusinessDriverListResponse(
            business_drivers=[BusinessDriverOut(**d) for d in drivers],
            total=len(drivers),
            by_type=by_type,
        )

    except Exception as e:
        logger.error(f"Error getting drivers by type: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/enrich-bulk")
async def bulk_enrich_drivers(
    project_id: UUID = Path(..., description="Project UUID"),
    driver_type: Literal["kpi", "pain", "goal", "all"] | None = Query(None, description="Filter by type"),
    depth: Literal["quick", "standard", "deep"] = Query("standard", description="Enrichment depth"),
) -> dict[str, Any]:
    """
    Bulk enrich multiple business drivers.

    Enriches all non-enriched drivers (or drivers of a specific type).
    Processes in parallel with max concurrency of 5.

    Args:
        project_id: Project UUID
        driver_type: Optional filter by type (kpi, pain, goal, all)
        depth: Enrichment depth

    Returns:
        Summary with total, succeeded, failed, and error details
    """
    import asyncio

    try:
        # Get all drivers (or filtered by type)
        filter_type = None if driver_type == "all" else driver_type
        all_drivers = drivers_db.list_business_drivers(project_id, driver_type=filter_type)

        # Filter to only non-enriched drivers
        drivers_to_enrich = [
            d for d in all_drivers
            if d.get("enrichment_status") != "enriched"
        ]

        if not drivers_to_enrich:
            return {
                "total": 0,
                "succeeded": 0,
                "failed": 0,
                "skipped": len(all_drivers),
                "message": "All drivers already enriched",
            }

        logger.info(
            f"Starting bulk enrichment of {len(drivers_to_enrich)} drivers",
            extra={"project_id": str(project_id), "driver_type": driver_type, "depth": depth},
        )

        # Enrich in parallel with max concurrency
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent
        results = {"succeeded": 0, "failed": 0, "errors": []}

        async def enrich_one(driver):
            async with semaphore:
                try:
                    driver_id = UUID(driver["id"])
                    driver_type = driver["driver_type"]

                    # Call appropriate enrichment chain
                    enrichment_result = None
                    updated_fields = {}

                    if driver_type == "kpi":
                        from app.chains.enrich_kpi import enrich_kpi
                        enrichment_result = await enrich_kpi(driver_id, project_id, depth)

                        if enrichment_result["success"] and enrichment_result["enrichment"]:
                            enrichment = enrichment_result["enrichment"]
                            if enrichment.get("baseline_value"):
                                updated_fields["baseline_value"] = enrichment["baseline_value"]
                            if enrichment.get("target_value"):
                                updated_fields["target_value"] = enrichment["target_value"]
                            if enrichment.get("measurement_method"):
                                updated_fields["measurement_method"] = enrichment["measurement_method"]
                            if enrichment.get("tracking_frequency"):
                                updated_fields["tracking_frequency"] = enrichment["tracking_frequency"]
                            if enrichment.get("data_source"):
                                updated_fields["data_source"] = enrichment["data_source"]
                            if enrichment.get("responsible_team"):
                                updated_fields["responsible_team"] = enrichment["responsible_team"]

                    elif driver_type == "pain":
                        from app.chains.enrich_pain_point import enrich_pain_point
                        enrichment_result = await enrich_pain_point(driver_id, project_id, depth)

                        if enrichment_result["success"] and enrichment_result["enrichment"]:
                            enrichment = enrichment_result["enrichment"]
                            if enrichment.get("severity"):
                                updated_fields["severity"] = enrichment["severity"]
                            if enrichment.get("frequency"):
                                updated_fields["frequency"] = enrichment["frequency"]
                            if enrichment.get("affected_users"):
                                updated_fields["affected_users"] = enrichment["affected_users"]
                            if enrichment.get("business_impact"):
                                updated_fields["business_impact"] = enrichment["business_impact"]
                            if enrichment.get("current_workaround"):
                                updated_fields["current_workaround"] = enrichment["current_workaround"]

                    elif driver_type == "goal":
                        from app.chains.enrich_goal import enrich_goal
                        enrichment_result = await enrich_goal(driver_id, project_id, depth)

                        if enrichment_result["success"] and enrichment_result["enrichment"]:
                            enrichment = enrichment_result["enrichment"]
                            if enrichment.get("goal_timeframe"):
                                updated_fields["goal_timeframe"] = enrichment["goal_timeframe"]
                            if enrichment.get("success_criteria"):
                                updated_fields["success_criteria"] = enrichment["success_criteria"]
                            if enrichment.get("dependencies"):
                                updated_fields["dependencies"] = enrichment["dependencies"]
                            if enrichment.get("owner"):
                                updated_fields["owner"] = enrichment["owner"]

                    # Update if successful
                    if enrichment_result and enrichment_result["success"] and updated_fields:
                        updated_fields["enrichment_status"] = "enriched"
                        updated_fields["enrichment_attempted_at"] = "now()"
                        updated_fields["enrichment_error"] = None
                        drivers_db.update_business_driver(driver_id, project_id, **updated_fields)

                        # Auto-link to features
                        drivers_db.auto_link_driver_to_features(driver_id, project_id)

                        results["succeeded"] += 1
                    else:
                        # No data found
                        drivers_db.update_business_driver(
                            driver_id,
                            project_id,
                            enrichment_status="none",
                            enrichment_attempted_at="now()",
                            enrichment_error="No enrichment data found",
                        )
                        results["failed"] += 1
                        results["errors"].append({
                            "driver_id": str(driver_id),
                            "description": driver["description"][:50],
                            "error": "No enrichment data found",
                        })

                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append({
                        "driver_id": driver.get("id"),
                        "description": driver.get("description", "")[:50],
                        "error": str(e),
                    })
                    logger.error(f"Failed to enrich driver {driver.get('id')}: {e}")

        # Run all enrichments
        await asyncio.gather(*[enrich_one(d) for d in drivers_to_enrich])

        logger.info(
            f"Bulk enrichment complete: {results['succeeded']} succeeded, {results['failed']} failed",
            extra={"project_id": str(project_id)},
        )

        return {
            "total": len(drivers_to_enrich),
            "succeeded": results["succeeded"],
            "failed": results["failed"],
            "errors": results["errors"][:10],  # Limit error details
        }

    except Exception as e:
        logger.error(f"Error in bulk enrichment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{driver_id}/associations")
async def get_driver_associations(
    project_id: UUID = Path(..., description="Project UUID"),
    driver_id: UUID = Path(..., description="Business driver UUID"),
) -> dict[str, Any]:
    """
    Get cross-entity associations for a business driver.

    Finds related entities through:
    - Evidence overlap (shared signal chunks)
    - Semantic similarity
    - Domain-specific rules (e.g., personas affected by pains)

    Args:
        project_id: Project UUID
        driver_id: Business driver UUID

    Returns:
        Dict with:
        - features: Features associated with this driver
        - personas: Personas impacted by or linked to this driver
        - related_kpis: Related KPI drivers
        - related_pains: Related pain drivers
        - related_goals: Related goal drivers
    """
    try:
        # Verify driver exists and belongs to project
        existing = drivers_db.get_business_driver(driver_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Business driver not found")
        if str(existing.get("project_id")) != str(project_id):
            raise HTTPException(status_code=404, detail="Business driver not found in this project")

        logger.info(
            f"Getting associations for driver {driver_id}",
            extra={"project_id": str(project_id), "driver_id": str(driver_id)},
        )

        # Get associations
        features = drivers_db.get_driver_associated_features(driver_id)
        personas = drivers_db.get_driver_associated_personas(driver_id)
        related_drivers = drivers_db.get_driver_related_drivers(driver_id)

        return {
            "features": features,
            "personas": personas,
            "related_kpis": related_drivers.get("related_kpis", []),
            "related_pains": related_drivers.get("related_pains", []),
            "related_goals": related_drivers.get("related_goals", []),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting driver associations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
