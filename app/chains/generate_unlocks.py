"""Generate strategic unlocks for a project using Sonnet.

Unlocks are strategic business outcomes that become possible when software
automates work — not features, but shifts in what a business can do, be, or reach.

Uses Anthropic tool_use for forced structured output (same pattern as
extract_entity_patches.py).
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


# =============================================================================
# Tool schema for forced structured output
# =============================================================================

UNLOCK_TOOL = {
    "name": "submit_unlocks",
    "description": "Submit the generated strategic unlocks.",
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
                            "description": "One-sentence outcome statement",
                        },
                        "narrative": {
                            "type": "string",
                            "description": "2-3 sentences: why this is now possible and what changes",
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
                            "description": "Quantified impact where possible, e.g. '3x client volume without hiring'",
                        },
                        "why_now": {
                            "type": "string",
                            "description": "What in the project enables this",
                        },
                        "non_obvious": {
                            "type": "string",
                            "description": "Why the client hasn't seen this yet — the consultant's superpower",
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

SYSTEM_PROMPT = """You are a senior strategy consultant analyzing what becomes STRATEGICALLY POSSIBLE for a business because of the system being built.

## What Unlocks Are
Unlocks are NOT features. They are business outcomes — what the organisation can now DO, BE, or REACH that was previously impossible, impractical, or invisible.

Examples of good unlocks:
- "Onboard new clients in hours instead of weeks" (operational_scale)
- "Run 3x the campaigns with the same team" (talent_leverage)
- "Eliminate manual reconciliation errors that cost $200k/year" (risk_elimination)
- "Offer real-time pricing that competitors can't match" (revenue_expansion)

Examples of BAD unlocks (too generic):
- "Better user experience" — too vague
- "Faster processing" — too obvious
- "Cost savings" — not specific to this project

## Your Task
Generate EXACTLY 9 unlocks in 3 tiers of 3:

**Tier 1: implement_now** (3 unlocks)
Quick wins that ride the core build. These are outcomes that fall out naturally from the workflows already being automated.

**Tier 2: after_feedback** (3 unlocks)
Layer on once the solution is validated. These require the core to work first, then enable a step-change.

**Tier 3: if_this_works** (3 unlocks)
Strategic bets on platform success. Bigger, bolder outcomes that become possible if the system proves itself.

## Rules
1. Every unlock MUST trace back to specific project entities with typed relationships (provenance).
2. The non_obvious field explains why the client probably hasn't seen this yet — this is the consultant's superpower.
3. DO NOT suggest generic improvements. Every unlock must be grounded in THIS project's specific workflows, data, and pains.
4. Use a mix of impact_types across the 9 unlocks — don't repeat the same type more than 3 times.
5. unlock_kind: "new_capability" = something that was never possible before; "feature_upgrade" = something that existed but gets dramatically better.
6. magnitude should quantify where possible: time saved, revenue unlocked, risk eliminated, capacity multiplied.
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

    # Data entities
    de_resp = (
        supabase.table("data_entities")
        .select("id, name, description, fields")
        .eq("project_id", pid)
        .execute()
    )
    data_ents = de_resp.data or []
    if data_ents:
        lines = ["## Data Entities"]
        for de in data_ents:
            lines.append(f"- **{de.get('name', '?')}** (id: {de['id']})")
            if de.get("description"):
                lines.append(f"  {de['description'][:150]}")
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
    """Generate 9 strategic unlocks for the given project.

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

    settings = Settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    system_blocks = [
        {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}},
    ]

    user_prompt = (
        f"Analyze the following project and generate exactly 9 strategic unlocks "
        f"(3 per tier).\n\n{context_text}"
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
