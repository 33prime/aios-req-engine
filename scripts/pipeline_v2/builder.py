"""Haiku Page Builders — 1 parallel Haiku call per screen.

Each builder receives:
  1. The full project plan (cached across all calls)
  2. Its single screen blueprint
  3. Component library reference (in system prompt, cached)

Outputs a single complete TSX page file per call.
Prompt caching: system prompt + plan context are shared across all calls.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from app.core.config import get_settings
from app.core.schemas_prototype_builder import PrototypePayload

logger = logging.getLogger(__name__)

# =============================================================================
# Tool schema — single page output (simpler = more reliable)
# =============================================================================

PAGE_TOOL = {
    "name": "submit_page",
    "description": "Submit the completed page TSX file.",
    "input_schema": {
        "type": "object",
        "required": ["route", "component_name", "tsx"],
        "properties": {
            "route": {
                "type": "string",
                "description": "URL route (e.g. '/dashboard')",
            },
            "component_name": {
                "type": "string",
                "description": ("React component name in PascalCase (e.g. 'DashboardPage')"),
            },
            "tsx": {
                "type": "string",
                "description": "Complete TSX source code for the page",
            },
        },
    },
}

# =============================================================================
# System prompt
# =============================================================================

BUILDER_SYSTEM_PROMPT = """\
You are a senior React+TypeScript developer building production-quality prototype pages.

You will receive a project plan and a single screen assignment. Write a complete, \
self-contained TSX page file that compiles and renders beautifully.

Refer to the Component TypeScript Interfaces block for exact prop types. \
Do NOT invent props that aren't defined.

## Available Imports

```tsx
// React — import what you need
import {{ useState }} from 'react'
import {{ useNavigate }} from 'react-router-dom'

// Component library — import only what you use
import {{
  Card, Badge, Button, TabGroup, Avatar,
  ProgressBar, LucideIcon, Modal, useToast,
}} from '@/components/ui'

// Feature bridge — wrap each feature section
import {{ Feature }} from '@/lib/aios/Feature'
```

## Component API Quick Reference

**Card** — Container with optional header/footer
```tsx
<Card
  header={{<h2 className="font-heading font-semibold">Title</h2>}}
  footer={{<Button>Save</Button>}}>
  {{children}}
</Card>
```

**Badge** — Status indicator. Variants: default, success, warning, danger, accent
```tsx
<Badge variant="success">Active</Badge>
```

**Button** — Action button. Variants: primary, secondary, ghost. Sizes: sm, md, lg
```tsx
<Button variant="primary" size="md" onClick={{() => navigate('/route')}}>Click Me</Button>
```

**LucideIcon** — Icon component. Use PascalCase names from lucide-react.
```tsx
<LucideIcon name="LayoutDashboard" size={{18}} className="text-primary" />
```
Common icons: LayoutDashboard, Users, BarChart3, Settings, Search, Plus, ArrowRight, \
Clock, Target, Activity, Bell, FileText, Folder, Globe, Heart, Mail, Star, Zap, \
CheckCircle, AlertCircle, TrendingUp, TrendingDown, ChevronRight, Filter, Download, \
Upload, Eye, Edit, Trash2, MoreVertical, Calendar, MessageCircle, Headphones, Mic, \
Play, Pause, SkipForward, Volume2, Radio, Podcast, Music, BookOpen, PenTool, Image, \
Video, Award, Gift, ShoppingCart, CreditCard, DollarSign, Percent, Hash, AtSign, \
Link, ExternalLink, Share2, Copy, Bookmark, Flag, MapPin, Navigation, Compass, Layers, \
Grid, List, Columns, Maximize2, Minimize2, RefreshCw, RotateCcw, Wifi, Bluetooth, Cpu

**Avatar** — User avatar circle
```tsx
<Avatar initials="MC" name="Maria Chen" size="md" />
```

**TabGroup** — Tab navigation
```tsx
<TabGroup items={{[
  {{ label: 'Overview', content: <div>...</div> }},
  {{ label: 'Details', content: <div>...</div> }},
]}} />
```

**Modal** — Dialog overlay
```tsx
const [open, setOpen] = useState(false)
<Modal open={{open}} onClose={{() => setOpen(false)}} title="Details">{{children}}</Modal>
```

**useToast** — Toast notifications
```tsx
const {{ toast }} = useToast()
// Call: toast('Saved successfully!', 'success')  // variants: success, error, info
```

**ProgressBar** — Progress indicator
```tsx
<ProgressBar value={{75}} label="Completion" />
```

**Feature** — AIOS bridge wrapper (REQUIRED around feature sections)
```tsx
<Feature id="feature-slug">{{feature content}}</Feature>
```

## Page Structure

Every page MUST follow this pattern:

```tsx
import {{ useState }} from 'react'
import {{ useNavigate }} from 'react-router-dom'
import {{ Card, Badge, Button, LucideIcon }} from '@/components/ui'
import {{ Feature }} from '@/lib/aios/Feature'

export default function PageNamePage() {{
  const navigate = useNavigate()
  // ... state hooks

  return (
    <div className="space-y-8">
      {{/* Page header */}}
      <div>
        <h1 className="text-2xl font-heading font-bold text-gray-900">Headline</h1>
        <p className="text-gray-500 mt-1">Subtitle</p>
      </div>

      {{/* Feature sections */}}
      <Feature id="feature-slug">
        {{/* Component content */}}
      </Feature>
    </div>
  )
}}
```

## CRITICAL RULES

1. **Default export** a single function component. Name ends with "Page".
2. **Import Feature** from '@/lib/aios/Feature' — wrap each feature section.
3. **All mock data is INLINE** — no API calls, no fetch, no external data.
4. **useNavigate** for ALL navigation — `onClick={{() => navigate('/route')}}`.
5. **useState** for ALL interactive elements: forms, toggles, search, filters, modals.
6. **Tailwind ONLY** — no inline styles except CSS custom properties.
7. **LucideIcon** for ALL icons — PascalCase names only, NEVER raw SVG.
8. **Only import what you use** — TypeScript strict mode rejects unused imports.
9. **Visually RICH** — use spacing, shadows, rounded corners, hover states, colors.
10. **Domain-specific mock data** — realistic names, values, dates for the industry.
11. **Every button does something** — navigates, opens modal, triggers toast, toggles state.
12. **Feature wrapping** — every distinct feature area gets a `<Feature id="slug">` wrapper.

## Tailwind Utilities

Custom classes available:
- `text-primary`, `bg-primary`, `border-primary` — brand primary color
- `text-secondary`, `bg-secondary` — brand secondary color
- `font-heading` — heading font family
- `font-body` — body font family
- `.glass-card` — frosted glass card effect
- `.gradient-hero` — primary→secondary gradient background
- `.stat-card` — pre-styled stat card
- `.animate-page-enter` — fade-in-up animation
- `.animate-slide-up` — slide up animation

Submit the page via the submit_page tool."""

# =============================================================================
# Component TypeScript interfaces — cached as a system block
# =============================================================================

COMPONENT_TYPES_REFERENCE = """\
# Component TypeScript Interfaces

These are the EXACT interfaces for every component in `@/components/ui`.
Only use props listed here. Do NOT invent props that aren't defined.

## Card
```tsx
interface CardProps {{
  children: ReactNode
  className?: string
  header?: ReactNode
  footer?: ReactNode
}}
// Usage: <Card header={{...}} footer={{...}} className="...">{{children}}</Card>
// NO onClick, NO title prop, NO variant prop.
```

## Badge
```tsx
const variants = {{
  default: 'bg-gray-100 text-gray-700',
  success: 'bg-green-50 text-green-700',
  warning: 'bg-amber-50 text-amber-700',
  danger: 'bg-red-50 text-red-700',
  accent: 'bg-primary/10 text-primary',
}} as const

interface BadgeProps {{
  children: React.ReactNode
  variant?: keyof typeof variants  // "default" | "success" | "warning" | "danger" | "accent"
  className?: string
}}
// Usage: <Badge variant="success">Active</Badge>
```

## Button
```tsx
const variants = {{
  primary: 'bg-primary text-white hover:shadow-lg',
  secondary: 'bg-white text-gray-900 border border-gray-200 hover:bg-gray-50',
  ghost: 'text-gray-600 hover:bg-gray-100',
}} as const

const sizes = {{
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-5 py-2.5 text-sm',
  lg: 'px-8 py-3 text-base',
}} as const

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {{
  variant?: keyof typeof variants  // "primary" | "secondary" | "ghost"
  size?: keyof typeof sizes        // "sm" | "md" | "lg"
}}
// Inherits onClick, disabled, className, children, type, etc. from ButtonHTMLAttributes.
// Usage: <Button variant="primary" size="md" onClick={{handler}}>Label</Button>
```

## TabGroup
```tsx
interface TabItem {{
  label: string
  content: React.ReactNode
}}

interface TabGroupProps {{
  items: TabItem[]
  defaultIndex?: number
}}
// Usage: <TabGroup items={{[{{ label: 'Tab1', content: <div>...</div> }}]}} />
// NO activeIndex prop. NO onTabChange prop. State is internal.
```

## Avatar
```tsx
const sizeMap = {{
  sm: 'w-8 h-8 text-xs',
  md: 'w-10 h-10 text-sm',
  lg: 'w-14 h-14 text-lg',
}} as const

interface AvatarProps {{
  initials: string
  name?: string
  size?: keyof typeof sizeMap  // "sm" | "md" | "lg"
  src?: string
  className?: string
}}
// Usage: <Avatar initials="MC" name="Maria Chen" size="md" />
// If src is provided, renders an <img>. Otherwise renders initials circle.
```

## ProgressBar
```tsx
interface ProgressBarProps {{
  value: number      // 0-100, clamped internally
  label?: string     // shown above the bar with percentage
  className?: string
}}
// Usage: <ProgressBar value={{75}} label="Completion" />
// NO color prop. NO size prop. Always uses bg-primary.
```

## LucideIcon
```tsx
interface LucideIconProps {{
  name: string       // PascalCase icon name from lucide-react
  size?: number      // pixel size, default 20
  className?: string
}}
// Usage: <LucideIcon name="BarChart3" size={{18}} className="text-primary" />
// Renders a fallback <span> if the icon name doesn't exist.
```

## Modal
```tsx
interface ModalProps {{
  open: boolean
  onClose: () => void
  title?: string
  children: React.ReactNode
}}
// Usage:
//   const [open, setOpen] = useState(false)
//   <Modal open={{open}} onClose={{() => setOpen(false)}} title="Details">
//     {{children}}
//   </Modal>
// NO size prop. NO fullScreen prop. Handles Escape key internally.
```

## useToast
```tsx
interface ToastContextType {{
  toast: (message: string, variant?: 'success' | 'error' | 'info') => void
}}

// Usage:
//   const {{ toast }} = useToast()
//   toast('Saved successfully!', 'success')
// Default variant is 'success'. Auto-dismisses after 3 seconds.
// NO duration param. NO position param.
```

## Feature (AIOS bridge wrapper)
```tsx
interface FeatureProps {{
  id: string          // feature slug
  children: ReactNode
}}
// Usage: <Feature id="feature-slug">{{content}}</Feature>
// REQUIRED around every distinct feature section.
```"""

# =============================================================================
# Context builder
# =============================================================================


def _format_plan_context(project_plan: dict, payload: PrototypePayload) -> str:
    """Format the project plan as a readable brief for the builder."""
    lines: list[str] = []

    lines.append(f"# Project Plan: {project_plan.get('app_name', 'Prototype')}")
    lines.append(f"Industry: {payload.company_industry}")
    if payload.personas:
        p0 = payload.personas[0]
        lines.append(f"Primary user: {p0.name} ({p0.role})")
    else:
        lines.append("")
    lines.append("")

    lines.append("## Design Direction")
    lines.append(project_plan.get("design_direction", "Modern, clean, professional"))
    lines.append("")

    lines.append("## Shared Patterns")
    for p in project_plan.get("shared_patterns", []):
        lines.append(f"- {p}")
    lines.append("")

    lines.append("## All Routes (for navigation targets)")
    for section in project_plan.get("nav_sections", []):
        for screen in section.get("screens", []):
            lines.append(f"- {screen['route']} → {screen['nav_label']}")
    lines.append("")

    # Shared mock data for cross-page consistency
    shared = project_plan.get("shared_data")
    if shared and isinstance(shared, dict):
        lines.append("## Shared Mock Data (USE THESE EXACT VALUES)")
        if shared.get("metrics"):
            lines.append("### Metrics")
            for k, v in shared["metrics"].items():
                lines.append(f"- {k}: {v}")
        if shared.get("user_names"):
            lines.append(f"### User Names: {', '.join(shared['user_names'])}")
        if shared.get("status_options"):
            lines.append(f"### Statuses: {', '.join(shared['status_options'])}")
        if shared.get("sample_items"):
            lines.append(f"### Sample Items ({len(shared['sample_items'])} items)")
            import json

            for item in shared["sample_items"][:3]:
                lines.append(f"  {json.dumps(item)}")
            if len(shared["sample_items"]) > 3:
                lines.append(f"  ... and {len(shared['sample_items']) - 3} more")
        lines.append("")

    return "\n".join(lines)


def _format_single_screen(screen: dict) -> str:
    """Format a single screen blueprint for the builder."""
    lines: list[str] = []

    lines.append(f"## Screen: {screen['page_title']}")
    lines.append(f"Route: {screen['route']}")
    lines.append(f"Layout: {screen['layout']}")
    if screen.get("ux_copy"):
        ux = screen["ux_copy"]
        lines.append(f"Headline: {ux.get('headline', '')}")
        lines.append(f"Subtitle: {ux.get('subtitle', '')}")
    lines.append("")
    lines.append("Components:")
    for comp in screen.get("components", []):
        lines.append(f"  [{comp['type']}] feature={comp.get('feature_slug', 'none')}")
        if comp.get("title"):
            lines.append(f"    Title: {comp['title']}")
        lines.append(f"    Guidance: {comp['guidance']}")
        lines.append("")

    return "\n".join(lines)


# =============================================================================
# Single page builder
# =============================================================================


async def _build_single_page(
    screen: dict,
    plan_context: str,
    project_plan: dict,
    client: Any,
) -> dict | None:
    """Build a single page with one Haiku call.

    Returns {route, component_name, tsx} or None on failure.
    """
    screen_blueprint = _format_single_screen(screen)
    route = screen["route"]

    # User message is screen-specific (small), plan context is cached
    user_message = (
        f"Build this page for the "
        f"{project_plan.get('app_name', '')} prototype.\n\n"
        f"{screen_blueprint}"
    )

    start = time.monotonic()
    logger.info(f"Building {route}...")

    try:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=8192,
            temperature=1,
            system=[
                {
                    "type": "text",
                    "text": BUILDER_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                },
                {
                    "type": "text",
                    "text": COMPONENT_TYPES_REFERENCE,
                    "cache_control": {"type": "ephemeral"},
                },
                {
                    "type": "text",
                    "text": plan_context,
                    "cache_control": {"type": "ephemeral"},
                },
            ],
            tools=[PAGE_TOOL],
            messages=[{"role": "user", "content": user_message}],
        )

        duration = time.monotonic() - start

        # Check cache performance
        usage = response.usage
        cached = getattr(usage, "cache_read_input_tokens", 0)
        created = getattr(usage, "cache_creation_input_tokens", 0)
        if cached:
            logger.info(f"  {route}: cache hit ({cached} tokens cached)")
        elif created:
            logger.info(f"  {route}: cache miss ({created} tokens written)")

        # Extract tool use result
        for block in response.content:
            if block.type == "tool_use" and block.name == "submit_page":
                page = block.input
                if page.get("tsx"):
                    lines = page["tsx"].count("\n") + 1
                    logger.info(
                        f"  {route}: {page.get('component_name', '?')} "
                        f"({lines} lines, {duration:.1f}s)"
                    )
                    return page
                else:
                    logger.warning(f"  {route}: empty tsx in {duration:.1f}s")
                    return None

        block_types = [b.type for b in response.content]
        logger.warning(f"  {route}: no tool_use after {duration:.1f}s. Blocks: {block_types}")
        return None

    except Exception as e:
        duration = time.monotonic() - start
        logger.error(f"  {route}: failed after {duration:.1f}s: {e}")
        return None


# =============================================================================
# Parallel execution — 1 call per screen
# =============================================================================


async def run_haiku_builders(
    project_plan: dict[str, Any],
    payload: PrototypePayload,
    prebuild: Any = None,
) -> list[dict]:
    """Run parallel Haiku builders — one call per screen.

    All calls share the same system prompt and plan context via
    Anthropic prompt caching, so only the per-screen blueprint
    is uncached.

    Returns list of {route, component_name, tsx} dicts.
    """
    from anthropic import AsyncAnthropic

    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Collect all screens from plan
    all_screens: list[dict] = []
    for section in project_plan.get("nav_sections", []):
        for screen in section.get("screens", []):
            all_screens.append(screen)

    if not all_screens:
        logger.warning("No screens in project plan")
        return []

    # Shared plan context (will be cached across all calls)
    plan_context = _format_plan_context(project_plan, payload)

    logger.info(
        f"Starting {len(all_screens)} parallel page builders "
        f"(plan context: ~{len(plan_context)} chars)"
    )

    start = time.monotonic()

    tasks = [
        _build_single_page(screen, plan_context, project_plan, client) for screen in all_screens
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    wall_time = time.monotonic() - start

    pages: list[dict] = []
    failed: list[str] = []
    for screen, result in zip(all_screens, results, strict=True):
        route = screen["route"]
        if isinstance(result, Exception):
            logger.error(f"  {route}: exception: {result}")
            failed.append(route)
        elif result is None:
            failed.append(route)
        else:
            pages.append(result)

    logger.info(
        f"Builders complete: {len(pages)}/{len(all_screens)} pages in {wall_time:.1f}s wall clock"
    )
    if failed:
        logger.warning(f"Failed pages: {', '.join(failed)}")

    return pages
