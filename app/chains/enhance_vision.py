"""Enhance project vision statement using LLM."""

import logging
from uuid import UUID

from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

ENHANCEMENT_PROMPTS = {
    "enhance": "Expand and strengthen this vision statement. Add specificity about outcomes, differentiation, and impact while preserving the core intent. Keep it under 3 sentences.",
    "simplify": "Simplify this vision statement to be clear and concise. Remove jargon and complex language. Aim for one powerful sentence that anyone can understand.",
    "metrics": "Add measurable outcomes and success indicators to this vision statement. Include specific targets or timeframes where the context supports them.",
    "professional": "Rewrite this vision statement in a polished, executive-ready tone. Make it suitable for board presentations and investor communications.",
}


async def enhance_vision(project_id: UUID, enhancement_type: str) -> str:
    """Enhance a project vision statement using Haiku 4.5.

    Args:
        project_id: The project UUID
        enhancement_type: One of 'enhance', 'simplify', 'metrics', 'professional'

    Returns:
        Enhanced vision text
    """
    if enhancement_type not in ENHANCEMENT_PROMPTS:
        raise ValueError(f"Invalid enhancement type: {enhancement_type}")

    client = get_supabase()

    # Load current vision
    project = client.table("projects").select("vision, name").eq("id", str(project_id)).single().execute()
    if not project.data or not project.data.get("vision"):
        raise ValueError("No vision statement to enhance")

    current_vision = project.data["vision"]
    project_name = project.data.get("name", "the project")

    # Load top features for context
    features = (
        client.table("features")
        .select("name, priority_group")
        .eq("project_id", str(project_id))
        .limit(10)
        .execute()
    )
    feature_context = ""
    if features.data:
        must_have = [f["name"] for f in features.data if f.get("priority_group") == "must_have"]
        if must_have:
            feature_context = f"\nKey features: {', '.join(must_have[:5])}"

    # Load top goals/pains for context
    drivers = (
        client.table("business_drivers")
        .select("description, driver_type")
        .eq("project_id", str(project_id))
        .in_("driver_type", ["goal", "pain"])
        .limit(6)
        .execute()
    )
    driver_context = ""
    if drivers.data:
        goals = [d["description"] for d in drivers.data if d["driver_type"] == "goal"][:3]
        pains = [d["description"] for d in drivers.data if d["driver_type"] == "pain"][:3]
        if goals:
            driver_context += f"\nBusiness goals: {'; '.join(goals)}"
        if pains:
            driver_context += f"\nKey pains: {'; '.join(pains)}"

    # Load constraints
    constraints = (
        client.table("constraints")
        .select("title, constraint_type, severity")
        .eq("project_id", str(project_id))
        .in_("severity", ["critical", "high"])
        .limit(4)
        .execute()
    )
    constraint_context = ""
    if constraints.data:
        constraint_context = f"\nCritical constraints: {'; '.join(c['title'] for c in constraints.data)}"

    prompt = f"""You are a business requirements consultant enhancing a vision statement for {project_name}.

Current vision: "{current_vision}"

Context:{feature_context}{driver_context}{constraint_context}

Task: {ENHANCEMENT_PROMPTS[enhancement_type]}

Return ONLY the enhanced vision text, no quotes, no preamble, no explanation."""

    import anthropic

    ai_client = anthropic.Anthropic()
    response = ai_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text.strip()
