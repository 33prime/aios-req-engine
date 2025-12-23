# Frontend Rebuild Plan: 4-Tab Consultant Workflow

## Executive Summary

Reorganize the Next.js workbench from multi-page navigation into a **unified 4-tab workspace** with a clean, status-driven design system. No backend logic changes—just reorganizing the UI to match the consultant-first workflow.

---

## Current State Analysis

### Existing Pages
```
/projects/[projectId]/
├── page.tsx                    → Dashboard (stats, agent runners)
├── features/page.tsx           → Features list
├── prd/page.tsx                → PRD sections
├── vp/page.tsx                 → Value Path steps
├── insights/page.tsx           → Red team insights
└── confirmations/page.tsx      → Client confirmations
```

### Existing Components
```
components/
├── FeatureDetailCard.tsx       → Feature details
├── PrdDetailCard.tsx           → PRD section details
├── VpDetailCard.tsx            → VP step details
├── InsightsDashboard.tsx       → Insights list
├── SignalInput.tsx             → Signal ingestion
└── ResearchIngest.tsx          → Research upload
```

### Key Functionality to Preserve
- Status tracking (draft, confirmed_consultant, needs_confirmation, confirmed_client)
- Evidence viewing (signal chunks)
- Agent runners (build, reconcile, red team, enrich)
- Signal/Research ingestion
- Confirmation management

---

## New Structure: 4-Tab Workspace

### Tab Architecture
```
/projects/[projectId]/
└── page.tsx (Main workspace with 4 tabs)
    ├── Tab 1: Product Requirements
    ├── Tab 2: Value Path
    ├── Tab 3: Insights
    └── Tab 4: Next Steps
```

### Two-Column Layout (All Tabs)
```
┌─────────────────────────────────────────────────────────────┐
│ Project Header + Tab Navigation                             │
├───────────────────┬─────────────────────────────────────────┤
│                   │                                         │
│  LIST (LEFT)      │  DETAIL (RIGHT)                         │
│  - Selectable     │  - Selected item details                │
│  - Status badges  │  - Evidence/enrichment                  │
│  - Minimal info   │  - Action buttons                       │
│                   │  - Status management                    │
│                   │                                         │
└───────────────────┴─────────────────────────────────────────┘
```

---

## Design System Implementation

### 1. Colors (Tailwind Classes)

```typescript
// Define in tailwind.config.js or use directly
const colors = {
  primary: '#044159',      // bg-[#044159], text-[#044159]
  accent: '#88BABF',       // bg-[#88BABF], text-[#88BABF]
  deepText: '#011F26',     // text-[#011F26]
  warmSand: '#F2E4BB',     // bg-[#F2E4BB]

  // UI Grays
  bgGray: '#FAFAFA',       // bg-[#FAFAFA]
  cardBorder: '#E5E5E5',   // border-[#E5E5E5]
  bodyText: '#4B4B4B',     // text-[#4B4B4B]
  supportText: '#7B7B7B',  // text-[#7B7B7B]
}
```

### 2. Typography Classes

```css
/* H1 - Page titles */
.heading-1 {
  font-size: 26px;
  font-weight: 600;
  color: #1D1D1F;
}

/* H2 - Tab titles, section headers */
.heading-2 {
  font-size: 20px;
  font-weight: 500;
  color: #044159;
}

/* Section headers */
.heading-section {
  font-size: 18px;
  font-weight: 600;
  color: #1D1D1F;
}

/* Body text */
.text-body {
  font-size: 16px;
  font-weight: 400;
  color: #4B4B4B;
}

/* Supporting text */
.text-support {
  font-size: 13px;
  font-weight: 400;
  color: #7B7B7B;
}
```

### 3. Status Badges

```typescript
const statusBadges = {
  ai_draft: {
    bg: 'bg-[#88BABF]/10',
    text: 'text-[#044159]',
    label: 'AI DRAFT'
  },
  needs_confirmation: {
    bg: 'bg-yellow-50',
    text: 'text-yellow-700',
    label: 'NEEDS CONFIRMATION'
  },
  confirmed_consultant: {
    bg: 'bg-blue-50',
    text: 'text-blue-700',
    label: 'CONFIRMED'
  },
  confirmed_client: {
    bg: 'bg-green-50',
    text: 'text-green-700',
    label: 'CONFIRMED (CLIENT)'
  }
}
```

### 4. Component Styles

```typescript
// Card (white background, subtle border)
const cardClass = "bg-white border border-[#E5E5E5] rounded-lg p-4 shadow-[0_1px_2px_rgba(0,0,0,0.04)]"

// Primary Button
const btnPrimary = "bg-[#044159] text-white px-4 py-2 rounded-lg hover:bg-[#033344] transition-colors"

// Secondary Button
const btnSecondary = "bg-[#F5F5F5] text-[#4B4B4B] px-4 py-2 rounded-lg hover:bg-[#E5E5E5] transition-colors"

// Outline Button
const btnOutline = "bg-white border border-[#044159] text-[#044159] px-4 py-2 rounded-lg hover:bg-[#044159]/5 transition-colors"
```

---

## Implementation Phases

### Phase 1: Design System Foundation
**Goal:** Set up the color palette, typography, and base components

**Files to Create:**
```
apps/workbench/
├── styles/
│   └── design-system.css          (Typography, custom utilities)
├── lib/
│   ├── design-tokens.ts           (Color constants, badge configs)
│   └── status-utils.ts            (Status badge helpers, mapping)
└── components/ui/
    ├── StatusBadge.tsx            (Reusable status badge)
    ├── Button.tsx                 (Primary, Secondary, Outline variants)
    ├── Card.tsx                   (Base card component)
    └── TwoColumnLayout.tsx        (List + Detail layout)
```

**Tasks:**
1. Create design tokens file with color constants
2. Add custom typography classes to globals.css
3. Build reusable StatusBadge component
4. Build reusable Button component (3 variants)
5. Build Card component
6. Build TwoColumnLayout component
7. Update tailwind.config.js with custom colors

**Acceptance Criteria:**
- All design tokens defined and exportable
- StatusBadge renders correct colors for all 4 statuses
- Buttons have correct hover states
- TwoColumnLayout responsive (stacks on mobile)

---

### Phase 2: Tab Navigation Shell
**Goal:** Create the main workspace with tab navigation (no content yet)

**Files to Create:**
```
apps/workbench/app/projects/[projectId]/
├── page.tsx                       (New main workspace)
└── components/
    ├── TabNavigation.tsx          (4-tab switcher)
    ├── WorkspaceHeader.tsx        (Project info + actions)
    └── tabs/
        ├── ProductRequirementsTab.tsx   (Empty shell)
        ├── ValuePathTab.tsx             (Empty shell)
        ├── InsightsTab.tsx              (Empty shell)
        └── NextStepsTab.tsx             (Empty shell)
```

**Tasks:**
1. Create new page.tsx with tab state management
2. Build TabNavigation component (4 tabs, active state)
3. Build WorkspaceHeader (project ID, research toggle, agent actions)
4. Create empty tab components (just placeholders)
5. Wire up tab switching with React state

**Acceptance Criteria:**
- Tabs switch correctly on click
- Active tab has visual indicator
- Header shows project info
- Agent action buttons present (non-functional yet)

---

### Phase 3: Tab 1 - Product Requirements
**Goal:** Migrate PRD sections into Tab 1 with two-column layout

**Files to Update/Create:**
```
apps/workbench/app/projects/[projectId]/components/tabs/
├── ProductRequirementsTab.tsx     (Update with full implementation)
└── prd/
    ├── PrdList.tsx                (Left column: selectable PRD sections)
    └── PrdDetail.tsx              (Right column: section detail + status)
```

**Tasks:**
1. Create PrdList component (left column)
   - Fetch PRD sections from API
   - Display as selectable list
   - Show status badges
   - Show section type (personas, key_features, etc.)

2. Create PrdDetail component (right column)
   - Display selected section details
   - Show enrichment data
   - Evidence viewing modal
   - Status update buttons (Confirm, Needs Confirmation)

3. Wire up two-column layout
4. Add "Enrich PRD" action to header
5. Implement status update logic

**Data Mapping:**
```typescript
// Map PRD section status to badge
section.status = "draft"                  → AI DRAFT badge
section.status = "confirmed_consultant"   → CONFIRMED badge
section.status = "needs_confirmation"     → NEEDS CONFIRMATION badge
section.status = "confirmed_client"       → CONFIRMED (CLIENT) badge
```

**Acceptance Criteria:**
- PRD sections load and display in list
- Clicking a section shows detail on right
- Status badges display correctly
- Consultant can confirm sections
- Consultant can mark sections as needing confirmation
- Evidence modal works

---

### Phase 4: Tab 2 - Value Path
**Goal:** Migrate VP steps into Tab 2 with two-column layout

**Files to Update/Create:**
```
apps/workbench/app/projects/[projectId]/components/tabs/
├── ValuePathTab.tsx               (Update with full implementation)
└── vp/
    ├── VpList.tsx                 (Left column: selectable VP steps)
    └── VpDetail.tsx               (Right column: step detail + enrichment)
```

**Tasks:**
1. Create VpList component (left column)
   - Fetch VP steps from API
   - Display as ordered list (step_index)
   - Show status badges
   - Show step label + brief description

2. Create VpDetail component (right column)
   - Display step details
   - Show enrichment sections:
     - Data schema (entities, fields, types)
     - Business logic
     - Transition logic
     - User benefit/pain
   - Evidence viewing
   - Status update buttons

3. Wire up two-column layout
4. Add "Enrich VP" action to header
5. Implement status update logic
6. Display VP completeness indicator

**Data Display:**
```typescript
// VP Step Card (left column)
<div>
  <span>Step {step.step_index}</span>
  <h3>{step.label}</h3>
  <StatusBadge status={step.status} />
  {step.enrichment && <CompletnessBadge />}
</div>

// VP Detail (right column)
<div>
  <h2>Step {step.step_index}: {step.label}</h2>
  <p>{step.description}</p>

  <Section title="User Benefit">
    {step.user_benefit_pain}
  </Section>

  <Section title="Data Schema">
    {step.enrichment?.data_schema}
  </Section>

  <Section title="Business Logic">
    {step.enrichment?.business_logic}
  </Section>

  <Section title="Transition Logic">
    {step.enrichment?.transition_logic}
  </Section>
</div>
```

**Acceptance Criteria:**
- VP steps load in order
- Step selection works
- Enrichment data displays properly
- Status badges work
- Completeness indicators show gaps

---

### Phase 5: Tab 3 - Insights
**Goal:** Migrate insights with consultant decision workflow

**Files to Update/Create:**
```
apps/workbench/app/projects/[projectId]/components/tabs/
├── InsightsTab.tsx                (Update with full implementation)
└── insights/
    ├── InsightList.tsx            (Left column: filterable insights)
    └── InsightDetail.tsx          (Right column: insight + actions)
```

**Tasks:**
1. Create InsightList component (left column)
   - Fetch insights from API
   - Filter by status (open, queued, applied, dismissed)
   - Filter by severity (critical, important, minor)
   - Filter by gate (completeness, validation, assumption, scope, wow)
   - Show severity badges
   - Show gate category

2. Create InsightDetail component (right column)
   - Display insight details (title, finding, why)
   - Show targets (VP steps, features, PRD sections)
   - Show evidence
   - Show gate category with explanation
   - Action buttons:
     - **Apply Internally** (consultant fixes without client)
     - **Needs Confirmation** (adds to Next Steps)
     - **Dismiss** (not applicable)

3. Wire up filtering
4. Add "Run Red Team" action to header
5. Implement insight actions (apply, confirm, dismiss)

**Insight Card Layout:**
```typescript
// Left column
<div className="insight-card">
  <div className="flex justify-between">
    <GateBadge gate={insight.gate} />
    <SeverityBadge severity={insight.severity} />
  </div>
  <h4>{insight.title}</h4>
  <p className="text-sm text-gray-600">
    {insight.targets.length} targets affected
  </p>
</div>

// Right column
<div className="insight-detail">
  <GateBadge gate={insight.gate} />
  <SeverityBadge severity={insight.severity} />

  <h2>{insight.title}</h2>

  <Section title="Finding">
    {insight.finding}
  </Section>

  <Section title="Why This Matters">
    {insight.why}
  </Section>

  <Section title="Affected Areas">
    {insight.targets.map(t => (
      <Badge>{t.kind}: {t.label}</Badge>
    ))}
  </Section>

  <Section title="Evidence">
    {insight.evidence.map(e => (
      <EvidenceCard chunk={e} />
    ))}
  </Section>

  <ActionButtons>
    <Button onClick={applyInternally}>Apply Internally</Button>
    <Button onClick={needsConfirmation}>Needs Confirmation</Button>
    <Button variant="outline" onClick={dismiss}>Dismiss</Button>
  </ActionButtons>
</div>
```

**Acceptance Criteria:**
- Insights load and filter correctly
- Severity badges display (critical=red, important=yellow, minor=gray)
- Gate badges display with tooltips
- "Apply Internally" calls /insights/{id}/apply
- "Needs Confirmation" calls /insights/{id}/confirm
- Filters work (status, severity, gate)

---

### Phase 6: Tab 4 - Next Steps
**Goal:** Consolidate all confirmations into client outreach

**Files to Update/Create:**
```
apps/workbench/app/projects/[projectId]/components/tabs/
├── NextStepsTab.tsx               (Update with full implementation)
└── next-steps/
    ├── ConfirmationList.tsx       (Left column: grouped confirmations)
    ├── ConfirmationDetail.tsx     (Right column: detail + resolution)
    └── OutreachGenerator.tsx      (Email/meeting generator)
```

**Tasks:**
1. Create ConfirmationList component (left column)
   - Fetch confirmations from API (status=open)
   - Group by source:
     - From PRD (needs_confirmation items)
     - From VP (needs_confirmation items)
     - From Insights (queued confirmations)
   - Show recommended channel (email vs meeting)
   - Show complexity score

2. Create ConfirmationDetail component (right column)
   - Display client-friendly prompt
   - Display detail text
   - Show metadata (source, targets, severity)
   - Resolution form:
     - Confirmed by: [email/call/doc]
     - Evidence: [text input or file upload]
     - Action buttons: Confirm, Reject, Modify

3. Create OutreachGenerator component
   - Batch selected confirmations
   - Generate email template OR meeting agenda
   - Show recommended channel
   - Copy to clipboard functionality

4. Wire up confirmation resolution
5. Implement batch outreach generation

**Confirmation Card:**
```typescript
// Left column
<div className="confirmation-card">
  <ChannelBadge channel={confirmation.metadata.recommended_channel} />
  <h4>{confirmation.prompt}</h4>
  <p className="text-sm">
    Source: {confirmation.metadata.source}
  </p>
  <ComplexityIndicator score={confirmation.metadata.complexity_score} />
</div>

// Right column
<div className="confirmation-detail">
  <h2>{confirmation.prompt}</h2>

  <Section title="Context">
    {confirmation.detail}
  </Section>

  <Section title="Recommended Approach">
    <ChannelBadge channel={confirmation.metadata.recommended_channel} />
    <p>{confirmation.metadata.channel_rationale}</p>
  </Section>

  <Section title="Resolution">
    <Select label="Confirmed via">
      <option>Email</option>
      <option>Call</option>
      <option>Meeting</option>
      <option>Document</option>
    </Select>

    <Textarea label="Evidence" />

    <FileUpload label="Attach evidence (optional)" />
  </Section>

  <ActionButtons>
    <Button onClick={confirm}>Confirm</Button>
    <Button onClick={reject}>Reject</Button>
    <Button variant="outline" onClick={modify}>Modify</Button>
  </ActionButtons>
</div>
```

**Outreach Generator:**
```typescript
<div className="outreach-generator">
  <h3>Generate Client Outreach</h3>

  <p>{selectedConfirmations.length} items selected</p>

  <RecommendationBadge>
    {hasHighComplexity ? 'Meeting Recommended' : 'Email Recommended'}
  </RecommendationBadge>

  <Tabs>
    <Tab label="Email Template">
      <EmailPreview confirmations={selectedConfirmations} />
      <Button onClick={copyEmail}>Copy Email</Button>
    </Tab>

    <Tab label="Meeting Agenda">
      <AgendaPreview confirmations={selectedConfirmations} />
      <Button onClick={copyAgenda}>Copy Agenda</Button>
    </Tab>
  </Tabs>
</div>
```

**Acceptance Criteria:**
- Confirmations load from all sources
- Grouping by source works
- Channel badges display correctly
- Resolution form works
- Status updates propagate to source entities
- Outreach generator creates readable templates
- Copy to clipboard works

---

### Phase 7: Header Actions & Polish
**Goal:** Wire up agent actions, signal input, and final polish

**Files to Update:**
```
apps/workbench/app/projects/[projectId]/
├── page.tsx                       (Add agent actions, signal input)
└── components/
    ├── WorkspaceHeader.tsx        (Wire up all actions)
    ├── SignalInputModal.tsx       (Modal for signal ingestion)
    └── AgentActionPanel.tsx       (Collapsed panel for agent runners)
```

**Tasks:**
1. Add Signal Input to header (modal)
2. Add Research Ingest to header (modal)
3. Wire up agent runners:
   - Build State
   - Reconcile
   - Red Team
   - Enrich PRD
   - Enrich VP
4. Add job polling and status toasts
5. Add baseline toggle (research access)
6. Add loading states for all async operations
7. Add error handling and user feedback
8. Polish animations and transitions
9. Mobile responsiveness
10. Keyboard navigation

**Header Layout:**
```typescript
<header className="workspace-header">
  <div className="flex items-center justify-between">
    <div>
      <h1>Project {projectId}</h1>
      <StatusIndicator baseline={baseline} />
    </div>

    <div className="actions">
      <Button onClick={openSignalInput}>Add Signal</Button>
      <Button onClick={openResearchIngest}>Add Research</Button>
      <DropdownMenu label="Run Agent">
        <MenuItem onClick={runBuildState}>Build State</MenuItem>
        <MenuItem onClick={runReconcile}>Reconcile</MenuItem>
        <MenuItem onClick={runRedTeam}>Red Team</MenuItem>
        <MenuItem onClick={enrichPrd}>Enrich PRD</MenuItem>
        <MenuItem onClick={enrichVp}>Enrich VP</MenuItem>
      </DropdownMenu>
      <Toggle checked={baseline} onChange={toggleBaseline}>
        Research Access
      </Toggle>
    </div>
  </div>
</header>
```

**Acceptance Criteria:**
- All agent actions work
- Signal/research input works
- Job polling shows progress
- Toasts show success/error
- Loading states everywhere
- Mobile responsive
- No console errors

---

### Phase 8: Migration & Cleanup
**Goal:** Remove old pages, update navigation, deploy

**Tasks:**
1. Archive old page files (don't delete yet)
   ```
   apps/workbench/app/projects/[projectId]/
   ├── _archive/
   │   ├── features/page.tsx
   │   ├── prd/page.tsx
   │   ├── vp/page.tsx
   │   ├── insights/page.tsx
   │   └── confirmations/page.tsx
   ```

2. Update any internal links that pointed to old pages
3. Remove old components that are no longer used
4. Update README with new architecture
5. Create user guide for new workflow
6. Test all flows end-to-end
7. Deploy to staging
8. Get user feedback
9. Deploy to production
10. Delete archived files after 2 weeks

**Final Testing Checklist:**
- [ ] All 4 tabs load correctly
- [ ] Two-column layout works
- [ ] Status badges display correctly
- [ ] Consultant can confirm items
- [ ] Consultant can mark items for confirmation
- [ ] Insights can be applied internally
- [ ] Insights can be sent to confirmations
- [ ] Next Steps batches confirmations
- [ ] Outreach generator works
- [ ] Evidence viewing works
- [ ] Agent runners work
- [ ] Signal/research input works
- [ ] Mobile responsive
- [ ] No accessibility issues
- [ ] Fast page loads (<2s)

---

## File Structure (Final)

```
apps/workbench/
├── styles/
│   └── design-system.css
├── lib/
│   ├── design-tokens.ts
│   ├── status-utils.ts
│   └── api.ts (existing)
├── components/
│   ├── ui/
│   │   ├── StatusBadge.tsx
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   └── TwoColumnLayout.tsx
│   └── (legacy components to deprecate)
└── app/
    └── projects/[projectId]/
        ├── page.tsx (NEW - main workspace)
        └── components/
            ├── TabNavigation.tsx
            ├── WorkspaceHeader.tsx
            ├── SignalInputModal.tsx
            ├── AgentActionPanel.tsx
            └── tabs/
                ├── ProductRequirementsTab.tsx
                │   └── prd/
                │       ├── PrdList.tsx
                │       └── PrdDetail.tsx
                ├── ValuePathTab.tsx
                │   └── vp/
                │       ├── VpList.tsx
                │       └── VpDetail.tsx
                ├── InsightsTab.tsx
                │   └── insights/
                │       ├── InsightList.tsx
                │       └── InsightDetail.tsx
                └── NextStepsTab.tsx
                    └── next-steps/
                        ├── ConfirmationList.tsx
                        ├── ConfirmationDetail.tsx
                        └── OutreachGenerator.tsx
```

---

## Data Flow Mapping

### Status Lifecycle
```
AI Draft
  ↓ (consultant confirms)
Confirmed (consultant)
  ↓ (consultant marks as needing client input)
Needs Confirmation → Creates confirmation item in Next Steps
  ↓ (consultant records client evidence)
Confirmed (client)
```

### Insight Workflow
```
Insight Generated (status=open)
  ↓
Consultant Reviews in Tab 3
  ↓
Decision:
├─ Apply Internally → status=applied (updates entities)
├─ Needs Confirmation → status=queued (creates confirmation)
└─ Dismiss → status=dismissed
```

### Next Steps Workflow
```
Confirmation Created (from PRD/VP/Insights)
  ↓
Appears in Tab 4 (Next Steps)
  ↓
Consultant batches confirmations
  ↓
Generate Email OR Meeting Agenda
  ↓
Reach out to client
  ↓
Record evidence → status=resolved → propagates to source entity
```

---

## API Endpoints Used

### Existing (No Changes)
```
GET  /v1/projects/{id}/baseline
PATCH /v1/projects/{id}/baseline

GET  /v1/features?project_id={id}
GET  /v1/prd-sections?project_id={id}
GET  /v1/vp-steps?project_id={id}
GET  /v1/insights?project_id={id}
GET  /v1/confirmations?project_id={id}

POST /v1/state/build
POST /v1/state/reconcile
POST /v1/agents/red-team
POST /v1/agents/enrich-prd
POST /v1/agents/enrich-vp

PATCH /v1/insights/{id}/apply
POST /v1/insights/{id}/confirm
PATCH /v1/confirmations/{id}/status

GET  /v1/jobs/{id}
```

### Status Update Pattern
```
// For PRD, VP, Features
PATCH /v1/{entity-type}/{id}
{
  "status": "confirmed_consultant" | "needs_confirmation" | "confirmed_client"
}
```

---

## Success Metrics

### Performance
- Page load: < 2 seconds
- Tab switch: < 200ms
- Status update: < 500ms

### UX
- Consultant can review 10 PRD sections in < 5 minutes
- Consultant can triage 20 insights in < 10 minutes
- Generating client outreach takes < 2 minutes

### Quality
- Zero console errors
- 100% mobile responsive
- WCAG 2.1 AA accessibility
- All status transitions work correctly

---

## Risks & Mitigation

### Risk: Complex state management across tabs
**Mitigation:** Use React Context for project-wide state, lift shared state to page.tsx

### Risk: Performance with large datasets (100+ insights)
**Mitigation:** Implement virtualization for lists, pagination

### Risk: Breaking changes to existing workflows
**Mitigation:** Keep old pages in _archive/ for 2 weeks, easy rollback

### Risk: Design system inconsistencies
**Mitigation:** Build atomic components first, use Storybook for component library

---

## Timeline Estimate

- **Phase 1:** Design System (3-4 hours)
- **Phase 2:** Tab Shell (2-3 hours)
- **Phase 3:** PRD Tab (4-5 hours)
- **Phase 4:** VP Tab (4-5 hours)
- **Phase 5:** Insights Tab (5-6 hours)
- **Phase 6:** Next Steps Tab (6-8 hours)
- **Phase 7:** Polish (4-5 hours)
- **Phase 8:** Migration (2-3 hours)

**Total: 30-40 hours** (1-2 weeks for single developer)

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Approve design system** (colors, typography, components)
3. **Set up development branch** (`feature/4-tab-workspace`)
4. **Start Phase 1** (design system foundation)
5. **Iterate with user feedback** after each phase

---

**Questions? Clarifications needed?**
Let me know if any phase needs more detail or if priorities should shift!
