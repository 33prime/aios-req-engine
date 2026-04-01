"""Coherence Agent — Sonnet produces a structured project plan.

Takes raw payload + prebuild data and makes all the architectural
decisions: screen grouping, nav structure, component selection,
theme application, and agent assignments.

Output is a structured JSON plan that Haiku builders execute.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.schemas_prototype_builder import PrebuildIntelligence, PrototypePayload
from app.core.slug import canonical_slug

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
            "nav_style",
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
            "nav_style": {
                "type": "string",
                "enum": ["sidebar-dark", "sidebar-light", "topnav", "icon-sidebar", "minimal"],
                "description": "Navigation style based on style_direction and product type.",
            },
            "theme": {
                "type": "object",
                "description": "Visual theme decisions",
                "properties": {
                    "nav_bg": {
                        "type": "string",
                        "description": "Tailwind bg class for nav area",
                    },
                    "nav_text": {
                        "type": "string",
                        "description": "Tailwind text class for nav text",
                    },
                    "nav_active": {
                        "type": "string",
                        "description": "Active nav item style classes",
                    },
                    "content_bg": {
                        "type": "string",
                        "enum": [
                            "bg-white",
                            "bg-gray-50",
                            "bg-slate-50",
                            "bg-zinc-50",
                            "bg-neutral-50",
                        ],
                        "description": "Tailwind bg class for content area. MUST be light.",
                    },
                    "accent_usage": {
                        "type": "string",
                        "description": "How to apply primary/accent colors",
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
                                            "kanban",
                                            "map",
                                            "timeline",
                                            "monitoring",
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
                    "Used by the AIOS bridge for guided tour navigation. "
                    "Use the exact [slug: ...] provided in the features list for "
                    "feature_slug in components and feature_routes keys."
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

1. **TARGET 5-8 SCREENS.** Start from solution flow steps — each step suggests a screen. \
Merge closely related steps into one screen (e.g. two entry-phase steps → one Onboarding wizard). \
The step's implied_pattern tells you the layout type. The step's feel_description tells you the \
aesthetic. Features are COMPONENTS within step-driven screens, not independent screens. \
Don't ignore the flow architecture to re-invent screens from scratch.

1b. **MAX 5 COMPONENTS PER SCREEN.** Combine related features into single component sections \
(e.g. one tabs or card_grid covering multiple features). More than 5 causes builder failures.

2. **SHORT NAV LABELS.** 1-2 words max. "Dashboard" not "Comprehensive Analytics Dashboard". \
"Listeners" not "Listener Profile & Discovery Hub". "Content" not "Content Strategy Management".

3. **SECTION GROUPING.** Group nav items under 2-4 section headers. \
Derive section names from the solution flow phases and domain language: entry → "GET STARTED", \
core_experience → domain-specific name (e.g. "STUDIO", "OPERATIONS"), output → "INSIGHTS", \
admin → "MANAGE". Use ALL CAPS for sidebar styles, Title Case for topnav. \
Don't always use generic names like "MAIN" — use the project's vocabulary.

4. **NAVIGATION STYLE.** Choose the nav_style that best fits the product's personality \
and style_direction. If a recommended_nav_style is provided, prefer it unless the product \
clearly demands otherwise. Options:
   - "sidebar-dark": Dark sidebar (bg-slate-900) — enterprise SaaS, data-heavy, analytics tools
   - "sidebar-light": Light sidebar (white/gray, border-r) — modern, approachable, creative tools
   - "topnav": Horizontal top navigation bar — content platforms, marketing tools, simpler apps
   - "icon-sidebar": Narrow icon-only rail (w-16) with tooltips — dense tools, maximized content
   - "minimal": No persistent nav, hamburger or bottom bar — mobile-first, consumer apps
   Read the style_direction and feel_description to decide. When in doubt, "sidebar-dark" for B2B, \
   "sidebar-light" for creative/modern, "topnav" for B2C.

4b. **CONTENT BACKGROUND MUST BE LIGHT.** The content_bg in your theme MUST be one of: \
bg-white, bg-gray-50, bg-slate-50, bg-zinc-50, bg-neutral-50. Dark backgrounds are ONLY \
for sidebar navigation. Forms, tables, and cards on dark backgrounds are invisible and broken.

5. **DIVERSE COMPONENTS.** Each screen should have a different feel. Use the step's \
implied_pattern as a starting point:
   - dashboard → metric_grid + chart + activity_feed
   - table → data_table with search/filters + stat_row summary
   - form/wizard → wizard_stepper or form with progress + validation
   - kanban → kanban board with columns + draggable cards
   - timeline → timeline with milestones + status indicators
   - map → map_view or spatial visualization + detail panel
   - monitoring → metric_grid + chart + activity_feed with real-time indicators
   - AI-powered steps → chat_interface OR card_grid with AI agent card, confidence indicators, \
     and automation badges. Show the agent_name as a visible brand element.

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

10. **AI AGENT VISIBILITY.** When a solution flow step has ai_config, its screen MUST showcase \
the AI. Include at least one of: a chat_interface for conversational agents, an agent identity \
card showing the agent_name and automation_estimate, a confidence/accuracy metric, or an \
activity_feed of AI decisions. Use the agent_name as a branded element (e.g. "Market Sizer" as \
a card title). Show behaviors as capability list items. Show automation_estimate as a percentage \
badge. Human_touchpoints become "Review Required" callouts.

11. **ANTI-PATTERNS (NEVER do these):**
- Dark content backgrounds (bg-slate-800, bg-gray-900 on content area)
- Monochrome pages where everything is the same shade of gray
- Cards without shadow or border (float in space)
- Invisible form inputs (inputs that blend into the background)
- Missing hover states on interactive elements
- Gray-on-gray text with insufficient contrast

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
        if payload.design_contract.recommended_nav_style:
            lines.append(
                f"Recommended nav style: {payload.design_contract.recommended_nav_style}"
            )
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
        lines.append(
            f"- [{f.horizon}] **{f.name}** [slug: {canonical_slug(f.name)}] "
            f"({f.priority}): {f.overview[:150]}"
        )
    lines.append("")

    # Solution flow — rich data for screen architecture
    lines.append(f"## Solution Flow ({len(payload.solution_flow_steps)} steps)")
    for s in payload.solution_flow_steps:
        lines.append(f"### [{s.phase}] {s.title}")
        lines.append(f"Goal: {s.goal[:150]}")
        if s.story_headline:
            lines.append(f"Story: {s.story_headline}")
        if s.implied_pattern:
            lines.append(f"Pattern: {s.implied_pattern}")
        if s.feel_description:
            lines.append(f"Feel: {s.feel_description}")
        if s.user_actions:
            lines.append(f"Actions: {'; '.join(s.user_actions[:5])}")
        if s.human_value_statement:
            lines.append(f"Value: {s.human_value_statement}")
        if s.how_it_works:
            lines.append(f"Narrative: {s.how_it_works[:200]}")
        if s.ai_config and isinstance(s.ai_config, dict):
            agent_name = s.ai_config.get("agent_name", "")
            agent_type = s.ai_config.get("agent_type", "")
            role = s.ai_config.get("role", "")
            behaviors = s.ai_config.get("behaviors", [])[:3]
            automation = s.ai_config.get("automation_estimate")
            lines.append(f"AI Agent: {agent_name} ({agent_type}) — {role}")
            if behaviors:
                lines.append(f"  Behaviors: {'; '.join(behaviors)}")
            if automation:
                lines.append(f"  Automation: {automation}%")
        if s.information_fields:
            field_names = [
                f.get("name", "") for f in s.information_fields[:6] if isinstance(f, dict)
            ]
            lines.append(f"Fields: {', '.join(field_names)}")
        if s.linked_feature_ids:
            lines.append(f"Features: {len(s.linked_feature_ids)} linked")
        lines.append("")

    # Epic plan — concise
    epics = prebuild.epic_plan.get("vision_epics", []) if prebuild.epic_plan else []
    lines.append(f"## Epic Plan ({len(epics)} epics)")
    for e in epics:
        feat_names = [f.get("name", "") for f in e.get("features", [])][:4]
        lines.append(
            f"- Epic {e.get('epic_index', '?')}: **{e.get('title', '')}** "
            f"→ {e.get('primary_route', '/???')} | {', '.join(feat_names)}"
        )
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

    # Fix nav_sections items that are list-wrapped dicts.
    # The model sometimes returns [{...}] instead of {...} for a section.
    sections = plan.get("nav_sections", [])
    if isinstance(sections, list):
        fixed_sections = []
        for s in sections:
            if isinstance(s, list):
                # Unwrap list-wrapped sections
                for item in s:
                    if isinstance(item, dict):
                        fixed_sections.append(item)
                logger.info(f"Unwrapped list-wrapped nav_section ({len(s)} items)")
            elif isinstance(s, dict):
                fixed_sections.append(s)
        if len(fixed_sections) != len(sections):
            plan["nav_sections"] = fixed_sections
            logger.info(
                f"Fixed nav_sections: {len(sections)} → {len(fixed_sections)} sections"
            )

    return plan


# =============================================================================
# Main entry point
# =============================================================================


_CACHE_DIR = Path("/tmp/pipeline_v2_coherence_cache")


def _get_cache_key(context: str) -> str:
    """Hash the context to create a stable cache key."""
    return hashlib.sha256(context.encode()).hexdigest()[:16]


async def run_coherence_agent(
    payload: PrototypePayload,
    prebuild: PrebuildIntelligence,
    *,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    """Run the Sonnet coherence agent to produce a structured project plan.

    Caches plans by context hash — if the same payload produces the same
    context string, the cached plan is returned instantly.

    Returns the project plan dict from the tool call output.
    """
    from anthropic import AsyncAnthropic

    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    context = _format_context(payload, prebuild)

    # Check cache
    cache_root = cache_dir or _CACHE_DIR
    cache_root.mkdir(parents=True, exist_ok=True)
    cache_key = _get_cache_key(context)
    cache_file = cache_root / f"{cache_key}.json"

    if cache_file.exists():
        try:
            cached_plan = json.loads(cache_file.read_text())
            logger.info(f"Coherence cache HIT ({cache_key}) — skipping Sonnet call")
            return cached_plan
        except (json.JSONDecodeError, OSError):
            logger.warning("Coherence cache file corrupt — regenerating")

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
        thinking={"type": "enabled", "budget_tokens": 4000},
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

            # Cache for future runs with same payload
            try:
                cache_file.write_text(json.dumps(plan, indent=2))
                logger.info(f"Coherence plan cached ({cache_key})")
            except OSError as cache_err:
                logger.warning(f"Failed to cache plan: {cache_err}")

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
