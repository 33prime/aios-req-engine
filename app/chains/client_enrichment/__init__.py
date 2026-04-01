"""Client enrichment — deterministic routing + PydanticAI chains.

Replaces the old Client Intelligence Agent (OBSERVE→THINK→DECIDE→ACT LLM loop)
with a simple deterministic router that picks the thinnest section and runs
the appropriate PydanticAI chain directly. Same outcome, one fewer LLM call.

Usage:
    from app.chains.client_enrichment import analyze_client
    result = await analyze_client(client_id)
"""

from uuid import UUID

from app.chains.client_enrichment.context import load_client_context
from app.chains.client_enrichment.models import AnalyzeResult
from app.chains.client_enrichment.scoring import (
    compute_section_scores,
    compute_total_score,
    find_thinnest_section,
    update_completeness,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


# Map section names → chain functions
SECTION_CHAINS = {
    "firmographics": "_run_firmographics",
    "stakeholder_map": "_run_stakeholders",
    "organizational_context": "_run_intelligence",
    "constraints": "_run_constraints",
    "vision_strategy": "_run_intelligence",
    "competitive_context": "_run_firmographics",  # competitors come from enrichment
    "data_landscape": None,  # no dedicated chain — skip
    "portfolio_health": None,  # deterministic — no LLM needed
}


async def analyze_client(
    client_id: UUID, recently_analyzed: set[str] | None = None
) -> AnalyzeResult:
    """Analyze a client by enriching the thinnest profile section.

    This is the main entry point that replaces invoke_client_intelligence_agent().

    Args:
        client_id: The client to analyze.
        recently_analyzed: Section names to skip (already enriched this session).
    """
    try:
        # 1. Score current state
        sections = compute_section_scores(client_id)
        before_total, _ = compute_total_score(sections)

        # 2. Find thinnest section (skipping recently analyzed)
        thinnest = find_thinnest_section(sections, skip=recently_analyzed)
        logger.info(f"Analyzing client {client_id}: thinnest section = {thinnest}")

        # 3. Run the appropriate chain
        chain_name = SECTION_CHAINS.get(thinnest)

        if chain_name is None:
            # Section has no LLM chain — just update completeness
            after_total, _ = update_completeness(client_id)
            return AnalyzeResult(
                section_analyzed=thinnest,
                profile_completeness_before=before_total,
                profile_completeness_after=after_total,
                summary=f"Section '{thinnest}' doesn't require AI analysis — updated scores.",
            )

        # Load shared context once
        ctx = await load_client_context(client_id)

        summary = await _dispatch_chain(chain_name, ctx)

        # 4. Recompute completeness
        after_total, label = update_completeness(client_id)

        logger.info(
            f"Client analysis complete: {thinnest}, "
            f"completeness {before_total}→{after_total} ({label})"
        )

        return AnalyzeResult(
            section_analyzed=thinnest,
            profile_completeness_before=before_total,
            profile_completeness_after=after_total,
            summary=summary,
        )

    except Exception as e:
        logger.error(f"Client analysis failed for {client_id}: {e}", exc_info=True)
        return AnalyzeResult(
            success=False,
            section_analyzed="unknown",
            profile_completeness_before=0,
            profile_completeness_after=0,
            error=str(e),
        )


async def _dispatch_chain(chain_name: str, ctx) -> str:
    """Dispatch to the appropriate chain function. Returns a summary string."""
    if chain_name == "_run_firmographics":
        from app.chains.client_enrichment.firmographics import enrich_firmographics

        result = await enrich_firmographics(ctx.client_id)
        fields = result.get("fields_enriched", [])
        source = result.get("enrichment_source", "ai")
        return f"Enriched {len(fields)} firmographic fields via {source}"

    elif chain_name == "_run_stakeholders":
        from app.chains.client_enrichment.stakeholders import (
            analyze_stakeholder_map,
            identify_role_gaps,
        )

        analysis = await analyze_stakeholder_map(ctx)
        gaps = await identify_role_gaps(ctx)
        parts = [f"Mapped {len(analysis.decision_makers)} decision-makers"]
        if analysis.potential_conflicts:
            parts.append(f"{len(analysis.potential_conflicts)} potential conflicts")
        if gaps.missing_roles:
            parts.append(f"{len(gaps.missing_roles)} role gaps identified")
        return "; ".join(parts)

    elif chain_name == "_run_constraints":
        from app.chains.client_enrichment.constraints import synthesize_constraints

        analysis = await synthesize_constraints(ctx)
        cats = len(analysis.category_summary)
        return f"Synthesized {len(analysis.constraints)} constraints across {cats} categories"

    elif chain_name == "_run_intelligence":
        from app.chains.client_enrichment.intelligence import synthesize_intelligence

        synthesis = await synthesize_intelligence(ctx)
        parts = []
        if synthesis.synthesized_vision:
            parts.append(f"Vision synthesized ({int(synthesis.clarity_score * 100)}% clarity)")
        if synthesis.decision_making_style != "unknown":
            parts.append(f"Org context: {synthesis.decision_making_style} decision-making")
        return "; ".join(parts) or "Intelligence synthesis complete"

    return "Unknown chain"
