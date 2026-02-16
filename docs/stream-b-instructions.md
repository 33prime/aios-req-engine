# Stream B: Client Intelligence + Portal

## Mission

Surface the Client Intelligence (CI) Agent's rich analysis on the client detail page and align the client portal with that data. The CI agent backend is fully built and produces constraints, role gaps, vision synthesis, organizational context, and profile completeness scoring — but almost none of this is visible in the UI.

---

## Scope — What to Build

### Task 1: Upgrade Client Detail Page (`/clients/[id]`)

**Problem:** The client detail page only shows basic enrichment data (company summary, market position, tech stack, growth signals, competitors). The CI agent produces far richer intelligence that is invisible.

**What to add:**

#### 1a. Add "Analyze" button to ClientHeader
- File: `apps/workbench/app/clients/[id]/components/ClientHeader.tsx`
- Next to the existing "Enrich" button, add an "Analyze" button that calls `analyzeClient(clientId)` (already in `lib/api.ts` line 2938)
- "Enrich" = basic web scraping. "Analyze" = full CI agent run.
- After triggering, poll `getClientIntelligence(clientId)` until `last_analyzed_at` changes (the analyze endpoint runs in background)
- Show loading state during analysis

#### 1b. Add Profile Completeness indicator to header
- Show a circular progress or bar showing `profile_completeness` (0-100) with label (Poor/Fair/Good/Excellent)
- Thresholds: Poor (<30), Fair (30-59), Good (60-79), Excellent (80+)
- Only show when CI agent has run (`last_analyzed_at` is not null)

#### 1c. Add "Intelligence" tab to the page
- File: `apps/workbench/app/clients/[id]/page.tsx` — currently has 2 tabs (Overview, Projects)
- Add a third tab: "Intelligence" with icon `Brain` from lucide-react
- This tab should show the CI agent output in organized sections

#### 1d. Build ClientIntelligenceTab component
- New file: `apps/workbench/app/clients/[id]/components/ClientIntelligenceTab.tsx`
- Fetch data via `getClientIntelligence(clientId)` (already in `lib/api.ts` line 2943)
- The response shape is `ClientIntelligenceProfile` (defined in `lib/api.ts` line 2899)

**Sections to display:**

1. **Profile Completeness** — 8-section breakdown as a horizontal bar chart or progress bars
   - firmographics (15 pts), stakeholder_map (20), organizational_context (15), constraints (15), vision_strategy (10), data_landscape (10), competitive_context (10), portfolio_health (5)

2. **Vision Synthesis** — `sections.vision` (text block, may be long)

3. **Organizational Context** — `sections.organizational_context` (JSONB with keys: decision_making_style, change_readiness, political_dynamics, etc.)

4. **Constraints** — `sections.constraints` array with title, description, category, severity, source, impacts
   - Show as cards grouped by category
   - Severity badge (high = red-ish neutral, medium = gray, low = light gray)
   - IMPORTANT: Use only neutral gray tones for badges per brand guide, no colored badges

5. **Role Gaps** — `sections.role_gaps` array with role, why_needed, urgency, which_areas
   - Show as a list with urgency indicator

6. **Competitors & Growth** — Already shown on Overview tab, but include here too for completeness with any additional CI context

#### 1e. Update TypeScript types
- File: `apps/workbench/types/workspace.ts` lines 1088-1129
- `ClientSummary` is missing CI agent fields. Add:
  ```typescript
  profile_completeness?: number | null
  constraint_summary?: Record<string, unknown> | null
  role_gaps?: Record<string, unknown> | null
  vision_synthesis?: string | null
  organizational_context?: Record<string, unknown> | null
  last_analyzed_at?: string | null
  ```
- `ClientDetail` extends `ClientSummary` so it inherits these

---

### Task 2: Align Client Portal with Client Intelligence

**Problem:** The portal (`/portal/[projectId]`) shows project context forms but doesn't surface any CI agent intelligence. Clients should see a high-level company profile section that reflects what the system knows about them.

**What to add:**

#### 2a. Understand current portal structure
- Portal pages: `apps/workbench/app/portal/[projectId]/page.tsx`
- Portal layout: `apps/workbench/app/portal/[projectId]/layout.tsx`
- Portal prototype page: `apps/workbench/app/portal/[projectId]/prototype/page.tsx`
- Backend: `app/api/client_portal.py` — has dashboard, info requests, project context, chat
- Auth: Token-based via `require_project_access` middleware

#### 2b. Add company context section to portal dashboard
- The portal dashboard endpoint already returns project info
- Need: A new endpoint or extend existing to return sanitized client intelligence for portal display
- Client-facing view should show: company summary, vision synthesis (if confirmed), and any open questions the CI agent flagged for client input
- Do NOT expose raw constraints/role_gaps to clients — those are consultant-facing

#### 2c. Add BRD summary view for portal
- Portal should let clients see a read-only BRD summary (features, personas, key workflows)
- Backend endpoint exists: `GET /projects/{id}/workspace/brd` — may need a portal-specific wrapper that respects token auth
- Create a simple read-only BRD view component for the portal

---

## Architecture Reference

### Backend Endpoints (already built)
```
POST /clients/{id}/enrich          # Basic web scraping enrichment
POST /clients/{id}/analyze         # Full CI agent analysis (background)
GET  /clients/{id}/intelligence    # Get CI agent profile + section scores
GET  /clients/{id}                 # Get client detail + projects

# Portal
GET  /portal/{project_id}/dashboard       # Portal dashboard
GET  /portal/{project_id}/info-requests   # Questions for client
POST /portal/{project_id}/context         # Client fills in context
POST /portal/{project_id}/chat            # AI chat (SSE streaming)

# BRD (project-scoped, needs portal wrapper if used)
GET  /projects/{id}/workspace/brd         # Full BRD data
GET  /projects/{id}/workspace/client-intelligence  # Merged client intel for project
```

### Frontend API Client (already built)
```typescript
// In lib/api.ts
enrichClient(clientId)                    // line ~2397
analyzeClient(clientId)                   // line 2938
getClientIntelligence(clientId)           // line 2943
getProjectClientIntelligence(projectId)   // line 2066
```

### Key Types (already defined)
```typescript
// In lib/api.ts (NOT workspace.ts)
interface ClientIntelligenceProfile {
  client_id: string
  name: string
  profile_completeness: number
  last_analyzed_at: string | null
  sections: {
    firmographics: { ... }
    constraints: Array<{ title, description, category, severity, source, impacts? }>
    role_gaps: Array<{ role, why_needed, urgency, which_areas? }>
    vision: string | null
    organizational_context: Record<string, unknown>
    competitors: Array<{ name, relationship? }>
    growth_signals: Array<{ signal, type }>
  }
  enrichment_status: string
}
```

### Existing Reference Component
- `apps/workbench/components/workspace/brd/components/ClientIntelligenceDrawer.tsx` — This drawer shows CI data in the BRD workspace context. Use it as a design reference but don't duplicate it. The client detail page should be the canonical full view.

### CI Agent Backend (do NOT modify)
- `app/agents/client_intelligence_agent.py` — OBSERVE→THINK→DECIDE→ACT loop
- `app/agents/client_intelligence_tools.py` — 10 tools
- `app/agents/client_intelligence_prompts.py` — System prompt
- `app/agents/client_intelligence_types.py` — Response types
- These are stable and working. Only touch frontend + types.

---

## Design Guidelines

Follow the brand guide strictly:

| Token | Value |
|-------|-------|
| Brand Green | `#3FAF7A` (primary actions, progress bars) |
| Brand Green Dark | `#25785A` (hover states) |
| Brand Navy | `#0A1E2F` (dark headers if needed) |
| Page Background | `#F4F4F4` |
| Card | `bg-white rounded-2xl border border-[#E5E5E5] shadow-md p-6` |
| Text Primary | `#333333` |
| Text Secondary | `#666666` |
| Text Muted | `#999999` |
| Borders | `#E5E5E5` |
| Badge (neutral) | `bg-[#F0F0F0] text-[#666666]` |
| Badge (positive) | `bg-[#E8F5E9] text-[#25785A]` |
| Font sizes | Labels: `text-[11px]`, Body: `text-[13px]`, Headings: `text-[14px]` |
| Buttons | `rounded-xl px-6 py-3` or `px-4 py-2` for compact |
| Icons | Lucide React, outline style, `w-3.5 h-3.5` or `w-4 h-4` |

**Rules:**
- NEVER use colored (yellow/orange/blue/purple) badges — only neutral gray or brand green
- Cards: always `rounded-2xl`, `shadow-md`, `border-[#E5E5E5]`
- Match the existing `ClientOverviewTab.tsx` patterns (InfoRow, MaturityBadge components)
- Use `text-[11px] text-[#999] font-medium uppercase tracking-wide` for section labels

---

## File Map

### Files to CREATE:
- `apps/workbench/app/clients/[id]/components/ClientIntelligenceTab.tsx`

### Files to MODIFY:
- `apps/workbench/app/clients/[id]/page.tsx` — add Intelligence tab
- `apps/workbench/app/clients/[id]/components/ClientHeader.tsx` — add Analyze button + completeness badge
- `apps/workbench/types/workspace.ts` — add CI agent fields to ClientSummary
- `apps/workbench/app/portal/[projectId]/page.tsx` — add company context section

### Files to READ (reference only):
- `apps/workbench/app/clients/[id]/components/ClientOverviewTab.tsx` — design patterns
- `apps/workbench/components/workspace/brd/components/ClientIntelligenceDrawer.tsx` — data display reference
- `apps/workbench/lib/api.ts` — API functions (lines 2895-2944)
- `app/api/clients.py` — backend endpoints
- `app/api/client_portal.py` — portal endpoints

---

## Order of Operations

1. **Update types** (workspace.ts) — add CI fields to ClientSummary
2. **Build ClientIntelligenceTab** — new component showing CI data
3. **Update page.tsx** — add Intelligence tab, wire it up
4. **Update ClientHeader** — add Analyze button + completeness indicator
5. **Test** the full flow: Enrich → Analyze → view Intelligence tab
6. **Portal: company context** — add summary section to portal dashboard
7. **Portal: BRD read-only view** — if time permits

---

## What NOT to Do

- Do NOT modify any backend Python files (agents, API routes, DB layer) — everything needed is already built
- Do NOT restructure the existing Overview tab — it works fine for basic enrichment
- Do NOT add WebSocket/real-time infrastructure — use polling after analyze trigger
- Do NOT add colored severity badges — use neutral gray tones only
- Do NOT import from `schemas_brd.py` in any new schema files (circular import risk)
- Do NOT add new npm dependencies unless absolutely necessary
