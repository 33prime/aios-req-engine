"""LLM chain for synthesizing the Canvas View value path.

Takes the full project context (actors, workflows, features, drivers, data entities)
and produces a synthesized "golden path" — the critical sequence of steps
the prototype must implement to demonstrate maximum value.
"""

import json
from uuid import UUID

from app.core.config import get_settings
from app.core.llm import parse_llm_json_dict
from app.core.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are a product architect synthesizing a value path for a software prototype.

You will receive context about a project including actors (personas), workflows,
features, business drivers, and data entities. Your job is to synthesize a linear
"golden path" — the critical sequence of steps the prototype must implement to
demonstrate maximum value.

Rules:
- Focus on steps that solve the greatest pain and achieve the highest goals
- Prioritize by ROI (time saved, automation level)
- EXCLUDE obvious/boilerplate flows: signup, login, registration, password reset,
  onboarding, basic navigation, account settings, profile setup
- Each step must link to specific features it enables
- Each step must reference the actor who performs it
- Order steps in the logical sequence a user would experience
- Maximum 12-15 steps (prototype scope)
- Include pain_addressed and goal_served for each step
- Set roi_impact based on time savings and automation potential:
  "high" = major time savings or full automation of painful manual process
  "medium" = moderate improvement
  "low" = minor convenience

For each step, include 1-3 "unlocks" — BONUS value this step enables IN ADDITION to
solving the core problem. These are the "wow" factor — surprising additional capabilities
that weren't originally contemplated but become possible because this step exists.

Think of it as: "Not only does this solve [the pain], it ALSO lets you..."

Unlock types:
- "capability": A completely new ability the business gains (couldn't do this before!)
- "scale": Can now handle dramatically more volume, users, or reach
- "insight": Surfaces data, patterns, or intelligence that didn't exist before
- "speed": So fast it fundamentally changes how decisions are made

For unlocks, also consider non-MVP features (should_have/could_have) that become
naturally available once this step is built. Reference these by name when relevant —
they're the "while we're here, we could also..." opportunities.

DO NOT frame unlocks as before→after or pain→goal. Those belong in the step itself.
Unlocks are the EXTRA, UNEXPECTED value on top of solving the stated problem.

Return valid JSON with this exact structure:
{
  "value_path": [
    {
      "step_index": 0,
      "title": "Short action title",
      "description": "What happens in this step",
      "actor_persona_id": "uuid or null",
      "actor_persona_name": "Name",
      "pain_addressed": "What pain this resolves",
      "goal_served": "What goal this achieves",
      "linked_feature_ids": ["uuid1"],
      "linked_feature_names": ["Feature Name"],
      "source_workflow_step_id": "uuid or null",
      "automation_level": "manual|semi_automated|fully_automated",
      "time_minutes": 5,
      "roi_impact": "high|medium|low",
      "unlocks": [
        {
          "description": "What ADDITIONAL thing becomes possible (the 'wow' factor)",
          "unlock_type": "capability|scale|insight|speed",
          "enabled_by": "What feature or capability enables this bonus",
          "strategic_value": "Why this extra value matters to the business",
          "suggested_feature": "Name of a non-MVP feature this could power, or empty string"
        }
      ]
    }
  ],
  "synthesis_rationale": "Brief explanation of why this path was chosen",
  "excluded_flows": ["signup", "login"]
}
"""


def _build_synthesis_prompt(
    actors: list[dict],
    workflow_pairs: list[dict],
    must_have_features: list[dict],
    business_drivers: list[dict],
    data_entities: list[dict],
    non_mvp_features: list[dict] | None = None,
) -> str:
    """Build the user prompt with full project context."""
    sections = []

    # Actors
    if actors:
        actor_lines = []
        for a in actors:
            role_str = f" ({a.get('role', '')})" if a.get('role') else ""
            canvas_str = f" [Canvas: {a.get('canvas_role', 'none')}]" if a.get('canvas_role') else ""
            goals = a.get("goals") or []
            pains = a.get("pain_points") or []
            actor_lines.append(
                f"- {a['name']}{role_str}{canvas_str}\n"
                f"  Goals: {'; '.join(goals[:5]) if goals else 'None specified'}\n"
                f"  Pain points: {'; '.join(pains[:5]) if pains else 'None specified'}"
            )
        sections.append(f"## Actors (Personas)\n" + "\n".join(actor_lines))

    # Workflows
    if workflow_pairs:
        wf_lines = []
        for wp in workflow_pairs:
            wf_lines.append(f"### Workflow: {wp.get('name', 'Untitled')}")
            if wp.get("description"):
                wf_lines.append(f"  {wp['description']}")

            future_steps = wp.get("future_steps") or []
            if future_steps:
                wf_lines.append("  Future-state steps:")
                for s in future_steps:
                    actor = s.get("actor_persona_name", "")
                    auto = s.get("automation_level", "")
                    time = s.get("time_minutes", "")
                    benefit = s.get("benefit_description", "")
                    features = s.get("feature_names") or []
                    feature_ids = s.get("feature_ids") or []
                    wf_lines.append(
                        f"    {s.get('step_index', 0)}. {s.get('label', '')} "
                        f"[id={s.get('id', '')}] "
                        f"(actor: {actor}, automation: {auto}, time: {time}min)"
                    )
                    if benefit:
                        wf_lines.append(f"       Benefit: {benefit}")
                    if features:
                        feat_str = ", ".join(
                            f"{name} [id={fid}]"
                            for name, fid in zip(features, feature_ids)
                        )
                        wf_lines.append(f"       Features: {feat_str}")

            roi = wp.get("roi")
            if roi and isinstance(roi, dict):
                saved = roi.get("time_saved_minutes", 0)
                pct = roi.get("time_saved_percent", 0)
                if saved > 0:
                    wf_lines.append(f"  ROI: saves {saved}min ({pct}%)")

        sections.append("\n".join(wf_lines))

    # Must-have features
    if must_have_features:
        feat_lines = []
        for f in must_have_features:
            desc = f.get("description") or f.get("overview") or ""
            desc_short = desc[:120] + "..." if len(desc) > 120 else desc
            feat_lines.append(
                f"- {f['name']} [id={f['id']}]: {desc_short}"
            )
        sections.append(f"## Must-Have Features\n" + "\n".join(feat_lines))

    # Business drivers
    if business_drivers:
        driver_lines = []
        for d in business_drivers:
            dtype = d.get("driver_type", "")
            desc = d.get("description", "")[:120]
            driver_lines.append(f"- [{dtype}] {desc}")
        sections.append(f"## Business Drivers\n" + "\n".join(driver_lines))

    # Data entities
    if data_entities:
        de_lines = []
        for de in data_entities:
            de_lines.append(f"- {de['name']} ({de.get('entity_category', 'domain')})")
        sections.append(f"## Data Entities\n" + "\n".join(de_lines))

    # Non-MVP features (for unlock suggestions)
    if non_mvp_features:
        nmvp_lines = []
        for f in non_mvp_features:
            pg = f.get("priority_group", "unset")
            desc = f.get("overview") or f.get("description") or ""
            desc_short = desc[:100] + "..." if len(desc) > 100 else desc
            nmvp_lines.append(f"- {f['name']} [{pg}]: {desc_short}")
        sections.append(
            f"## Non-MVP Features (for unlock suggestions)\n"
            f"These are NOT in scope for the golden path, but consider them for unlock ideas.\n"
            + "\n".join(nmvp_lines)
        )

    prompt = (
        "Synthesize the optimal value path for this project's prototype.\n\n"
        + "\n\n".join(sections)
        + "\n\nReturn the JSON value path now."
    )

    return prompt


async def synthesize_value_path(project_id: UUID) -> dict:
    """
    Run the value path synthesis chain.

    Loads all project context, calls the LLM, and stores the result.

    Args:
        project_id: Project UUID

    Returns:
        Dict with value_path, synthesis_rationale, etc.
    """
    from app.db.canvas_synthesis import upsert_canvas_synthesis
    from app.db.personas import get_canvas_actors
    from app.db.supabase_client import get_supabase

    settings = get_settings()
    client = get_supabase()

    # 1. Load canvas actors
    actors = get_canvas_actors(project_id)
    if not actors:
        raise ValueError("No canvas actors selected")

    actor_ids = [a["id"] for a in actors]

    # 2. Load workflow pairs
    workflow_pairs = []
    try:
        from app.db.workflows import get_workflow_pairs
        workflow_pairs = get_workflow_pairs(project_id)
    except Exception:
        logger.debug(f"Could not load workflow pairs for synthesis")

    # 3. Load must-have features
    features_result = client.table("features").select(
        "id, name, overview, category, vp_step_id"
    ).eq("project_id", str(project_id)).eq("priority_group", "must_have").execute()
    must_have_features = features_result.data or []

    # 3b. Load non-MVP features (for unlock suggestions)
    non_mvp_result = client.table("features").select(
        "id, name, overview, category, priority_group"
    ).eq("project_id", str(project_id)).neq("priority_group", "must_have").execute()
    non_mvp_features = [f for f in (non_mvp_result.data or []) if f.get("priority_group") != "out_of_scope"]

    # 4. Load business drivers
    drivers_result = client.table("business_drivers").select(
        "id, description, driver_type, severity"
    ).eq("project_id", str(project_id)).execute()
    business_drivers = drivers_result.data or []

    # 5. Load data entities
    de_result = client.table("data_entities").select(
        "id, name, entity_category"
    ).eq("project_id", str(project_id)).execute()
    data_entities = de_result.data or []

    # 6. Build prompt
    user_prompt = _build_synthesis_prompt(
        actors=actors,
        workflow_pairs=workflow_pairs,
        must_have_features=must_have_features,
        business_drivers=business_drivers,
        data_entities=data_entities,
        non_mvp_features=non_mvp_features,
    )

    # 7. Call LLM
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage

    model = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        temperature=0.1,
        max_tokens=8192,
        api_key=settings.ANTHROPIC_API_KEY,
    )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]

    response = await model.ainvoke(messages)
    raw_output = response.content if isinstance(response.content, str) else str(response.content)

    # 8. Parse output
    parsed = parse_llm_json_dict(raw_output)
    value_path = parsed.get("value_path", [])
    synthesis_rationale = parsed.get("synthesis_rationale", "")
    excluded_flows = parsed.get("excluded_flows", [])

    # Extract source IDs
    source_workflow_ids = list({
        wp.get("id") for wp in workflow_pairs if wp.get("id")
    })

    # 9. Store result
    result = upsert_canvas_synthesis(
        project_id=project_id,
        value_path=value_path,
        rationale=synthesis_rationale,
        excluded_flows=excluded_flows,
        source_workflow_ids=source_workflow_ids,
        source_persona_ids=actor_ids,
    )

    logger.info(
        f"Synthesized value path for project {project_id}: {len(value_path)} steps",
        extra={"project_id": str(project_id), "step_count": len(value_path)},
    )

    return {
        "value_path": value_path,
        "synthesis_rationale": synthesis_rationale,
        "excluded_flows": excluded_flows,
        "step_count": len(value_path),
        "version": result.get("version", 1),
    }
