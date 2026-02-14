"""Analyze a single value path step for the Canvas View drawer.

Pure data-driven — no LLM calls. Assembles actors, data operations,
features, and constraints from existing DB records. Business calculations
are derived from the step's time/automation/ROI data.
"""

from uuid import UUID

from app.core.logging import get_logger
from app.core.schemas_canvas import (
    StepActor,
    StepBusinessLogic,
    StepDataOperation,
    StepLinkedFeature,
    ValuePathStepDetail,
)

logger = get_logger(__name__)


async def get_value_path_step_detail(
    project_id: UUID,
    step_index: int,
) -> ValuePathStepDetail:
    """
    Build the full detail for a value path step.

    Pure data assembly — no LLM calls. Instant response.
    """
    from app.db.canvas_synthesis import get_canvas_synthesis
    from app.db.supabase_client import get_supabase

    client = get_supabase()

    # 1. Load the value path synthesis
    synthesis = get_canvas_synthesis(project_id)
    if not synthesis:
        raise ValueError("No value path synthesis found")

    value_path = synthesis.get("value_path") or []
    step_data = None
    for s in value_path:
        if s.get("step_index") == step_index:
            step_data = s
            break

    if not step_data:
        raise ValueError(f"Step index {step_index} not found in value path")

    # 2. Resolve actor persona(s)
    actors: list[StepActor] = []
    actor_id = step_data.get("actor_persona_id")
    if actor_id:
        try:
            persona_result = client.table("personas").select(
                "id, name, role, goals, pain_points, canvas_role"
            ).eq("id", actor_id).maybe_single().execute()
            if persona_result.data:
                p = persona_result.data
                actors.append(StepActor(
                    persona_id=p["id"],
                    persona_name=p["name"],
                    role=p.get("role"),
                    pain_at_step=step_data.get("pain_addressed"),
                    goal_at_step=step_data.get("goal_served"),
                    is_primary=p.get("canvas_role") == "primary",
                ))
        except Exception:
            logger.debug(f"Could not load actor persona {actor_id}")

    # 3. Load data entity operations via source workflow step
    source_step_id = step_data.get("source_workflow_step_id")
    data_operations: list[StepDataOperation] = []
    if source_step_id:
        try:
            de_links = client.table("data_entity_workflow_steps").select(
                "data_entity_id, operation_type, description, "
                "data_entities(id, name, entity_category)"
            ).eq("vp_step_id", source_step_id).execute()

            for link in (de_links.data or []):
                de = link.get("data_entities") or {}
                if de.get("id"):
                    data_operations.append(StepDataOperation(
                        entity_id=de["id"],
                        entity_name=de.get("name", "Unknown"),
                        entity_category=de.get("entity_category", "domain"),
                        operation=link.get("operation_type", "read"),
                        description=link.get("description"),
                    ))
        except Exception:
            logger.debug(f"Could not load data entity links for step {source_step_id}")

    # 4. Load linked features
    linked_features: list[StepLinkedFeature] = []
    feature_ids = step_data.get("linked_feature_ids") or []
    if feature_ids:
        try:
            feat_result = client.table("features").select(
                "id, name, category, priority_group, confirmation_status"
            ).in_("id", feature_ids).execute()

            for f in (feat_result.data or []):
                linked_features.append(StepLinkedFeature(
                    feature_id=f["id"],
                    feature_name=f["name"],
                    category=f.get("category"),
                    priority_group=f.get("priority_group"),
                    confirmation_status=f.get("confirmation_status"),
                ))
        except Exception:
            logger.debug(f"Could not load features for step {step_index}")

    # 5. Build business calculations from step data
    business_logic = _build_business_calculations(step_data, actors, data_operations)

    # 6. Build combined value from available data
    combined_value = _build_combined_value(step_data, actors, linked_features)

    # 7. Assemble the full detail
    return ValuePathStepDetail(
        step_index=step_data["step_index"],
        title=step_data["title"],
        description=step_data.get("description", ""),
        automation_level=step_data.get("automation_level", "manual"),
        time_minutes=step_data.get("time_minutes"),
        roi_impact=step_data.get("roi_impact", "medium"),
        pain_addressed=step_data.get("pain_addressed"),
        goal_served=step_data.get("goal_served"),
        # Tab 1: Actors
        actors=actors,
        combined_value=combined_value,
        # Tab 2: System Flow
        data_operations=data_operations,
        input_dependencies=[],
        output_effects=[],
        # Tab 3: Business Calculations
        business_logic=business_logic,
        # Tab 4: Features
        recommended_components=[],
        linked_features=linked_features,
        ai_suggestions=[],
        effort_level=_estimate_effort(step_data, data_operations, linked_features),
    )


def _build_business_calculations(
    step_data: dict,
    actors: list[StepActor],
    data_operations: list[StepDataOperation],
) -> StepBusinessLogic:
    """Build business-focused calculations from step data."""
    decision_points: list[str] = []
    validation_rules: list[str] = []
    edge_cases: list[str] = []
    error_states: list[str] = []

    time_minutes = step_data.get("time_minutes")
    automation = step_data.get("automation_level", "manual")
    roi_impact = step_data.get("roi_impact", "medium")
    pain = step_data.get("pain_addressed", "")
    goal = step_data.get("goal_served", "")

    # ROI calculation
    if time_minutes and automation in ("semi_automated", "fully_automated"):
        savings_factor = 0.8 if automation == "fully_automated" else 0.5
        saved_per_run = round(time_minutes * savings_factor)
        if saved_per_run > 0:
            monthly_runs = 200  # reasonable assumption
            monthly_hours = round((saved_per_run * monthly_runs) / 60, 1)
            decision_points.append(
                f"Time savings: {time_minutes}min manual → {time_minutes - saved_per_run}min "
                f"{'automated' if automation == 'fully_automated' else 'assisted'} "
                f"= {saved_per_run}min saved per execution"
            )
            decision_points.append(
                f"Volume impact: At ~{monthly_runs} executions/month, "
                f"saves ~{monthly_hours} hours/month"
            )

    # Before/After from pain → goal
    if pain and goal:
        validation_rules.append(f"Before: {pain}")
        validation_rules.append(f"After: {goal}")

    # Automation impact
    if automation == "fully_automated":
        edge_cases.append("Fully automated — removes human bottleneck entirely")
    elif automation == "semi_automated":
        edge_cases.append("Semi-automated — human reviews AI recommendations before proceeding")
    else:
        edge_cases.append("Manual step — opportunity for future automation")

    # Data complexity
    if len(data_operations) > 0:
        create_ops = [op for op in data_operations if op.operation.lower() == "create"]
        read_ops = [op for op in data_operations if op.operation.lower() == "read"]
        if create_ops:
            error_states.append(
                f"Creates {len(create_ops)} data record(s): "
                + ", ".join(op.entity_name for op in create_ops)
            )
        if read_ops:
            error_states.append(
                f"Reads from {len(read_ops)} source(s): "
                + ", ".join(op.entity_name for op in read_ops)
            )

    # Success criteria
    success = ""
    if goal:
        success = goal
    elif roi_impact == "high":
        success = f"Step completes with measurable impact on core workflow"
    else:
        success = f"Step completes successfully for {actors[0].persona_name}" if actors else "Step completes"

    return StepBusinessLogic(
        decision_points=decision_points,
        validation_rules=validation_rules,
        edge_cases=edge_cases,
        success_criteria=success,
        error_states=error_states,
    )


def _build_combined_value(
    step_data: dict,
    actors: list[StepActor],
    linked_features: list[StepLinkedFeature],
) -> str:
    """Build a combined value statement from step data."""
    parts = []
    if step_data.get("goal_served"):
        parts.append(step_data["goal_served"])
    if actors:
        actor_names = [a.persona_name for a in actors]
        parts.append(f"for {', '.join(actor_names)}")
    if linked_features:
        feat_names = [f.feature_name for f in linked_features[:3]]
        parts.append(f"powered by {', '.join(feat_names)}")
    return " — ".join(parts) if parts else ""


def _estimate_effort(
    step_data: dict,
    data_operations: list[StepDataOperation],
    linked_features: list[StepLinkedFeature],
) -> str:
    """Estimate implementation effort from complexity signals."""
    score = 0
    if step_data.get("automation_level") == "fully_automated":
        score += 2
    elif step_data.get("automation_level") == "semi_automated":
        score += 1
    score += min(len(data_operations), 3)
    score += min(len(linked_features), 3)
    if score >= 5:
        return "heavy"
    elif score >= 3:
        return "medium"
    return "light"
