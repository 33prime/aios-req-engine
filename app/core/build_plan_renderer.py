"""Render a ProjectPlan + PrototypePayload into consumable files.

Pure Python — no LLM calls. Produces:
- CLAUDE.md (from Opus-generated content)
- build-plan.md (ralph-loop compatible checklist)
- streams/{id}.md (per-stream task plans)
- design-tokens.json
- mock-data-seed.json
- feature-inventory.json
- orchestrator.md (guided-mode commands)
- public/aios-bridge.js (bridge injection script)
- src/lib/aios/* (reusable bridge component library)
"""

from __future__ import annotations

import json
import logging
import re

from app.core.schemas_prototype_builder import ProjectPlan, PrototypePayload

logger = logging.getLogger(__name__)


def render_build_plan(plan: ProjectPlan, payload: PrototypePayload) -> dict[str, str]:
    """Render a plan + payload into a filename→content map."""
    files: dict[str, str] = {}

    # ── CLAUDE.md ──────────────────────────────────────────────────────────
    files["CLAUDE.md"] = plan.claude_md_content or _fallback_claude_md(payload)

    # ── build-plan.md (ralph-loop compatible) ──────────────────────────────
    files["build-plan.md"] = _render_build_plan_md(plan, payload)

    # ── Per-stream plans ───────────────────────────────────────────────────
    task_by_id = {t.task_id: t for t in plan.tasks}
    for stream in plan.streams:
        stream_tasks = [task_by_id[tid] for tid in stream.tasks if tid in task_by_id]
        if stream_tasks:
            files[f"streams/{stream.stream_id}.md"] = _render_stream_md(stream, stream_tasks)

    # ── design-tokens.json ─────────────────────────────────────────────────
    if payload.design_contract:
        dc = payload.design_contract
        files["design-tokens.json"] = json.dumps(
            {
                "colors": {
                    "primary": dc.tokens.primary_color,
                    "secondary": dc.tokens.secondary_color,
                    "accent": dc.tokens.accent_color,
                },
                "brand_colors": dc.brand_colors,
                "typography": {
                    "heading": dc.tokens.font_heading,
                    "body": dc.tokens.font_body,
                },
                "spacing": dc.tokens.spacing,
                "corners": dc.tokens.corners,
                "style_direction": dc.style_direction,
            },
            indent=2,
        )

    # ── mock-data-seed.json ────────────────────────────────────────────────
    mock_seed: dict = {
        "personas": [
            {"name": p.name, "role": p.role, "goals": p.goals[:3]} for p in payload.personas[:5]
        ],
        "screens": [
            {
                "step_id": s.id,
                "title": s.title,
                "phase": s.phase,
                "narrative": s.how_it_works[:300] if s.how_it_works else "",
            }
            for s in payload.solution_flow_steps
        ],
    }
    files["mock-data-seed.json"] = json.dumps(mock_seed, indent=2)

    # ── feature-inventory.json ─────────────────────────────────────────────
    slug_map = _build_slug_map(payload.features)
    inventory = {
        f.id: {
            "name": f.name,
            "slug": slug_map.get(f.id, _slugify(f.name)),
            "priority": f.priority,
            "overview": f.overview[:200] if f.overview else "",
        }
        for f in payload.features
    }
    files["feature-inventory.json"] = json.dumps(inventory, indent=2)

    # ── orchestrator.md ────────────────────────────────────────────────────
    files["orchestrator.md"] = _render_orchestrator_md(plan)

    # ── public/aios-bridge.js ──────────────────────────────────────────────
    from app.services.bridge_injector import BRIDGE_SCRIPT

    files["public/aios-bridge.js"] = BRIDGE_SCRIPT

    # ── src/lib/aios/* (bridge component library) ──────────────────────────
    files["src/lib/aios/Feature.tsx"] = _AIOS_FEATURE_TSX
    files["src/lib/aios/Screen.tsx"] = _AIOS_SCREEN_TSX
    files["src/lib/aios/useFeatureProps.ts"] = _AIOS_USE_FEATURE_PROPS_TS
    files["src/lib/aios/types.ts"] = _AIOS_TYPES_TS
    files["src/lib/aios/AiosOverlay.tsx"] = _AIOS_OVERLAY_TSX
    files["src/lib/aios/index.ts"] = _AIOS_INDEX_TS
    files["src/lib/aios/registry.ts"] = _render_registry_ts(payload.features)

    # ── Pre-rendered Vite scaffold ────────────────────────────────────────
    files.update(_render_vite_scaffold(payload))

    logger.info(f"Rendered {len(files)} files for plan {plan.plan_id}")
    return files


# =============================================================================
# Renderers
# =============================================================================


def _render_build_plan_md(plan: ProjectPlan, payload: PrototypePayload) -> str:
    """Render ralph-loop compatible build-plan.md."""
    lines = [
        f"# Build Plan: {payload.project_name}",
        f"Generated: {plan.created_at} | Cost: ~${plan.total_estimated_cost_usd:.2f} "
        f"| Time: ~{plan.total_estimated_minutes} min | Streams: {len(plan.streams)}",
        "",
    ]

    task_by_id = {t.task_id: t for t in plan.tasks}

    for phase in sorted(plan.phases, key=lambda p: p.phase_number):
        lines.append(f"## Phase {phase.phase_number}: {phase.name} [NOT STARTED]")
        if phase.description:
            lines.append(f"> {phase.description}")
        lines.append("")

        for tid in phase.task_ids:
            task = task_by_id.get(tid)
            if not task:
                continue
            deps = ""
            if task.depends_on:
                deps = f" [depends: {', '.join(task.depends_on)}]"
            lines.append(
                f"- [ ] {task.task_id}: {task.name} ({task.model}){deps} "
                f"— ${task.estimated_cost_usd:.2f}"
            )
        lines.append("")

    if plan.completion_criteria:
        lines.append("## Completion Criteria")
        for c in plan.completion_criteria:
            lines.append(f"- [ ] {c}")
        lines.append("")

    return "\n".join(lines)


def _render_stream_md(stream, tasks) -> str:
    """Render a per-stream plan."""
    lines = [
        f"# Stream: {stream.name}",
        f"Model: {stream.model} | Branch: {stream.branch_name} "
        f"| Est: ~{stream.estimated_duration_minutes} min",
        "",
        "## Tasks (in order)",
        "",
    ]

    for task in tasks:
        lines.append(f"### {task.task_id}: {task.name}")
        lines.append(f"**Model**: {task.model}")
        if task.description:
            lines.append(f"\n{task.description}")
        if task.depends_on:
            lines.append(f"\n**Depends on**: {', '.join(task.depends_on)}")
        if task.file_targets:
            lines.append(f"\n**Files**: {', '.join(task.file_targets)}")
        if task.acceptance_criteria:
            lines.append("\n**Acceptance criteria**:")
            for ac in task.acceptance_criteria:
                lines.append(f"- {ac}")
        lines.append("")

    return "\n".join(lines)


def _render_orchestrator_md(plan: ProjectPlan) -> str:
    """Render orchestration guide for guided-mode execution."""
    lines = [
        "# Orchestration Guide",
        "",
        "Run each stream in a separate terminal. Streams within the same phase "
        "can run in parallel.",
        "",
    ]

    for i, stream in enumerate(plan.streams, 1):
        lines.append(f"## Stream {i} ({stream.model}): {stream.name}")
        lines.append("```bash")
        wt = f".worktrees/{stream.stream_id}"
        lines.append(f"cd /project && git worktree add {wt} -b {stream.branch_name}")
        lines.append(f"cd {wt}")
        ralph_cmd = (
            f"claude --model {stream.model} "
            f'"/ralph-loop \\"Read streams/{stream.stream_id}.md. '
            f'Pick up next unchecked task, implement it, mark done.\\""'
        )
        lines.append(ralph_cmd)
        lines.append("```")
        lines.append("")

    lines.append("## After All Streams Complete")
    lines.append("```bash")
    lines.append("cd /project")
    for stream in plan.streams:
        lines.append(f"git merge {stream.branch_name}")
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def _fallback_claude_md(payload: PrototypePayload) -> str:
    """Generate a minimal CLAUDE.md if Opus didn't provide one."""
    slug_map = _build_slug_map(payload.features)
    lines = [
        f"# {payload.project_name} — Prototype",
        "",
        f"Company: {payload.company_name}",
        f"Vision: {payload.project_vision[:300]}",
        "",
        "## Stack",
        f"- Scaffold: {payload.tech_contract.scaffold_type}",
        f"- Design: {payload.tech_contract.design_system}",
        "",
        "## Feature Inventory",
        "",
    ]
    for f in payload.features:
        slug = slug_map.get(f.id, _slugify(f.name))
        lines.append(f"- `{slug}` → `{f.id}` — {f.name}")
    lines.append("")
    lines.append("## AIOS Feature Tracking (REQUIRED)")
    lines.append("Import from `src/lib/aios/`:")
    lines.append('- Wrap interactive components: `<Feature id="content-calendar">...</Feature>`')
    lines.append('- Wrap pages: `<Screen name="Dashboard">...</Screen>`')
    lines.append("- Third-party elements: `const props = useFeatureProps('content-calendar')`")
    lines.append("- Use SLUGS, not UUIDs. See `src/lib/aios/registry.ts` for the slug map.")
    lines.append("- Do NOT modify files in `src/lib/aios/` or `public/aios-bridge.js`")
    lines.append("- `<AiosOverlay />` MUST be in the root layout")
    lines.append("")
    return "\n".join(lines)


# =============================================================================
# Pre-rendered Vite scaffold
# =============================================================================

SPACING_MAP = {"compact": "0.5rem", "balanced": "1rem", "generous": "1.5rem"}
CORNERS_MAP = {
    "sharp": "0",
    "slightly-rounded": "0.375rem",
    "rounded": "0.75rem",
    "pill": "9999px",
}


def _render_vite_scaffold(payload: PrototypePayload) -> dict[str, str]:
    """Render 12 deterministic Vite scaffold files from payload data.

    Eliminates the need for an agent to run npm create, install deps,
    and write configs — saving ~$1.20 per build.
    """
    files: dict[str, str] = {}
    slug = _slugify(payload.project_name) if payload.project_name else "prototype"

    # Design token values
    dc = payload.design_contract
    primary = dc.tokens.primary_color if dc else "#3b82f6"
    secondary = dc.tokens.secondary_color if dc else "#6b7280"
    accent = dc.tokens.accent_color if dc else "#f59e0b"
    font_heading = dc.tokens.font_heading if dc else "Inter"
    font_body = dc.tokens.font_body if dc else "Inter"
    spacing = dc.tokens.spacing if dc else "balanced"
    corners = dc.tokens.corners if dc else "slightly-rounded"

    spacing_val = SPACING_MAP.get(spacing, "1rem")
    corners_val = CORNERS_MAP.get(corners, "0.375rem")

    # ── package.json ──────────────────────────────────────────────────────
    files["package.json"] = json.dumps(
        {
            "name": slug,
            "private": True,
            "version": "0.1.0",
            "type": "module",
            "scripts": {
                "dev": "vite",
                "build": "tsc && vite build",
                "preview": "vite preview",
            },
            "dependencies": {
                "react": "^18.3.1",
                "react-dom": "^18.3.1",
                "react-router-dom": "^6.28.0",
            },
            "devDependencies": {
                "@types/react": "^18.3.12",
                "@types/react-dom": "^18.3.1",
                "@vitejs/plugin-react": "^4.3.4",
                "autoprefixer": "^10.4.20",
                "postcss": "^8.4.49",
                "tailwindcss": "^3.4.15",
                "typescript": "^5.6.3",
                "vite": "^5.4.11",
            },
        },
        indent=2,
    )

    # ── vite.config.ts ────────────────────────────────────────────────────
    files["vite.config.ts"] = (
        "import { defineConfig } from 'vite'\n"
        "import react from '@vitejs/plugin-react'\n"
        "\n"
        "export default defineConfig({\n"
        "  plugins: [react()],\n"
        "  resolve: {\n"
        "    alias: { '@': '/src' },\n"
        "  },\n"
        "})\n"
    )

    # ── tailwind.config.js ────────────────────────────────────────────────
    files["tailwind.config.js"] = (
        "/** @type {import('tailwindcss').Config} */\n"
        "export default {\n"
        "  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],\n"
        "  theme: {\n"
        "    extend: {\n"
        "      colors: {\n"
        "        primary: 'var(--color-primary)',\n"
        "        secondary: 'var(--color-secondary)',\n"
        "        accent: 'var(--color-accent)',\n"
        "      },\n"
        "      fontFamily: {\n"
        "        heading: 'var(--font-heading)',\n"
        "        body: 'var(--font-body)',\n"
        "      },\n"
        "      borderRadius: {\n"
        "        DEFAULT: 'var(--radius)',\n"
        "      },\n"
        "    },\n"
        "  },\n"
        "  plugins: [],\n"
        "}\n"
    )

    # ── postcss.config.js ─────────────────────────────────────────────────
    files["postcss.config.js"] = (
        "export default {\n  plugins: {\n    tailwindcss: {},\n    autoprefixer: {},\n  },\n}\n"
    )

    # ── tsconfig.json ─────────────────────────────────────────────────────
    files["tsconfig.json"] = json.dumps(
        {
            "compilerOptions": {
                "target": "ES2020",
                "useDefineForClassFields": True,
                "lib": ["ES2020", "DOM", "DOM.Iterable"],
                "module": "ESNext",
                "skipLibCheck": True,
                "moduleResolution": "bundler",
                "allowImportingTsExtensions": True,
                "isolatedModules": True,
                "moduleDetection": "force",
                "noEmit": True,
                "jsx": "react-jsx",
                "strict": True,
                "noUnusedLocals": True,
                "noUnusedParameters": True,
                "noFallthroughCasesInSwitch": True,
                "paths": {"@/*": ["./src/*"]},
            },
            "include": ["src"],
        },
        indent=2,
    )

    # ── tsconfig.node.json ────────────────────────────────────────────────
    files["tsconfig.node.json"] = json.dumps(
        {
            "compilerOptions": {
                "target": "ES2022",
                "lib": ["ES2023"],
                "module": "ESNext",
                "skipLibCheck": True,
                "moduleResolution": "bundler",
                "allowImportingTsExtensions": True,
                "isolatedModules": True,
                "moduleDetection": "force",
                "noEmit": True,
                "strict": True,
            },
            "include": ["vite.config.ts"],
        },
        indent=2,
    )

    # ── index.html ────────────────────────────────────────────────────────
    # Build Google Fonts link for heading + body fonts
    font_families = []
    for font in {font_heading, font_body}:
        if font and font != "system-ui":
            font_families.append(font.replace(" ", "+"))

    font_link = ""
    if font_families:
        families_param = "&".join(f"family={f}:wght@400;500;600;700" for f in sorted(font_families))
        font_link = (
            f'    <link rel="preconnect" href="https://fonts.googleapis.com" />\n'
            f'    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />\n'
            f'    <link rel="stylesheet" '
            f'href="https://fonts.googleapis.com/css2?{families_param}&display=swap" />\n'
        )

    title = payload.project_name or "Prototype"
    files["index.html"] = (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "  <head>\n"
        '    <meta charset="UTF-8" />\n'
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0" />\n'
        f"{font_link}"
        f"    <title>{title}</title>\n"
        "  </head>\n"
        "  <body>\n"
        '    <div id="root"></div>\n'
        '    <script type="module" src="/src/main.tsx"></script>\n'
        "  </body>\n"
        "</html>\n"
    )

    # ── src/main.tsx ──────────────────────────────────────────────────────
    files["src/main.tsx"] = (
        "import React from 'react'\n"
        "import ReactDOM from 'react-dom/client'\n"
        "import { BrowserRouter } from 'react-router-dom'\n"
        "import App from './App'\n"
        "import './index.css'\n"
        "\n"
        "ReactDOM.createRoot(document.getElementById('root')!).render(\n"
        "  <React.StrictMode>\n"
        "    <BrowserRouter>\n"
        "      <App />\n"
        "    </BrowserRouter>\n"
        "  </React.StrictMode>,\n"
        ")\n"
    )

    # ── Solution flow → routes + pages ────────────────────────────────────
    steps = payload.solution_flow_steps or []
    step_slugs: list[tuple[str, str, str]] = []  # (slug, title, component_name)
    for step in steps:
        step_slug = _slugify(step.title)
        # PascalCase component name — strip non-alpha before capitalizing
        words = re.sub(r"[^a-zA-Z0-9 ]", " ", step.title).split()[:4]
        component = "".join(w.capitalize() for w in words) + "Page"
        step_slugs.append((step_slug, step.title, component))

    # ── src/App.tsx ────────────────────────────────────────────────────────
    app_imports = ["import { Routes, Route } from 'react-router-dom'"]
    app_imports.append("import Layout from './components/Layout'")
    for _, _, component in step_slugs:
        app_imports.append(f"import {component} from './pages/{component}'")

    app_routes = []
    for i, (step_slug, _, component) in enumerate(step_slugs):
        path = "/" if i == 0 else f"/{step_slug}"
        app_routes.append(f'        <Route path="{path}" element={{<{component} />}} />')

    files["src/App.tsx"] = (
        "\n".join(app_imports)
        + "\n"
        + "import { AiosOverlay } from './lib/aios'\n"
        + "\n"
        + "export default function App() {\n"
        + "  return (\n"
        + "    <>\n"
        + "      <Routes>\n"
        + "        <Route element={<Layout />}>\n"
        + "\n".join(app_routes)
        + "\n"
        + "        </Route>\n"
        + "      </Routes>\n"
        + "      <AiosOverlay />\n"
        + "    </>\n"
        + "  )\n"
        + "}\n"
    )

    # ── src/index.css ─────────────────────────────────────────────────────
    files["src/index.css"] = (
        "@tailwind base;\n"
        "@tailwind components;\n"
        "@tailwind utilities;\n"
        "\n"
        ":root {\n"
        f"  --color-primary: {primary};\n"
        f"  --color-secondary: {secondary};\n"
        f"  --color-accent: {accent};\n"
        f"  --font-heading: '{font_heading}', system-ui, sans-serif;\n"
        f"  --font-body: '{font_body}', system-ui, sans-serif;\n"
        f"  --spacing-base: {spacing_val};\n"
        f"  --radius: {corners_val};\n"
        "}\n"
        "\n"
        "body {\n"
        "  font-family: var(--font-body);\n"
        "  @apply bg-white text-gray-900 antialiased;\n"
        "}\n"
        "\n"
        "h1, h2, h3, h4, h5, h6 {\n"
        "  font-family: var(--font-heading);\n"
        "}\n"
    )

    # ── src/components/Layout.tsx ──────────────────────────────────────────
    nav_links = []
    for i, (step_slug, title, _) in enumerate(step_slugs):
        path = "/" if i == 0 else f"/{step_slug}"
        link = f'<Link to="{path}" className="hover:text-primary">{title}</Link>'
        nav_links.append(f"          {link}")

    nav_block = "\n".join(nav_links) if nav_links else "          <span>App</span>"

    files["src/components/Layout.tsx"] = (
        "import { Link, Outlet } from 'react-router-dom'\n"
        "\n"
        "export default function Layout() {\n"
        "  return (\n"
        '    <div className="min-h-screen flex flex-col">\n'
        '      <nav className="border-b px-6 py-3 flex items-center gap-6'
        ' font-heading text-sm">\n'
        f"{nav_block}\n"
        "      </nav>\n"
        '      <main className="flex-1">\n'
        "        <Outlet />\n"
        "      </main>\n"
        "    </div>\n"
        "  )\n"
        "}\n"
    )

    # ── src/pages/{StepSlug}Page.tsx (one per solution flow step) ──────────
    for _, title, component in step_slugs:
        files[f"src/pages/{component}.tsx"] = (
            "import { Screen } from '../lib/aios'\n"
            "\n"
            f"export default function {component}() {{\n"
            f"  return (\n"
            f'    <Screen name="{title}">\n'
            f'      <div className="p-8">\n'
            f'        <h1 className="text-2xl font-heading font-bold mb-4">{title}</h1>\n'
            f'        <p className="text-gray-500">Implement this screen.</p>\n'
            f"      </div>\n"
            f"    </Screen>\n"
            f"  )\n"
            f"}}\n"
        )

    return files


# =============================================================================
# Slugify + Registry helpers
# =============================================================================


def _slugify(name: str) -> str:
    """Convert a feature name to a URL-safe slug.

    "Content Calendar" → "content-calendar"
    """
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "unnamed"


def _build_slug_map(
    features: list,
) -> dict[str, str]:
    """Build a feature-id → slug map, handling duplicate slugs with numeric suffixes."""
    slug_counts: dict[str, int] = {}
    id_to_slug: dict[str, str] = {}

    for f in features:
        base = _slugify(f.name)
        count = slug_counts.get(base, 0)
        if count == 0:
            slug = base
        else:
            slug = f"{base}-{count}"
        slug_counts[base] = count + 1
        id_to_slug[f.id] = slug

    return id_to_slug


def _render_registry_ts(features: list) -> str:
    """Render src/lib/aios/registry.ts from payload features."""
    slug_map = _build_slug_map(features)

    lines = [
        "// AUTO-GENERATED by AIOS — DO NOT MODIFY",
        "",
        "export interface FeatureEntry {",
        "  id: string",
        "  name: string",
        "  priority: string",
        "}",
        "",
        "export const FEATURE_REGISTRY: Record<string, FeatureEntry> = {",
    ]

    for f in features:
        slug = slug_map[f.id]
        # Escape single quotes in feature names
        safe_name = f.name.replace("'", "\\'")
        lines.append(
            f"  '{slug}': {{ id: '{f.id}', name: '{safe_name}', priority: '{f.priority}' }},"
        )

    lines.append("}")
    lines.append("")
    lines.append("export function resolveFeatureId(slugOrId: string): string {")
    lines.append("  if (slugOrId in FEATURE_REGISTRY) return FEATURE_REGISTRY[slugOrId].id")
    lines.append("  return slugOrId  // passthrough for raw UUIDs")
    lines.append("}")
    lines.append("")

    return "\n".join(lines)


# =============================================================================
# AIOS bridge component library templates
# =============================================================================

_AIOS_FEATURE_TSX = """\
import React from 'react'
import { resolveFeatureId, FEATURE_REGISTRY } from './registry'

interface FeatureProps {
  id: string
  name?: string
  as?: React.ElementType
  children: React.ReactNode
  className?: string
  [key: string]: any
}

/**
 * AIOS Feature wrapper — auto-adds data-feature-id + data-component.
 * Use feature SLUGS from registry.ts, not raw UUIDs.
 * DO NOT MODIFY — managed by AIOS.
 */
export function Feature({  // noqa: E501
  id, name, as: Component = 'div', children, className, ...rest
}: FeatureProps) {
  const featureId = resolveFeatureId(id)
  const entry = FEATURE_REGISTRY[id]
  const componentName = name || entry?.name || id
  return (
    <Component
      data-feature-id={featureId}
      data-component={componentName}
      className={className}
      {...rest}
    >
      {children}
    </Component>
  )
}

export default Feature
"""

_AIOS_SCREEN_TSX = """\
import React from 'react'

interface ScreenProps {
  name: string
  children: React.ReactNode
  className?: string
}

/**
 * AIOS Screen wrapper — auto-adds data-component for page-level tracking.
 * DO NOT MODIFY — managed by AIOS.
 */
export function Screen({ name, children, className }: ScreenProps) {
  return (
    <div data-component={name} className={className}>
      {children}
    </div>
  )
}

export default Screen
"""

_AIOS_USE_FEATURE_PROPS_TS = """\
import { resolveFeatureId, FEATURE_REGISTRY } from './registry'

/**
 * Hook that returns AIOS bridge props for spreading onto elements.
 * Use for third-party components that can't be wrapped with <Feature>.
 *
 * Usage: <SomeLibComponent {...useFeatureProps('content-calendar')} />
 *
 * DO NOT MODIFY — managed by AIOS.
 */
export function useFeatureProps(
  slugOrId: string,
  nameOverride?: string,
): { 'data-feature-id': string; 'data-component': string } {
  const featureId = resolveFeatureId(slugOrId)
  const entry = FEATURE_REGISTRY[slugOrId]
  const componentName = nameOverride || entry?.name || slugOrId
  return {
    'data-feature-id': featureId,
    'data-component': componentName,
  }
}

export default useFeatureProps
"""

_AIOS_TYPES_TS = """\
// AIOS Bridge message types — mirrors apps/workbench/types/prototype.ts
// DO NOT MODIFY — managed by AIOS.

// Events from bridge script (iframe → parent)
export interface AiosFeatureClickEvent {
  type: 'aios:feature-click'
  featureId: string
  componentName: string | null
  elementTag: string
  textContent: string
}

export interface AiosPageChangeEvent {
  type: 'aios:page-change'
  path: string
  visibleFeatures: string[]
}

export interface AiosHighlightReadyEvent {
  type: 'aios:highlight-ready'
  featureId: string
  rect: { top: number; left: number; width: number; height: number }
}

export interface AiosHighlightNotFoundEvent {
  type: 'aios:highlight-not-found'
  featureId: string
}

export interface AiosTourStepCompleteEvent {
  type: 'aios:tour-step-complete'
  featureId: string
}

export type AiosBridgeEvent =
  | AiosFeatureClickEvent
  | AiosPageChangeEvent
  | AiosHighlightReadyEvent
  | AiosHighlightNotFoundEvent
  | AiosTourStepCompleteEvent

// Commands from parent (parent → iframe)
export interface RadarFeature {
  featureId: string
  featureName: string
  componentName?: string
  keywords?: string[]
}

export interface AiosHighlightCommand {  // noqa: E501
  type: 'aios:highlight-feature'
  featureId: string
  featureName: string
  description: string
  stepLabel: string
  componentName?: string
  keywords?: string[]
}

export interface AiosTourStartCommand {
  type: 'aios:start-tour'
  steps: Array<{
    featureId: string
    featureName: string
    description: string
    stepLabel: string
    route: string | null
  }>
}

export interface AiosTourNavigateCommand {
  type: 'aios:tour-navigate'
  path?: string | null
  highlightAfter?: boolean
  featureId?: string
  featureName?: string
  description?: string
  stepLabel?: string
  componentName?: string
  keywords?: string[]
  features?: RadarFeature[]
}

export type AiosBridgeCommand =
  | AiosHighlightCommand
  | { type: 'aios:clear-highlights' }
  | { type: 'aios:navigate'; path: string }
  | { type: 'aios:show-radar'; features: RadarFeature[] }
  | { type: 'aios:clear-radar' }
  | AiosTourStartCommand
  | AiosTourNavigateCommand
  | { type: 'aios:next-step' }
  | { type: 'aios:prev-step' }
"""

_AIOS_OVERLAY_TSX = """\
import { useEffect } from 'react'

/**
 * AIOS Overlay — loads the bridge script for feature tracking.
 * Include this component in your root layout.
 * DO NOT MODIFY — managed by AIOS.
 */
export function AiosOverlay() {
  useEffect(() => {
    const script = document.createElement('script')
    script.src = '/aios-bridge.js'
    script.async = true
    document.body.appendChild(script)
    return () => {
      document.body.removeChild(script)
    }
  }, [])

  return null
}

export default AiosOverlay
"""

_AIOS_INDEX_TS = """\
// AIOS Bridge Library — barrel export
// DO NOT MODIFY — managed by AIOS.

export { Feature } from './Feature'
export { Screen } from './Screen'
export { useFeatureProps } from './useFeatureProps'
export { AiosOverlay } from './AiosOverlay'
export { FEATURE_REGISTRY, resolveFeatureId } from './registry'
export type { FeatureEntry } from './registry'
export type {
  AiosFeatureClickEvent,
  AiosPageChangeEvent,
  AiosHighlightReadyEvent,
  AiosHighlightNotFoundEvent,
  AiosTourStepCompleteEvent,
  AiosBridgeEvent,
  AiosHighlightCommand,
  AiosTourStartCommand,
  AiosTourNavigateCommand,
  RadarFeature,
  AiosBridgeCommand,
} from './types'
"""
