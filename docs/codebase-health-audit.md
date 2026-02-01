# Codebase Health Audit

> Generated 2026-01-31 after dead code cleanup (commit e6bbff9)

---

## 1. Broken Imports: CLEAN

TypeScript compiles with zero errors. All 79 deleted component files have no remaining references. The prior cleanup was thorough.

---

## 2. Backend Tests: NEEDS WORK

| Metric | Value |
|--------|-------|
| Passed | 408 |
| Failed | 79 |
| Errors | 31 |
| Collection failures | 2 |
| **Pass rate** | **78.8%** |

### Root Causes

- **Schema drift** — `BuildStateOutput`, `EvidenceRef`, `ResearchReport` schemas changed but tests weren't updated
- **Stale imports** — Tests still reference removed subsystems (reconcile, red team, insights, `enrich_prd_graph`)
- **DB constraint changes** — New check constraints reject old test data
- **API signature changes** — `smart_upsert_stakeholder()`, `create_business_driver()` changed signatures

### Broken Test Files

| File | Root Cause |
|------|-----------|
| `tests/test_baseline_enforcement_mock.py` | Imports `check_baseline_gate` from `app.api.projects` (no longer exported) |
| `tests/test_prd_enrich_basic.py` | Imports `app.graphs.enrich_prd_graph` (module removed) |
| `tests/test_reconcile_agent_mock.py` (3 errors) | References `app.api.reconcile` (removed) |
| `tests/test_phase2b_behavioral.py` (4 errors) | References `app.db.insights` (removed) |
| `tests/test_reconcile_prompt_inputs_mock.py` (5 errors) | References `reconcile_inputs.list_prd_sections` (removed) |
| `tests/test_redteam_agent_mock.py` (4 errors) | `EvidenceRef` type changed (UUID vs str for `chunk_id`) |
| `tests/test_baseline_endpoints_mock.py` (6 errors) | References `app.api.projects.evaluate_baseline` and `update_gate_config` (removed) |
| `tests/test_ingest_research_endpoint_mock.py` (6 errors) | References `app.api.research.check_baseline_gate` (removed) |
| `tests/test_build_state_agent_mock.py` (3 errors) | `BuildStateOutput` schema changed (now requires `personas` field) |

### Coverage Gaps

| Layer | Modules | Tested | Untested | Coverage |
|-------|---------|--------|----------|----------|
| `app/db/` | 53 | 5 | 48 | 8% |
| `app/chains/` | 57 | 4 | 53 | 7% |
| `app/context/` | 8 | 0 | 8 | 0% |
| `app/graphs/` | 11 | 3 | 8 | 27% |
| `app/api/` | 46 | 0 (HTTP-layer) | 46 | 0% |
| `app/agents/` | 14 | 3 | 11 | 21% |

---

## 3. Frontend/Backend API Sync

### Critical: Phantom Endpoint

`resendInvite` (`apps/workbench/lib/api.ts:459`) calls `POST /v1/admin/projects/{id}/members/{uid}/resend` — that route does not exist in the backend. Will 404 at runtime.

**Action**: Either implement the backend route in `app/api/admin.py` or remove the frontend function.

### Duplicate Function

`getProjectTasks` and `listTasks` both hit `GET /projects/{id}/tasks` with different TypeScript return types.

**Action**: Remove `getProjectTasks` and consolidate callers to `listTasks`.

### Backend-Only Endpoints (~100+)

Many backend endpoints have no caller in `api.ts`. Most are expected:
- Auth routes called from auth-specific frontend code
- Client portal routes called from the portal app
- Phase0 routes (`/ingest`, `/search`) called from tooling
- Chat routes called from the assistant component
- DI agent foundation extraction routes are backend-internal

### Route Duplication

Standalone routers for `stakeholders.py`, `business_drivers.py`, `competitor_refs.py`, `risks.py` have their own prefixed routes that overlap with routes in `state.py`. Neither set is called from `api.ts`.

---

## 4. Frontend Code Quality

### TypeScript `any` Usage (~80 instances)

**`types/api.ts`** (18 instances) — highest priority, propagates type-unsafety everywhere:
- `Job.input/output: any`
- `Feature.details/evidence: any`
- `Persona.demographics/psychographics: Record<string, any>`
- Various `settings`, `preferences`, `agenda`, `gates` fields

**`lib/api.ts`** (15 instances):
- `changes: Record<string, any>`, `answer_data: Record<string, any>`
- Several inline interface fields: `discovery_prep?: any`, `validation?: any`, `active_touchpoint: any`

**Components** (~47 instances), worst offenders:
- `TaskDetailModal.tsx` (7)
- `commands.ts` (5)
- `BusinessDriverCard.tsx` (5)
- `FeatureCard.tsx` (4)
- `PersonaModal.tsx` (3)

### Debug Console Statements (2 remaining)

| File | Line | Statement |
|------|------|-----------|
| `app/auth/page.tsx` | 41 | `console.error('❌ Auth error:', authError)` |
| `lib/assistant/commands.ts` | 1060 | `console.error('🧠 DI Agent error:', error)` |

Also: `components/auth/AuthProvider.tsx:93` has `console.log('Auth state changed:', event)` which fires on every auth event in production.

### Large Files (500+ lines)

| Lines | File |
|-------|------|
| 2,129 | `lib/assistant/commands.ts` |
| 2,026 | `lib/api.ts` |
| 1,572 | `components/workspace/panels/ContextPanel.tsx` |
| 1,270 | `app/projects/[projectId]/components/ChatPanel.tsx` |
| 856 | `components/workspace/WorkspaceChat.tsx` |
| 844 | `components/workspace/panels/EvidencePanel.tsx` |
| 683 | `components/workspace/CollaborationHub.tsx` |
| 627 | `lib/assistant/modes.ts` |
| 620 | `components/personas/PersonaModal.tsx` |
| 603 | `lib/assistant/context.tsx` |
| 591 | `components/profile/ProfileTab.tsx` |
| 566 | `app/projects/[projectId]/components/discovery-prep/DiscoveryPrepSection.tsx` |
| 517 | `lib/assistant/proactive.ts` |

### Deployment Risk

`NEXT_PUBLIC_ADMIN_API_KEY` in `.env.local` will be bundled into client-side JavaScript when `NEXT_PUBLIC_BYPASS_AUTH=true` is set. Gated by the bypass flag but the key is exposed in the client bundle.

### Clean Areas

- Zero TODO/FIXME/HACK comments
- No hardcoded secrets in source code
- Supabase anon key usage is correct (designed for client-side)
- Localhost fallbacks are standard dev patterns

---

## Recommended Priority Order

### P0: Fix Broken Tests
- Delete or fix 112 broken tests (79 failed + 31 errors + 2 collection failures)
- Tests referencing removed subsystems (reconcile, red team, insights) should be deleted
- Tests with schema drift should be updated to match current schemas
- Get to 100% pass rate on existing tests before adding new ones

### P1: Fix Phantom Endpoint
- Either implement `POST /admin/projects/{id}/members/{uid}/resend` in backend
- Or remove `resendInvite` from `api.ts` and any UI that calls it

### P2: Clean Up `any` Types
- Start with `types/api.ts` (18 instances) — these define the contract for everything
- Then `lib/api.ts` (15 instances)
- Then component-level `any` casts (~47 instances)

### P3: Remove Debug Logging
- Remove 2 emoji-prefixed console statements
- Gate `AuthProvider.tsx` auth state logging behind a debug flag or remove it

### P4: Large File Decomposition
- `commands.ts` (2,129 lines) — split by command category
- `api.ts` (2,026 lines) — split by domain (projects, features, collaboration, etc.)
- `ContextPanel.tsx` (1,572 lines) — extract sub-sections into child components

### P5: Increase Test Coverage
- Add HTTP-layer integration tests for critical API routes
- Add coverage for `app/db/` layer (currently 8%)
- Add coverage for `app/chains/` layer (currently 7%)
