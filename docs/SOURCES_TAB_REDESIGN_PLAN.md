# Sources Tab Redesign - Implementation Plan

> **Vision**: A "Show Your Work" dashboard providing transparency into everything that informed the project, how it helped, and what's still needed.

---

## Table of Contents

1. [Design Overview](#design-overview)
2. [What's Being Replaced](#whats-being-replaced)
3. [New Architecture](#new-architecture)
4. [Implementation Phases](#implementation-phases)
5. [Task Breakdown](#task-breakdown)
6. [API Specifications](#api-specifications)
7. [Component Specifications](#component-specifications)
8. [Dependencies](#dependencies)

---

## Design Overview

### Tab Structure

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Sources                                                                  │
│ Here's everything that informed this project                            │
│                                                                         │
│ ┌─────────────────────────────────┐  ┌──────────┐  ┌──────────────────┐│
│ │ 🔍 Search across all sources... │  │ 52% ●●●○ │  │ + Upload         ││
│ └─────────────────────────────────┘  │ Strong   │  └──────────────────┘│
├─────────────────────────────────────────────────────────────────────────┤
│  [Documents]  [Signals]  [Research]  [Intelligence]  [Memory]           │
└─────────────────────────────────────────────────────────────────────────┘
```

### Tab Purposes

| Tab | Content | Key Features |
|-----|---------|--------------|
| **Documents** | Uploaded files (PDF, DOCX, etc.) | Cards with summary, usage stats, evidence badges, semantic search |
| **Signals** | Timeline of notes/emails/transcripts | Chronological, filter by type, shows entity impact |
| **Research** | External research & competitor data | Markdown display, copyable, source attribution |
| **Intelligence** | AI transparency & suggestions | Stats, activity feed, evidence quality, suggested sources |
| **Memory** | Project decisions/learnings/questions | Read-only markdown, "use chat to update" |

### Evidence Confidence Model

```
Client Confirmed:      100% (●●●●●)
Consultant Confirmed:   90% (●●●●○)
AI + Strong Evidence:   70% (●●●○○)
AI + Some Evidence:     50% (●●○○○)
AI Generated:           40% (●○○○○)
```

---

## What's Being Replaced

### Files to Remove/Archive

#### Frontend Components (apps/workbench/)

| File | Current Purpose | Replacement |
|------|-----------------|-------------|
| `app/projects/[projectId]/components/tabs/SourcesTab.tsx` | Main sources tab container | New `SourcesTabRedesign.tsx` |
| `app/projects/[projectId]/components/tabs/sources/SignalList.tsx` | Left column signal list | Replaced by sub-tabs |
| `app/projects/[projectId]/components/tabs/sources/SignalDetailView.tsx` | Right column with 4 sub-tabs (Details, Impact, Timeline, Analytics) | Functionality distributed across new tabs |
| `components/SignalInput.tsx` | Modal for adding signals | New inline signal input in Signals tab |

#### Features Being Removed

1. **Two-column layout** - Replaced with full-width tabbed interface
2. **Chunk-level display** - No longer showing raw chunks in UI (kept in backend)
3. **Signal detail sub-tabs** - Impact/Timeline/Analytics merged into Intelligence tab
4. **Portal response special grouping** - Simplified to chronological timeline

#### Features Being Preserved (Backend)

- All `signal_impact` tracking (used for usage stats)
- Chunk storage and embeddings (used for search)
- Timeline events API (used in Intelligence tab)
- Analytics API (used in Intelligence tab)

---

## New Architecture

### Component Hierarchy

```
SourcesTabRedesign/
├── SourcesHeader.tsx           # Search bar, evidence badge, upload button
├── SourcesTabBar.tsx           # Tab navigation (Documents, Signals, etc.)
├── tabs/
│   ├── DocumentsTab.tsx        # Document library with cards
│   │   ├── DocumentCard.tsx    # Individual document card
│   │   ├── DocumentFilters.tsx # Filter controls
│   │   └── DocumentSearch.tsx  # Search within documents
│   ├── SignalsTab.tsx          # Signal timeline
│   │   ├── SignalTimeline.tsx  # Timeline component
│   │   ├── SignalTimelineItem.tsx
│   │   └── SignalFilters.tsx   # Type filter chips
│   ├── ResearchTab.tsx         # Research library
│   │   └── ResearchCard.tsx    # Markdown research card
│   ├── IntelligenceTab.tsx     # AI transparency
│   │   ├── AIStatsGrid.tsx     # Stats cards
│   │   ├── AIActivityFeed.tsx  # Recent AI activity
│   │   ├── EvidenceQuality.tsx # Quality breakdown
│   │   └── SuggestedSources.tsx # What's missing
│   └── MemoryTab.tsx           # Project memory (read-only)
│       └── MemoryDisplay.tsx   # Markdown renderer
└── shared/
    ├── UsageBar.tsx            # Usage indicator bar
    ├── EvidenceBadge.tsx       # Confidence badge (●●●○)
    └── SourceTypeIcon.tsx      # Icon by source type
```

### Data Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Document       │────▶│  Signal          │────▶│  Signal Impact  │
│  Uploads        │     │  (with chunks)   │     │  (entity links) │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                       │                        │
        ▼                       ▼                        ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Documents Tab  │     │  Signals Tab     │     │  Intelligence   │
│  (cards, usage) │     │  (timeline)      │     │  (usage stats)  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

---

## Implementation Phases

### Phase 1: Foundation (Backend APIs)
**Duration**: ~1 day

- New/updated API endpoints for document summaries
- Source usage aggregation endpoint
- Evidence quality calculation endpoint
- Suggested sources tool integration

### Phase 2: Core Components
**Duration**: ~1.5 days

- SourcesHeader with global search
- SourcesTabBar navigation
- Shared components (UsageBar, EvidenceBadge, etc.)

### Phase 3: Documents Tab
**Duration**: ~1 day

- Document cards with summaries and usage
- Filtering and search
- Upload integration

### Phase 4: Signals Tab
**Duration**: ~0.5 day

- Timeline view with filters
- Signal type icons and badges

### Phase 5: Research Tab
**Duration**: ~0.5 day

- Research cards with markdown
- Copy functionality
- Source attribution

### Phase 6: Intelligence Tab
**Duration**: ~1 day

- AI stats grid
- Activity feed
- Evidence quality breakdown
- Suggested sources integration

### Phase 7: Memory Tab
**Duration**: ~0.5 day

- Read-only memory display
- Markdown rendering
- "Use chat to update" guidance

### Phase 8: Integration & Polish
**Duration**: ~0.5 day

- Global search across all tabs
- Tab state persistence
- Loading states and empty states
- Mobile responsiveness

---

## Task Breakdown

### Phase 1: Foundation (Backend APIs)

#### Task 1.1: Document Summary Endpoint
**Priority**: High | **Depends on**: None

```python
GET /v1/projects/{project_id}/documents/summary
```

Returns documents with:
- AI-generated summary (content_summary field)
- Usage count (from signal_impact)
- Contributed entities (features, personas, etc.)
- Evidence confidence level

**Files to modify**:
- `app/api/document_uploads.py` - Add summary endpoint
- `app/db/document_uploads.py` - Add usage aggregation query

---

#### Task 1.2: Source Usage Aggregation
**Priority**: High | **Depends on**: None

```python
GET /v1/projects/{project_id}/sources/usage
```

Returns per-source:
- Total usage count
- Usage by entity type
- Last used timestamp
- Entities contributed to

**Files to modify**:
- `app/api/signals.py` - Add usage aggregation endpoint
- `app/db/signals.py` - Add aggregation query

---

#### Task 1.3: Evidence Quality Endpoint
**Priority**: High | **Depends on**: None

```python
GET /v1/projects/{project_id}/evidence/quality
```

Returns:
- Breakdown by confirmation status (client, consultant, gap, AI)
- Percentage with strong evidence
- Entity counts per tier

**Files to create**:
- `app/api/evidence.py` - New evidence endpoints
- `app/db/evidence.py` - Evidence aggregation queries

---

#### Task 1.4: Suggested Sources Tool
**Priority**: Medium | **Depends on**: 1.3

Integrate with DI Agent as callable tool:
- Analyze project gaps
- Match gaps to document types
- Cross-reference with stakeholders
- Return prioritized suggestions

**Files to modify**:
- `app/agents/di_agent_tools.py` - Add suggest_sources tool
- `app/agents/di_agent_prompts.py` - Add tool definition

---

#### Task 1.5: Global Search Endpoint
**Priority**: High | **Depends on**: None

```python
GET /v1/projects/{project_id}/sources/search?q={query}
```

Unified search across:
- Documents (summary + content)
- Signals (content)
- Research (content)

Returns grouped results with relevance scores.

**Files to create**:
- `app/api/sources.py` - New unified sources API
- `app/db/sources.py` - Federated search query

---

### Phase 2: Core Components

#### Task 2.1: SourcesHeader Component
**Priority**: High | **Depends on**: 1.5

Features:
- Global search input
- Evidence quality mini-badge (clickable → Intelligence tab)
- Upload button

**Files to create**:
- `apps/workbench/app/projects/[projectId]/components/tabs/sources-redesign/SourcesHeader.tsx`

---

#### Task 2.2: SourcesTabBar Component
**Priority**: High | **Depends on**: None

Features:
- 5 tabs with counts
- Active state styling
- Tab persistence in URL

**Files to create**:
- `apps/workbench/app/projects/[projectId]/components/tabs/sources-redesign/SourcesTabBar.tsx`

---

#### Task 2.3: Shared Components
**Priority**: High | **Depends on**: None

Components:
- `UsageBar.tsx` - Horizontal bar showing usage percentage
- `EvidenceBadge.tsx` - Confidence indicator (●●●○)
- `SourceTypeIcon.tsx` - Icon mapping for source types

**Files to create**:
- `apps/workbench/app/projects/[projectId]/components/tabs/sources-redesign/shared/UsageBar.tsx`
- `apps/workbench/app/projects/[projectId]/components/tabs/sources-redesign/shared/EvidenceBadge.tsx`
- `apps/workbench/app/projects/[projectId]/components/tabs/sources-redesign/shared/SourceTypeIcon.tsx`

---

#### Task 2.4: Main Container Component
**Priority**: High | **Depends on**: 2.1, 2.2

Features:
- Tab routing
- State management
- Loading states

**Files to create**:
- `apps/workbench/app/projects/[projectId]/components/tabs/sources-redesign/SourcesTabRedesign.tsx`

---

### Phase 3: Documents Tab

#### Task 3.1: DocumentCard Component
**Priority**: High | **Depends on**: 2.3, 1.1

Features:
- File icon by type
- Title, date, page count
- Usage bar with count
- AI summary (2-3 lines)
- Contributed entities list
- Evidence badge

**Files to create**:
- `apps/workbench/app/projects/[projectId]/components/tabs/sources-redesign/documents/DocumentCard.tsx`

---

#### Task 3.2: DocumentFilters Component
**Priority**: Medium | **Depends on**: None

Filters:
- Document type (PDF, DOCX, etc.)
- Evidence level
- Sort (most used, recent, alphabetical)

**Files to create**:
- `apps/workbench/app/projects/[projectId]/components/tabs/sources-redesign/documents/DocumentFilters.tsx`

---

#### Task 3.3: DocumentsTab Container
**Priority**: High | **Depends on**: 3.1, 3.2, 1.1

Features:
- Search within documents
- Filter controls
- Grid layout
- Empty state
- Upload trigger

**Files to create**:
- `apps/workbench/app/projects/[projectId]/components/tabs/sources-redesign/documents/DocumentsTab.tsx`

---

### Phase 4: Signals Tab

#### Task 4.1: SignalTimelineItem Component
**Priority**: High | **Depends on**: 2.3

Features:
- Timeline marker with icon
- Date header
- Content card with type badge
- Impact summary (→ Created/Updated: X)

**Files to create**:
- `apps/workbench/app/projects/[projectId]/components/tabs/sources-redesign/signals/SignalTimelineItem.tsx`

---

#### Task 4.2: SignalFilters Component
**Priority**: Medium | **Depends on**: None

Filter chips:
- All
- Email
- Notes
- Transcripts
- Chat

**Files to create**:
- `apps/workbench/app/projects/[projectId]/components/tabs/sources-redesign/signals/SignalFilters.tsx`

---

#### Task 4.3: SignalsTab Container
**Priority**: High | **Depends on**: 4.1, 4.2

Features:
- Filter bar
- Timeline list
- Add note button
- Export option
- Empty state

**Files to create**:
- `apps/workbench/app/projects/[projectId]/components/tabs/sources-redesign/signals/SignalsTab.tsx`

---

### Phase 5: Research Tab

#### Task 5.1: ResearchCard Component
**Priority**: High | **Depends on**: 2.3

Features:
- Title with globe icon
- Source URLs
- Fetch date
- Markdown content area
- Copy button
- Usage summary

**Files to create**:
- `apps/workbench/app/projects/[projectId]/components/tabs/sources-redesign/research/ResearchCard.tsx`

---

#### Task 5.2: ResearchTab Container
**Priority**: High | **Depends on**: 5.1

Features:
- Research cards list
- Add research button
- Empty state

**Files to create**:
- `apps/workbench/app/projects/[projectId]/components/tabs/sources-redesign/research/ResearchTab.tsx`

---

### Phase 6: Intelligence Tab

#### Task 6.1: AIStatsGrid Component
**Priority**: High | **Depends on**: None

Stats cards:
- Features enriched
- Personas built
- Gap analyses
- Connections inferred

**Files to create**:
- `apps/workbench/app/projects/[projectId]/components/tabs/sources-redesign/intelligence/AIStatsGrid.tsx`

---

#### Task 6.2: AIActivityFeed Component
**Priority**: Medium | **Depends on**: None

Features:
- Recent AI actions list
- Timestamp per action
- Action description
- Left border accent

**Files to create**:
- `apps/workbench/app/projects/[projectId]/components/tabs/sources-redesign/intelligence/AIActivityFeed.tsx`

---

#### Task 6.3: EvidenceQuality Component
**Priority**: High | **Depends on**: 1.3

Features:
- Progress bars per tier
- Percentages
- Summary callout ("52% strong evidence")

**Files to create**:
- `apps/workbench/app/projects/[projectId]/components/tabs/sources-redesign/intelligence/EvidenceQuality.tsx`

---

#### Task 6.4: SuggestedSources Component
**Priority**: High | **Depends on**: 1.4

Features:
- Suggestion cards
- Impact description
- Upload button
- Ask Client button (→ Collaboration tab)

**Files to create**:
- `apps/workbench/app/projects/[projectId]/components/tabs/sources-redesign/intelligence/SuggestedSources.tsx`

---

#### Task 6.5: IntelligenceTab Container
**Priority**: High | **Depends on**: 6.1, 6.2, 6.3, 6.4

Layout:
- Stats grid (top)
- Two columns: Evidence Quality + Activity Feed
- Suggested Sources (bottom)

**Files to create**:
- `apps/workbench/app/projects/[projectId]/components/tabs/sources-redesign/intelligence/IntelligenceTab.tsx`

---

### Phase 7: Memory Tab

#### Task 7.1: MemoryDisplay Component
**Priority**: High | **Depends on**: None

Features:
- Read-only markdown renderer
- Warning banner ("Use chat to update")
- Last updated timestamp
- View history button (optional)

**Files to create**:
- `apps/workbench/app/projects/[projectId]/components/tabs/sources-redesign/memory/MemoryDisplay.tsx`

---

#### Task 7.2: MemoryTab Container
**Priority**: High | **Depends on**: 7.1

Features:
- Fetch memory from API
- Loading state
- Empty state

**Files to create**:
- `apps/workbench/app/projects/[projectId]/components/tabs/sources-redesign/memory/MemoryTab.tsx`

---

### Phase 8: Integration & Polish

#### Task 8.1: Global Search Integration
**Priority**: High | **Depends on**: 1.5, All tabs

Features:
- Search results overlay
- Grouped by source type
- Click to navigate to tab + item

---

#### Task 8.2: Tab State Persistence
**Priority**: Medium | **Depends on**: 2.4

Features:
- URL query param for active tab
- Restore tab on page load

---

#### Task 8.3: Loading & Empty States
**Priority**: Medium | **Depends on**: All tabs

Features:
- Skeleton loaders per tab
- Empty state illustrations
- Call-to-action buttons

---

#### Task 8.4: Mobile Responsiveness
**Priority**: Medium | **Depends on**: All tabs

Features:
- Stacked layout on mobile
- Tab scrolling
- Touch-friendly interactions

---

#### Task 8.5: Wire Up to Main App
**Priority**: High | **Depends on**: All tasks

Features:
- Replace old SourcesTab with new
- Update tab routing
- Test all flows

**Files to modify**:
- `apps/workbench/app/projects/[projectId]/components/ProjectTabs.tsx`

---

## API Specifications

### New Endpoints

#### GET /v1/projects/{project_id}/documents/summary

```typescript
interface DocumentSummaryResponse {
  documents: Array<{
    id: string
    original_filename: string
    file_type: string
    file_size_bytes: number
    page_count: number | null
    created_at: string
    content_summary: string | null
    usage_count: number
    contributed_to: {
      features: number
      personas: number
      vp_steps: number
      other: number
    }
    confidence_level: 'client' | 'consultant' | 'ai_strong' | 'ai_weak'
    processing_status: string
  }>
  total: number
}
```

#### GET /v1/projects/{project_id}/sources/usage

```typescript
interface SourceUsageResponse {
  sources: Array<{
    source_id: string
    source_type: 'document' | 'signal' | 'research'
    source_name: string
    total_uses: number
    uses_by_entity: {
      feature: number
      persona: number
      vp_step: number
      business_driver: number
    }
    last_used: string | null
    entities_contributed: string[] // entity IDs
  }>
}
```

#### GET /v1/projects/{project_id}/evidence/quality

```typescript
interface EvidenceQualityResponse {
  breakdown: {
    client_confirmed: { count: number, percentage: number }
    consultant_confirmed: { count: number, percentage: number }
    gap_analysis: { count: number, percentage: number }
    ai_generated: { count: number, percentage: number }
  }
  total_entities: number
  strong_evidence_percentage: number // client + consultant
  summary: string // "52% of entities have strong evidence"
}
```

#### GET /v1/projects/{project_id}/sources/search

```typescript
interface SourceSearchRequest {
  q: string
  types?: ('document' | 'signal' | 'research')[]
  limit?: number
}

interface SourceSearchResponse {
  results: {
    documents: Array<{
      id: string
      filename: string
      excerpt: string
      relevance: number
    }>
    signals: Array<{
      id: string
      source_label: string
      excerpt: string
      relevance: number
    }>
    research: Array<{
      id: string
      title: string
      excerpt: string
      relevance: number
    }>
  }
  total_results: number
}
```

#### POST /v1/projects/{project_id}/sources/suggest

```typescript
interface SuggestSourcesResponse {
  suggestions: Array<{
    document_type: string
    title: string
    description: string
    impact: string
    would_help: string[] // entity names
    likely_owner: {
      stakeholder_id: string | null
      stakeholder_name: string | null
      role: string | null
    } | null
    priority: 'high' | 'medium' | 'low'
  }>
  generated_at: string
}
```

---

## Component Specifications

### Design Tokens (from HTML mockup)

```css
:root {
  --primary: #009b87;
  --primary-hover: #007a6b;
  --gray-50: #FAFAFA;
  --gray-100: #F5F5F5;
  --gray-200: #E5E5E5;
  --gray-300: #D4D4D4;
  --gray-500: #737373;
  --gray-600: #525252;
  --gray-700: #404040;
  --gray-900: #171717;
  --emerald-50: #ecfdf5;
  --emerald-100: #d1fae5;
  --success-text: #065f46;
  --warning-bg: #fef3c7;
  --warning-text: #92400e;
}
```

### Component Styling Guidelines

1. **Cards**: `bg-gray-50 border border-gray-200 rounded-xl p-4`
2. **Section headers**: `text-lg font-semibold text-gray-900`
3. **Counts**: `bg-emerald-50 text-primary px-2 py-0.5 rounded-full text-xs font-semibold`
4. **Buttons**: Primary uses `bg-primary text-white`, Secondary uses `bg-white border border-gray-300`
5. **Usage bars**: `h-2 bg-gray-200 rounded-full` with `bg-primary` fill

---

## Dependencies

### Task Dependency Graph

```
Phase 1 (Backend)
├── 1.1 Document Summary ──────┐
├── 1.2 Source Usage ──────────┤
├── 1.3 Evidence Quality ──────┼──▶ 1.4 Suggested Sources
└── 1.5 Global Search ─────────┘

Phase 2 (Core)
├── 2.1 SourcesHeader ◀── 1.5
├── 2.2 SourcesTabBar
├── 2.3 Shared Components
└── 2.4 Main Container ◀── 2.1, 2.2

Phase 3 (Documents)
├── 3.1 DocumentCard ◀── 2.3, 1.1
├── 3.2 DocumentFilters
└── 3.3 DocumentsTab ◀── 3.1, 3.2

Phase 4 (Signals)
├── 4.1 SignalTimelineItem ◀── 2.3
├── 4.2 SignalFilters
└── 4.3 SignalsTab ◀── 4.1, 4.2

Phase 5 (Research)
├── 5.1 ResearchCard ◀── 2.3
└── 5.2 ResearchTab ◀── 5.1

Phase 6 (Intelligence)
├── 6.1 AIStatsGrid
├── 6.2 AIActivityFeed
├── 6.3 EvidenceQuality ◀── 1.3
├── 6.4 SuggestedSources ◀── 1.4
└── 6.5 IntelligenceTab ◀── 6.1-6.4

Phase 7 (Memory)
├── 7.1 MemoryDisplay
└── 7.2 MemoryTab ◀── 7.1

Phase 8 (Integration)
└── 8.5 Wire Up ◀── All tasks
```

### External Dependencies

- Existing `Markdown` component for rendering
- Existing `uploadDocument` API function
- Existing `getProjectMemory` API function
- Existing DI Agent infrastructure for suggested sources

---

## Files to Remove After Implementation

Once the new Sources tab is complete and tested:

```
# Frontend - Safe to remove
apps/workbench/app/projects/[projectId]/components/tabs/SourcesTab.tsx
apps/workbench/app/projects/[projectId]/components/tabs/sources/SignalList.tsx
apps/workbench/app/projects/[projectId]/components/tabs/sources/SignalDetailView.tsx
apps/workbench/components/SignalInput.tsx

# Keep but may need updates
apps/workbench/components/evidence/EvidenceChip.tsx  # May reuse
apps/workbench/components/evidence/EvidenceChain.tsx # May reuse
```

### Backend - No Removal Needed

All existing backend APIs and database tables remain. The new UI consumes existing data differently but doesn't require backend removal.

---

## Success Criteria

1. **Documents Tab**: Shows all uploaded documents with summaries, usage stats, and evidence badges
2. **Signals Tab**: Clean timeline view with filtering by type
3. **Research Tab**: Markdown cards with copy functionality
4. **Intelligence Tab**: Clear AI transparency with suggested sources
5. **Memory Tab**: Read-only memory display with clear update guidance
6. **Search**: Works across all source types with grouped results
7. **Performance**: Lazy loading per tab, no unnecessary API calls
8. **Mobile**: Responsive layout on all screen sizes

---

## Estimated Timeline

| Phase | Tasks | Duration |
|-------|-------|----------|
| Phase 1 | Backend APIs | ~1 day |
| Phase 2 | Core Components | ~1.5 days |
| Phase 3 | Documents Tab | ~1 day |
| Phase 4 | Signals Tab | ~0.5 day |
| Phase 5 | Research Tab | ~0.5 day |
| Phase 6 | Intelligence Tab | ~1 day |
| Phase 7 | Memory Tab | ~0.5 day |
| Phase 8 | Integration | ~0.5 day |
| **Total** | | **~6.5 days** |

---

*Document created: January 2025*
*Last updated: January 2025*
