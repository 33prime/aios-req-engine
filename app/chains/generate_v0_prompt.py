"""Generate a comprehensive v0.dev prompt from AIOS discovery data.

Uses Opus to transform features, personas, VP steps, and business context
into a detailed prompt that v0 can use to generate a prototype.
"""

import json
from typing import Any

from anthropic import Anthropic

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.schemas_prototypes import V0PromptOutput

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are a senior UI/UX architect specializing in converting product requirements into \
detailed prototyping prompts for v0.dev (an AI code generation tool).

Your task: Given a complete set of AIOS discovery data (features, personas, user flows, \
business context), generate a single comprehensive prompt that v0 will use to create a \
functional React + Tailwind prototype.

=== CRITICAL REQUIREMENTS FOR THE PROMPT YOU GENERATE ===

1. FEATURE TRACKING: Every interactive element MUST have a `data-feature-id="{uuid}"` \
attribute matching the AIOS feature UUID. This is how we link prototype UI to requirements.

2. HANDOFF.MD: The prompt MUST instruct v0 to create a HANDOFF.md file at the repo root with:
   - Feature inventory (name, ID, file path, component)
   - Page routes and what features appear on each
   - Mock data schema
   - Known limitations

3. FILE STRUCTURE: Instruct feature-based folder organization:
   ```
   src/
     components/
       {feature-name}/
         {FeatureName}.tsx
         {FeatureName}.test.tsx
     pages/
       ...
   ```

4. MOCK DATA: Generate realistic mock data matching the personas. Use names and scenarios \
from the persona definitions.

5. USER FLOWS: Define clear navigation paths based on VP steps. Each flow should be \
walkable in the prototype.

6. JSDoc ANNOTATIONS: Every component should have JSDoc with @feature-id and @description.

7. TECHNICAL STACK: React + Tailwind CSS. No backend — all data is mocked.

=== OUTPUT FORMAT ===
Output ONLY valid JSON with this structure:
{
  "prompt": "<the complete v0 prompt as a single string>",
  "features_included": ["<feature_id_1>", "<feature_id_2>", ...],
  "flows_included": ["<vp_step_label_1>", "<vp_step_label_2>", ...]
}
"""


def build_user_message(
    project: dict[str, Any],
    features: list[dict[str, Any]],
    personas: list[dict[str, Any]],
    vp_steps: list[dict[str, Any]],
    business_drivers: list[dict[str, Any]] | None = None,
    company_info: dict[str, Any] | None = None,
    design_preferences: dict[str, Any] | None = None,
    learnings: list[dict[str, Any]] | None = None,
) -> str:
    """Assemble user message from AIOS data."""
    sections = []

    # Project overview
    sections.append(f"## Project: {project.get('name', 'Unnamed')}")
    if project.get("description"):
        sections.append(f"Description: {project['description']}")

    # Company info
    if company_info:
        sections.append(f"\n## Company Context")
        sections.append(json.dumps(company_info, indent=2, default=str))

    # Design preferences
    if design_preferences:
        sections.append(f"\n## Design Preferences")
        sections.append(json.dumps(design_preferences, indent=2, default=str))

    # Personas
    sections.append(f"\n## Personas ({len(personas)})")
    for p in personas:
        persona_data = {
            "id": p.get("id"),
            "name": p.get("name"),
            "role": p.get("role"),
            "goals": p.get("goals", []),
            "pain_points": p.get("pain_points", []),
            "key_workflows": p.get("key_workflows", []),
        }
        sections.append(json.dumps(persona_data, indent=2, default=str))

    # Features
    sections.append(f"\n## Features ({len(features)})")
    for f in features:
        feature_data = {
            "id": f.get("id"),
            "name": f.get("name"),
            "category": f.get("category"),
            "is_mvp": f.get("is_mvp"),
            "overview": f.get("overview"),
            "user_actions": f.get("user_actions", []),
            "system_behaviors": f.get("system_behaviors", []),
            "ui_requirements": f.get("ui_requirements", []),
            "rules": f.get("rules", []),
        }
        sections.append(json.dumps(feature_data, indent=2, default=str))

    # VP Steps (user flow)
    sections.append(f"\n## User Journey ({len(vp_steps)} steps)")
    for step in sorted(vp_steps, key=lambda s: s.get("step_index", 0)):
        step_data = {
            "step_index": step.get("step_index"),
            "label": step.get("label"),
            "description": step.get("description"),
            "actor_persona_name": step.get("actor_persona_name"),
            "features_used": step.get("features_used", []),
            "narrative_user": step.get("narrative_user"),
        }
        sections.append(json.dumps(step_data, indent=2, default=str))

    # Business drivers
    if business_drivers:
        sections.append(f"\n## Business Drivers ({len(business_drivers)})")
        for bd in business_drivers:
            sections.append(f"- {bd.get('description', bd.get('name', ''))}")

    # Cross-project learnings
    if learnings:
        sections.append(f"\n## Prompt Learnings (from previous prototypes)")
        for l in learnings:
            sections.append(f"- [{l.get('category')}] {l.get('learning')}")

    return "\n".join(sections)


def generate_v0_prompt(
    project: dict[str, Any],
    features: list[dict[str, Any]],
    personas: list[dict[str, Any]],
    vp_steps: list[dict[str, Any]],
    settings: Settings,
    business_drivers: list[dict[str, Any]] | None = None,
    company_info: dict[str, Any] | None = None,
    design_preferences: dict[str, Any] | None = None,
    learnings: list[dict[str, Any]] | None = None,
    model_override: str | None = None,
) -> V0PromptOutput:
    """Generate a v0 prompt from AIOS discovery data.

    Args:
        project: Project record
        features: All features for the project
        personas: All personas for the project
        vp_steps: All VP steps for the project
        settings: App settings
        business_drivers: Optional business drivers
        company_info: Optional company info
        design_preferences: Optional design preferences
        learnings: Optional cross-project prompt learnings
        model_override: Optional model override

    Returns:
        V0PromptOutput with the complete prompt and metadata
    """
    model = model_override or settings.PROTOTYPE_PROMPT_MODEL
    logger.info(f"Generating v0 prompt using {model} for project {project.get('id')}")

    user_message = build_user_message(
        project=project,
        features=features,
        personas=personas,
        vp_steps=vp_steps,
        business_drivers=business_drivers,
        company_info=company_info,
        design_preferences=design_preferences,
        learnings=learnings,
    )

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    response_text = response.content[0].text.strip()
    if response_text.startswith("```json"):
        response_text = response_text[len("```json") :]
    if response_text.startswith("```"):
        response_text = response_text[len("```") :]
    if response_text.endswith("```"):
        response_text = response_text[: -len("```")]
    parsed = json.loads(response_text.strip())
    output = V0PromptOutput(**parsed)

    logger.info(
        f"Generated v0 prompt: {len(output.prompt)} chars, "
        f"{len(output.features_included)} features, {len(output.flows_included)} flows"
    )
    return output
