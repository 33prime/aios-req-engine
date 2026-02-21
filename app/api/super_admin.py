"""Super admin endpoints for platform management."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.auth_middleware import AuthContext, require_super_admin
from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

router = APIRouter(prefix="/super-admin", tags=["super_admin"])


# =============================================================================
# Schemas
# =============================================================================


class AdminDashboardStats(BaseModel):
    total_users: int
    active_users_7d: int
    total_projects: int
    active_projects: int
    total_clients: int
    total_signals: int
    total_icp_signals: int
    total_cost_usd: float
    cost_7d_usd: float
    total_tokens: int
    projects_by_stage: dict[str, int]
    users_by_role: dict[str, int]
    recent_signups: list[dict]


class AdminUserSummary(BaseModel):
    user_id: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    photo_url: str | None = None
    platform_role: str
    enrichment_status: str | None = None
    profile_completeness: int = 0
    project_count: int = 0
    signal_count: int = 0
    total_cost_usd: float = 0
    total_tokens: int = 0
    last_active: str | None = None
    created_at: str


class AdminUserDetail(BaseModel):
    profile: dict
    projects: list[dict]
    total_signals_submitted: int
    signals_by_type: dict[str, int]
    total_entities_generated: int
    icp_scores: list[dict]
    recent_signals: list[dict]
    enriched_profile: dict | None = None
    total_cost_usd: float = 0
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    cost_by_workflow: dict[str, float] = {}
    cost_by_model: dict[str, float] = {}
    cost_30d_usd: float = 0
    recent_llm_calls: list[dict] = []


class AdminCostAnalytics(BaseModel):
    total_cost_usd: float
    total_tokens_input: int
    total_tokens_output: int
    total_calls: int
    cost_by_workflow: list[dict]
    cost_by_model: list[dict]
    cost_by_user: list[dict]
    daily_cost: list[dict]


class AdminProjectSummary(BaseModel):
    id: str
    name: str
    stage: str | None = None
    status: str | None = None
    client_name: str | None = None
    owner_id: str | None = None
    owner_name: str | None = None
    owner_photo_url: str | None = None
    signal_count: int = 0
    feature_count: int = 0
    readiness_score: float | None = None
    created_at: str


class RoleUpdateRequest(BaseModel):
    platform_role: str


# =============================================================================
# Dashboard
# =============================================================================


@router.get("/dashboard", response_model=AdminDashboardStats)
async def get_dashboard(auth: AuthContext = Depends(require_super_admin)):
    """Get aggregate platform stats for admin dashboard."""
    client = get_supabase()
    now = datetime.now(timezone.utc)
    seven_days_ago = (now - timedelta(days=7)).isoformat()

    profiles_resp = client.table("profiles").select(
        "id, email, first_name, last_name, photo_url, platform_role, created_at, updated_at"
    ).execute()
    projects_resp = client.table("projects").select("id, stage, status, created_at").execute()
    clients_resp = client.table("clients").select("id").execute()
    signals_resp = client.table("signals").select("id", count="exact").execute()

    # icp_signals might not exist yet — handle gracefully
    try:
        icp_signals_resp = client.table("icp_signals").select("id", count="exact").execute()
        icp_count = icp_signals_resp.count or len(icp_signals_resp.data or [])
    except Exception:
        icp_count = 0

    # Cost data
    try:
        cost_resp = client.table("llm_usage_log").select("estimated_cost_usd, tokens_input, tokens_output").execute()
        cost_7d_resp = (
            client.table("llm_usage_log")
            .select("estimated_cost_usd")
            .gte("created_at", seven_days_ago)
            .execute()
        )
        cost_data = cost_resp.data or []
        cost_7d_data = cost_7d_resp.data or []
    except Exception:
        cost_data = []
        cost_7d_data = []

    profiles = profiles_resp.data or []
    projects = projects_resp.data or []

    # Active users (updated in last 7 days)
    active_users_7d = sum(
        1 for p in profiles
        if p.get("updated_at") and p["updated_at"] >= seven_days_ago
    )

    # Active projects (not archived)
    active_projects = sum(1 for p in projects if p.get("status") != "archived")

    # Projects by stage
    projects_by_stage: dict[str, int] = {}
    for p in projects:
        stage = p.get("stage") or "unknown"
        projects_by_stage[stage] = projects_by_stage.get(stage, 0) + 1

    # Users by role
    users_by_role: dict[str, int] = {}
    for p in profiles:
        role = p.get("platform_role") or "consultant"
        users_by_role[role] = users_by_role.get(role, 0) + 1

    # Recent signups (last 5) — include name and email
    sorted_profiles = sorted(profiles, key=lambda p: p.get("created_at", ""), reverse=True)
    recent_signups = []
    for p in sorted_profiles[:5]:
        name = f"{p.get('first_name', '') or ''} {p.get('last_name', '') or ''}".strip()
        recent_signups.append({
            "user_id": p["id"],
            "name": name or p.get("email", "").split("@")[0],
            "email": p.get("email", ""),
            "photo_url": p.get("photo_url"),
            "platform_role": p.get("platform_role", "consultant"),
            "created_at": p.get("created_at"),
        })

    # Cost totals
    total_cost = sum(r.get("estimated_cost_usd", 0) for r in cost_data)
    total_tokens = sum(r.get("tokens_input", 0) + r.get("tokens_output", 0) for r in cost_data)
    cost_7d = sum(r.get("estimated_cost_usd", 0) for r in cost_7d_data)

    return AdminDashboardStats(
        total_users=len(profiles),
        active_users_7d=active_users_7d,
        total_projects=len(projects),
        active_projects=active_projects,
        total_clients=len(clients_resp.data or []),
        total_signals=signals_resp.count or len(signals_resp.data or []),
        total_icp_signals=icp_count,
        total_cost_usd=round(total_cost, 2),
        cost_7d_usd=round(cost_7d, 2),
        total_tokens=total_tokens,
        projects_by_stage=projects_by_stage,
        users_by_role=users_by_role,
        recent_signups=recent_signups,
    )


# =============================================================================
# Users
# =============================================================================


@router.get("/users", response_model=list[AdminUserSummary])
async def list_users(
    search: str | None = Query(None),
    role: str | None = Query(None),
    auth: AuthContext = Depends(require_super_admin),
):
    """List all platform users with stats."""
    client = get_supabase()

    query = client.table("profiles").select("*")
    if role:
        query = query.eq("platform_role", role)
    profiles_resp = query.order("created_at", desc=True).execute()
    profiles = profiles_resp.data or []

    if search:
        search_lower = search.lower()
        profiles = [
            p for p in profiles
            if search_lower in (p.get("email") or "").lower()
            or search_lower in (p.get("first_name") or "").lower()
            or search_lower in (p.get("last_name") or "").lower()
        ]

    # Get project counts per user (projects.created_by exists)
    projects_resp = client.table("projects").select("id, created_by").execute()
    project_counts: dict[str, int] = {}
    for p in (projects_resp.data or []):
        uid = p.get("created_by")
        if uid:
            project_counts[uid] = project_counts.get(uid, 0) + 1

    # Signal counts per user: signals don't have created_by,
    # so count signals per project and attribute to project owner
    signals_resp = client.table("signals").select("id, project_id").execute()
    signals_per_project: dict[str, int] = {}
    for s in (signals_resp.data or []):
        pid = s.get("project_id")
        if pid:
            signals_per_project[pid] = signals_per_project.get(pid, 0) + 1

    # Map project_id → owner
    project_owners: dict[str, str] = {}
    for p in (projects_resp.data or []):
        if p.get("created_by"):
            project_owners[p["id"]] = p["created_by"]

    signal_counts: dict[str, int] = {}
    for pid, count in signals_per_project.items():
        owner = project_owners.get(pid)
        if owner:
            signal_counts[owner] = signal_counts.get(owner, 0) + count

    # Get cost per user
    try:
        cost_resp = client.table("llm_usage_log").select("user_id, estimated_cost_usd, tokens_input, tokens_output").execute()
        user_costs: dict[str, float] = {}
        user_tokens: dict[str, int] = {}
        for r in (cost_resp.data or []):
            uid = r.get("user_id")
            if uid:
                user_costs[uid] = user_costs.get(uid, 0) + r.get("estimated_cost_usd", 0)
                user_tokens[uid] = user_tokens.get(uid, 0) + r.get("tokens_input", 0) + r.get("tokens_output", 0)
    except Exception:
        user_costs = {}
        user_tokens = {}

    result = []
    for p in profiles:
        uid = p["id"]
        result.append(AdminUserSummary(
            user_id=uid,
            email=p.get("email", ""),
            first_name=p.get("first_name"),
            last_name=p.get("last_name"),
            photo_url=p.get("photo_url"),
            platform_role=p.get("platform_role", "consultant"),
            enrichment_status=p.get("enrichment_status"),
            profile_completeness=p.get("profile_completeness") or 0,
            project_count=project_counts.get(uid, 0),
            signal_count=signal_counts.get(uid, 0),
            total_cost_usd=round(user_costs.get(uid, 0), 4),
            total_tokens=user_tokens.get(uid, 0),
            last_active=p.get("updated_at"),
            created_at=p.get("created_at", ""),
        ))

    return result


@router.get("/users/{user_id}", response_model=AdminUserDetail)
async def get_user_detail(
    user_id: UUID,
    auth: AuthContext = Depends(require_super_admin),
):
    """Get detailed user info including projects, signals, ICP scores, and cost."""
    client = get_supabase()
    uid = str(user_id)

    # Profile
    profile_resp = client.table("profiles").select("*").eq("id", uid).single().execute()
    profile = profile_resp.data

    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    # Projects owned by this user
    projects_resp = (
        client.table("projects")
        .select("id, name, stage, status, client_name, created_at")
        .eq("created_by", uid)
        .order("created_at", desc=True)
        .execute()
    )
    user_projects = projects_resp.data or []
    user_project_ids = [p["id"] for p in user_projects]

    # Signals across user's projects
    all_signals: list[dict] = []
    recent_signals: list[dict] = []
    if user_project_ids:
        all_signals_resp = (
            client.table("signals")
            .select("id, source_type, project_id, created_at")
            .in_("project_id", user_project_ids)
            .execute()
        )
        all_signals = all_signals_resp.data or []

        recent_signals_resp = (
            client.table("signals")
            .select("id, source_type, project_id, created_at")
            .in_("project_id", user_project_ids)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        recent_signals = recent_signals_resp.data or []

    signals_by_type: dict[str, int] = {}
    for s in all_signals:
        st = s.get("source_type") or "unknown"
        signals_by_type[st] = signals_by_type.get(st, 0) + 1

    # Entity counts across user's projects
    total_entities = 0
    if user_project_ids:
        features_resp = client.table("features").select("id", count="exact").in_("project_id", user_project_ids).execute()
        personas_resp = client.table("personas").select("id", count="exact").in_("project_id", user_project_ids).execute()
        total_entities = (features_resp.count or 0) + (personas_resp.count or 0)

    # ICP scores
    try:
        icp_resp = (
            client.table("icp_consultant_scores")
            .select("*, icp_profiles(name)")
            .eq("user_id", uid)
            .execute()
        )
        icp_scores = [
            {
                "profile_name": s.get("icp_profiles", {}).get("name", "Unknown") if s.get("icp_profiles") else "Unknown",
                "score": s.get("score", 0),
                "signal_count": s.get("signal_count", 0),
                "computed_at": s.get("computed_at"),
            }
            for s in (icp_resp.data or [])
        ]
    except Exception:
        icp_scores = []

    # Enriched profile data
    enriched = None
    if profile.get("enrichment_status") == "completed":
        enriched = {
            "consultant_summary": profile.get("consultant_summary"),
            "expertise_areas": profile.get("expertise_areas"),
            "industry_expertise": profile.get("industry_expertise"),
            "methodology_expertise": profile.get("methodology_expertise"),
        }

    # Cost data
    try:
        cost_resp = (
            client.table("llm_usage_log")
            .select("workflow, model, estimated_cost_usd, tokens_input, tokens_output, created_at, duration_ms")
            .eq("user_id", uid)
            .execute()
        )
        cost_data = cost_resp.data or []
    except Exception:
        cost_data = []

    total_cost = sum(r.get("estimated_cost_usd", 0) for r in cost_data)
    total_input = sum(r.get("tokens_input", 0) for r in cost_data)
    total_output = sum(r.get("tokens_output", 0) for r in cost_data)

    wf_costs: dict[str, float] = {}
    for r in cost_data:
        wf = r.get("workflow", "unknown")
        wf_costs[wf] = wf_costs.get(wf, 0) + r.get("estimated_cost_usd", 0)

    model_costs: dict[str, float] = {}
    for r in cost_data:
        m = r.get("model", "unknown")
        model_costs[m] = model_costs.get(m, 0) + r.get("estimated_cost_usd", 0)

    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    cost_30d = sum(r.get("estimated_cost_usd", 0) for r in cost_data if (r.get("created_at") or "") >= thirty_days_ago)

    # Recent LLM calls (last 20)
    try:
        recent_cost_resp = (
            client.table("llm_usage_log")
            .select("workflow, chain, model, tokens_input, tokens_output, estimated_cost_usd, duration_ms, created_at")
            .eq("user_id", uid)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        recent_llm = recent_cost_resp.data or []
    except Exception:
        recent_llm = []

    return AdminUserDetail(
        profile=profile,
        projects=user_projects,
        total_signals_submitted=len(all_signals),
        signals_by_type=signals_by_type,
        total_entities_generated=total_entities,
        icp_scores=icp_scores,
        recent_signals=recent_signals,
        enriched_profile=enriched,
        total_cost_usd=round(total_cost, 4),
        total_tokens_input=total_input,
        total_tokens_output=total_output,
        cost_by_workflow={k: round(v, 4) for k, v in sorted(wf_costs.items(), key=lambda x: -x[1])},
        cost_by_model={k: round(v, 4) for k, v in sorted(model_costs.items(), key=lambda x: -x[1])},
        cost_30d_usd=round(cost_30d, 4),
        recent_llm_calls=recent_llm,
    )


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: UUID,
    body: RoleUpdateRequest,
    auth: AuthContext = Depends(require_super_admin),
):
    """Update a user's platform role."""
    valid_roles = ["consultant", "sales_consultant", "solution_architect", "super_admin"]
    if body.platform_role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")

    client = get_supabase()
    resp = (
        client.table("profiles")
        .update({"platform_role": body.platform_role})
        .eq("id", str(user_id))
        .execute()
    )

    if not resp.data:
        raise HTTPException(status_code=404, detail="User not found")

    return {"status": "ok", "user_id": str(user_id), "platform_role": body.platform_role}


# =============================================================================
# Projects
# =============================================================================


@router.get("/projects", response_model=list[AdminProjectSummary])
async def list_projects(
    search: str | None = Query(None),
    stage: str | None = Query(None),
    auth: AuthContext = Depends(require_super_admin),
):
    """List all projects with owner attribution."""
    client = get_supabase()

    query = client.table("projects").select(
        "id, name, stage, status, created_by, client_id, client_name, cached_readiness_score, created_at"
    )
    if stage:
        query = query.eq("stage", stage)
    projects_resp = query.order("created_at", desc=True).execute()
    projects = projects_resp.data or []

    if search:
        search_lower = search.lower()
        projects = [p for p in projects if search_lower in (p.get("name") or "").lower()]

    # Resolve owners
    owner_ids = list(set(p.get("created_by") for p in projects if p.get("created_by")))
    owners: dict[str, dict] = {}
    if owner_ids:
        owners_resp = client.table("profiles").select("id, first_name, last_name, photo_url").in_("id", owner_ids).execute()
        for o in (owners_resp.data or []):
            owners[o["id"]] = o

    # Resolve client names from clients table for projects that have client_id
    client_ids = list(set(p.get("client_id") for p in projects if p.get("client_id")))
    clients_map: dict[str, str] = {}
    if client_ids:
        clients_resp = client.table("clients").select("id, name").in_("id", client_ids).execute()
        for c in (clients_resp.data or []):
            clients_map[c["id"]] = c.get("name", "")

    # Get signal/feature counts per project
    signals_resp = client.table("signals").select("id, project_id").execute()
    signal_counts: dict[str, int] = {}
    for s in (signals_resp.data or []):
        pid = s.get("project_id")
        if pid:
            signal_counts[pid] = signal_counts.get(pid, 0) + 1

    features_resp = client.table("features").select("id, project_id").execute()
    feature_counts: dict[str, int] = {}
    for f in (features_resp.data or []):
        pid = f.get("project_id")
        if pid:
            feature_counts[pid] = feature_counts.get(pid, 0) + 1

    result = []
    for p in projects:
        owner = owners.get(p.get("created_by", ""), {})
        owner_name = None
        if owner.get("first_name") or owner.get("last_name"):
            owner_name = f"{owner.get('first_name', '') or ''} {owner.get('last_name', '') or ''}".strip()

        # Use client_name from project first, then from clients table
        client_name = p.get("client_name") or clients_map.get(p.get("client_id", ""))

        result.append(AdminProjectSummary(
            id=p["id"],
            name=p.get("name", ""),
            stage=p.get("stage"),
            status=p.get("status"),
            client_name=client_name,
            owner_id=p.get("created_by"),
            owner_name=owner_name,
            owner_photo_url=owner.get("photo_url"),
            signal_count=signal_counts.get(p["id"], 0),
            feature_count=feature_counts.get(p["id"], 0),
            readiness_score=p.get("cached_readiness_score"),
            created_at=p.get("created_at", ""),
        ))

    return result


# =============================================================================
# Cost Analytics
# =============================================================================


@router.get("/cost", response_model=AdminCostAnalytics)
async def get_cost_analytics(
    auth: AuthContext = Depends(require_super_admin),
):
    """Get comprehensive cost analytics."""
    client = get_supabase()

    try:
        usage_resp = (
            client.table("llm_usage_log")
            .select("user_id, workflow, model, provider, estimated_cost_usd, tokens_input, tokens_output, created_at")
            .order("created_at", desc=True)
            .execute()
        )
        data = usage_resp.data or []
    except Exception:
        data = []

    total_cost = sum(r.get("estimated_cost_usd", 0) for r in data)
    total_input = sum(r.get("tokens_input", 0) for r in data)
    total_output = sum(r.get("tokens_output", 0) for r in data)
    total_calls = len(data)

    # Cost by workflow
    wf_agg: dict[str, dict] = {}
    for r in data:
        wf = r.get("workflow", "unknown")
        if wf not in wf_agg:
            wf_agg[wf] = {"workflow": wf, "cost": 0, "calls": 0, "tokens": 0}
        wf_agg[wf]["cost"] += r.get("estimated_cost_usd", 0)
        wf_agg[wf]["calls"] += 1
        wf_agg[wf]["tokens"] += r.get("tokens_input", 0) + r.get("tokens_output", 0)
    cost_by_workflow = sorted(wf_agg.values(), key=lambda x: -x["cost"])
    for item in cost_by_workflow:
        item["cost"] = round(item["cost"], 4)

    # Cost by model
    model_agg: dict[str, dict] = {}
    for r in data:
        m = r.get("model", "unknown")
        if m not in model_agg:
            model_agg[m] = {"model": m, "provider": r.get("provider", "unknown"), "cost": 0, "calls": 0, "tokens": 0}
        model_agg[m]["cost"] += r.get("estimated_cost_usd", 0)
        model_agg[m]["calls"] += 1
        model_agg[m]["tokens"] += r.get("tokens_input", 0) + r.get("tokens_output", 0)
    cost_by_model = sorted(model_agg.values(), key=lambda x: -x["cost"])
    for item in cost_by_model:
        item["cost"] = round(item["cost"], 4)

    # Cost by user (top 20)
    user_agg: dict[str, dict] = {}
    for r in data:
        uid = r.get("user_id") or "system"
        if uid not in user_agg:
            user_agg[uid] = {"user_id": uid, "cost": 0, "calls": 0}
        user_agg[uid]["cost"] += r.get("estimated_cost_usd", 0)
        user_agg[uid]["calls"] += 1

    # Resolve user names
    user_ids = [uid for uid in user_agg.keys() if uid != "system"]
    user_names: dict[str, dict] = {}
    if user_ids:
        names_resp = client.table("profiles").select("id, first_name, last_name, email").in_("id", user_ids).execute()
        for u in (names_resp.data or []):
            name = f"{u.get('first_name', '') or ''} {u.get('last_name', '') or ''}".strip() or u.get("email", "")
            user_names[u["id"]] = {"name": name, "email": u.get("email", "")}

    cost_by_user = sorted(user_agg.values(), key=lambda x: -x["cost"])[:20]
    for item in cost_by_user:
        item["cost"] = round(item["cost"], 4)
        info = user_names.get(item["user_id"], {})
        item["name"] = info.get("name", "System")
        item["email"] = info.get("email", "")

    # Daily cost (last 30 days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    daily_agg: dict[str, dict] = {}
    for r in data:
        created = r.get("created_at", "")
        if created and created >= thirty_days_ago.isoformat():
            day = created[:10]
            if day not in daily_agg:
                daily_agg[day] = {"date": day, "cost": 0, "calls": 0}
            daily_agg[day]["cost"] += r.get("estimated_cost_usd", 0)
            daily_agg[day]["calls"] += 1

    daily_cost = sorted(daily_agg.values(), key=lambda x: x["date"])
    for item in daily_cost:
        item["cost"] = round(item["cost"], 4)

    return AdminCostAnalytics(
        total_cost_usd=round(total_cost, 2),
        total_tokens_input=total_input,
        total_tokens_output=total_output,
        total_calls=total_calls,
        cost_by_workflow=cost_by_workflow,
        cost_by_model=cost_by_model,
        cost_by_user=cost_by_user,
        daily_cost=daily_cost,
    )


# =============================================================================
# ICP Leaderboard
# =============================================================================


@router.get("/icp/leaderboard")
async def get_icp_leaderboard(
    profile_id: UUID = Query(...),
    auth: AuthContext = Depends(require_super_admin),
):
    """Get ICP leaderboard for a specific profile."""
    client = get_supabase()

    resp = (
        client.table("icp_consultant_scores")
        .select("user_id, score, signal_count, computed_at, profiles(first_name, last_name, email, photo_url)")
        .eq("icp_profile_id", str(profile_id))
        .order("score", desc=True)
        .execute()
    )

    result = []
    for i, row in enumerate(resp.data or []):
        profile_data = row.get("profiles") or {}
        name = f"{profile_data.get('first_name', '') or ''} {profile_data.get('last_name', '') or ''}".strip()
        result.append({
            "rank": i + 1,
            "user_id": row.get("user_id"),
            "name": name or profile_data.get("email", "Unknown"),
            "email": profile_data.get("email", ""),
            "photo_url": profile_data.get("photo_url"),
            "score": row.get("score", 0),
            "signal_count": row.get("signal_count", 0),
            "computed_at": row.get("computed_at"),
        })

    return result


@router.get("/users/{user_id}/icp-signals")
async def get_user_icp_signals(
    user_id: UUID,
    auth: AuthContext = Depends(require_super_admin),
):
    """Get all ICP signals for a specific user."""
    client = get_supabase()

    resp = (
        client.table("icp_signals")
        .select("*")
        .eq("user_id", str(user_id))
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )

    return resp.data or []


# =============================================================================
# Pulse Engine Admin
# =============================================================================


class AdminPulseConfigSummary(BaseModel):
    id: str
    project_id: str | None = None
    version: str = "1.0"
    label: str = ""
    is_active: bool = False
    created_at: str = ""


class AdminProjectPulse(BaseModel):
    project_id: str
    project_name: str = ""
    stage: str = "discovery"
    stage_progress: float = 0.0
    health_scores: dict[str, float] = {}
    risk_score: float = 0.0
    top_action: str | None = None
    snapshot_count: int = 0
    last_snapshot_at: str | None = None


@router.get("/pulse/configs", response_model=list[AdminPulseConfigSummary])
async def list_pulse_configs(
    auth: AuthContext = Depends(require_super_admin),
) -> list[AdminPulseConfigSummary]:
    """List all pulse configs (global + per-project)."""
    from app.db.pulse import list_pulse_configs as db_list_configs

    configs = db_list_configs()
    return [
        AdminPulseConfigSummary(
            id=c["id"],
            project_id=c.get("project_id"),
            version=c.get("version", "1.0"),
            label=c.get("label", ""),
            is_active=c.get("is_active", False),
            created_at=c.get("created_at", ""),
        )
        for c in configs
    ]


@router.get("/pulse/projects", response_model=list[AdminProjectPulse])
async def list_project_pulses(
    auth: AuthContext = Depends(require_super_admin),
) -> list[AdminProjectPulse]:
    """Get latest pulse snapshot for all active projects (heatmap data)."""
    client = get_supabase()

    # Get all active projects
    projects_resp = (
        client.table("projects")
        .select("id, name, stage, status")
        .neq("status", "archived")
        .order("updated_at", desc=True)
        .execute()
    )
    projects = projects_resp.data or []

    results: list[AdminProjectPulse] = []
    for proj in projects:
        pid = proj["id"]

        # Get latest snapshot
        snap_resp = (
            client.table("pulse_snapshots")
            .select("stage, stage_progress, health, risks, actions, created_at")
            .eq("project_id", pid)
            .order("created_at", desc=True)
            .limit(1)
            .maybe_single()
            .execute()
        )

        # Get snapshot count
        count_resp = (
            client.table("pulse_snapshots")
            .select("id", count="exact")
            .eq("project_id", pid)
            .execute()
        )
        snap_count = count_resp.count if count_resp.count is not None else len(count_resp.data or [])

        snap = snap_resp.data
        if snap:
            health = snap.get("health", {})
            health_scores = {
                et: h.get("health_score", 0) for et, h in health.items()
            } if isinstance(health, dict) else {}

            risks = snap.get("risks", {})
            risk_score = risks.get("risk_score", 0) if isinstance(risks, dict) else 0

            actions = snap.get("actions", [])
            top_action = actions[0].get("sentence") if actions else None

            results.append(AdminProjectPulse(
                project_id=pid,
                project_name=proj.get("name", ""),
                stage=snap.get("stage", proj.get("stage", "discovery")),
                stage_progress=snap.get("stage_progress", 0),
                health_scores=health_scores,
                risk_score=risk_score,
                top_action=top_action,
                snapshot_count=snap_count,
                last_snapshot_at=snap.get("created_at"),
            ))
        else:
            results.append(AdminProjectPulse(
                project_id=pid,
                project_name=proj.get("name", ""),
                stage=proj.get("stage", "discovery"),
                snapshot_count=0,
            ))

    return results


@router.get("/pulse/projects/{project_id}")
async def get_project_pulse_detail(
    project_id: UUID,
    auth: AuthContext = Depends(require_super_admin),
):
    """Full latest snapshot + history for one project."""
    from app.db.pulse import get_latest_pulse_snapshot, list_pulse_snapshots

    client = get_supabase()

    # Get project name
    proj_resp = (
        client.table("projects")
        .select("name")
        .eq("id", str(project_id))
        .maybe_single()
        .execute()
    )
    project_name = proj_resp.data.get("name", "") if proj_resp.data else ""

    latest = get_latest_pulse_snapshot(project_id)
    history = list_pulse_snapshots(project_id, limit=20)

    return {
        "project_name": project_name,
        "latest": latest,
        "history": history,
    }
