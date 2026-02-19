"""
Analyze Requirements Gaps Chain

Analyzes the current requirements model (features, personas, VP steps) for logical gaps,
missing references, and inconsistencies. Uses Claude Sonnet 4 for intelligent analysis.
"""

import json
from typing import Any
from uuid import UUID

from anthropic import Anthropic

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.features import list_features
from app.db.personas import list_personas
from app.db.vp import list_vp_steps

logger = get_logger(__name__)

REQUIREMENTS_GAP_ANALYSIS_PROMPT = """You are a requirements analyst checking a software project for logical gaps and inconsistencies.

## Current Project State

### Features ({feature_count} total)
{features_summary}

### Personas ({persona_count} total)
{personas_summary}

### Value Path Steps ({vp_step_count} total)
{vp_steps_summary}

## Your Task

Analyze this requirements model for gaps and inconsistencies. Check for:

1. **VP→Feature References**: VP steps reference features - are those features actually defined?
2. **Persona Pain Coverage**: Do features address the pain points defined in personas?
3. **Feature→Persona Coverage**: Do features have target personas? Do those personas exist?
4. **VP Flow Continuity**: Are VP steps properly sequenced? Any gaps in the user journey?
5. **Missing Actors**: Do VP steps reference personas that don't exist?
6. **Orphaned Entities**: Features not used in any VP step? Personas not targeted by any feature?
7. **Incomplete Definitions**: Features missing key fields? Personas without pain points?

{focus_instruction}

## Output Format

Return a JSON object with this structure:
{{
    "gaps": [
        {{
            "gap_type": "missing_feature_reference" | "orphaned_feature" | "orphaned_persona" | "missing_persona_reference" | "incomplete_feature" | "incomplete_persona" | "vp_flow_gap" | "pain_point_not_addressed",
            "severity": "high" | "medium" | "low",
            "entity_type": "feature" | "persona" | "vp_step",
            "entity_id": "uuid or null if general gap",
            "entity_name": "name of the entity",
            "description": "Clear description of what's missing or wrong",
            "suggestion": "Specific suggestion to fix this gap"
        }}
    ],
    "summary": {{
        "total_gaps": number,
        "high_severity": number,
        "medium_severity": number,
        "low_severity": number,
        "most_critical_area": "feature" | "persona" | "vp_step" | "none",
        "overall_completeness": "good" | "moderate" | "needs_work" | "incomplete"
    }},
    "recommendations": [
        "Prioritized list of actions to improve requirements completeness"
    ]
}}

Return ONLY valid JSON. Do not include any explanation or markdown code fences.
"""


async def analyze_requirements_gaps(
    project_id: UUID,
    focus_areas: list[str] | None = None,
) -> dict[str, Any]:
    """
    Analyze the current requirements model for logical gaps.

    Args:
        project_id: Project UUID
        focus_areas: Optional list of areas to focus on:
            - "persona_coverage" - Check if features cover persona pain points
            - "vp_flow" - Check VP step continuity and references
            - "feature_references" - Check if VP steps reference valid features
            - "orphaned_entities" - Find entities not used anywhere

    Returns:
        Dict with:
        - success: bool
        - gaps: list of gap objects
        - summary: summary statistics
        - recommendations: prioritized actions
    """
    settings = get_settings()
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    try:
        # Gather current state
        features = list_features(project_id)
        personas = list_personas(project_id)
        vp_steps = list_vp_steps(project_id)

        # Build summaries for the prompt
        features_summary = _build_features_summary(features)
        personas_summary = _build_personas_summary(personas)
        vp_steps_summary = _build_vp_steps_summary(vp_steps)

        # Build focus instruction
        focus_instruction = ""
        if focus_areas:
            focus_instruction = f"\n**Focus Areas**: Prioritize analysis of: {', '.join(focus_areas)}\n"

        # Build prompt
        prompt = REQUIREMENTS_GAP_ANALYSIS_PROMPT.format(
            feature_count=len(features),
            features_summary=features_summary or "No features defined yet.",
            persona_count=len(personas),
            personas_summary=personas_summary or "No personas defined yet.",
            vp_step_count=len(vp_steps),
            vp_steps_summary=vp_steps_summary or "No value path steps defined yet.",
            focus_instruction=focus_instruction,
        )

        # Call Claude Sonnet 4 for analysis
        logger.info(f"Analyzing requirements gaps for project {project_id}")

        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            temperature=0.2,  # Lower temperature for more consistent analysis
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = response.content[0].text if response.content else ""

        # Parse JSON response
        try:
            # Handle potential markdown code fences
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            result = json.loads(response_text.strip())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse gap analysis response: {e}")
            return {
                "success": False,
                "error": f"JSON parse error: {e}",
                "gaps": [],
                "summary": {},
                "recommendations": [],
            }

        logger.info(
            f"Requirements gap analysis complete for project {project_id}",
            extra={
                "total_gaps": result.get("summary", {}).get("total_gaps", 0),
                "high_severity": result.get("summary", {}).get("high_severity", 0),
            },
        )

        return {
            "success": True,
            "gaps": result.get("gaps", []),
            "summary": result.get("summary", {}),
            "recommendations": result.get("recommendations", []),
            "entities_analyzed": {
                "features": len(features),
                "personas": len(personas),
                "vp_steps": len(vp_steps),
            },
        }

    except Exception as e:
        logger.error(f"Requirements gap analysis failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "gaps": [],
            "summary": {},
            "recommendations": [],
        }


def _build_features_summary(features: list[dict]) -> str:
    """Build a summary of features for the prompt."""
    if not features:
        return ""

    lines = []
    for f in features:
        name = f.get("name", "Unnamed")
        feature_id = f.get("id", "?")
        category = f.get("category", "uncategorized")
        is_mvp = f.get("is_mvp", False)
        overview = f.get("overview", "")[:100] if f.get("overview") else ""
        target_personas = f.get("target_personas", [])

        # Get linked persona names if available
        persona_info = ""
        if target_personas:
            if isinstance(target_personas, list) and len(target_personas) > 0:
                persona_info = f" | Personas: {', '.join(str(p) for p in target_personas[:3])}"

        lines.append(
            f"- [{feature_id[:8]}] {name} ({category}, MVP={is_mvp}){persona_info}"
            f"{' | ' + overview if overview else ''}"
        )

    return "\n".join(lines)


def _build_personas_summary(personas: list[dict]) -> str:
    """Build a summary of personas for the prompt."""
    if not personas:
        return ""

    lines = []
    for p in personas:
        name = p.get("name", "Unnamed")
        persona_id = p.get("id", "?")
        role = p.get("role", "Unknown role")
        pain_points = p.get("pain_points", [])
        goals = p.get("goals", [])

        pain_count = len(pain_points) if isinstance(pain_points, list) else 0
        goal_count = len(goals) if isinstance(goals, list) else 0

        lines.append(
            f"- [{persona_id[:8]}] {name} - {role} | {pain_count} pain points, {goal_count} goals"
        )

    return "\n".join(lines)


def _build_vp_steps_summary(vp_steps: list[dict]) -> str:
    """Build a summary of VP steps for the prompt."""
    if not vp_steps:
        return ""

    lines = []
    for step in sorted(vp_steps, key=lambda x: x.get("step_index", 0)):
        step_id = step.get("id", "?")
        step_index = step.get("step_index", 0)
        label = step.get("label", "Untitled")
        description = step.get("description", "")[:80] if step.get("description") else ""

        # Check for feature references in enrichment
        enrichment = step.get("enrichment", {}) or {}
        features_used = enrichment.get("features_used", [])
        actor_persona = enrichment.get("actor_persona_id") or step.get("actor_persona_id")

        feature_info = f" | Features: {', '.join(str(f) for f in features_used[:3])}" if features_used else ""
        actor_info = f" | Actor: {actor_persona}" if actor_persona else ""

        lines.append(
            f"- Step {step_index} [{step_id[:8]}]: {label}{actor_info}{feature_info}"
            f"{' | ' + description if description else ''}"
        )

    return "\n".join(lines)
