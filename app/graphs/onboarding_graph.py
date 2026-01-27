"""
Onboarding graph that chains extract_facts → build_state.

Used when a project is created with a description to automatically
analyze the description and build initial project state.
"""

import logging
from uuid import UUID

logger = logging.getLogger(__name__)


def run_onboarding(
    project_id: UUID,
    signal_id: UUID,
    job_id: UUID,
    run_id: UUID,
) -> dict:
    """
    Run full onboarding: extract_facts then build_state.

    This is a convenience wrapper that chains the two agents together
    for the project creation flow.

    Args:
        project_id: The project UUID
        signal_id: The signal UUID (from ingested description)
        job_id: The onboarding job UUID for tracking
        run_id: The run UUID for tracing

    Returns:
        dict with counts of entities created:
        - facts_extracted: number of facts found
        - prd_sections: number of PRD sections created
        - vp_steps: number of value path steps created
        - features: number of features created
        - personas: number of personas created
    """
    from app.graphs.extract_facts_graph import run_extract_facts
    from app.graphs.build_state_graph import run_build_state_agent

    logger.info(
        f"Starting onboarding for project {project_id}",
        extra={"project_id": str(project_id), "signal_id": str(signal_id), "job_id": str(job_id)},
    )

    # Step 1: Extract facts from the description signal
    logger.info("Step 1: Running extract_facts")
    try:
        facts_output, facts_id, _ = run_extract_facts(
            signal_id=signal_id,
            project_id=project_id,
            job_id=None,  # Don't create separate job - we're tracking with onboarding job
            run_id=run_id,
            top_chunks=None,  # Use default
        )
        facts_count = len(facts_output.facts) if facts_output and facts_output.facts else 0
        logger.info(f"Extracted {facts_count} facts from description")
    except Exception as e:
        logger.error(f"Extract facts failed: {e}")
        facts_count = 0

    # Step 2: Build state (VP, features, personas)
    # Run even if no facts were extracted - might still generate useful structure
    logger.info("Step 2: Running build_state")
    try:
        build_output, vp_count, features_count = run_build_state_agent(
            project_id=project_id,
            job_id=None,  # Don't create separate job
            run_id=run_id,
            include_research=False,  # No research yet, just description
        )
        personas_count = len(build_output.personas) if build_output and build_output.personas else 0
        logger.info(
            f"Built state: {vp_count} VP steps, "
            f"{features_count} features, {personas_count} personas"
        )
    except Exception as e:
        logger.error(f"Build state failed: {e}")
        vp_count = 0
        features_count = 0
        personas_count = 0

    result = {
        "facts_extracted": facts_count,
        "vp_steps": vp_count,
        "features": features_count,
        "personas": personas_count,
    }

    logger.info(
        f"Onboarding complete for project {project_id}",
        extra={"project_id": str(project_id), "result": result},
    )

    return result
