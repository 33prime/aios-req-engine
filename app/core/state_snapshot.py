"""State snapshot system for providing consistent context to agents.

The state snapshot is a ~500 token cached context that gets injected into
every agent call. This provides optimal context without noise.

Structure:
- Identity & Purpose: ~100 tokens
- Current State: ~150 tokens
- References & Constraints: ~100 tokens
- Next Actions: ~50 tokens
- Recent Activity: ~100 tokens
"""

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from dateutil import parser as dateutil_parser

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

# Cache TTL - regenerate if older than this
SNAPSHOT_CACHE_TTL_MINUTES = 5


def get_state_snapshot(project_id: UUID, force_refresh: bool = False) -> str:
    """
    Get the cached state snapshot for a project.

    If the snapshot is stale or doesn't exist, regenerates it.

    Args:
        project_id: Project UUID
        force_refresh: If True, always regenerate

    Returns:
        State snapshot text (~500 tokens)
    """
    supabase = get_supabase()

    if not force_refresh:
        # Try to get cached snapshot
        try:
            response = (
                supabase.table("state_snapshots")
                .select("snapshot_text, generated_at")
                .eq("project_id", str(project_id))
                .single()
                .execute()
            )

            if response.data:
                generated_at = response.data.get("generated_at")
                if generated_at:
                    # Check if still fresh
                    gen_time = dateutil_parser.isoparse(generated_at)
                    if datetime.now(gen_time.tzinfo) - gen_time < timedelta(minutes=SNAPSHOT_CACHE_TTL_MINUTES):
                        logger.debug(f"Using cached snapshot for project {project_id}")
                        return response.data["snapshot_text"]

        except Exception as e:
            logger.debug(f"No cached snapshot found: {e}")

    # Generate new snapshot
    return regenerate_state_snapshot(project_id)


def regenerate_state_snapshot(project_id: UUID) -> str:
    """
    Generate and cache a new state snapshot for a project.

    Call this when any entity changes to keep the snapshot fresh.

    Args:
        project_id: Project UUID

    Returns:
        Generated snapshot text
    """
    supabase = get_supabase()

    try:
        snapshot_text = _build_snapshot_text(project_id)
        token_count = _estimate_tokens(snapshot_text)

        # Upsert snapshot
        supabase.table("state_snapshots").upsert(
            {
                "project_id": str(project_id),
                "snapshot_text": snapshot_text,
                "token_count": token_count,
                "generated_at": datetime.utcnow().isoformat(),
                "last_entity_change_at": datetime.utcnow().isoformat(),
                "version": 1,
            },
            on_conflict="project_id",
        ).execute()

        logger.info(f"Regenerated state snapshot for project {project_id} ({token_count} tokens)")
        return snapshot_text

    except Exception as e:
        logger.error(f"Failed to regenerate state snapshot: {e}")
        # Return a minimal snapshot on error
        return f"# Project {project_id}\nSnapshot generation failed. Operating with minimal context."


def _build_snapshot_text(project_id: UUID) -> str:
    """Build the actual snapshot text from project data."""
    supabase = get_supabase()
    sections = []

    # 1. Identity & Purpose (~100 tokens)
    identity = _build_identity_section(supabase, project_id)
    if identity:
        sections.append(identity)

    # 2. Current State (~150 tokens)
    state = _build_state_section(supabase, project_id)
    if state:
        sections.append(state)

    # 3. References & Constraints (~100 tokens)
    refs = _build_references_section(supabase, project_id)
    if refs:
        sections.append(refs)

    # 4. Next Actions (~50 tokens)
    actions = _build_actions_section(supabase, project_id)
    if actions:
        sections.append(actions)

    # 5. Recent Activity (~100 tokens)
    activity = _build_activity_section(supabase, project_id)
    if activity:
        sections.append(activity)

    return "\n\n".join(sections)


def _build_identity_section(supabase, project_id: UUID) -> str:
    """Build project identity section."""
    lines = ["# PROJECT IDENTITY"]

    # Get project info
    try:
        proj = (
            supabase.table("projects")
            .select("name, description, metadata")
            .eq("id", str(project_id))
            .single()
            .execute()
        ).data
        if proj:
            lines.append(f"Project: {proj.get('name', 'Unknown')}")
            if proj.get("description"):
                lines.append(f"Description: {proj['description'][:150]}...")
            meta = proj.get("metadata") or {}
            if meta.get("industry"):
                lines.append(f"Industry: {meta['industry']}")
    except Exception as e:
        logger.debug(f"Failed to get project info: {e}")

    # Get company info
    try:
        company = (
            supabase.table("company_info")
            .select("name, industry, stage, size")
            .eq("project_id", str(project_id))
            .maybe_single()
            .execute()
        ).data
        if company:
            company_str = company.get("name", "")
            if company.get("industry"):
                company_str += f" ({company['industry']}"
                if company.get("stage"):
                    company_str += f", {company['stage']}"
                company_str += ")"
            lines.append(f"Company: {company_str}")
    except Exception:
        pass  # Table might not exist yet

    # Get primary stakeholder
    try:
        stakeholders = (
            supabase.table("stakeholders")
            .select("name, role, is_economic_buyer")
            .eq("project_id", str(project_id))
            .limit(2)
            .execute()
        ).data
        if stakeholders:
            for s in stakeholders:
                role = "Decision Maker" if s.get("is_economic_buyer") else s.get("role", "Stakeholder")
                lines.append(f"{role}: {s.get('name', 'Unknown')}")
    except Exception:
        pass

    return "\n".join(lines) if len(lines) > 1 else ""


def _build_state_section(supabase, project_id: UUID) -> str:
    """Build current state section."""
    lines = ["# CURRENT STATE"]

    # Get counts
    try:
        features = supabase.table("features").select("id, is_mvp, name").eq("project_id", str(project_id)).execute().data or []
        mvp_features = [f for f in features if f.get("is_mvp")]
        non_mvp = [f for f in features if not f.get("is_mvp")]

        lines.append(f"Features: {len(features)} total, {len(mvp_features)} MVP")
        if mvp_features:
            mvp_names = [f.get("name", "?")[:30] for f in mvp_features[:5]]
            lines.append(f"  MVP: {', '.join(mvp_names)}")
        if non_mvp:
            other_names = [f.get("name", "?")[:30] for f in non_mvp[:3]]
            lines.append(f"  Other: {', '.join(other_names)}")
    except Exception:
        pass

    try:
        personas = supabase.table("personas").select("name, role").eq("project_id", str(project_id)).execute().data or []
        if personas:
            persona_strs = [f"{p.get('name', '?')} ({p.get('role', '?')})" for p in personas[:4]]
            lines.append(f"Personas: {', '.join(persona_strs)}")
    except Exception:
        pass

    try:
        vp_steps = supabase.table("vp_steps").select("id, step_order").eq("project_id", str(project_id)).execute().data or []
        lines.append(f"Value Path: {len(vp_steps)} stages")
    except Exception:
        pass

    # Get business drivers
    try:
        drivers = (
            supabase.table("business_drivers")
            .select("driver_type, description, measurement")
            .eq("project_id", str(project_id))
            .order("priority")
            .limit(3)
            .execute()
        ).data or []
        if drivers:
            lines.append("Business Drivers:")
            for d in drivers:
                dtype = d.get("driver_type", "?").upper()
                desc = d.get("description", "")[:60]
                if d.get("measurement"):
                    desc += f" (target: {d['measurement'][:30]})"
                lines.append(f"  {dtype}: {desc}")
    except Exception:
        pass  # Table might not exist yet

    return "\n".join(lines) if len(lines) > 1 else ""


def _build_references_section(supabase, project_id: UUID) -> str:
    """Build references and constraints section."""
    lines = ["# REFERENCES & CONSTRAINTS"]

    # Get competitors
    try:
        competitors = (
            supabase.table("competitor_references")
            .select("name, reference_type")
            .eq("project_id", str(project_id))
            .limit(5)
            .execute()
        ).data or []
        if competitors:
            comp_names = [c.get("name") for c in competitors if c.get("reference_type") == "competitor"]
            design_refs = [c.get("name") for c in competitors if c.get("reference_type") == "design_inspiration"]
            if comp_names:
                lines.append(f"Competitors: {', '.join(comp_names[:3])}")
            if design_refs:
                lines.append(f"Design Inspiration: {', '.join(design_refs[:3])}")
    except Exception:
        pass  # Table might not exist yet

    # Get constraints
    try:
        constraints = (
            supabase.table("constraints")
            .select("name, constraint_type")
            .eq("project_id", str(project_id))
            .limit(5)
            .execute()
        ).data or []
        if constraints:
            constraint_strs = [c.get("name", "?")[:40] for c in constraints[:3]]
            lines.append(f"Constraints: {', '.join(constraint_strs)}")
    except Exception:
        pass

    return "\n".join(lines) if len(lines) > 1 else ""


def _build_actions_section(supabase, project_id: UUID) -> str:
    """Build next actions section."""
    lines = ["# NEXT ACTIONS"]

    # Get pending proposals
    try:
        proposals = (
            supabase.table("batch_proposals")
            .select("id")
            .eq("project_id", str(project_id))
            .eq("status", "pending")
            .execute()
        ).data or []
        if proposals:
            lines.append(f"Pending Proposals: {len(proposals)}")
    except Exception:
        pass

    # Get open confirmations
    try:
        confirmations = (
            supabase.table("confirmation_items")
            .select("id")
            .eq("project_id", str(project_id))
            .eq("status", "open")
            .execute()
        ).data or []
        if confirmations:
            lines.append(f"Open Confirmations: {len(confirmations)}")
    except Exception:
        pass

    return "\n".join(lines) if len(lines) > 1 else ""


def _build_activity_section(supabase, project_id: UUID) -> str:
    """Build recent activity section."""
    lines = ["# RECENT ACTIVITY"]

    try:
        revisions = (
            supabase.table("revisions")
            .select("entity_type, entity_id, summary, created_at")
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        ).data or []

        if revisions:
            lines.append("Last 5 changes:")
            for i, rev in enumerate(revisions, 1):
                entity = rev.get("entity_type", "?")
                summary = rev.get("summary", "Updated")[:50]
                lines.append(f"{i}. [{entity}] {summary}")
    except Exception:
        pass

    return "\n".join(lines) if len(lines) > 1 else ""


def _estimate_tokens(text: str) -> int:
    """Rough token estimate (4 chars = 1 token)."""
    return len(text) // 4


def invalidate_snapshot(project_id: UUID) -> None:
    """
    Mark a snapshot as needing regeneration.

    Call this when any entity changes. The next get_state_snapshot call
    will regenerate it.
    """
    supabase = get_supabase()
    try:
        # Delete the cached snapshot so it regenerates on next access
        supabase.table("state_snapshots").delete().eq("project_id", str(project_id)).execute()
        logger.debug(f"Invalidated snapshot for project {project_id}")
    except Exception as e:
        logger.debug(f"Failed to invalidate snapshot: {e}")
