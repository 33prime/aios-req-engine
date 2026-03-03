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
) -> dict[str, str]:
    """Build the complete file tree from scaffold + plan + pages.

    Args:
        payload: Project payload (for design tokens, branding)
        prebuild: Prebuild intelligence (not used directly here)
        project_plan: Coherence agent's project plan
        pages: List of {route, component_name, tsx} from Haiku builders

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
    """Generate Layout.tsx with sidebar navigation from the coherence plan."""
    theme = project_plan.get("theme", {})
    nav_sections = project_plan.get("nav_sections", [])
    app_name = project_plan.get("app_name", payload.project_name or "Prototype")

    sidebar_bg = theme.get("sidebar_bg", "bg-slate-900")
    sidebar_text = theme.get("sidebar_text", "text-slate-300")
    sidebar_active = theme.get("sidebar_active_bg", "bg-primary/10 text-primary font-medium")
    content_bg = theme.get("content_bg", "bg-gray-50")

    # Build nav sections data
    sections_data = []
    for section in nav_sections:
        items = []
        for screen in section.get("screens", []):
            items.append(
                {
                    "route": screen["route"],
                    "label": screen.get("nav_label", screen.get("page_title", "")),
                    "icon": screen.get("icon", "Circle"),
                }
            )
        sections_data.append(
            {
                "label": section.get("label", ""),
                "items": items,
            }
        )

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
            f"  {{\n    label: '{section['label']}',\n    items: [\n{items_joined},\n    ],\n  }}"
        )

    nav_ts = "[\n" + ",\n".join(nav_ts_items) + ",\n]"

    # Primary persona for user menu
    persona = payload.personas[0] if payload.personas else None
    user_name = persona.name if persona else "Demo User"
    user_role = persona.role if persona else "User"
    user_initials = "".join(w[0].upper() for w in user_name.split()[:2]) if user_name else "DU"

    return f"""\
import {{ NavLink, Outlet }} from 'react-router-dom'
import {{ LucideIcon, Avatar }} from '@/components/ui'

const NAV_SECTIONS = {nav_ts}

export default function Layout() {{
  return (
    <div className="flex h-screen">
      {{/* Sidebar */}}
      <nav className="w-64 {sidebar_bg} {sidebar_text} flex flex-col shrink-0">
        {{/* Logo */}}
        <div className="px-6 py-5 border-b border-white/10">
          <h1 className="font-heading font-bold text-white text-lg">{app_name}</h1>
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
                        ? '{sidebar_active} border-r-2 border-primary'
                        : 'hover:bg-white/5 {sidebar_text}'
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
          <Avatar initials="{user_initials}" name="{user_name}" size="sm" />
          <div>
            <p className="text-sm font-medium text-white">{user_name}</p>
            <p className="text-xs text-slate-500">{user_role}</p>
          </div>
        </div>
      </nav>

      {{/* Content */}}
      <main className="flex-1 overflow-y-auto {content_bg}">
        <div className="p-8 animate-page-enter">
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
