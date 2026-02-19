"""
Propose Entity Updates Chain

Takes gap analysis output and generates proposals to fill identified gaps.
Creates proposals for features, personas, and VP steps using the existing proposal system.
Uses Claude Sonnet 4 for intelligent proposal generation.
"""

import json
from typing import Any
from uuid import UUID, uuid4

from anthropic import Anthropic

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.features import list_features
from app.db.personas import list_personas
from app.db.proposals import create_proposal
from app.db.vp import list_vp_steps

logger = get_logger(__name__)

PROPOSE_UPDATES_PROMPT = """You are a requirements architect generating proposals to fill gaps in a software project.

## Gap Analysis Results

{gap_analysis_json}

## Current Project State

### Features ({feature_count} total)
{features_summary}

### Personas ({persona_count} total)
{personas_summary}

### Value Path Steps ({vp_step_count} total)
{vp_steps_summary}

## Project Stage Context

Current stage: {project_stage}
- Discovery: Focus on core entities, keep it simple
- Requirements: Full detail, MVP prioritization
- Design: Refinement, cross-references important
- Later: Conservative, only critical updates

## Your Task

Generate specific proposals to address the most important gaps. For each proposal:
1. Be specific - include actual field values, not placeholders
2. Reference existing entities by ID where applicable
3. Prioritize high-severity gaps
4. Respect the project stage - don't over-engineer early

{entity_type_filter}

## Output Format

Return a JSON object with proposals:
{{
    "proposals": [
        {{
            "entity_type": "feature" | "persona" | "vp_step",
            "operation": "create" | "update",
            "priority": "high" | "medium" | "low",
            "gap_addressed": "Description of which gap this addresses",
            "rationale": "Why this proposal helps",
            "entity_id": "UUID for updates, null for creates",
            "changes": {{
                // For features:
                "name": "Feature name",
                "overview": "What it does",
                "category": "core|support|nice_to_have",
                "is_mvp": true|false,
                "target_personas": ["persona_id_1"],

                // For personas:
                "name": "Persona name",
                "role": "Their role",
                "pain_points": ["pain 1", "pain 2"],
                "goals": ["goal 1"],

                // For vp_steps:
                "label": "Step label",
                "description": "What happens",
                "step_index": number,
                "actor_persona_id": "persona_id",
                "features_used": ["feature_id_1"]
            }}
        }}
    ],
    "summary": {{
        "total_proposals": number,
        "creates": number,
        "updates": number,
        "by_entity_type": {{"feature": 0, "persona": 0, "vp_step": 0}},
        "gaps_addressed": number,
        "gaps_remaining": number
    }}
}}

Generate a maximum of {max_proposals} proposals, prioritizing by severity.
Return ONLY valid JSON. Do not include any explanation or markdown code fences.
"""


async def propose_entity_updates(
    project_id: UUID,
    gap_analysis: dict[str, Any],
    max_proposals: int = 5,
    entity_types: list[str] | None = None,
    project_stage: str = "requirements",
    auto_create_proposals: bool = True,
) -> dict[str, Any]:
    """
    Generate proposals to fill identified requirement gaps.

    Args:
        project_id: Project UUID
        gap_analysis: Output from analyze_requirements_gaps
        max_proposals: Maximum number of proposals to generate (default: 5)
        entity_types: Filter to specific entity types (feature, persona, vp_step)
        project_stage: Current project stage for context
        auto_create_proposals: Whether to create proposals in DB (default: True)

    Returns:
        Dict with:
        - success: bool
        - proposals: list of generated proposals
        - proposals_created: list of created proposal IDs (if auto_create_proposals)
        - summary: summary statistics
    """
    settings = get_settings()
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    try:
        # Validate gap analysis input
        gaps = gap_analysis.get("gaps", [])
        if not gaps:
            return {
                "success": True,
                "proposals": [],
                "proposals_created": [],
                "summary": {
                    "total_proposals": 0,
                    "message": "No gaps to address",
                },
            }

        # Gather current state for context
        features = list_features(project_id)
        personas = list_personas(project_id)
        vp_steps = list_vp_steps(project_id)

        # Build summaries
        features_summary = _build_features_summary(features)
        personas_summary = _build_personas_summary(personas)
        vp_steps_summary = _build_vp_steps_summary(vp_steps)

        # Build entity type filter instruction
        entity_type_filter = ""
        if entity_types:
            entity_type_filter = f"\n**Entity Type Filter**: Only generate proposals for: {', '.join(entity_types)}\n"

        # Build prompt
        prompt = PROPOSE_UPDATES_PROMPT.format(
            gap_analysis_json=json.dumps(gap_analysis, indent=2),
            feature_count=len(features),
            features_summary=features_summary or "No features defined yet.",
            persona_count=len(personas),
            personas_summary=personas_summary or "No personas defined yet.",
            vp_step_count=len(vp_steps),
            vp_steps_summary=vp_steps_summary or "No value path steps defined yet.",
            project_stage=project_stage,
            entity_type_filter=entity_type_filter,
            max_proposals=max_proposals,
        )

        # Call Claude Sonnet 4 for proposal generation
        logger.info(
            f"Generating entity update proposals for project {project_id}",
            extra={"gap_count": len(gaps), "max_proposals": max_proposals},
        )

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            temperature=0.3,  # Slightly more creative for proposals
            messages=[{"role": "user", "content": prompt}],
            output_config={"effort": "medium"},
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
            logger.error(f"Failed to parse proposal generation response: {e}")
            return {
                "success": False,
                "error": f"JSON parse error: {e}",
                "proposals": [],
                "proposals_created": [],
                "summary": {},
            }

        proposals = result.get("proposals", [])
        proposals_created = []

        # Create proposals in the database if requested
        if auto_create_proposals and proposals:
            for proposal_data in proposals:
                try:
                    created = _create_proposal_from_data(project_id, proposal_data)
                    if created:
                        proposals_created.append(created)
                except Exception as e:
                    logger.warning(f"Failed to create proposal: {e}")

        logger.info(
            f"Entity update proposals generated for project {project_id}",
            extra={
                "proposals_generated": len(proposals),
                "proposals_created": len(proposals_created),
            },
        )

        return {
            "success": True,
            "proposals": proposals,
            "proposals_created": proposals_created,
            "summary": result.get("summary", {}),
        }

    except Exception as e:
        logger.error(f"Proposal generation failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "proposals": [],
            "proposals_created": [],
            "summary": {},
        }


def _create_proposal_from_data(project_id: UUID, proposal_data: dict) -> dict | None:
    """
    Create a proposal in the database from the LLM-generated proposal data.

    Args:
        project_id: Project UUID
        proposal_data: Proposal data from LLM

    Returns:
        Created proposal dict or None if failed
    """
    entity_type = proposal_data.get("entity_type")
    operation = proposal_data.get("operation", "create")
    changes = proposal_data.get("changes", {})
    rationale = proposal_data.get("rationale", "")
    gap_addressed = proposal_data.get("gap_addressed", "")
    entity_id = proposal_data.get("entity_id")

    if not entity_type or not changes:
        logger.warning("Invalid proposal data - missing entity_type or changes")
        return None

    # Build the change structure for the proposal system
    proposal_changes = [
        {
            "entity_type": entity_type,
            "operation": operation,
            "entity_id": entity_id,
            "before": None if operation == "create" else {},  # Would need to fetch for updates
            "after": changes,
            "evidence": [],  # Gap analysis is the evidence
            "rationale": f"{gap_addressed}\n\n{rationale}",
        }
    ]

    # Build title
    title = f"Fill gap: {gap_addressed[:50]}..." if len(gap_addressed) > 50 else f"Fill gap: {gap_addressed}"

    try:
        proposal = create_proposal(
            project_id=project_id,
            conversation_id=None,
            title=title,
            description=f"Generated by DI Agent requirements gap analysis.\n\n{rationale}",
            proposal_type=entity_type,  # 'feature', 'persona', or 'vp_step'
            changes=proposal_changes,
            user_request=None,
            context_snapshot=None,
            created_by="di_agent",
        )
        return proposal
    except Exception as e:
        logger.error(f"Failed to create proposal: {e}")
        return None


def _build_features_summary(features: list[dict]) -> str:
    """Build a summary of features for the prompt."""
    if not features:
        return ""

    lines = []
    for f in features[:20]:  # Limit to 20 for context window
        name = f.get("name", "Unnamed")
        feature_id = f.get("id", "?")
        category = f.get("category", "uncategorized")
        is_mvp = f.get("is_mvp", False)
        target_personas = f.get("target_personas", [])

        lines.append(
            f"- [{feature_id}] {name} (category={category}, mvp={is_mvp}, "
            f"personas={target_personas if target_personas else 'none'})"
        )

    return "\n".join(lines)


def _build_personas_summary(personas: list[dict]) -> str:
    """Build a summary of personas for the prompt."""
    if not personas:
        return ""

    lines = []
    for p in personas[:10]:  # Limit to 10
        name = p.get("name", "Unnamed")
        persona_id = p.get("id", "?")
        role = p.get("role", "Unknown")
        pain_points = p.get("pain_points", [])

        lines.append(
            f"- [{persona_id}] {name} ({role}) - {len(pain_points)} pain points"
        )

    return "\n".join(lines)


def _build_vp_steps_summary(vp_steps: list[dict]) -> str:
    """Build a summary of VP steps for the prompt."""
    if not vp_steps:
        return ""

    lines = []
    for step in sorted(vp_steps, key=lambda x: x.get("step_index", 0))[:15]:  # Limit to 15
        step_id = step.get("id", "?")
        step_index = step.get("step_index", 0)
        label = step.get("label", "Untitled")
        actor = step.get("actor_persona_id") or "unassigned"

        lines.append(
            f"- Step {step_index} [{step_id}]: {label} (actor={actor})"
        )

    return "\n".join(lines)
