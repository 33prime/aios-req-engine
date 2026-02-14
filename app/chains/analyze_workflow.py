"""
Workflow Step Enrichment Chain

On-demand AI analysis for individual workflow steps. Generates:
- Narrative description
- Optimization suggestions
- Risk assessment
- Automation opportunity score
- Complexity rating

Follows the enrich_pain_point.py pattern: load context, prompt, parse, store.
"""

from typing import Any, Literal
from uuid import UUID

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


class StepUnlock(BaseModel):
    """A capability, insight, or scale advantage that automation of this step enables."""

    description: str = Field(
        ...,
        description="One concrete sentence describing what becomes possible. E.g. 'Real-time inventory visibility enables predictive reorder triggers.'",
    )
    unlock_type: Literal["capability", "scale", "insight", "speed"] = Field(
        ...,
        description="capability = something previously impossible; scale = same thing at impossible volume; insight = new understanding; speed = fast enough to change the game.",
    )
    enabled_by: str = Field(
        ...,
        description="What about the automation specifically makes this possible. E.g. 'Continuous automated scanning replaces daily manual counts.'",
    )
    strategic_value: str = Field(
        ...,
        description="Why this matters beyond time savings — competitive advantage, new revenue, risk reduction. One sentence.",
    )
    linked_goal_id: str | None = Field(
        None,
        description="If this unlock directly advances one of the provided business goals, include that goal's ID. Otherwise null.",
    )


class WorkflowStepEnrichment(BaseModel):
    """AI-generated analysis for a workflow step."""

    narrative: str | None = Field(
        None,
        description="A 2-3 sentence narrative explaining what this step does, why it matters, and how it fits into the larger workflow.",
    )
    optimization_suggestions: list[str] = Field(
        default_factory=list,
        description="Concrete suggestions for improving this step (automation, simplification, elimination, reordering).",
    )
    risk_assessment: str | None = Field(
        None,
        description="Potential risks or failure points for this step.",
    )
    automation_opportunity_score: float = Field(
        0.0,
        description="Score 0.0-1.0 indicating how suitable this step is for automation. 1.0 = perfect automation candidate.",
    )
    automation_approach: str | None = Field(
        None,
        description="If automation score > 0.5, describe how automation could be implemented.",
    )
    unlocks: list[StepUnlock] = Field(
        default_factory=list,
        description="1-3 capabilities, insights, or advantages that automating this step makes possible — things the manual process fundamentally couldn't support. Only include if the step moves from manual/semi to a higher automation level. Ground each in the project goals provided. Do NOT include generic 'saves time' statements.",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="Key dependencies this step has on other systems, data, or people.",
    )
    complexity: Literal["low", "medium", "high", "critical"] | None = Field(
        None,
        description="Implementation complexity: low (simple), medium (moderate effort), high (significant work), critical (major initiative).",
    )
    confidence: float = Field(
        0.0,
        description="Confidence in this analysis (0.0-1.0).",
    )


async def enrich_workflow_step(
    step_id: UUID,
    project_id: UUID,
) -> dict[str, Any]:
    """
    Analyze a workflow step using Claude Sonnet and store results.

    Returns the enrichment data dict.
    """
    settings = get_settings()
    supabase = get_supabase()

    # 1. Load step
    step_result = supabase.table("vp_steps").select("*").eq(
        "id", str(step_id)
    ).maybe_single().execute()
    step = step_result.data if step_result else None
    if not step:
        raise ValueError(f"Step not found: {step_id}")

    # 2. Load workflow context
    workflow_name = ""
    state_type = ""
    if step.get("workflow_id"):
        wf_result = supabase.table("workflows").select(
            "name, state_type, description"
        ).eq("id", step["workflow_id"]).maybe_single().execute()
        if wf_result and wf_result.data:
            workflow_name = wf_result.data.get("name", "")
            state_type = wf_result.data.get("state_type", "")

    # 3. Load project context
    project_result = supabase.table("projects").select(
        "name, description, vision"
    ).eq("id", str(project_id)).maybe_single().execute()
    project = project_result.data if project_result else {}

    # 4. Load linked features
    features_result = supabase.table("features").select(
        "name, category, priority_group"
    ).eq("vp_step_id", str(step_id)).execute()
    features = features_result.data or []

    # 5. Load linked business drivers + all goals for unlock grounding
    drivers_result = supabase.table("business_drivers").select(
        "id, description, driver_type, severity, linked_vp_step_ids"
    ).eq("project_id", str(project_id)).execute()
    all_drivers = drivers_result.data or []
    linked_drivers = []
    project_goals = []
    for d in all_drivers:
        linked_ids = d.get("linked_vp_step_ids") or []
        if str(step_id) in [str(lid) for lid in linked_ids]:
            linked_drivers.append(d)
        if d.get("driver_type") == "goal":
            project_goals.append(d)

    # 6. Load actor persona
    actor_name = "Unknown"
    if step.get("actor_persona_id"):
        persona_result = supabase.table("personas").select(
            "name, role"
        ).eq("id", step["actor_persona_id"]).maybe_single().execute()
        if persona_result and persona_result.data:
            actor_name = persona_result.data.get("name", "Unknown")

    # Build prompt
    parser = PydanticOutputParser(pydantic_object=WorkflowStepEnrichment)

    context_parts = [
        f"Project: {project.get('name', 'Unknown')}",
        f"Vision: {project.get('vision') or project.get('description') or 'Not set'}",
        f"Workflow: {workflow_name} ({state_type} state)",
        f"Step {step.get('step_index', '?')}: {step.get('label', '')}",
        f"Description: {step.get('description') or 'None'}",
        f"Actor: {actor_name}",
        f"Automation level: {step.get('automation_level', 'manual')}",
        f"Time: {step.get('time_minutes') or 'Unknown'} minutes",
        f"Operation type: {step.get('operation_type') or 'None'}",
    ]

    if step.get("pain_description"):
        context_parts.append(f"Pain: {step['pain_description']}")
    if step.get("benefit_description"):
        context_parts.append(f"Benefit: {step['benefit_description']}")

    if features:
        context_parts.append(
            f"Linked features: {', '.join(f.get('name', '') for f in features)}"
        )
    if linked_drivers:
        context_parts.append(
            f"Linked drivers: {', '.join(d.get('description', '')[:80] for d in linked_drivers)}"
        )

    # Include project goals for unlock grounding
    if project_goals:
        goal_lines = []
        for g in project_goals[:8]:  # Cap at 8 goals
            goal_lines.append(f"  - [{g['id']}] {g.get('description', '')[:100]}")
        context_parts.append("Project business goals (use IDs for linked_goal_id):\n" + "\n".join(goal_lines))

    system_msg = SystemMessage(content=(
        "You are a business process analyst helping consultants understand workflow steps. "
        "Analyze the given workflow step in context and provide actionable insights. "
        "Be specific, practical, and grounded in the provided data. "
        "Do not hallucinate features or capabilities not mentioned in the context.\n\n"
        "IMPORTANT for unlocks: Think beyond time savings. What does automating this step "
        "make POSSIBLE that the manual process fundamentally couldn't support? "
        "Only include unlocks when automation creates genuinely new capabilities, insights, "
        "or scale — not just faster versions of the same thing. Max 1-3 unlocks. "
        "Ground each unlock in a project goal when possible.\n\n"
        f"{parser.get_format_instructions()}"
    ))

    human_msg = HumanMessage(content=(
        "Analyze this workflow step and provide enrichment:\n\n"
        + "\n".join(context_parts)
    ))

    # 7. Call LLM
    try:
        llm = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=settings.anthropic_api_key,
            temperature=0.3,
            max_tokens=1500,
        )
        response = await llm.ainvoke([system_msg, human_msg])
        enrichment = parser.parse(response.content)
        enrichment_data = enrichment.model_dump()

        # 8. Store results
        supabase.table("vp_steps").update({
            "enrichment_data": enrichment_data,
            "enrichment_status": "enriched",
            "enrichment_attempted_at": "now()",
        }).eq("id", str(step_id)).execute()

        logger.info(f"Enriched workflow step {step_id} (confidence: {enrichment.confidence})")
        return enrichment_data

    except Exception as e:
        logger.exception(f"Failed to enrich workflow step {step_id}")
        # Mark as failed
        try:
            supabase.table("vp_steps").update({
                "enrichment_status": "failed",
                "enrichment_attempted_at": "now()",
            }).eq("id", str(step_id)).execute()
        except Exception:
            pass
        raise
