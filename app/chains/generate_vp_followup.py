"""Generate a Turn 2 follow-up prompt for v0 to solidify value path flows.

After v0 builds the initial app (Turn 1), this chain creates a follow-up
prompt that instructs v0 to wire up realistic navigation through the value
path steps — ensuring each step is walkable, features have data-feature-id
coverage, and transitions between screens feel intentional.

Two-phase generation:
1. Build a VP template: ordered steps with actor, action, feature, and page hints
2. Opus reviews/enhances the template with Turn 1 context (what v0 actually built)
"""

import json
from typing import Any

from anthropic import Anthropic

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are a UX flow architect. Your job is to take a structured value-path template \
and transform it into a precise follow-up instruction for v0.dev.

The user will provide:
1. A VP step template — ordered steps describing the user journey
2. A list of features with IDs that should be present in the prototype
3. Optionally, a summary of what v0 built in Turn 1

Your output must be a SINGLE follow-up message to send to v0 that:

- References the specific pages/components v0 already built (if Turn 1 summary provided)
- Ensures every VP step has a corresponding navigable path in the prototype
- Adds `data-feature-id="{uuid}"` to every interactive element for each feature
- Creates realistic transitions between screens (e.g., clicking "Submit" on step 3 \
navigates to the step 4 page)
- Adds breadcrumb or progress indicators showing where the user is in the flow
- Uses realistic mock data that matches the persona names from the steps

Keep the instruction concrete and actionable. Reference specific file paths, component \
names, and routes where possible. Do NOT repeat the full app spec — only address flow \
solidification.

Output ONLY the follow-up prompt text (plain text, not JSON).
"""


def _build_vp_template(
    vp_steps: list[dict[str, Any]],
    features: list[dict[str, Any]],
) -> str:
    """Build a structured VP template from steps and features."""
    feature_map = {f["id"]: f.get("name", "Unknown") for f in features}

    lines = ["## Value Path Flow (ordered steps)\n"]
    sorted_steps = sorted(vp_steps, key=lambda s: s.get("step_index", 0))

    for step in sorted_steps:
        idx = step.get("step_index", "?")
        label = step.get("label", "Untitled Step")
        actor = step.get("actor_persona_name", "User")
        narrative = step.get("narrative_user", step.get("description", ""))
        features_used = step.get("features_used", [])

        feature_names = []
        for fid in features_used:
            name = feature_map.get(fid, fid)
            feature_names.append(f"{name} (data-feature-id=\"{fid}\")")

        lines.append(f"### Step {idx}: {label}")
        lines.append(f"- **Actor**: {actor}")
        lines.append(f"- **Action**: {narrative}")
        if feature_names:
            lines.append(f"- **Features**: {', '.join(feature_names)}")
        lines.append("")

    lines.append("## Feature ID Reference\n")
    for f in features:
        lines.append(f"- `{f['id']}` → {f.get('name', 'Unknown')}")

    return "\n".join(lines)


def generate_vp_followup(
    vp_steps: list[dict[str, Any]],
    features: list[dict[str, Any]],
    settings: Settings,
    turn1_summary: str | None = None,
    model_override: str | None = None,
) -> str:
    """Generate a Turn 2 follow-up prompt for v0 to solidify VP flows.

    Args:
        vp_steps: Ordered VP steps with step_index, label, actor, narrative
        features: Feature list with id and name for cross-reference
        settings: App settings
        turn1_summary: Optional summary of what v0 built in Turn 1
        model_override: Optional model override

    Returns:
        The follow-up prompt string to send to v0
    """
    model = model_override or settings.PROTOTYPE_PROMPT_MODEL
    logger.info(f"Generating VP followup prompt using {model}")

    vp_template = _build_vp_template(vp_steps, features)

    user_message = f"""## VP Step Template
{vp_template}

## Features ({len(features)} total)
{json.dumps([{"id": f["id"], "name": f.get("name", "")} for f in features], indent=2, default=str)}
"""

    if turn1_summary:
        user_message += f"""
## Turn 1 Summary (what v0 already built)
{turn1_summary}

Use the above to reference actual component names, file paths, and routes
that v0 created. Wire the VP flow through existing pages and components.
"""
    else:
        user_message += """
## Turn 1 Summary
Not available — generate the follow-up assuming standard Next.js page routes
and component naming conventions.
"""

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    followup = response.content[0].text
    logger.info(f"Generated VP followup prompt: {len(followup)} chars for {len(vp_steps)} steps")
    return followup
