# Canvas Views Evolution

## Current State

Discovery phase has two views:
- **BRD View** (default): Document-style, MoSCoW grouped, Notion-like UI
- **Canvas View**: DnD-based, persona row + journey flow, feature mapping

Toggle persists in localStorage (`discovery-view-mode`).

## Original Assumptions

1. Consultants prefer visual drag-drop over document editing
2. Journey flow (persona → step → features) is the natural mental model
3. Feature-to-step mapping via DnD is the primary interaction
4. Visual canvas matches how consultants think about requirements

## Evolution Timeline

### 2026-02-06 - Added BRD Canvas as Default View

**Trigger**: Hypothesis that document-style better matches:
- How consultants present to clients (PRD format)
- How clients review (reading, not dragging)
- How confirmation flows (section by section)

**Before**:
- Only `RequirementsCanvas` with DnD
- Persona row + Journey flow + Unmapped features pool
- Feature chips draggable between steps

**After**:
- `BRDCanvas` is default (Business Requirements Document style)
- Sections: Background, Pain Points, Goals, Vision, Success Metrics, Actors, Workflows, Requirements (MoSCoW), Constraints
- Each section has collapsible cards with evidence
- DnD for moving features between MoSCoW groups
- "Canvas View" toggle for legacy DnD view

**Learning**: TBD - need beta feedback to validate

**Evidence**: Commit cafb36b

**New Assumptions to Validate**:
- [ ] Consultants prefer reading/confirming over dragging
- [ ] MoSCoW grouping helps scope conversations
- [ ] Document view better matches client expectations
- [ ] Batch confirm (per section) is frequently used

### 2026-01-XX - Original Canvas Implementation

**Trigger**: Initial product vision - visual requirements workspace

**Before**: No discovery workspace

**After**:
- `RequirementsCanvas` component
- Three-part layout: Persona row, Journey flow, Unmapped pool
- DnD with `@dnd-kit/core`
- Feature chips show status, can drag to steps
- Persona colors auto-assigned

**Learning**:
- Visual mapping is powerful for understanding
- May be overwhelming for large projects
- DnD is fiddly on mobile/tablet

**Evidence**: Initial implementation

---

## Open Questions

1. Do consultants use BRD view or toggle to Canvas?
2. Which view produces faster confirmation completion?
3. Do clients prefer BRD-style or canvas-style reviews?
4. Is the MoSCoW grouping helpful or confusing?

## Related Features

- BRD-001 to BRD-013 (BRD View)
- DC-001 to DC-006 (Canvas View)
