"""Value Path v2 generation chain.

Generates the "golden path" narrative from enriched features and personas.
This creates a consultant-friendly demo script showing:
- User narrative (what the user experiences)
- System narrative (what happens behind the scenes)
- Value created at each step
- Evidence supporting each step
"""

import json
from typing import Any
from uuid import UUID

from openai import OpenAI
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.schemas_vp_v2 import GenerateVPV2Output, VPStepV2
from app.db.features import list_features
from app.db.personas import list_personas
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


SYSTEM_PROMPT = """You are a requirements consultant creating a Value Path - a "golden path" narrative that shows how a product creates value through a sequence of steps.

You will receive:
1. Enriched features with user_actions, system_behaviors, rules, integrations
2. Personas with key_workflows showing how they use features
3. Evidence from client signals

Your job is to synthesize this into a coherent VALUE PATH - the optimal journey through the product that maximizes value creation.

You MUST output ONLY valid JSON matching this exact schema:

{
  "project_id": "uuid",
  "steps": [
    {
      "step_index": 1,
      "label": "Short step name (e.g., 'Client Needs Analysis')",
      "actor_persona_id": "uuid or null",
      "actor_persona_name": "Name of the primary persona for this step",
      "narrative_user": "2-4 sentences describing what the user experiences. Write as if narrating a demo: 'The sales rep opens the app and sees...'",
      "narrative_system": "Bullet points of what happens behind the scenes:\\n• System validates client data\\n• Audio recording starts\\n• Data syncs to cloud",
      "value_created": "One sentence: the outcome/value of this step",
      "features_used": [
        {"feature_id": "uuid", "feature_name": "Feature Name", "role": "core|supporting"}
      ],
      "rules_applied": ["Business rules active during this step"],
      "integrations_triggered": ["External systems used"],
      "ui_highlights": ["Key UI elements shown"],
      "evidence": [
        {
          "chunk_id": "uuid or null",
          "excerpt": "Quote from signal",
          "source_type": "signal|research|inferred",
          "rationale": "Why this evidence is relevant"
        }
      ],
      "has_signal_evidence": true
    }
  ],
  "generation_summary": "Summary of the value path and what it covers",
  "gaps_identified": ["List any gaps: missing evidence, unclear steps, etc."],
  "schema_version": "vp_v2"
}

CRITICAL RULES:
1. Output ONLY the JSON object, no markdown, no explanation.
2. Steps should flow logically - this is a DEMO SCRIPT a consultant can read.
3. narrative_user should be warm and descriptive - paint a picture.
4. narrative_system should be bullet points (use \\n• for each bullet).
5. A step can span multiple features if they're used together.
6. Prefer evidence from signals (source_type: "signal") over inferred.
7. If a step has signal evidence, set has_signal_evidence: true.
8. Identify gaps honestly - this helps consultants know what needs work.
9. The value path should cover MVP features first, then supporting features.
10. Each step should have a clear value_created - why does this step matter?"""


def _build_generation_prompt(
    project_id: UUID,
    features: list[dict[str, Any]],
    personas: list[dict[str, Any]],
) -> str:
    """Build the prompt for VP generation."""
    prompt_parts = [
        "# Value Path Generation",
        "",
        "Generate a Value Path (golden path) from the following enriched data.",
        "",
    ]

    # Add personas with workflows
    prompt_parts.append("## Personas & Workflows")
    for persona in personas:
        prompt_parts.append(f"\n### {persona.get('name', 'Unknown')} (ID: {persona.get('id')})")
        if persona.get('role'):
            prompt_parts.append(f"Role: {persona.get('role')}")
        if persona.get('overview'):
            prompt_parts.append(f"Overview: {persona.get('overview')[:300]}")

        # Key workflows are crucial for understanding the flow
        workflows = persona.get('key_workflows', [])
        if workflows:
            prompt_parts.append("\nKey Workflows:")
            for wf in workflows:
                prompt_parts.append(f"  **{wf.get('name', 'Unnamed')}**: {wf.get('description', '')}")
                steps = wf.get('steps', [])
                if steps:
                    for step in steps[:6]:
                        prompt_parts.append(f"    - {step}")
                features_used = wf.get('features_used', [])
                if features_used:
                    prompt_parts.append(f"    Features: {', '.join(features_used[:5])}")
    prompt_parts.append("")

    # Add features with enrichment
    prompt_parts.append("## Features (Enriched)")
    mvp_features = [f for f in features if f.get('is_mvp')]
    other_features = [f for f in features if not f.get('is_mvp')]

    prompt_parts.append("\n### MVP Features (prioritize these)")
    for feature in mvp_features:
        _add_feature_to_prompt(prompt_parts, feature)

    if other_features:
        prompt_parts.append("\n### Supporting Features")
        for feature in other_features[:5]:  # Limit to avoid token overflow
            _add_feature_to_prompt(prompt_parts, feature)
    prompt_parts.append("")

    # Instructions
    prompt_parts.extend([
        "## Instructions",
        f"- Project ID: {project_id}",
        "- Create a coherent value path (5-10 steps typically)",
        "- Each step should flow naturally to the next",
        "- Focus on MVP features first",
        "- Include evidence where available (prefer signal-based)",
        "- Write narrative_user as a demo script",
        "- Write narrative_system as bullet points",
        "- Identify gaps (missing evidence, unclear value, etc.)",
        "",
        "Output ONLY valid JSON matching the schema.",
    ])

    return "\n".join(prompt_parts)


def _add_feature_to_prompt(prompt_parts: list, feature: dict) -> None:
    """Add a feature's details to the prompt."""
    prompt_parts.append(f"\n**{feature.get('name', 'Unknown')}** (ID: {feature.get('id')})")
    prompt_parts.append(f"Category: {feature.get('category', 'General')}")

    if feature.get('overview'):
        prompt_parts.append(f"Overview: {feature.get('overview')[:200]}")

    # Target personas
    target_personas = feature.get('target_personas', [])
    if target_personas:
        personas_str = ", ".join([
            f"{tp.get('persona_name')} ({tp.get('role')})"
            for tp in target_personas[:3]
        ])
        prompt_parts.append(f"Used by: {personas_str}")

    # User actions
    user_actions = feature.get('user_actions', [])
    if user_actions:
        prompt_parts.append("User Actions:")
        for action in user_actions[:4]:
            prompt_parts.append(f"  - {action}")

    # System behaviors
    system_behaviors = feature.get('system_behaviors', [])
    if system_behaviors:
        prompt_parts.append("System Behaviors:")
        for behavior in system_behaviors[:4]:
            prompt_parts.append(f"  - {behavior}")

    # Rules
    rules = feature.get('rules', [])
    if rules:
        prompt_parts.append(f"Rules: {', '.join(rules[:3])}")

    # Integrations
    integrations = feature.get('integrations', [])
    if integrations:
        prompt_parts.append(f"Integrations: {', '.join(integrations)}")

    # Evidence
    evidence = feature.get('evidence', [])
    if evidence:
        prompt_parts.append("Evidence:")
        for ev in evidence[:2]:
            excerpt = ev.get('excerpt', '')[:100]
            prompt_parts.append(f"  - \"{excerpt}...\"")


def generate_value_path_v2(
    project_id: UUID,
    model_override: str | None = None,
) -> GenerateVPV2Output:
    """
    Generate a complete Value Path v2 from enriched features and personas.

    Args:
        project_id: Project UUID
        model_override: Optional model name override

    Returns:
        GenerateVPV2Output with VP steps

    Raises:
        ValueError: If insufficient data for generation
    """
    settings = get_settings()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # Get enriched features
    features = list_features(project_id)
    enriched_features = [f for f in features if f.get('enrichment_status') == 'enriched']

    if not enriched_features:
        # Fall back to all features if none enriched
        enriched_features = features
        logger.warning(f"No enriched features found, using all {len(features)} features")

    if not enriched_features:
        raise ValueError("No features found for VP generation")

    # Get personas
    personas = list_personas(project_id)
    enriched_personas = [p for p in personas if p.get('enrichment_status') == 'enriched']

    if not enriched_personas:
        enriched_personas = personas
        logger.warning(f"No enriched personas found, using all {len(personas)} personas")

    logger.info(
        f"Generating VP v2 for project {project_id}",
        extra={
            "project_id": str(project_id),
            "feature_count": len(enriched_features),
            "persona_count": len(enriched_personas),
        },
    )

    # Build prompt
    prompt = _build_generation_prompt(
        project_id=project_id,
        features=enriched_features,
        personas=enriched_personas,
    )

    # Call LLM
    model = model_override or settings.FEATURES_ENRICH_MODEL
    logger.info(f"Calling {model} for VP v2 generation")

    response = client.chat.completions.create(
        model=model,
        temperature=0.3,
        max_tokens=8192,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )

    raw_output = response.choices[0].message.content or ""

    # Parse and validate
    try:
        result = _parse_and_validate(raw_output, project_id)
    except (json.JSONDecodeError, ValidationError) as e:
        logger.warning(f"First VP generation attempt failed: {e}")

        # Retry with fix prompt
        fix_prompt = f"""The previous output was invalid. Error: {e}

Please fix and output ONLY valid JSON matching the schema. No markdown."""

        retry_response = client.chat.completions.create(
            model=model,
            temperature=0,
            max_tokens=8192,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": raw_output},
                {"role": "user", "content": fix_prompt},
            ],
        )

        retry_output = retry_response.choices[0].message.content or ""
        result = _parse_and_validate(retry_output, project_id)

    logger.info(
        f"Generated VP v2 with {len(result.steps)} steps",
        extra={"project_id": str(project_id), "step_count": len(result.steps)},
    )

    return result


def _parse_and_validate(raw_output: str, project_id: UUID) -> GenerateVPV2Output:
    """Parse and validate LLM output."""
    from app.core.llm import parse_llm_json_dict
    parsed = parse_llm_json_dict(raw_output)
    parsed["project_id"] = str(project_id)
    return GenerateVPV2Output.model_validate(parsed)


def save_vp_steps(
    project_id: UUID,
    steps: list[VPStepV2],
    preserve_consultant_edited: bool = True,
) -> dict[str, Any]:
    """
    Save generated VP steps to database.

    Args:
        project_id: Project UUID
        steps: Generated VP steps
        preserve_consultant_edited: If True, don't overwrite consultant-edited steps

    Returns:
        Summary of save operation
    """
    supabase = get_supabase()

    # Get existing steps
    existing_response = (
        supabase.table("vp_steps")
        .select("id, step_index, consultant_edited")
        .eq("project_id", str(project_id))
        .execute()
    )
    existing_steps = {s["step_index"]: s for s in (existing_response.data or [])}

    created = 0
    updated = 0
    preserved = 0

    for step in steps:
        existing = existing_steps.get(step.step_index)

        # Check if we should preserve
        if existing and preserve_consultant_edited and existing.get("consultant_edited"):
            preserved += 1
            # Just update staleness
            supabase.table("vp_steps").update({
                "is_stale": False,
                "stale_reason": None,
            }).eq("id", existing["id"]).execute()
            continue

        # Determine confirmation status
        confirmation_status = "ai_generated"
        if step.has_signal_evidence:
            confirmation_status = "confirmed_consultant"  # Auto-confirm if signal evidence

        step_data = {
            "project_id": str(project_id),
            "step_index": step.step_index,
            "label": step.label,
            "actor_persona_id": step.actor_persona_id,
            "actor_persona_name": step.actor_persona_name,
            "narrative_user": step.narrative_user,
            "narrative_system": step.narrative_system,
            "description": step.narrative_user,  # Legacy field
            "value_created": step.value_created,
            "features_used": [f.model_dump() for f in step.features_used],
            "rules_applied": step.rules_applied,
            "integrations_triggered": step.integrations_triggered,
            "ui_highlights": step.ui_highlights,
            "evidence": [e.model_dump() for e in step.evidence],
            "has_signal_evidence": step.has_signal_evidence,
            "generation_status": "generated",
            "generated_at": "now()",
            "is_stale": False,
            "stale_reason": None,
            "confirmation_status": confirmation_status,
            "updated_at": "now()",
        }

        if existing:
            # Update existing step
            supabase.table("vp_steps").update(step_data).eq("id", existing["id"]).execute()
            updated += 1
        else:
            # Create new step
            step_data["status"] = "draft"  # Legacy field
            supabase.table("vp_steps").insert(step_data).execute()
            created += 1

    # Delete orphaned steps (steps with higher index than generated)
    max_index = max(s.step_index for s in steps) if steps else 0
    if existing_steps:
        for idx, existing in existing_steps.items():
            if idx > max_index and not existing.get("consultant_edited"):
                supabase.table("vp_steps").delete().eq("id", existing["id"]).execute()

    return {
        "created": created,
        "updated": updated,
        "preserved": preserved,
        "total_steps": len(steps),
    }


def generate_and_save_value_path(
    project_id: UUID,
    preserve_consultant_edited: bool = True,
) -> dict[str, Any]:
    """
    Generate VP v2 and save to database.

    Args:
        project_id: Project UUID
        preserve_consultant_edited: Preserve consultant-edited steps

    Returns:
        Summary with generation results and gaps
    """
    # Generate
    result = generate_value_path_v2(project_id)

    # Save
    save_result = save_vp_steps(
        project_id=project_id,
        steps=result.steps,
        preserve_consultant_edited=preserve_consultant_edited,
    )

    # Log generation
    supabase = get_supabase()
    supabase.table("vp_generation_log").insert({
        "project_id": str(project_id),
        "generation_type": "full",
        "steps_created": save_result["created"],
        "steps_updated": save_result["updated"],
        "steps_preserved": save_result["preserved"],
        "trigger_reason": "manual_generation",
        "completed_at": "now()",
    }).execute()

    return {
        "project_id": str(project_id),
        "steps_generated": len(result.steps),
        "steps_created": save_result["created"],
        "steps_updated": save_result["updated"],
        "steps_preserved": save_result["preserved"],
        "generation_summary": result.generation_summary,
        "gaps_identified": result.gaps_identified,
    }
