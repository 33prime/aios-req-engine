"""API endpoints for ICP signal extraction system."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.chains.route_icp_signals import route_signal
from app.chains.score_icp_consultant import compute_consultant_score
from app.core.auth_middleware import AuthContext, require_consultant
from app.core.logging import get_logger
from app.core.schemas_icp import (
    ICPConsultantScore,
    ICPMetrics,
    ICPProfile,
    ICPProfileCreate,
    ICPProfileUpdate,
    ICPSignal,
    ICPSignalReview,
    PostHogWebhookPayload,
)
from app.db.icp_profiles import (
    create_icp_profile,
    get_icp_profile,
    list_icp_profiles,
    update_icp_profile,
)
from app.db.icp_scores import get_user_scores, upsert_consultant_score
from app.db.icp_signals import (
    get_review_queue,
    get_signal_metrics,
    get_user_signals,
    update_signal_routing,
)
from app.services.posthog_ingest import process_posthog_webhook

logger = get_logger(__name__)

router = APIRouter(prefix="/icp", tags=["icp"])


# ============================================================================
# ICP Profiles
# ============================================================================


@router.get("/profiles", response_model=list[ICPProfile])
async def list_profiles(
    active_only: bool = True,
    auth: AuthContext = Depends(require_consultant),
):
    """List active ICP profiles."""
    profiles = await list_icp_profiles(active_only=active_only)
    return profiles


@router.post("/profiles", response_model=ICPProfile)
async def create_profile(
    data: ICPProfileCreate,
    auth: AuthContext = Depends(require_consultant),
):
    """Create a new ICP profile. Requires super_admin role."""
    # Check for super_admin
    if not _is_super_admin(auth):
        raise HTTPException(status_code=403, detail="Super admin access required")

    profile = await create_icp_profile(data.model_dump(mode="json"))
    return profile


@router.patch("/profiles/{profile_id}", response_model=ICPProfile)
async def update_profile(
    profile_id: UUID,
    data: ICPProfileUpdate,
    auth: AuthContext = Depends(require_consultant),
):
    """Update an ICP profile. Requires super_admin role."""
    if not _is_super_admin(auth):
        raise HTTPException(status_code=403, detail="Super admin access required")

    update_data = {k: v for k, v in data.model_dump(mode="json").items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    profile = await update_icp_profile(profile_id, update_data)
    if not profile:
        raise HTTPException(status_code=404, detail="ICP profile not found")
    return profile


# ============================================================================
# ICP Signals
# ============================================================================


@router.get("/signals/review", response_model=list[ICPSignal])
async def get_signals_review_queue(
    limit: int = 50,
    offset: int = 0,
    auth: AuthContext = Depends(require_consultant),
):
    """Get signals pending review. Requires super_admin role."""
    if not _is_super_admin(auth):
        raise HTTPException(status_code=403, detail="Super admin access required")
    return await get_review_queue(limit=limit, offset=offset)


@router.patch("/signals/{signal_id}/review")
async def review_signal(
    signal_id: UUID,
    review: ICPSignalReview,
    auth: AuthContext = Depends(require_consultant),
):
    """Approve or dismiss a signal. Requires super_admin role."""
    if not _is_super_admin(auth):
        raise HTTPException(status_code=403, detail="Super admin access required")

    if review.action == "approve":
        status = "auto_routed"
    elif review.action == "dismiss":
        status = "dismissed"
    else:
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'dismiss'")

    result = await update_signal_routing(
        signal_id=signal_id,
        routing_status=status,
        matched_profile_id=review.matched_profile_id,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Signal not found")
    return {"status": "ok", "signal": result}


@router.post("/signals/ingest")
async def ingest_posthog_signals(
    payload: PostHogWebhookPayload,
):
    """Receive batch of PostHog events and route them as ICP signals.

    This endpoint is called by PostHog webhooks or batch ingestion.
    No auth required — validated by API key or webhook secret at infra level.
    """
    events = [e.model_dump(mode="json") for e in payload.events]
    counts = await process_posthog_webhook(events)
    return counts


# ============================================================================
# ICP Metrics
# ============================================================================


@router.get("/metrics", response_model=ICPMetrics)
async def get_metrics(
    auth: AuthContext = Depends(require_consultant),
):
    """Get aggregated ICP signal metrics. Requires super_admin role."""
    if not _is_super_admin(auth):
        raise HTTPException(status_code=403, detail="Super admin access required")
    metrics = await get_signal_metrics()
    return ICPMetrics(**metrics)


# ============================================================================
# ICP Scores
# ============================================================================


@router.get("/scores/me")
async def get_my_scores(
    auth: AuthContext = Depends(require_consultant),
):
    """Get the authenticated consultant's ICP scores."""
    scores = await get_user_scores(auth.user_id)
    return scores


@router.post("/scores/compute")
async def compute_scores(
    auth: AuthContext = Depends(require_consultant),
):
    """Trigger ICP score computation for all consultants. Requires super_admin."""
    if not _is_super_admin(auth):
        raise HTTPException(status_code=403, detail="Super admin access required")

    profiles = await list_icp_profiles(active_only=True)
    if not profiles:
        return {"status": "ok", "message": "No active ICP profiles", "computed": 0}

    # Get all unique user IDs from signals
    from app.db.supabase_client import get_supabase
    client = get_supabase()
    user_result = (
        client.table("icp_signals")
        .select("user_id")
        .eq("routing_status", "auto_routed")
        .execute()
    )

    unique_users = set(row["user_id"] for row in (user_result.data or []))
    computed = 0

    for user_id_str in unique_users:
        user_id = UUID(user_id_str)
        for profile in profiles:
            # Get user's signals matched to this profile
            user_signals = (
                client.table("icp_signals")
                .select("*")
                .eq("user_id", user_id_str)
                .eq("matched_profile_id", str(profile["id"]))
                .eq("routing_status", "auto_routed")
                .execute()
            ).data or []

            if not user_signals:
                continue

            score_result = compute_consultant_score(user_signals, profile)
            await upsert_consultant_score(
                user_id=user_id,
                profile_id=UUID(profile["id"]),
                score=score_result["score"],
                signal_count=score_result["signal_count"],
                scoring_breakdown=score_result["scoring_breakdown"],
            )
            computed += 1

    return {"status": "ok", "computed": computed, "users": len(unique_users)}


# ============================================================================
# Helpers
# ============================================================================


def _is_super_admin(auth: AuthContext) -> bool:
    """Check if user has super_admin platform role."""
    # Check profile for platform_role
    try:
        from app.db.supabase_client import get_supabase
        client = get_supabase()
        result = (
            client.table("profiles")
            .select("platform_role")
            .eq("user_id", str(auth.user_id))
            .execute()
        )
        if result.data:
            return result.data[0].get("platform_role") == "super_admin"
    except Exception:
        pass
    return False
