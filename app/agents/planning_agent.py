"""Planning Agent — ScreenMap generation for prototypes.

Three-phase pipeline:
  1. Deterministic assembly: ScreenMap skeleton from payload + prebuild (~50ms)
  2. Parallel Haiku enrichment: UX copy, refined props, interactions (~5s)
  3. Merge enrichments into skeleton

Produces a ScreenMap consumed by the scaffold renderer.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.core.schemas_prototype_builder import PrebuildIntelligence, PrototypePayload
from app.core.schemas_screen_map import Screen, ScreenMap, UXCopy

logger = logging.getLogger(__name__)


# =============================================================================
# Haiku Enrichment — parallel per-screen calls
# =============================================================================

ENRICHMENT_TOOL = {
    "name": "enrich_screen",
    "description": (
        "Submit enrichments for this screen: UX copy, component refinements, interactions."
    ),
    "input_schema": {
        "type": "object",
        "required": ["ux_copy"],
        "properties": {
            "ux_copy": {
                "type": "object",
                "properties": {
                    "headline": {"type": "string"},
                    "subtitle": {"type": "string"},
                    "pain_point_callout": {"type": "string"},
                    "value_prop": {"type": "string"},
                },
            },
            "component_refinements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "integer"},
                        "props_patch": {"type": "object"},
                    },
                },
            },
            "interactions": {
                "type": "array",
                "items": {"type": "string"},
            },
            "feel": {"type": "string"},
        },
    },
}


async def _enrich_single_screen(
    screen: Screen,
    payload: PrototypePayload,
    step_map: dict[str, Any],
    epic_data: dict | None,
) -> dict:
    """Enrich a single screen via one Haiku 4.5 call.

    Returns enrichment dict or empty dict on failure.
    """
    settings = get_settings()

    # Build context for this screen
    linked_steps = [step_map[sid] for sid in screen.solution_flow_step_ids if sid in step_map]
    step_context = "\n".join(
        f"- {getattr(s, 'title', '')}: goal={getattr(s, 'goal', '')}, "
        f"pain_points={[pp.get('text', '') if isinstance(pp, dict) else str(pp) for pp in (getattr(s, 'pain_points_addressed', []) or [])[:3]]}"  # noqa: E501
        for s in linked_steps
    )

    feature_context = "\n".join(f"- {name}" for name in (screen.features_shown or [])[:8])

    narrative = epic_data.get("narrative", "") if epic_data else ""

    component_summary = "\n".join(
        f"  [{i}] {c.type} (feature: {c.feature_id or 'none'})"
        for i, c in enumerate(screen.components)
    )

    prompt = f"""You are enriching a prototype screen skeleton with personality and polish.
The skeleton components are already built. Add UX copy, refine props, and describe interactions.

Screen: {screen.title} ({screen.route})
Layout: {screen.layout}
Depth: {screen.depth}

Epic narrative: {narrative[:500]}

Linked features:
{feature_context}

Linked solution flow steps:
{step_context}

Components on this screen:
{component_summary}

Domain: {payload.company_industry or "general"}
Primary user: {payload.personas[0].name if payload.personas else "User"} \
({payload.personas[0].role if payload.personas else "User"})
Project: {payload.project_name}

Provide enrichments using the enrich_screen tool. Be specific, domain-relevant, and inspiring.
The headline should make the user feel like THIS is the product they need.
The subtitle should ground the value proposition.
Interactions should describe what clickable elements do."""

    try:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            tools=[ENRICHMENT_TOOL],
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract tool use result
        for block in response.content:
            if block.type == "tool_use" and block.name == "enrich_screen":
                return block.input

    except Exception as e:
        logger.warning(f"Haiku enrichment failed for {screen.route}: {e}")

    return {}


async def _enrich_all_screens(
    skeleton: ScreenMap,
    payload: PrototypePayload,
    epic_plan: dict,
) -> list[dict]:
    """Run parallel Haiku enrichment for all screens."""
    step_map = {s.id: s for s in payload.solution_flow_steps}
    vision_epics = epic_plan.get("vision_epics", [])

    # Map routes to epic data
    epic_by_route: dict[str, dict] = {}
    for epic in vision_epics:
        route = epic.get("primary_route", "")
        if route:
            epic_by_route[route] = epic

    tasks = [
        _enrich_single_screen(
            screen=screen,
            payload=payload,
            step_map=step_map,
            epic_data=epic_by_route.get(screen.route),
        )
        for screen in skeleton.screens
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    enrichments = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning(f"Enrichment failed for screen {skeleton.screens[i].route}: {result}")
            enrichments.append({})
        else:
            enrichments.append(result)

    return enrichments


def _merge_enrichments(skeleton: ScreenMap, enrichments: list[dict]) -> ScreenMap:
    """Merge Haiku enrichments into the skeleton ScreenMap."""
    for i, enrichment in enumerate(enrichments):
        if i >= len(skeleton.screens) or not enrichment:
            continue

        screen = skeleton.screens[i]

        # UX copy
        ux_data = enrichment.get("ux_copy", {})
        if ux_data:
            existing_hl = screen.ux_copy.headline if screen.ux_copy else screen.title
            screen.ux_copy = UXCopy(
                headline=ux_data.get("headline", existing_hl),
                subtitle=ux_data.get("subtitle"),
                pain_point_callout=ux_data.get("pain_point_callout"),
                value_prop=ux_data.get("value_prop"),
            )

        # Component refinements
        for refinement in enrichment.get("component_refinements", []):
            idx = refinement.get("index", -1)
            patch = refinement.get("props_patch", {})
            if 0 <= idx < len(screen.components) and patch:
                screen.components[idx].props.update(patch)

        # Interactions
        interactions = enrichment.get("interactions", [])
        if interactions:
            screen.interactions = interactions

        # Feel
        feel = enrichment.get("feel")
        if feel:
            screen.feel = feel

    return skeleton


# =============================================================================
# Legacy Tool Handler (for backward compat fallback)
# =============================================================================


async def _handle_tool_call(
    tool_name: str,
    tool_input: dict[str, Any],
    project_id: UUID,
) -> str:
    """Route tool calls to existing infrastructure functions."""
    try:
        if tool_name == "query":
            return await _handle_query(tool_input, project_id)
        elif tool_name == "search":
            return await _handle_search(tool_input, project_id)
        elif tool_name == "inspect":
            return await _handle_inspect(tool_input, project_id)
        elif tool_name == "submit_screen_map":
            return json.dumps({"status": "accepted"})
        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
    except Exception as e:
        logger.error(f"Planning tool {tool_name} failed: {e}", exc_info=True)
        return json.dumps({"error": str(e), "tool": tool_name})


async def _handle_query(tool_input: dict, project_id: UUID) -> str:
    action = tool_input["action"]

    if action == "payload":
        from app.core.prototype_payload import assemble_prototype_payload

        resp = await assemble_prototype_payload(project_id)
        payload = resp.payload.model_dump()
        return json.dumps(payload, default=str)

    elif action == "solution_flow":
        from app.core.solution_flow_context import build_solution_flow_context

        ctx = await build_solution_flow_context(str(project_id))
        return json.dumps(
            {
                "flow_summary": ctx.flow_summary_prompt,
                "cross_step_insights": ctx.cross_step_prompt,
                "retrieval_hints": ctx.retrieval_hints,
            }
        )

    elif action == "horizons":
        from app.context.intelligence_signals import load_horizon_state

        state = await load_horizon_state(project_id)
        return json.dumps(state, default=str)

    elif action == "beliefs":
        from app.context.intelligence_signals import load_confidence_state

        state = await load_confidence_state(project_id)
        return json.dumps(state, default=str)

    elif action == "unlocks":
        from app.db.unlocks import list_unlocks

        unlocks = list_unlocks(str(project_id), limit=30)
        return json.dumps(
            [
                {
                    "id": u["id"],
                    "title": u.get("title", ""),
                    "insight": u.get("insight", ""),
                    "impact_type": u.get("impact_type", ""),
                    "tier": u.get("tier"),
                    "status": u.get("status", ""),
                    "linked_feature_id": u.get("linked_feature_id"),
                }
                for u in unlocks
            ],
            default=str,
        )

    elif action == "prebuild":
        from app.db.prototypes import get_prototype_for_project

        proto = get_prototype_for_project(str(project_id))
        if proto and proto.get("prebuild_intelligence"):
            return json.dumps(proto["prebuild_intelligence"], default=str)
        from app.graphs.prebuild_intelligence_graph import run_prebuild_intelligence

        result = await run_prebuild_intelligence(project_id)
        if result:
            return json.dumps(result.model_dump(), default=str)
        return json.dumps({"error": "No prebuild intelligence available"})

    return json.dumps({"error": f"Unknown query action: {action}"})


async def _handle_search(tool_input: dict, project_id: UUID) -> str:
    from app.core.chat_context import build_retrieval_context

    query = tool_input["query"]
    context = await build_retrieval_context(
        message=query,
        project_id=str(project_id),
        page_context=None,
        focused_entity=None,
    )
    return context if context else "No relevant results found."


async def _handle_inspect(tool_input: dict, project_id: UUID) -> str:
    from app.db.graph_queries import get_entity_neighborhood

    neighborhood = get_entity_neighborhood(
        entity_id=UUID(tool_input["entity_id"]),
        entity_type=tool_input["entity_type"],
        project_id=project_id,
        depth=tool_input.get("depth", 1),
        apply_recency=True,
        apply_confidence=True,
    )
    result = {
        "entity": neighborhood.get("entity", {}),
        "related": neighborhood.get("related", [])[:20],
        "stats": neighborhood.get("stats", {}),
    }
    return json.dumps(result, default=str)


# =============================================================================
# Legacy Agent Loop (fallback if no payload/prebuild provided)
# =============================================================================

# Tool definitions for legacy mode
PLANNING_TOOLS = [
    {
        "name": "query",
        "description": (
            "Query project data. Actions: payload, solution_flow, "
            "horizons, beliefs, unlocks, prebuild."
        ),
        "input_schema": {
            "type": "object",
            "required": ["action"],
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "payload",
                        "solution_flow",
                        "horizons",
                        "beliefs",
                        "unlocks",
                        "prebuild",
                    ],
                },
            },
        },
    },
    {
        "name": "search",
        "description": "Search project knowledge for specific topics.",
        "input_schema": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer", "default": 8},
            },
        },
    },
    {
        "name": "inspect",
        "description": "Deep-dive into a specific entity's graph neighborhood.",
        "input_schema": {
            "type": "object",
            "required": ["action", "entity_id", "entity_type"],
            "properties": {
                "action": {"type": "string", "enum": ["entity_neighborhood"]},
                "entity_id": {"type": "string"},
                "entity_type": {
                    "type": "string",
                    "enum": ["feature", "persona", "solution_flow_step", "driver", "constraint"],
                },
                "depth": {"type": "integer", "default": 1},
            },
        },
    },
    {
        "name": "submit_screen_map",
        "description": "Submit the completed ScreenMap specification.",
        "input_schema": ScreenMap.model_json_schema(),
    },
]

PLANNING_SYSTEM_PROMPT = """\
You are the Screen Architect for AIOS prototype generation. Produce a ScreenMap — \
a structured JSON specification for every screen in the prototype.

Research project data thoroughly via tools, then submit_screen_map with the complete spec.
The prototype should BE THE PRODUCT, not a presentation of the solution flow.

COMPONENT TYPES: hero, metric_grid, form, data_table, chart, card_grid, activity_feed, \
chat_interface, kanban, calendar, file_list, settings_form, stats_banner, timeline, tabs, \
horizon_roadmap, empty_state, ai_indicator, image_section, prose, cta_section
"""


async def _run_legacy_agent(
    project_id: UUID,
    project_name: str,
    feature_count: int,
) -> dict[str, Any]:
    """Fallback: run the full agentic loop when no payload/prebuild is available."""
    from anthropic import AsyncAnthropic

    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    thinking_budget = max(10_000, min(50_000, feature_count * 2000))

    logger.info(
        f"Planning Agent (legacy) starting for '{project_name}' "
        f"({feature_count} features, {thinking_budget} thinking tokens)"
    )

    messages: list[dict] = [
        {
            "role": "user",
            "content": (
                f"Plan the prototype for project '{project_name}' "
                f"(ID: {project_id}). "
                f"There are {feature_count} confirmed features. "
                f"Research the project data thoroughly, then produce a "
                f"complete ScreenMap specification."
            ),
        }
    ]

    tool_call_count = 0
    screen_map: ScreenMap | None = None
    start = time.monotonic()
    max_turns = 20

    for _turn in range(max_turns):
        try:
            max_tokens = thinking_budget + 16_000
            async with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=max_tokens,
                temperature=1,
                thinking={"type": "enabled", "budget_tokens": thinking_budget},
                system=PLANNING_SYSTEM_PROMPT,
                tools=PLANNING_TOOLS,
                messages=messages,
            ) as stream:
                response = await stream.get_final_message()
        except Exception as e:
            logger.error(f"Planning Agent API call failed: {e}", exc_info=True)
            raise

        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if not tool_use_blocks:
            break

        tool_results = []
        for tool_block in tool_use_blocks:
            tool_name = tool_block.name
            tool_input = tool_block.input
            tool_call_count += 1

            if tool_name == "submit_screen_map":
                try:
                    screen_map = ScreenMap.model_validate(tool_input)
                    result_str = json.dumps({"status": "accepted"})
                except Exception as e:
                    result_str = json.dumps({"status": "rejected", "error": str(e)})
            else:
                result_str = await _handle_tool_call(tool_name, tool_input, project_id)

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_block.id,
                    "content": result_str,
                }
            )

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

        if screen_map is not None:
            break

    duration = time.monotonic() - start

    if screen_map is None:
        raise RuntimeError(
            f"Planning Agent did not produce a ScreenMap after "
            f"{max_turns} turns and {tool_call_count} tool calls"
        )

    return {
        "screen_map": screen_map,
        "tool_calls": tool_call_count,
        "thinking_tokens": 0,
        "duration_s": round(duration, 1),
    }


# =============================================================================
# Main Entry Point
# =============================================================================


async def plan_prototype(
    project_id: UUID,
    payload: PrototypePayload | None = None,
    prebuild: PrebuildIntelligence | None = None,
    project_name: str = "",
    feature_count: int = 0,
) -> dict[str, Any]:
    """Produce a ScreenMap for the given project.

    Fast path (payload + prebuild provided):
      1. Deterministic assembly (~50ms)
      2. Parallel Haiku enrichment (~5s)
      3. Merge → final ScreenMap

    Fallback (no payload/prebuild):
      Legacy agentic loop with Sonnet + extended thinking.

    Returns:
        {screen_map: ScreenMap, tool_calls: int, thinking_tokens: int, duration_s: float}
    """
    start = time.monotonic()

    # ── Fast path: deterministic + Haiku enrichment ───────────────────
    if payload is not None and prebuild is not None:
        logger.info(
            f"Planning Agent (fast) starting for '{project_name}' "
            f"({len(payload.features)} features)"
        )

        # Phase 1: Deterministic assembly
        from app.core.screen_map_assembler import assemble_screen_map

        skeleton = assemble_screen_map(payload, prebuild)
        assembly_ms = (time.monotonic() - start) * 1000
        logger.info(f"ScreenMap skeleton assembled in {assembly_ms:.0f}ms")

        # Phase 2: Parallel Haiku enrichment
        enrichment_start = time.monotonic()
        enrichments = await _enrich_all_screens(skeleton, payload, prebuild.epic_plan or {})
        enrichment_s = time.monotonic() - enrichment_start
        logger.info(f"Haiku enrichment completed in {enrichment_s:.1f}s")

        # Phase 3: Merge
        screen_map = _merge_enrichments(skeleton, enrichments)

        duration = time.monotonic() - start
        logger.info(
            f"Planning Agent (fast) complete: {screen_map.total_screens} screens, "
            f"{duration:.1f}s (assembly={assembly_ms:.0f}ms, enrichment={enrichment_s:.1f}s)"
        )

        return {
            "screen_map": screen_map,
            "tool_calls": len(enrichments),
            "thinking_tokens": 0,
            "duration_s": round(duration, 1),
        }

    # ── Fallback: legacy agentic loop ─────────────────────────────────
    logger.info("No payload/prebuild provided — falling back to legacy agent")
    return await _run_legacy_agent(project_id, project_name, feature_count)
