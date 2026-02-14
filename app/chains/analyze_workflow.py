"""
Workflow Batch Enrichment Chain

One LLM call per workflow — analyzes all current/future steps together.
Produces per-step enrichments + workflow-level strategic unlocks.

8 calls per project instead of 64.
"""

import json
import re
from typing import Any, Literal
from uuid import UUID

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


# ============================================================================
# Output schemas
# ============================================================================


class StepUnlock(BaseModel):
    """A capability unlocked by automation — used at both step and workflow level."""

    description: str = Field(
        ...,
        description="One concrete sentence: what becomes possible.",
    )
    unlock_type: Literal["capability", "scale", "insight", "speed"] = Field(
        ...,
        description="capability=previously impossible; scale=impossible volume; insight=new understanding; speed=game-changing fast.",
    )
    enabled_by: str = Field(
        ...,
        description="What about the automation makes this possible.",
    )
    strategic_value: str = Field(
        ...,
        description="Why this matters beyond time savings. One sentence.",
    )
    linked_goal_id: str | None = Field(
        None,
        description="ID of the business goal this advances, if applicable.",
    )


class StepEnrichmentResult(BaseModel):
    """Per-step output from the batch workflow analysis."""

    step_id: str = Field(..., description="The UUID of the step being analyzed.")
    narrative: str = Field(
        ...,
        description="1-2 sentences: what this step does, why it matters in the workflow.",
    )
    optimization_suggestions: list[str] = Field(
        default_factory=list,
        description="0-2 concrete improvement suggestions.",
    )
    automation_opportunity_score: float = Field(
        0.0,
        description="0.0-1.0 automation suitability score.",
    )
    complexity: Literal["low", "medium", "high", "critical"] | None = Field(
        None,
        description="Implementation complexity.",
    )


class WorkflowEnrichmentResult(BaseModel):
    """Complete output from one workflow batch analysis call."""

    transformation_narrative: str = Field(
        ...,
        description="2-3 sentences capturing the before→after story of this workflow transformation.",
    )
    strategic_unlocks: list[StepUnlock] = Field(
        default_factory=list,
        description="1-3 NEW capabilities this workflow transformation makes possible. NOT time savings. Ground in project goals.",
    )
    cross_step_insights: list[str] = Field(
        default_factory=list,
        description="0-3 observations about patterns, bottlenecks, or dependencies across steps.",
    )
    overall_complexity: Literal["low", "medium", "high", "critical"] | None = Field(
        None,
        description="Overall implementation complexity of the full transformation.",
    )
    step_enrichments: list[StepEnrichmentResult] = Field(
        default_factory=list,
        description="Per-step enrichment for each future-state step.",
    )


# ============================================================================
# Main batch enrichment function
# ============================================================================


async def enrich_workflow(
    workflow_id: UUID,
    project_id: UUID,
) -> dict[str, Any]:
    """
    Batch-analyze a full workflow in one LLM call.

    Loads all current + future steps, project context, and business goals.
    Returns enrichment data stored on both the workflow and individual steps.
    """
    settings = get_settings()
    supabase = get_supabase()

    # 1. Load the workflow (could be a pair — find both sides)
    wf_result = supabase.table("workflows").select("*").eq(
        "id", str(workflow_id)
    ).maybe_single().execute()
    workflow = wf_result.data if wf_result else None
    if not workflow:
        raise ValueError(f"Workflow not found: {workflow_id}")

    workflow_name = workflow.get("name", "")
    state_type = workflow.get("state_type", "")
    paired_id = workflow.get("paired_workflow_id")

    # Determine current/future workflow IDs
    if state_type == "current":
        current_wf_id = str(workflow_id)
        future_wf_id = paired_id
    elif state_type == "future":
        future_wf_id = str(workflow_id)
        current_wf_id = paired_id
    else:
        current_wf_id = str(workflow_id)
        future_wf_id = paired_id

    # 2. Load all steps for both sides
    wf_ids = [wid for wid in [current_wf_id, future_wf_id] if wid]
    steps_result = supabase.table("vp_steps").select("*").in_(
        "workflow_id", wf_ids
    ).order("step_index").execute()
    all_steps = steps_result.data or []

    current_steps = [s for s in all_steps if s.get("workflow_id") == current_wf_id]
    future_steps = [s for s in all_steps if s.get("workflow_id") == future_wf_id]

    if not current_steps and not future_steps:
        logger.warning(f"No steps found for workflow {workflow_id}")
        return {}

    # 3. Load project context
    project_result = supabase.table("projects").select(
        "name, description, vision"
    ).eq("id", str(project_id)).maybe_single().execute()
    project = project_result.data if project_result else {}

    # 4. Load business drivers and goals
    drivers_result = supabase.table("business_drivers").select(
        "id, description, driver_type, severity, linked_vp_step_ids"
    ).eq("project_id", str(project_id)).execute()
    all_drivers = drivers_result.data or []
    project_goals = [d for d in all_drivers if d.get("driver_type") == "goal"]

    # 5. Load features linked to any step in this workflow
    step_ids = [s["id"] for s in all_steps]
    features_result = supabase.table("features").select(
        "id, name, category, vp_step_id"
    ).in_("vp_step_id", step_ids).execute()
    all_features = features_result.data or []
    features_by_step: dict[str, list[str]] = {}
    for f in all_features:
        sid = f.get("vp_step_id")
        if sid:
            features_by_step.setdefault(sid, []).append(f.get("name", ""))

    # 6. Load personas for actor resolution
    actor_ids = list({s["actor_persona_id"] for s in all_steps if s.get("actor_persona_id")})
    persona_map: dict[str, str] = {}
    if actor_ids:
        personas_result = supabase.table("personas").select(
            "id, name"
        ).in_("id", actor_ids).execute()
        for p in (personas_result.data or []):
            persona_map[p["id"]] = p.get("name", "Unknown")

    # 7. Build the prompt
    prompt_parts = [
        f"PROJECT: {project.get('name', 'Unknown')}",
        f"VISION: {project.get('vision') or project.get('description') or 'Not set'}",
        f"\nWORKFLOW: {workflow_name}",
    ]
    if workflow.get("description"):
        prompt_parts.append(f"Description: {workflow['description']}")

    # Current state steps
    if current_steps:
        prompt_parts.append("\n--- CURRENT STATE STEPS ---")
        for s in current_steps:
            actor = persona_map.get(s.get("actor_persona_id", ""), "Unassigned")
            line = f"  {s.get('step_index', '?')}. [{s['id']}] {s.get('label', '')}"
            line += f" | Actor: {actor} | {s.get('automation_level', 'manual')}"
            if s.get("time_minutes") is not None:
                line += f" | {s['time_minutes']}min"
            prompt_parts.append(line)
            if s.get("pain_description"):
                prompt_parts.append(f"     Pain: {s['pain_description']}")

    # Future state steps
    if future_steps:
        prompt_parts.append("\n--- FUTURE STATE STEPS ---")
        for s in future_steps:
            actor = persona_map.get(s.get("actor_persona_id", ""), "Unassigned")
            line = f"  {s.get('step_index', '?')}. [{s['id']}] {s.get('label', '')}"
            line += f" | Actor: {actor} | {s.get('automation_level', 'manual')}"
            if s.get("time_minutes") is not None:
                line += f" | {s['time_minutes']}min"
            prompt_parts.append(line)
            if s.get("benefit_description"):
                prompt_parts.append(f"     Benefit: {s['benefit_description']}")
            step_features = features_by_step.get(s["id"], [])
            if step_features:
                prompt_parts.append(f"     Features: {', '.join(step_features)}")

    # Business goals for unlock grounding
    if project_goals:
        prompt_parts.append("\n--- PROJECT GOALS (use IDs for linked_goal_id) ---")
        for g in project_goals[:8]:
            prompt_parts.append(f"  [{g['id']}] {g.get('description', '')[:120]}")

    # Build step_ids list for the output schema reference
    future_step_ids = [{"step_id": s["id"], "label": s.get("label", "")} for s in future_steps]
    prompt_parts.append(f"\n--- FUTURE STEP IDS (include all in step_enrichments) ---")
    prompt_parts.append(json.dumps(future_step_ids, indent=2))

    system_msg = SystemMessage(content=(
        "You are a business process transformation analyst. You analyze COMPLETE workflow "
        "transformations — the full current→future journey — in one pass.\n\n"
        "Your job:\n"
        "1. For EACH future-state step: write a brief narrative, suggest 0-2 optimizations, "
        "rate automation opportunity (0.0-1.0), assess complexity.\n"
        "2. For the WORKFLOW AS A WHOLE: write a transformation narrative (before→after story), "
        "identify 1-3 strategic unlocks that the transformation makes POSSIBLE that manual "
        "processes fundamentally couldn't support.\n\n"
        "UNLOCK RULES:\n"
        "- NOT 'saves time' or 'reduces errors' — those are just efficiency\n"
        "- YES: new capabilities, new scale, new insights, game-changing speed\n"
        "- Ground each in a project goal when possible (use the goal ID)\n"
        "- The best unlocks come from seeing MULTIPLE steps transform together\n\n"
        "Be specific, practical, grounded in the data provided. No hallucination.\n\n"
        "Return VALID JSON matching this schema exactly:\n"
        "{\n"
        '  "transformation_narrative": "string",\n'
        '  "strategic_unlocks": [{"description": "...", "unlock_type": "capability|scale|insight|speed", '
        '"enabled_by": "...", "strategic_value": "...", "linked_goal_id": "uuid|null"}],\n'
        '  "cross_step_insights": ["string"],\n'
        '  "overall_complexity": "low|medium|high|critical",\n'
        '  "step_enrichments": [{"step_id": "uuid", "narrative": "...", '
        '"optimization_suggestions": ["..."], "automation_opportunity_score": 0.0, '
        '"complexity": "low|medium|high|critical"}]\n'
        "}\n"
        "Include a step_enrichment entry for EVERY future-state step listed."
    ))

    human_msg = HumanMessage(content=(
        "Analyze this complete workflow transformation:\n\n"
        + "\n".join(prompt_parts)
    ))

    # 8. Call LLM
    try:
        llm = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=settings.ANTHROPIC_API_KEY,
            temperature=0.3,
            max_tokens=4000,
        )
        response = await llm.ainvoke([system_msg, human_msg])
        result = _parse_response(response.content)

        # 9. Store per-step enrichments
        step_enrichment_map: dict[str, dict] = {}
        for se in result.step_enrichments:
            step_data = {
                "narrative": se.narrative,
                "optimization_suggestions": se.optimization_suggestions,
                "automation_opportunity_score": se.automation_opportunity_score,
                "complexity": se.complexity,
            }
            step_enrichment_map[se.step_id] = step_data
            try:
                supabase.table("vp_steps").update({
                    "enrichment_data": step_data,
                    "enrichment_status": "enriched",
                    "enrichment_attempted_at": "now()",
                }).eq("id", se.step_id).execute()
            except Exception:
                logger.warning(f"Failed to update step {se.step_id} enrichment")

        # 10. Store workflow-level enrichment
        workflow_data = {
            "transformation_narrative": result.transformation_narrative,
            "strategic_unlocks": [u.model_dump() for u in result.strategic_unlocks],
            "cross_step_insights": result.cross_step_insights,
            "overall_complexity": result.overall_complexity,
        }

        # Update both workflow sides if paired
        for wid in wf_ids:
            try:
                supabase.table("workflows").update({
                    "enrichment_data": workflow_data,
                    "enrichment_status": "enriched",
                    "enrichment_attempted_at": "now()",
                }).eq("id", wid).execute()
            except Exception:
                logger.warning(f"Failed to update workflow {wid} enrichment")

        enriched_count = len(step_enrichment_map)
        unlock_count = len(result.strategic_unlocks)
        logger.info(
            f"Enriched workflow '{workflow_name}': "
            f"{enriched_count} steps, {unlock_count} unlocks"
        )
        return {
            "workflow": workflow_data,
            "steps": step_enrichment_map,
            "enriched_step_count": enriched_count,
            "unlock_count": unlock_count,
        }

    except Exception as e:
        logger.exception(f"Failed to enrich workflow {workflow_id}")
        # Mark workflow as failed
        for wid in wf_ids:
            try:
                supabase.table("workflows").update({
                    "enrichment_status": "failed",
                    "enrichment_attempted_at": "now()",
                }).eq("id", wid).execute()
            except Exception:
                pass
        raise


def _parse_response(content: str) -> WorkflowEnrichmentResult:
    """Parse LLM response, handling markdown code fences."""
    text = content.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)

    try:
        data = json.loads(text)
        return WorkflowEnrichmentResult(**data)
    except (json.JSONDecodeError, Exception) as e:
        # Try to extract JSON from the response
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            data = json.loads(match.group())
            return WorkflowEnrichmentResult(**data)
        raise ValueError(f"Could not parse LLM response as JSON: {e}") from e
