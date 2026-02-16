"""State snapshot system for providing consistent context to agents.

The state snapshot is a 500-750 token cached context that gets injected into
every agent call. This provides optimal context without noise.

Structure:
- Identity & Purpose: ~100 tokens
- Strategic Context: ~200 tokens (business drivers, goals, KPIs)
- Product State: ~200 tokens (features, personas, VP)
- References & Constraints: ~100 tokens
- Next Actions: ~50 tokens
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
    """Build the actual snapshot text from project data (500-750 tokens target)."""
    supabase = get_supabase()
    sections = []

    # 1. Identity & Purpose (~100 tokens)
    identity = _build_identity_section(supabase, project_id)
    if identity:
        sections.append(identity)

    # 2. Strategic Context (~200 tokens) - business drivers, goals, KPIs
    strategic = _build_strategic_section(supabase, project_id)
    if strategic:
        sections.append(strategic)

    # 3. Product State (~200 tokens) - features, personas, VP
    state = _build_state_section(supabase, project_id)
    if state:
        sections.append(state)

    # 4. References & Constraints (~100 tokens)
    refs = _build_references_section(supabase, project_id)
    if refs:
        sections.append(refs)

    # 5. Next Actions (~50 tokens)
    actions = _build_actions_section(supabase, project_id)
    if actions:
        sections.append(actions)

    return "\n\n".join(sections)


def _build_identity_section(supabase, project_id: UUID) -> str:
    """Build project identity section (~150 tokens)."""
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
                # Take first 200 chars for a meaningful summary
                desc = proj["description"][:200].replace("\n", " ").strip()
                lines.append(f"Summary: {desc}...")
            meta = proj.get("metadata") or {}
            if meta.get("industry"):
                lines.append(f"Industry: {meta['industry']}")
    except Exception as e:
        logger.debug(f"Failed to get project info: {e}")

    # Get company info with enrichment details
    try:
        company = (
            supabase.table("company_info")
            .select("name, industry, stage, size, location, unique_selling_point, key_differentiators, company_type")
            .eq("project_id", str(project_id))
            .maybe_single()
            .execute()
        ).data
        if company:
            company_str = company.get("name", "")
            details = []
            if company.get("industry"):
                details.append(company["industry"])
            if company.get("stage"):
                details.append(company["stage"])
            if company.get("company_type"):
                details.append(company["company_type"])
            if details:
                company_str += f" ({' • '.join(details)})"
            lines.append(f"Company: {company_str}")

            if company.get("location"):
                lines.append(f"Location: {company['location']}")

            # Add unique selling point if available
            if company.get("unique_selling_point"):
                usp = company["unique_selling_point"][:150].replace("\n", " ").strip()
                lines.append(f"Value Proposition: {usp}")

            # Add key differentiators if available
            if company.get("key_differentiators"):
                diffs = company["key_differentiators"]
                if isinstance(diffs, list) and diffs:
                    diff_str = ", ".join(str(d)[:30] for d in diffs[:3])
                    lines.append(f"Differentiators: {diff_str}")
    except Exception:
        pass  # Table might not exist yet

    # Get stakeholders with more detail
    try:
        stakeholders = (
            supabase.table("stakeholders")
            .select("name, role, is_economic_buyer, stakeholder_type")
            .eq("project_id", str(project_id))
            .limit(4)
            .execute()
        ).data
        if stakeholders:
            lines.append("Key Stakeholders:")
            for s in stakeholders[:3]:
                name = s.get("name", "Unknown")
                role = s.get("role", "")
                stype = s.get("stakeholder_type", "")
                buyer = " [Decision Maker]" if s.get("is_economic_buyer") else ""
                stake_line = f"  • {name}"
                if role:
                    stake_line += f" - {role}"
                if stype:
                    stake_line += f" ({stype})"
                stake_line += buyer
                lines.append(stake_line)
    except Exception:
        pass

    return "\n".join(lines) if len(lines) > 1 else ""


def _build_strategic_section(supabase, project_id: UUID) -> str:
    """Build strategic context section (~200 tokens) - business drivers grouped by type."""
    lines = ["# STRATEGIC CONTEXT"]

    try:
        drivers = (
            supabase.table("business_drivers")
            .select("driver_type, description, measurement, priority, status")
            .eq("project_id", str(project_id))
            .order("priority")
            .execute()
        ).data or []

        if drivers:
            # Group by type
            pains = [d for d in drivers if d.get("driver_type") == "pain"]
            goals = [d for d in drivers if d.get("driver_type") == "goal"]
            kpis = [d for d in drivers if d.get("driver_type") == "kpi"]

            if pains:
                lines.append(f"Pain Points ({len(pains)}):")
                for p in pains[:4]:
                    desc = p.get("description", "?")[:100]
                    status = p.get("status", "")
                    status_tag = " [confirmed]" if status == "confirmed" else ""
                    lines.append(f"  • {desc}{status_tag}")

            if goals:
                lines.append(f"Business Goals ({len(goals)}):")
                for g in goals[:4]:
                    desc = g.get("description", "?")[:100]
                    status = g.get("status", "")
                    status_tag = " [confirmed]" if status == "confirmed" else ""
                    lines.append(f"  • {desc}{status_tag}")

            if kpis:
                lines.append(f"Success Metrics ({len(kpis)}):")
                for k in kpis[:4]:
                    desc = k.get("description", "?")[:80]
                    measurement = k.get("measurement", "")
                    if measurement:
                        desc += f" → Target: {measurement[:50]}"
                    status = k.get("status", "")
                    status_tag = " [confirmed]" if status == "confirmed" else ""
                    lines.append(f"  • {desc}{status_tag}")

            # Summary line
            confirmed = len([d for d in drivers if d.get("status") == "confirmed"])
            if confirmed > 0:
                lines.append(f"Status: {confirmed}/{len(drivers)} drivers confirmed by client")
            else:
                lines.append("Status: All drivers pending client confirmation")
        else:
            lines.append("Business Drivers: Not yet defined")
            lines.append("  → Run /run-foundation to extract from signals")

    except Exception:
        pass  # Table might not exist yet

    return "\n".join(lines) if len(lines) > 1 else ""


def _build_state_section(supabase, project_id: UUID) -> str:
    """Build product state section (~200 tokens) - features, personas, VP."""
    lines = ["# PRODUCT STATE"]
    has_any_content = False

    # Features with more detail
    try:
        features = (
            supabase.table("features")
            .select("id, is_mvp, name, description, confirmation_status")
            .eq("project_id", str(project_id))
            .execute()
        ).data or []

        mvp_features = [f for f in features if f.get("is_mvp")]
        other_features = [f for f in features if not f.get("is_mvp")]

        if features:
            has_any_content = True
            confirmed = len([f for f in features if f.get("confirmation_status") in ("confirmed_client", "confirmed_consultant")])
            draft = len([f for f in features if f.get("confirmation_status") == "ai_generated"])
            lines.append(f"Features ({len(features)} total, {len(mvp_features)} MVP, {confirmed} confirmed, {draft} draft):")
            for f in mvp_features[:5]:
                name = f.get("name", "?")[:50]
                status = f.get("confirmation_status", "ai_generated")
                status_tag = " [confirmed]" if status in ("confirmed_client", "confirmed_consultant") else " [draft]"
                lines.append(f"  [MVP] {name}{status_tag}")
            if other_features:
                other_confirmed = len([f for f in other_features if f.get("confirmation_status") in ("confirmed_client", "confirmed_consultant")])
                lines.append(f"  + {len(other_features)} additional features ({other_confirmed} confirmed)")
        else:
            lines.append("Features: Not yet defined")
            lines.append("  → Add signals or run enrichment to generate features")
    except Exception:
        pass

    # Personas with more detail
    try:
        personas = (
            supabase.table("personas")
            .select("name, role, goals, frustrations, is_primary, confirmation_status")
            .eq("project_id", str(project_id))
            .execute()
        ).data or []

        if personas:
            has_any_content = True
            primary = [p for p in personas if p.get("is_primary")]
            confirmed = len([p for p in personas if p.get("confirmation_status") in ("confirmed_client", "confirmed_consultant")])
            draft = len([p for p in personas if p.get("confirmation_status") == "ai_generated"])
            lines.append(f"Target Users ({len(personas)} personas, {confirmed} confirmed, {draft} draft):")
            # Show primary first
            for p in (primary + [p for p in personas if not p.get("is_primary")])[:4]:
                name = p.get("name", "?")
                role = p.get("role", "")
                is_primary = p.get("is_primary")
                status = p.get("confirmation_status", "ai_generated")
                primary_tag = " [Primary]" if is_primary else ""
                status_tag = " [confirmed]" if status in ("confirmed_client", "confirmed_consultant") else " [draft]"
                persona_line = f"  • {name}"
                if role:
                    persona_line += f" - {role}"
                persona_line += primary_tag + status_tag
                lines.append(persona_line)
                # Add goals if present
                if p.get("goals"):
                    goals_str = p["goals"][:80] if isinstance(p["goals"], str) else str(p["goals"])[:80]
                    lines.append(f"    Goal: {goals_str}")
                # Add frustrations if present
                if p.get("frustrations"):
                    frust_str = p["frustrations"][:80] if isinstance(p["frustrations"], str) else str(p["frustrations"])[:80]
                    lines.append(f"    Pain: {frust_str}")
        else:
            lines.append("Personas: Not yet defined")
            lines.append("  → Add signals or run enrichment to generate personas")
    except Exception:
        pass

    # Value Path with step details
    try:
        vp_steps = (
            supabase.table("vp_steps")
            .select("name, step_order, description, outcome, confirmation_status")
            .eq("project_id", str(project_id))
            .order("step_order")
            .execute()
        ).data or []

        if vp_steps:
            has_any_content = True
            confirmed = len([s for s in vp_steps if s.get("confirmation_status") in ("confirmed_client", "confirmed_consultant")])
            draft = len([s for s in vp_steps if s.get("confirmation_status") == "ai_generated"])
            lines.append(f"Value Path ({len(vp_steps)} stages, {confirmed} confirmed, {draft} draft):")
            for step in vp_steps[:6]:
                order = step.get("step_order", "?")
                name = step.get("name", "Untitled")[:50]
                outcome = step.get("outcome", "")[:40]
                status = step.get("confirmation_status", "ai_generated")
                status_tag = " [confirmed]" if status in ("confirmed_client", "confirmed_consultant") else " [draft]"
                lines.append(f"  {order}. {name}{status_tag}")
                if outcome:
                    lines.append(f"     → {outcome}")
        else:
            lines.append("Value Path: Not yet defined")
            lines.append("  → Run /enrich-vp to generate user journey")
    except Exception:
        pass

    # Workflows
    try:
        workflows = (
            supabase.table("workflows")
            .select("id, name, state_type, description")
            .eq("project_id", str(project_id))
            .order("created_at")
            .execute()
        ).data or []
        if workflows:
            has_any_content = True
            lines.append(f"Workflows ({len(workflows)} total):")
            for w in workflows[:6]:
                lines.append(f"  [{w.get('state_type', 'future')}] {w.get('name', 'Untitled')}")
    except Exception:
        pass

    # Data Entities
    try:
        data_entities = (
            supabase.table("data_entities")
            .select("id, name, entity_category")
            .eq("project_id", str(project_id))
            .limit(10)
            .execute()
        ).data or []
        if data_entities:
            has_any_content = True
            lines.append(f"Data Entities ({len(data_entities)} total):")
            for de in data_entities[:5]:
                lines.append(f"  {de.get('name', 'Untitled')} [{de.get('entity_category', 'domain')}]")
    except Exception:
        pass

    # Add overall status if no content
    if not has_any_content:
        lines.append("")
        lines.append("Product definition is in early stage.")
        lines.append("Next steps: Add signals, run /run-foundation, then /enrich-features")

    return "\n".join(lines) if len(lines) > 1 else ""


def _build_references_section(supabase, project_id: UUID) -> str:
    """Build references and constraints section (~100 tokens)."""
    lines = ["# MARKET CONTEXT"]
    has_content = False

    # Get competitors with research notes
    try:
        competitors = (
            supabase.table("competitor_refs")
            .select("name, reference_type, research_notes")
            .eq("project_id", str(project_id))
            .limit(8)
            .execute()
        ).data or []
        if competitors:
            has_content = True
            comp_list = [c for c in competitors if c.get("reference_type") == "competitor"]
            design_refs = [c for c in competitors if c.get("reference_type") == "design_inspiration"]
            feature_refs = [c for c in competitors if c.get("reference_type") == "feature_inspiration"]

            if comp_list:
                lines.append(f"Competitors ({len(comp_list)}):")
                for c in comp_list[:3]:
                    name = c.get("name", "?")
                    notes = c.get("research_notes", "")[:60]
                    lines.append(f"  • {name}")
                    if notes:
                        lines.append(f"    {notes}...")
            if design_refs:
                names = [c.get("name") for c in design_refs[:3]]
                lines.append(f"Design Inspiration: {', '.join(names)}")
            if feature_refs:
                names = [c.get("name") for c in feature_refs[:3]]
                lines.append(f"Feature Inspiration: {', '.join(names)}")
    except Exception:
        pass  # Table might not exist yet

    # Get constraints with types
    try:
        constraints = (
            supabase.table("constraints")
            .select("name, constraint_type, description")
            .eq("project_id", str(project_id))
            .limit(6)
            .execute()
        ).data or []
        if constraints:
            has_content = True
            lines.append(f"Constraints ({len(constraints)}):")
            # Group by type
            tech = [c for c in constraints if c.get("constraint_type") == "technical"]
            compliance = [c for c in constraints if c.get("constraint_type") == "compliance"]
            business = [c for c in constraints if c.get("constraint_type") == "business"]
            other = [c for c in constraints if c.get("constraint_type") not in ("technical", "compliance", "business")]

            for c in (tech + compliance + business + other)[:4]:
                name = c.get("name", "?")[:50]
                ctype = c.get("constraint_type", "")
                type_tag = f" [{ctype}]" if ctype else ""
                lines.append(f"  • {name}{type_tag}")
    except Exception:
        pass

    if not has_content:
        lines.append("No competitors or constraints defined yet")
        lines.append("  → Add during strategic foundation or enrichment")

    return "\n".join(lines) if len(lines) > 1 else ""


def _build_actions_section(supabase, project_id: UUID) -> str:
    """Build next actions and status section (~100 tokens)."""
    lines = ["# STATUS & NEXT ACTIONS"]

    pending_items = []
    completed_items = []

    # Get pending proposals
    try:
        proposals = (
            supabase.table("batch_proposals")
            .select("id, proposal_type")
            .eq("project_id", str(project_id))
            .eq("status", "pending")
            .execute()
        ).data or []
        if proposals:
            pending_items.append(f"{len(proposals)} proposals awaiting review")
    except Exception:
        pass

    # Get open confirmations
    try:
        confirmations = (
            supabase.table("confirmation_items")
            .select("id, entity_type")
            .eq("project_id", str(project_id))
            .eq("status", "open")
            .execute()
        ).data or []
        if confirmations:
            pending_items.append(f"{len(confirmations)} items need client confirmation")
    except Exception:
        pass

    # Get signals count
    try:
        signals = (
            supabase.table("signals")
            .select("id")
            .eq("project_id", str(project_id))
            .execute()
        ).data or []
        if signals:
            completed_items.append(f"{len(signals)} signals processed")
    except Exception:
        pass

    # Show status
    if pending_items:
        lines.append("Pending:")
        for item in pending_items:
            lines.append(f"  • {item}")

    if completed_items:
        lines.append("Completed:")
        for item in completed_items:
            lines.append(f"  • {item}")

    # Suggest next steps based on what's missing
    try:
        # Check what's defined
        features = supabase.table("features").select("id").eq("project_id", str(project_id)).execute().data or []
        personas = supabase.table("personas").select("id").eq("project_id", str(project_id)).execute().data or []
        vp_steps = supabase.table("vp_steps").select("id").eq("project_id", str(project_id)).execute().data or []
        drivers = supabase.table("business_drivers").select("id").eq("project_id", str(project_id)).execute().data or []

        suggestions = []
        if not drivers:
            suggestions.append("Run /run-foundation to extract business drivers")
        if not features:
            suggestions.append("Run /enrich-features to generate features")
        if not personas:
            suggestions.append("Run /enrich-personas to generate user personas")
        if not vp_steps:
            suggestions.append("Run /enrich-vp to generate value path")

        if suggestions:
            lines.append("Suggested Next Steps:")
            for s in suggestions[:3]:
                lines.append(f"  → {s}")
        elif not pending_items:
            lines.append("Project is well-defined. Ready for client review.")
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
