# Meetings + Call Intelligence Integration Plan

**Created**: 2026-02-17
**Status**: Draft — awaiting implementation
**Source**: RTG Forge `call_intelligence` module + existing AIOS meetings infrastructure

## Context

AIOS has a partially built meetings backend (CRUD, Recall.ai bot deploy, Google Calendar sync, consent tracking) but **zero frontend** — no pages, no list views, no detail views. The existing recording pipeline is basic: Recall records → raw text transcript → optionally ingested as signal. There's no speaker diarization, no AI analysis, and no Deepgram integration.

The RTG Forge `call_intelligence` module provides the missing intelligence layer: Deepgram transcription (nova-2 with speaker diarization), multi-dimensional Claude analysis (engagement scoring, feature reactions, coaching, competitive intel), and a config-driven dimension pack system.

**Goal**: Merge the Forge module's intelligence capabilities into the existing AIOS meetings infrastructure and build the complete frontend — meetings page, detail view, transcript viewer, analysis panels, and auto note-taker flow.

---

## Existing Infrastructure (What We Have)

### Backend
- `meetings` table (migration 0057) — project-scoped with date/time, stakeholders, agenda, google_meet_link
- `meeting_bots` table (migration 0097) — Recall.ai bot lifecycle (deploying→recording→done)
- `communication_integrations` table — Google OAuth, calendar_sync_enabled, recording_default
- `meeting_agendas` table (migration 0013)
- `app/api/meetings.py` — 6 endpoints (list, upcoming, get, create, update, delete)
- `app/api/communications.py` — bot deploy/status/cancel, Google OAuth, consent
- `app/api/meeting_agendas.py` — agenda generation from confirmations
- `app/core/recall_service.py` — basic Recall.ai (deploy, status, transcript text, remove)
- `app/services/calendar_sync.py` — Google Calendar sync + auto-deploy bots
- `app/core/google_calendar_service.py` — Google Calendar API v3
- `app/chains/generate_meeting_agenda.py` — LLM agenda generation

### Frontend
- `RecordingToggle.tsx` — single component (bot deploy/cancel with status polling)
- Types in `api.ts`: `Meeting`, `MeetingBot`, `BotStatus`, `ConsentStatus`
- API client functions: `listMeetings`, `createMeeting`, `updateMeeting`, `deleteMeeting`, `deployBot`, `getBotStatus`, `cancelBot`
- **No pages, no routes, no list/detail views**

### Config
- `RECALL_API_KEY`, `RECALL_API_URL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `TOKEN_ENCRYPTION_KEY`
- **Missing**: `DEEPGRAM_API_KEY`, `MEETING_AGENDA_MODEL` (bug — referenced but not defined)

---

## RTG Forge `call_intelligence` Module (What It Provides)

### Pipeline
```
Record (Recall.ai) → Transcribe (Deepgram nova-2) → Analyze (Claude multi-dimensional) → Notify (Slack)
```

### 8 Database Tables
- `call_recordings` — recording metadata + status machine (8 states)
- `call_transcripts` — full text + speaker-diarized segments JSONB
- `call_analyses` — scores, timeline, summary, custom dimensions
- `call_feature_insights` — feature reactions + quotes
- `call_signals` — ICP/market signals (pain points, goals, budget)
- `call_coaching_moments` — performance feedback
- `call_content_nuggets` — reusable content extracts
- `call_competitive_mentions` — competitor tracking

### Analysis Engine
- 4 dimension packs: core (engagement, summary, talk ratio), sales (feature insights, signals, readiness), coaching (strengths, improvements, objections), research (content nuggets, competitive intel)
- Custom dimensions via config JSON
- Single Claude API call per analysis (~$0.05-0.10 per 30min call)

### Providers
- `RecallClient` — webhook verification, media URL extraction, duration computation
- `DeepgramClient` — httpx-based (no SDK), nova-2 with speaker diarization
- Slack notifications with template variables

---

## Architecture Decision: Two-Layer Bridge

```
meetings (scheduling)     call_recordings (intelligence)
┌─────────────────┐      ┌──────────────────────┐
│ title, date     │──FK──│ meeting_id            │
│ stakeholders    │      │ Recall bot lifecycle  │
│ agenda, status  │      │ Deepgram transcript   │
│ Google Calendar │      │ Claude analysis       │
│ Meet link       │      │ → Signal pipeline     │
└─────────────────┘      └──────────────────────┘
```

- `meetings` = scheduling layer (keep as-is)
- `call_recordings` = recording + intelligence layer (new, linked by `meeting_id` FK)
- Not all meetings are recorded; not all recordings need a meeting parent

---

## Phase 1: Database Migration

**File**: `migrations/0135_call_intelligence.sql`

### New tables (8, adapted from Forge)

| Table | Purpose | Key adaptations from Forge |
|-------|---------|---------------------------|
| `call_recordings` | Recording metadata + status machine | Add `meeting_id FK→meetings`, `project_id FK→projects`, `signal_id FK→signals`. Drop `contact_*` (use stakeholders instead) |
| `call_transcripts` | Full text + speaker-diarized segments JSONB | As Forge |
| `call_analyses` | Scores, timeline, summary, custom dimensions | As Forge |
| `call_feature_insights` | Feature reactions + quotes | Add `feature_id FK→features` (nullable, for linking to AIOS features) |
| `call_signals` | ICP/market signals from calls | As Forge (distinct from AIOS `signals` table) |
| `call_coaching_moments` | Performance feedback | As Forge |
| `call_content_nuggets` | Reusable content extracts | As Forge |
| `call_competitive_mentions` | Competitor tracking | As Forge |

### RLS policies (CRITICAL)

Every table gets `authenticated` + `service_role` full access policies (per migration 0107/0108/0113/0118 pattern — prevents silent empty queries in production).

### Backlink on meetings table

```sql
ALTER TABLE meetings ADD COLUMN IF NOT EXISTS call_recording_id UUID REFERENCES call_recordings(id) ON DELETE SET NULL;
```

---

## Phase 2: Backend — Config + Schemas + DB Layer

### 2a. Config additions (`app/core/config.py`)

```python
DEEPGRAM_API_KEY: str | None = None
DEEPGRAM_MODEL: str = "nova-2"
CALL_ANALYSIS_MODEL: str = "claude-sonnet-4-20250514"
CALL_ANALYSIS_MAX_TOKENS: int = 16384
CALL_ACTIVE_PACKS: str = "core,research"  # Not sales/coaching by default — AIOS is requirements tool, not sales CRM
MEETING_AGENDA_MODEL: str = "gpt-4.1-mini"  # Fix missing config bug
```

### 2b. Schemas (`app/core/schemas_call_intelligence.py`)

Port Forge `models.py` with AIOS adaptations:
- `CallRecordingStatus` enum (8 states: pending → bot_scheduled → recording → transcribing → analyzing → complete | skipped | failed)
- Request/Response models for all endpoints
- `TranscriptSegment`, `FeatureInsight`, `Signal`, `CoachingMoment`, `ContentNugget`, `CompetitiveMention`
- `AnalysisResult` (full structured output)
- `CallDetails` (aggregated transcript + analysis + child records)

### 2c. DB layer (`app/db/call_intelligence.py`)

Sync Supabase CRUD following `app/db/meetings.py` pattern:
- `create_call_recording(project_id, meeting_id, meeting_url)`
- `update_call_recording(recording_id, updates)`
- `get_call_recording(recording_id)` / `get_by_bot(recall_bot_id)` / `get_for_meeting(meeting_id)`
- `list_call_recordings(project_id, status, limit)`
- `save_transcript(recording_id, data)` / `get_transcript(recording_id)`
- `save_analysis(recording_id, data)` / `get_analysis(recording_id)`
- `save_feature_insights(...)` / `save_call_signals(...)` / `save_coaching_moments(...)` / `save_content_nuggets(...)` / `save_competitive_mentions(...)`
- `get_call_details(recording_id)` — aggregated query

---

## Phase 3: Backend — Providers + Analysis Engine

### 3a. Deepgram client (`app/services/deepgram_client.py`)

Port Forge `providers/deepgram.py`:
- Async httpx POST to Deepgram REST API (no SDK dependency)
- Input: audio URL → Output: `Transcript` model with segments + speaker_map
- Uses `DEEPGRAM_API_KEY` and `DEEPGRAM_MODEL` from config

### 3b. Enhanced Recall client

Extend existing `app/core/recall_service.py` with:
- `fetch_bot(bot_id)` — get full bot details including media URLs
- `extract_media_urls(bot_data)` — parse recording_url, audio_url, video_url
- `compute_duration(bot_data)` — calculate from status_changes timestamps
- `verify_webhook(body, headers, secret)` — HMAC-SHA256 signature verification

### 3c. Analysis chain (`app/chains/analyze_call.py`)

Port Forge `analysis/engine.py` + `analysis/dimensions.py`:
- `DIMENSION_PACKS` dict with 4 packs (core, sales, coaching, research)
- `resolve_dimensions(active_packs, custom_dims)` — returns dimension specs
- `analyze_call_transcript(transcript_text, dimensions, context_blocks, settings)` — single Claude API call
- Uses Anthropic client directly (matches `analyze_feature_overlay.py` pattern)
- Integrated with `log_llm_usage()` for cost tracking

### 3d. Call Intelligence service (`app/services/call_intelligence.py`)

Port Forge `service.py` to sync AIOS patterns:
- Uses `get_supabase()` sync client (not async injection)
- Pipeline methods:
  - `schedule_recording(meeting_id, meeting_url, project_id)` — create call_recording + deploy Recall bot
  - `handle_recall_event(event, bot_id, payload)` — webhook event handler (background task)
  - `transcribe_call(recording_id)` — fetch audio from Recall, transcribe via Deepgram
  - `analyze_call(recording_id, context_blocks)` — run dimension-pack analysis
  - `create_signal_from_call(recording_id)` — auto-create AIOS signal from transcript
- After analysis: auto-create signal via `insert_signal()` with `signal_type="transcript"`

---

## Phase 4: Backend — API Endpoints

### New router: `app/api/call_intelligence.py`

Prefix: `/call-intelligence`

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/recordings/schedule` | Schedule recording bot + create call_recording |
| `POST` | `/webhooks/recall` | Recall.ai webhook (returns 200 immediately, BackgroundTask) |
| `POST` | `/recordings/{id}/analyze` | Trigger (re-)analysis |
| `GET` | `/recordings` | List recordings (`project_id` query param) |
| `GET` | `/recordings/{id}` | Get single recording |
| `GET` | `/recordings/{id}/details` | Full analysis details (transcript + analysis + child records) |
| `POST` | `/recordings/{id}/create-signal` | Create AIOS signal from transcript |

### Extend existing `app/api/meetings.py`

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/meetings/{id}/recording` | Get call_recording linked to meeting |
| `POST` | `/meetings/{id}/record` | One-click: deploy bot + create call_recording |

### Register in `app/api/__init__.py`

```python
from app.api import call_intelligence
router.include_router(call_intelligence.router, tags=["call_intelligence"])
```

### Webhook design

```
POST /call-intelligence/webhooks/recall
  → verify signature (if RECALL_WEBHOOK_SECRET set)
  → parse bot_id + event from payload
  → BackgroundTask: process_recall_event()
      → "recording" events: update status
      → "done" event: fetch media → Deepgram transcribe → Claude analyze → create signal → notify
      → "error/failed" events: update status + error_log
```

---

## Phase 5: Frontend — Types + API Client

### Types additions (`apps/workbench/types/api.ts`)

- `CallRecordingStatus` type union (8 states)
- `CallRecording` interface (id, project_id, meeting_id, status, recall_bot_id, recording_url, audio_url, video_url, duration_seconds, signal_id)
- `TranscriptSegment` interface (speaker, text, start, end)
- `CallTranscript` interface (full_text, segments, speaker_map, word_count, duration_seconds)
- `CallAnalysis` interface (engagement_score, talk_ratio, engagement_timeline, executive_summary, prospect_readiness_score, custom_dimensions)
- `CallFeatureInsight`, `CallSignalInsight`, `CoachingMoment`, `ContentNugget`, `CompetitiveMention`
- `CallDetails` aggregated interface

### API client additions (`apps/workbench/lib/api.ts`)

- `listCallRecordings(projectId, status?)` → `GET /call-intelligence/recordings`
- `getCallRecording(recordingId)` → `GET /call-intelligence/recordings/{id}`
- `getCallDetails(recordingId)` → `GET /call-intelligence/recordings/{id}/details`
- `scheduleCallRecording(data)` → `POST /call-intelligence/recordings/schedule`
- `analyzeCallRecording(recordingId, contextBlocks?)` → `POST /call-intelligence/recordings/{id}/analyze`
- `createSignalFromCall(recordingId)` → `POST /call-intelligence/recordings/{id}/create-signal`
- `getMeetingRecording(meetingId)` → `GET /meetings/{id}/recording`
- `startMeetingRecording(meetingId)` → `POST /meetings/{id}/record`

---

## Phase 6: Frontend — Pages + Components

### 6a. Navigation updates

**LayoutWrapper** (`components/LayoutWrapper.tsx`):
Add `isMeetingsPage` check to bypass app shell (follows `/people` and `/clients` pattern).

**AppSidebar** (`components/workspace/AppSidebar.tsx`):
Add `Meetings` nav item (Calendar icon from lucide-react) between People and Settings.

### 6b. Meetings List Page (`apps/workbench/app/meetings/page.tsx`)

Layout follows `/people` page pattern:
- `AppSidebar` + `marginLeft` offset
- Top nav: "Meetings" title, search, filters (project, type, status), date range, "Schedule Meeting" button
- **Upcoming section**: Next 5 meetings as `MeetingCard` components with countdown
- **Past/All section**: Paginated table/grid of meetings with analysis score badges

### 6c. Meeting Detail Page (`apps/workbench/app/meetings/[id]/page.tsx`)

Two-column layout:

**Left column (60%)**:
- Header: title, datetime, duration, type badge, status badge
- Participants: stakeholder chips (link to `/people/[id]`)
- Agenda section (if present)
- Transcript: `TranscriptViewer` component

**Right column (40%)**:
- Recording status card with `RecordingToggle`
- Analysis summary: engagement donut, talk ratio bar, executive summary
- Feature insights list (reaction badges + quotes)
- Call signals list (type badge, intensity bar)
- Coaching moments (collapsible by type)
- "Ingest as Signal" button

### 6d. New Components

All in `apps/workbench/components/meetings/`:

| Component | Purpose |
|-----------|---------|
| `MeetingCard.tsx` | List view card: type badge, title, datetime, duration, participants count, project name, recording indicator, analysis score |
| `MeetingCreateModal.tsx` | Modal form: title, project selector, date/time pickers, duration, type, stakeholder multi-select, Meet link, auto-record toggle |
| `TranscriptViewer.tsx` | Speaker-diarized display with colored labels, timestamps, search input, speaker filter, copy-to-clipboard |
| `AnalysisPanel.tsx` | Wrapper for all analysis sub-components |
| `EngagementScore.tsx` | Circular score display (0-10, color gradient) |
| `TalkRatioBar.tsx` | Horizontal stacked bar (presenter vs prospect %) |
| `EngagementTimeline.tsx` | Line chart (recharts) with annotated key moments |
| `FeatureInsightRow.tsx` | Feature name, reaction badge, quote, aha indicator |
| `CallSignalRow.tsx` | Signal type badge, title, intensity bar |
| `CoachingMomentRow.tsx` | Moment type, title, suggestion, quote |
| `MeetingsTopNav.tsx` | Search + filters bar for list page |

### 6e. Design tokens (brand guide compliance)

- Cards: `rounded-2xl`, `shadow-md`, white bg, `#E5E5E5` border
- Type badges: neutral gray (`#F0F0F0` bg, `#666666` text)
- Status badges: scheduled = brand green, completed = neutral gray, cancelled = muted
- Engagement score: brand green (7-10), neutral (4-6), muted red (1-3)
- Primary action button: `#3FAF7A` bg, `#25785A` hover
- Page bg: `#F4F4F4`

---

## Phase 7: Auto Note-Taker Pipeline

End-to-end automated flow:

```
Calendar Sync (cron every 15 min)
    │
    ▼
sync_user_calendar() — match Google Calendar events to AIOS meetings
    │
    ▼
auto_deploy_bots() [ENHANCE existing in calendar_sync.py]
    ├── Check meetings starting within 5 min with recording_enabled=true
    ├── deploy_bot() via Recall.ai
    ├── create_bot() in meeting_bots table
    └── create_call_recording() in call_recordings table ← NEW
    │
    ▼
Recall.ai Bot joins meeting, records
    │
    ▼
Recall webhook → POST /call-intelligence/webhooks/recall
    │
    ▼
BackgroundTask: process_recall_event()
    ├── "recording" → update call_recordings.status
    └── "done" →
         ├── Fetch media URLs from Recall API
         ├── Transcribe via Deepgram nova-2 (speaker diarization)
         ├── Save to call_transcripts
         ├── Run Claude analysis (dimension packs)
         ├── Save to call_analyses + child tables
         ├── Auto-create AIOS signal (signal_type="transcript")
         ├── Update meeting status → "completed"
         ├── Log LLM usage
         └── (Optional) Slack notification
```

---

## Implementation Order

| # | Phase | Files | Depends on |
|---|-------|-------|------------|
| 1 | Migration | `migrations/0135_call_intelligence.sql` | — |
| 2 | Config fix | `app/core/config.py` | — |
| 3 | Schemas | `app/core/schemas_call_intelligence.py` | — |
| 4 | DB layer | `app/db/call_intelligence.py` | Phase 1 |
| 5 | Deepgram client | `app/services/deepgram_client.py` | Phase 2 |
| 6 | Enhanced Recall | `app/core/recall_service.py` (extend) | Phase 2 |
| 7 | Analysis chain | `app/chains/analyze_call.py` | Phase 3 |
| 8 | Service layer | `app/services/call_intelligence.py` | Phases 4-7 |
| 9 | API endpoints | `app/api/call_intelligence.py` | Phase 8 |
| 10 | Register router | `app/api/__init__.py` | Phase 9 |
| 11 | Frontend types | `apps/workbench/types/api.ts` | — |
| 12 | Frontend API client | `apps/workbench/lib/api.ts` | Phase 11 |
| 13 | Navigation | `LayoutWrapper.tsx`, `AppSidebar.tsx` | — |
| 14 | Meeting components | `components/meetings/*.tsx` | Phase 12 |
| 15 | Meetings list page | `app/meetings/page.tsx` | Phases 13-14 |
| 16 | Meeting detail page | `app/meetings/[id]/page.tsx` | Phases 14-15 |
| 17 | Auto note-taker | `calendar_sync.py` enhancement | Phases 8-9 |

**Phases 1-3 and 11-13 can run in parallel (no dependencies).**

---

## Files to Create

```
migrations/0135_call_intelligence.sql
app/core/schemas_call_intelligence.py
app/db/call_intelligence.py
app/services/deepgram_client.py
app/services/call_intelligence.py
app/chains/analyze_call.py
app/api/call_intelligence.py
apps/workbench/app/meetings/page.tsx
apps/workbench/app/meetings/[id]/page.tsx
apps/workbench/components/meetings/MeetingCard.tsx
apps/workbench/components/meetings/MeetingCreateModal.tsx
apps/workbench/components/meetings/TranscriptViewer.tsx
apps/workbench/components/meetings/AnalysisPanel.tsx
apps/workbench/components/meetings/EngagementScore.tsx
apps/workbench/components/meetings/TalkRatioBar.tsx
apps/workbench/components/meetings/EngagementTimeline.tsx
apps/workbench/components/meetings/FeatureInsightRow.tsx
apps/workbench/components/meetings/CallSignalRow.tsx
apps/workbench/components/meetings/CoachingMomentRow.tsx
apps/workbench/components/meetings/MeetingsTopNav.tsx
```

## Files to Modify

```
app/core/config.py                             (add DEEPGRAM_*, CALL_*, MEETING_AGENDA_MODEL)
app/core/recall_service.py                     (add fetch_bot, extract_media, verify_webhook)
app/api/__init__.py                            (register call_intelligence router)
app/api/meetings.py                            (add /recording and /record endpoints)
app/services/calendar_sync.py                  (enhance auto_deploy_bots)
apps/workbench/types/api.ts                    (add call intelligence types)
apps/workbench/lib/api.ts                      (add call intelligence API functions)
apps/workbench/components/LayoutWrapper.tsx     (add isMeetingsPage bypass)
apps/workbench/components/workspace/AppSidebar.tsx  (add Meetings nav item)
```

---

## Verification

1. **Migration**: Apply 0135 to Supabase, verify tables + RLS policies via `execute_sql`
2. **Backend**: `uv run python -c "from app.core.schemas_call_intelligence import *; print('OK')"` — schemas import clean
3. **Webhook**: Deploy a test Recall bot, verify webhook fires and pipeline executes
4. **Deepgram**: Transcribe a test audio URL, verify speaker diarization output
5. **Analysis**: Run `analyze_call` on a test transcript, verify dimension results
6. **Frontend**: `cd apps/workbench && npx tsc --noEmit` — TypeScript check
7. **E2E**: Navigate to `/meetings`, create meeting, record, verify transcript + analysis display
8. **Signal pipeline**: Verify transcript auto-creates AIOS signal, enters fact extraction
