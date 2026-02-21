"""Generate capability unlocks for a project using Sonnet.

Unlocks are concrete capabilities that become possible when the system is built —
grounded in specific workflows, data entities, and user pains. Each unlock includes
a feature sketch that makes it directly promotable to a feature.

Uses Anthropic tool_use for forced structured output (same pattern as
extract_entity_patches.py).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2
_INITIAL_DELAY = 1.0


# =============================================================================
# Tool schema for forced structured output
# =============================================================================

UNLOCK_TOOL = {
    "name": "submit_unlocks",
    "description": "Submit the generated capability unlocks.",
    "input_schema": {
        "type": "object",
        "properties": {
            "unlocks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "One-sentence capability statement — what the system could now do. Start with a verb.",
                        },
                        "narrative": {
                            "type": "string",
                            "description": "2-3 sentences: what specific data/workflow makes this possible and what changes for the user",
                        },
                        "feature_sketch": {
                            "type": "string",
                            "description": "One concrete feature description ready to become a backlog item. Format: 'Add a [component] that [does what] using [which data/workflow]'",
                        },
                        "impact_type": {
                            "type": "string",
                            "enum": [
                                "operational_scale",
                                "talent_leverage",
                                "risk_elimination",
                                "revenue_expansion",
                                "data_intelligence",
                                "compliance",
                                "speed_to_change",
                            ],
                        },
                        "unlock_kind": {
                            "type": "string",
                            "enum": ["new_capability", "feature_upgrade"],
                        },
                        "tier": {
                            "type": "string",
                            "enum": [
                                "implement_now",
                                "after_feedback",
                                "if_this_works",
                            ],
                        },
                        "magnitude": {
                            "type": "string",
                            "description": "One short sentence: quantified impact using specific numbers. Reference entities by NAME only, never by UUID/ID. Example: 'Reduces resource selection from ~8 options to 1 personalized pick per user'",
                        },
                        "why_now": {
                            "type": "string",
                            "description": "Which specific workflow step or data entity makes this possible — reference by name",
                        },
                        "non_obvious": {
                            "type": "string",
                            "description": "Why the client hasn't thought of this — what cross-cutting insight the consultant sees",
                        },
                        "provenance": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "entity_type": {
                                        "type": "string",
                                        "enum": [
                                            "workflow",
                                            "feature",
                                            "pain",
                                            "goal",
                                            "kpi",
                                            "competitor",
                                            "data_entity",
                                        ],
                                    },
                                    "entity_id": {"type": "string"},
                                    "entity_name": {"type": "string"},
                                    "relationship": {
                                        "type": "string",
                                        "enum": [
                                            "enables",
                                            "solves",
                                            "serves",
                                            "validated_by",
                                        ],
                                    },
                                },
                                "required": [
                                    "entity_type",
                                    "entity_id",
                                    "entity_name",
                                    "relationship",
                                ],
                            },
                            "minItems": 1,
                            "maxItems": 4,
                        },
                    },
                    "required": [
                        "title",
                        "narrative",
                        "feature_sketch",
                        "impact_type",
                        "unlock_kind",
                        "tier",
                        "magnitude",
                        "why_now",
                        "non_obvious",
                        "provenance",
                    ],
                },
                "minItems": 9,
                "maxItems": 9,
            },
        },
        "required": ["unlocks"],
    },
}


# =============================================================================
# System prompt
# =============================================================================

SYSTEM_PROMPT = """You are a senior product consultant analyzing what concrete capabilities become possible because of the system being built.

## What Unlocks Are

Unlocks are CAPABILITIES — specific things the system could do that nobody has explicitly asked for yet. They emerge from looking at the workflows being automated, the data being collected, and the pain points being solved, then asking: "What else becomes possible now?"

Think of unlocks as the consultant's superpower: the client asked for workflow automation, but you can see that the data flowing through those workflows enables capabilities they haven't imagined.

## How to Find Good Unlocks

1. **Look at the data entities** — what information is being captured? What could you DO with that data beyond its primary purpose?
2. **Look at workflow transitions** — where a manual step becomes automated, what new speed or scale does that create?
3. **Look at pain points** — the system solves the stated pain, but what ADJACENT pain does the same solution address?
4. **Look across personas** — data captured for one user type often serves another user type in unexpected ways.

## Examples of GOOD Unlocks (functionality-grounded)

- "Auto-generate personalized study plans from assessment weak-spot data" → feature_sketch: "Add a 'My Study Plan' tab that maps weak topic areas to educational resources using QuestionAttempt performance data"
- "Flag at-risk accounts before renewal by correlating usage drop-offs with support tickets" → feature_sketch: "Add an 'Account Health' dashboard widget that scores engagement trends against historical churn signals"
- "Let managers clone a top performer's workflow template for new hires" → feature_sketch: "Add a 'Save as Template' action on completed workflows that extracts the step sequence and timing benchmarks"

## Examples of BAD Unlocks (too abstract)

- "Position the company as a market leader" — not a capability
- "Improve operational efficiency" — too vague
- "Enable data-driven decisions" — says nothing specific
- "Reduce costs across the organization" — not grounded in a feature

## Your Task

Generate EXACTLY 9 unlocks in 3 tiers of 3:

**Tier 1: implement_now** (3 unlocks)
Low-hanging fruit that falls out of existing data and workflows with minimal extra build. The data is already there — you just need a view, a trigger, or a small integration.

**Tier 2: after_feedback** (3 unlocks)
Smart extensions that add a screen, report, or integration on top of the core. Requires the core to work first, then enables a meaningful new capability.

**Tier 3: if_this_works** (3 unlocks)
Platform plays — bigger capabilities that require the system to prove itself first. These involve combining multiple data sources or workflows in ways that create compound value.

## Rules

1. Every unlock MUST reference specific data entities, workflow steps, or features by name in the provenance AND in the why_now field.
2. The feature_sketch MUST be concrete enough to become a backlog item. Format: "Add a [component] that [does what] using [which data/workflow]".
3. At least 5 of the 9 unlocks must reference a data_entity in their provenance — data is where hidden capabilities live.
4. DO NOT generate revenue projections or market positioning statements. Focus on what the SYSTEM can do.
5. unlock_kind: "new_capability" = something the system couldn't do before; "feature_upgrade" = an existing feature that gets dramatically smarter or faster.
6. The non_obvious field should explain the cross-cutting insight: what connection between entities/workflows/personas reveals this capability.
7. magnitude should be ONE short sentence with specific numbers: "reduces X from Y to Z", "eliminates N manual steps", "surfaces patterns across N records". NEVER include UUIDs or entity IDs — reference entities by NAME only.
"""


# =============================================================================
# Context assembly
# =============================================================================


async def _load_project_context(project_id: UUID) -> str:
    """Load project data for unlock generation context."""
    from app.db.supabase_client import get_supabase

    supabase = get_supabase()
    pid = str(project_id)
    sections: list[str] = []

    # Workflows with steps
    wf_resp = supabase.table("workflows").select("*").eq("project_id", pid).execute()
    workflows = wf_resp.data or []
    if workflows:
        lines = ["## Workflows"]
        for wf in workflows:
            lines.append(f"- **{wf.get('name', 'Untitled')}** (id: {wf['id']})")
            if wf.get("description"):
                lines.append(f"  {wf['description']}")
            # Load steps
            steps_resp = (
                supabase.table("vp_steps")
                .select("*")
                .eq("workflow_id", wf["id"])
                .order("step_index")
                .execute()
            )
            for step in steps_resp.data or []:
                auto = step.get("automation_level", "manual")
                time_m = step.get("time_minutes", "?")
                lines.append(
                    f"  - Step {step.get('step_index', '?')}: {step.get('label', '?')} "
                    f"[{step.get('operation_type', '?')}] ({auto}, {time_m}m)"
                )
                if step.get("pain_description"):
                    lines.append(f"    Pain: {step['pain_description']}")
                if step.get("benefit_description"):
                    lines.append(f"    Benefit: {step['benefit_description']}")
        sections.append("\n".join(lines))

    # Features
    feat_resp = (
        supabase.table("features")
        .select("id, name, overview, priority_group, confirmation_status")
        .eq("project_id", pid)
        .execute()
    )
    features = feat_resp.data or []
    if features:
        lines = ["## Features"]
        for f in features:
            pri = f.get("priority_group", "unset")
            lines.append(f"- **{f.get('name', '?')}** (id: {f['id']}, priority: {pri})")
            if f.get("overview"):
                lines.append(f"  {f['overview'][:200]}")
        sections.append("\n".join(lines))

    # Business drivers (goals, KPIs, pains)
    bd_resp = (
        supabase.table("business_drivers")
        .select("id, driver_type, description, severity, priority")
        .eq("project_id", pid)
        .execute()
    )
    drivers = bd_resp.data or []
    if drivers:
        lines = ["## Business Drivers"]
        for d in drivers:
            sev = d.get("severity", "")
            desc = d.get("description", "?")
            short_desc = desc[:80] if desc else "?"
            lines.append(
                f"- [{d.get('driver_type', '?')}] **{short_desc}** "
                f"(id: {d['id']}{', severity: ' + sev if sev else ''})"
            )
            if desc and len(desc) > 80:
                lines.append(f"  {desc[:200]}")
        sections.append("\n".join(lines))

    # Personas
    pers_resp = (
        supabase.table("personas")
        .select("id, name, role, goals, pain_points")
        .eq("project_id", pid)
        .execute()
    )
    personas = pers_resp.data or []
    if personas:
        lines = ["## Personas"]
        for p in personas:
            lines.append(f"- **{p.get('name', '?')}** — {p.get('role', '?')} (id: {p['id']})")
            if p.get("goals"):
                goals = p["goals"] if isinstance(p["goals"], list) else [p["goals"]]
                lines.append(f"  Goals: {', '.join(str(g) for g in goals[:3])}")
            if p.get("pain_points"):
                pains = p["pain_points"] if isinstance(p["pain_points"], list) else [p["pain_points"]]
                lines.append(f"  Pains: {', '.join(str(pp) for pp in pains[:3])}")
        sections.append("\n".join(lines))

    # Data entities — CRITICAL for capability discovery
    de_resp = (
        supabase.table("data_entities")
        .select("id, name, description, fields")
        .eq("project_id", pid)
        .execute()
    )
    data_ents = de_resp.data or []
    if data_ents:
        lines = ["## Data Entities (key source for capability discovery)"]
        for de in data_ents:
            lines.append(f"- **{de.get('name', '?')}** (id: {de['id']})")
            if de.get("description"):
                lines.append(f"  {de['description'][:200]}")
            fields = de.get("fields") or []
            if fields and isinstance(fields, list):
                field_names = [f.get("name", "?") if isinstance(f, dict) else str(f) for f in fields[:8]]
                lines.append(f"  Fields: {', '.join(field_names)}")
        sections.append("\n".join(lines))

    # Competitors
    comp_resp = (
        supabase.table("competitor_references")
        .select("id, name, category, strengths, weaknesses, key_differentiator")
        .eq("project_id", pid)
        .eq("reference_type", "competitor")
        .execute()
    )
    competitors = comp_resp.data or []
    if competitors:
        lines = ["## Competitors"]
        for c in competitors:
            lines.append(f"- **{c.get('name', '?')}** (id: {c['id']}, category: {c.get('category', '?')})")
            if c.get("key_differentiator"):
                lines.append(f"  Differentiator: {c['key_differentiator']}")
            if c.get("strengths"):
                lines.append(f"  Strengths: {', '.join(c['strengths'][:3])}")
            if c.get("weaknesses"):
                lines.append(f"  Weaknesses: {', '.join(c['weaknesses'][:3])}")
        sections.append("\n".join(lines))

    # Vision
    proj_resp = (
        supabase.table("projects")
        .select("vision")
        .eq("id", pid)
        .maybe_single()
        .execute()
    )
    if proj_resp.data and proj_resp.data.get("vision"):
        sections.append(f"## Project Vision\n{proj_resp.data['vision'][:500]}")

    return "\n\n".join(sections) if sections else "No project data available yet."


# =============================================================================
# Main generation function
# =============================================================================


async def generate_unlocks(project_id: UUID) -> list[dict[str, Any]]:
    """Generate 9 capability unlocks for the given project.

    Returns:
        List of unlock dicts ready for bulk_create_unlocks().
    """
    from anthropic import (
        APIConnectionError,
        APITimeoutError,
        AsyncAnthropic,
        InternalServerError,
        RateLimitError,
    )

    from app.core.config import Settings

    context_text = await _load_project_context(project_id)

    # Parallel retrieval for three unlock tiers
    try:
        from app.core.retrieval import retrieve
        from app.core.retrieval_format import format_retrieval_for_context

        operational, strategic, visionary = await asyncio.gather(
            retrieve(
                query="workflow automation pain manual process efficiency",
                project_id=str(project_id),
                entity_types=["workflow", "feature"],
                skip_evaluation=True, skip_reranking=True,
            ),
            retrieve(
                query="competitive advantage differentiation market position",
                project_id=str(project_id),
                entity_types=["competitor", "business_driver"],
                skip_evaluation=True, skip_reranking=True,
            ),
            retrieve(
                query="vision future state transformation scale",
                project_id=str(project_id),
                entity_types=["feature", "business_driver"],
                skip_evaluation=True, skip_reranking=True,
            ),
        )
        tier_evidence = []
        for label, result in [("Operational", operational), ("Strategic", strategic), ("Visionary", visionary)]:
            evidence = format_retrieval_for_context(result, style="generation", max_tokens=600)
            if evidence:
                tier_evidence.append(f"### {label} Evidence\n{evidence}")
        if tier_evidence:
            context_text += "\n\n## Retrieved Evidence by Tier\n" + "\n\n".join(tier_evidence)
    except Exception:
        pass  # Non-blocking

    settings = Settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    system_blocks = [
        {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}},
    ]

    user_prompt = (
        f"Analyze the following project data. Focus on the data entities and workflow steps "
        f"to discover hidden capabilities. Generate exactly 9 unlocks (3 per tier), each with "
        f"a concrete feature_sketch.\n\n{context_text}"
    )

    last_error: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            t0 = time.monotonic()
            response = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=8000,
                system=system_blocks,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=0.4,
                tools=[UNLOCK_TOOL],
                tool_choice={"type": "tool", "name": "submit_unlocks"},
            )
            elapsed_ms = int((time.monotonic() - t0) * 1000)

            # Extract tool result
            for block in response.content:
                if block.type == "tool_use" and block.name == "submit_unlocks":
                    unlocks = block.input.get("unlocks", [])
                    logger.info(
                        f"Generated {len(unlocks)} unlocks for project {project_id} "
                        f"in {elapsed_ms}ms"
                    )
                    return unlocks

            logger.warning("No tool_use block found in response")
            return []

        except (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError) as e:
            last_error = e
            if attempt < _MAX_RETRIES:
                delay = _INITIAL_DELAY * (2**attempt)
                logger.warning(
                    f"Transient error on attempt {attempt + 1}: {e}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"All {_MAX_RETRIES + 1} attempts failed: {e}")

    if last_error:
        raise last_error
    return []
