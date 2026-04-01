"""Deterministic Stitch — combines scaffold, layout, routing, and builder pages.

Produces the complete file tree:
  - Config scaffold (package.json, vite, tailwind, tsconfig, index.html, etc.)
  - Component library (Card, Badge, Button, etc.)
  - Bridge files (Feature wrapper, aios-bridge.js)
  - Layout.tsx (sidebar navigation from coherence plan)
  - App.tsx (routing from coherence plan)
  - Page files (from Haiku builders)
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.schemas_prototype_builder import PrototypePayload

logger = logging.getLogger(__name__)


def _kebab_to_pascal(name: str) -> str:
    """Convert kebab-case to PascalCase for component names."""
    return "".join(w.capitalize() for w in name.strip("/").split("-") if w)


def _route_to_component_name(route: str) -> str:
    """Convert route to a React component name."""
    clean = route.strip("/")
    if not clean:
        return "IndexPage"
    parts = clean.split("/")
    return "".join(w.capitalize() for w in parts[0].split("-") if w) + "Page"


def stitch_scaffold(
    payload: PrototypePayload,
    prebuild: Any,
    project_plan: dict[str, Any],
    pages: list[dict],
    ai_demos: list[dict] | None = None,
) -> dict[str, str]:
    """Build the complete file tree from scaffold + plan + pages.

    Args:
        payload: Project payload (for design tokens, branding)
        prebuild: Prebuild intelligence (not used directly here)
        project_plan: Coherence agent's project plan
        pages: List of {route, component_name, tsx} from Haiku builders
        ai_demos: List of {agent_slug, component_name, tsx} from AI demo builders

    Returns:
        dict of filename → content
    """
    from app.core.build_plan_renderer import _render_vite_config_scaffold

    files: dict[str, str] = {}

    # ── Config scaffold (package.json, vite, tailwind, components, etc.) ──
    files.update(_render_vite_config_scaffold(payload))

    # ── Override LucideIcon to handle kebab-case names ──
    files["src/components/ui/LucideIcon.tsx"] = (
        "import * as icons from 'lucide-react'\n"
        "import type { LucideProps } from 'lucide-react'\n\n"
        "type IconComponent = React.FC<LucideProps>\n\n"
        "function toPascal(str: string) {\n"
        "  return str.replace(/(^|[-_])(\\w)/g, (_, __, c) => c.toUpperCase())\n"
        "}\n\n"
        "interface LucideIconProps {\n"
        "  name: string\n"
        "  size?: number\n"
        "  className?: string\n"
        "}\n\n"
        "export function LucideIcon({ name, size = 20, className = '' }: LucideIconProps) {\n"
        "  const pascal = toPascal(name)\n"
        "  const Icon = (icons as unknown as Record<string, IconComponent>)[pascal]\n"
        "    ?? (icons as unknown as Record<string, IconComponent>)[name]\n"
        "  if (!Icon) return <span className={className}>{name}</span>\n"
        "  return <Icon size={size} className={className} />\n"
        "}\n"
    )

    # ── Feature wrapper + AiosBridge ──
    files["src/lib/aios/Feature.tsx"] = _FEATURE_TSX
    files["src/lib/aios/AiosBridge.tsx"] = _AIOS_BRIDGE_TSX

    # ── Route manifest (static JSON for workbench to fetch) ──
    import json as _json

    route_manifest = project_plan.get("route_manifest", {})
    if route_manifest:
        files["public/route-manifest.json"] = _json.dumps(route_manifest, indent=2)

    # ── SPA redirect for Netlify ──
    files["public/_redirects"] = "/* /index.html 200\n"

    # ── Layout.tsx ──
    files["src/pages/Layout.tsx"] = _generate_layout(project_plan, payload)

    # ── App.tsx ──
    files["src/App.tsx"] = _generate_app(project_plan, pages)

    # ── Page files from Haiku builders ──
    for page in pages:
        component_name = page.get("component_name", "")
        tsx = page.get("tsx", "")
        if component_name and tsx:
            files[f"src/pages/{component_name}.tsx"] = tsx

    # ── AI panel component files ──
    for ai_panel in ai_demos or []:
        component_name = ai_panel.get("component_name", "")
        tsx = ai_panel.get("tsx", "")
        if component_name and tsx:
            files[f"src/components/ai/{component_name}.tsx"] = tsx

    # ── Fallback pages for routes with no builder output ──
    built_routes = {p.get("route") for p in pages}
    for section in project_plan.get("nav_sections", []):
        for screen in section.get("screens", []):
            route = screen["route"]
            if route not in built_routes:
                comp_name = _route_to_component_name(route)
                nav_label = screen.get("nav_label", route)
                files[f"src/pages/{comp_name}.tsx"] = _generate_fallback_page(
                    comp_name, nav_label, screen.get("page_title", nav_label)
                )
                logger.warning(f"Generated fallback page for {route} ({comp_name})")

    logger.info(f"Stitched {len(files)} files ({len(pages)} builder pages)")
    return files


# =============================================================================
# Layout generation
# =============================================================================


def _generate_layout(project_plan: dict, payload: PrototypePayload) -> str:
    """Generate Layout.tsx with navigation from the coherence plan.

    Dispatches to a nav-style-specific renderer based on the plan's nav_style.
    """
    nav_style = project_plan.get("nav_style", "sidebar-dark")
    renderer = {
        "sidebar-dark": _render_sidebar_dark,
        "sidebar-light": _render_sidebar_light,
        "topnav": _render_topnav,
        "icon-sidebar": _render_icon_sidebar,
        "minimal": _render_minimal,
    }.get(nav_style, _render_sidebar_dark)
    return renderer(project_plan, payload)


# -- Shared nav data helper --------------------------------------------------


def _build_nav_data(
    project_plan: dict, payload: PrototypePayload
) -> dict[str, Any]:
    """Extract common nav data used by all renderers."""
    theme = project_plan.get("theme", {})
    nav_sections = project_plan.get("nav_sections", [])
    app_name = project_plan.get("app_name", payload.project_name or "Prototype")

    # Read theme with backward-compatible fallbacks
    nav_bg = theme.get("nav_bg") or theme.get("sidebar_bg", "bg-slate-900")
    nav_text = theme.get("nav_text") or theme.get("sidebar_text", "text-slate-300")
    nav_active = (
        theme.get("nav_active")
        or theme.get("sidebar_active_bg", "bg-primary/10 text-primary font-medium")
    )
    content_bg = theme.get("content_bg", "bg-gray-50")
    # Hard fallback: content area MUST be light
    _ALLOWED_CONTENT_BG = {
        "bg-white",
        "bg-gray-50",
        "bg-slate-50",
        "bg-zinc-50",
        "bg-neutral-50",
    }
    if content_bg not in _ALLOWED_CONTENT_BG:
        content_bg = "bg-gray-50"

    # Build sections data
    sections_data = []
    flat_items = []
    for section in nav_sections:
        if not isinstance(section, dict):
            continue
        items = []
        for screen in section.get("screens", []):
            item = {
                "route": screen["route"],
                "label": screen.get("nav_label", screen.get("page_title", "")),
                "icon": screen.get("icon", "Circle"),
            }
            items.append(item)
            flat_items.append(item)
        sections_data.append({"label": section.get("label", ""), "items": items})

    # Serialize nav sections as TypeScript
    nav_ts_items = []
    for section in sections_data:
        items_ts = []
        for item in section["items"]:
            items_ts.append(
                f"      {{ route: '{item['route']}', "
                f"label: '{item['label']}', "
                f"icon: '{item['icon']}' }}"
            )
        items_joined = ",\n".join(items_ts)
        nav_ts_items.append(
            f"  {{\n    label: '{section['label']}',\n"
            f"    items: [\n{items_joined},\n    ],\n  }}"
        )
    nav_ts = "[\n" + ",\n".join(nav_ts_items) + ",\n]"

    # Flat items TS (for topnav / icon-sidebar)
    flat_ts_items = []
    for item in flat_items:
        flat_ts_items.append(
            f"  {{ route: '{item['route']}', "
            f"label: '{item['label']}', "
            f"icon: '{item['icon']}' }}"
        )
    flat_items_ts = "[\n" + ",\n".join(flat_ts_items) + ",\n]"

    # Primary persona for user menu
    persona = payload.personas[0] if payload.personas else None
    user_name = persona.name if persona else "Demo User"
    user_role = persona.role if persona else "User"
    user_initials = (
        "".join(w[0].upper() for w in user_name.split()[:2]) if user_name else "DU"
    )

    return {
        "app_name": app_name,
        "nav_bg": nav_bg,
        "nav_text": nav_text,
        "nav_active": nav_active,
        "content_bg": content_bg,
        "sections_data": sections_data,
        "nav_ts": nav_ts,
        "flat_items_ts": flat_items_ts,
        "user_name": user_name,
        "user_role": user_role,
        "user_initials": user_initials,
    }


# -- Sidebar Dark (default) --------------------------------------------------


def _render_sidebar_dark(project_plan: dict, payload: PrototypePayload) -> str:
    d = _build_nav_data(project_plan, payload)
    return f"""\
import {{ NavLink, Outlet }} from 'react-router-dom'
import {{ LucideIcon, Avatar }} from '@/components/ui'

const NAV_SECTIONS = {d["nav_ts"]}

export default function Layout() {{
  return (
    <div className="flex h-screen">
      {{/* Sidebar */}}
      <nav className="w-64 {d["nav_bg"]} {d["nav_text"]} flex flex-col shrink-0">
        {{/* Logo */}}
        <div className="px-6 py-5 border-b border-white/10">
          <h1 className="font-heading font-bold text-white text-lg">{d["app_name"]}</h1>
        </div>

        {{/* Nav sections */}}
        <div className="flex-1 overflow-y-auto py-4">
          {{NAV_SECTIONS.map((section) => (
            <div key={{section.label}} className="mb-6">
              <h3 className={{"px-6 text-[11px] font-semibold " +
                "text-slate-500 uppercase tracking-wider mb-2"}}>
                {{section.label}}
              </h3>
              {{section.items.map((item) => (
                <NavLink
                  key={{item.route}}
                  to={{item.route}}
                  className={{({{ isActive }}) =>
                    `flex items-center gap-3 px-6 py-2 text-sm transition-colors ${{
                      isActive
                        ? '{d["nav_active"]} border-r-2 border-primary'
                        : 'hover:bg-white/5 {d["nav_text"]}'
                    }}`
                  }}
                >
                  <LucideIcon name={{item.icon}} size={{18}} />
                  {{item.label}}
                </NavLink>
              ))}}
            </div>
          ))}}
        </div>

        {{/* User menu */}}
        <div className="px-6 py-4 border-t border-white/10 flex items-center gap-3">
          <Avatar initials="{d["user_initials"]}" name="{d["user_name"]}" size="sm" />
          <div>
            <p className="text-sm font-medium text-white">{d["user_name"]}</p>
            <p className="text-xs text-slate-500">{d["user_role"]}</p>
          </div>
        </div>
      </nav>

      {{/* Content */}}
      <main className="flex-1 overflow-y-auto {d["content_bg"]}">
        <div className="p-8 animate-page-enter">
          <Outlet />
        </div>
      </main>
    </div>
  )
}}
"""


# -- Sidebar Light ------------------------------------------------------------


def _render_sidebar_light(project_plan: dict, payload: PrototypePayload) -> str:
    d = _build_nav_data(project_plan, payload)
    # Override defaults for light sidebar
    light_bg_default = "bg-white border-r border-gray-200"
    light_active_default = "bg-primary/10 text-primary font-medium"
    nav_bg = (
        d["nav_bg"]
        if "white" in d["nav_bg"] or "gray" in d["nav_bg"]
        else light_bg_default
    )
    nav_text = d["nav_text"] if "gray" in d["nav_text"] else "text-gray-600"
    nav_active = (
        d["nav_active"] if "primary" in d["nav_active"] else light_active_default
    )

    return f"""\
import {{ NavLink, Outlet }} from 'react-router-dom'
import {{ LucideIcon, Avatar }} from '@/components/ui'

const NAV_SECTIONS = {d["nav_ts"]}

export default function Layout() {{
  return (
    <div className="flex h-screen">
      {{/* Sidebar */}}
      <nav className="w-64 {nav_bg} {nav_text} flex flex-col shrink-0">
        {{/* Logo */}}
        <div className="px-6 py-5 border-b border-gray-100">
          <h1 className="font-heading font-bold text-gray-900 text-lg">{d["app_name"]}</h1>
        </div>

        {{/* Nav sections */}}
        <div className="flex-1 overflow-y-auto py-4">
          {{NAV_SECTIONS.map((section) => (
            <div key={{section.label}} className="mb-6">
              <h3 className={{"px-6 text-[11px] font-semibold " +
                "text-gray-400 uppercase tracking-wider mb-2"}}>
                {{section.label}}
              </h3>
              {{section.items.map((item) => (
                <NavLink
                  key={{item.route}}
                  to={{item.route}}
                  className={{({{ isActive }}) =>
                    `flex items-center gap-3 px-6 py-2 text-sm transition-colors ${{
                      isActive
                        ? '{nav_active} border-r-2 border-primary'
                        : 'hover:bg-gray-50 {nav_text}'
                    }}`
                  }}
                >
                  <LucideIcon name={{item.icon}} size={{18}} />
                  {{item.label}}
                </NavLink>
              ))}}
            </div>
          ))}}
        </div>

        {{/* User menu */}}
        <div className="px-6 py-4 border-t border-gray-100 flex items-center gap-3">
          <Avatar initials="{d["user_initials"]}" name="{d["user_name"]}" size="sm" />
          <div>
            <p className="text-sm font-medium text-gray-900">{d["user_name"]}</p>
            <p className="text-xs text-gray-500">{d["user_role"]}</p>
          </div>
        </div>
      </nav>

      {{/* Content */}}
      <main className="flex-1 overflow-y-auto {d["content_bg"]}">
        <div className="p-8 animate-page-enter">
          <Outlet />
        </div>
      </main>
    </div>
  )
}}
"""


# -- Top Navigation -----------------------------------------------------------


def _render_topnav(project_plan: dict, payload: PrototypePayload) -> str:
    d = _build_nav_data(project_plan, payload)
    nav_bg = d["nav_bg"] if "white" in d["nav_bg"] or "slate" in d["nav_bg"] else "bg-white"
    border = "border-b border-gray-200"

    return f"""\
import {{ NavLink, Outlet }} from 'react-router-dom'
import {{ LucideIcon, Avatar }} from '@/components/ui'

const NAV_ITEMS = {d["flat_items_ts"]}

export default function Layout() {{
  return (
    <div className="flex flex-col h-screen">
      {{/* Top navigation bar */}}
      <nav className="{nav_bg} h-16 flex items-center px-6 shrink-0 {border}">
        <h1 className="font-heading font-bold text-lg mr-8">{d["app_name"]}</h1>
        <div className="flex items-center gap-1 flex-1">
          {{NAV_ITEMS.map((item) => (
            <NavLink
              key={{item.route}}
              to={{item.route}}
              className={{({{ isActive }}) =>
                `flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${{
                  isActive
                    ? '{d["nav_active"]}'
                    : 'text-gray-600 hover:bg-gray-100'
                }}`
              }}
            >
              <LucideIcon name={{item.icon}} size={{16}} />
              {{item.label}}
            </NavLink>
          ))}}
        </div>
        <div className="flex items-center gap-3">
          <Avatar initials="{d["user_initials"]}" name="{d["user_name"]}" size="sm" />
        </div>
      </nav>
      <main className="flex-1 overflow-y-auto {d["content_bg"]}">
        <div className="p-8 max-w-7xl mx-auto animate-page-enter">
          <Outlet />
        </div>
      </main>
    </div>
  )
}}
"""


# -- Icon Sidebar (narrow rail) ----------------------------------------------


def _render_icon_sidebar(project_plan: dict, payload: PrototypePayload) -> str:
    d = _build_nav_data(project_plan, payload)
    initial = d["app_name"][0].upper() if d["app_name"] else "P"

    return f"""\
import {{ NavLink, Outlet }} from 'react-router-dom'
import {{ LucideIcon, Avatar }} from '@/components/ui'

const NAV_ITEMS = {d["flat_items_ts"]}

export default function Layout() {{
  return (
    <div className="flex h-screen">
      <nav className="w-16 {d["nav_bg"]} flex flex-col items-center py-4 shrink-0">
        <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center mb-6">
          <span className="text-white font-bold text-sm">{initial}</span>
        </div>
        <div className="flex-1 flex flex-col items-center gap-2">
          {{NAV_ITEMS.map((item) => (
            <NavLink
              key={{item.route}}
              to={{item.route}}
              title={{item.label}}
              className={{({{ isActive }}) =>
                `w-10 h-10 rounded-xl flex items-center justify-center transition-colors ${{
                  isActive
                    ? 'bg-primary/10 text-primary'
                    : '{d["nav_text"]} hover:bg-white/10'
                }}`
              }}
            >
              <LucideIcon name={{item.icon}} size={{20}} />
            </NavLink>
          ))}}
        </div>
        <Avatar initials="{d["user_initials"]}" name="{d["user_name"]}" size="sm" />
      </nav>
      <main className="flex-1 overflow-y-auto {d["content_bg"]}">
        <div className="p-8 animate-page-enter">
          <Outlet />
        </div>
      </main>
    </div>
  )
}}
"""


# -- Minimal (hamburger drawer) ----------------------------------------------


def _render_minimal(project_plan: dict, payload: PrototypePayload) -> str:
    d = _build_nav_data(project_plan, payload)

    return f"""\
import {{ useState }} from 'react'
import {{ NavLink, Outlet }} from 'react-router-dom'
import {{ LucideIcon, Avatar }} from '@/components/ui'

const NAV_SECTIONS = {d["nav_ts"]}

export default function Layout() {{
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div className="flex flex-col h-screen">
      {{/* Minimal top bar */}}
      <div className="h-14 flex items-center px-6 border-b border-gray-200 bg-white shrink-0">
        <button onClick={{() => setMenuOpen(true)}} className="p-2 hover:bg-gray-100 rounded-lg">
          <LucideIcon name="Menu" size={{20}} />
        </button>
        <h1 className="font-heading font-bold ml-4">{d["app_name"]}</h1>
      </div>

      {{/* Drawer overlay */}}
      {{menuOpen && (
        <div className="fixed inset-0 z-50 flex">
          <div className="fixed inset-0 bg-black/30" onClick={{() => setMenuOpen(false)}} />
          <nav className="relative w-72 bg-white h-full shadow-xl p-6 overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h2 className="font-heading font-bold text-lg">{d["app_name"]}</h2>
              <button
                onClick={{() => setMenuOpen(false)}}
                className="p-1 hover:bg-gray-100 rounded"
              >
                <LucideIcon name="X" size={{18}} />
              </button>
            </div>
            {{NAV_SECTIONS.map((section) => (
              <div key={{section.label}} className="mb-6">
                <h3 className={{"text-[11px] font-semibold " +
                  "text-gray-400 uppercase tracking-wider mb-2"}}>
                  {{section.label}}
                </h3>
                {{section.items.map((item) => (
                  <NavLink
                    key={{item.route}}
                    to={{item.route}}
                    onClick={{() => setMenuOpen(false)}}
                    className={{({{ isActive }}) =>
                      `flex items-center gap-3 px-3 py-2 text-sm ${{
                        "rounded-lg transition-colors mb-1"
                      }} ${{
                        isActive
                          ? '{d["nav_active"]}'
                          : 'text-gray-600 hover:bg-gray-50'
                      }}`
                    }}
                  >
                    <LucideIcon name={{item.icon}} size={{18}} />
                    {{item.label}}
                  </NavLink>
                ))}}
              </div>
            ))}}
            <div className="border-t border-gray-100 pt-4 flex items-center gap-3">
              <Avatar initials="{d["user_initials"]}" name="{d["user_name"]}" size="sm" />
              <div>
                <p className="text-sm font-medium text-gray-900">{d["user_name"]}</p>
                <p className="text-xs text-gray-500">{d["user_role"]}</p>
              </div>
            </div>
          </nav>
        </div>
      )}}

      <main className="flex-1 overflow-y-auto {d["content_bg"]}">
        <div className="p-6 animate-page-enter">
          <Outlet />
        </div>
      </main>
    </div>
  )
}}
"""


# =============================================================================
# App.tsx generation
# =============================================================================


def _generate_app(project_plan: dict, pages: list[dict]) -> str:
    """Generate App.tsx with routing from the project plan."""
    nav_sections = project_plan.get("nav_sections", [])

    # Collect all routes and their component names
    route_map: dict[str, str] = {}  # route → component name

    # From builder output
    for page in pages:
        route = page.get("route", "")
        comp_name = page.get("component_name", "")
        if route and comp_name:
            route_map[route] = comp_name

    # From plan (fill gaps with generated names)
    for section in nav_sections:
        for screen in section.get("screens", []):
            route = screen["route"]
            if route not in route_map:
                route_map[route] = _route_to_component_name(route)

    if not route_map:
        route_map["/"] = "IndexPage"

    # Find first route for redirect
    first_route = "/"
    for section in nav_sections:
        for screen in section.get("screens", []):
            first_route = screen["route"]
            break
        break

    # Build imports
    import_lines = ["import { Routes, Route, Navigate } from 'react-router-dom'"]
    import_lines.append("import { AiosBridge } from './lib/aios/AiosBridge'")
    import_lines.append("import Layout from './pages/Layout'")
    for _route, comp_name in sorted(route_map.items(), key=lambda x: x[0]):
        import_lines.append(f"import {comp_name} from './pages/{comp_name}'")

    # Build routes
    route_lines = []
    for route, comp_name in sorted(route_map.items(), key=lambda x: x[0]):
        route_lines.append(f'        <Route path="{route}" element={{<{comp_name} />}} />')

    imports = "\n".join(import_lines)
    routes = "\n".join(route_lines)

    return f"""\
{imports}

export default function App() {{
  return (
    <>
      <AiosBridge />
      <Routes>
        <Route element={{<Layout />}}>
          <Route index element={{<Navigate to="{first_route}" replace />}} />
{routes}
        </Route>
      </Routes>
    </>
  )
}}
"""


# =============================================================================
# Fallback page for missing builder output
# =============================================================================


def _generate_fallback_page(comp_name: str, nav_label: str, page_title: str) -> str:
    """Generate a simple fallback page for routes with no builder output."""
    return f"""\
import {{ LucideIcon }} from '@/components/ui'

export default function {comp_name}() {{
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-heading font-bold text-gray-900">{page_title}</h1>
        <p className="text-gray-500 mt-1">This page is under construction.</p>
      </div>
      <div className={{"flex items-center justify-center h-64 " +
        "bg-white rounded-xl border-2 border-dashed border-gray-200"}}>
        <div className="text-center text-gray-400">
          <LucideIcon name="Construction" size={{48}} className="mx-auto mb-3" />
          <p className="font-medium">{nav_label}</p>
          <p className="text-sm">Coming soon</p>
        </div>
      </div>
    </div>
  )
}}
"""


# =============================================================================
# Feature wrapper component
# =============================================================================

_FEATURE_TSX = """\
import type { ReactNode } from 'react'

interface FeatureProps {
  id: string
  children: ReactNode
}

export function Feature({ id, children }: FeatureProps) {
  return (
    <div data-aios-feature={id} data-feature-id={id} className="relative">
      {children}
    </div>
  )
}
"""

# =============================================================================
# AiosBridge — zero-UI component for postMessage communication
# =============================================================================

_AIOS_BRIDGE_TSX = """\
import { useEffect, useCallback, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'

/**
 * AiosBridge — zero-UI React component for postMessage communication
 * with the parent AIOS workbench iframe host.
 *
 * Inbound commands:
 *   aios:navigate         → SPA navigation via react-router
 *   aios:highlight-feature → scroll to + pulse outline a single feature
 *   aios:clear-highlights → remove all highlight classes
 *   aios:show-radar       → overlay indicator dots on multiple features
 *
 * Outbound events:
 *   aios:page-change      → reports current path + visible feature IDs
 *   aios:feature-click    → when user clicks inside a Feature wrapper
 */
export function AiosBridge() {
  const navigate = useNavigate()
  const location = useLocation()
  const radarDotsRef = useRef<Array<{
    featureId: string; element: Element; dotEl: HTMLElement
  }>>([])
  const scrollHandlerRef = useRef<(() => void) | null>(null)

  // Report page changes to parent
  useEffect(() => {
    const featureEls = document.querySelectorAll('[data-aios-feature]')
    const featureIds = Array.from(featureEls).map(
      (el) => el.getAttribute('data-aios-feature') || ''
    ).filter(Boolean)

    window.parent.postMessage(
      { type: 'aios:page-change', path: location.pathname, featureIds },
      '*'
    )
  }, [location.pathname])

  // Feature click handler — delegated on document
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      const target = (e.target as HTMLElement).closest('[data-aios-feature]')
      if (!target) return
      const featureId = target.getAttribute('data-aios-feature')
      if (featureId) {
        window.parent.postMessage(
          { type: 'aios:feature-click', featureId },
          '*'
        )
      }
    }
    document.addEventListener('click', handler)
    return () => document.removeEventListener('click', handler)
  }, [])

  // Position a radar dot element over its target feature
  const positionRadarDot = useCallback(
    (dotEl: HTMLElement, targetEl: Element) => {
      const rect = targetEl.getBoundingClientRect()
      const scrollX = window.scrollX || window.pageXOffset
      const scrollY = window.scrollY || window.pageYOffset
      dotEl.style.top = `${rect.top + scrollY + 4}px`
      dotEl.style.left = `${rect.right + scrollX - 28}px`
    }, []
  )

  // Remove all radar dot DOM elements
  const clearAllRadar = useCallback(() => {
    for (const dot of radarDotsRef.current) {
      dot.dotEl?.parentNode?.removeChild(dot.dotEl)
    }
    radarDotsRef.current = []
    if (scrollHandlerRef.current) {
      window.removeEventListener('scroll', scrollHandlerRef.current, true)
      scrollHandlerRef.current = null
    }
  }, [])

  // Clear highlight outlines
  const clearHighlights = useCallback(() => {
    document.querySelectorAll('.aios-highlight').forEach((el) => {
      el.classList.remove('aios-highlight')
    })
  }, [])

  // Highlight a single feature
  const highlightFeature = useCallback((featureId: string) => {
    clearHighlights()
    clearAllRadar()
    const el = document.querySelector(`[data-aios-feature="${featureId}"]`)
    if (el) {
      el.classList.add('aios-highlight')
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }, [clearHighlights, clearAllRadar])

  // Show radar dots on multiple features — creates actual DOM elements
  const showRadar = useCallback(
    (features: Array<{ featureId: string }>) => {
      clearAllRadar()
      clearHighlights()

      for (const f of features) {
        const el = document.querySelector(
          `[data-aios-feature="${f.featureId}"]`
        )
        if (!el) continue

        // Outline highlight on the feature container
        el.classList.add('aios-highlight')

        // Create radar dot element
        const dot = document.createElement('div')
        dot.className = 'aios-radar'
        dot.setAttribute('data-radar-feature', f.featureId)
        dot.innerHTML =
          '<div class="aios-radar-core"></div>' +
          '<div class="aios-radar-ring"></div>' +
          '<div class="aios-radar-ring aios-radar-ring-2"></div>'

        // Click sends feature-click to parent
        const fId = f.featureId
        dot.addEventListener('click', (e) => {
          e.stopPropagation()
          window.parent.postMessage(
            { type: 'aios:feature-click', featureId: fId },
            '*'
          )
        })

        document.body.appendChild(dot)
        positionRadarDot(dot, el)
        radarDotsRef.current.push({
          featureId: f.featureId, element: el, dotEl: dot,
        })
      }

      // Reposition dots on scroll
      if (radarDotsRef.current.length > 0) {
        const handler = () => {
          for (const d of radarDotsRef.current) {
            if (d.element && d.dotEl) positionRadarDot(d.dotEl, d.element)
          }
        }
        window.addEventListener('scroll', handler, true)
        scrollHandlerRef.current = handler
      }

      // Scroll to first match
      const first = features[0]
      if (first) {
        const el = document.querySelector(
          `[data-aios-feature="${first.featureId}"]`
        )
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }
    },
    [clearAllRadar, clearHighlights, positionRadarDot]
  )

  // Listen for inbound postMessage commands from parent
  useEffect(() => {
    const handler = (e: MessageEvent) => {
      const data = e.data
      if (!data || typeof data.type !== 'string') return

      switch (data.type) {
        case 'aios:navigate':
          if (data.path && typeof data.path === 'string') {
            navigate(data.path)
          }
          break
        case 'aios:highlight-feature':
          if (data.featureId) {
            highlightFeature(data.featureId)
          }
          break
        case 'aios:clear-highlights':
          clearHighlights()
          clearAllRadar()
          break
        case 'aios:show-radar':
          if (Array.isArray(data.features)) {
            showRadar(data.features)
          }
          break
        case 'aios:clear-radar':
          clearAllRadar()
          break
      }
    }
    window.addEventListener('message', handler)
    return () => window.removeEventListener('message', handler)
  }, [navigate, highlightFeature, showRadar, clearHighlights, clearAllRadar])

  return null
}
"""
