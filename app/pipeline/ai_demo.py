"""AI Result Panel Builders — 1 parallel Haiku call per AI agent in the solution flow.

Each builder receives:
  1. The design quality reference (cached)
  2. The agent's ai_config + step context
  3. Component library reference

Outputs a self-contained TSX panel component per AI agent showing completed results.
Prompt caching: system prompt + design ref are shared across all calls.
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.schemas_prototype_builder import PrototypePayload

logger = logging.getLogger(__name__)

# Load shared design quality reference
_DESIGN_REF = (Path(__file__).parent / "references" / "design_quality.md").read_text()

# =============================================================================
# Tool schema — single AI result panel output
# =============================================================================

AI_DEMO_TOOL = {
    "name": "submit_ai_panel",
    "description": "Submit the completed AI result panel TSX file.",
    "input_schema": {
        "type": "object",
        "required": ["agent_slug", "component_name", "tsx"],
        "properties": {
            "agent_slug": {
                "type": "string",
                "description": "Kebab-case agent identifier (e.g. 'market-sizer')",
            },
            "component_name": {
                "type": "string",
                "description": "PascalCase component name (e.g. 'MarketSizerPanel')",
            },
            "tsx": {
                "type": "string",
                "description": "Complete TSX source code for the AI result panel component",
            },
        },
    },
}

# =============================================================================
# System prompt
# =============================================================================

AI_DEMO_SYSTEM_PROMPT = f"""\
{_DESIGN_REF}

---

You are a senior React+TypeScript developer building AI result panel components.

Each panel is an INLINE component that shows the AI agent's COMPLETED output — as if \
the agent already did its work. The panel is rendered directly on the page, NOT in a modal.
Max 80 lines TSX.

## Available Imports

```tsx
import {{ useState }} from 'react'
import {{ Card, Badge, Button, LucideIcon, ProgressBar }} from '@/components/ui'
```

## WHAT TO SHOW (the AI's finished results)

### 1. Data the AI Processed (3-5 items)
Show results as a compact list or mini-table with confidence scores:
- Item name + AI assessment in one line
- Confidence shown as a subtle Badge (success for high, warning for medium)
- Use realistic domain-specific data

### 2. Classifications or Decisions (2-3 items)
Show what the AI decided, with brief rationale:
- Decision label + one-line reason
- Color-coded by confidence: high=success, medium=warning

### 3. Recommendations (1-2 items)
A brief AI recommendation banner:
```tsx
<div className="bg-primary/5 border border-primary/10 rounded-lg p-3 flex items-start gap-3">
  <LucideIcon name="Sparkles" size={{16}} className="text-primary mt-0.5 shrink-0" />
  <div>
    <p className="text-sm font-medium text-gray-900">Recommendation headline</p>
    <p className="text-xs text-gray-500 mt-0.5">Brief rationale</p>
  </div>
</div>
```

### 4. Subtle Agent Attribution (always include)
```tsx
<div className="flex items-center gap-2 text-xs text-gray-400 mt-4">
  <LucideIcon name="Zap" size={{12}} />
  <span>Analyzed by {{agentName}}</span>
</div>
```

## WHAT NOT TO SHOW

- NO processing visualizations or step animations
- NO "how it works" explanations
- NO modal wrapping — this is an inline component
- NO "See How It Works" buttons
- NO agent type labels like "Watcher agent" or "Classifier agent"
- NO automation percentages or giant identity cards
- NO progress bars showing processing steps

## CRITICAL RULES

1. **Default export** a single function component. Name ends with "Panel".
2. **Max 80 lines** — keep it tight and native-feeling.
3. **All mock data is INLINE** — no API calls, no fetch.
4. **Tailwind ONLY** — no inline styles.
5. **LucideIcon** for all icons — PascalCase names only.
6. **Domain-specific mock data** — use the agent's actual behaviors and domain.
7. **Escape apostrophes** — write `don&apos;t` or `{{"don't"}}`, NEVER raw `don't`.
8. **Look native** — the panel should blend into the page like any other data card.

Submit the component via the submit_ai_panel tool."""

# =============================================================================
# Context builder
# =============================================================================


def _format_agent_context(step: Any, payload: PrototypePayload) -> str:
    """Format agent context for the panel builder."""
    lines: list[str] = []
    if isinstance(step, dict):
        sd = step
    elif hasattr(step, "model_dump"):
        sd = step.model_dump()
    else:
        sd = {}

    ai = sd.get("ai_config") or {}
    lines.append(f"# Agent: {ai.get('agent_name', 'AI Agent')}")
    lines.append(f"Type: {ai.get('agent_type', 'assistant')}")
    lines.append(f"Role: {ai.get('role', '')}")

    if ai.get("behaviors"):
        lines.append(f"Behaviors: {'; '.join(ai['behaviors'][:6])}")
    if ai.get("automation_estimate"):
        lines.append(f"Automation: {ai['automation_estimate']}%")
    if ai.get("human_touchpoints"):
        lines.append(f"Human checkpoints: {'; '.join(ai['human_touchpoints'][:4])}")

    lines.append("")
    lines.append(f"## Step Context: {sd.get('title', '')}")
    if sd.get("goal"):
        lines.append(f"Goal: {sd['goal'][:200]}")
    if sd.get("feel_description"):
        lines.append(f"Feel: {sd['feel_description']}")
    if sd.get("story_headline"):
        lines.append(f"Story: {sd['story_headline']}")

    lines.append("")
    lines.append(f"Industry: {payload.company_industry}")
    lines.append(f"Company: {payload.company_name}")

    return "\n".join(lines)


# =============================================================================
# Single panel builder
# =============================================================================


async def _build_single_demo(
    step: Any,
    payload: PrototypePayload,
    client: Any,
) -> dict | None:
    """Build a single AI result panel component with one Haiku call.

    Returns {agent_slug, component_name, tsx} or None on failure.
    """
    if isinstance(step, dict):
        sd = step
    elif hasattr(step, "model_dump"):
        sd = step.model_dump()
    else:
        sd = {}
    ai = sd.get("ai_config") or {}
    agent_name = ai.get("agent_name", "AI Agent")

    # Build slug from agent name
    agent_slug = agent_name.lower().replace(" ", "-").replace("_", "-")

    context = _format_agent_context(step, payload)

    user_message = (
        f"Build an AI result panel component for the {agent_name} agent.\n\n"
        f"{context}\n\n"
        f"The component name should be {_slug_to_pascal(agent_slug)}Panel."
    )

    start = time.monotonic()
    logger.info(f"Building AI panel: {agent_name}...")

    try:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=6000,
            temperature=1,
            system=[
                {
                    "type": "text",
                    "text": AI_DEMO_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                },
            ],
            tools=[AI_DEMO_TOOL],
            messages=[{"role": "user", "content": user_message}],
        )

        duration = time.monotonic() - start

        # Check cache performance
        usage = response.usage
        cached = getattr(usage, "cache_read_input_tokens", 0)
        created = getattr(usage, "cache_creation_input_tokens", 0)
        if cached:
            logger.info(f"  {agent_name}: cache hit ({cached} tokens cached)")
        elif created:
            logger.info(f"  {agent_name}: cache miss ({created} tokens written)")

        # Extract tool use result
        for block in response.content:
            if block.type == "tool_use" and block.name == "submit_ai_panel":
                panel = block.input
                if panel.get("tsx"):
                    lines = panel["tsx"].count("\n") + 1
                    logger.info(
                        f"  {agent_name}: {panel.get('component_name', '?')} "
                        f"({lines} lines, {duration:.1f}s)"
                    )
                    return panel
                else:
                    logger.warning(f"  {agent_name}: empty tsx in {duration:.1f}s")
                    return None

        block_types = [b.type for b in response.content]
        logger.warning(
            f"  {agent_name}: no tool_use after {duration:.1f}s. Blocks: {block_types}"
        )
        return None

    except Exception as e:
        duration = time.monotonic() - start
        logger.error(f"  {agent_name}: failed after {duration:.1f}s: {e}")
        return None


def _slug_to_pascal(slug: str) -> str:
    """Convert kebab-case slug to PascalCase."""
    return "".join(w.capitalize() for w in slug.split("-") if w)


# =============================================================================
# Parallel execution — 1 call per AI agent
# =============================================================================


async def run_ai_demo_builders(
    payload: PrototypePayload,
) -> list[dict]:
    """Run parallel Haiku builders — one per AI agent in the solution flow.

    Returns list of {agent_slug, component_name, tsx} dicts.
    """
    from anthropic import AsyncAnthropic

    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Collect steps that have ai_config
    ai_steps = [
        s
        for s in payload.solution_flow_steps
        if s.ai_config and isinstance(s.ai_config, dict) and s.ai_config.get("agent_name")
    ]

    if not ai_steps:
        logger.info("No AI agents in solution flow — skipping panel builders")
        return []

    logger.info(f"Starting {len(ai_steps)} parallel AI panel builders")
    start = time.monotonic()

    tasks = [_build_single_demo(step, payload, client) for step in ai_steps]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    panels: list[dict] = []
    for step, result in zip(ai_steps, results, strict=True):
        agent_name = (step.ai_config or {}).get("agent_name", "?")
        if isinstance(result, Exception):
            logger.error(f"  {agent_name}: exception: {result}")
        elif result is None:
            logger.warning(f"  {agent_name}: no output")
        else:
            panels.append(result)

    wall_time = time.monotonic() - start
    logger.info(
        f"AI panel builders complete: {len(panels)}/{len(ai_steps)} panels "
        f"in {wall_time:.1f}s wall clock"
    )

    return panels
