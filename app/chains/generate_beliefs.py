"""Generate core beliefs about why a solution matters to the client.

Beliefs connect pain points, goals, and stakeholder context to specific features
or workflow outcomes. Generated via Haiku 3.5 (fast, cheap — beliefs are simple
synthesis). Each belief is stored as a memory_node with node_type='belief'.
"""

import json
import time

from app.core.config import get_settings
from app.core.llm_usage import log_llm_usage
from app.core.logging import get_logger

logger = get_logger(__name__)

HAIKU_MODEL = "claude-3-5-haiku-20241022"

BELIEFS_SYSTEM = """You generate core beliefs about why a solution matters to a client. Each belief connects a real pain point, goal, or stakeholder need to a specific feature or workflow outcome.

## Rules
- Generate 3-5 beliefs, each a single confident statement (1-2 sentences)
- Frame positively — what succeeds, what improves, what becomes possible
- Be specific — reference actual features, workflows, and stakeholder names from the context
- Each belief should have a different domain (user_experience, business_value, technical, strategic, operational)
- Confidence: 0.6-0.9 (these are synthesized, not directly confirmed)

## Output
Return a JSON object:
{
  "beliefs": [
    {
      "statement": "The automated scheduling workflow will eliminate the 3-hour weekly planning bottleneck Sarah flagged, freeing the ops team to focus on exception handling.",
      "confidence": 0.8,
      "domain": "operational",
      "linked_entity_type": "feature|persona|workflow|stakeholder",
      "linked_entity_name": "Name of the entity this belief relates to most"
    }
  ]
}

No markdown fences. Just the JSON."""

BELIEFS_USER = """<project_name>{project_name}</project_name>

<features>
{features}
</features>

<pain_points>
{pain_points}
</pain_points>

<goals>
{goals}
</goals>

<workflows>
{workflows}
</workflows>

<stakeholders>
{stakeholders}
</stakeholders>

Generate 3-5 core beliefs about why this solution matters to the client. Be specific and reference actual entities from the context."""


async def generate_beliefs(
    project_name: str,
    features: list[dict],
    pain_points: list[dict],
    goals: list[dict],
    workflows: list[dict],
    stakeholders: list[str],
    project_id: str | None = None,
) -> list[dict]:
    """Generate core beliefs via Haiku 3.5.

    Returns:
        List of {statement, confidence, domain, linked_entity_type, linked_entity_name}
    """
    from anthropic import AsyncAnthropic

    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Format features
    feature_lines = []
    for f in features[:15]:
        name = f.get("name", "Unnamed")
        overview = f.get("overview") or f.get("description") or ""
        feature_lines.append(f"- {name}: {overview[:120]}")
    features_text = "\n".join(feature_lines) if feature_lines else "No features yet."

    # Format pain points
    pain_lines = [f"- {p.get('description', '')[:120]}" for p in pain_points[:10]]
    pain_text = "\n".join(pain_lines) if pain_lines else "No pain points documented."

    # Format goals
    goal_lines = [f"- {g.get('description', '')[:120]}" for g in goals[:10]]
    goals_text = "\n".join(goal_lines) if goal_lines else "No goals documented."

    # Format workflows
    wf_lines = []
    for w in workflows[:8]:
        name = w.get("name", "Unnamed")
        steps = w.get("current_steps") or []
        step_names = [s.get("label", "step") for s in steps[:4]]
        wf_lines.append(f"- {name}: {', '.join(step_names)}")
    workflows_text = "\n".join(wf_lines) if wf_lines else "No workflows defined."

    stakeholders_text = ", ".join(stakeholders[:8]) if stakeholders else "None identified"

    user_message = BELIEFS_USER.format(
        project_name=project_name,
        features=features_text,
        pain_points=pain_text,
        goals=goals_text,
        workflows=workflows_text,
        stakeholders=stakeholders_text,
    )

    start = time.time()
    response = await client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=1024,
        temperature=0.4,
        system=[
            {
                "type": "text",
                "text": BELIEFS_SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_message}],
    )
    duration_ms = int((time.time() - start) * 1000)

    usage = response.usage
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    cache_create = getattr(usage, "cache_creation_input_tokens", 0) or 0

    log_llm_usage(
        workflow="generate_beliefs",
        model=HAIKU_MODEL,
        provider="anthropic",
        tokens_input=usage.input_tokens,
        tokens_output=usage.output_tokens,
        duration_ms=duration_ms,
        chain="generate_beliefs",
        project_id=project_id,
        tokens_cache_read=cache_read,
        tokens_cache_create=cache_create,
    )

    # Parse response
    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        result = json.loads(text)
        return result.get("beliefs", [])
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse beliefs JSON: {e}")
        return []
