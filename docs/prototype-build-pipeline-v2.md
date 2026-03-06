# Prototype Build Pipeline v2 — The Complete Reference

> **The initial prototype build is the truest of all true KPIs.** Everything is optimized so that when a consultant and client first see it, they think: *holy shit, we have reached AGI.*

---

## Philosophy

This pipeline exists to make one thing: a prototype that **inspires**. Not a wireframe. Not a feature checklist. A real, interactive, deployable app that shows the client their vision coming to life. The prototype is the 3D version of the 2D solution flow.

We are doing **discovery and requirements validation**, not QA. We're not auditing code, checking edge cases, or testing error states. We're validating that the **solution solves real pain** and **produces real value**. Features combine. User flows matter. Sign-in and notifications are plumbing — they don't get epics.

---

## Architecture at a Glance

```
Confirmed Discovery Data (features, personas, solution flow, drivers)
    ↓
Phase 0: Pre-Build Intelligence (LangGraph, ~30s)
    ├─ Graph enrichment + confidence scoring
    ├─ Epic assembly (5-7 narrative journey epics)
    ├─ Narrative composition (Sonnet 4.6)
    └─ Depth assignment per feature (full/visual/placeholder)
    ↓
Payload Assembly (13 parallel DB queries, ~2s)
    ↓
Pipeline v2 (total ~5-8 min):
    1. Coherence Agent (Sonnet 4.6, ~3-4 min) → structured project plan
    2. Haiku Builders (parallel, 1 per screen, ~1-2 min) → raw TSX pages
    3. Deterministic Stitch (~0.1s) → complete file tree
    4. Deterministic Cleanup (~0.1s) → fix common TS errors
    5. npm install (~5s)
    6. Finisher Agent (Sonnet 4.6, up to 2 passes, ~1-2 min) → surgical patches
    7. tsc + vite build (~5s)
    ↓
Deployed Prototype (Netlify)
```

---

## Models Used

| Role | Model | Model ID | Why |
|------|-------|----------|-----|
| **Coherence Agent** | Sonnet 4.6 | `claude-sonnet-4-6` | Architectural planning — needs reasoning quality |
| **Page Builders** | Haiku 4.5 | `claude-haiku-4-5-20251001` | Parallel code gen — speed + cost for known patterns |
| **Finisher Agent** | Sonnet 4.6 | `claude-sonnet-4-6` | Error diagnosis — needs to understand TS semantics |

**Not used**: Opus (too slow for build pipeline), Sonnet 4.5 (doesn't exist — Sonnet 4.6 is the current version).

---

## Phase-by-Phase Breakdown

### Phase 1: Coherence Agent

**File**: `app/pipeline/coherence.py`
**Model**: Sonnet 4.6 with extended thinking (budget: 4000 tokens)
**Duration**: ~3-4 minutes (the bottleneck)
**Caching**: Plans cached by context hash — repeat builds skip this entirely

The coherence agent receives all discovery data and produces a structured project plan via `tool_use`. This plan is the blueprint that all Haiku builders follow.

**Output structure** (`submit_project_plan` tool):
- `app_name` — short branding name
- `theme` — sidebar colors, content bg, accent usage
- `nav_sections` — 2-4 sidebar groups with 5-8 screens
- `design_direction` — 2-3 sentence visual brief
- `shared_patterns` — rules for all builders
- `shared_data` — canonical mock data (metrics, names, statuses, sample items)
- `agent_assignments` — which routes each builder handles
- `route_manifest` — epic→route and feature→route mappings

**Critical rules in the prompt**:
1. Target 5-8 screens (group solution flow steps, NEVER 1:1)
2. Max 5 components per screen (more causes builder failures)
3. Short nav labels (1-2 words)
4. Dark sidebar always (bg-slate-900)
5. Domain-specific realistic mock data
6. Every button does something (navigate, toast, toggle)

**Known gotcha**: The model sometimes serializes arrays/objects as JSON strings inside the tool_use input. `_fix_string_encoded_fields()` handles this with `json_repair`.

**Optimization history**:
- Thinking budget reduced from 6000 → 4000 (no quality loss, saves ~30s)
- Context trimmed: solution flow and epic plan sections made concise
- Plans cached by context hash — second run with same data is instant

### Phase 2: Haiku Builders

**File**: `app/pipeline/builder.py`
**Model**: Haiku 4.5 (`claude-haiku-4-5-20251001`)
**Duration**: ~1-2 minutes (parallel, all screens at once)
**Max tokens**: 12000 per page
**Prompt caching**: System prompt + component reference + plan context cached across all calls

Each screen gets one Haiku call. All calls run in parallel via `asyncio.gather`. The system prompt and plan context are cached as `cache_control: {"type": "ephemeral"}` blocks — so the first call pays the cache write cost, and subsequent calls get cache hits.

**3-pass retry strategy**:
1. Initial parallel build — all screens at once
2. Retry failed pages — same prompt (Haiku is stochastic)
3. Simplified retry — caps components at 3, adds conciseness directive

**Output**: Each call returns `{route, component_name, tsx}` via `submit_page` tool.

**Known gotchas**:
- **Token truncation**: Pages with many components can exceed max_tokens, causing `stop_reason: "max_tokens"` and a truncated tool call. Increased from 8192→12000 to eliminate most truncation.
- **Badge variant typing**: Haiku generates `Record<string, string>` maps for variant lookups. Badge expects `"default" | "success" | "warning" | "danger" | "accent"`. Builder prompt now includes explicit typing rules.
- **Card onClick**: Haiku adds `onClick` to Card, but Card has no onClick prop. Builder prompt now warns about this. Cleanup pass also fixes it.
- **Unescaped apostrophes**: Haiku writes `don't` in JSX text. Builder prompt now says to use `&apos;`. Cleanup pass also fixes it.
- **Cache miss on first run**: All 8 initial calls are cache misses on the first run (cache write). Second run gets cache hits. This is unavoidable with ephemeral caching.

**Component library** (available imports):
- `Card` (header, footer, children — NO onClick, NO variant)
- `Badge` (variant: default/success/warning/danger/accent)
- `Button` (variant: primary/secondary/ghost, size: sm/md/lg, inherits ButtonHTMLAttributes)
- `TabGroup` (items: {label, content}[], defaultIndex)
- `Avatar` (initials, name, size: sm/md/lg, src)
- `ProgressBar` (value: 0-100, label)
- `LucideIcon` (name: PascalCase, size, className)
- `Modal` (open, onClose, title, children)
- `useToast` → toast(message, variant: success/error/info)
- `Feature` (id: feature slug, children) — REQUIRED wrapper

### Phase 3: Deterministic Stitch

**File**: `app/pipeline/stitch.py`
**Duration**: ~0.1s (pure Python, no LLM)

Assembles the complete file tree from:
1. **Config scaffold** (package.json, vite.config, tailwind, tsconfig, index.html) — from `_render_vite_config_scaffold()`
2. **LucideIcon override** — handles kebab-case icon names
3. **Feature wrapper** + AiosBridge — postMessage communication with parent iframe
4. **Route manifest** — JSON for workbench to fetch
5. **Layout.tsx** — sidebar nav from coherence plan (dark theme, persona in user menu)
6. **App.tsx** — React Router routes from plan
7. **Page files** — from Haiku builders
8. **Fallback pages** — stub pages for any route with no builder output

**Known gotcha**: Layout.tsx generates literal TypeScript with nav sections data inline. If a nav label contains a single quote, it breaks the string literal. Not yet fixed — hasn't happened in practice.

### Phase 4: Deterministic Cleanup

**File**: `app/pipeline/cleanup.py`
**Duration**: ~0.1s
**Target**: 90%+ of tsc errors from Haiku output

6 regex-based passes that run on every `src/pages/*.tsx` file:

| Pass | What it fixes | Common? |
|------|--------------|---------|
| 1. Unused imports | Imported symbols not used in body | Very common |
| 2. Unused useState | Both value+setter unused → remove; setter unused → simplify | Common |
| 3. Card onClick | Wraps `<Card onClick={...}>` with clickable div | Occasional |
| 4. Unescaped apostrophes | `don't` → `don&apos;t` in JSX text | Common |
| 5. Missing React keys | Adds `key` prop to `.map()` calls missing it | Occasional |
| 6. Variant type safety | `Record<string,string>` → `as const` + union cast | Common |

**Goal**: Reduce finisher work from ~13 issues to near-zero. Every error the cleanup catches is one less LLM token spent and one less chance for the finisher to introduce a regression.

### Phase 5: Finisher Agent

**File**: `app/pipeline/finisher.py`
**Model**: Sonnet 4.6 with extended thinking (budget: 8000 tokens)
**Duration**: ~1-2 minutes (up to 2 passes)

Pre-flight: runs `tsc --noEmit` to find real errors. Sends error output + all page files + route list to Sonnet for surgical patching.

**What it checks**:
1. Import resolution (knows exact exports of every module)
2. Unused imports/variables (strict mode violations)
3. Navigation targets (navigate calls match real routes)
4. React keys on .map() calls
5. Type safety (no implicit any)
6. JSX validity (unclosed tags, invalid attributes)

**Output**: `{patches, issues_found, assessment}` via `submit_review` tool. Each patch is `{file, find, replace}` — exact string find-and-replace.

**2-pass loop**: If tsc still has errors after pass 1, reload files from disk and run again. Stops after pass 2 regardless.

**Known gotchas**:
- Finisher patches must match exactly (whitespace-sensitive). If the find string doesn't exist in the file (because cleanup already fixed it, or another patch changed the context), the patch silently fails.
- Finisher sometimes "fixes" things by removing functionality. The prompt says "ONLY fix compilation/runtime errors" but Sonnet occasionally refactors.
- Finisher occasionally misses errors that span multiple files (e.g., App.tsx imports a component that doesn't exist because the builder named it differently).

**The goal is to eliminate the finisher entirely.** Every cleanup pass we add, every builder prompt improvement we make, reduces the finisher's workload. When cleanup catches 100% of tsc errors, the finisher becomes a validation-only step (run tsc, confirm clean, done).

---

## The File Tree

```
build/
├── package.json              # React 18 + Tailwind + Vite
├── vite.config.ts            # Path aliases (@/)
├── tailwind.config.js        # Design tokens, custom classes
├── tsconfig.json             # Strict mode
├── tsconfig.app.json
├── postcss.config.js
├── index.html
├── public/
│   ├── route-manifest.json   # Epic→route, feature→route mappings
│   └── _redirects            # Netlify SPA redirect
└── src/
    ├── main.tsx              # React root + ToastProvider
    ├── App.tsx               # React Router routes
    ├── index.css             # Tailwind imports + custom classes
    ├── components/
    │   └── ui/
    │       ├── index.ts      # Re-exports all components
    │       ├── Card.tsx
    │       ├── Badge.tsx
    │       ├── Button.tsx
    │       ├── TabGroup.tsx
    │       ├── Avatar.tsx
    │       ├── ProgressBar.tsx
    │       ├── LucideIcon.tsx  # Overridden: handles kebab-case
    │       ├── Modal.tsx
    │       └── Toast.tsx       # useToast + ToastProvider
    ├── lib/
    │   └── aios/
    │       ├── Feature.tsx     # Feature wrapper (data-aios-feature)
    │       └── AiosBridge.tsx  # PostMessage bridge (zero UI)
    └── pages/
        ├── Layout.tsx          # Sidebar + Outlet
        ├── DashboardPage.tsx   # Builder output
        ├── ...Page.tsx         # One per screen
        └── SettingsPage.tsx
```

---

## Timing Breakdown (Real Numbers from PersonaPulse Build)

| Phase | Duration | Notes |
|-------|----------|-------|
| Coherence (Sonnet 4.6) | 259s (4.3 min) | The bottleneck. Thinking + tool_use. |
| Builders (Haiku 4.5, 8 parallel) | 120s (2 min) | 5/8 on first pass, 3 needed retries |
| Stitch | <1s | Pure Python |
| Cleanup | <1s | 6 regex passes |
| npm install | 5s | |
| Finisher pass 1 (Sonnet 4.6) | 65s | 15 patches |
| Finisher pass 2 (Sonnet 4.6) | 60s | 7 patches |
| tsc + vite build | 5s | |
| **Total** | **518s (~8.5 min)** | |

**After optimizations** (projected):
- Coherence: ~180s (reduced thinking budget + trimmed context)
- Builders: ~80s (12K max_tokens eliminates most retries)
- Cleanup: catches 80-90% of finisher's work
- Finisher: 0-1 pass (ideally zero patches needed)
- **Target total: ~5-6 min**

---

## Gotchas & Failure Patterns

### Builder Failures

| Pattern | Cause | Fix |
|---------|-------|-----|
| Empty tsx output | Haiku hit max_tokens, tool call truncated | Increase max_tokens (8192→12000) |
| `stop_reason: "max_tokens"` | Page too complex (>5 components) | Coherence caps at 5 components/screen |
| `Record<string, string>` on Badge | Haiku doesn't know Badge variant is a union | Builder prompt + cleanup pass |
| `onClick` on Card | Card has no onClick prop | Builder prompt + cleanup pass |
| Unescaped `'` in JSX | Haiku writes `don't` instead of `don&apos;t` | Builder prompt + cleanup pass |
| Unused imports | Haiku imports everything from ui, uses some | Cleanup pass 1 |
| Unused useState | Haiku declares state for planned features, doesn't use it | Cleanup pass 2 |
| Import from wrong path | `@/components/Badge` instead of `@/components/ui` | Finisher catches this |

### Coherence Failures

| Pattern | Cause | Fix |
|---------|-------|-----|
| JSON strings in tool output | Model serializes objects as strings | `_fix_string_encoded_fields()` + `json_repair` |
| Too many screens (>10) | Model creates 1 screen per solution flow step | System prompt rule: "TARGET 5-8 SCREENS" |
| Long nav labels | Model writes "Comprehensive Analytics Dashboard" | System prompt rule: "1-2 words max" |
| No tool_use in response | Model responds with text instead of tool call | Fallback JSON parser on text blocks |
| Missing route_manifest | Model forgets this field | Required in tool schema |

### Stitch Failures

| Pattern | Cause | Fix |
|---------|-------|-----|
| Component name mismatch | Builder outputs `Dashboard` but plan says `DashboardPage` | `_route_to_component_name()` normalizes |
| Missing page file | Builder failed all 3 retries | Fallback stub page generated |
| Nav label with `'` | Breaks TypeScript string literal in Layout.tsx | Not yet fixed (rare) |

### Finisher Failures

| Pattern | Cause | Fix |
|---------|-------|-----|
| Patch doesn't match | Find string changed by cleanup or previous patch | Silently skipped (logged) |
| Introduces regression | "Fix" removes valid code | System prompt says "ONLY fix compilation errors" |
| Misses cross-file error | Doesn't see relationships between files | Limited to what tsc reports |
| Takes 2+ passes | Some errors only visible after fixing others | Loop limit: 2 passes |

---

## Optimizing Data BEFORE the Build

The initial prototype build quality is entirely determined by what goes IN. Garbage in, garbage out. Here's how to maximize the "holy shit" factor:

### 1. Solution Flow Quality is Everything

The solution flow is the spine of the prototype. Every screen maps to solution flow steps. If the flow is weak, the prototype is weak.

**What makes a great solution flow**:
- **5-8 steps** covering the complete user journey (entry → core → output)
- Each step has a clear **goal** (what the user achieves)
- Each step has **information_fields** (captured, displayed, computed) — this tells the builder what UI components to use
- Steps have **ai_config** when AI plays a role — this enables AI-specific component types
- Steps have **implied_pattern** (e.g., "dashboard", "wizard", "kanban") — this maps directly to screen layouts
- Steps link to **features** — this ensures every feature appears somewhere

**What kills a solution flow**:
- Too many steps (>10) → coherence creates too many screens
- Vague goals ("manage things") → builder generates generic UI
- No information fields → builder has no idea what data to show
- Missing AI annotations → AI features look like regular forms

### 2. Feature Confirmation Coverage

Only confirmed features make it into the payload. Unconfirmed features are invisible to the pipeline.

**Optimization**: Run `bulk_recommend_assignments()` + get stakeholder confirmations before building. Every confirmed feature = one more element in the prototype.

**Minimum for a good build**: 5+ confirmed features across at least 2 horizons.

### 3. Persona Richness

Personas drive mock data quality. A persona with just a name produces generic UI. A persona with goals, pain points, and a clear role produces domain-specific, realistic mock data.

**Minimum**: 1 primary persona with goals, pain points, role, and a name that sounds real (not "User A").

### 4. Business Drivers → KPI Cards

Business drivers with measurement methods become KPI metric cards on dashboards. Without them, the dashboard is just pretty boxes.

**Minimum**: 2-3 drivers with measurable targets.

### 5. Design Contract

The design contract controls visual identity: primary/secondary/accent colors, fonts, style direction. Without it, the prototype uses the default "tech_modern" theme — which is fine but generic.

**Best**: Client provides brand colors + font preferences during onboarding. The prototype then immediately feels "theirs."

### 6. Workflow Data → ROI Stories

Current→future workflow pairs produce before/after comparisons. This is gold for prototypes — showing "here's how it works today vs how it'll work with the solution."

**Minimum**: 2+ workflow pairs with time/frequency estimates.

### 7. The Compounding Effect

Each data source compounds:
- **Features + solution flow** → screen structure
- **Personas + features** → mock data quality
- **Drivers + features** → KPI dashboards
- **Workflows + solution flow** → automation stories
- **AI annotations + features** → intelligent component types
- **Constraints** → scope boundaries (what's NOT in the prototype)

The more confirmed, interconnected data, the more the prototype feels like a real product instead of a demo shell.

### 8. Pre-Build Intelligence (Phase 0)

The prebuild pipeline clusters features into narrative epics and assigns build depth. This is where you can influence which features get full treatment vs placeholder stubs.

**Depth assignment rules**:
- `must_have` priority → full (interactive, complete)
- H1 horizon → full
- `should_have` + H2 → visual (styled, limited interaction)
- `could_have` or H3 → placeholder (stub with Feature wrapper)

**Optimization**: Ensure high-value features are marked `must_have` and `H1` before the build. This guarantees they get full treatment.

---

## Token Economics

| Component | Input tokens | Output tokens | Cost |
|-----------|-------------|---------------|------|
| Coherence (Sonnet) | ~5,000 | ~3,000 | ~$0.06 |
| 8 Builders (Haiku) | ~3,000 each | ~2,000 each | ~$0.10 total |
| Finisher (Sonnet) | ~8,000 | ~2,000 | ~$0.06 |
| **Total per build** | | | **~$0.22** |

Prompt caching saves ~60% on builder input costs when system prompt hits cache (all but first call).

---

## Source Files

| File | Lines | Role |
|------|-------|------|
| `app/pipeline/__init__.py` | ~250 | Main orchestrator |
| `app/pipeline/coherence.py` | ~670 | Sonnet coherence agent |
| `app/pipeline/builder.py` | ~680 | Haiku page builders |
| `app/pipeline/stitch.py` | ~500 | Deterministic file assembly |
| `app/pipeline/cleanup.py` | ~500 | Deterministic TSX cleanup |
| `app/pipeline/finisher.py` | ~250 | Sonnet finisher agent |
| `app/core/prototype_payload.py` | ~420 | Payload assembly |
| `app/core/schemas_prototype_builder.py` | ~350 | Pydantic schemas |
| `app/core/build_plan_renderer.py` | varies | Config scaffold generation |
| `scripts/pipeline_v2/run.py` | ~400 | Test harness |

---

## Road to Zero Finisher

The finisher is a tax. Every patch it applies is a failure of the builder or cleanup to get it right the first time. Here's the roadmap to eliminating it:

### Already Done
- [x] Builder prompt includes component type interfaces
- [x] Builder prompt warns about Card onClick, Badge variant typing, apostrophes
- [x] Cleanup catches unused imports and useState
- [x] Cleanup fixes Card onClick, apostrophes, missing keys, variant types
- [x] max_tokens increased to 12000 to prevent truncation

### Next Steps
- [ ] Add cleanup pass for implicit `any` in `.map()` callbacks (e.g., `.map((item) =>` → `.map((item: typeof data[0]) =>`)
- [ ] Add cleanup pass for common event handler types (e.g., `onChange={(e) =>` → `onChange={(e: React.ChangeEvent<HTMLInputElement>) =>`)
- [ ] Add navigation target validation to cleanup (check App.tsx routes)
- [ ] Track finisher patch categories across builds to identify new patterns
- [ ] When cleanup catches 100% of errors for 5 consecutive builds, make finisher opt-in

### The Ultimate State
```
Coherence → Builders → Stitch → Cleanup → tsc --noEmit → PASS → vite build → PASS → Done
                                                   ↑
                                            No finisher needed
```

---

## Test Harness

```bash
# Default: PersonaPulse project
uv run python scripts/pipeline_v2/run.py

# Custom project
uv run python scripts/pipeline_v2/run.py --project-id <uuid>

# Skip coherence (reuse cached plan)
uv run python scripts/pipeline_v2/run.py --skip-coherence

# Output goes to /tmp/pipeline_v2_test/build/
# Deploy: cd /tmp/pipeline_v2_test/build && netlify deploy --dir=dist --prod --site=<site-id>
```

PersonaPulse test project UUID: `43ee2e56-00f9-48e9-9dbc-4fded7c3255b`
