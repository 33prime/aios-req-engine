"""API endpoints for feature enrichment."""

import uuid
from uuid import UUID

from fastapi import APIRouter, HTTPException

# Baseline gate removed - no longer needed
from app.core.logging import get_logger
from app.core.schemas_feature_enrich import EnrichFeaturesRequest, EnrichFeaturesResponse
from app.db.jobs import complete_job, create_job, fail_job, start_job
from app.graphs.enrich_features_graph import run_enrich_features_agent

logger = get_logger(__name__)

router = APIRouter()


@router.post("/agents/enrich-features", response_model=EnrichFeaturesResponse)
async def enrich_features(request: EnrichFeaturesRequest) -> EnrichFeaturesResponse:
    """
    Enrich features with structured details from project context.

    This endpoint:
    1. Selects features to enrich (all, specific IDs, or MVP only)
    2. Gathers context from facts, insights, confirmations, and signals
    3. Runs enrichment LLM on each feature
    4. Stores enrichment details in feature.details JSONB column
    5. Tracks enrichment metadata (model, prompt version, etc.)

    Args:
        request: EnrichFeaturesRequest with project_id and enrichment options

    Returns:
        EnrichFeaturesResponse with processing counts and summary

    Raises:
        HTTPException 500: If enrichment fails
    """
    run_id = uuid.uuid4()
    job_id: UUID | None = None

    try:
        # Create and start job
        job_id = create_job(
            project_id=request.project_id,
            job_type="enrich_features",
            input_json={
                "feature_ids": [str(fid) for fid in (request.feature_ids or [])],
                "only_mvp": request.only_mvp,
                "include_research": request.include_research,
                "top_k_context": request.top_k_context,
            },
            run_id=run_id,
        )
        start_job(job_id)

        logger.info(
            f"Starting feature enrichment for project {request.project_id}",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "project_id": str(request.project_id),
                "feature_ids": request.feature_ids,
                "only_mvp": request.only_mvp,
                "research_enabled": request.include_research,
            },
        )

        # Run the enrich features agent
        features_processed, features_updated, summary = run_enrich_features_agent(
            project_id=request.project_id,
            run_id=run_id,
            job_id=job_id,
            feature_ids=request.feature_ids,
            only_mvp=request.only_mvp,
            include_research=request.include_research,
            top_k_context=request.top_k_context,
        )

        # Complete job
        output = {
            "features_processed": features_processed,
            "features_updated": features_updated,
            "summary": summary,
        }
        complete_job(job_id, output)

        # Mark unified memory synthesis as stale so DI Agent sees fresh data
        try:
            from app.core.unified_memory_synthesis import mark_synthesis_stale
            mark_synthesis_stale(request.project_id, "feature_enriched")
        except Exception as e:
            logger.warning(f"Failed to mark memory stale: {e}")

        # Refresh state snapshot so subsequent operations have fresh context
        try:
            from app.core.state_snapshot import regenerate_state_snapshot
            regenerate_state_snapshot(request.project_id)
        except Exception as e:
            logger.warning(f"Failed to refresh state snapshot: {e}")

        logger.info(
            f"Completed feature enrichment: {features_processed} processed, {features_updated} updated",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "features_processed": features_processed,
                "features_updated": features_updated,
            },
        )

        return EnrichFeaturesResponse(
            run_id=run_id,
            job_id=job_id,
            features_processed=features_processed,
            features_updated=features_updated,
            summary=summary,
        )

    except Exception as e:
        error_msg = f"Feature enrichment failed: {str(e)}"
        logger.error(error_msg, extra={"run_id": str(run_id)})

        if job_id:
            fail_job(job_id, error_msg)

        raise HTTPException(status_code=500, detail=error_msg) from e
