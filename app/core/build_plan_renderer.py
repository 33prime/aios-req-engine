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
                "qrcode.react": "^4.2.0",
                "lucide-react": "^0.468.0",
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
        "  @apply bg-gray-50 text-gray-900 antialiased;\n"
        "}\n"
        "\n"
        "h1, h2, h3, h4, h5, h6 {\n"
        "  font-family: var(--font-heading);\n"
        "}\n"
        "\n"
        ".glass-card {\n"
        "  @apply bg-white/80 backdrop-blur-sm border border-white/60 shadow-lg;\n"
        "}\n"
        "\n"
        ".gradient-hero {\n"
        f"  background: linear-gradient(135deg, {primary} 0%, {secondary} 100%);\n"
        "}\n"
        "\n"
        ".gradient-accent {\n"
        f"  background: linear-gradient(135deg, {accent} 0%, {primary} 100%);\n"
        "}\n"
        "\n"
        ".stat-card {\n"
        "  @apply bg-white rounded-xl shadow-md border border-gray-100 p-6"
        " hover:shadow-lg transition-shadow;\n"
        "}\n"
    )

    # ── src/components/Layout.tsx ──────────────────────────────────────────
    nav_links = []
    for i, (step_slug, title, _) in enumerate(step_slugs):
        path = "/" if i == 0 else f"/{step_slug}"
        safe_nav_title = _escape_jsx(title[:24])
        nav_links.append(
            f'        <Link to="{path}" className={{'
            f'pathname === "{path}"'
            f' ? "bg-primary/10 text-primary font-semibold px-3 py-1.5 rounded-full text-sm"'
            f' : "text-gray-500 hover:text-primary px-3 py-1.5 text-sm"'
            f"}}>{safe_nav_title}</Link>"
        )

    nav_active_block = "\n".join(nav_links) if nav_links else "        <span>App</span>"

    project_title = _escape_jsx(payload.project_name or "Prototype")
    files["src/components/Layout.tsx"] = (
        "import { Link, Outlet, useLocation } from 'react-router-dom'\n"
        "\n"
        "export default function Layout() {\n"
        "  const { pathname } = useLocation()\n"
        "  return (\n"
        '    <div className="min-h-screen flex flex-col bg-gray-50">\n'
        '      <nav className="bg-white/90 backdrop-blur-md border-b'
        " border-gray-200/60 sticky top-0 z-50"
        ' px-6 py-3 flex items-center gap-1">\n'
        f'        <span className="font-heading font-bold text-primary'
        f' text-lg mr-6">{project_title}</span>\n'
        f"{nav_active_block}\n"
        "      </nav>\n"
        '      <main className="flex-1">\n'
        "        <Outlet />\n"
        "      </main>\n"
        '      <footer className="border-t border-gray-200/60 bg-white/60'
        ' backdrop-blur-sm py-6 px-8 text-center">\n'
        '        <p className="text-xs text-gray-400">'
        f"&copy; 2026 {project_title}. All rights reserved.</p>\n"
        "      </footer>\n"
        "    </div>\n"
        "  )\n"
        "}\n"
    )

    # ── src/components/ShareCard.tsx ─────────────────────────────────────
    files["src/components/ShareCard.tsx"] = (
        "import { QRCodeSVG } from 'qrcode.react'\n"
        "\n"
        "interface ShareCardProps {\n"
        "  title?: string\n"
        "  description?: string\n"
        "}\n"
        "\n"
        "export function ShareCard({ title, description }: ShareCardProps) {\n"
        "  const url = typeof window !== 'undefined' ? window.location.href : ''\n"
        "  return (\n"
        '    <div className="glass-card rounded-2xl p-8 text-center max-w-sm mx-auto">\n'
        '      <div className="bg-white rounded-xl p-4 inline-block shadow-sm mb-4">\n'
        "        <QRCodeSVG\n"
        "          value={url}\n"
        "          size={160}\n"
        f'          fgColor="{primary}"\n'
        '          level="M"\n'
        "        />\n"
        "      </div>\n"
        "      {title && (\n"
        '        <h3 className="font-heading font-semibold text-gray-900 mb-1">'
        "{title}</h3>\n"
        "      )}\n"
        "      {description && (\n"
        '        <p className="text-sm text-gray-500">{description}</p>\n'
        "      )}\n"
        '      <p className="text-xs text-gray-400 mt-3 break-all">{url}</p>\n'
        "    </div>\n"
        "  )\n"
        "}\n"
    )

    # ── Feature-to-page distribution (round-robin by step_order) ────────
    sorted_features = sorted(
        payload.features,
        key=lambda f: {"must_have": 0, "should_have": 1, "could_have": 2}.get(f.priority, 3),
    )
    features_per_step: dict[int, list] = {i: [] for i in range(len(steps))}
    for i, feat in enumerate(sorted_features):
        if steps:
            features_per_step[i % len(steps)].append(feat)

    # ── src/pages/{StepSlug}Page.tsx (one per solution flow step) ──────────
    for step_idx, (_, title, component) in enumerate(step_slugs):
        step = steps[step_idx] if step_idx < len(steps) else None
        assigned_features = features_per_step.get(step_idx, [])
        files[f"src/pages/{component}.tsx"] = _render_rich_page(
            step=step,
            title=title,
            component_name=component,
            assigned_features=assigned_features,
            personas=payload.personas[:3],
            design_contract=payload.design_contract,
            step_index=step_idx,
            total_steps=len(steps),
        )

    return files


# =============================================================================
# Rich page rendering — phase-based layout templates
# =============================================================================


def _render_rich_page(
    step,
    title: str,
    component_name: str,
    assigned_features: list,
    personas: list,
    design_contract,
    step_index: int,
    total_steps: int,
) -> str:
    """Render a complete TSX page with phase-appropriate layout and real content."""
    phase = step.phase if step else "core_experience"
    goal = _escape_jsx(step.goal) if step and step.goal else ""
    how_it_works = _escape_jsx(step.how_it_works) if step and step.how_it_works else ""
    success_criteria = step.success_criteria if step else []
    safe_title = _escape_jsx(title)

    # Build feature cards JSX
    feature_cards = _render_feature_cards(assigned_features)

    # Build success metrics JSX
    metrics_block = _render_metrics(success_criteria)

    # Build persona greeting (for entry pages)
    persona_greeting = ""
    if personas:
        p = personas[0]
        persona_greeting = _escape_jsx(f"Welcome, {p.name}. {p.role}.")

    # Progress indicator
    progress = _render_progress_bar(step_index, total_steps)

    # Select layout by phase
    renderer = _PHASE_RENDERERS.get(phase, _render_core_experience_page)
    body = renderer(
        safe_title=safe_title,
        goal=goal,
        how_it_works=how_it_works,
        feature_cards=feature_cards,
        metrics_block=metrics_block,
        persona_greeting=persona_greeting,
        progress=progress,
        success_criteria=success_criteria,
        assigned_features=assigned_features,
    )

    # Entry pages get QR + ShareCard import
    extra_import = ""
    share_block = ""
    if phase == "entry":
        extra_import = "import { ShareCard } from '../components/ShareCard'\n"
        share_block = (
            '      <div className="py-12 px-6">\n'
            "        <ShareCard\n"
            '          title="Scan to Share"\n'
            '          description="Share this experience on mobile"\n'
            "        />\n"
            "      </div>\n"
        )

    return (
        "import { Screen, Feature } from '../lib/aios'\n"
        f"{extra_import}"
        "\n"
        f"export default function {component_name}() {{\n"
        f"  return (\n"
        f'    <Screen name="{safe_title}">\n'
        f"{body}"
        f"{share_block}"
        f"    </Screen>\n"
        f"  )\n"
        f"}}\n"
    )


def _render_entry_page(
    safe_title: str,
    goal: str,
    how_it_works: str,
    feature_cards: str,
    metrics_block: str,
    persona_greeting: str,
    progress: str,
    **_,
) -> str:
    """Centered hero with gradient, CTA, and onboarding form."""
    return (
        # Gradient hero section
        '      <div className="gradient-hero text-white">\n'
        '        <div className="max-w-4xl mx-auto px-6 py-20 text-center">\n'
        + (
            f'          <p className="text-sm font-medium text-white/70'
            f' uppercase tracking-wider mb-4">{persona_greeting}</p>\n'
            if persona_greeting
            else ""
        )
        + f'          <h1 className="text-5xl font-heading font-bold mb-6'
        f' leading-tight">{safe_title}</h1>\n'
        + (
            f'          <p className="text-xl text-white/90'
            f' max-w-2xl mx-auto mb-10 leading-relaxed">{goal}</p>\n'
            if goal
            else ""
        )
        + '          <div className="flex items-center justify-center gap-4">\n'
        '            <button className="bg-white text-primary px-8 py-3.5'
        " rounded-full font-heading font-semibold shadow-lg"
        ' hover:shadow-xl hover:scale-105 transition-all">Get Started</button>\n'
        '            <button className="border-2 border-white/40 text-white px-8 py-3.5'
        " rounded-full font-heading font-medium"
        ' hover:bg-white/10 transition-all">Learn More</button>\n'
        "          </div>\n"
        "        </div>\n"
        "      </div>\n"
        # How it works section
        + (
            '      <div className="max-w-4xl mx-auto px-6 py-12">\n'
            '        <div className="glass-card rounded-2xl p-8 -mt-10 relative z-10">\n'
            '          <h2 className="font-heading font-semibold text-lg'
            ' text-primary mb-3">How It Works</h2>\n'
            f'          <p className="text-gray-700 leading-relaxed">'
            f"{how_it_works[:400]}</p>\n"
            "        </div>\n"
            "      </div>\n"
            if how_it_works
            else ""
        )
        # Quick survey / onboarding questions
        + '      <div className="max-w-2xl mx-auto px-6 py-8">\n'
        '        <h2 className="font-heading font-semibold text-xl text-center'
        ' mb-6">Tell Us About Your Needs</h2>\n'
        '        <div className="space-y-4">\n'
        '          <div className="glass-card rounded-xl p-5">\n'
        '            <label className="block text-sm font-medium'
        ' text-gray-700 mb-2">What best describes your role?</label>\n'
        '            <div className="grid grid-cols-2 gap-2">\n'
        '              <button className="border-2 border-gray-200'
        " rounded-lg px-4 py-3 text-sm hover:border-primary"
        ' hover:bg-primary/5 transition-all text-left">'
        "Executive / Decision Maker</button>\n"
        '              <button className="border-2 border-gray-200'
        " rounded-lg px-4 py-3 text-sm hover:border-primary"
        ' hover:bg-primary/5 transition-all text-left">'
        "Operations / Manager</button>\n"
        '              <button className="border-2 border-gray-200'
        " rounded-lg px-4 py-3 text-sm hover:border-primary"
        ' hover:bg-primary/5 transition-all text-left">'
        "Technical / Developer</button>\n"
        '              <button className="border-2 border-gray-200'
        " rounded-lg px-4 py-3 text-sm hover:border-primary"
        ' hover:bg-primary/5 transition-all text-left">'
        "End User / Consumer</button>\n"
        "            </div>\n"
        "          </div>\n"
        '          <div className="glass-card rounded-xl p-5">\n'
        '            <label className="block text-sm font-medium'
        ' text-gray-700 mb-2">What is your primary goal?</label>\n'
        '            <textarea className="w-full border-2 border-gray-200'
        " rounded-lg px-4 py-3 text-sm resize-none focus:border-primary"
        ' focus:ring-2 focus:ring-primary/20 outline-none transition-all"'
        ' rows={3} placeholder="Describe what you hope to achieve..." />\n'
        "          </div>\n"
        '          <button className="w-full bg-primary text-white py-3.5'
        " rounded-xl font-heading font-semibold shadow-md"
        ' hover:shadow-lg hover:brightness-110 transition-all">'
        "Continue</button>\n"
        "        </div>\n"
        "      </div>\n" + f"{progress}" + f"{feature_cards}"
    )


def _render_core_experience_page(
    safe_title: str,
    goal: str,
    how_it_works: str,
    feature_cards: str,
    metrics_block: str,
    progress: str,
    **_,
) -> str:
    """Full-width card grid with colored accents — for core experience pages."""
    return (
        '      <div className="max-w-6xl mx-auto px-6 py-10">\n'
        f"{progress}"
        # Page header with accent bar
        '        <div className="flex items-start gap-4 mb-8">\n'
        '          <div className="w-1.5 h-12 rounded-full bg-primary flex-shrink-0 mt-1">'
        "</div>\n"
        "          <div>\n"
        f'            <h1 className="text-3xl font-heading font-bold'
        f' text-gray-900">{safe_title}</h1>\n'
        + (f'            <p className="text-gray-500 mt-1">{goal}</p>\n' if goal else "")
        + "          </div>\n"
        "        </div>\n"
        # Narrative in a colored card
        + (
            '        <div className="bg-gradient-to-r from-primary/5 to-accent/5'
            ' rounded-2xl p-8 mb-10 border border-primary/10">\n'
            '          <div className="flex items-center gap-2 mb-3">\n'
            '            <span className="w-8 h-8 rounded-full bg-primary/10'
            ' flex items-center justify-center text-primary text-sm">'
            "&#9733;</span>\n"
            '            <h2 className="font-heading font-semibold'
            ' text-gray-800">Overview</h2>\n'
            "          </div>\n"
            f'          <p className="text-gray-700 leading-relaxed">'
            f"{how_it_works[:500]}</p>\n"
            "        </div>\n"
            if how_it_works
            else ""
        )
        + f"{feature_cards}"
        + f"{metrics_block}"
        + "      </div>\n"
    )


def _render_output_page(
    safe_title: str,
    goal: str,
    how_it_works: str,
    feature_cards: str,
    metrics_block: str,
    progress: str,
    success_criteria: list[str],
    **_,
) -> str:
    """Dashboard/results layout with colored stat cards."""
    # Build metric summary cards with color variety
    stat_cards = ""
    sample_values = ["87%", "24", "3.2x", "$12K", "92%", "156", "4.8", "98%"]
    card_styles = [
        ("bg-primary/10", "text-primary"),
        ("bg-accent/10", "text-accent"),
        ("bg-secondary/10", "text-secondary"),
        ("bg-green-50", "text-green-600"),
    ]
    for i, criterion in enumerate(success_criteria[:4]):
        val = sample_values[i % len(sample_values)]
        safe_crit = _escape_jsx(criterion[:60])
        bg_cls, txt_cls = card_styles[i % len(card_styles)]
        stat_cards += (
            f'          <div className="stat-card">\n'
            f'            <div className="w-10 h-10 rounded-xl {bg_cls}'
            f' flex items-center justify-center mb-3">\n'
            f'              <span className="{txt_cls} font-bold text-lg">'
            f"{val[:2]}</span>\n"
            "            </div>\n"
            f'            <p className="text-3xl font-heading font-bold'
            f' {txt_cls}">{val}</p>\n'
            f'            <p className="text-sm text-gray-500 mt-1">{safe_crit}</p>\n'
            f"          </div>\n"
        )

    return (
        '      <div className="max-w-6xl mx-auto px-6 py-10">\n'
        f"{progress}"
        # Header
        f'        <h1 className="text-3xl font-heading font-bold'
        f' text-gray-900 mb-1">{safe_title}</h1>\n'
        + (f'        <p className="text-gray-500 mb-8">{goal}</p>\n' if goal else "")
        # Stat cards grid
        + (
            '        <div className="grid grid-cols-2 lg:grid-cols-4 gap-5 mb-10">\n'
            f"{stat_cards}"
            "        </div>\n"
            if stat_cards
            else ""
        )
        # Results summary in accent card
        + (
            '        <div className="bg-white rounded-2xl shadow-md border'
            ' border-gray-100 p-8 mb-10">\n'
            '          <div className="flex items-center gap-3 mb-4">\n'
            '            <div className="w-10 h-10 rounded-xl gradient-accent'
            ' flex items-center justify-center">\n'
            '              <span className="text-white font-bold">&#9776;</span>\n'
            "            </div>\n"
            '            <h2 className="font-heading font-semibold text-lg'
            '">Results Summary</h2>\n'
            "          </div>\n"
            f'          <p className="text-gray-700 leading-relaxed">'
            f"{how_it_works[:400]}</p>\n"
            "        </div>\n"
            if how_it_works
            else ""
        )
        + f"{feature_cards}"
        + "      </div>\n"
    )


def _render_admin_page(
    safe_title: str,
    goal: str,
    feature_cards: str,
    metrics_block: str,
    progress: str,
    assigned_features: list,
    **_,
) -> str:
    """Data table / analytics layout with polished styling."""
    # Generate mock table rows from features
    table_rows = ""
    statuses = ["Active", "Pending", "In Review", "Completed", "Draft"]
    dates = ["Mar 1", "Feb 28", "Feb 27", "Feb 25", "Feb 22"]
    badge_styles = {
        "Active": "bg-green-100 text-green-700",
        "Pending": "bg-amber-100 text-amber-700",
        "In Review": "bg-primary/10 text-primary",
        "Completed": "bg-blue-100 text-blue-700",
        "Draft": "bg-gray-100 text-gray-600",
    }
    for i, feat in enumerate(assigned_features[:6]):
        safe_name = _escape_jsx(feat.name)
        status = statuses[i % len(statuses)]
        date = dates[i % len(dates)]
        badge_cls = badge_styles.get(status, "bg-gray-100 text-gray-600")
        prio_display = feat.priority.replace("_", " ").title()
        table_rows += (
            '              <tr className="border-b border-gray-100'
            ' hover:bg-gray-50/50 transition-colors">\n'
            f'                <td className="py-4 px-5 font-medium">{safe_name}</td>\n'
            f'                <td className="py-4 px-5">'
            f'<span className="{badge_cls}'
            f' text-xs font-medium px-2.5 py-1 rounded-full">'
            f"{status}</span></td>\n"
            f'                <td className="py-4 px-5 text-gray-500">{date}</td>\n'
            f'                <td className="py-4 px-5 text-gray-500">{prio_display}</td>\n'
            f"              </tr>\n"
        )

    if not table_rows:
        table_rows = (
            '              <tr><td colSpan={4} className="py-12 text-center'
            ' text-gray-400">No data yet</td></tr>\n'
        )

    return (
        '      <div className="max-w-6xl mx-auto px-6 py-10">\n'
        f"{progress}"
        f'        <h1 className="text-3xl font-heading font-bold'
        f' text-gray-900 mb-1">{safe_title}</h1>\n'
        + (f'        <p className="text-gray-500 mb-8">{goal}</p>\n' if goal else "")
        # Top action bar
        + '        <div className="flex items-center gap-3 mb-6">\n'
        "          <input"
        ' type="text" placeholder="Search..."'
        ' className="border-2 border-gray-200 rounded-xl px-4 py-2.5 text-sm'
        " flex-1 max-w-xs focus:border-primary focus:ring-2"
        ' focus:ring-primary/20 outline-none transition-all" />\n'
        '          <select className="border-2 border-gray-200 rounded-xl'
        ' px-4 py-2.5 text-sm text-gray-600">\n'
        "            <option>All Statuses</option>\n"
        "            <option>Active</option>\n"
        "            <option>Pending</option>\n"
        "          </select>\n"
        '          <button className="bg-primary text-white px-5 py-2.5'
        " rounded-xl text-sm font-semibold shadow-md"
        ' hover:shadow-lg hover:brightness-110 transition-all"'
        ">Export</button>\n"
        "        </div>\n"
        # Table in card
        '        <div className="bg-white rounded-2xl shadow-md border'
        ' border-gray-100 overflow-hidden mb-10">\n'
        '          <table className="w-full text-left text-sm">\n'
        "            <thead>\n"
        '              <tr className="bg-gray-50/80 border-b border-gray-100">\n'
        '                <th className="py-3.5 px-5 font-semibold text-gray-600'
        ' text-xs uppercase tracking-wider">Name</th>\n'
        '                <th className="py-3.5 px-5 font-semibold text-gray-600'
        ' text-xs uppercase tracking-wider">Status</th>\n'
        '                <th className="py-3.5 px-5 font-semibold text-gray-600'
        ' text-xs uppercase tracking-wider">Date</th>\n'
        '                <th className="py-3.5 px-5 font-semibold text-gray-600'
        ' text-xs uppercase tracking-wider">Priority</th>\n'
        "              </tr>\n"
        "            </thead>\n"
        "            <tbody>\n"
        f"{table_rows}"
        "            </tbody>\n"
        "          </table>\n"
        "        </div>\n" + f"{feature_cards}" + "      </div>\n"
    )


# Phase → renderer dispatch
_PHASE_RENDERERS = {
    "entry": _render_entry_page,
    "core_experience": _render_core_experience_page,
    "output": _render_output_page,
    "admin": _render_admin_page,
}


def _render_feature_cards(features: list) -> str:
    """Render a grid of Feature-wrapped cards with colored accents."""
    if not features:
        return ""
    # Rotating accent colors for visual variety
    accent_borders = [
        "border-l-primary",
        "border-l-accent",
        "border-l-secondary",
        "border-l-green-500",
        "border-l-purple-500",
        "border-l-rose-500",
    ]
    priority_badge = {
        "must_have": "bg-red-50 text-red-600 ring-1 ring-red-200",
        "should_have": "bg-amber-50 text-amber-600 ring-1 ring-amber-200",
        "could_have": "bg-blue-50 text-blue-600 ring-1 ring-blue-200",
    }
    cards = ""
    for i, feat in enumerate(features[:6]):
        slug = _slugify(feat.name)
        safe_name = _escape_jsx(feat.name)
        overview = _escape_jsx(feat.overview[:120]) if feat.overview else ""
        border_cls = accent_borders[i % len(accent_borders)]
        badge_cls = priority_badge.get(
            feat.priority, "bg-gray-50 text-gray-600 ring-1 ring-gray-200"
        )
        prio_label = feat.priority.replace("_", " ")
        cards += (
            f'          <Feature id="{slug}">\n'
            f'            <div className="bg-white rounded-xl border-l-4 {border_cls}'
            f' shadow-sm hover:shadow-lg transition-all p-5">\n'
            f'              <div className="flex items-center justify-between mb-3">\n'
            f'                <h3 className="font-heading font-semibold'
            f' text-gray-900">{safe_name}</h3>\n'
            f'                <span className="{badge_cls}'
            f' text-xs font-medium px-2.5 py-0.5 rounded-full">'
            f"{prio_label}</span>\n"
            f"              </div>\n"
            + (
                f'              <p className="text-sm text-gray-600 leading-relaxed">'
                f"{overview}</p>\n"
                if overview
                else ""
            )
            + "            </div>\n"
            "          </Feature>\n"
        )
    return (
        '        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5 mt-10">\n'
        f"{cards}"
        "        </div>\n"
    )


def _render_metrics(criteria: list[str]) -> str:
    """Render success criteria as visual checklist cards with colored checks."""
    if not criteria:
        return ""
    items = ""
    for c in criteria[:5]:
        safe = _escape_jsx(c[:100])
        items += (
            '          <div className="flex items-start gap-3 p-4 bg-white'
            " rounded-xl border border-gray-100 shadow-sm"
            ' hover:border-primary/30 transition-colors">\n'
            '            <span className="w-6 h-6 rounded-full bg-primary/10'
            " text-primary flex items-center justify-center"
            ' flex-shrink-0 mt-0.5 text-sm font-bold">&#10003;</span>\n'
            f'            <span className="text-sm text-gray-700 leading-relaxed">'
            f"{safe}</span>\n"
            "          </div>\n"
        )
    return (
        '        <div className="mt-10">\n'
        '          <h2 className="font-heading font-semibold text-lg mb-4">'
        "Success Criteria</h2>\n"
        '          <div className="space-y-3">\n'
        f"{items}"
        "          </div>\n"
        "        </div>\n"
    )


def _render_progress_bar(current: int, total: int) -> str:
    """Render a step progress indicator with colored dots."""
    if total <= 1:
        return ""
    dots = ""
    for i in range(total):
        if i < current:
            cls = "bg-primary"
        elif i == current:
            cls = "bg-primary shadow-md shadow-primary/30"
        else:
            cls = "bg-gray-200"
        dots += f'            <div className="h-2 flex-1 rounded-full {cls}"></div>\n'
    return (
        '        <div className="mb-8">\n'
        f'          <p className="text-xs font-medium text-gray-400'
        f' uppercase tracking-wider mb-2">Step {current + 1} of {total}</p>\n'
        '          <div className="flex gap-1.5">\n'
        f"{dots}"
        f"          </div>\n"
        f"        </div>\n"
    )


def _escape_jsx(text: str) -> str:
    """Escape special characters for safe JSX rendering."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("{", "&#123;")
        .replace("}", "&#125;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


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
