"""API endpoints for consultant profile enrichment."""

from fastapi import APIRouter, Depends, HTTPException

from app.chains.enrich_consultant import enrich_consultant_profile
from app.core.analytics import track_server_event
from app.core.auth_middleware import AuthContext, require_consultant
from app.core.logging import get_logger
from app.core.schemas_consultant import (
    ConsultantEnrichmentStatus,
    ConsultantEnrichRequest,
    ConsultantEnrichResponse,
)
from app.db.profiles import get_profile_by_user_id, update_profile_enrichment

logger = get_logger(__name__)

router = APIRouter(prefix="/consultant-enrichment", tags=["consultant_enrichment"])


@router.post("/enrich", response_model=ConsultantEnrichResponse)
async def enrich_profile(
    request: ConsultantEnrichRequest,
    auth: AuthContext = Depends(require_consultant),
):
    """Trigger consultant profile enrichment from raw text sources."""
    user_id = auth.user_id

    if not any([request.linkedin_text, request.website_text, request.additional_context]):
        raise HTTPException(status_code=400, detail="At least one text source required")

    # Mark as enriching
    await update_profile_enrichment(user_id, {
        "enrichment_status": "enriching",
        "linkedin_raw_text": request.linkedin_text,
        "website_raw_text": request.website_text,
    })

    try:
        enriched, metadata = enrich_consultant_profile(
            linkedin_text=request.linkedin_text,
            website_text=request.website_text,
            additional_context=request.additional_context,
        )

        # Persist enrichment results
        enrichment_data = {
            "enrichment_status": "enriched",
            "enriched_profile": enriched.model_dump(mode="json"),
            "industry_expertise": [iv.industry for iv in enriched.industry_verticals],
            "methodology_expertise": enriched.methodology_expertise,
            "consulting_style": enriched.consulting_approach.model_dump(mode="json"),
            "consultant_summary": enriched.professional_summary,
            "profile_completeness": enriched.profile_completeness,
            "enriched_at": "now()",
            "enrichment_source": _determine_source(request),
        }

        await update_profile_enrichment(user_id, enrichment_data)

        # Log the enrichment run
        from app.db.supabase_client import get_supabase
        get_supabase().table("consultant_enrichment_logs").insert({
            "user_id": str(user_id),
            "trigger_type": "user_request",
            "input_sources": {
                "linkedin": bool(request.linkedin_text),
                "website": bool(request.website_text),
                "additional": bool(request.additional_context),
            },
            "enriched_profile": enriched.model_dump(mode="json"),
            "profile_completeness": enriched.profile_completeness,
            "model_used": metadata.get("model"),
            "tokens_used": metadata.get("tokens_used", 0),
            "duration_ms": metadata.get("duration_ms", 0),
            "status": "completed",
            "completed_at": "now()",
        }).execute()

        track_server_event(str(user_id), "consultant_enriched", {
            "profile_completeness": enriched.profile_completeness,
            "source": _determine_source(request),
            "tokens_used": metadata.get("tokens_used", 0),
        })

        return ConsultantEnrichResponse(
            status="enriched",
            message="Profile enriched successfully",
            enriched_profile=enriched,
            profile_completeness=enriched.profile_completeness,
        )

    except Exception as e:
        logger.error(f"Enrichment failed for user {user_id}: {e}")
        await update_profile_enrichment(user_id, {"enrichment_status": "failed"})

        # Log the failure
        from app.db.supabase_client import get_supabase
        get_supabase().table("consultant_enrichment_logs").insert({
            "user_id": str(user_id),
            "trigger_type": "user_request",
            "input_sources": {
                "linkedin": bool(request.linkedin_text),
                "website": bool(request.website_text),
            },
            "status": "failed",
            "error_message": str(e)[:500],
        }).execute()

        raise HTTPException(status_code=500, detail=f"Enrichment failed: {e}")


@router.get("/status", response_model=ConsultantEnrichmentStatus)
async def get_enrichment_status(
    auth: AuthContext = Depends(require_consultant),
):
    """Get current enrichment status and enriched profile for the authenticated consultant."""
    profile = await get_profile_by_user_id(auth.user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return ConsultantEnrichmentStatus(
        enrichment_status=profile.enrichment_status,
        profile_completeness=profile.profile_completeness,
        enriched_at=profile.enriched_at,
        enrichment_source=profile.enrichment_source,
        enriched_profile=profile.enriched_profile,
        industry_expertise=profile.industry_expertise,
        methodology_expertise=profile.methodology_expertise,
        consulting_style=profile.consulting_style,
        consultant_summary=profile.consultant_summary,
    )


def _determine_source(request: ConsultantEnrichRequest) -> str:
    """Determine enrichment source label."""
    sources = []
    if request.linkedin_text:
        sources.append("linkedin")
    if request.website_text:
        sources.append("website")
    if request.additional_context:
        sources.append("additional")
    return "+".join(sources)
