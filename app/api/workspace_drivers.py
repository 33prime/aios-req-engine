"""Workspace endpoints for business driver detail and financials."""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.workspace_helpers import _parse_evidence
from app.core.schemas_brd import (
    AssociatedFeature,
    AssociatedPersona,
    BusinessDriverDetail,
    BusinessDriverFinancialUpdate,
    RelatedDriver,
    RevisionEntry,
)
from app.db.supabase_client import get_supabase as get_client

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/brd/drivers/backfill-links")
async def backfill_driver_links_endpoint(project_id: UUID) -> dict:
    """Backfill linked_*_ids arrays for all business drivers in a project.

    Uses evidence overlap for feature links, text matching for persona/workflow links.
    Safe to run multiple times (idempotent).
    """
    from app.db.business_drivers import backfill_driver_links

    try:
        stats = backfill_driver_links(project_id)
        return {"success": True, **stats}
    except Exception as e:
        logger.exception(f"Failed to backfill driver links for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/brd/drivers/{driver_id}/detail", response_model=BusinessDriverDetail)
async def get_brd_driver_detail(project_id: UUID, driver_id: UUID) -> BusinessDriverDetail:
    """
    Get full detail for a business driver including associations and history.
    Used by the detail drawer in the BRD canvas.
    """
    from app.db.business_drivers import (
        get_business_driver,
        get_driver_associated_features,
        get_driver_associated_personas,
        get_driver_related_drivers,
    )
    from app.db.change_tracking import count_entity_versions, get_entity_history

    client = get_client()

    try:
        driver = get_business_driver(str(driver_id))
        if not driver:
            raise HTTPException(status_code=404, detail="Business driver not found")

        # Verify project ownership
        if driver.get("project_id") != str(project_id):
            raise HTTPException(status_code=403, detail="Driver does not belong to this project")

        dtype = driver.get("driver_type", "")
        evidence = _parse_evidence(driver.get("evidence"))

        # Compute missing_field_count for KPIs
        missing = 0
        if dtype == "kpi":
            missing = sum(1 for f in [
                driver.get("baseline_value"),
                driver.get("target_value"),
                driver.get("measurement_method"),
            ] if not f)

        # Resolve explicit link arrays into association objects
        assoc_personas: list[AssociatedPersona] = []
        linked_persona_ids = driver.get("linked_persona_ids") or []
        if linked_persona_ids:
            try:
                persona_rows = client.table("personas").select(
                    "id, name, role"
                ).in_("id", [str(pid) for pid in linked_persona_ids]).execute()
                for p in (persona_rows.data or []):
                    assoc_personas.append(AssociatedPersona(
                        id=p["id"],
                        name=p.get("name", ""),
                        role=p.get("role"),
                        association_reason="Linked via enrichment analysis",
                    ))
            except Exception:
                logger.debug(f"Could not resolve linked personas for driver {driver_id}")

        # Fallback to old overlap method if no explicit links
        if not assoc_personas:
            try:
                raw_personas = get_driver_associated_personas(str(driver_id))
                for p in (raw_personas or []):
                    assoc_personas.append(AssociatedPersona(
                        id=p.get("id", ""),
                        name=p.get("name", ""),
                        role=p.get("role"),
                        association_reason=p.get("association_reason", "Evidence overlap"),
                    ))
            except Exception:
                pass

        assoc_features: list[AssociatedFeature] = []
        linked_feature_ids = driver.get("linked_feature_ids") or []
        if linked_feature_ids:
            try:
                feature_rows = client.table("features").select(
                    "id, name, category, confirmation_status"
                ).in_("id", [str(fid) for fid in linked_feature_ids]).execute()
                for f in (feature_rows.data or []):
                    assoc_features.append(AssociatedFeature(
                        id=f["id"],
                        name=f.get("name", ""),
                        category=f.get("category"),
                        confirmation_status=f.get("confirmation_status"),
                        association_reason="Linked via enrichment analysis",
                    ))
            except Exception:
                logger.debug(f"Could not resolve linked features for driver {driver_id}")

        if not assoc_features:
            try:
                raw_features = get_driver_associated_features(str(driver_id))
                for f in (raw_features or []):
                    assoc_features.append(AssociatedFeature(
                        id=f.get("id", ""),
                        name=f.get("name", ""),
                        category=f.get("category"),
                        confirmation_status=f.get("confirmation_status"),
                        association_reason=f.get("association_reason", "Evidence overlap"),
                    ))
            except Exception:
                pass

        related: list[RelatedDriver] = []
        linked_driver_ids = driver.get("linked_driver_ids") or []
        if linked_driver_ids:
            try:
                driver_rows = client.table("business_drivers").select(
                    "id, description, driver_type"
                ).in_("id", [str(did) for did in linked_driver_ids]).execute()
                for r in (driver_rows.data or []):
                    related.append(RelatedDriver(
                        id=r["id"],
                        description=r.get("description", ""),
                        driver_type=r.get("driver_type", ""),
                        relationship="Linked via enrichment analysis",
                    ))
            except Exception:
                logger.debug(f"Could not resolve linked drivers for driver {driver_id}")

        if not related:
            try:
                raw_related = get_driver_related_drivers(str(driver_id))
                for r in (raw_related or []):
                    related.append(RelatedDriver(
                        id=r.get("id", ""),
                        description=r.get("description", ""),
                        driver_type=r.get("driver_type", ""),
                        relationship=r.get("relationship", ""),
                    ))
            except Exception:
                pass

        # History
        revisions: list[RevisionEntry] = []
        revision_count = 0
        try:
            raw_history = get_entity_history(str(driver_id))
            for h in (raw_history or []):
                revisions.append(RevisionEntry(
                    revision_number=h.get("revision_number", 0),
                    revision_type=h.get("revision_type", ""),
                    diff_summary=h.get("diff_summary", ""),
                    changes=h.get("changes"),
                    created_at=h.get("created_at", ""),
                    created_by=h.get("created_by"),
                ))
            revision_count = count_entity_versions(str(driver_id))
        except Exception:
            logger.debug(f"Could not fetch history for driver {driver_id}")

        # Compute relatability score
        from app.core.relatability import compute_relatability_score
        # Build minimal project_entities for scoring — use resolved associations
        score_entities = {
            "features": [{"id": f.id, "confirmation_status": f.confirmation_status} for f in assoc_features],
            "personas": [{"id": p.id, "confirmation_status": None} for p in assoc_personas],
            "vp_steps": [],
            "drivers": [{"id": r.id, "confirmation_status": None} for r in related],
        }
        score = compute_relatability_score(driver, score_entities)

        return BusinessDriverDetail(
            id=driver["id"],
            description=driver.get("description", ""),
            driver_type=dtype,
            severity=driver.get("severity"),
            confirmation_status=driver.get("confirmation_status"),
            version=driver.get("version"),
            evidence=evidence,
            # Pain
            business_impact=driver.get("business_impact"),
            affected_users=driver.get("affected_users"),
            current_workaround=driver.get("current_workaround"),
            frequency=driver.get("frequency"),
            # Goal
            success_criteria=driver.get("success_criteria"),
            owner=driver.get("owner"),
            goal_timeframe=driver.get("goal_timeframe"),
            dependencies=driver.get("dependencies"),
            # KPI
            baseline_value=driver.get("baseline_value"),
            target_value=driver.get("target_value"),
            measurement_method=driver.get("measurement_method"),
            tracking_frequency=driver.get("tracking_frequency"),
            data_source=driver.get("data_source"),
            responsible_team=driver.get("responsible_team"),
            missing_field_count=missing,
            # Monetary impact
            monetary_value_low=driver.get("monetary_value_low"),
            monetary_value_high=driver.get("monetary_value_high"),
            monetary_type=driver.get("monetary_type"),
            monetary_timeframe=driver.get("monetary_timeframe"),
            monetary_confidence=driver.get("monetary_confidence"),
            monetary_source=driver.get("monetary_source"),
            # Associations
            associated_personas=assoc_personas,
            associated_features=assoc_features,
            related_drivers=related,
            # Relatability intelligence
            relatability_score=score,
            linked_feature_count=len(driver.get("linked_feature_ids") or []),
            linked_persona_count=len(driver.get("linked_persona_ids") or []),
            linked_workflow_count=len(driver.get("linked_vp_step_ids") or []),
            vision_alignment=driver.get("vision_alignment"),
            is_stale=driver.get("is_stale", False),
            stale_reason=driver.get("stale_reason"),
            revision_count=revision_count,
            revisions=revisions,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get driver detail for {driver_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/brd/drivers/{driver_id}/financials")
async def update_driver_financials(
    project_id: UUID,
    driver_id: UUID,
    data: BusinessDriverFinancialUpdate,
) -> dict:
    """Update financial impact fields on a KPI business driver."""
    from app.db.business_drivers import get_business_driver

    client = get_client()

    try:
        driver = get_business_driver(str(driver_id))
        if not driver:
            raise HTTPException(status_code=404, detail="Business driver not found")

        if driver.get("project_id") != str(project_id):
            raise HTTPException(status_code=403, detail="Driver does not belong to this project")

        # Build update dict from non-None fields
        update_fields: dict = {}
        for field in [
            "monetary_value_low",
            "monetary_value_high",
            "monetary_type",
            "monetary_timeframe",
            "monetary_confidence",
            "monetary_source",
        ]:
            val = getattr(data, field)
            if val is not None:
                update_fields[field] = val

        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        update_fields["updated_at"] = "now()"

        result = (
            client.table("business_drivers")
            .update(update_fields)
            .eq("id", str(driver_id))
            .execute()
        )

        if result.data:
            return result.data[0]
        raise HTTPException(status_code=500, detail="Update returned no data")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update driver financials for {driver_id}")
        raise HTTPException(status_code=500, detail=str(e))
