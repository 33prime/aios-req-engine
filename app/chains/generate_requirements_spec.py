"""Generate a comprehensive requirements specification document.

Triggered when readiness >= 85% or after session 3, producing a complete
Markdown requirements document from all AIOS data plus session insights.
"""

import json
from typing import Any

from anthropic import Anthropic

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are a senior requirements engineer producing a comprehensive requirements \
specification from prototype refinement sessions. Write a professional, structured \
Markdown document.

The document MUST include these sections:
1. **Executive Summary** — Project overview, scope, key stakeholders
2. **User Personas** — Each persona with goals, pain points, key workflows
3. **User Flows** — End-to-end journeys through the system (from VP steps)
4. **Feature Requirements** — Each feature with:
   - Description and rationale
   - Acceptance criteria (from confirmed requirements)
   - Business rules (with confidence levels)
   - Data requirements
   - UI requirements
   - Dependencies
5. **Data Model** — Entities, relationships, key fields
6. **Integrations** — External systems, APIs, data flows
7. **Non-Functional Requirements** — Performance, security, accessibility, compliance
8. **Open Questions** — Remaining unknowns with suggested owners

Be thorough but concise. Use tables where they aid clarity. Reference specific \
feature IDs for traceability.

Output the complete Markdown document.
"""


def generate_requirements_spec(
    project: dict[str, Any],
    features: list[dict[str, Any]],
    personas: list[dict[str, Any]],
    vp_steps: list[dict[str, Any]],
    overlays: list[dict[str, Any]],
    synthesis_results: list[dict[str, Any]],
    unanswered_questions: list[dict[str, Any]],
    settings: Settings,
    model_override: str | None = None,
) -> str:
    """Generate a full requirements specification document.

    Args:
        project: Project record
        features: All features with enrichment data
        personas: All personas
        vp_steps: All VP steps
        overlays: Feature overlay data from prototype analysis
        synthesis_results: Feedback synthesis from all sessions
        unanswered_questions: Questions that remain unanswered
        settings: App settings
        model_override: Optional model override

    Returns:
        Markdown requirements specification
    """
    model = model_override or settings.PROTOTYPE_PROMPT_MODEL  # Use Opus for quality
    logger.info(f"Generating requirements spec using {model}")

    user_message = f"""## Project: {project.get("name", "Unnamed")}
{project.get("description", "")}

## Personas ({len(personas)})
{json.dumps(personas, indent=2, default=str)[:4000]}

## Features ({len(features)})
{json.dumps(features, indent=2, default=str)[:6000]}

## User Journey ({len(vp_steps)} steps)
{json.dumps(sorted(vp_steps, key=lambda s: s.get("step_index", 0)), indent=2, default=str)[:4000]}

## Feature Overlay Analysis ({len(overlays)} features analyzed)
{json.dumps(overlays, indent=2, default=str)[:4000]}

## Session Feedback Synthesis ({len(synthesis_results)} sessions)
{json.dumps(synthesis_results, indent=2, default=str)[:4000]}

## Unanswered Questions ({len(unanswered_questions)})
{json.dumps(unanswered_questions, indent=2, default=str)[:2000]}

Generate the complete requirements specification document.
"""

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    spec = response.content[0].text
    logger.info(f"Generated requirements spec: {len(spec)} chars")
    return spec
