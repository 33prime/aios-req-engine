"""Planning Agent — Screen Architect for prototype generation.

Two-phase agentic loop:
  Phase 1 (Research): Tool calls to query project data via 3 consolidated tools
  Phase 2 (Architect): Extended thinking to reason, then submit_screen_map

Produces a ScreenMap consumed by the scaffold renderer. Every architectural
decision is made here; downstream is mechanical.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any
from uuid import UUID

from anthropic import AsyncAnthropic

from app.core.config import get_settings
from app.core.schemas_screen_map import ScreenMap

logger = logging.getLogger(__name__)

# =============================================================================
# Tool Definitions (3 consolidated + 1 output)
# =============================================================================

PLANNING_TOOLS = [
    {
        "name": "query",
        "description": (
            "Query project data. Returns structured data from the project's "
            "confirmed entities and intelligence layers.\n\n"
            "Actions:\n"
            "- payload: All confirmed features, personas, solution flow steps, "
            "workflows, drivers, constraints, competitors, design contract. "
            "Call this FIRST.\n"
            "- solution_flow: Full solution flow context with cross-step insights, "
            "shared actors, shared data fields, feature→step mappings.\n"
            "- horizons: H1/H2/H3 crystallization, blocking outcomes, "
            "compound decisions.\n"
            "- beliefs: Memory nodes with confidence scores. Low confidence "
            "(<0.5) means uncertain — use conservative implementations.\n"
            "- unlocks: Strategic and tactical insights discovered during "
            "analysis. Promoted unlocks are linked to features.\n"
            "- prebuild: Phase 0 intelligence — journey epics (5-7), "
            "feature build specs with depth assignments (full/visual/placeholder), "
            "AI flow cards, horizon cards, discovery threads."
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
        "description": (
            "Search project knowledge for specific topics. Uses the full "
            "Tier 2.5 retrieval pipeline: decompose → retrieve → graph expand "
            "→ Cohere rerank. Returns reranked chunks with provenance and "
            "confidence scores.\n\n"
            "Use AFTER reading the payload to explore specific areas: pain "
            "points, competitive gaps, workflows, technical decisions, client "
            "statements about priority or vision."
        ),
        "input_schema": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language query. Be specific.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results (default 8).",
                    "default": 8,
                },
            },
        },
    },
    {
        "name": "inspect",
        "description": (
            "Deep-dive into a specific entity's graph neighborhood. Returns "
            "the entity with all connected entities via knowledge graph "
            "relationships (features, personas, drivers, constraints, workflows, "
            "signals). Use when a feature has complex relationships or you need "
            "to understand how entities connect.\n\n"
            "Actions:\n"
            "- entity_neighborhood: Full graph neighborhood with confidence "
            "overlay and recency weighting."
        ),
        "input_schema": {
            "type": "object",
            "required": ["action", "entity_id", "entity_type"],
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["entity_neighborhood"],
                },
                "entity_id": {
                    "type": "string",
                    "description": "UUID of the entity.",
                },
                "entity_type": {
                    "type": "string",
                    "enum": [
                        "feature",
                        "persona",
                        "solution_flow_step",
                        "driver",
                        "constraint",
                    ],
                },
                "depth": {
                    "type": "integer",
                    "description": (
                        "Graph expansion depth: 0=entity only, "
                        "1=direct neighbors, 2=neighbors of neighbors."
                    ),
                    "default": 1,
                },
            },
        },
    },
    {
        "name": "submit_screen_map",
        "description": (
            "Submit the completed ScreenMap specification. Call this ONCE after "
            "you have finished researching and reasoning. The ScreenMap must "
            "include every confirmed feature, realistic mock data, and "
            "complete component specifications for each screen.\n\n"
            "QUALITY CHECKLIST — verify before submitting:\n"
            "□ Every confirmed feature appears in feature_coverage\n"
            "□ Every screen has at least one component\n"
            "□ Every feature component has a feature_id (slug) for bridge wrapping\n"
            "□ Mock users use actual persona names\n"
            "□ Form components use information_fields from solution flow steps\n"
            "□ H2 features have depth 'visual', H3 features have depth 'placeholder'\n"
            "□ All image slots have fallback_gradient\n"
            "□ Navigation items match screen routes\n"
            "□ feature_coverage has no orphaned features"
        ),
        "input_schema": ScreenMap.model_json_schema(),
    },
]


# =============================================================================
# System Prompt
# =============================================================================

PLANNING_SYSTEM_PROMPT = """\
You are the Screen Architect for AIOS prototype generation. You receive a \
project's complete data (features, personas, solution flow, horizons, beliefs, \
unlocks, epics) and produce a ScreenMap — a structured JSON specification for \
every screen in the prototype.

Your output is consumed by a deterministic renderer that translates your spec \
into React + Tailwind code. The renderer has templates for specific component \
types. You don't write code — you specify WHAT appears on each screen, with \
what data, in what layout. The renderer builds it.

The prototype should BE THE PRODUCT. Not a presentation of the solution flow. \
If the solution flow says "User discovers relevant properties," the screen \
should show a property listing with search filters, map pins, and price cards \
— not a page that says "Discovery: explore properties."

═══════════════════════════════════════════════════════════════════
STEP 1 — RESEARCH (tool calls)
═══════════════════════════════════════════════════════════════════

1. Call query(action="payload") FIRST — this gives you all confirmed entities.
2. Call query(action="solution_flow") — understand the user journey.
3. Call query(action="prebuild") — get epics, feature depth assignments, \
   AI flow cards, horizon cards.
4. Call query(action="horizons") and query(action="beliefs") — understand \
   confidence and time horizons.
5. Call query(action="unlocks") — get strategic/tactical insights.
6. Based on what you learned, make 1-3 targeted search() calls for specific \
   topics: pain points, competitive gaps, key workflows, client priorities.
7. Optionally use inspect() for features with complex entity relationships.

Minimum 5 tool calls. Typically 6-9. Do not skip steps 1-5.

═══════════════════════════════════════════════════════════════════
STEP 2 — REASON (extended thinking)
═══════════════════════════════════════════════════════════════════

With all data loaded, reason through:

SCREEN INVENTORY:
- Start from epics (from prebuild intelligence) — each epic suggests a screen \
  or screen section. Epics are the PRIMARY grouping mechanism.
- Within each epic, use solution flow steps to determine component order.
- Use linked_feature_ids on steps to know which features appear on which screens.
- If a step has no linked features, distribute unlinked features by relevance.
- H1 features get full screens. H2 features get visual sections. H3 features \
  all go on a single /roadmap screen.
- EVERY confirmed feature must appear somewhere in the prototype.
- Target 5-8 screens total. Dense > sparse. 5 rich screens > 13 empty ones.

NAVIGATION PATTERN:
- 2-4 screens → top_tabs or wizard_flow
- 5-8 screens → sidebar
- 9+ screens → sidebar with grouped sections
- Linear journey (entry→core→output) → consider wizard_flow for entry screens
- Parallel paths or dashboard-centric → sidebar

COMPONENT SELECTION (use information_fields to drive this):
- information_fields with type "captured" → form component (input fields!)
- information_fields with type "displayed" → data_table or card_grid
- information_fields with type "computed" → metric_grid or chart
- ai_config present on step → add ai_indicator component
- implied_pattern on step → select matching component template
- success_criteria → metric cards showing target values
- pain_points_addressed → UX copy callouts

MOCK DATA — MUST BE REALISTIC:
- Use persona names as mock users (actual name from persona, actual role)
- Use information_field mock_values as form pre-fills and table data
- Generate 6-10 realistic data rows per table (domain-appropriate)
- Use pain_points_addressed text for empty-state copy and value props
- Currency, dates, entities should match the project domain

IMAGES:
- If step has image_url → use source "url" with that Supabase URL
- If design tokens include logo_url → use for branding
- Hero backgrounds → source "gradient" (primary → secondary)
- Avatars → source "initials" from persona names
- Feature illustrations → source "icon" from lucide-react
- EVERY image slot must have a fallback_gradient

DEPTH RULES (from prebuild feature_specs):
- full → all components interactive, mock data, state management
- visual → beautiful static mockup, limited interactions, can show "Coming \
  Soon" badge
- placeholder → single card on /roadmap with title + description + horizon badge

UNLOCKS:
- Strategic unlocks → hero headline or value proposition in ux_copy
- Promoted unlocks (linked to features) → give those features more prominence
- Competitive insights → differentiation callouts in ux_copy

CONFIDENCE:
- Low confidence beliefs (<0.5) → conservative component choices, simpler UI
- Open questions on steps → note in screen's ux_copy, pick safe defaults
- High open_question_count on features → reduce depth regardless of assignment

═══════════════════════════════════════════════════════════════════
STEP 3 — OUTPUT (submit_screen_map)
═══════════════════════════════════════════════════════════════════

Call submit_screen_map with the complete ScreenMap. One call. Include:
- app_shell with correct navigation pattern and nav_items
- All screens with components, images, interactions, ux_copy
- mock_context with primary + secondary users from personas
- image_manifest for all referenced images
- feature_coverage mapping every feature slug to its screen route
- depth_summary counts
- planning_notes summarizing your key decisions

COMPONENT TYPES AVAILABLE:
hero, metric_grid, form, data_table, chart, card_grid, activity_feed, \
chat_interface, kanban, calendar, file_list, settings_form, stats_banner, \
timeline, tabs, horizon_roadmap, empty_state, ai_indicator, image_section, \
prose, cta_section

Use ONLY these types. The renderer has templates for each one.
"""


# =============================================================================
# Tool Handler — routes to existing infrastructure
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
            # Validated by caller — just echo back for extraction
            return json.dumps({"status": "accepted"})
        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
    except Exception as e:
        logger.error(f"Planning tool {tool_name} failed: {e}", exc_info=True)
        return json.dumps({"error": str(e), "tool": tool_name})


async def _handle_query(tool_input: dict, project_id: UUID) -> str:
    """Handle consolidated query tool."""
    action = tool_input["action"]

    if action == "payload":
        from app.core.prototype_payload import assemble_prototype_payload

        resp = await assemble_prototype_payload(project_id)
        payload = resp.payload.model_dump()
        # Truncate verbose fields to stay within context
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
        # Return only relevant fields
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
        # Run prebuild if not cached
        from app.graphs.prebuild_intelligence_graph import run_prebuild_intelligence

        result = await run_prebuild_intelligence(project_id)
        if result:
            return json.dumps(result.model_dump(), default=str)
        return json.dumps({"error": "No prebuild intelligence available"})

    return json.dumps({"error": f"Unknown query action: {action}"})


async def _handle_search(tool_input: dict, project_id: UUID) -> str:
    """Handle knowledge search via 2.5 retrieval pipeline."""
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
    """Handle entity neighborhood inspection."""
    from app.db.graph_queries import get_entity_neighborhood

    neighborhood = get_entity_neighborhood(
        entity_id=UUID(tool_input["entity_id"]),
        entity_type=tool_input["entity_type"],
        project_id=project_id,
        depth=tool_input.get("depth", 1),
        apply_recency=True,
        apply_confidence=True,
    )
    # Trim to essential fields
    result = {
        "entity": neighborhood.get("entity", {}),
        "related": neighborhood.get("related", [])[:20],
        "stats": neighborhood.get("stats", {}),
    }
    return json.dumps(result, default=str)


# =============================================================================
# Agent Loop
# =============================================================================


async def plan_prototype(
    project_id: UUID,
    project_name: str = "",
    feature_count: int = 0,
) -> dict[str, Any]:
    """Run the Planning Agent to produce a ScreenMap.

    Args:
        project_id: Project UUID
        project_name: Display name for logging
        feature_count: Confirmed feature count (for thinking budget)

    Returns:
        {screen_map: ScreenMap, tool_calls: int, thinking_tokens: int, duration_s: float}
    """
    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Thinking budget scales with complexity
    thinking_budget = max(10_000, min(50_000, feature_count * 2000))

    logger.info(
        f"Planning Agent starting for '{project_name}' "
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
    thinking_tokens_used = 0
    screen_map: ScreenMap | None = None
    start = time.monotonic()
    max_turns = 20

    for turn in range(max_turns):
        try:
            response = await client.messages.create(
                model="claude-sonnet-4-5-20250514",
                max_tokens=16_000,
                temperature=1,  # required for extended thinking
                thinking={
                    "type": "enabled",
                    "budget_tokens": thinking_budget,
                },
                system=PLANNING_SYSTEM_PROMPT,
                tools=PLANNING_TOOLS,
                messages=messages,
            )
        except Exception as e:
            logger.error(f"Planning Agent API call failed: {e}", exc_info=True)
            raise

        # Track thinking token usage
        if hasattr(response, "usage") and response.usage:
            thinking_tokens_used += getattr(response.usage, "cache_creation_input_tokens", 0)

        # Check for tool use
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if not tool_use_blocks:
            # Agent is done (end_turn with no tools)
            logger.info(
                f"Planning Agent finished in {turn + 1} turns, {tool_call_count} tool calls"
            )
            break

        # Process tool calls
        tool_results = []
        for tool_block in tool_use_blocks:
            tool_name = tool_block.name
            tool_input = tool_block.input
            tool_call_count += 1

            logger.info(
                f"Planning Agent tool call #{tool_call_count}: "
                f"{tool_name}({json.dumps(tool_input, default=str)[:200]})"
            )

            # Check for submit_screen_map — extract and validate
            if tool_name == "submit_screen_map":
                try:
                    screen_map = ScreenMap.model_validate(tool_input)
                    logger.info(
                        f"ScreenMap accepted: {screen_map.total_screens} screens, "
                        f"{len(screen_map.feature_coverage)} features covered"
                    )
                    result_str = json.dumps({"status": "accepted"})
                except Exception as e:
                    logger.warning(f"ScreenMap validation failed: {e}")
                    result_str = json.dumps(
                        {
                            "status": "rejected",
                            "error": str(e),
                            "hint": "Fix the validation errors and resubmit.",
                        }
                    )
            else:
                result_str = await _handle_tool_call(tool_name, tool_input, project_id)

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_block.id,
                    "content": result_str,
                }
            )

        # Append assistant message + tool results
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

        # If we got a valid screen_map, we're done
        if screen_map is not None:
            break

    duration = time.monotonic() - start

    if screen_map is None:
        raise RuntimeError(
            f"Planning Agent did not produce a ScreenMap after "
            f"{max_turns} turns and {tool_call_count} tool calls"
        )

    logger.info(
        f"Planning Agent complete: {screen_map.total_screens} screens, "
        f"{tool_call_count} tool calls, {duration:.1f}s"
    )

    return {
        "screen_map": screen_map,
        "tool_calls": tool_call_count,
        "thinking_tokens": thinking_tokens_used,
        "duration_s": round(duration, 1),
    }
