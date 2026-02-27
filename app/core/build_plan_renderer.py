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

export type AiosBridgeCommand =
  | AiosHighlightCommand
  | { type: 'aios:clear-highlights' }
  | { type: 'aios:navigate'; path: string }
  | { type: 'aios:show-radar'; features: RadarFeature[] }
  | { type: 'aios:clear-radar' }
  | AiosTourStartCommand
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
  RadarFeature,
  AiosBridgeCommand,
} from './types'
"""
