"""Stakeholder enrichment — deterministic routing + PydanticAI chains.

Replaces the old Stakeholder Intelligence Agent (OBSERVE->THINK->DECIDE->ACT
LLM loop) with deterministic routing that picks the thinnest section
and runs the appropriate PydanticAI chain directly.

Enrichment depth is tiered by stakeholder type:
- champion/sponsor: full (up to 4 iterations)
- blocker: decision-focused (up to 3)
- influencer: moderate (up to 2)
- end_user: minimal (1 iteration)

Usage:
    from app.chains.stakeholder_enrichment import analyze_stakeholder
    result = await analyze_stakeholder(stakeholder_id, project_id)
"""

from uuid import UUID

from app.chains.stakeholder_enrichment.context import (
    load_stakeholder_context,
)
from app.chains.stakeholder_enrichment.models import (
    AnalyzeStakeholderResult,
)
from app.chains.stakeholder_enrichment.scoring import (
    compute_section_scores,
    compute_total_score,
    find_thinnest_section,
    update_completeness,
)
from app.chains.stakeholder_enrichment.scoring import (
    get_max_iterations as get_max_iterations,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

# Section → chain function name
SECTION_CHAINS: dict[str, str | None] = {
    "core_identity": "_run_external",
    "engagement_profile": "_run_engagement",
    "decision_authority": "_run_decisions",
    "relationships": "_run_relationships",
    "communication": "_run_communication",
    "win_conditions_concerns": "_run_win_conditions",
    "evidence_depth": None,  # no chain — comes from signals
}


async def analyze_stakeholder(
    stakeholder_id: UUID,
    project_id: UUID,
    trigger: str = "user_request",
    trigger_context: str | None = None,
    specific_request: str | None = None,
    focus_areas: list[str] | None = None,
) -> AnalyzeStakeholderResult:
    """Analyze a stakeholder by enriching the thinnest section.

    Drop-in replacement for invoke_stakeholder_intelligence_agent().
    Returns AnalyzeStakeholderResult which has action_type for compat.
    """
    try:
        # 1. Score current state
        sections = compute_section_scores(stakeholder_id)
        before_total, _ = compute_total_score(sections)

        # 2. Load context
        ctx = load_stakeholder_context(stakeholder_id, project_id)
        sh_type = ctx.stakeholder_type

        # 3. Find thinnest section (filtered by tier)
        thinnest = find_thinnest_section(sections, sh_type)
        chain_name = SECTION_CHAINS.get(thinnest)

        logger.info(
            f"Analyzing stakeholder {stakeholder_id}: "
            f"type={sh_type}, thinnest={thinnest}",
        )

        if chain_name is None:
            after_total, _ = update_completeness(stakeholder_id)
            return AnalyzeStakeholderResult(
                section_analyzed=thinnest,
                profile_completeness_before=before_total,
                profile_completeness_after=after_total,
                summary=f"Section '{thinnest}' has no enrichment chain.",
                action_type="stop",
            )

        # 4. Run the chain
        changed = await _dispatch_chain(chain_name, ctx)

        # 5. Also try external enrichment if core_identity is thin
        # and we haven't already run it
        if (
            chain_name != "_run_external"
            and sections.get("core_identity", 0) < 8
            and (
                ctx.stakeholder.get("linkedin_profile")
                or ctx.stakeholder.get("email")
            )
        ):
            ext_changed = await _dispatch_chain("_run_external", ctx)
            changed.extend(ext_changed)

        # 6. Try CI cross-reference for key people
        if ctx.is_key_person and trigger == "ci_agent_completed":
            cr_changed = await _dispatch_chain(
                "_run_ci_crossref", ctx,
            )
            changed.extend(cr_changed)

        # 7. Update completeness
        after_total, label = update_completeness(stakeholder_id)

        logger.info(
            f"Stakeholder analysis complete: {thinnest}, "
            f"{before_total}->{after_total} ({label}), "
            f"changed={changed}",
        )

        return AnalyzeStakeholderResult(
            section_analyzed=thinnest,
            profile_completeness_before=before_total,
            profile_completeness_after=after_total,
            fields_updated=changed,
            summary=_build_summary(thinnest, changed),
            action_type="tool_call",
        )

    except Exception as e:
        logger.error(
            f"Stakeholder analysis failed for {stakeholder_id}: {e}",
            exc_info=True,
        )
        return AnalyzeStakeholderResult(
            success=False,
            section_analyzed="unknown",
            profile_completeness_before=0,
            profile_completeness_after=0,
            error=str(e),
            action_type="stop",
        )


async def _dispatch_chain(chain_name: str, ctx) -> list[str]:
    """Run a chain, return list of changed field names."""
    try:
        if chain_name == "_run_external":
            from app.chains.stakeholder_enrichment.external import (
                enrich_from_external,
            )
            return await enrich_from_external(ctx)

        elif chain_name == "_run_engagement":
            from app.chains.stakeholder_enrichment.engagement import (
                enrich_engagement,
            )
            return await enrich_engagement(ctx)

        elif chain_name == "_run_decisions":
            from app.chains.stakeholder_enrichment.decisions import (
                analyze_decision_authority,
            )
            return await analyze_decision_authority(ctx)

        elif chain_name == "_run_relationships":
            from app.chains.stakeholder_enrichment.relationships import (
                infer_relationships,
            )
            return await infer_relationships(ctx)

        elif chain_name == "_run_communication":
            from app.chains.stakeholder_enrichment.communication import (
                detect_communication,
            )
            return await detect_communication(ctx)

        elif chain_name == "_run_win_conditions":
            from app.chains.stakeholder_enrichment.win_conditions import (
                synthesize_win_conditions,
            )
            return await synthesize_win_conditions(ctx)

        elif chain_name == "_run_ci_crossref":
            from app.chains.stakeholder_enrichment.ci_crossref import (
                cross_reference_ci,
            )
            return await cross_reference_ci(ctx)

    except Exception as e:
        logger.error(f"Chain {chain_name} failed: {e}", exc_info=True)

    return []


def _build_summary(section: str, changed: list[str]) -> str:
    label = section.replace("_", " ").title()
    if not changed:
        return f"Analyzed {label} — no new fields"
    return f"Enriched {label}: {', '.join(changed[:5])}"
