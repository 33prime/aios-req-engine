"""Context Snapshot builder for Signal Pipeline v2.

Assembles a 4-layer prompt context that gets injected into every extraction run:
  Layer 1: Entity inventory (IDs, names, confirmation status, staleness)
  Layer 2: Memory beliefs, insights, open questions
  Layer 3: Gap summary from the context frame
  Layer 4: Extraction briefing (Haiku-synthesized coverage/dedup/targets)

All layers are pre-rendered as prompt strings — the extraction chain just
concatenates them into the system prompt. Layer 4 costs ~$0.002 per signal.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ContextSnapshot(BaseModel):
    """Pre-rendered 4-layer context for extraction prompts.

    Each layer is a ready-to-inject prompt string.
    """

    # Layer 1: What exists now (entity IDs, names, statuses)
    entity_inventory_prompt: str = ""

    # Layer 2: What we believe (memory graph)
    memory_prompt: str = ""

    # Layer 3: What's missing (gaps + rules)
    gaps_prompt: str = ""

    # Layer 4: Extraction directive (Pulse Engine or Haiku fallback)
    extraction_briefing_prompt: str = ""

    # Raw data for downstream use (scoring, resolution)
    entity_inventory: dict[str, list[dict]] = Field(default_factory=dict)
    beliefs: list[dict] = Field(default_factory=list)
    open_questions: list[dict] = Field(default_factory=list)

    # Pulse snapshot (None if pulse computation failed)
    pulse: Any = None


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

    # Pre-load open questions once (reused by memory layer + extraction briefing)
    open_questions_raw: list[dict] = []
    try:
        from app.db.open_questions import list_open_questions

        open_questions_raw = await asyncio.to_thread(
            list_open_questions, project_id, "open", 10
        )
    except Exception as e:
        logger.debug(f"Open questions pre-load failed: {e}")

    # Run layers 1-3 in parallel (independent of each other)
    entity_inventory_task = _build_entity_inventory(project_id, project_data=project_data)
    memory_task = _build_memory_layer(project_id, open_questions_raw=open_questions_raw)
    gaps_task = _build_gaps_layer(project_id, project_data=project_data)

    entity_inventory, (memory_prompt, beliefs, open_questions), gaps_prompt = (
        await asyncio.gather(entity_inventory_task, memory_task, gaps_task)
    )

    entity_prompt = _render_entity_inventory_prompt(entity_inventory)

    # Layer 4: Pulse Engine directive (deterministic, $0) with Haiku fallback
    pulse = None
    briefing_prompt = ""
    try:
        from app.core.pulse_engine import compute_project_pulse

        pulse = await compute_project_pulse(
            project_id,
            project_data=project_data,
            entity_inventory=entity_inventory,
        )
        briefing_prompt = pulse.extraction_directive.rendered_prompt
        logger.info(
            f"Pulse computed: stage={pulse.stage.current.value} "
            f"config=v{pulse.config_version} rules={len(pulse.rules_fired)}"
        )
    except Exception as e:
        logger.warning(f"Pulse engine failed, falling back to Haiku briefing: {e}")
        briefing_prompt = await _build_extraction_briefing(
            project_id,
            project_data=project_data,
            entity_inventory=entity_inventory,
            open_questions_raw=open_questions_raw,
        )

    return ContextSnapshot(
        entity_inventory_prompt=entity_prompt,
        memory_prompt=memory_prompt,
        gaps_prompt=gaps_prompt,
        extraction_briefing_prompt=briefing_prompt,
        entity_inventory=entity_inventory,
        beliefs=beliefs,
        open_questions=open_questions,
        pulse=pulse,
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

    # Load stakeholders, data_entities, constraints, competitors in parallel
    from app.db.supabase_client import get_supabase

    sb = get_supabase()
    pid = str(project_id)

    def _q_stakeholders():
        try:
            return sb.table("stakeholders").select("id, name, first_name, last_name, stakeholder_type, confirmation_status, is_stale").eq("project_id", pid).execute()
        except Exception:
            return None

    def _q_data_entities():
        try:
            return sb.table("data_entities").select("id, name, entity_category, confirmation_status, is_stale").eq("project_id", pid).execute()
        except Exception:
            return None

    def _q_constraints():
        try:
            return sb.table("constraints").select("id, title, constraint_type, confirmation_status").eq("project_id", pid).execute()
        except Exception:
            return None

    def _q_competitors():
        try:
            return sb.table("competitor_references").select("id, name, reference_type").eq("project_id", pid).execute()
        except Exception:
            return None

    stk_resp, de_resp, con_resp, comp_resp = await asyncio.gather(
        asyncio.to_thread(_q_stakeholders),
        asyncio.to_thread(_q_data_entities),
        asyncio.to_thread(_q_constraints),
        asyncio.to_thread(_q_competitors),
    )

    inventory["stakeholder"] = [
        {
            "id": str(s.get("id", "")),
            "name": f"{s.get('first_name', '')} {s.get('last_name', '')}".strip() or s.get("name", ""),
            "stakeholder_type": s.get("stakeholder_type", ""),
            "confirmation_status": s.get("confirmation_status", "ai_generated"),
            "is_stale": s.get("is_stale", False),
        }
        for s in ((stk_resp.data or []) if stk_resp else [])
    ]

    inventory["data_entity"] = [
        {
            "id": str(d.get("id", "")),
            "name": d.get("name", ""),
            "entity_category": d.get("entity_category", ""),
            "confirmation_status": d.get("confirmation_status", "ai_generated"),
            "is_stale": d.get("is_stale", False),
        }
        for d in ((de_resp.data or []) if de_resp else [])
    ]

    inventory["constraint"] = [
        {
            "id": str(c.get("id", "")),
            "name": c.get("title", ""),
            "constraint_type": c.get("constraint_type", ""),
            "confirmation_status": c.get("confirmation_status", "ai_generated"),
        }
        for c in ((con_resp.data or []) if con_resp else [])
    ]

    inventory["competitor"] = [
        {
            "id": str(c.get("id", "")),
            "name": c.get("name", ""),
            "reference_type": c.get("reference_type", "competitor"),
        }
        for c in ((comp_resp.data or []) if comp_resp else [])
    ]

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


async def _build_memory_layer(
    project_id: UUID,
    open_questions_raw: list[dict] | None = None,
) -> tuple[str, list[dict], list[dict]]:
    """Build memory prompt from beliefs, insights, and open questions.

    Args:
        project_id: Project UUID
        open_questions_raw: Pre-loaded open questions (avoids duplicate DB query)

    Returns:
        (prompt_string, beliefs_list, open_questions_list)
    """
    beliefs: list[dict] = []
    insights: list[dict] = []

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

    # Open questions — use pre-loaded data if available
    raw_questions = open_questions_raw if open_questions_raw is not None else []
    if open_questions_raw is None:
        try:
            from app.db.open_questions import list_open_questions

            raw_questions = list_open_questions(project_id, status="open", limit=10)
        except Exception as e:
            logger.debug(f"Open questions load failed: {e}")

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


# =============================================================================
# Layer 4: Extraction briefing (Haiku-synthesized)
# =============================================================================

_BRIEFING_MODEL = "claude-haiku-4-5-20251001"

BRIEFING_TOOL = {
    "name": "submit_extraction_briefing",
    "description": "Submit the extraction briefing with coverage map, dedup alerts, and extraction targets.",
    "input_schema": {
        "type": "object",
        "properties": {
            "coverage_map": {
                "type": "string",
                "description": "Which entity types are saturated (>15), adequate, thin (<3), or missing (0). Name counts.",
            },
            "dedup_alerts": {
                "type": "string",
                "description": "Specific themes/entity names that are over-represented. Say 'merge into existing, don't create new.'",
            },
            "extraction_targets": {
                "type": "string",
                "description": "Based on thin/missing types and open questions, say what to look for.",
            },
        },
        "required": ["coverage_map", "dedup_alerts", "extraction_targets"],
    },
}

_BRIEFING_SYSTEM = """You are an extraction strategist preparing a briefing for a requirements extraction AI.
Given entity inventory metrics, produce a concise briefing that prevents duplicates and targets gaps.

Output 3 sections:
1. coverage_map: Which types are saturated (>15 entities), adequate, thin (<3), or missing (0). Name counts.
2. dedup_alerts: Name specific themes/entity names that are over-represented. Say "merge into existing, don't create new."
3. extraction_targets: Based on thin/missing types and open questions, say what to look for.

Be concrete — name entities, quote descriptions, cite counts. ~300-400 tokens total."""


async def _build_extraction_briefing(
    project_id: UUID,
    project_data: dict | None = None,
    entity_inventory: dict[str, list[dict]] | None = None,
    open_questions_raw: list[dict] | None = None,
) -> str:
    """Build a Haiku-synthesized extraction briefing from entity inventory metrics.

    Computes counts from project_data + entity_inventory (avoids duplicate
    DB queries when inventory is already loaded by _build_entity_inventory).
    Falls back to a deterministic metrics-only briefing on failure.

    Args:
        project_id: Project UUID
        project_data: Pre-loaded project data (avoids duplicate DB call)
        entity_inventory: Pre-loaded entity inventory (avoids 4 count queries)
        open_questions_raw: Pre-loaded open questions (avoids duplicate DB call)

    Returns:
        Rendered briefing prompt string
    """
    try:
        if project_data is None:
            from app.core.action_engine import _load_project_data

            project_data = await _load_project_data(project_id)
    except Exception as e:
        logger.warning(f"Failed to load project data for briefing: {e}")
        return ""

    # Compute entity counts — use inventory if available (no extra DB queries)
    counts: dict[str, int] = {}
    counts["feature"] = len(project_data.get("features") or [])
    counts["persona"] = len(project_data.get("personas") or [])

    workflow_pairs = project_data.get("workflow_pairs") or []
    counts["workflow"] = len(workflow_pairs)
    step_count = 0
    for pair in workflow_pairs:
        step_count += len(pair.get("current_steps") or [])
        step_count += len(pair.get("future_steps") or [])
    counts["workflow_step"] = step_count

    drivers = project_data.get("drivers") or []
    counts["business_driver"] = len(drivers)

    if entity_inventory:
        # Derive counts from already-loaded inventory (eliminates 4 DB round-trips)
        counts["stakeholder"] = len(entity_inventory.get("stakeholder", []))
        counts["data_entity"] = len(entity_inventory.get("data_entity", []))
        counts["constraint"] = len(entity_inventory.get("constraint", []))
        counts["competitor"] = len(entity_inventory.get("competitor", []))
    else:
        # Fallback: run 4 count queries in parallel
        try:
            from app.db.supabase_client import get_supabase

            sb = get_supabase()
            pid = str(project_id)
            tables = [
                ("stakeholders", "stakeholder"),
                ("data_entities", "data_entity"),
                ("constraints", "constraint"),
                ("competitor_references", "competitor"),
            ]

            async def _count(table: str) -> int:
                r = await asyncio.to_thread(
                    lambda t=table: sb.table(t).select("id", count="exact").eq("project_id", pid).execute()
                )
                return r.count or 0

            count_results = await asyncio.gather(*[_count(t) for t, _ in tables])
            for (_, etype), c in zip(tables, count_results):
                counts[etype] = c
        except Exception as e:
            logger.debug(f"Briefing count queries failed: {e}")

    total = sum(counts.values())
    if total == 0:
        return ""  # New project, no briefing needed

    # Build compact input for Haiku
    input_lines = ["## Entity Inventory Metrics"]
    for etype, count in sorted(counts.items(), key=lambda x: -x[1]):
        confirmed = 0
        if etype == "business_driver":
            confirmed = sum(1 for d in drivers if d.get("confirmation_status", "").startswith("confirmed"))
        elif etype == "feature":
            confirmed = sum(
                1 for f in (project_data.get("features") or [])
                if f.get("confirmation_status", "").startswith("confirmed")
            )
        label = f" ({confirmed} confirmed)" if confirmed else ""
        input_lines.append(f"- {etype}: {count}{label}")

    # Top 5 BD descriptions grouped by driver_type
    if drivers:
        input_lines.append("\n### Business Drivers by Type")
        by_type: dict[str, list[str]] = {}
        for d in drivers:
            dt = d.get("driver_type", "unknown")
            desc = (d.get("description") or "")[:60]
            if desc:
                by_type.setdefault(dt, []).append(desc)
        for dt, descs in by_type.items():
            input_lines.append(f"  {dt} ({len(descs)}):")
            for desc in descs[:5]:
                input_lines.append(f"    - {desc}")

    # Top 5 names for other types
    for etype, key_field, data_key in [
        ("feature", "name", "features"),
        ("persona", "name", "personas"),
    ]:
        items = project_data.get(data_key) or []
        if items:
            names = [i.get(key_field, "") for i in items[:5] if i.get(key_field)]
            if names:
                input_lines.append(f"\n### Top {etype}s: {', '.join(names)}")

    # Open questions — use pre-loaded data if available
    raw_questions = open_questions_raw if open_questions_raw is not None else []
    if open_questions_raw is None:
        try:
            from app.db.open_questions import list_open_questions

            raw_questions = list_open_questions(project_id, status="open", limit=5)
        except Exception as e:
            logger.debug(f"Briefing open questions load failed: {e}")
    if raw_questions:
        input_lines.append("\n### Open Questions")
        for q in raw_questions[:5]:
            input_lines.append(f"- {q.get('question', '')}")

    input_text = "\n".join(input_lines)

    # Call Haiku
    try:
        from anthropic import AsyncAnthropic

        from app.core.config import Settings

        settings = Settings()
        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        response = await client.messages.create(
            model=_BRIEFING_MODEL,
            max_tokens=800,
            system=_BRIEFING_SYSTEM,
            messages=[{"role": "user", "content": input_text}],
            temperature=0,
            tools=[BRIEFING_TOOL],
            tool_choice={"type": "tool", "name": "submit_extraction_briefing"},
        )

        for block in response.content:
            if block.type == "tool_use":
                data = block.input
                # Handle string values (Anthropic bug)
                coverage = data.get("coverage_map", "")
                if isinstance(coverage, str):
                    pass  # already a string
                dedup = data.get("dedup_alerts", "")
                targets = data.get("extraction_targets", "")

                return _render_briefing(coverage, dedup, targets)

        logger.warning("No tool_use block in briefing response, falling back to deterministic")
    except Exception as e:
        logger.warning(f"Haiku briefing call failed, using deterministic fallback: {e}")

    # Deterministic fallback
    return _build_deterministic_briefing(counts, drivers, project_data)


def _render_briefing(coverage: str, dedup: str, targets: str) -> str:
    """Render the 3-section briefing prompt."""
    return f"""## Extraction Briefing

### Coverage
{coverage}

### Dedup Alerts
{dedup}

### Extraction Targets
{targets}"""


def _build_deterministic_briefing(
    counts: dict[str, int],
    drivers: list[dict],
    project_data: dict,
) -> str:
    """Metrics-only fallback when Haiku is unavailable."""
    lines = ["## Extraction Briefing (metrics-based)"]

    for etype, count in sorted(counts.items(), key=lambda x: -x[1]):
        if count > 15:
            confirmed = 0
            if etype == "business_driver":
                confirmed = sum(
                    1 for d in drivers if d.get("confirmation_status", "").startswith("confirmed")
                )
            label = f", {confirmed} confirmed" if confirmed else ""
            lines.append(
                f"SATURATED: {etype} ({count} entities{label}) — strongly prefer merge over create."
            )
        elif count == 0:
            lines.append(f"MISSING: {etype}")
        elif count < 3:
            lines.append(f"THIN: {etype} ({count})")

    return "\n".join(lines)
