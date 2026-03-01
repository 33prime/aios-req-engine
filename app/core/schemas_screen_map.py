"""ScreenMap schema — the contract between Planning Agent and scaffold renderer.

The Planning Agent produces a ScreenMap; the renderer translates it into
React + Tailwind code. Every architectural decision lives here.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# =============================================================================
# Image + Branding
# =============================================================================


class ImageSlot(BaseModel):
    """An image placement within a screen."""

    slot: str  # e.g. "hero_bg", "feature_illustration", "avatar_1"
    source: Literal["url", "gradient", "initials", "icon", "css_pattern"]
    value: str  # URL, gradient spec, initials text, icon name, pattern name
    alt: str = ""
    fallback_gradient: str = ""  # CSS gradient fallback if image fails


class BrandingSpec(BaseModel):
    """App-level branding applied to every screen."""

    logo_source: Literal["text", "url", "svg"] = "text"
    logo_value: str = ""  # text name, Supabase URL, or inline SVG
    app_title: str = ""


# =============================================================================
# Navigation + App Shell
# =============================================================================


class NavItem(BaseModel):
    """A single navigation entry."""

    label: str
    route: str
    icon: str = ""  # lucide-react icon name
    epic_id: str | None = None


class AppShell(BaseModel):
    """Top-level app chrome: navigation, branding, footer."""

    navigation: Literal["sidebar", "top_tabs", "wizard_flow", "single_page"] = "sidebar"
    nav_items: list[NavItem] = Field(default_factory=list)
    branding: BrandingSpec = Field(default_factory=BrandingSpec)
    footer: bool = True
    user_menu: bool = True


# =============================================================================
# Components — the building blocks of screens
# =============================================================================


class Component(BaseModel):
    """A UI component within a screen.

    `type` selects the renderer template. `props` carry type-specific config.
    The scaffold renderer has a template per type; the planning agent composes.

    Supported types and their props:

    hero:
        headline (str), subtitle (str), cta_primary (str), cta_secondary (str|None),
        background (str: "gradient"|"image"|"pattern"), image_slot (str|None)

    metric_grid:
        metrics (list[{label, value, trend, icon}])

    form:
        fields (list[{name, type, label, placeholder, options?, required?}]),
        submit_label (str), description (str|None)

    data_table:
        columns (list[{key, label, sortable?}]), rows (list[dict]),
        searchable (bool), filters (list[str]|None)

    chart:
        chart_type ("area"|"bar"|"line"|"pie"|"donut"),
        title (str), mock_series (list[{name, data}]),
        x_labels (list[str]|None)

    card_grid:
        cards (list[{title, description, icon, badge?, image_slot?}]),
        columns (int: 2|3|4)

    activity_feed:
        entries (list[{user, action, time, avatar_initials?}])

    chat_interface:
        messages (list[{role, content}]), input_placeholder (str)

    kanban:
        columns (list[{title, cards: list[{title, assignee?, tag?}]}])

    calendar:
        events (list[{title, date, time?, color?}]), view ("month"|"week")

    file_list:
        files (list[{name, type, size, modified}])

    settings_form:
        sections (list[{title, fields: list[{name, type, label, value}]}])

    stats_banner:
        stats (list[{label, value, icon}])

    timeline:
        events (list[{title, description, date, status?}]),
        orientation ("horizontal"|"vertical")

    tabs:
        tabs (list[{label, content_summary}]), default_tab (int)

    horizon_roadmap:
        h2_features (list[{name, description}]),
        h3_features (list[{name, description}])

    empty_state:
        icon (str), headline (str), description (str), cta (str|None)

    ai_indicator:
        role (str), status ("active"|"learning"|"ready"),
        behaviors (list[str])

    image_section:
        image_slot (str), caption (str|None), layout ("full"|"half"|"card")

    prose:
        content (str), style ("narrative"|"callout"|"quote")

    cta_section:
        headline (str), description (str),
        primary_action (str), secondary_action (str|None)
    """

    type: str
    feature_id: str | None = None  # slug — for Feature wrapper + bridge tracking
    depth: Literal["full", "visual", "placeholder"] | None = None
    props: dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# UX Copy
# =============================================================================


class UXCopy(BaseModel):
    """Screen-level copy derived from project intelligence."""

    headline: str | None = None
    subtitle: str | None = None
    empty_state: str | None = None
    pain_point_callout: str | None = None  # from unlock or persona pain
    value_prop: str | None = None  # from strategic unlock


# =============================================================================
# Screen
# =============================================================================


class Screen(BaseModel):
    """A single screen/page in the prototype."""

    route: str
    title: str
    epic_id: str | None = None
    layout: Literal[
        "dashboard",
        "form_wizard",
        "detail",
        "list",
        "landing",
        "settings",
        "split",
        "kanban",
        "calendar",
        "roadmap",
    ] = "dashboard"
    depth: Literal["full", "visual", "placeholder"] = "full"
    solution_flow_step_ids: list[str] = Field(default_factory=list)
    features_shown: list[str] = Field(default_factory=list)  # feature slugs
    components: list[Component] = Field(default_factory=list)
    images: list[ImageSlot] = Field(default_factory=list)
    interactions: list[str] = Field(default_factory=list)  # human-readable
    ux_copy: UXCopy | None = None
    feel: str | None = None  # from solution flow step feel_description


# =============================================================================
# Mock Data Context
# =============================================================================


class MockUser(BaseModel):
    """A mock user derived from a project persona."""

    name: str
    role: str
    avatar_initials: str
    avatar_bg: Literal["primary", "secondary", "accent"] = "primary"
    persona_id: str | None = None


class DomainContext(BaseModel):
    """Domain-specific context for realistic mock data."""

    industry: str = ""
    primary_entity: str = "items"  # "projects", "patients", "properties"
    secondary_entity: str = ""
    currency: str = "USD"
    date_format: str = "MMM d, yyyy"


class MockContext(BaseModel):
    """Global mock data context shared across all screens."""

    primary_user: MockUser
    secondary_users: list[MockUser] = Field(default_factory=list)
    domain: DomainContext = Field(default_factory=DomainContext)


# =============================================================================
# Shared Components
# =============================================================================


class SharedComponent(BaseModel):
    """A component reused across multiple screens."""

    name: str  # "Sidebar", "TopNav", "NotificationBell", "UserMenu"
    used_on: list[str] = Field(default_factory=list)  # routes
    props: dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Image Manifest
# =============================================================================


class ImageEntry(BaseModel):
    """Global image registry entry."""

    id: str  # referenced by ImageSlot.value or ImageSlot.slot
    source: Literal["supabase", "unsplash", "gradient", "initials", "icon"]
    value: str  # URL, photo-id, gradient CSS, initials, icon name
    alt: str = ""
    fallback_gradient: str | None = None


# =============================================================================
# ScreenMap — the top-level contract
# =============================================================================


class ScreenMap(BaseModel):
    """Complete prototype specification produced by the Planning Agent.

    This is the single source of truth between planning and rendering.
    The scaffold renderer translates this into React + Tailwind code.
    """

    # App-level structure
    app_shell: AppShell
    screens: list[Screen] = Field(default_factory=list)
    shared_components: list[SharedComponent] = Field(default_factory=list)
    mock_context: MockContext
    image_manifest: list[ImageEntry] = Field(default_factory=list)

    # Metadata for validation and tracking
    total_screens: int = 0
    feature_coverage: dict[str, str] = Field(default_factory=dict)  # feature_slug → route
    depth_summary: dict[str, int] = Field(default_factory=dict)  # full: 8, visual: 3, ...
    planning_notes: str = ""  # agent's reasoning summary
