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

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
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
    """Build the actual snapshot text from project data (500-750 tokens target).

    All 14 independent queries run in parallel via ThreadPoolExecutor,
    then sections are formatted from the results in-memory.
    """
    pid = str(project_id)

    # Define all independent queries
    def _q(table, select, extra_filters=None, order_col=None, limit=None):
        """Generic query helper — each call gets its own client."""
        try:
            sb = get_supabase()
            q = sb.table(table).select(select).eq("project_id", pid)
            if extra_filters:
                for col, val in extra_filters:
                    q = q.eq(col, val)
            if order_col:
                q = q.order(order_col)
            if limit:
                q = q.limit(limit)
            return q.execute().data or []
        except Exception:
            return []

    def _q_project():
        try:
            sb = get_supabase()
            return sb.table("projects").select("name, description, metadata").eq("id", pid).single().execute().data
        except Exception:
            return None

    def _q_company():
        try:
            sb = get_supabase()
            return sb.table("company_info").select(
                "name, industry, stage, size, location, unique_selling_point, key_differentiators, company_type"
            ).eq("project_id", pid).maybe_single().execute().data
        except Exception:
            return None

    # Fire all 14 queries in parallel
    with ThreadPoolExecutor(max_workers=14) as pool:
        f_project = pool.submit(_q_project)
        f_company = pool.submit(_q_company)
        f_stakeholders = pool.submit(_q, "stakeholders", "name, role, is_economic_buyer, stakeholder_type", None, None, 4)
        f_drivers = pool.submit(_q, "business_drivers", "driver_type, description, measurement, priority, status", None, "priority")
        f_features = pool.submit(_q, "features", "id, is_mvp, name, description, confirmation_status")
        f_personas = pool.submit(_q, "personas", "name, role, goals, frustrations, is_primary, confirmation_status")
        f_vp_steps = pool.submit(_q, "vp_steps", "name, step_order, description, outcome, confirmation_status", None, "step_order")
        f_workflows = pool.submit(_q, "workflows", "id, name, state_type, description", None, "created_at")
        f_data_entities = pool.submit(_q, "data_entities", "id, name, entity_category", None, None, 10)
        f_competitors = pool.submit(_q, "competitor_refs", "name, reference_type, research_notes", None, None, 8)
        f_constraints = pool.submit(_q, "constraints", "name, constraint_type, description", None, None, 6)
        f_proposals = pool.submit(_q, "batch_proposals", "id, proposal_type", [("status", "pending")])
        f_confirmations = pool.submit(_q, "confirmation_items", "id, entity_type", [("status", "open")])
        f_signals = pool.submit(_q, "signals", "id")

    # Collect results
    proj = f_project.result()
    company = f_company.result()
    stakeholders = f_stakeholders.result()
    drivers = f_drivers.result()
    features = f_features.result()
    personas = f_personas.result()
    vp_steps = f_vp_steps.result()
    workflows = f_workflows.result()
    data_entities = f_data_entities.result()
    competitors = f_competitors.result()
    constraints = f_constraints.result()
    proposals = f_proposals.result()
    confirmations = f_confirmations.result()
    signals = f_signals.result()

    # Format sections from pre-loaded data
    sections = []

    identity = _format_identity(proj, company, stakeholders)
    if identity:
        sections.append(identity)

    strategic = _format_strategic(drivers)
    if strategic:
        sections.append(strategic)

    state = _format_state(features, personas, vp_steps, workflows, data_entities)
    if state:
        sections.append(state)

    refs = _format_references(competitors, constraints)
    if refs:
        sections.append(refs)

    # Actions section reuses already-fetched data instead of re-querying
    actions = _format_actions(proposals, confirmations, signals, features, personas, vp_steps, drivers)
    if actions:
        sections.append(actions)

    return "\n\n".join(sections)


def _format_identity(proj: dict | None, company: dict | None, stakeholders: list) -> str:
    """Format identity section from pre-loaded data."""
    lines = ["# PROJECT IDENTITY"]

    if proj:
        lines.append(f"Project: {proj.get('name', 'Unknown')}")
        if proj.get("description"):
            desc = proj["description"][:200].replace("\n", " ").strip()
            lines.append(f"Summary: {desc}...")
        meta = proj.get("metadata") or {}
        if meta.get("industry"):
            lines.append(f"Industry: {meta['industry']}")

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
        if company.get("unique_selling_point"):
            usp = company["unique_selling_point"][:150].replace("\n", " ").strip()
            lines.append(f"Value Proposition: {usp}")
        if company.get("key_differentiators"):
            diffs = company["key_differentiators"]
            if isinstance(diffs, list) and diffs:
                diff_str = ", ".join(str(d)[:30] for d in diffs[:3])
                lines.append(f"Differentiators: {diff_str}")

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

    return "\n".join(lines) if len(lines) > 1 else ""


def _format_strategic(drivers: list) -> str:
    """Format strategic section from pre-loaded drivers."""
    lines = ["# STRATEGIC CONTEXT"]

    if drivers:
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

        confirmed = len([d for d in drivers if d.get("status") == "confirmed"])
        if confirmed > 0:
            lines.append(f"Status: {confirmed}/{len(drivers)} drivers confirmed by client")
        else:
            lines.append("Status: All drivers pending client confirmation")
    else:
        lines.append("Business Drivers: Not yet defined")
        lines.append("  → Run /run-foundation to extract from signals")

    return "\n".join(lines) if len(lines) > 1 else ""


def _format_state(features: list, personas: list, vp_steps: list, workflows: list, data_entities: list) -> str:
    """Format product state section from pre-loaded data."""
    lines = ["# PRODUCT STATE"]
    has_any_content = False

    if features:
        has_any_content = True
        mvp_features = [f for f in features if f.get("is_mvp")]
        other_features = [f for f in features if not f.get("is_mvp")]
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

    if personas:
        has_any_content = True
        primary = [p for p in personas if p.get("is_primary")]
        confirmed = len([p for p in personas if p.get("confirmation_status") in ("confirmed_client", "confirmed_consultant")])
        draft = len([p for p in personas if p.get("confirmation_status") == "ai_generated"])
        lines.append(f"Target Users ({len(personas)} personas, {confirmed} confirmed, {draft} draft):")
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
            if p.get("goals"):
                goals_str = p["goals"][:80] if isinstance(p["goals"], str) else str(p["goals"])[:80]
                lines.append(f"    Goal: {goals_str}")
            if p.get("frustrations"):
                frust_str = p["frustrations"][:80] if isinstance(p["frustrations"], str) else str(p["frustrations"])[:80]
                lines.append(f"    Pain: {frust_str}")
    else:
        lines.append("Personas: Not yet defined")
        lines.append("  → Add signals or run enrichment to generate personas")

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

    if workflows:
        has_any_content = True
        lines.append(f"Workflows ({len(workflows)} total):")
        for w in workflows[:6]:
            lines.append(f"  [{w.get('state_type', 'future')}] {w.get('name', 'Untitled')}")

    if data_entities:
        has_any_content = True
        lines.append(f"Data Entities ({len(data_entities)} total):")
        for de in data_entities[:5]:
            lines.append(f"  {de.get('name', 'Untitled')} [{de.get('entity_category', 'domain')}]")

    if not has_any_content:
        lines.append("")
        lines.append("Product definition is in early stage.")
        lines.append("Next steps: Add signals, run /run-foundation, then /enrich-features")

    return "\n".join(lines) if len(lines) > 1 else ""


def _format_references(competitors: list, constraints: list) -> str:
    """Format references section from pre-loaded data."""
    lines = ["# MARKET CONTEXT"]
    has_content = False

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

    if constraints:
        has_content = True
        lines.append(f"Constraints ({len(constraints)}):")
        tech = [c for c in constraints if c.get("constraint_type") == "technical"]
        compliance = [c for c in constraints if c.get("constraint_type") == "compliance"]
        business = [c for c in constraints if c.get("constraint_type") == "business"]
        other = [c for c in constraints if c.get("constraint_type") not in ("technical", "compliance", "business")]
        for c in (tech + compliance + business + other)[:4]:
            name = c.get("name", "?")[:50]
            ctype = c.get("constraint_type", "")
            type_tag = f" [{ctype}]" if ctype else ""
            lines.append(f"  • {name}{type_tag}")

    if not has_content:
        lines.append("No competitors or constraints defined yet")
        lines.append("  → Add during strategic foundation or enrichment")

    return "\n".join(lines) if len(lines) > 1 else ""


def _format_actions(proposals: list, confirmations: list, signals: list,
                    features: list, personas: list, vp_steps: list, drivers: list) -> str:
    """Format actions section from pre-loaded data (no re-queries needed)."""
    lines = ["# STATUS & NEXT ACTIONS"]

    pending_items = []
    completed_items = []

    if proposals:
        pending_items.append(f"{len(proposals)} proposals awaiting review")
    if confirmations:
        pending_items.append(f"{len(confirmations)} items need client confirmation")
    if signals:
        completed_items.append(f"{len(signals)} signals processed")

    if pending_items:
        lines.append("Pending:")
        for item in pending_items:
            lines.append(f"  • {item}")
    if completed_items:
        lines.append("Completed:")
        for item in completed_items:
            lines.append(f"  • {item}")

    # Suggest next steps — reuse already-fetched result sets (no extra queries)
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
