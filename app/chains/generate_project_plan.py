"""Generate a project plan for prototype building via Opus.

Follows the generate_solution_flow.py pattern:
- AsyncAnthropic with tool_use + cache_control + streaming
- Anthropic string bug guard
- Retry with exponential backoff
- log_llm_usage with cache stats
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any
from uuid import UUID, uuid4

from app.core.schemas_prototype_builder import (
    BuildPhase,
    BuildStream,
    BuildTask,
    OrchestrationConfig,
    ProjectPlan,
    PrototypePayload,
)

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2
_INITIAL_DELAY = 1.0
_MODEL = "claude-opus-4-6"

# Cost per 1K output tokens by model tier (for task-level estimates)
MODEL_COST_PER_1K: dict[str, float] = {
    "opus": 0.090,
    "sonnet": 0.018,
    "haiku": 0.0048,
}


# =============================================================================
# Tool schema — Opus submits the complete plan
# =============================================================================

PROJECT_PLAN_TOOL = {
    "name": "submit_project_plan",
    "description": (
        "Submit the complete project plan with phases, tasks, streams, and CLAUDE.md content."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "phases": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "phase_number": {"type": "integer"},
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                    },
                    "required": ["phase_number", "name"],
                },
            },
            "tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string"},
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "model": {
                            "type": "string",
                            "enum": ["opus", "sonnet", "haiku"],
                        },
                        "phase": {"type": "integer"},
                        "parallel_group": {"type": "string"},
                        "depends_on": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "acceptance_criteria": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "file_targets": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "estimated_tokens": {"type": "integer"},
                    },
                    "required": ["task_id", "name", "description", "model", "phase"],
                },
            },
            "streams": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "stream_id": {"type": "string"},
                        "name": {"type": "string"},
                        "model": {
                            "type": "string",
                            "enum": ["opus", "sonnet", "haiku"],
                        },
                        "task_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "branch_name": {"type": "string"},
                    },
                    "required": ["stream_id", "name", "model", "task_ids"],
                },
            },
            "completion_criteria": {
                "type": "array",
                "items": {"type": "string"},
            },
            "claude_md_content": {
                "type": "string",
                "description": "Full CLAUDE.md content for the prototype project",
            },
        },
        "required": ["phases", "tasks", "streams", "completion_criteria", "claude_md_content"],
    },
}


# =============================================================================
# System prompt — cached across calls
# =============================================================================

SYSTEM_PROMPT = """\
You are a senior software architect creating a build plan for an interactive prototype.

## Your Task

Given a project payload (features, personas, solution flow steps, design tokens, workflows), create:

1. **Phases** — sequential build phases (foundation → screens → integration → polish)
2. **Tasks** — specific build tasks with model assignment and dependencies
3. **Streams** — parallel execution streams for concurrent work
4. **CLAUDE.md** — a comprehensive project guide for Claude Code instances

## Principles

### Phase Design
- Phase 1: Screens (one task per screen/page — scaffold, routing, design system,
  and shared components are PRE-RENDERED and already in the repo)
- Phase 2: Integration (cross-page state, navigation, data flow)
- Phase 3: Polish (animations, responsive, final mock data)

### Pre-rendered Foundation
The following are already committed before your plan runs. Do NOT create tasks for
scaffold, routing, design tokens, or layout shell:
- package.json, vite.config.ts, tailwind.config.js, postcss.config.js, tsconfig*.json
- index.html, src/main.tsx, src/App.tsx, src/index.css
- src/components/Layout.tsx, src/pages/*Page.tsx (stubs with Screen wrapper)
- src/lib/aios/*, public/aios-bridge.js

Focus tasks on FEATURE IMPLEMENTATION within existing pages.

### Model Assignment (depth-aware)
Feature depth levels are shown in brackets: [depth: full], [depth: visual], [depth: placeholder].
- **sonnet**: Features with [depth: full] — interactive pages, state management, real UX
- **haiku**: Features with [depth: visual] or [depth: placeholder] — static UI, stubs, mock data
- **opus**: Do NOT assign — reserved for CLAUDE.md (handled externally)

### Stream Grouping by Depth
Group features by depth tier into separate streams:
- "full" streams (model: sonnet) for [depth: full] features
- "visual" stream (model: haiku) for [depth: visual] features
- "placeholder" stream (model: haiku) for [depth: placeholder] features
Split streams of the same tier for parallelism if needed.

### Task Dependencies
- Screen tasks can start immediately (scaffold is pre-rendered)
- Integration tasks depend on the screens they connect
- Polish tasks depend on integration

### Solution Flow → Screen Mapping
- Each solution flow step typically maps to one screen/page
- Steps with the same phase may share a screen (e.g., multiple entry steps → onboarding wizard)
- Collapse steps that logically belong on the same page

### Parallel Streams
- Group independent screens into parallel streams
- Each stream gets its own git branch for worktree execution
- Streams should be roughly equal in estimated work

### Token Estimation
- Simple component/page: 500-1500 tokens
- Complex interactive page: 1500-3000 tokens
- Mock data file: 200-500 tokens
- Configuration/setup: 200-500 tokens

## CLAUDE.md Requirements

The CLAUDE.md must include:
1. Project overview with company context and vision
2. Design tokens (colors, typography, spacing, corners)
3. Technology stack and conventions
4. AIOS Bridge Library usage — a pre-built `src/lib/aios/` library is provided with:
   - `<Feature id="slug">` wrapper (auto-adds data-feature-id + data-component)
   - `<Screen name="PageName">` wrapper (page-level data-component)
   - `useFeatureProps('slug')` hook (for third-party components)
   - Feature slugs are defined in `src/lib/aios/registry.ts` — use SLUGS, not UUIDs
   - `<AiosOverlay />` MUST be in the root layout
5. Files in `src/lib/aios/` and `public/aios-bridge.js` must NOT be modified
8. Persona-driven mock data guidelines
9. Page/route structure derived from solution flow

## Output Format

Submit a complete plan via the submit_project_plan tool. Ensure:
- Every task has a unique task_id (format: t-{phase}-{index})
- Dependencies reference valid task_ids
- Streams reference valid task_ids
- CLAUDE.md is comprehensive (2000-4000 tokens)
"""


# =============================================================================
# Context builder
# =============================================================================


def _build_context(payload: PrototypePayload, config: OrchestrationConfig) -> str:
    """Build the user prompt context from payload."""
    sections: list[str] = []

    # Project identity
    sections.append(f"# Project: {payload.project_name}")
    if payload.company_name:
        sections.append(f"Company: {payload.company_name} ({payload.company_industry})")
    if payload.project_vision:
        sections.append(f"Vision: {payload.project_vision[:500]}")

    # Configuration
    sections.append("\n## Build Configuration")
    sections.append(f"Scaffold: {config.scaffold_type}")
    sections.append(f"Design system: {config.design_system}")
    sections.append(f"Mock strategy: {config.mock_strategy}")
    sections.append(f"Max parallel streams: {config.max_parallel_streams}")
    sections.append(f"Budget cap: ${config.budget_cap_usd:.2f}")
    sections.append(f"Overlay enabled: {config.overlay_enabled}")

    # Design tokens
    if payload.design_contract:
        dc = payload.design_contract
        sections.append("\n## Design Tokens")
        sections.append(f"Primary: {dc.tokens.primary_color}")
        sections.append(f"Secondary: {dc.tokens.secondary_color}")
        sections.append(f"Accent: {dc.tokens.accent_color}")
        sections.append(f"Headings: {dc.tokens.font_heading}")
        sections.append(f"Body: {dc.tokens.font_body}")
        sections.append(f"Spacing: {dc.tokens.spacing}")
        sections.append(f"Corners: {dc.tokens.corners}")
        if dc.style_direction:
            sections.append(f"Style: {dc.style_direction}")

    # Personas
    if payload.personas:
        sections.append(f"\n## Personas ({len(payload.personas)})")
        for p in payload.personas:
            sections.append(f"- **{p.name}** ({p.role})")
            if p.goals:
                sections.append(f"  Goals: {', '.join(str(g) for g in p.goals[:5])}")
            if p.pain_points:
                sections.append(f"  Pains: {', '.join(str(pp) for pp in p.pain_points[:5])}")

    # Features
    if payload.features:
        sections.append(f"\n## Features ({len(payload.features)})")
        for pri in ("must_have", "should_have", "could_have", "unset"):
            group = [f for f in payload.features if f.priority == pri]
            if group:
                sections.append(f"\n### [{pri}]")
                for f in group:
                    overview = f" — {f.overview[:120]}" if f.overview else ""
                    depth_tag = f" [depth: {f.build_depth}]" if f.build_depth else ""
                    sections.append(f"- {f.name} (id: {f.id}){depth_tag}{overview}")

        depth_counts = {"full": 0, "visual": 0, "placeholder": 0}
        for f in payload.features:
            depth_counts[getattr(f, "build_depth", "visual")] += 1
        sections.append("\n## Depth Summary")
        sections.append(
            f"Full: {depth_counts['full']} | Visual: {depth_counts['visual']} "
            f"| Placeholder: {depth_counts['placeholder']}"
        )

    # Solution flow steps
    if payload.solution_flow_steps:
        sections.append(f"\n## Solution Flow ({len(payload.solution_flow_steps)} steps)")
        for s in payload.solution_flow_steps:
            sections.append(f"- [{s.phase}] {s.title} (id: {s.id})")
            if s.goal:
                sections.append(f"  Goal: {s.goal[:200]}")
            if s.how_it_works:
                sections.append(f"  How: {s.how_it_works[:200]}")

    # Workflows
    if payload.workflows:
        sections.append(f"\n## Workflows ({len(payload.workflows)})")
        for wf in payload.workflows:
            sections.append(f"- [{wf.state_type}] {wf.name}")
            for step in wf.steps[:5]:
                label = step.get("label", "?")
                sections.append(f"  → {label}")

    # Business drivers
    if payload.business_drivers:
        sections.append(f"\n## Business Drivers ({len(payload.business_drivers)})")
        for d in payload.business_drivers:
            sections.append(f"- [{d.driver_type}] {d.description[:150]}")

    # Constraints
    if payload.constraints:
        sections.append(f"\n## Constraints ({len(payload.constraints)})")
        for c in payload.constraints:
            sections.append(f"- [{c.constraint_type}] {c.name}: {c.description[:100]}")

    # Competitors
    if payload.competitors:
        sections.append(f"\n## Competitors ({len(payload.competitors)})")
        for cr in payload.competitors:
            sections.append(f"- {cr.name}: {cr.description[:100]}")

    return "\n".join(sections)


# =============================================================================
# Cost estimation
# =============================================================================


def _estimate_task_cost(task: BuildTask) -> float:
    """Estimate cost for a single task based on model and tokens."""
    rate = MODEL_COST_PER_1K.get(task.model, 0.018)
    return round(rate * (task.estimated_tokens / 1000), 4)


def _estimate_stream_duration(tasks: list[BuildTask]) -> int:
    """Rough duration estimate in minutes based on token count."""
    total_tokens = sum(t.estimated_tokens for t in tasks)
    # ~2K tokens/minute for code gen
    return max(1, round(total_tokens / 2000))


# =============================================================================
# Main generation function
# =============================================================================


async def generate_project_plan(
    payload: PrototypePayload,
    config: OrchestrationConfig | None = None,
    project_id: UUID | None = None,
) -> ProjectPlan:
    """Generate a project plan using Opus with tool_use.

    Follows generate_solution_flow.py pattern exactly:
    - AsyncAnthropic + tool_use + cache_control + streaming
    - Anthropic string bug guard
    - Retry with exponential backoff
    - log_llm_usage with cache stats
    """
    from anthropic import (
        APIConnectionError,
        APITimeoutError,
        AsyncAnthropic,
        InternalServerError,
        RateLimitError,
    )

    from app.core.config import Settings

    if config is None:
        config = OrchestrationConfig()

    settings = Settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    context = _build_context(payload, config)

    user_prompt = (
        f"Create a build plan for this prototype project.\n\n{context}\n\n"
        f"Generate a plan with up to {config.max_parallel_streams} parallel streams "
        f"and stay within a ${config.budget_cap_usd:.2f} budget cap."
    )

    system_blocks = [
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        },
    ]

    for attempt in range(_MAX_RETRIES + 1):
        try:
            t0 = time.monotonic()
            async with client.messages.stream(
                model=_MODEL,
                max_tokens=16000,
                system=system_blocks,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=0,
                tools=[PROJECT_PLAN_TOOL],
                tool_choice={"type": "tool", "name": "submit_project_plan"},
            ) as stream:
                response = await stream.get_final_message()
            elapsed_ms = int((time.monotonic() - t0) * 1000)

            # Extract tool result
            for block in response.content:
                if block.type == "tool_use" and block.name == "submit_project_plan":
                    result = block.input

                    # Anthropic string bug guard
                    for key in ("phases", "tasks", "streams", "completion_criteria"):
                        val = result.get(key, [])
                        if isinstance(val, str):
                            try:
                                result[key] = json.loads(val)
                            except (json.JSONDecodeError, TypeError):
                                logger.warning(f"{key} returned as unparseable string")
                                result[key] = []

                    # Build plan models
                    tasks = []
                    for t in result.get("tasks", []):
                        if not isinstance(t, dict):
                            continue
                        bt = BuildTask(
                            task_id=t.get("task_id", f"t-{len(tasks)}"),
                            name=t.get("name", ""),
                            description=t.get("description", ""),
                            model=t.get("model", "sonnet"),
                            phase=t.get("phase", 1),
                            parallel_group=t.get("parallel_group", ""),
                            depends_on=t.get("depends_on", []) or [],
                            estimated_tokens=t.get("estimated_tokens", 1000),
                            acceptance_criteria=t.get("acceptance_criteria", []) or [],
                            file_targets=t.get("file_targets", []) or [],
                        )
                        bt.estimated_cost_usd = _estimate_task_cost(bt)
                        tasks.append(bt)

                    phases = []
                    for i, p in enumerate(result.get("phases", [])):
                        if not isinstance(p, dict):
                            continue
                        pnum = p.get("phase_number", i + 1)
                        phases.append(
                            BuildPhase(
                                phase_number=pnum,
                                name=p.get("name", ""),
                                description=p.get("description", ""),
                                task_ids=[t.task_id for t in tasks if t.phase == pnum],
                            )
                        )

                    streams = []
                    for s in result.get("streams", []):
                        if not isinstance(s, dict):
                            continue
                        task_ids = s.get("task_ids", []) or []
                        stream_tasks = [t for t in tasks if t.task_id in task_ids]
                        bs = BuildStream(
                            stream_id=s.get("stream_id", f"s-{len(streams)}"),
                            name=s.get("name", ""),
                            model=s.get("model", "sonnet"),
                            tasks=task_ids,
                            branch_name=s.get("branch_name", f"stream-{len(streams) + 1}"),
                            estimated_duration_minutes=_estimate_stream_duration(stream_tasks),
                        )
                        streams.append(bs)

                    total_cost = round(sum(t.estimated_cost_usd for t in tasks), 2)
                    total_minutes = max((s.estimated_duration_minutes for s in streams), default=0)

                    plan = ProjectPlan(
                        plan_id=str(uuid4()),
                        project_id=payload.project_id,
                        payload_hash=payload.payload_hash,
                        tasks=tasks,
                        streams=streams,
                        phases=phases,
                        total_estimated_cost_usd=total_cost,
                        total_estimated_minutes=total_minutes,
                        completion_criteria=result.get("completion_criteria", []) or [],
                        claude_md_content=result.get("claude_md_content", ""),
                        created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    )

                    # Log usage
                    cache_read = getattr(response.usage, "cache_read_input_tokens", 0) or 0
                    cache_create = getattr(response.usage, "cache_creation_input_tokens", 0) or 0
                    logger.info(
                        f"Generated plan: {len(tasks)} tasks, {len(streams)} streams, "
                        f"${total_cost:.2f} est. cost in {elapsed_ms}ms "
                        f"(in={response.usage.input_tokens}, out={response.usage.output_tokens}, "
                        f"cache_read={cache_read}, cache_create={cache_create})"
                    )

                    try:
                        _log_usage(project_id, response, elapsed_ms)
                    except Exception:
                        pass

                    return plan

            logger.warning(f"No tool_use block in response (stop_reason={response.stop_reason})")
            return ProjectPlan(
                plan_id=str(uuid4()),
                project_id=payload.project_id,
                payload_hash=payload.payload_hash,
            )

        except (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError) as e:
            if attempt < _MAX_RETRIES:
                delay = _INITIAL_DELAY * (2**attempt)
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retry in {delay}s")
                await asyncio.sleep(delay)
            else:
                logger.error(f"All attempts failed: {e}")

    return ProjectPlan(
        plan_id=str(uuid4()),
        project_id=payload.project_id,
        payload_hash=payload.payload_hash,
    )


def _log_usage(
    project_id: UUID | None,
    response: Any,
    elapsed_ms: int,
) -> None:
    """Log LLM usage via centralized logger."""
    from app.core.llm_usage import log_llm_usage

    usage = response.usage
    log_llm_usage(
        workflow="prototype_builder",
        chain="generate_project_plan",
        model=_MODEL,
        provider="anthropic",
        tokens_input=usage.input_tokens,
        tokens_output=usage.output_tokens,
        tokens_cache_read=getattr(usage, "cache_read_input_tokens", 0) or 0,
        tokens_cache_create=getattr(usage, "cache_creation_input_tokens", 0) or 0,
        duration_ms=elapsed_ms,
        project_id=project_id,
    )
