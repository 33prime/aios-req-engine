"""LLM chain for generating batch proposals with context and evidence."""

import json
from typing import Any
from uuid import UUID

from openai import OpenAI
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.embeddings import embed_texts
from app.core.logging import get_logger
from app.db.features import list_features
from app.db.personas import list_personas
from app.db.phase0 import vector_search_with_priority
from app.db.proposals import create_proposal
from app.db.vp import list_vp_steps

logger = get_logger(__name__)

# System prompt for proposal generation
SYSTEM_PROMPT = """You are a context-aware prototype coach AI helping consultants build excellent first versions.

Your task is to generate batch proposals for changes to a project's features, Value Path steps, or personas.

You MUST output ONLY valid JSON matching this exact schema:

{
  "title": "string - concise proposal title (e.g., 'Add Dark Mode Support')",
  "description": "string - brief description of the batch proposal",
  "proposal_type": "string - one of: features, vp, personas, mixed",
  "changes": [
    {
      "entity_type": "string - one of: feature, vp_step, persona",
      "operation": "string - one of: create, update, delete",
      "entity_id": "string|null - UUID for update/delete, null for create",
      "before": "object|null - current state for update/delete",
      "after": "object - desired state",
      "evidence": [
        {
          "chunk_id": "string - UUID from research chunks",
          "excerpt": "string - verbatim text from chunk (max 280 chars)",
          "rationale": "string - why this evidence supports the change"
        }
      ],
      "rationale": "string - explanation for this specific change"
    }
  ]
}

CRITICAL RULES:
1. Output ONLY the JSON object, no markdown, no explanation, no preamble.
2. The JSON MUST have: title, description, proposal_type, and changes array.
3. Each change must have: entity_type, operation, entity_id (or null), after, evidence (can be empty array), and rationale.
4. For creates: entity_id should be null, before should be null or omitted.
5. For updates: entity_id MUST be a real UUID from the current state (e.g., "a1b2c3d4-e5f6-..."). NEVER use placeholders like "existing-feature-uuid" or feature names - always use the exact UUID provided in the current state.
6. For deletes: entity_id required (must be real UUID), before should contain current state, after can be null or empty.
7. Evidence chunks should come from the provided research when available.
8. Be specific and actionable - avoid vague statements.
9. Changes should align with the user's intent and project context.
10. Group related changes logically (e.g., all features for dark mode together).
11. Provide clear rationales explaining why each change is needed.
12. NEVER invent or guess UUIDs - only use the exact UUIDs provided in the "Current Project State" section.

ENTITY-SPECIFIC GUIDELINES:

For features:
- Required fields: name, category, is_mvp, confidence, status
- Valid categories: Core, Security, Integration, UX, Performance, etc.
- Valid confidence: low, medium, high
- Valid status: draft, confirmed_consultant, confirmed_client
- Valid lifecycle_stage: discovered (default for new), refined, confirmed
- Enrichment fields (use these for detailed feature updates):
  - overview: Business-friendly description of what the feature does and why it matters
  - target_personas: Array of [{persona_id, persona_name, role: 'primary'|'secondary', context}]
  - user_actions: Array of step-by-step actions ["Taps Start", "Enters info", ...]
  - system_behaviors: Array of behind-the-scenes behaviors ["Starts recording", "Sends to API", ...]
  - ui_requirements: Array of UI specs ["One question at a time", "Progress indicator", ...]
  - rules: Array of business/validation rules ["Cannot start without name", ...]
  - integrations: Array of external systems ["HubSpot", "OpenAI Whisper", ...]
- Optional: evidence array, details object (legacy JSONB for backward compatibility)

For vp_steps:
- Required fields: step_index, label, status, description
- step_index: integer (1, 2, 3...)
- Optional: user_benefit_pain, ui_overview, value_created, kpi_impact, needed array, evidence array

For personas:
- Required fields: slug, name, role, demographics, psychographics, goals, pain_points
- slug: lowercase-hyphenated (e.g., 'sales-manager')
- demographics: object with age_range, location, etc.
- psychographics: object with tech_savviness, motivations, etc.
- goals and pain_points: arrays of strings
- Optional: description, related_features

CONTEXT-AWARE INTELLIGENCE:
- If user requests "add X", prefer creating new entities rather than updating
- If user requests "update X" or "improve X", prefer updating existing entities
- If current state has gaps (e.g., no personas), proactively suggest creates
- Link evidence from research when it supports the change
- Consider MVP status when prioritizing changes
- Ensure changes align with project's current mode (initial vs maintenance)

FEATURE → VALUE PATH INTEGRATION:
When creating or updating a feature, ALWAYS consider how it affects the Value Path:
- Identify which VP steps the feature relates to (e.g., a "voice dictation" feature relates to survey input steps)
- Include VP step updates in the same proposal to add the feature to the step's "needed" array
- Update the step's description/ui_overview if the feature changes the user experience
- This ensures features and user flows stay synchronized

Example: If adding "Voice Dictation" feature, also update VP step "Survey Data Entry" to include:
  - needed: [{name: "Voice Dictation", type: "feature", description: "Enables speech-to-text input"}]
  - ui_overview: Updated to mention voice input option"""


FIX_SCHEMA_PROMPT = """The previous output was invalid. Here is the error:

{error}

Here is your previous output:

{previous_output}

CRITICAL FIX REQUIRED:
- Your JSON must have: title, description, proposal_type, changes
- Each change must have: entity_type, operation, after, rationale
- entity_type must be one of: feature, vp_step, persona
- operation must be one of: create, update, delete
- proposal_type must be one of: features, vp, personas, mixed

Please fix the output to match the required JSON schema exactly. Output ONLY valid JSON, no explanation."""


async def generate_feature_proposal(
    project_id: UUID,
    intent: str,
    scope: str = "new_features",
    include_evidence: bool = True,
    count_hint: int | None = None,
    conversation_id: UUID | None = None,
    context_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Generate a batch proposal for features with context and evidence.

    Args:
        project_id: Project UUID
        intent: User's intent/request (e.g., "add dark mode support")
        scope: Scope of changes ('new_features', 'update_existing', 'both')
        include_evidence: Whether to search research for evidence
        count_hint: Approximate number of features (1-10)
        conversation_id: Optional conversation UUID
        context_snapshot: Optional context snapshot

    Returns:
        Created proposal record

    Raises:
        Exception: If proposal generation fails
    """
    settings = get_settings()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    try:
        # 1. Load current project state
        current_features = list_features(project_id)
        current_vp = list_vp_steps(project_id)
        current_personas = list_personas(project_id)

        # 2. Search research for evidence (if requested)
        evidence_chunks = []
        if include_evidence:
            try:
                # Embed the user intent
                query_embedding = embed_texts([intent])[0]

                # Search with priority boosting
                search_results = vector_search_with_priority(
                    query_embedding=query_embedding,
                    match_count=10,
                    project_id=project_id,
                    priority_boost=True,
                )

                evidence_chunks = search_results[:8] if search_results else []

                logger.info(
                    f"Found {len(evidence_chunks)} evidence chunks for proposal",
                    extra={"project_id": str(project_id), "intent": intent},
                )

            except Exception as e:
                logger.warning(
                    f"Failed to search research for evidence: {e}",
                    extra={"project_id": str(project_id)},
                )

        # 3. Build user prompt with context
        user_prompt = build_proposal_prompt(
            intent=intent,
            scope=scope,
            count_hint=count_hint,
            current_features=current_features,
            current_prd=current_prd,
            current_vp=current_vp,
            current_personas=current_personas,
            evidence_chunks=evidence_chunks,
        )

        # 4. Call LLM to generate proposal
        max_retries = 2
        last_error = None
        previous_output = None

        for attempt in range(max_retries):
            try:
                if attempt == 0:
                    # First attempt
                    messages = [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ]
                else:
                    # Retry with fix prompt
                    messages.append({
                        "role": "assistant",
                        "content": previous_output,
                    })
                    messages.append({
                        "role": "user",
                        "content": FIX_SCHEMA_PROMPT.format(
                            error=str(last_error),
                            previous_output=previous_output,
                        ),
                    })

                response = client.chat.completions.create(
                    model=settings.STATE_BUILDER_MODEL,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=4000,
                    response_format={"type": "json_object"},
                )

                raw_output = response.choices[0].message.content
                previous_output = raw_output

                # Parse JSON
                proposal_data = json.loads(raw_output)

                # Validate required fields
                if not all(k in proposal_data for k in ["title", "description", "proposal_type", "changes"]):
                    raise ValueError("Missing required fields: title, description, proposal_type, or changes")

                # Validate proposal_type
                valid_types = ["features", "prd", "vp", "personas", "mixed"]
                if proposal_data["proposal_type"] not in valid_types:
                    raise ValueError(f"Invalid proposal_type: {proposal_data['proposal_type']}")

                # Validate changes
                for change in proposal_data["changes"]:
                    if not all(k in change for k in ["entity_type", "operation", "after", "rationale"]):
                        raise ValueError("Change missing required fields")

                    if change["entity_type"] not in ["feature", "vp_step", "persona"]:
                        raise ValueError(f"Invalid entity_type: {change['entity_type']}")

                    if change["operation"] not in ["create", "update", "delete"]:
                        raise ValueError(f"Invalid operation: {change['operation']}")

                # 5. Create proposal record
                proposal = create_proposal(
                    project_id=project_id,
                    conversation_id=conversation_id,
                    title=proposal_data["title"],
                    description=proposal_data.get("description"),
                    proposal_type=proposal_data["proposal_type"],
                    changes=proposal_data["changes"],
                    user_request=intent,
                    context_snapshot=context_snapshot or {},
                    created_by="chat_assistant",
                )

                logger.info(
                    f"Generated proposal {proposal['id']} with {len(proposal_data['changes'])} changes",
                    extra={
                        "project_id": str(project_id),
                        "proposal_id": proposal["id"],
                        "proposal_type": proposal_data["proposal_type"],
                    },
                )

                return proposal

            except (json.JSONDecodeError, ValueError, ValidationError) as e:
                last_error = e
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries} failed: {e}",
                    extra={"project_id": str(project_id)},
                )

                if attempt == max_retries - 1:
                    raise

        # If we get here, all retries failed
        raise Exception(f"Failed to generate valid proposal after {max_retries} attempts: {last_error}")

    except Exception as e:
        logger.error(
            f"Error generating proposal: {e}",
            exc_info=True,
            extra={"project_id": str(project_id), "intent": intent},
        )
        raise


def build_proposal_prompt(
    intent: str,
    scope: str,
    count_hint: int | None,
    current_features: list[dict],
    current_prd: list[dict],
    current_vp: list[dict],
    current_personas: list[dict],
    evidence_chunks: list[dict],
) -> str:
    """
    Build the user prompt with context for proposal generation.

    Args:
        intent: User's intent/request
        scope: Scope of changes
        count_hint: Approximate number of features
        current_features: Current features
        current_prd: Current PRD sections
        current_vp: Current VP steps
        current_personas: Current personas
        evidence_chunks: Evidence chunks from research

    Returns:
        Formatted user prompt
    """
    # Build current state summary - IMPORTANT: Include entity IDs for updates!
    state_summary = f"""# Current Project State

## Features ({len(current_features)} total)
IMPORTANT: Use these exact UUIDs when creating update operations!
"""
    if current_features:
        for feature in current_features[:10]:  # Show first 10 with IDs
            feature_id = feature.get('id', 'unknown')
            state_summary += f"- ID: {feature_id} | {feature['name']} (category: {feature.get('category', 'Unknown')}, mvp: {feature.get('is_mvp', False)})\n"
        if len(current_features) > 10:
            state_summary += f"... and {len(current_features) - 10} more\n"
    else:
        state_summary += "No features yet.\n"

    state_summary += f"\n## PRD Sections ({len(current_prd)} total)\n"
    state_summary += "IMPORTANT: Use these exact UUIDs when creating update operations!\n"
    if current_prd:
        for section in current_prd[:10]:
            section_id = section.get('id', 'unknown')
            state_summary += f"- ID: {section_id} | {section['label']} ({section['slug']})\n"
    else:
        state_summary += "No PRD sections yet.\n"

    state_summary += f"\n## Value Path Steps ({len(current_vp)} total)\n"
    state_summary += "IMPORTANT: Use these exact UUIDs when creating update operations!\n"
    if current_vp:
        for step in current_vp[:10]:
            step_id = step.get('id', 'unknown')
            state_summary += f"- ID: {step_id} | Step {step['step_index']}: {step.get('label', 'Untitled')}\n"
    else:
        state_summary += "No VP steps yet.\n"

    state_summary += f"\n## Personas ({len(current_personas)} total)\n"
    state_summary += "IMPORTANT: Use these exact UUIDs when creating update operations!\n"
    if current_personas:
        for persona in current_personas:
            persona_id = persona.get('id', 'unknown')
            state_summary += f"- ID: {persona_id} | {persona['name']} ({persona.get('role', 'Unknown role')})\n"
    else:
        state_summary += "No personas yet.\n"

    # Build evidence section
    evidence_summary = ""
    if evidence_chunks:
        evidence_summary = "\n# Available Research Evidence\n\n"
        for i, chunk in enumerate(evidence_chunks, 1):
            chunk_id = chunk.get('id') or chunk.get('chunk_id') or f'chunk-{i}'
            evidence_summary += f"## Chunk {i} (ID: {chunk_id})\n"
            evidence_summary += f"Similarity: {chunk.get('similarity', 0):.3f}\n"
            evidence_summary += f"Text: {chunk.get('text', '')[:300]}...\n"
            evidence_summary += f"Source: {chunk.get('metadata', {}).get('source_type', 'unknown')}\n\n"

    # Build request section
    request_section = f"""# User Request

Intent: {intent}
Scope: {scope}
"""
    if count_hint:
        request_section += f"Approximate count: {count_hint} items\n"

    # Combine all sections
    return f"""{state_summary}

{evidence_summary}

{request_section}

Generate a batch proposal that addresses the user's intent. Create changes (create/update/delete) as appropriate.
Link evidence from the research chunks when relevant.
Provide clear rationales for each change."""


def assess_proposal_complexity(proposal_data: dict[str, Any]) -> dict[str, Any]:
    """
    Assess whether a proposal should be auto-applied or requires batch preview.

    Criteria for auto-apply:
    - Single change only
    - High confidence (if applicable)
    - No cross-entity dependencies
    - Create or simple update operation

    Args:
        proposal_data: Proposal data dictionary

    Returns:
        Assessment dict with auto_apply_ok, complexity_level, reasoning
    """
    changes = proposal_data.get("changes", [])

    # Count changes by type
    change_count = len(changes)
    creates = sum(1 for c in changes if c.get("operation") == "create")
    updates = sum(1 for c in changes if c.get("operation") == "update")
    deletes = sum(1 for c in changes if c.get("operation") == "delete")

    # Count entity types affected
    entity_types = set(c.get("entity_type") for c in changes)

    # Default to requiring preview
    auto_apply_ok = False
    complexity_level = "complex"
    reasoning = []

    # Simple case: single create with high confidence
    if change_count == 1:
        change = changes[0]
        if change.get("operation") == "create":
            # Check if it's a high-confidence feature
            after = change.get("after", {})
            if change.get("entity_type") == "feature" and after.get("confidence") == "high":
                auto_apply_ok = True
                complexity_level = "simple"
                reasoning.append("Single high-confidence feature creation")
            else:
                complexity_level = "moderate"
                reasoning.append("Single creation but not high-confidence feature")
        elif change.get("operation") == "update":
            # Single update - check if it affects VP steps
            if change.get("entity_type") == "vp_step":
                complexity_level = "moderate"
                reasoning.append("Single update to VP - may affect multiple areas")
            else:
                auto_apply_ok = True
                complexity_level = "simple"
                reasoning.append("Single simple update")

    # Multiple changes of same type
    elif change_count <= 3 and len(entity_types) == 1:
        if "vp_step" not in entity_types:
            # Multiple features/personas only
            if creates == change_count:  # All creates
                complexity_level = "moderate"
                reasoning.append(f"{change_count} creates of same type - moderate complexity")
            else:
                complexity_level = "moderate"
                reasoning.append(f"{change_count} mixed operations on same entity type")
        else:
            complexity_level = "complex"
            reasoning.append("Changes to VP steps affect multiple areas")

    # Many changes or mixed types
    else:
        complexity_level = "complex"
        if change_count > 3:
            reasoning.append(f"{change_count} changes - requires review")
        if len(entity_types) > 1:
            reasoning.append(f"Affects {len(entity_types)} different entity types")

    return {
        "auto_apply_ok": auto_apply_ok,
        "complexity_level": complexity_level,  # simple, moderate, complex
        "reasoning": "; ".join(reasoning),
        "change_summary": {
            "total": change_count,
            "creates": creates,
            "updates": updates,
            "deletes": deletes,
            "entity_types": list(entity_types),
        }
    }
