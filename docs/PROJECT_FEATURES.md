# AIOS Feature Inventory

> **Last Updated**: 2026-02-06 (Manual)
> **Auto-Update**: Weekly via `/scripts/update-feature-inventory.ts`
> **Memory**: See `docs/feature-evolution/` for change history

## Purpose

This document serves as the canonical reference for all user-facing features in AIOS. Use it for:
- **Beta Testing**: Map feedback to specific features
- **Assumption Tracking**: Validate if features solve intended pains/goals
- **Memory**: Track how features evolved and why

---

## Primary User: The Consultant

**Role**: Requirements Engineer / Business Consultant
**Technical Level**: Non-technical (browser-based, no CLI)
**Core Job**: Translate client signals → validated requirements → prototype → handoff

### Consultant's Top Pains (What AIOS Solves)
| ID | Pain | Feature(s) That Address It |
|----|------|---------------------------|
| P1 | Discovery chaos (100s of emails, calls, scattered notes) | Signal Ingestion, Evidence Search, Source Attribution |
| P2 | Manual analysis bottleneck | AI Extraction, Build State, Auto-Enrichment |
| P3 | Can't verify AI accuracy | Evidence Tracing, Confirmation Queue, Status Badges |
| P4 | Prototype iteration loop is slow | Prototype Review, Feature Overlays, Code Update |
| P5 | Stakeholder alignment | Stakeholder Tracking, Who Would Know, Client Portal |
| P6 | Losing track of changes | Change Log, Memory Panel, Enrichment Revisions |

### Consultant's Goals
| ID | Goal | Feature(s) That Support It |
|----|------|---------------------------|
| G1 | Complete discovery in 2-4 weeks (not 6-8) | Automated Extraction, Readiness Gates |
| G2 | 90%+ requirements confirmed by client | Confirmation Workflow, Client Portal |
| G3 | Defend every feature with source evidence | Evidence Attribution, Field-Level Sourcing |
| G4 | Clear MVP scope prevents scope creep | MoSCoW Prioritization, BRD Canvas |
| G5 | Client says "you understand us" | Persona Extraction, Pain Point Analysis |
| G6 | Dev team receives complete, traceable spec | PRD Generation, Prototype Handoff |

---

## Feature Inventory by Phase

### PHASE: Overview
*"What's the status and what should I do next?"*

| Feature ID | Feature Name | Screen/Component | Solves Pain | Supports Goal | Assumptions |
|------------|--------------|------------------|-------------|---------------|-------------|
| OV-001 | Readiness Score | `OverviewPanel` > Readiness Card | P2, P6 | G1, G2 | Score reflects actual prototype-readiness |
| OV-002 | Status Narrative | `OverviewPanel` > Narrative | P6 | G1 | AI summary matches reality |
| OV-003 | Open Tasks | `OverviewPanel` > Task List | P1 | G1 | Tasks are actionable, not noise |
| OV-004 | Recommended Actions | `OverviewPanel` > Actions | P1 | G1 | AI recommends right next step |
| OV-005 | Phase Progress | `CollaborationHub` | P6 | G1 | Phases are meaningful milestones |

### PHASE: Discovery
*"What are we building and for whom?"*

#### Canvas View (Requirements Canvas)
| Feature ID | Feature Name | Screen/Component | Solves Pain | Supports Goal | Assumptions |
|------------|--------------|------------------|-------------|---------------|-------------|
| DC-001 | Pitch Line Editor | `StoryEditor` | P1 | G5 | One sentence captures essence |
| DC-002 | Persona Cards | `PersonaRow` | P2 | G5 | AI personas match real users |
| DC-003 | Journey Flow | `JourneyFlow` | P2 | G6 | Value path captures user flow |
| DC-004 | Feature DnD Mapping | `UnmappedFeatures` + `FeatureChip` | P2 | G4 | Drag-drop is intuitive |
| DC-005 | Persona Detail Drawer | `PersonaDetailDrawer` | P3 | G5 | Consultant can edit/validate |
| DC-006 | VP Step Detail Drawer | `VpStepDetailDrawer` | P3 | G6 | Step details are editable |

#### BRD View (Business Requirements Document)
| Feature ID | Feature Name | Screen/Component | Solves Pain | Supports Goal | Assumptions |
|------------|--------------|------------------|-------------|---------------|-------------|
| BRD-001 | Background Section | `BusinessContextSection` | P1 | G5 | Company context is captured |
| BRD-002 | Pain Points List | `BusinessContextSection` > Pains | P1 | G5 | Pains are real, not invented |
| BRD-003 | Goals List | `BusinessContextSection` > Goals | P1 | G5 | Goals match client priorities |
| BRD-004 | Vision Editor | `BusinessContextSection` > Vision | P1 | G5 | Vision is articulated clearly |
| BRD-005 | Success Metrics | `BusinessContextSection` > KPIs | P1 | G3 | Metrics are measurable |
| BRD-006 | Actors Section | `ActorsSection` | P2 | G5 | Personas shown in BRD context |
| BRD-007 | Workflows Section | `WorkflowsSection` | P2 | G6 | VP steps shown as workflows |
| BRD-008 | MoSCoW Requirements | `RequirementsSection` | P2 | G4 | Priority grouping helps scope |
| BRD-009 | Drag Between Priorities | `PriorityGroup` + DnD | P2 | G4 | Reprioritization is easy |
| BRD-010 | Constraints Section | `ConstraintsSection` | P1 | G6 | Constraints are tracked |
| BRD-011 | Confirm All Action | `SectionHeader` | P3 | G2 | Batch confirm saves time |
| BRD-012 | Evidence Citations | `EvidenceBlock` | P3 | G3 | Source is always visible |
| BRD-013 | Status Badges | `BRDStatusBadge` | P3, P6 | G2 | Status is clear at glance |

### PHASE: Build
*"Does the prototype match requirements?"*

| Feature ID | Feature Name | Screen/Component | Solves Pain | Supports Goal | Assumptions |
|------------|--------------|------------------|-------------|---------------|-------------|
| BD-001 | Prototype Frame | `PrototypeFrame` | P4 | G6 | iframe renders correctly |
| BD-002 | Feature Overlays | `FeatureOverlayPanel` | P4 | G3 | Overlays match features |
| BD-003 | Guided Tour | `TourController` | P4 | G6 | Tour covers key features |
| BD-004 | Contextual Questions | `ContextualSidebar` | P4 | G2 | Questions surface issues |
| BD-005 | Session Chat | `SessionChat` | P4 | G2 | Chat captures feedback |
| BD-006 | End Review → Synthesize | `BuildPhaseView` | P4 | G6 | Synthesis is accurate |
| BD-007 | Code Update Trigger | `BuildPhaseView` | P4 | G6 | Code changes are correct |
| BD-008 | Design Selection | `DesignSelectionModal` | P4 | G6 | Design prefs applied |

### CROSS-CUTTING: Confirmation
*"Is this AI output correct?"*

| Feature ID | Feature Name | Screen/Component | Solves Pain | Supports Goal | Assumptions |
|------------|--------------|------------------|-------------|---------------|-------------|
| CF-001 | Confirmation Queue | `PendingItemsModal` | P3 | G2 | Queue surfaces right items |
| CF-002 | Confirm Action | `ConfirmActions` | P3 | G2 | Single-click confirm works |
| CF-003 | Needs Review Action | `ConfirmActions` | P3 | G2 | Flags items for client |
| CF-004 | Batch Confirm | `SectionHeader` > Confirm All | P3 | G2 | Bulk operations work |

### CROSS-CUTTING: Evidence & Memory
*"Where did this come from? What changed?"*

| Feature ID | Feature Name | Screen/Component | Solves Pain | Supports Goal | Assumptions |
|------------|--------------|------------------|-------------|---------------|-------------|
| EV-001 | Evidence Panel | `EvidencePanel` | P1, P3 | G3 | All signals searchable |
| EV-002 | Source Attribution | `EvidenceBlock` | P3 | G3 | Chunk links to original |
| EV-003 | Memory Panel | `MemoryPanel` | P6 | G3 | Memory is useful, not noise |
| EV-004 | Evolution Tab | `EvolutionTab` | P6 | G3 | Change history is clear |
| EV-005 | Knowledge Graph | `GraphTab` | P6 | G3 | Connections are insightful |
| EV-006 | Context Window | `ContextWindowTab` | P3 | G3 | AI context is transparent |

### CROSS-CUTTING: Collaboration
*"How do I work with clients?"*

| Feature ID | Feature Name | Screen/Component | Solves Pain | Supports Goal | Assumptions |
|------------|--------------|------------------|-------------|---------------|-------------|
| CL-001 | Workspace Chat | `WorkspaceChat` | P1, P2 | G1 | Chat is powerful helper |
| CL-002 | File Drop Upload | `WorkspaceChat` | P1 | G1 | Drag-drop ingests files |
| CL-003 | Slash Commands | `WorkspaceChat` | P2 | G1 | Commands are discoverable |
| CL-004 | Collaboration Hub | `CollaborationHub` | P5 | G2 | Actions are context-aware |
| CL-005 | Prep Review Modal | `PrepReviewModal` | P5 | G2 | Prep package is complete |
| CL-006 | Client Invite | `ClientPortalModal` | P5 | G2 | Invite flow is smooth |
| CL-007 | Portal Sync | `PortalSyncIndicator` | P5 | G2 | Sync is reliable |

### CLIENT PORTAL
*"How do clients interact?"*

| Feature ID | Feature Name | Screen/Component | Solves Pain | Supports Goal | Assumptions |
|------------|--------------|------------------|-------------|---------------|-------------|
| PT-001 | Question Answering | `portal/[projectId]/page.tsx` | P5 | G2 | Clients answer questions |
| PT-002 | Document Upload | Portal Actions | P5 | G3 | Clients share evidence |
| PT-003 | Progress Tracking | Portal Header | P5 | G2 | Clients see progress |
| PT-004 | Prototype Review | `portal/[projectId]/prototype` | P4, P5 | G2 | Clients give feedback |

### SETTINGS & ADMIN
| Feature ID | Feature Name | Screen/Component | Solves Pain | Supports Goal | Assumptions |
|------------|--------------|------------------|-------------|---------------|-------------|
| ST-001 | Profile Settings | `/settings` > Profile | - | - | Profile is editable |
| ST-002 | Org Management | `/settings` > Organization | P5 | G5 | Team access is managed |
| ST-003 | Member Invites | `InviteMemberModal` | P5 | G5 | Invites work reliably |

---

## Backend Capabilities Reference

For each frontend feature, these backend capabilities power it:

| Feature Area | Backend Endpoints | LLM Chains | Graphs |
|--------------|-------------------|------------|--------|
| Signal Ingestion | `POST /ingest`, `/research/ingest` | - | `document_processing_graph` |
| Fact Extraction | `POST /extract-facts` | `extract_facts.py` | `extract_facts_graph` |
| State Building | `POST /state/build` | `build_state.py` | `build_state_graph` |
| Enrichment | `POST /agents/enrich-*` | `enrich_*.py` | `enrich_*_graph` |
| BRD Data | `GET /workspace/brd` | - | - |
| Confirmations | `GET/PATCH /confirmations/*` | - | - |
| Prototype | `POST /prototypes/generate` | `generate_v0_prompt.py` | `prototype_analysis_graph` |
| Sessions | `/prototype-sessions/*` | `synthesize_feedback.py` | - |
| Chat | `POST /chat` | `chat_context.py` | - |

---

## Feedback Mapping Template

When beta feedback comes in, map it using:

```markdown
**Feedback ID**: FB-001
**Source**: [User name, date]
**Raw Feedback**: "[exact quote]"

**Mapped To**:
- Feature ID: [e.g., BRD-008]
- Screen: [e.g., Discovery > BRD View]
- Component: [e.g., RequirementsSection]
- Specific Element: [e.g., MoSCoW dropdown]

**Type**: [Bug | Usability | Feature Request | Confusion]

**Assumption Challenged**:
- Pain: [which pain, if any]
- Goal: [which goal, if any]
- Original Assumption: [what we assumed]
- New Learning: [what we now know]

**Action**:
- [ ] Fix in UI
- [ ] Fix in backend
- [ ] Update assumption
- [ ] Needs more research
```

---

## Change Log

| Date | Change | Feature IDs | Why |
|------|--------|-------------|-----|
| 2026-02-06 | Added BRD Canvas | BRD-001 to BRD-013 | Replace DnD canvas with document-style BRD |
| 2026-02-06 | Initial inventory | All | Beta testing foundation |

---

## Memory: Feature Evolution

See `docs/feature-evolution/` for:
- `personas.md` - How persona extraction evolved
- `requirements.md` - How requirements capture evolved
- `prototype.md` - How prototype review evolved
- `confirmation.md` - How confirmation workflow evolved

Each file tracks:
1. Original assumption
2. Signals that challenged it
3. Changes made
4. Current state
