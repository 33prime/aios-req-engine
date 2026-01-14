"""Context preparation for Research Agent."""

from typing import Any
from uuid import UUID

from app.core.embeddings import embed_texts
from app.core.logging import get_logger
from app.db.phase0 import search_signal_chunks
from app.db.state import get_enriched_state

logger = get_logger(__name__)


def identify_research_gaps(
    enriched_state: dict[str, Any],
    seed_context: dict[str, Any],
) -> list[str]:
    """
    Identify what research is needed based on project state.

    Returns:
        List of gap descriptions
    """
    gaps = []

    # Check features without competitive context
    features = enriched_state.get('features', [])
    if len(features) > 0:
        gaps.append(
            f"Have {len(features)} features but no competitive benchmarking data"
        )

    # Check personas
    facts = enriched_state.get('facts', [])
    persona_facts = [f for f in facts if f.get('fact_type') == 'persona']
    if len(persona_facts) < 2:
        gaps.append("Limited persona information - need real user pain points and behaviors")

    # Check VP steps for user benefit/pain
    vp_steps = enriched_state.get('vp_steps', [])
    steps_without_value = [
        step for step in vp_steps
        if not step.get('user_benefit_pain')
    ]
    if steps_without_value:
        gaps.append(
            f"{len(steps_without_value)} VP steps lack user benefit/pain evidence"
        )

    # Check for competitive analysis based on competitors
    competitors = seed_context.get('competitors', [])
    if competitors:
        gaps.append(
            f"Need detailed feature analysis for competitors: {', '.join(competitors)}"
        )

    # Check focus areas
    focus_areas = seed_context.get('focus_areas', [])
    if focus_areas:
        gaps.append(
            f"Need market validation for focus areas: {', '.join(focus_areas)}"
        )

    # Check custom questions
    custom_questions = seed_context.get('custom_questions', [])
    if custom_questions:
        gaps.append(
            f"Need answers to {len(custom_questions)} custom questions from consultant"
        )

    return gaps


def get_research_context(
    project_id: UUID,
    seed_context: dict[str, Any],
) -> dict[str, Any]:
    """
    Gather all context for research agent.

    Returns:
        Dict with enriched_state, gaps, existing_research
    """
    logger.info(f"Gathering research context for project {project_id}")

    # Get current project state
    enriched_state = get_enriched_state(project_id)

    # Identify gaps
    gaps = identify_research_gaps(enriched_state, seed_context)

    logger.info(f"Identified {len(gaps)} research gaps")

    # Get existing research to avoid duplication
    existing_research = []
    if seed_context.get('competitors'):
        query = f"competitive analysis {' '.join(seed_context['competitors'][:3])}"
        try:
            query_embedding = embed_texts([query])[0]
            existing = search_signal_chunks(
                query_embedding=query_embedding,
                match_count=10,
                project_id=project_id,
            )
            existing_research = [
                c for c in existing
                if c.get('signal_metadata', {}).get('authority') == 'research'
            ]
            logger.info(f"Found {len(existing_research)} existing research chunks")
        except Exception as e:
            logger.warning(f"Failed to search existing research: {e}")
            existing_research = []

    return {
        "enriched_state": enriched_state,
        "gaps": gaps,
        "existing_research": existing_research,
    }
