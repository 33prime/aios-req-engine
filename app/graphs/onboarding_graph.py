"""
Onboarding graph that chains extract_facts → build_state.

Used when a project is created with a description to automatically
analyze the description and build initial project state.
"""

import asyncio
import logging
from uuid import UUID
from typing import TypedDict

logger = logging.getLogger(__name__)


class QualityAssessment(TypedDict):
    """Quality assessment of the intake signal."""
    score: str  # "excellent", "good", "basic", "sparse"
    message: str  # User-friendly feedback message
    details: list[str]  # Specific highlights


def assess_intake_quality(
    facts_count: int,
    features_count: int,
    personas_count: int,
    vp_count: int,
    feature_names: list[str],
    persona_names: list[str],
    vp_labels: list[str],
) -> QualityAssessment:
    """
    Assess the quality of the intake based on extraction results.

    Returns a quality assessment with score, message, and details.
    """
    details: list[str] = []

    # Calculate total richness
    total_entities = features_count + personas_count + vp_count

    # Build specific highlights
    if features_count >= 4:
        details.append(f"Captured **{features_count} features** ready for refinement")
    elif features_count >= 2:
        details.append(f"Identified **{features_count} core features**")
    elif features_count == 1:
        details.append("Found **1 feature** - consider adding more")

    if personas_count >= 3:
        details.append(f"Defined **{personas_count} distinct personas** with clear roles")
    elif personas_count >= 2:
        details.append(f"Identified **{personas_count} user personas**")
    elif personas_count == 1:
        details.append("Found **1 persona** - who else will use this?")

    if vp_count >= 5:
        details.append(f"Built **{vp_count}-step value path** from awareness to success")
    elif vp_count >= 3:
        details.append(f"Mapped **{vp_count} value path steps**")
    elif vp_count >= 1:
        details.append(f"Started value path with **{vp_count} step{'s' if vp_count > 1 else ''}**")

    if facts_count >= 10:
        details.append(f"Extracted **{facts_count} actionable facts** from your input")
    elif facts_count >= 5:
        details.append(f"Found **{facts_count} key facts** to work with")

    # Determine overall score and message
    if features_count >= 4 and personas_count >= 2 and vp_count >= 4:
        return QualityAssessment(
            score="excellent",
            message="Excellent intake! Rich detail gives us a strong foundation.",
            details=details,
        )
    elif features_count >= 3 and personas_count >= 1 and vp_count >= 3:
        return QualityAssessment(
            score="good",
            message="Good foundation! We have solid context to build on.",
            details=details,
        )
    elif total_entities >= 3:
        return QualityAssessment(
            score="basic",
            message="Got the basics. Add more detail for better results.",
            details=details if details else ["Consider describing the problem, users, and key features"],
        )
    else:
        return QualityAssessment(
            score="sparse",
            message="Limited extraction. Try adding problem statement, target users, and features.",
            details=details if details else ["We need more context to help effectively"],
        )


def run_onboarding(
    project_id: UUID,
    signal_id: UUID,
    job_id: UUID,
    run_id: UUID,
) -> dict:
    """
    DEPRECATED: Uses V1 build_state_graph which destructively overwrites entities.
    New projects should use project_launch.py (entity_generation + entity_linking with V2).
    Only still called from legacy project creation paths (projects.py, project_creation.py).

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
    from app.db.project_memory import get_or_create_project_memory, add_decision

    logger.info(
        f"Starting onboarding for project {project_id}",
        extra={"project_id": str(project_id), "signal_id": str(signal_id), "job_id": str(job_id)},
    )

    # Initialize project memory early
    try:
        get_or_create_project_memory(project_id)
        logger.info(f"Initialized project memory for {project_id}")
    except Exception as e:
        logger.warning(f"Failed to initialize project memory: {e}")

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

    # Initialize entity name lists (used for decision log, memory synthesis, and quality assessment)
    feature_names: list[str] = []
    persona_names: list[str] = []
    vp_labels: list[str] = []

    # Fetch entity names for summaries
    try:
        from app.db.supabase_client import get_supabase
        supabase = get_supabase()

        if features_count > 0:
            features_resp = (
                supabase.table("features")
                .select("name")
                .eq("project_id", str(project_id))
                .order("created_at", desc=True)
                .limit(features_count)
                .execute()
            )
            feature_names = [f["name"] for f in (features_resp.data or [])]

        if personas_count > 0:
            personas_resp = (
                supabase.table("personas")
                .select("name")
                .eq("project_id", str(project_id))
                .order("created_at", desc=True)
                .limit(personas_count)
                .execute()
            )
            persona_names = [p["name"] for p in (personas_resp.data or [])]

        if vp_count > 0:
            vp_resp = (
                supabase.table("vp_steps")
                .select("label")
                .eq("project_id", str(project_id))
                .order("sort_order")
                .limit(vp_count)
                .execute()
            )
            vp_labels = [s["label"] for s in (vp_resp.data or [])]
    except Exception as e:
        logger.warning(f"Failed to fetch entity names for summary: {e}")

    # Assess intake quality
    quality = assess_intake_quality(
        facts_count=facts_count,
        features_count=features_count,
        personas_count=personas_count,
        vp_count=vp_count,
        feature_names=feature_names,
        persona_names=persona_names,
        vp_labels=vp_labels,
    )
    logger.info(f"Intake quality assessment: {quality['score']} - {quality['message']}")

    # Update the signal metadata with quality assessment
    try:
        supabase.table("signals").update({
            "metadata": {
                "authority": "client",
                "auto_ingested": True,
                "quality_score": quality["score"],
                "quality_message": quality["message"],
                "quality_details": quality["details"],
                "extraction_summary": {
                    "facts": facts_count,
                    "features": features_count,
                    "personas": personas_count,
                    "vp_steps": vp_count,
                    "feature_names": feature_names,
                    "persona_names": persona_names,
                    "vp_labels": vp_labels,
                },
            }
        }).eq("id", str(signal_id)).execute()
        logger.info(f"Updated signal {signal_id} with quality assessment")
    except Exception as e:
        logger.warning(f"Failed to update signal with quality assessment: {e}")

    result = {
        "facts_extracted": facts_count,
        "vp_steps": vp_count,
        "features": features_count,
        "personas": personas_count,
        "quality": quality,
    }

    # Log to project memory what was created - detailed intake summary
    try:
        total_entities = features_count + personas_count + vp_count
        if total_entities > 0:

            # Build detailed decision text
            decision_parts = ["Project initialized from description intake."]

            if feature_names:
                decision_parts.append(f"\n\n**Features ({len(feature_names)}):** " + ", ".join(feature_names))
            elif features_count > 0:
                decision_parts.append(f"\n\n**Features:** {features_count} identified")

            if persona_names:
                decision_parts.append(f"\n\n**Personas ({len(persona_names)}):** " + ", ".join(persona_names))
            elif personas_count > 0:
                decision_parts.append(f"\n\n**Personas:** {personas_count} identified")

            if vp_labels:
                decision_parts.append(f"\n\n**Value Path ({len(vp_labels)} steps):**\n" + "\n".join(f"  {i+1}. {label}" for i, label in enumerate(vp_labels)))
            elif vp_count > 0:
                decision_parts.append(f"\n\n**Value Path:** {vp_count} steps defined")

            decision_text = "".join(decision_parts)

            # Shorter summary for title
            entity_parts = []
            if features_count > 0:
                entity_parts.append(f"{features_count} feature{'s' if features_count > 1 else ''}")
            if personas_count > 0:
                entity_parts.append(f"{personas_count} persona{'s' if personas_count > 1 else ''}")
            if vp_count > 0:
                entity_parts.append(f"{vp_count} value path step{'s' if vp_count > 1 else ''}")
            entity_summary = ", ".join(entity_parts)

            add_decision(
                project_id=project_id,
                title=f"Project intake: {entity_summary}",
                decision=decision_text,
                rationale=f"Analyzed project description ({facts_count} facts extracted) to build initial structure",
                evidence_signal_ids=[str(signal_id)],
                decision_type="initialization",
                decided_by="system",
                confidence=0.85,
            )
            logger.info(f"Logged onboarding results to memory: {entity_summary}")
    except Exception as e:
        logger.warning(f"Failed to log onboarding to memory: {e}")

    # Step 3: Synthesize intelligent memory using LLM
    logger.info("Step 3: Synthesizing project memory with LLM")
    try:
        from app.chains.synthesize_memory import synthesize_intake_memory
        from app.db.project_memory import update_project_memory

        # Get project name for context
        project_name = "Unknown Project"
        try:
            from app.db.supabase_client import get_supabase
            supabase = get_supabase()
            project_resp = (
                supabase.table("projects")
                .select("name, description")
                .eq("id", str(project_id))
                .single()
                .execute()
            )
            project_name = project_resp.data.get("name", "Unknown Project")
            intake_text = project_resp.data.get("description", "")
        except Exception as e:
            logger.warning(f"Failed to get project name: {e}")
            intake_text = ""

        # Generate intelligent memory document
        memory_content = synthesize_intake_memory(
            project_id=project_id,
            project_name=project_name,
            intake_text=intake_text,
            features=feature_names,
            personas=persona_names,
            vp_steps=vp_labels,
        )

        # Save the synthesized memory
        update_project_memory(
            project_id=project_id,
            content=memory_content,
            updated_by="llm_intake_synthesis",
        )
        logger.info(f"Synthesized and saved intelligent memory for {project_id}")

    except Exception as e:
        logger.warning(f"Failed to synthesize memory with LLM: {e}")
        # Don't fail onboarding if memory synthesis fails

    logger.info(
        f"Onboarding complete for project {project_id}",
        extra={"project_id": str(project_id), "result": result},
    )

    return result
