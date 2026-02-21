"""Solution Flow Context Builder — zero-LLM-cost context for chat.

Builds a rich SolutionFlowContext from DB reads + string formatting.
Typically ~100ms, 4 layers: flow summary, focused step detail,
cross-step intelligence, retrieval hints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.solution_flow import get_flow_step, get_or_create_flow, list_flow_steps

logger = get_logger(__name__)


@dataclass
class SolutionFlowContext:
    """Structured context for solution flow chat prompts."""

    flow_summary_prompt: str = ""
    focused_step_prompt: str = ""
    cross_step_prompt: str = ""
    retrieval_hints: list[str] = field(default_factory=list)
    entity_change_delta: str = ""
    confirmation_history: str = ""


def _resolve_entity_names_batch(
    ids_by_table: dict[str, list[str]],
) -> dict[str, str]:
    """Batch-resolve entity IDs to names across tables.

    Args:
        ids_by_table: {table_name: [id1, id2, ...]}

    Returns:
        {entity_id: display_name}
    """
    from app.db.supabase_client import get_supabase

    if not ids_by_table:
        return {}

    lookup: dict[str, str] = {}
    supabase = get_supabase()

    table_name_fields = {
        "features": "name",
        "workflows": "name",
        "data_entities": "name",
    }

    for table, ids in ids_by_table.items():
        if not ids:
            continue
        name_field = table_name_fields.get(table, "name")
        try:
            result = (
                supabase.table(table)
                .select(f"id, {name_field}")
                .in_("id", ids)
                .execute()
            )
            for row in result.data or []:
                lookup[row["id"]] = row.get(name_field, row["id"][:8])
        except Exception:
            for eid in ids:
                lookup.setdefault(eid, eid[:8])

    return lookup


def _build_flow_summary(steps: list[dict[str, Any]]) -> str:
    """Layer 1: One line per step, ~50 tokens each."""
    if not steps:
        return "No steps defined yet."

    lines = []
    for step in steps:
        phase = step.get("phase", "?")
        title = step.get("title", "Untitled")
        actors = step.get("actors") or []
        actor_str = ", ".join(actors) if actors else "no actors"

        info_fields = step.get("information_fields") or []
        known = sum(
            1 for f in info_fields
            if isinstance(f, dict) and f.get("confidence") in ("known", "inferred")
        )
        guess = len(info_fields) - known

        open_qs = step.get("open_questions") or []
        open_count = sum(
            1 for q in open_qs
            if isinstance(q, dict) and q.get("status") == "open"
        )

        pending = " [PENDING UPDATES]" if step.get("has_pending_updates") else ""

        line = f"[{phase}] {title} — {actor_str} | fields: {known} known, {guess} guess | explore: {open_count} open{pending}"
        lines.append(line)

    return "\n".join(lines)


def _build_focused_step(
    step: dict[str, Any],
    entity_lookup: dict[str, str],
    prev_title: str | None,
    next_title: str | None,
) -> str:
    """Layer 2: Full detail of the selected step, ~300 tokens."""
    parts: list[str] = []

    # Step ID — critical for tool calls
    parts.append(f"Step ID: {step.get('id', '?')}")

    # Basic info
    parts.append(f"Title: {step.get('title', '?')}")
    parts.append(f"Phase: {step.get('phase', '?')}")
    parts.append(f"Goal: {step.get('goal', '?')}")

    actors = step.get("actors") or []
    if actors:
        parts.append(f"Actors: {', '.join(actors)}")

    # Navigation context
    nav_parts = []
    if prev_title:
        nav_parts.append(f"Previous: {prev_title}")
    if next_title:
        nav_parts.append(f"Next: {next_title}")
    if nav_parts:
        parts.append(" | ".join(nav_parts))

    # Information fields
    info_fields = step.get("information_fields") or []
    if info_fields:
        field_lines = []
        for f in info_fields:
            if isinstance(f, dict):
                conf = f.get("confidence", "unknown")
                ftype = f.get("type", "?")
                mock = f.get("mock_value", "")
                field_lines.append(f"  - {f.get('name', '?')} [{ftype}, {conf}]: {mock}")
        if field_lines:
            parts.append("Information Fields:\n" + "\n".join(field_lines))

    # Open questions
    open_qs = step.get("open_questions") or []
    if open_qs:
        q_lines = []
        for q in open_qs:
            if isinstance(q, dict):
                status = q.get("status", "open")
                question = q.get("question", "?")
                if status == "resolved":
                    q_lines.append(f"  - [resolved] {question} -> {q.get('resolved_answer', '')}")
                elif status == "escalated":
                    q_lines.append(f"  - [escalated] {question}")
                else:
                    q_lines.append(f"  - [open] {question}")
        if q_lines:
            parts.append("Questions:\n" + "\n".join(q_lines))

    # Linked entities
    linked_parts = []
    for key, label in [
        ("linked_feature_ids", "Features"),
        ("linked_workflow_ids", "Workflows"),
        ("linked_data_entity_ids", "Data Entities"),
    ]:
        ids = step.get(key) or []
        if ids:
            names = [entity_lookup.get(eid, eid[:8]) for eid in ids]
            linked_parts.append(f"  {label}: {', '.join(names)}")
    if linked_parts:
        parts.append("Linked Entities:\n" + "\n".join(linked_parts))

    # Optional fields
    if step.get("implied_pattern"):
        parts.append(f"Implied Pattern: {step['implied_pattern']}")
    if step.get("mock_data_narrative"):
        parts.append(f"Preview Narrative: {step['mock_data_narrative']}")
    if step.get("success_criteria"):
        criteria = step["success_criteria"]
        if isinstance(criteria, list):
            parts.append("Success Criteria:\n" + "\n".join(f"  - {c}" for c in criteria))
    if step.get("pain_points_addressed"):
        pps = step["pain_points_addressed"]
        if isinstance(pps, list):
            pp_lines = []
            for pp in pps:
                if isinstance(pp, dict):
                    text = pp.get("text", "?")
                    persona = pp.get("persona")
                    pp_lines.append(f"  - {text}" + (f" ({persona})" if persona else ""))
                else:
                    pp_lines.append(f"  - {pp}")
            if pp_lines:
                parts.append("Pain Points Addressed:\n" + "\n".join(pp_lines))
    if step.get("goals_addressed"):
        goals = step["goals_addressed"]
        if isinstance(goals, list):
            parts.append("Goals Addressed:\n" + "\n".join(f"  - {g}" for g in goals))
    if step.get("ai_config"):
        ai = step["ai_config"]
        if isinstance(ai, dict) and ai.get("role"):
            parts.append(f"AI Role: {ai['role']}")

    return "\n".join(parts)


def _build_cross_step_intelligence(steps: list[dict[str, Any]]) -> str:
    """Layer 3: 5 deterministic checks, no LLM. ~200 tokens."""
    if len(steps) < 2:
        return ""

    insights: list[str] = []

    # 1. Actor gaps — steps with no actors defined
    no_actors = [s.get("title", "?") for s in steps if not (s.get("actors") or [])]
    if no_actors:
        insights.append(f"Steps missing actors: {', '.join(no_actors)}")

    # 2. Phase coverage
    phases_present = {s.get("phase") for s in steps}
    expected = {"entry", "core_experience", "output"}
    missing = expected - phases_present
    if missing:
        insights.append(f"Missing phases: {', '.join(missing)}")

    # 3. Confidence distribution
    total_known = 0
    total_fields = 0
    for s in steps:
        for f in s.get("information_fields") or []:
            if isinstance(f, dict):
                total_fields += 1
                if f.get("confidence") in ("known", "inferred"):
                    total_known += 1
    if total_fields:
        pct = int(total_known / total_fields * 100)
        insights.append(f"Field confidence: {pct}% known/inferred ({total_known}/{total_fields})")

    # 4. Explore hotspots — top 3 steps by open question count
    step_qs = []
    for s in steps:
        open_count = sum(
            1 for q in (s.get("open_questions") or [])
            if isinstance(q, dict) and q.get("status") == "open"
        )
        if open_count:
            step_qs.append((s.get("title", "?"), open_count))
    step_qs.sort(key=lambda x: x[1], reverse=True)
    if step_qs:
        hotspot_strs = [f"{t} ({c})" for t, c in step_qs[:3]]
        insights.append(f"Explore hotspots: {', '.join(hotspot_strs)}")

    # 5. Data flow opportunities — duplicate info field names across steps
    field_names: dict[str, list[str]] = {}
    for s in steps:
        for f in s.get("information_fields") or []:
            if isinstance(f, dict):
                name = f.get("name", "")
                if name:
                    field_names.setdefault(name, []).append(s.get("title", "?"))
    shared = {
        name: titles for name, titles in field_names.items() if len(titles) > 1
    }
    if shared:
        shared_strs = [
            f"{name} (in {', '.join(titles)})"
            for name, titles in list(shared.items())[:3]
        ]
        insights.append(f"Shared data fields: {'; '.join(shared_strs)}")

    # 6. Staleness — steps with confidence_impact or needs_review
    stale_steps = [
        s.get("title", "?") for s in steps
        if s.get("confidence_impact") and s["confidence_impact"] > 0
    ]
    needs_review = [
        s.get("title", "?") for s in steps
        if s.get("confirmation_status") == "needs_review"
    ]
    if stale_steps:
        insights.append(f"Steps linked to stale entities: {', '.join(stale_steps[:3])}")
    if needs_review:
        insights.append(f"Steps needing review: {', '.join(needs_review[:3])}")

    return "\n".join(f"- {i}" for i in insights) if insights else ""


def _build_retrieval_hints(step: dict[str, Any]) -> list[str]:
    """Layer 4: 2-4 retrieval hint strings from focused step."""
    hints: list[str] = []

    # Goal text (most important)
    goal = step.get("goal", "")
    if goal and len(goal) > 10:
        hints.append(goal[:200])

    # Open question texts
    for q in (step.get("open_questions") or []):
        if isinstance(q, dict) and q.get("status") == "open":
            question = q.get("question", "")
            if question:
                hints.append(question[:150])
            if len(hints) >= 4:
                break

    # Actor names as search terms
    actors = step.get("actors") or []
    if actors and len(hints) < 4:
        hints.append(f"{', '.join(actors)} user experience")

    return hints[:4]


async def build_solution_flow_context(
    project_id: str,
    focused_step_id: str | None = None,
) -> SolutionFlowContext:
    """Build full solution flow context for chat prompts.

    Zero LLM cost, ~100ms. Pure DB reads + string formatting.

    Args:
        project_id: Project UUID string
        focused_step_id: Currently selected step ID (optional)

    Returns:
        SolutionFlowContext with 4 layers of prompt content
    """
    ctx = SolutionFlowContext()

    try:
        flow = get_or_create_flow(UUID(project_id))
        flow_id = flow["id"]

        # Load all steps
        steps = list_flow_steps(UUID(flow_id))
        if not steps:
            ctx.flow_summary_prompt = "No steps defined yet."
            return ctx

        # Layer 1: Flow summary
        ctx.flow_summary_prompt = _build_flow_summary(steps)

        # If we have a focused step, build detailed context
        if focused_step_id:
            focused_step = get_flow_step(UUID(focused_step_id))
            if focused_step:
                # Collect all entity IDs for batch resolution
                ids_by_table: dict[str, list[str]] = {}
                for key, table in [
                    ("linked_feature_ids", "features"),
                    ("linked_workflow_ids", "workflows"),
                    ("linked_data_entity_ids", "data_entities"),
                ]:
                    ids = focused_step.get(key) or []
                    if ids:
                        ids_by_table[table] = ids

                entity_lookup = _resolve_entity_names_batch(ids_by_table)

                # Find prev/next step titles
                step_index = focused_step.get("step_index", 0)
                prev_title = None
                next_title = None
                for s in steps:
                    if s.get("step_index") == step_index - 1:
                        prev_title = s.get("title")
                    elif s.get("step_index") == step_index + 1:
                        next_title = s.get("title")

                # Layer 2: Focused step detail
                ctx.focused_step_prompt = _build_focused_step(
                    focused_step, entity_lookup, prev_title, next_title
                )

                # Layer 4: Retrieval hints
                ctx.retrieval_hints = _build_retrieval_hints(focused_step)

                # Entity change delta — recent changes to linked entities
                ctx.entity_change_delta = _build_entity_change_delta(focused_step)

                # Confirmation history — step's own revision timeline
                ctx.confirmation_history = _build_confirmation_history(focused_step)
            else:
                logger.warning(f"Focused step not found in DB: {focused_step_id}")

        # Layer 3: Cross-step intelligence
        ctx.cross_step_prompt = _build_cross_step_intelligence(steps)

    except Exception as e:
        logger.warning(f"Failed to build solution flow context: {e}", exc_info=True)

    return ctx


def _build_entity_change_delta(step: dict[str, Any]) -> str:
    """Build a summary of recent changes to entities linked to this step."""
    from app.db.revisions_enrichment import list_entity_revisions

    all_linked_ids: list[tuple[str, str]] = []  # (entity_type, entity_id)
    for eid in step.get("linked_feature_ids") or []:
        all_linked_ids.append(("feature", eid))
    for eid in step.get("linked_workflow_ids") or []:
        all_linked_ids.append(("workflow", eid))
    for eid in step.get("linked_data_entity_ids") or []:
        all_linked_ids.append(("data_entity", eid))

    if not all_linked_ids:
        return ""

    changes: list[str] = []
    for entity_type, entity_id in all_linked_ids[:6]:  # Cap at 6 to limit DB calls
        try:
            revisions = list_entity_revisions(entity_type, UUID(entity_id), limit=3)
            for rev in revisions:
                diff = rev.get("diff_summary", "")
                label = rev.get("entity_label", entity_id[:8])
                if diff:
                    changes.append(f"- {entity_type} \"{label}\": {diff}")
        except Exception:
            continue

    return "\n".join(changes[:8]) if changes else ""


def _build_confirmation_history(step: dict[str, Any]) -> str:
    """Build a summary of this step's own revision history."""
    from app.db.revisions_enrichment import list_entity_revisions

    step_id = step.get("id")
    if not step_id:
        return ""

    try:
        revisions = list_entity_revisions("solution_flow_step", UUID(step_id), limit=5)
    except Exception:
        return ""

    if not revisions:
        status = step.get("confirmation_status", "ai_generated")
        version = step.get("generation_version", 1)
        return f"Status: {status}, generation version {version}. No revisions recorded."

    lines = [f"Status: {step.get('confirmation_status', 'ai_generated')} (v{step.get('generation_version', 1)})"]
    for rev in revisions:
        diff = rev.get("diff_summary", "updated")
        trigger = rev.get("trigger_event", "")
        created_at = rev.get("created_at", "")[:16]
        lines.append(f"- [{created_at}] {trigger}: {diff}")

    return "\n".join(lines)
