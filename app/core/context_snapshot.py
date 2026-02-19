"""Context Snapshot builder for Signal Pipeline v2.

Assembles a 3-layer prompt context that gets injected into every extraction run:
  Layer 1: Entity inventory (IDs, names, confirmation status, staleness)
  Layer 2: Memory beliefs, insights, open questions
  Layer 3: Gap summary from the context frame

All layers are pre-rendered as prompt strings — the extraction chain just
concatenates them into the system prompt. Zero LLM cost, ~200ms to build.
"""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ContextSnapshot(BaseModel):
    """Pre-rendered 3-layer context for extraction prompts.

    Each layer is a ready-to-inject prompt string.
    """

    # Layer 1: What exists now (entity IDs, names, statuses)
    entity_inventory_prompt: str = ""

    # Layer 2: What we believe (memory graph)
    memory_prompt: str = ""

    # Layer 3: What's missing (gaps + rules)
    gaps_prompt: str = ""

    # Raw data for downstream use (scoring, resolution)
    entity_inventory: dict[str, list[dict]] = Field(default_factory=dict)
    beliefs: list[dict] = Field(default_factory=list)
    open_questions: list[dict] = Field(default_factory=list)


async def build_context_snapshot(project_id: UUID) -> ContextSnapshot:
    """Build a 3-layer context snapshot for a project.

    Combines data from the context frame engine, memory renderer, and gap
    intelligence — all existing functions, no new DB queries.

    Args:
        project_id: Project UUID

    Returns:
        ContextSnapshot with pre-rendered prompt strings
    """
    # Load shared project data once (used by Layer 1 + Layer 3)
    try:
        from app.core.action_engine import _load_project_data

        project_data = await _load_project_data(project_id)
    except Exception as e:
        logger.warning(f"Failed to load project data for context snapshot: {e}")
        project_data = {}

    # Run all 3 layers in parallel (independent of each other)
    entity_inventory_task = _build_entity_inventory(project_id, project_data=project_data)
    memory_task = _build_memory_layer(project_id)
    gaps_task = _build_gaps_layer(project_id, project_data=project_data)

    entity_inventory, (memory_prompt, beliefs, open_questions), gaps_prompt = (
        await asyncio.gather(entity_inventory_task, memory_task, gaps_task)
    )

    entity_prompt = _render_entity_inventory_prompt(entity_inventory)

    return ContextSnapshot(
        entity_inventory_prompt=entity_prompt,
        memory_prompt=memory_prompt,
        gaps_prompt=gaps_prompt,
        entity_inventory=entity_inventory,
        beliefs=beliefs,
        open_questions=open_questions,
    )


# =============================================================================
# Layer 1: Entity inventory
# =============================================================================


async def _build_entity_inventory(
    project_id: UUID,
    project_data: dict | None = None,
) -> dict[str, list[dict]]:
    """Load entity inventory from compute_context_frame() data.

    Plucks {id, name, confirmation_status, is_stale} per entity type.
    Reuses the same _load_project_data() as the action engine — zero new queries.

    Args:
        project_id: Project UUID
        project_data: Pre-loaded project data (avoids duplicate DB call)
    """
    try:
        if project_data is not None:
            data = project_data
        else:
            from app.core.action_engine import _load_project_data
            data = await _load_project_data(project_id)
    except Exception as e:
        logger.warning(f"Failed to load project data for inventory: {e}")
        return {}

    inventory: dict[str, list[dict]] = {}

    # Features
    features = data.get("features") or []
    inventory["feature"] = [
        {
            "id": str(f.get("id", "")),
            "name": f.get("name", ""),
            "confirmation_status": f.get("confirmation_status", "ai_generated"),
            "is_stale": f.get("is_stale", False),
        }
        for f in features
    ]

    # Personas
    personas = data.get("personas") or []
    inventory["persona"] = [
        {
            "id": str(p.get("id", "")),
            "name": p.get("name", ""),
            "confirmation_status": p.get("confirmation_status", "ai_generated"),
            "is_stale": p.get("is_stale", False),
        }
        for p in personas
    ]

    # Workflows + steps
    workflow_pairs = data.get("workflow_pairs") or []
    workflows = []
    workflow_steps = []
    for pair in workflow_pairs:
        wf_id = str(pair.get("id", ""))
        wf_name = pair.get("name", "Unnamed")
        workflows.append(
            {
                "id": wf_id,
                "name": wf_name,
                "confirmation_status": pair.get("confirmation_status", "ai_generated"),
                "is_stale": pair.get("is_stale", False),
            }
        )
        for step in (pair.get("current_steps") or []) + (pair.get("future_steps") or []):
            workflow_steps.append(
                {
                    "id": str(step.get("id", "")),
                    "name": step.get("label", ""),
                    "confirmation_status": step.get("confirmation_status", "ai_generated"),
                    "is_stale": step.get("is_stale", False),
                    "workflow_name": wf_name,
                }
            )

    inventory["workflow"] = workflows
    inventory["workflow_step"] = workflow_steps

    # Business drivers
    drivers = data.get("drivers") or []
    inventory["business_driver"] = [
        {
            "id": str(d.get("id", "")),
            "name": d.get("description", "")[:80],
            "driver_type": d.get("driver_type", ""),
            "confirmation_status": d.get("confirmation_status", "ai_generated"),
            "is_stale": d.get("is_stale", False),
        }
        for d in drivers
    ]

    # Stakeholders (loaded separately in _load_project_data as names only — extend)
    try:
        from app.db.supabase_client import get_supabase

        sb = get_supabase()
        result = (
            sb.table("stakeholders")
            .select("id, name, first_name, last_name, stakeholder_type, confirmation_status, is_stale")
            .eq("project_id", str(project_id))
            .execute()
        )
        inventory["stakeholder"] = [
            {
                "id": str(s.get("id", "")),
                "name": f"{s.get('first_name', '')} {s.get('last_name', '')}".strip() or s.get("name", ""),
                "stakeholder_type": s.get("stakeholder_type", ""),
                "confirmation_status": s.get("confirmation_status", "ai_generated"),
                "is_stale": s.get("is_stale", False),
            }
            for s in (result.data or [])
        ]
    except Exception as e:
        logger.debug(f"Stakeholder inventory load failed: {e}")
        inventory["stakeholder"] = []

    # Data entities
    try:
        from app.db.supabase_client import get_supabase

        sb = get_supabase()
        result = (
            sb.table("data_entities")
            .select("id, name, entity_category, confirmation_status, is_stale")
            .eq("project_id", str(project_id))
            .execute()
        )
        inventory["data_entity"] = [
            {
                "id": str(d.get("id", "")),
                "name": d.get("name", ""),
                "entity_category": d.get("entity_category", ""),
                "confirmation_status": d.get("confirmation_status", "ai_generated"),
                "is_stale": d.get("is_stale", False),
            }
            for d in (result.data or [])
        ]
    except Exception as e:
        logger.debug(f"Data entity inventory load failed: {e}")
        inventory["data_entity"] = []

    # Constraints
    try:
        from app.db.supabase_client import get_supabase

        sb = get_supabase()
        result = (
            sb.table("constraints")
            .select("id, title, constraint_type, confirmation_status")
            .eq("project_id", str(project_id))
            .execute()
        )
        inventory["constraint"] = [
            {
                "id": str(c.get("id", "")),
                "name": c.get("title", ""),
                "constraint_type": c.get("constraint_type", ""),
                "confirmation_status": c.get("confirmation_status", "ai_generated"),
            }
            for c in (result.data or [])
        ]
    except Exception as e:
        logger.debug(f"Constraint inventory load failed: {e}")
        inventory["constraint"] = []

    # Competitors
    try:
        from app.db.supabase_client import get_supabase

        sb = get_supabase()
        result = (
            sb.table("competitor_references")
            .select("id, name, reference_type")
            .eq("project_id", str(project_id))
            .execute()
        )
        inventory["competitor"] = [
            {
                "id": str(c.get("id", "")),
                "name": c.get("name", ""),
                "reference_type": c.get("reference_type", "competitor"),
            }
            for c in (result.data or [])
        ]
    except Exception as e:
        logger.debug(f"Competitor inventory load failed: {e}")
        inventory["competitor"] = []

    return inventory


def _render_entity_inventory_prompt(inventory: dict[str, list[dict]]) -> str:
    """Render entity inventory as a prompt string for extraction context."""
    if not inventory:
        return "No entities exist yet. This is a new project."

    lines = ["## Current Entity Inventory"]

    total = sum(len(v) for v in inventory.values())
    lines.append(f"Total: {total} entities across {len([k for k, v in inventory.items() if v])} types\n")

    for entity_type, entities in inventory.items():
        if not entities:
            continue

        label = entity_type.replace("_", " ").title() + "s"
        lines.append(f"### {label} ({len(entities)})")

        for e in entities[:20]:  # Cap at 20 per type for prompt size
            eid = e.get("id", "?")  # Full UUID — LLM needs complete IDs for merge/update patches
            name = e.get("name", "unnamed")
            status = e.get("confirmation_status", "")
            stale = " [STALE]" if e.get("is_stale") else ""
            extra = ""

            # Type-specific extras
            if entity_type == "business_driver" and e.get("driver_type"):
                extra = f" ({e['driver_type']})"
            elif entity_type == "workflow_step" and e.get("workflow_name"):
                extra = f" in {e['workflow_name']}"
            elif entity_type == "stakeholder" and e.get("stakeholder_type"):
                extra = f" ({e['stakeholder_type']})"

            lines.append(f"- [{eid}] {name}{extra} [{status}]{stale}")

        if len(entities) > 20:
            lines.append(f"  ... and {len(entities) - 20} more")
        lines.append("")

    return "\n".join(lines)


# =============================================================================
# Layer 2: Memory
# =============================================================================


async def _build_memory_layer(project_id: UUID) -> tuple[str, list[dict], list[dict]]:
    """Build memory prompt from beliefs, insights, and open questions.

    Returns:
        (prompt_string, beliefs_list, open_questions_list)
    """
    beliefs: list[dict] = []
    insights: list[dict] = []
    open_questions: list[dict] = []

    try:
        from app.core.memory_renderer import (
            format_beliefs_for_prompt,
            format_insights_for_prompt,
            render_memory_for_di_agent,
        )

        memory_data = await render_memory_for_di_agent(project_id, max_tokens=2000)

        beliefs = memory_data.get("beliefs", [])
        insights = memory_data.get("insights", [])

        # Build prompt sections
        lines = ["## Project Memory (Beliefs & Insights)"]

        # Beliefs
        beliefs_text = format_beliefs_for_prompt(beliefs)
        lines.append(f"\n### Active Beliefs\n{beliefs_text}")

        # Insights
        insights_text = format_insights_for_prompt(insights)
        lines.append(f"\n### Strategic Insights\n{insights_text}")

    except Exception as e:
        logger.debug(f"Memory layer build failed: {e}")
        lines = ["## Project Memory\nMemory graph not available."]

    # Open questions (from action engine data)
    try:
        from app.db.open_questions import list_open_questions

        raw_questions = list_open_questions(project_id, status="open", limit=10)
        open_questions = [
            {
                "id": str(q.get("id", "")),
                "question": q.get("question", ""),
                "priority": q.get("priority", "medium"),
                "category": q.get("category", ""),
            }
            for q in raw_questions
        ]

        if open_questions:
            lines.append("\n### Open Questions")
            for q in open_questions:
                priority_tag = f" [{q['priority']}]" if q["priority"] != "medium" else ""
                lines.append(f"- {q['question']}{priority_tag}")

    except Exception as e:
        logger.debug(f"Open questions load failed: {e}")

    prompt = "\n".join(lines)
    return prompt, beliefs, open_questions


# =============================================================================
# Layer 3: Gaps
# =============================================================================


async def _build_gaps_layer(
    project_id: UUID,
    project_data: dict | None = None,
) -> str:
    """Build gap summary from context frame structural_gaps + top_gaps.

    Args:
        project_id: Project UUID
        project_data: Pre-loaded project data (avoids duplicate DB call)
    """
    try:
        from app.core.action_engine import _build_structural_gaps, _detect_context_phase, _load_project_data

        if project_data is not None:
            data = project_data
        else:
            data = await _load_project_data(project_id)
        phase, _ = _detect_context_phase(data)

        structural_gaps = _build_structural_gaps(data["workflow_pairs"], phase.value)

        lines = ["## Current Gaps & Priorities"]
        lines.append(f"Project phase: {phase.value}")
        lines.append(f"Structural gaps found: {len(structural_gaps)}\n")

        if structural_gaps:
            lines.append("### Top Structural Gaps (prioritize filling these)")
            for gap in structural_gaps[:10]:
                lines.append(f"- {gap.sentence} (score: {gap.score:.0f})")
        else:
            lines.append("No structural gaps detected. Focus on enrichment and validation.")

        return "\n".join(lines)

    except Exception as e:
        logger.debug(f"Gaps layer build failed: {e}")
        return "## Current Gaps\nGap analysis not available."
