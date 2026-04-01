# Prototype Builder — Current State (March 2026)

## Architecture

```
Phase 0 (Sonnet) → prebuild intelligence (epics, feature specs, depth assignments)
    ↓
Payload Assembly → design contract resolution (industry-aware default)
    ↓
Coherence Agent (Sonnet) → structured project plan (nav, screens, components, theme)
    ↓                                    ↓
Haiku Page Builders (parallel)    AI Panel Builders (parallel, 1 per AI agent)
    ↓                                    ↓
Deterministic Cleanup → remove unused imports, fix types, fix apostrophes
    ↓
Stitch → scaffold + layout + routing + pages + AI panels
    ↓
Finisher (Sonnet) → TSX error patches (2-pass retry)
    ↓
npm install → tsc → vite build → deploy
```

## Key Files

| File | Purpose |
|------|---------|
| `app/pipeline/__init__.py` | Pipeline orchestrator — runs all phases |
| `app/pipeline/coherence.py` | Sonnet coherence agent — produces project plan |
| `app/pipeline/builder.py` | Haiku page builders — 1 call per screen |
| `app/pipeline/ai_demo.py` | Haiku AI panel builders — 1 call per AI agent |
| `app/pipeline/stitch.py` | Deterministic stitcher — scaffold + layout + routing |
| `app/pipeline/cleanup.py` | Regex-based TSX cleanup (6 passes) |
| `app/pipeline/finisher.py` | Sonnet finisher — fix remaining tsc errors |
| `app/pipeline/references/design_quality.md` | Design quality reference — loaded into every builder prompt |
| `app/core/build_plan_renderer.py` | Scaffold templates (component library, tailwind config) |
| `app/core/prototype_payload.py` | Payload assembly from project entities |
| `app/core/schemas_prototype_builder.py` | Pydantic schemas for the pipeline |
| `app/core/schemas_prototypes.py` | Design styles (10 styles), design tokens |

## Design Quality System

The design quality reference (`app/pipeline/references/design_quality.md`) is prepended to
every Haiku builder system prompt. It enforces:

- **Anti-slop rules**: no indigo/violet defaults, no gradient buttons, no pill-shaped cards,
  no bouncy animations, no glassmorphism
- **Typography scale**: exact Tailwind classes for each hierarchy level
- **Button + icon alignment**: `inline-flex items-center justify-center gap-2` at scaffold level
- **Status color discipline**: overdue/pending = amber (warning), red only for errors
- **Form patterns**: multi-step wizard template, 1-3 fields per step
- **Spacing grid**: consistent 8px grid

### Badge `danger` variant

Changed from red (`bg-red-50 text-red-700`) to orange (`bg-orange-50 text-orange-700`) at
the scaffold level in `build_plan_renderer.py`. This ensures even when Haiku picks `danger`
for non-error states, it renders warm orange instead of harsh red.

### Button component

Fixed at scaffold level to include `inline-flex items-center justify-center gap-2 rounded-lg`.
Previously was a plain `<button>` with `rounded-full` and no flex — caused icons to stack
above text instead of beside it.

## Design Selection Flow

1. Build API receives optional `design_selection` dict
2. If present → use those tokens directly
3. If absent → check existing prototype's saved design_selection in DB
4. If still absent → **industry-aware default**:
   - Reads company `industry` field + first 300 chars of `description`
   - Keyword matches: legal→luxury_refined, health→healthcare_clinical, tech→tech_modern,
     finance→fintech_pro, creative→creative_playful, retail→marketplace_fresh
   - Fallback: warm_organic (earthy brown, never generic navy)

## 10 Design Styles

All styles have `recommended_nav_style` and 2-3 sentence `style_direction`.
No indigo (#4f46e5) or violet (#7c3aed) — those were removed as AI slop.

| ID | Primary | Nav Style | Character |
|----|---------|-----------|-----------|
| minimal_clean | #1a1a1a | sidebar-light | Sharp, generous whitespace |
| bold_expressive | #1a1a2e | sidebar-dark | High contrast, vibrant red accent |
| warm_organic | #5c4033 | sidebar-light | Earthy, approachable, serif headings |
| luxury_refined | #0c0c0c | sidebar-dark | Gold accent, premium serif |
| tech_modern | #0f172a | sidebar-dark | Navy + blue, dashboard-ready |
| healthcare_clinical | #134e4a | sidebar-light | Deep teal, clinical trust |
| creative_playful | #e11d48 | topnav | Warm rose, playful amber accent |
| fintech_pro | #059669 | sidebar-dark | Emerald, data-precise |
| saas_dashboard | #1e293b | icon-sidebar | Deep slate, teal accent |
| marketplace_fresh | #ea580c | topnav | Warm orange, consumer-friendly |

## AI Agent Integration

When solution flow steps have `ai_config`, two things happen:

1. **Page builders** show AI as having already done its work — inline results,
   confidence scores, subtle "Analyzed by [agent]" attribution. No demo modals,
   no giant identity cards, no automation percentages.

2. **AI Panel builders** (parallel Haiku calls) produce inline result components
   that show the agent's completed output — classifications, decisions, recommendations.
   Written to `src/components/ai/{AgentName}Panel.tsx`.

## Known Issues

- **Red raw Tailwind still appears**: Haiku uses `bg-red-50`, `text-red-600` directly
  in JSX despite prompt instructions. Badge `danger` is now orange but raw classes bypass it.
  Fix: add a cleanup pass to replace `bg-red-*`/`text-red-*` with amber equivalents.
- **AI panels sometimes have syntax errors**: ~10-20% of Haiku-generated panel components
  have JSX syntax issues (unclosed tags, stray braces). Currently handled by removing broken
  files before build. Could add a validation + retry pass.
- **`w-full` button abuse**: Builder rule 16 says not to, but Haiku still does it sometimes.
  Could add a cleanup pass to remove `w-full` from buttons.
- **Coherence cache**: Plans are cached by context hash in `/tmp/pipeline_v2_coherence_cache/`.
  Delete cache files to force regeneration after prompt changes.
