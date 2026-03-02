"""Deterministic ScreenMap assembly from PrototypePayload + PrebuildIntelligence.

Zero LLM calls. Pure Python. Builds a complete ScreenMap skeleton from
pre-computed data. The skeleton is then enriched by parallel Haiku calls
in the planning agent.

Flow:
  epic_plan.vision_epics[] → screens
  solution_flow_step.information_fields[] → components
  payload.personas[] → mock_context
  feature_specs[].depth → screen depth
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.core.schemas_prototype_builder import (
    PrebuildIntelligence,
    PrototypePayload,
)
from app.core.schemas_screen_map import (
    AppShell,
    BrandingSpec,
    Component,
    DomainContext,
    ImageEntry,
    ImageSlot,
    MockContext,
    MockUser,
    NavItem,
    Screen,
    ScreenMap,
    UXCopy,
)

logger = logging.getLogger(__name__)

# =============================================================================
# Icon mapping — deterministic theme/type → lucide-react icon name
# =============================================================================

THEME_ICON_MAP: dict[str, str] = {
    "dashboard": "layout-dashboard",
    "analytics": "bar-chart-3",
    "settings": "settings",
    "users": "users",
    "user": "user",
    "profile": "user-circle",
    "inbox": "inbox",
    "messages": "message-square",
    "chat": "message-circle",
    "search": "search",
    "discovery": "compass",
    "explore": "globe",
    "calendar": "calendar",
    "schedule": "clock",
    "reports": "file-text",
    "document": "file-text",
    "project": "folder",
    "task": "check-square",
    "workflow": "git-branch",
    "pipeline": "git-merge",
    "integration": "plug",
    "notification": "bell",
    "billing": "credit-card",
    "payment": "credit-card",
    "finance": "dollar-sign",
    "home": "home",
    "overview": "layout-dashboard",
    "monitor": "activity",
    "health": "heart-pulse",
    "security": "shield",
    "team": "users",
    "collaboration": "users",
    "roadmap": "map",
    "planning": "map-pin",
    "inventory": "package",
    "product": "box",
    "order": "shopping-cart",
    "customer": "contact",
    "lead": "target",
    "crm": "contact",
    "marketing": "megaphone",
    "campaign": "megaphone",
    "content": "pen-tool",
    "media": "image",
    "ai": "sparkles",
    "intelligence": "brain",
    "insight": "lightbulb",
    "data": "database",
    "import": "upload",
    "export": "download",
    "map": "map",
    "location": "map-pin",
    "property": "building",
    "listing": "list",
}

COMPONENT_ICON_MAP: dict[str, str] = {
    "form": "clipboard-list",
    "data_table": "table",
    "chart": "bar-chart-3",
    "card_grid": "layout-grid",
    "metric_grid": "trending-up",
    "activity_feed": "activity",
    "chat_interface": "message-circle",
    "kanban": "columns",
    "calendar": "calendar",
    "settings_form": "settings",
    "file_list": "folder",
    "timeline": "clock",
    "hero": "zap",
}

# =============================================================================
# Mock data generation (deterministic, no LLM)
# =============================================================================

_STATUS_VALUES = ["Active", "Pending", "Completed", "In Review"]
_RELATIVE_DATES = [
    "Today",
    "Yesterday",
    "2 days ago",
    "Last week",
    "Mar 1",
    "Feb 28",
    "Feb 25",
    "Feb 20",
]
_PRIORITY_VALUES = ["High", "Medium", "Low", "Critical"]


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]


def _generate_mock_rows(
    columns: list[dict],
    domain: str,
    persona_names: list[str],
    count: int = 8,
) -> list[dict]:
    """Generate deterministic mock rows from column definitions."""
    rows = []
    for i in range(count):
        row: dict[str, Any] = {}
        for ci, col in enumerate(columns):
            key = col.get("key", col.get("label", f"col_{ci}"))
            col_type = col.get("type", "text")
            label_lower = key.lower()

            if any(w in label_lower for w in ("name", "user", "owner", "assigned", "author")):
                if persona_names:
                    row[key] = persona_names[i % len(persona_names)]
                else:
                    row[key] = f"User {i + 1}"
            elif any(w in label_lower for w in ("status", "state")):
                row[key] = _STATUS_VALUES[i % len(_STATUS_VALUES)]
            elif any(w in label_lower for w in ("date", "created", "updated", "time")):
                row[key] = _RELATIVE_DATES[i % len(_RELATIVE_DATES)]
            elif any(w in label_lower for w in ("priority", "urgency")):
                row[key] = _PRIORITY_VALUES[i % len(_PRIORITY_VALUES)]
            elif any(w in label_lower for w in ("amount", "price", "cost", "revenue", "value")):
                row[key] = f"${(i + 1) * 1250:,}"
            elif any(w in label_lower for w in ("count", "total", "qty", "quantity")):
                row[key] = str((i + 1) * 12)
            elif any(w in label_lower for w in ("percent", "rate", "%", "score")):
                row[key] = f"{65 + i * 4}%"
            elif any(w in label_lower for w in ("email",)):
                name = persona_names[i % len(persona_names)] if persona_names else f"user{i + 1}"
                row[key] = f"{name.lower().replace(' ', '.')}@{domain or 'company'}.com"
            elif col_type == "number":
                row[key] = str((i + 1) * 42)
            else:
                # Use mock_value if available
                mock_val = col.get("mock_value", "")
                if mock_val:
                    row[key] = str(mock_val)
                else:
                    row[key] = f"{key.replace('_', ' ').title()} {i + 1}"
        rows.append(row)
    return rows


# =============================================================================
# Component selection from information_fields
# =============================================================================


def _select_components(
    step: Any,
    features_for_step: list[dict],
    depth: str,
    persona_names: list[str],
    domain: str,
) -> list[Component]:
    """Map a solution flow step's information_fields to components."""
    components: list[Component] = []
    info_fields = getattr(step, "information_fields", []) or []

    # Group fields by type
    captured: list[dict] = []
    displayed: list[dict] = []
    computed: list[dict] = []

    for field in info_fields:
        if not isinstance(field, dict):
            continue
        ftype = field.get("type", "displayed")
        if ftype == "captured":
            captured.append(field)
        elif ftype == "computed":
            computed.append(field)
        else:
            displayed.append(field)

    # Find feature_id for this step's components
    feature_slug = None
    if features_for_step:
        feature_slug = _slugify(features_for_step[0].get("name", ""))

    # Captured → form
    if captured:
        form_fields = []
        for f in captured:
            field_name = f.get("name", f.get("field_name", "field"))
            field_type = "text"
            options = None
            if f.get("options") or f.get("enum"):
                field_type = "select"
                options = f.get("options") or f.get("enum", [])
            elif "date" in field_name.lower():
                field_type = "date"
            elif "email" in field_name.lower():
                field_type = "email"
            elif "description" in field_name.lower() or "notes" in field_name.lower():
                field_type = "textarea"
            form_fields.append(
                {
                    "name": field_name,
                    "type": field_type,
                    "label": f.get("label", field_name.replace("_", " ").title()),
                    "placeholder": f.get("mock_value", ""),
                    "required": f.get("required", False),
                    **({"options": options} if options else {}),
                }
            )
        components.append(
            Component(
                type="form",
                feature_id=feature_slug,
                depth=depth if depth != "full" else None,
                props={
                    "fields": form_fields,
                    "submit_label": f"Save {getattr(step, 'title', 'Data')}",
                    "description": getattr(step, "goal", ""),
                },
            )
        )

    # Displayed → data_table or card_grid
    if displayed:
        if len(displayed) > 6:
            # data_table
            columns = [
                {
                    "key": f.get("name", f.get("field_name", f"col_{i}")),
                    "label": f.get(
                        "label",
                        f.get("name", f.get("field_name", "Column")).replace("_", " ").title(),
                    ),
                    "sortable": True,
                    "mock_value": f.get("mock_value", ""),
                }
                for i, f in enumerate(displayed)
            ]
            rows = _generate_mock_rows(columns, domain, persona_names)
            components.append(
                Component(
                    type="data_table",
                    feature_id=feature_slug,
                    depth=depth if depth != "full" else None,
                    props={
                        "columns": columns,
                        "rows": rows,
                        "searchable": True,
                        "filters": [],
                    },
                )
            )
        else:
            # card_grid
            cards = [
                {
                    "title": f.get(
                        "label",
                        f.get("name", f.get("field_name", "Item")).replace("_", " ").title(),
                    ),
                    "description": f.get("mock_value", "") or f.get("description", ""),
                    "icon": COMPONENT_ICON_MAP.get("card_grid", "layout-grid"),
                }
                for f in displayed
            ]
            components.append(
                Component(
                    type="card_grid",
                    feature_id=feature_slug,
                    depth=depth if depth != "full" else None,
                    props={
                        "cards": cards,
                        "columns": min(len(cards), 3),
                    },
                )
            )

    # Computed → metric_grid
    if computed:
        metrics = [
            {
                "label": f.get(
                    "label",
                    f.get("name", f.get("field_name", "Metric")).replace("_", " ").title(),
                ),
                "value": f.get("mock_value", "0"),
                "trend": "",
                "icon": "trending-up",
            }
            for f in computed
        ]
        components.append(
            Component(
                type="metric_grid",
                feature_id=feature_slug,
                depth=depth if depth != "full" else None,
                props={"metrics": metrics},
            )
        )

    # AI indicator
    if getattr(step, "ai_config", None):
        ai = step.ai_config
        components.append(
            Component(
                type="ai_indicator",
                feature_id=feature_slug,
                props={
                    "role": (
                        ai.get("role", "AI Assistant") if isinstance(ai, dict) else "AI Assistant"
                    ),
                    "status": "active",
                    "behaviors": (
                        ai.get("behaviors", [])
                        if isinstance(ai, dict)
                        else ["Intelligent automation"]
                    ),
                },
            )
        )

    # Implied pattern override
    implied = getattr(step, "implied_pattern", None)
    if implied:
        pattern_lower = implied.lower()
        if "kanban" in pattern_lower and not any(c.type == "kanban" for c in components):
            components.append(
                Component(
                    type="kanban",
                    feature_id=feature_slug,
                    props={
                        "columns": [
                            {
                                "title": status,
                                "cards": [
                                    {
                                        "title": f"Task {j + 1}",
                                        "assignee": persona_names[j % len(persona_names)]
                                        if persona_names
                                        else "",
                                    }
                                    for j in range(3)
                                ],
                            }
                            for status in ["To Do", "In Progress", "Done"]
                        ]
                    },
                )
            )
        elif "calendar" in pattern_lower and not any(c.type == "calendar" for c in components):
            components.append(
                Component(
                    type="calendar",
                    feature_id=feature_slug,
                    props={
                        "events": [
                            {"title": f"Event {j + 1}", "date": str(j + 5), "color": "primary"}
                            for j in range(4)
                        ],
                        "view": "month",
                    },
                )
            )
        elif "chat" in pattern_lower and not any(c.type == "chat_interface" for c in components):
            components.append(
                Component(
                    type="chat_interface",
                    feature_id=feature_slug,
                    props={
                        "messages": [
                            {
                                "role": "assistant",
                                "content": f"Welcome! How can I help with "
                                f"{getattr(step, 'title', 'your task')}?",
                            },
                            {
                                "role": "user",
                                "content": "Show me the latest updates.",
                            },
                            {
                                "role": "assistant",
                                "content": "Here's a summary of recent activity...",
                            },
                        ],
                        "input_placeholder": f"Ask about {getattr(step, 'title', '')}...",
                    },
                )
            )

    # If step has success_criteria but no computed metrics, add them
    criteria = getattr(step, "success_criteria", []) or []
    if criteria and not computed:
        metrics = [
            {
                "label": str(c)[:50] if isinstance(c, str) else str(c.get("text", ""))[:50],
                "value": "—",
                "trend": "",
                "icon": "target",
            }
            for c in criteria[:4]
        ]
        if metrics:
            components.append(
                Component(
                    type="metric_grid",
                    feature_id=feature_slug,
                    props={"metrics": metrics},
                )
            )

    # Fallback: if no components generated from fields, create a card_grid from features
    if not components and features_for_step:
        cards = [
            {
                "title": feat.get("name", "Feature"),
                "description": feat.get("overview", "")[:120],
                "icon": "zap",
            }
            for feat in features_for_step[:6]
        ]
        components.append(
            Component(
                type="card_grid",
                feature_id=feature_slug,
                props={"cards": cards, "columns": min(len(cards), 3)},
            )
        )

    return components


# =============================================================================
# Main assembler
# =============================================================================


def assemble_screen_map(
    payload: PrototypePayload,
    prebuild: PrebuildIntelligence,
) -> ScreenMap:
    """Build a complete ScreenMap skeleton from pre-computed data.

    Zero LLM calls. Pure deterministic logic.

    Args:
        payload: Full project payload with features, personas, steps, etc.
        prebuild: Phase 0 intelligence with epics, feature specs, depth assignments.

    Returns:
        A ScreenMap ready for optional Haiku enrichment.
    """
    epic_plan = prebuild.epic_plan or {}
    vision_epics = epic_plan.get("vision_epics", [])
    feature_specs = prebuild.feature_specs or []

    # Build lookup maps
    feature_by_id: dict[str, Any] = {f.id: f for f in payload.features}
    step_by_id: dict[str, Any] = {s.id: s for s in payload.solution_flow_steps}
    spec_by_feature: dict[str, Any] = {s.feature_id: s for s in feature_specs}
    persona_names = [p.name for p in payload.personas]
    domain = payload.company_industry or payload.company_name or "company"

    # ── Build screens from epics ──────────────────────────────────────
    screens: list[Screen] = []
    feature_coverage: dict[str, str] = {}
    covered_features: set[str] = set()

    for epic in vision_epics:
        epic_index = epic.get("epic_index", 0)
        route = epic.get("primary_route", f"/screen-{epic_index}")
        title = epic.get("title", f"Screen {epic_index + 1}")
        epic_id = f"epic-{epic_index}"
        step_ids = epic.get("solution_flow_step_ids", [])
        epic_features = epic.get("features", [])

        # Determine screen depth from linked features
        screen_depth = "full"
        for ef in epic_features:
            fid = ef.get("feature_id", "")
            spec = spec_by_feature.get(fid)
            if spec and spec.depth == "placeholder":
                screen_depth = "placeholder"
                break
            elif spec and spec.depth == "visual":
                screen_depth = "visual"

        # Determine layout from step phases
        step_phases = set()
        for sid in step_ids:
            step = step_by_id.get(sid)
            if step:
                step_phases.add(getattr(step, "phase", "core_experience"))

        if "entry" in step_phases:
            layout = "landing"
        elif any(
            getattr(step_by_id.get(sid), "implied_pattern", "") == "kanban"
            for sid in step_ids
            if step_by_id.get(sid)
        ):
            layout = "kanban"
        elif any(
            getattr(step_by_id.get(sid), "implied_pattern", "") == "calendar"
            for sid in step_ids
            if step_by_id.get(sid)
        ):
            layout = "calendar"
        else:
            layout = "dashboard"

        # Build components from steps
        components: list[Component] = []
        for sid in step_ids:
            step = step_by_id.get(sid)
            if not step:
                continue
            # Find features linked to this step
            linked_fids = getattr(step, "linked_feature_ids", []) or []
            step_features = [
                {"name": feature_by_id[fid].name, "overview": feature_by_id[fid].overview}
                for fid in linked_fids
                if fid in feature_by_id
            ]
            step_comps = _select_components(
                step, step_features, screen_depth, persona_names, domain
            )
            components.extend(step_comps)

        # If no components from steps, build from epic's features directly
        if not components:
            epic_feat_details = [
                {
                    "name": feature_by_id[ef["feature_id"]].name,
                    "overview": feature_by_id[ef["feature_id"]].overview,
                }
                for ef in epic_features
                if ef.get("feature_id") in feature_by_id
            ]
            if epic_feat_details:
                components.append(
                    Component(
                        type="card_grid",
                        feature_id=_slugify(epic_feat_details[0]["name"]),
                        props={
                            "cards": [
                                {
                                    "title": f["name"],
                                    "description": f["overview"][:120],
                                    "icon": "zap",
                                }
                                for f in epic_feat_details[:6]
                            ],
                            "columns": min(len(epic_feat_details), 3),
                        },
                    )
                )

        # Track feature coverage
        for ef in epic_features:
            fid = ef.get("feature_id", "")
            fname = ef.get("name", "")
            if fname:
                slug = _slugify(fname)
                feature_coverage[slug] = route
                covered_features.add(fid)

        # Build images
        images: list[ImageSlot] = []
        for sid in step_ids:
            step = step_by_id.get(sid)
            if step and getattr(step, "image_url", None):
                images.append(
                    ImageSlot(
                        slot=f"step-{sid[:8]}",
                        source="url",
                        value=step.image_url,
                        alt=getattr(step, "title", ""),
                        fallback_gradient=(
                            "linear-gradient(135deg, var(--color-primary), var(--color-secondary))"
                        ),
                    )
                )

        # UX copy from step data
        ux_copy = UXCopy(headline=title)
        pain_callouts = []
        for sid in step_ids:
            step = step_by_id.get(sid)
            if step:
                for pp in getattr(step, "pain_points_addressed", []) or []:
                    text = pp.get("text", "") if isinstance(pp, dict) else str(pp)
                    if text:
                        pain_callouts.append(text)
        if pain_callouts:
            ux_copy.pain_point_callout = pain_callouts[0]

        screens.append(
            Screen(
                route=route,
                title=title,
                epic_id=epic_id,
                layout=layout,
                depth=screen_depth,
                solution_flow_step_ids=step_ids,
                features_shown=[ef.get("name", "") for ef in epic_features],
                components=components,
                images=images,
                ux_copy=ux_copy,
                feel=epic.get("narrative", "")[:200] if epic.get("narrative") else None,
            )
        )

    # ── First screen gets hero ────────────────────────────────────────
    if screens and payload.project_vision:
        hero = Component(
            type="hero",
            props={
                "headline": payload.project_name or screens[0].title,
                "subtitle": payload.project_vision[:200],
                "cta_primary": f"Explore {screens[1].title}" if len(screens) > 1 else "Get Started",
                "cta_secondary": "Learn More",
                "background": "gradient",
            },
        )
        screens[0].components.insert(0, hero)

    # ── Uncovered features → roadmap screen ───────────────────────────
    uncovered = [f for f in payload.features if f.id not in covered_features]
    h2_features = [f for f in uncovered if f.horizon == "H2"]
    h3_features = [f for f in uncovered if f.horizon == "H3"]
    remaining = [f for f in uncovered if f.horizon == "H1"]

    # Also gather covered H2/H3 features for roadmap
    for spec in feature_specs:
        f = feature_by_id.get(spec.feature_id)
        if f and spec.depth == "placeholder" and f.id in covered_features:
            if f.horizon == "H2" and f not in h2_features:
                h2_features.append(f)
            elif f.horizon == "H3" and f not in h3_features:
                h3_features.append(f)

    if h2_features or h3_features or remaining:
        roadmap_components = []
        if remaining:
            roadmap_components.append(
                Component(
                    type="card_grid",
                    props={
                        "cards": [
                            {
                                "title": f.name,
                                "description": f.overview[:120],
                                "badge": f.priority,
                                "icon": "zap",
                            }
                            for f in remaining[:6]
                        ],
                        "columns": min(len(remaining), 3),
                    },
                )
            )
        roadmap_components.append(
            Component(
                type="horizon_roadmap",
                props={
                    "h2_features": [
                        {"name": f.name, "description": f.overview[:120]} for f in h2_features
                    ],
                    "h3_features": [
                        {"name": f.name, "description": f.overview[:120]} for f in h3_features
                    ],
                },
            )
        )
        screens.append(
            Screen(
                route="/roadmap",
                title="Roadmap",
                layout="roadmap",
                depth="placeholder",
                components=roadmap_components,
                ux_copy=UXCopy(
                    headline="Product Roadmap",
                    subtitle="Upcoming features and future vision",
                ),
            )
        )
        for f in uncovered:
            feature_coverage[_slugify(f.name)] = "/roadmap"

    # ── Navigation pattern ────────────────────────────────────────────
    num_screens = len(screens)
    if num_screens <= 4:
        nav_type = "top_tabs"
    elif (
        all(
            getattr(step_by_id.get(s), "phase", "") in ("entry", "core_experience", "output")
            for s in (vision_epics[0].get("solution_flow_step_ids", []) if vision_epics else [])
        )
        and num_screens <= 5
    ):
        nav_type = "wizard_flow"
    else:
        nav_type = "sidebar"

    # ── Nav items ─────────────────────────────────────────────────────
    nav_items: list[NavItem] = []
    for screen in screens:
        # Pick icon from theme
        icon = "circle"
        title_lower = screen.title.lower()
        for keyword, icon_name in THEME_ICON_MAP.items():
            if keyword in title_lower:
                icon = icon_name
                break
        else:
            # Fallback: use epic theme from vision_epics
            for epic in vision_epics:
                if epic.get("primary_route") == screen.route:
                    theme_lower = (epic.get("theme", "") or "").lower()
                    for keyword, icon_name in THEME_ICON_MAP.items():
                        if keyword in theme_lower:
                            icon = icon_name
                            break
                    break

        nav_items.append(
            NavItem(
                label=screen.title,
                route=screen.route,
                icon=icon,
                epic_id=screen.epic_id,
            )
        )

    # ── Mock context ──────────────────────────────────────────────────
    primary_persona = payload.personas[0] if payload.personas else None
    primary_user = MockUser(
        name=primary_persona.name if primary_persona else "Alex Demo",
        role=primary_persona.role if primary_persona else "User",
        avatar_initials=(
            "".join(w[0].upper() for w in primary_persona.name.split()[:2])
            if primary_persona and primary_persona.name
            else "AD"
        ),
        avatar_bg="primary",
        persona_id=primary_persona.id if primary_persona else None,
    )
    secondary_users = [
        MockUser(
            name=p.name,
            role=p.role,
            avatar_initials="".join(w[0].upper() for w in p.name.split()[:2]) if p.name else "??",
            avatar_bg=["secondary", "accent"][i % 2],
            persona_id=p.id,
        )
        for i, p in enumerate(payload.personas[1:4])
    ]

    domain_ctx = DomainContext(
        industry=payload.company_industry or "",
        primary_entity=_infer_primary_entity(payload),
        currency="USD",
        date_format="MMM d, yyyy",
    )

    mock_context = MockContext(
        primary_user=primary_user,
        secondary_users=secondary_users,
        domain=domain_ctx,
    )

    # ── Branding ──────────────────────────────────────────────────────
    branding = BrandingSpec(
        logo_source="text",
        logo_value=payload.project_name or "Prototype",
        app_title=payload.project_name or "Prototype",
    )

    # ── Image manifest ────────────────────────────────────────────────
    image_manifest: list[ImageEntry] = [
        ImageEntry(
            id="hero-gradient",
            source="gradient",
            value="linear-gradient(135deg, var(--color-primary), var(--color-secondary))",
            alt="Hero background",
            fallback_gradient="linear-gradient(135deg, #3b82f6, #8b5cf6)",
        ),
    ]
    # Add persona avatar entries
    for user in [primary_user, *secondary_users]:
        image_manifest.append(
            ImageEntry(
                id=f"avatar-{_slugify(user.name)}",
                source="initials",
                value=user.avatar_initials,
                alt=user.name,
            )
        )

    # ── Depth summary ─────────────────────────────────────────────────
    depth_counts: dict[str, int] = {"full": 0, "visual": 0, "placeholder": 0}
    for s in screens:
        depth_counts[s.depth] = depth_counts.get(s.depth, 0) + 1

    # ── Assemble ──────────────────────────────────────────────────────
    screen_map = ScreenMap(
        app_shell=AppShell(
            navigation=nav_type,
            nav_items=nav_items,
            branding=branding,
            footer=True,
            user_menu=True,
        ),
        screens=screens,
        mock_context=mock_context,
        image_manifest=image_manifest,
        total_screens=len(screens),
        feature_coverage=feature_coverage,
        depth_summary=depth_counts,
        planning_notes=(
            f"Deterministic assembly: {len(screens)} screens from "
            f"{len(vision_epics)} epics, {len(payload.features)} features. "
            f"Nav: {nav_type}."
        ),
    )

    logger.info(
        f"Assembled ScreenMap: {len(screens)} screens, "
        f"{len(feature_coverage)} features covered, nav={nav_type}"
    )

    return screen_map


def _infer_primary_entity(payload: PrototypePayload) -> str:
    """Infer the primary domain entity from project data."""
    industry = (payload.company_industry or "").lower()
    entity_map = {
        "real estate": "properties",
        "healthcare": "patients",
        "education": "students",
        "finance": "accounts",
        "retail": "products",
        "logistics": "shipments",
        "hr": "employees",
        "legal": "cases",
        "construction": "projects",
        "marketing": "campaigns",
        "saas": "accounts",
        "consulting": "projects",
    }
    for key, entity in entity_map.items():
        if key in industry:
            return entity
    return "items"
