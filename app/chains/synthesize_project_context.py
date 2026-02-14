"""LLM chain for synthesizing the living Project Context.

Takes the full BRD data (vision, personas, features, workflows, constraints,
data entities, stakeholders, competitors) and produces a structured project
context document — the single source of truth for the dev agent.
"""

import json
from uuid import UUID

from app.core.config import get_settings
from app.core.llm import parse_llm_json_dict
from app.core.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are synthesizing a clean, living Software Summary for a project.

You will receive discovery data — vision, personas, workflows, features, constraints,
stakeholders, and competitors. Synthesize this into a clear, executive-level summary
that describes what the software does, who it's for, and what it aims to achieve.

Think of this as the single document someone reads to understand the project in 2 minutes.
It should be clean and polished — not a data dump.

Rules:
- Write in clear, confident prose. Active voice, present tense.
- Each section should be 2-4 sentences — concise but substantive.
- Reference specific personas, features, and workflows by name.
- Focus on goals and objectives, not implementation details.
- Assumptions = beliefs that could be wrong but are guiding decisions.
- Open questions = things that, if answered differently, would change the product.

Return valid JSON with this exact structure:
{
  "product_vision": "What this software is and why it exists. The big picture in 2-3 sentences.",
  "target_users": "Who uses this and what they need. Reference personas by name and role.",
  "core_value_proposition": "The specific value this delivers. What changes for the users.",
  "key_workflows": "The core processes this software supports. Reference workflow names.",
  "data_landscape": "The key information the system manages and how it connects.",
  "technical_boundaries": "Known constraints and non-negotiables — keep it brief.",
  "design_principles": "Visual direction and UX philosophy — only if discovered.",
  "assumptions": ["Assumption 1", "Assumption 2"],
  "open_questions": ["Question 1", "Question 2"]
}
"""


def _build_context_prompt(
    project: dict,
    personas: list[dict],
    features: list[dict],
    workflow_pairs: list[dict],
    constraints: list[dict],
    data_entities: list[dict],
    stakeholders: list[dict],
    competitors: list[dict],
    business_drivers: list[dict],
) -> str:
    """Build the user prompt with full project data."""
    sections = []

    # Project basics
    project_lines = []
    if project.get("name"):
        project_lines.append(f"Project: {project['name']}")
    if project.get("vision"):
        project_lines.append(f"Vision: {project['vision']}")

    # Company info
    company = project.get("company_info") or {}
    if company.get("name"):
        project_lines.append(f"Client: {company['name']}")
    if company.get("industry"):
        project_lines.append(f"Industry: {company['industry']}")
    if company.get("description"):
        project_lines.append(f"Background: {company['description'][:300]}")
    if project_lines:
        sections.append("## Project\n" + "\n".join(project_lines))

    # Personas
    if personas:
        lines = []
        for p in personas:
            goals = p.get("goals") or []
            pains = p.get("pain_points") or []
            role = p.get("role", "")
            canvas = p.get("canvas_role", "")
            line = f"- **{p['name']}** ({role})"
            if canvas:
                line += f" [Canvas: {canvas}]"
            if goals:
                line += f"\n  Goals: {'; '.join(goals[:4])}"
            if pains:
                line += f"\n  Pains: {'; '.join(pains[:4])}"
            lines.append(line)
        sections.append("## Personas\n" + "\n".join(lines))

    # Business drivers
    if business_drivers:
        by_type: dict[str, list[str]] = {}
        for d in business_drivers:
            dtype = d.get("driver_type", "other")
            desc = d.get("description", "")[:150]
            by_type.setdefault(dtype, []).append(desc)
        lines = []
        for dtype, descs in by_type.items():
            lines.append(f"### {dtype.upper()}")
            for desc in descs[:6]:
                lines.append(f"- {desc}")
        sections.append("## Business Drivers\n" + "\n".join(lines))

    # Workflows
    if workflow_pairs:
        lines = []
        for wp in workflow_pairs:
            lines.append(f"### {wp.get('name', 'Untitled')}")
            if wp.get("description"):
                lines.append(f"  {wp['description'][:200]}")
            future = wp.get("future_steps") or []
            if future:
                step_names = [s.get("label", "") for s in future[:8]]
                lines.append(f"  Future steps: {' → '.join(step_names)}")
            roi = wp.get("roi")
            if roi and isinstance(roi, dict) and roi.get("time_saved_percent"):
                lines.append(f"  ROI: {roi['time_saved_percent']:.0f}% time saved")
        sections.append("## Workflows\n" + "\n".join(lines))

    # Features
    if features:
        by_priority: dict[str, list[str]] = {}
        for f in features:
            pg = f.get("priority_group") or "unset"
            name = f["name"]
            desc = (f.get("overview") or f.get("description") or "")[:80]
            by_priority.setdefault(pg, []).append(f"{name}: {desc}" if desc else name)
        lines = []
        for pg in ["must_have", "should_have", "could_have", "out_of_scope", "unset"]:
            items = by_priority.get(pg, [])
            if items:
                lines.append(f"### {pg.replace('_', ' ').title()} ({len(items)})")
                for item in items[:10]:
                    lines.append(f"- {item}")
        sections.append("## Features\n" + "\n".join(lines))

    # Data entities
    if data_entities:
        lines = []
        for de in data_entities:
            fields = de.get("fields") or []
            field_names = [f_item.get("name", "") for f_item in fields[:6]] if isinstance(fields, list) else []
            line = f"- **{de['name']}** ({de.get('entity_category', 'domain')})"
            if field_names:
                line += f" — fields: {', '.join(field_names)}"
            lines.append(line)
        sections.append("## Data Entities\n" + "\n".join(lines))

    # Constraints
    if constraints:
        lines = []
        for c in constraints:
            severity = c.get("severity", "medium")
            ctype = c.get("constraint_type", "general")
            title = c.get("title", c.get("description", "")[:80])
            lines.append(f"- [{ctype}/{severity}] {title}")
        sections.append("## Constraints\n" + "\n".join(lines))

    # Stakeholders
    if stakeholders:
        lines = []
        for s in stakeholders[:8]:
            stype = s.get("stakeholder_type", "")
            influence = s.get("influence_level", "")
            lines.append(f"- {s.get('name', '')} ({stype}, {influence} influence)")
        sections.append("## Stakeholders\n" + "\n".join(lines))

    # Competitors
    if competitors:
        lines = []
        for comp in competitors[:6]:
            pos = comp.get("market_position", "")
            diff = comp.get("key_differentiator", "")
            line = f"- {comp['name']}"
            if pos:
                line += f" ({pos})"
            if diff:
                line += f": {diff[:100]}"
            lines.append(line)
        sections.append("## Competitors\n" + "\n".join(lines))

    return (
        "Synthesize the Project Context for this product.\n\n"
        + "\n\n".join(sections)
        + "\n\nReturn the JSON project context now."
    )


async def synthesize_project_context(project_id: UUID) -> dict:
    """
    Run the project context synthesis chain.

    Loads all project data, calls the LLM, and stores the result.

    Returns:
        Dict matching ProjectContext schema.
    """
    from app.db.canvas_synthesis import get_canvas_synthesis, upsert_canvas_synthesis
    from app.db.supabase_client import get_supabase

    settings = get_settings()
    client = get_supabase()

    # ---- Gather all BRD data ----

    # Project + company info
    project_result = client.table("projects").select(
        "id, name, vision, description"
    ).eq("id", str(project_id)).maybe_single().execute()
    project = project_result.data or {}

    company_info = {}
    try:
        ci_result = client.table("company_info").select(
            "name, industry, description, website, stage, size"
        ).eq("project_id", str(project_id)).maybe_single().execute()
        company_info = ci_result.data or {}
    except Exception:
        pass
    project["company_info"] = company_info

    # Personas
    personas_result = client.table("personas").select(
        "id, name, role, description, goals, pain_points, canvas_role, confirmation_status"
    ).eq("project_id", str(project_id)).execute()
    personas = personas_result.data or []

    # Features
    features_result = client.table("features").select(
        "id, name, overview, category, priority_group, confirmation_status, vp_step_id"
    ).eq("project_id", str(project_id)).execute()
    features = features_result.data or []

    # Workflows
    workflow_pairs = []
    try:
        from app.db.workflows import get_workflow_pairs
        workflow_pairs = get_workflow_pairs(project_id)
    except Exception:
        logger.debug("Could not load workflow pairs for context synthesis")

    # Business drivers
    drivers_result = client.table("business_drivers").select(
        "id, description, driver_type, severity"
    ).eq("project_id", str(project_id)).execute()
    business_drivers = drivers_result.data or []

    # Constraints
    constraints_result = client.table("constraints").select(
        "id, title, constraint_type, description, severity, confirmation_status"
    ).eq("project_id", str(project_id)).execute()
    constraints = constraints_result.data or []

    # Data entities
    de_result = client.table("data_entities").select(
        "id, name, entity_category, fields, description"
    ).eq("project_id", str(project_id)).execute()
    data_entities = de_result.data or []

    # Stakeholders
    stakeholders_result = client.table("stakeholders").select(
        "id, name, role, stakeholder_type, influence_level"
    ).eq("project_id", str(project_id)).execute()
    stakeholders = stakeholders_result.data or []

    # Competitors
    competitors = []
    try:
        comp_result = client.table("competitor_references").select(
            "id, name, category, market_position, key_differentiator"
        ).eq("project_id", str(project_id)).eq("reference_type", "competitor").execute()
        competitors = comp_result.data or []
    except Exception:
        pass

    # Count sources
    source_count = (
        len(personas) + len(features) + len(workflow_pairs)
        + len(business_drivers) + len(constraints) + len(data_entities)
        + len(stakeholders) + len(competitors)
    )

    # ---- Build prompt ----
    user_prompt = _build_context_prompt(
        project=project,
        personas=personas,
        features=features,
        workflow_pairs=workflow_pairs,
        constraints=constraints,
        data_entities=data_entities,
        stakeholders=stakeholders,
        competitors=competitors,
        business_drivers=business_drivers,
    )

    # ---- Call LLM ----
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage

    model = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        temperature=0.15,
        max_tokens=4096,
        api_key=settings.ANTHROPIC_API_KEY,
    )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]

    response = await model.ainvoke(messages)
    raw_output = response.content if isinstance(response.content, str) else str(response.content)

    # ---- Parse output ----
    parsed = parse_llm_json_dict(raw_output)

    context_data = {
        "product_vision": parsed.get("product_vision", ""),
        "target_users": parsed.get("target_users", ""),
        "core_value_proposition": parsed.get("core_value_proposition", ""),
        "key_workflows": parsed.get("key_workflows", ""),
        "data_landscape": parsed.get("data_landscape", ""),
        "technical_boundaries": parsed.get("technical_boundaries", ""),
        "design_principles": parsed.get("design_principles", ""),
        "assumptions": parsed.get("assumptions", []),
        "open_questions": parsed.get("open_questions", []),
        "source_count": source_count,
    }

    # ---- Store in canvas_synthesis with synthesis_type='project_context' ----
    result = upsert_canvas_synthesis(
        project_id=project_id,
        value_path=[context_data],  # Store as single-item list in value_path JSONB
        rationale=None,
        excluded_flows=[],
        source_workflow_ids=[],
        source_persona_ids=[str(p["id"]) for p in personas],
        synthesis_type="project_context",
    )

    logger.info(
        f"Synthesized project context for {project_id} from {source_count} sources",
        extra={"project_id": str(project_id), "source_count": source_count},
    )

    context_data["version"] = result.get("version", 1)
    context_data["generated_at"] = result.get("generated_at")
    context_data["is_stale"] = False

    return context_data
