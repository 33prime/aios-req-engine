"""Coherence Agent — Sonnet produces a structured project plan.

Takes raw payload + prebuild data and makes all the architectural
decisions: screen grouping, nav structure, component selection,
theme application, and agent assignments.

Output is a structured JSON plan that Haiku builders execute.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from app.core.config import get_settings
from app.core.schemas_prototype_builder import PrebuildIntelligence, PrototypePayload

logger = logging.getLogger(__name__)

# =============================================================================
# Tool schema — structured output for the project plan
# =============================================================================

COHERENCE_TOOL = {
    "name": "submit_project_plan",
    "description": "Submit the complete project plan for the prototype build.",
    "input_schema": {
        "type": "object",
        "required": [
            "app_name",
            "theme",
            "nav_sections",
            "design_direction",
            "shared_patterns",
            "agent_assignments",
            "shared_data",
            "route_manifest",
        ],
        "properties": {
            "app_name": {
                "type": "string",
                "description": "Short app name for branding (e.g. 'PersonaPulse')",
            },
            "theme": {
                "type": "object",
                "description": "Visual theme decisions",
                "properties": {
                    "sidebar_bg": {
                        "type": "string",
                        "description": "Tailwind bg class for sidebar (e.g. 'bg-slate-900')",
                    },
                    "sidebar_text": {
                        "type": "string",
                        "description": (
                            "Tailwind text class for sidebar text (e.g. 'text-slate-300')"
                        ),
                    },
                    "sidebar_active_bg": {
                        "type": "string",
                        "description": "Active nav item style (e.g. 'bg-primary/10 text-primary')",
                    },
                    "content_bg": {
                        "type": "string",
                        "description": "Tailwind bg class for content area (e.g. 'bg-gray-50')",
                    },
                    "accent_usage": {
                        "type": "string",
                        "description": "How to use the primary/accent colors throughout the app",
                    },
                },
            },
            "nav_sections": {
                "type": "array",
                "description": "Navigation sections (sidebar groups)",
                "items": {
                    "type": "object",
                    "required": ["label", "screens"],
                    "properties": {
                        "label": {
                            "type": "string",
                            "description": (
                                "Section header (e.g. 'MAIN', 'ANALYTICS'). Use ALL CAPS."
                            ),
                        },
                        "screens": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": [
                                    "route",
                                    "nav_label",
                                    "page_title",
                                    "icon",
                                    "layout",
                                    "components",
                                ],
                                "properties": {
                                    "route": {
                                        "type": "string",
                                        "description": "URL path (e.g. '/dashboard')",
                                    },
                                    "nav_label": {
                                        "type": "string",
                                        "description": "Short sidebar label. 1-2 words ONLY.",
                                    },
                                    "page_title": {
                                        "type": "string",
                                        "description": "Full page title shown in header",
                                    },
                                    "icon": {
                                        "type": "string",
                                        "description": (
                                            "Lucide icon name in "
                                            "PascalCase "
                                            "(e.g. 'LayoutDashboard')"
                                        ),
                                    },
                                    "layout": {
                                        "type": "string",
                                        "enum": [
                                            "dashboard",
                                            "form-wizard",
                                            "split",
                                            "list",
                                            "detail",
                                            "settings",
                                            "landing",
                                        ],
                                        "description": "Page layout pattern",
                                    },
                                    "components": {
                                        "type": "array",
                                        "description": "Components on this page, in order",
                                        "items": {
                                            "type": "object",
                                            "required": [
                                                "type",
                                                "feature_slug",
                                                "guidance",
                                            ],
                                            "properties": {
                                                "type": {
                                                    "type": "string",
                                                    "description": "Component type",
                                                    "enum": [
                                                        "hero",
                                                        "metric_grid",
                                                        "form",
                                                        "data_table",
                                                        "chart",
                                                        "card_grid",
                                                        "activity_feed",
                                                        "chat_interface",
                                                        "kanban",
                                                        "calendar",
                                                        "settings_form",
                                                        "tabs",
                                                        "timeline",
                                                        "wizard_stepper",
                                                        "split_detail",
                                                        "stat_row",
                                                        "list_with_actions",
                                                    ],
                                                },
                                                "feature_slug": {
                                                    "type": "string",
                                                    "description": (
                                                        "Feature slug for "
                                                        "bridge wrapper "
                                                        "(kebab-case)"
                                                    ),
                                                },
                                                "title": {
                                                    "type": "string",
                                                    "description": (
                                                        "Section title "
                                                        "(optional, shown "
                                                        "above component)"
                                                    ),
                                                },
                                                "guidance": {
                                                    "type": "string",
                                                    "description": (
                                                        "Detailed rendering "
                                                        "guidance for the "
                                                        "builder. Include "
                                                        "specific mock data "
                                                        "values, column "
                                                        "names, field labels,"
                                                        " metric values, "
                                                        "card content, etc. "
                                                        "Be VERY specific — "
                                                        "the builder will "
                                                        "follow this "
                                                        "literally."
                                                    ),
                                                },
                                            },
                                        },
                                    },
                                    "ux_copy": {
                                        "type": "object",
                                        "properties": {
                                            "headline": {
                                                "type": "string",
                                                "description": "Page headline",
                                            },
                                            "subtitle": {
                                                "type": "string",
                                                "description": "Page subtitle/description",
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            },
            "design_direction": {
                "type": "string",
                "description": (
                    "2-3 sentences describing the overall visual direction. "
                    "What should this app FEEL like? What aesthetic references? "
                    "This guides the builders' styling choices."
                ),
            },
            "shared_patterns": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "List of shared patterns/rules for builders. "
                    "E.g. 'Use gradient-hero class for section headers', "
                    "'All action buttons use primary variant', etc."
                ),
            },
            "agent_assignments": {
                "type": "object",
                "description": "Which routes each Haiku builder handles",
                "properties": {
                    "agent_1": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Routes for builder agent 1",
                    },
                    "agent_2": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Routes for builder agent 2",
                    },
                    "agent_3": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Routes for builder agent 3",
                    },
                },
            },
            "shared_data": {
                "type": "object",
                "description": "Canonical mock data shared across all pages for consistency.",
                "properties": {
                    "metrics": {
                        "type": "object",
                        "description": (
                            "Key metric values referenced across pages. "
                            "E.g. {'total_users': '12.4K', 'mrr': '$34.2K', 'pending_items': 3}"
                        ),
                    },
                    "sample_items": {
                        "type": "array",
                        "description": (
                            "8-12 realistic sample data items for tables/lists. "
                            "Each item should have: name, status, date, value fields "
                            "relevant to the domain."
                        ),
                        "items": {"type": "object"},
                    },
                    "user_names": {
                        "type": "array",
                        "description": "5-8 realistic names for avatars and activity feeds.",
                        "items": {"type": "string"},
                    },
                    "status_options": {
                        "type": "array",
                        "description": (
                            "Domain-specific status labels (e.g. ['Active', 'Draft', 'Archived'])."
                        ),
                        "items": {"type": "string"},
                    },
                },
            },
            "route_manifest": {
                "type": "object",
                "description": (
                    "Mapping of epic indices and feature slugs to screen routes. "
                    "Used by the AIOS bridge for guided tour navigation."
                ),
                "properties": {
                    "epic_routes": {
                        "type": "object",
                        "description": (
                            "Map of epic index (as string) to the screen route. "
                            "E.g. {'0': '/dashboard', '1': '/assessment'}"
                        ),
                    },
                    "feature_routes": {
                        "type": "object",
                        "description": (
                            "Map of feature slug to the screen route where it appears. "
                            "E.g. {'risk-scoring': '/assessment', 'user-dashboard': '/dashboard'}"
                        ),
                    },
                },
            },
        },
    },
}

# =============================================================================
# System prompt
# =============================================================================

SYSTEM_PROMPT = """\
You are the Solution Architect for an AI-powered prototype builder. Your job is to transform \
raw discovery intelligence into a cohesive, production-grade prototype plan.

You are designing a REAL PRODUCT — not a wireframe, not a feature list, not a presentation of \
the solution flow. Think like a senior product designer at a top design studio.

## CRITICAL DESIGN RULES

1. **TARGET 5-8 SCREENS.** Group related solution flow steps and features into logical screens. \
A "Dashboard" screen combines metrics from multiple steps. An "Onboarding" screen merges \
several entry-phase steps into a wizard. NEVER create 1 screen per solution flow step.

1b. **MAX 5 COMPONENTS PER SCREEN.** Combine related features into single component sections \
(e.g. one tabs or card_grid covering multiple features). More than 5 causes builder failures.

2. **SHORT NAV LABELS.** 1-2 words max. "Dashboard" not "Comprehensive Analytics Dashboard". \
"Listeners" not "Listener Profile & Discovery Hub". "Content" not "Content Strategy Management".

3. **SECTION GROUPING.** Group nav items under 2-4 section headers in ALL CAPS. \
E.g. "MAIN" (Dashboard, Home), "CONTENT" (Episodes, Library), "INSIGHTS" (Analytics, Reports), \
"MANAGE" (Settings, Team).

4. **DARK SIDEBAR.** Always use a dark sidebar (bg-slate-900 or darker) with light text. \
This creates a professional SaaS feel. The content area should be light (bg-gray-50).

5. **DIVERSE COMPONENTS.** Each screen should have a different feel:
   - Dashboard → metric_grid + chart + activity_feed
   - Content/Library → data_table or card_grid with filters
   - Onboarding → wizard_stepper or form with progress
   - Analytics → chart + metric_grid + tabs
   - Settings → settings_form with sections
   - Detail → split layout with sidebar info + main content
   - AI features → chat_interface or card_grid with AI indicators

6. **BRAND APPLICATION.** Use the primary color aggressively: active nav items, CTA buttons, \
chart accents, metric trend indicators, card borders on hover. Don't leave everything gray.

7. **REAL MOCK DATA.** Specify domain-specific, realistic values:
   - Bad: "Value 1", "123", "Item A"
   - Good: "12.4K listeners", "$34.2K MRR", "Maria Chen — Product Lead"

8. **WORKING INTERACTIONS.** Every button navigates. Every form submits with toast. \
Every table has search. Every card is clickable. Specify these in component guidance.

9. **SHARED DATA.** Provide canonical mock data in shared_data: metric values, sample items, \
user names, and status options. Builders will use these exact values so cross-page references \
are consistent (e.g. if Dashboard shows "3 pending drafts", the Content page shows 3 draft items).

## COMPONENT TYPES

Use these component types in your plan:

| Type | Best For | Key Props |
|------|----------|-----------|
| hero | Landing/first screen | headline, subtitle, CTA, gradient background |
| metric_grid | KPI dashboards | 3-6 stat cards with value, trend, icon |
| form | Data entry, onboarding | fields with labels, types, validation |
| data_table | Lists, inventories | columns, rows, searchable, sortable |
| chart | Analytics, trends | area/bar/line/pie, series data, labels |
| card_grid | Browsing, selection | 2-4 col grid of cards with icon/title/desc |
| activity_feed | Recent events | avatar, action text, timestamp |
| chat_interface | AI features | message history, input, suggestions |
| kanban | Workflow/pipeline | columns with draggable cards |
| calendar | Scheduling | events with dates, colors |
| settings_form | Configuration | sections with toggles, inputs |
| tabs | Multi-view pages | tab labels with content areas |
| timeline | Progress/history | events with dates, status |
| wizard_stepper | Multi-step flows | numbered steps, progress, back/next |
| split_detail | Master/detail views | sidebar list + main content area |
| stat_row | Inline metrics | horizontal row of stats |
| list_with_actions | Action lists | items with action buttons |

## SCREEN ASSIGNMENT

Distribute screens across 3 builder agents (agent_1, agent_2, agent_3). \
Roughly equal load. Group related screens to the same agent when possible.

## ROUTE MANIFEST

CRITICAL: Screen routes MUST match the epic primary_routes from the epic plan. \
Provide a route_manifest mapping each epic index to its screen route, and each \
feature slug to the screen route where it appears. This enables the guided tour \
to navigate between epics without page reloads.

CRITICAL: Every screen you plan MUST have real content. Do NOT plan screens you can't fully \
specify. Merge thin screens into others rather than creating placeholders.

Submit your plan via the submit_project_plan tool."""


# =============================================================================
# Context formatting
# =============================================================================


def _format_context(
    payload: PrototypePayload,
    prebuild: PrebuildIntelligence,
) -> str:
    """Format payload + prebuild into a context string for the agent."""
    lines: list[str] = []

    # Project overview
    lines.append(f"# Project: {payload.project_name}")
    lines.append(f"Vision: {payload.project_vision}")
    lines.append(f"Company: {payload.company_name} ({payload.company_industry})")
    lines.append("")

    # Design tokens
    if payload.design_contract and payload.design_contract.tokens:
        t = payload.design_contract.tokens
        lines.append("## Design Tokens")
        lines.append(f"Primary: {t.primary_color}")
        lines.append(f"Secondary: {t.secondary_color}")
        lines.append(f"Accent: {t.accent_color}")
        lines.append(f"Heading font: {t.font_heading}")
        lines.append(f"Body font: {t.font_body}")
        if payload.design_contract.style_direction:
            lines.append(f"Style: {payload.design_contract.style_direction}")
        lines.append("")

    # Personas
    lines.append(f"## Personas ({len(payload.personas)})")
    for p in payload.personas:
        lines.append(f"- **{p.name}** ({p.role})")
        if p.goals:
            lines.append(f"  Goals: {'; '.join(p.goals[:3])}")
        if p.pain_points:
            lines.append(f"  Pain points: {'; '.join(p.pain_points[:3])}")
    lines.append("")

    # Features — filter out placeholders so coherence focuses on buildable features
    buildable = [f for f in payload.features if getattr(f, "build_depth", "full") != "placeholder"]
    if not buildable:
        buildable = list(payload.features)  # fallback: show all if everything is placeholder
    h1 = [f for f in buildable if f.horizon == "H1"]
    h2 = [f for f in buildable if f.horizon == "H2"]
    h3 = [f for f in buildable if f.horizon == "H3"]
    lines.append(f"## Features ({len(buildable)}: {len(h1)} H1, {len(h2)} H2, {len(h3)} H3)")
    for f in buildable:
        lines.append(f"- [{f.horizon}] **{f.name}** ({f.priority}): {f.overview[:150]}")
    lines.append("")

    # Solution flow
    lines.append(f"## Solution Flow ({len(payload.solution_flow_steps)} steps)")
    for s in payload.solution_flow_steps:
        info_summary = ""
        if s.information_fields:
            captured = [
                f
                for f in s.information_fields
                if isinstance(f, dict) and f.get("type") == "captured"
            ]
            displayed = [
                f
                for f in s.information_fields
                if isinstance(f, dict) and f.get("type") == "displayed"
            ]
            computed = [
                f
                for f in s.information_fields
                if isinstance(f, dict) and f.get("type") == "computed"
            ]
            info_summary = (
                f" [captured:{len(captured)}, displayed:{len(displayed)}, computed:{len(computed)}]"
            )

        ai_note = ""
        if s.ai_config:
            role = s.ai_config.get("role", "AI") if isinstance(s.ai_config, dict) else "AI"
            ai_note = f" [AI: {role}]"

        pattern_note = ""
        if s.implied_pattern:
            pattern_note = f" [pattern: {s.implied_pattern}]"

        lines.append(
            f"- [{s.phase}] **{s.title}** (order {s.step_order}): "
            f"{s.goal[:120]}{info_summary}{ai_note}{pattern_note}"
        )
        if s.pain_points_addressed:
            pps = [
                pp.get("text", str(pp))[:60] if isinstance(pp, dict) else str(pp)[:60]
                for pp in s.pain_points_addressed[:2]
            ]
            lines.append(f"  Pain addressed: {'; '.join(pps)}")
        if s.linked_feature_ids:
            lines.append(f"  Linked features: {len(s.linked_feature_ids)} features")
    lines.append("")

    # Epic plan
    epics = prebuild.epic_plan.get("vision_epics", []) if prebuild.epic_plan else []
    lines.append(f"## Epic Plan ({len(epics)} epics)")
    for e in epics:
        feats = e.get("features", [])
        feat_names = [f.get("name", "") for f in feats][:5]
        lines.append(
            f"- Epic {e.get('epic_index', '?')}: **{e.get('title', '')}** "
            f"(theme: {e.get('theme', '')}, route: {e.get('primary_route', '')})"
        )
        lines.append(f"  Narrative: {e.get('narrative', '')[:200]}")
        lines.append(f"  Features: {', '.join(feat_names)}")
        lines.append(f"  Steps: {len(e.get('solution_flow_step_ids', []))}")
    lines.append("")

    # Feature specs (depth assignments)
    lines.append("## Feature Depth Assignments")
    for spec in prebuild.feature_specs:
        lines.append(f"- {spec.name}: {spec.depth} (H{spec.horizon[-1] if spec.horizon else '?'})")

    return "\n".join(lines)


# =============================================================================
# Fix string-encoded fields
# =============================================================================


def _lenient_json_loads(s: str) -> Any:
    """Parse JSON string with lenient handling of malformed JSON.

    The model sometimes produces JSON strings with unescaped inner
    double quotes. Uses json_repair for robust recovery.
    """
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass

    from json_repair import repair_json

    result = repair_json(s, return_objects=True)
    if isinstance(result, (list, dict)):
        return result

    raise ValueError(f"Could not repair JSON string ({len(s)} chars)")


def _fix_string_encoded_fields(plan: dict) -> dict:
    """Fix fields that the model returned as JSON strings.

    Sometimes the model serializes arrays/objects as JSON strings
    inside the tool_use input instead of actual arrays/objects.
    """
    for key in list(plan.keys()):
        val = plan[key]
        if isinstance(val, str) and val.strip().startswith(("[", "{")):
            try:
                parsed = _lenient_json_loads(val)
                plan[key] = parsed
                logger.info(
                    f"Fixed string-encoded field '{key}' "
                    f"({len(val)} chars → "
                    f"{type(parsed).__name__})"
                )
            except (json.JSONDecodeError, ValueError):
                logger.warning(f"Could not parse string field '{key}' ({len(val)} chars)")
    return plan


# =============================================================================
# Main entry point
# =============================================================================


async def run_coherence_agent(
    payload: PrototypePayload,
    prebuild: PrebuildIntelligence,
) -> dict[str, Any]:
    """Run the Sonnet coherence agent to produce a structured project plan.

    Returns the project plan dict from the tool call output.
    """
    from anthropic import AsyncAnthropic

    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    context = _format_context(payload, prebuild)

    user_message = (
        f"Design the prototype for this project. Study all the data carefully, "
        f"then submit a complete project plan.\n\n{context}"
    )

    start = time.monotonic()
    logger.info("Coherence agent starting...")

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=20000,
        temperature=1,
        thinking={"type": "enabled", "budget_tokens": 6000},
        system=SYSTEM_PROMPT,
        tools=[COHERENCE_TOOL],
        messages=[{"role": "user", "content": user_message}],
    )

    duration = time.monotonic() - start

    # Log response blocks for debugging
    block_types = [b.type for b in response.content]
    logger.info(f"Response blocks: {block_types}")

    # Extract tool use result
    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_project_plan":
            plan = block.input

            # Fix string-encoded fields (model sometimes
            # serializes arrays/objects as JSON strings)
            plan = _fix_string_encoded_fields(plan)

            logger.info(f"Raw plan keys: {list(plan.keys())}")

            sections = plan.get("nav_sections", [])
            screen_count = 0
            for s in sections:
                if isinstance(s, dict):
                    screen_count += len(s.get("screens", []))
            logger.info(
                f"Coherence agent complete: "
                f"{len(sections)} sections, "
                f"{screen_count} screens, {duration:.1f}s"
            )
            return plan

    # If no tool use, try to parse from text
    for block in response.content:
        if block.type == "text" and "{" in block.text:
            logger.info(f"No tool_use — trying text parse: {block.text[:200]}")
            try:
                return json.loads(block.text)
            except json.JSONDecodeError:
                pass

    raise RuntimeError(
        f"Coherence agent did not produce a project plan "
        f"after {duration:.1f}s. Response had {len(response.content)} blocks."
    )
