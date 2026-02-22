"""Workspace endpoints for business driver detail and financials."""

import asyncio
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
        # Round 1: Fetch driver
        driver = get_business_driver(str(driver_id))
        if not driver:
            raise HTTPException(status_code=404, detail="Business driver not found")
        if driver.get("project_id") != str(project_id):
            raise HTTPException(status_code=403, detail="Driver does not belong to this project")

        dtype = driver.get("driver_type", "")
        evidence = _parse_evidence(driver.get("evidence"))

        missing = 0
        if dtype == "kpi":
            missing = sum(1 for f in [
                driver.get("baseline_value"),
                driver.get("target_value"),
                driver.get("measurement_method"),
            ] if not f)

        # Round 2: All association lookups + history in parallel
        linked_persona_ids = driver.get("linked_persona_ids") or []
        linked_feature_ids = driver.get("linked_feature_ids") or []
        linked_driver_ids = driver.get("linked_driver_ids") or []

        def _q_personas():
            if linked_persona_ids:
                try:
                    rows = client.table("personas").select(
                        "id, name, role"
                    ).in_("id", [str(pid) for pid in linked_persona_ids]).execute()
                    return [AssociatedPersona(
                        id=p["id"], name=p.get("name", ""), role=p.get("role"),
                        association_reason="Linked via enrichment analysis",
                    ) for p in (rows.data or [])]
                except Exception:
                    pass
            # Fallback
            try:
                raw = get_driver_associated_personas(str(driver_id))
                return [AssociatedPersona(
                    id=p.get("id", ""), name=p.get("name", ""), role=p.get("role"),
                    association_reason=p.get("association_reason", "Evidence overlap"),
                ) for p in (raw or [])]
            except Exception:
                return []

        def _q_features():
            if linked_feature_ids:
                try:
                    rows = client.table("features").select(
                        "id, name, category, confirmation_status"
                    ).in_("id", [str(fid) for fid in linked_feature_ids]).execute()
                    return [AssociatedFeature(
                        id=f["id"], name=f.get("name", ""), category=f.get("category"),
                        confirmation_status=f.get("confirmation_status"),
                        association_reason="Linked via enrichment analysis",
                    ) for f in (rows.data or [])]
                except Exception:
                    pass
            # Fallback
            try:
                raw = get_driver_associated_features(str(driver_id))
                return [AssociatedFeature(
                    id=f.get("id", ""), name=f.get("name", ""), category=f.get("category"),
                    confirmation_status=f.get("confirmation_status"),
                    association_reason=f.get("association_reason", "Evidence overlap"),
                ) for f in (raw or [])]
            except Exception:
                return []

        def _q_related():
            if linked_driver_ids:
                try:
                    rows = client.table("business_drivers").select(
                        "id, description, driver_type"
                    ).in_("id", [str(did) for did in linked_driver_ids]).execute()
                    return [RelatedDriver(
                        id=r["id"], description=r.get("description", ""),
                        driver_type=r.get("driver_type", ""),
                        relationship="Linked via enrichment analysis",
                    ) for r in (rows.data or [])]
                except Exception:
                    pass
            # Fallback
            try:
                raw = get_driver_related_drivers(str(driver_id))
                return [RelatedDriver(
                    id=r.get("id", ""), description=r.get("description", ""),
                    driver_type=r.get("driver_type", ""),
                    relationship=r.get("relationship", ""),
                ) for r in (raw or [])]
            except Exception:
                return []

        def _q_history():
            return get_entity_history(str(driver_id)) or []

        def _q_versions():
            return count_entity_versions(str(driver_id))

        (
            assoc_personas, assoc_features, related, raw_history, revision_count,
        ) = await asyncio.gather(
            asyncio.to_thread(_q_personas),
            asyncio.to_thread(_q_features),
            asyncio.to_thread(_q_related),
            asyncio.to_thread(_q_history),
            asyncio.to_thread(_q_versions),
        )

        # History
        revisions: list[RevisionEntry] = []
        for h in raw_history:
            revisions.append(RevisionEntry(
                revision_number=h.get("revision_number", 0),
                revision_type=h.get("revision_type", ""),
                diff_summary=h.get("diff_summary", ""),
                changes=h.get("changes"),
                created_at=h.get("created_at", ""),
                created_by=h.get("created_by"),
            ))

        # Relatability score (in-memory, uses resolved associations)
        from app.core.relatability import compute_relatability_score
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
            business_impact=driver.get("business_impact"),
            affected_users=driver.get("affected_users"),
            current_workaround=driver.get("current_workaround"),
            frequency=driver.get("frequency"),
            success_criteria=driver.get("success_criteria"),
            owner=driver.get("owner"),
            goal_timeframe=driver.get("goal_timeframe"),
            dependencies=driver.get("dependencies"),
            baseline_value=driver.get("baseline_value"),
            target_value=driver.get("target_value"),
            measurement_method=driver.get("measurement_method"),
            tracking_frequency=driver.get("tracking_frequency"),
            data_source=driver.get("data_source"),
            responsible_team=driver.get("responsible_team"),
            missing_field_count=missing,
            monetary_value_low=driver.get("monetary_value_low"),
            monetary_value_high=driver.get("monetary_value_high"),
            monetary_type=driver.get("monetary_type"),
            monetary_timeframe=driver.get("monetary_timeframe"),
            monetary_confidence=driver.get("monetary_confidence"),
            monetary_source=driver.get("monetary_source"),
            associated_personas=assoc_personas,
            associated_features=assoc_features,
            related_drivers=related,
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
