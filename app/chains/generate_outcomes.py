"""Generate outcome candidates from the entity graph.

Outcomes are state changes that organize everything. They sit above entities.
This chain reads business_drivers, personas, pain points, goals, and the
entity relationship graph to synthesize outcome candidates.

Does NOT run on every signal — uses change-detection triggers.

Usage:
    from app.chains.generate_outcomes import generate_outcomes

    outcomes = await generate_outcomes(
        project_id=project_id,
        entity_graph=graph,
        existing_outcomes=existing,
    )
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2
_INITIAL_DELAY = 1.0
_MODEL = "claude-sonnet-4-6"


# =============================================================================
# Tool schema
# =============================================================================

OUTCOME_TOOL = {
    "name": "submit_outcomes",
    "description": "Submit the synthesized outcome candidates.",
    "input_schema": {
        "type": "object",
        "properties": {
            "macro_outcome": {
                "type": "string",
                "description": "One sentence: the overarching state change for the entire engagement.",
            },
            "outcomes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "State change statement. Observable, not a feature. What MUST be true.",
                        },
                        "description": {
                            "type": "string",
                            "description": "Fuller context — 2-3 sentences.",
                        },
                        "horizon": {
                            "type": "string",
                            "enum": ["h1", "h2", "h3"],
                        },
                        "what_helps": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "3-5 bullets: what helps this outcome become true.",
                        },
                        "actor_outcomes": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "persona_name": {"type": "string"},
                                    "title": {
                                        "type": "string",
                                        "description": "Persona-specific state change in first person: 'I can...'",
                                    },
                                    "before_state": {
                                        "type": "string",
                                        "description": "Today's reality for this persona.",
                                    },
                                    "after_state": {
                                        "type": "string",
                                        "description": "What must be true after. Specific, observable.",
                                    },
                                    "metric": {
                                        "type": "string",
                                        "description": "How you'd know. Measurable criterion.",
                                    },
                                },
                                "required": ["persona_name", "title", "before_state", "after_state", "metric"],
                            },
                            "minItems": 1,
                        },
                        "evidence": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "direction": {
                                        "type": "string",
                                        "enum": ["toward", "away", "reframe"],
                                    },
                                    "text": {"type": "string"},
                                    "source": {"type": "string"},
                                },
                            },
                        },
                        "linked_entity_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "UUIDs of entities that serve or evidence this outcome.",
                        },
                    },
                    "required": ["title", "description", "horizon", "what_helps", "actor_outcomes"],
                },
            },
        },
        "required": ["outcomes"],
    },
}


# =============================================================================
# System prompt
# =============================================================================

_SYSTEM_PROMPT = """You are an outcomes synthesizer for a requirements engineering platform.

Your job: read the entity graph (business drivers, personas, pain points, goals) and synthesize OUTCOMES — state changes that must be true after this engagement.

Rules:
1. Outcomes are NOT features. "Add document upload" is a feature. "Document gaps are closed" is an outcome.
2. Each outcome should affect 2+ personas (actor outcomes). If only 1 persona is affected, it's too narrow.
3. Frame as observable state changes, not capabilities. "Error rate drops to near-zero" not "System has error detection."
4. Actor outcomes use first person: "I can present mom's Healthcare POA in 90 seconds."
5. Before states describe TODAY's pain. After states describe what MUST be true. Be specific.
6. Metrics must be measurable: time ("< 90 seconds"), count ("zero stockouts"), percentage ("95% coverage").
7. Derive from the EVIDENCE — pain severity, goal success criteria, KPI targets. Don't invent.
8. Aim for 3-7 core outcomes. More = too granular. Fewer = too abstract.
9. H1 = prove it works for the initial engagement. H2 = scale it. H3 = platform play.
10. Link to entity IDs from the context — business_drivers, features, workflows that serve each outcome.

Evidence direction:
- "toward" = signal supports this outcome (pain described, goal stated, metric defined)
- "away" = signal contradicts (client pushback, constraint, competing priority)
- "reframe" = signal changes the framing (new perspective, pivot in understanding)"""


# =============================================================================
# Core function
# =============================================================================


async def generate_outcomes(
    project_id: UUID,
    entity_graph: dict[str, list[dict]],
    existing_outcomes: list[dict] | None = None,
) -> dict[str, Any]:
    """Generate outcome candidates from the entity graph.

    Args:
        project_id: Project UUID.
        entity_graph: Dict of entity_type → list of entity dicts.
            Expected keys: business_drivers, personas, features, workflows, constraints.
        existing_outcomes: Current outcomes to avoid duplicating.

    Returns:
        {
            "macro_outcome": "...",
            "outcomes": [outcome_dicts],
            "generation_model": "claude-sonnet-4-6",
            "duration_ms": int,
        }
    """
    start = time.monotonic()

    # Build context for the LLM
    context_parts = []

    # Personas
    personas = entity_graph.get("personas") or entity_graph.get("persona", [])
    if personas:
        lines = ["## Personas"]
        for p in personas[:10]:
            name = p.get("name", "")
            role = p.get("role", "")
            goals = p.get("goals", [])
            pains = p.get("pain_points", [])
            lines.append(f"- **{name}** ({role})")
            if goals:
                lines.append(f"  Goals: {', '.join(goals[:5])}")
            if pains:
                lines.append(f"  Pain points: {', '.join(pains[:5])}")
        context_parts.append("\n".join(lines))

    # Business drivers (pain/goal/kpi)
    drivers = entity_graph.get("business_drivers") or entity_graph.get("business_driver", [])
    if drivers:
        for dtype in ["pain", "goal", "kpi"]:
            typed = [d for d in drivers if d.get("driver_type") == dtype]
            if typed:
                label = {"pain": "Pain Points", "goal": "Goals", "kpi": "KPIs / Metrics"}[dtype]
                lines = [f"## {label}"]
                for d in typed[:8]:
                    desc = d.get("description", d.get("title", ""))
                    did = d.get("id", "")
                    severity = d.get("severity", "")
                    baseline = d.get("baseline_value", "")
                    target = d.get("target_value", "")
                    line = f"- [{did[:8]}] {desc}"
                    if severity:
                        line += f" (severity: {severity})"
                    if baseline and target:
                        line += f" [{baseline} → {target}]"
                    lines.append(line)
                context_parts.append("\n".join(lines))

    # Features
    features = entity_graph.get("features") or entity_graph.get("feature", [])
    if features:
        lines = ["## Features"]
        for f in features[:15]:
            name = f.get("name", "")
            fid = f.get("id", "")
            lines.append(f"- [{fid[:8]}] {name}")
        context_parts.append("\n".join(lines))

    # Workflows
    workflows = entity_graph.get("workflows") or entity_graph.get("workflow", [])
    if workflows:
        lines = ["## Workflows"]
        for w in workflows[:10]:
            name = w.get("name", "")
            wid = w.get("id", "")
            lines.append(f"- [{wid[:8]}] {name}")
        context_parts.append("\n".join(lines))

    # Constraints
    constraints_list = entity_graph.get("constraints") or entity_graph.get("constraint", [])
    if constraints_list:
        lines = ["## Constraints"]
        for c in constraints_list[:8]:
            title = c.get("title", c.get("name", ""))
            lines.append(f"- {title}")
        context_parts.append("\n".join(lines))

    # Existing outcomes (for dedup)
    if existing_outcomes:
        lines = ["## Existing Outcomes (do NOT duplicate)"]
        for o in existing_outcomes:
            lines.append(f"- {o.get('title', '')}")
        context_parts.append("\n".join(lines))

    user_prompt = (
        "## Entity Graph\n\n"
        + "\n\n".join(context_parts)
        + "\n\n---\n\nSynthesize 3-7 core outcomes from this entity graph. "
        "Each must have 2+ actor outcomes with specific before/after/metric."
    )

    system_blocks = [
        {
            "type": "text",
            "text": _SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        },
    ]

    # Call LLM
    result = await _call_outcome_llm(system_blocks, user_prompt)

    elapsed_ms = int((time.monotonic() - start) * 1000)

    return {
        "macro_outcome": result.get("macro_outcome"),
        "outcomes": result.get("outcomes", []),
        "generation_model": _MODEL,
        "duration_ms": elapsed_ms,
    }


async def _call_outcome_llm(
    system_blocks: list[dict],
    user_prompt: str,
) -> dict[str, Any]:
    """Call Sonnet to generate outcomes."""
    from anthropic import (
        APIConnectionError,
        APITimeoutError,
        AsyncAnthropic,
        InternalServerError,
        RateLimitError,
    )
    from app.core.config import Settings

    settings = Settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    last_error: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = await client.messages.create(
                model=_MODEL,
                max_tokens=8000,
                system=system_blocks,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=0.3,
                tools=[OUTCOME_TOOL],
                tool_choice={"type": "tool", "name": "submit_outcomes"},
            )

            for block in response.content:
                if block.type == "tool_use":
                    data = block.input
                    outcomes_raw = data.get("outcomes", [])
                    if isinstance(outcomes_raw, str):
                        try:
                            outcomes_raw = json.loads(outcomes_raw)
                        except json.JSONDecodeError:
                            outcomes_raw = []
                    return {
                        "macro_outcome": data.get("macro_outcome"),
                        "outcomes": outcomes_raw,
                    }

            logger.warning("No tool_use block in outcome generation response")
            return {"outcomes": []}

        except (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError) as e:
            last_error = e
            if attempt < _MAX_RETRIES:
                delay = _INITIAL_DELAY * (2 ** attempt)
                logger.warning(
                    f"Outcome generation attempt {attempt + 1}/{_MAX_RETRIES + 1} "
                    f"failed ({type(e).__name__}), retrying in {delay}s"
                )
                await asyncio.sleep(delay)
            else:
                raise

    raise last_error  # type: ignore[misc]


# =============================================================================
# Change-detection trigger
# =============================================================================


def should_trigger_outcome_generation(
    project_id: UUID,
    signal_count: int,
    new_entity_types: set[str] | None = None,
    created_count: int = 0,
    has_driver_change: bool = False,
) -> bool:
    """Determine whether outcome generation should run based on change-detection.

    Triggers:
    - Signals 1, 2, 3 (bootstrap period)
    - New entity type appears for the first time
    - 3+ entities created in one signal
    - Any business_driver created or modified
    """
    # Bootstrap: always run for first 3 signals
    if signal_count <= 3:
        return True

    # New entity type in the graph
    if new_entity_types:
        return True

    # Bulk creates
    if created_count >= 3:
        return True

    # Business driver change (high-value signal for outcomes)
    if has_driver_change:
        return True

    return False


# =============================================================================
# Persist generated outcomes
# =============================================================================


async def persist_generated_outcomes(
    project_id: UUID,
    generation_result: dict[str, Any],
    entity_graph: dict[str, list[dict]],
) -> list[dict]:
    """Persist outcome generation results to the database.

    Creates outcome records, actor outcomes, and entity links.
    Deduplicates against existing outcomes via embedding similarity.
    Returns list of created outcome dicts.
    """
    from app.db.outcomes import (
        create_outcome,
        create_outcome_actor,
        create_outcome_entity_link,
        embed_outcome,
        get_macro_outcome,
        list_outcomes,
        update_macro_outcome,
    )

    # Update macro outcome if provided
    macro = generation_result.get("macro_outcome")
    if macro:
        existing_macro = get_macro_outcome(project_id)
        if not existing_macro.get("macro_outcome"):
            update_macro_outcome(project_id, macro_outcome=macro)

    existing_outcomes = list_outcomes(project_id)
    existing_titles = {o["title"].lower().strip() for o in existing_outcomes}

    # Build persona lookup for linking
    personas = entity_graph.get("personas") or entity_graph.get("persona", [])
    persona_lookup = {p.get("name", "").lower(): p for p in personas}

    created = []

    for outcome_data in generation_result.get("outcomes", []):
        title = outcome_data.get("title", "").strip()
        if not title:
            continue

        # Simple dedup: skip exact title matches
        if title.lower() in existing_titles:
            logger.debug(f"Skipping duplicate outcome: {title}")
            continue

        # Create core outcome
        outcome = create_outcome(
            project_id=project_id,
            title=title,
            description=outcome_data.get("description", ""),
            horizon=outcome_data.get("horizon", "h1"),
            source_type="system_generated",
            what_helps=outcome_data.get("what_helps", []),
            evidence=outcome_data.get("evidence", []),
            generation_context={"source": "generate_outcomes", "entity_count": sum(len(v) for v in entity_graph.values())},
        )

        # Create actor outcomes
        for actor_data in outcome_data.get("actor_outcomes", []):
            persona_name = actor_data.get("persona_name", "")
            persona = persona_lookup.get(persona_name.lower())
            persona_id = UUID(persona["id"]) if persona and persona.get("id") else None

            create_outcome_actor(
                outcome_id=UUID(outcome["id"]),
                persona_name=persona_name,
                title=actor_data.get("title", ""),
                before_state=actor_data.get("before_state", ""),
                after_state=actor_data.get("after_state", ""),
                metric=actor_data.get("metric", ""),
                persona_id=persona_id,
            )

        # Create entity links
        for entity_id in outcome_data.get("linked_entity_ids", []):
            if not entity_id or len(entity_id) < 8:
                continue
            # Determine entity type from graph
            for etype, entities in entity_graph.items():
                for e in entities:
                    if str(e.get("id", "")).startswith(entity_id[:8]):
                        clean_type = etype.rstrip("s") if etype.endswith("s") and etype != "vp_steps" else etype
                        link_type = "evidence_for" if clean_type == "business_driver" else "serves"
                        entity_name = e.get("name") or e.get("title") or e.get("description", "")[:40]
                        how = (
                            f"{clean_type} '{entity_name}' provides evidence for this outcome"
                            if link_type == "evidence_for"
                            else f"{clean_type} '{entity_name}' serves this outcome"
                        )
                        create_outcome_entity_link(
                            outcome_id=UUID(outcome["id"]),
                            entity_id=e["id"],
                            entity_type=clean_type,
                            link_type=link_type,
                            how_served=how,
                        )
                        break

        # Embed the outcome
        try:
            await embed_outcome(outcome)
        except Exception:
            logger.debug(f"Failed to embed outcome {outcome['id']}", exc_info=True)

        created.append(outcome)

    logger.info(f"Persisted {len(created)} outcomes for project {project_id}")
    return created
