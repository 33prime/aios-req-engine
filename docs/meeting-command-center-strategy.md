# Meeting Command Center — Strategy Doc

## Status: Planned (tabled for now — current implementation works)

## Vision

The meeting detail page becomes a **mission control** that automatically shifts between pre-call and post-call states based on meeting status. Pre-call is a consultant prep playbook. Post-call is a debrief that maps outcomes back to what was planned.

## Current State (Working)

- Left panel: Discovery themes, stakeholder briefing (live), focus areas
- Right panel: Intelligence hub (analysis, recording, transcript tabs)
- Stakeholder briefing pulls live enrichment data (not stale brief snapshot)
- Discovery themes are workflow-first ("Map X", "Explore X", "Uncover X")
- No awareness of meeting lifecycle — same view pre and post

## The Problem

1. Discovery themes become stale after the call — they're missions, not results
2. Post-call intelligence (transcript, feature insights, consultant performance) has no relationship to pre-call planning
3. Consultant can't see "what changed" — no delta between before/after
4. No tactical landscape briefing to get the consultant up to speed fast

---

## Design: Two-Phase Auto-Switch

```
Meeting status: scheduled/pending → PRE-CALL view
Meeting status: completed/analyzed → POST-CALL view
No transcript available           → POST-CALL with "No analysis available" state
```

Auto-switch based on meeting status. Include a toggle to view prep notes from post-call view ("View prep notes" link at top).

### Phase 1: Pre-Call — Consultant Prep Playbook

**Left Panel — "Your Mission"**

1. **Landscape Briefing** (NEW)
   - Quick tactical context on the project domain (e.g., RevOps landscape)
   - Key industry terms, common pain patterns, relevant benchmarks
   - What this client's competitors/peers are doing
   - Generated from project signals + research docs + client profile
   - Goal: consultant walks in fluent in the client's world in 60 seconds

2. **Discovery Themes** (existing, working)
   - Workflow-first missions: Map, Uncover, Explore
   - Each theme: context, discovery question, what it explores, evidence, confidence

3. **Stakeholder Briefing** (existing, working — live data)
   - Approach strategy (always visible)
   - Win conditions, concerns, decision power, domain expertise
   - Expandable detail sections
   - Completeness ring showing intel quality

4. **Knowledge Map** (NEW — future)
   - What we know (high confidence) vs. what we need (low confidence)
   - Visual representation of explored vs. unexplored territory
   - Links to evidence for what we know

**Right Panel — Evidence & Context**
- Knowledge graph visualization
- Belief confidence explorer
- Evidence trail for each theme
- (Or keep current intelligence hub tabs)

### Phase 2: Post-Call — Mission Debrief

**Left Panel — "What Happened"**

1. **Theme Outcomes** (discovery themes → resolved missions)
   - Each pre-call theme gets a resolution:
     - `explored` — we got the information we needed
     - `partially_explored` — some progress, follow up needed
     - `not_addressed` — didn't get to it
     - `redirected` — conversation went a different direction, new insight
   - Link to transcript moments where each theme was addressed
   - New intelligence extracted per theme

2. **What We Learned** (NEW)
   - New facts/beliefs extracted from the call
   - Features confirmed, challenged, or newly discovered
   - Workflow understanding delta (confidence before → after)
   - Surprises — things that contradicted our assumptions

3. **Stakeholder Reactions** (from call analysis)
   - Per-stakeholder: engagement level during call, key quotes
   - Feature insights: excited/interested/confused/resistant per feature
   - Who talked most, who was quiet (talk ratio)
   - Aha moments flagged

4. **Intelligence Delta** (NEW)
   - Confidence scores before vs. after
   - Gaps closed vs. gaps remaining
   - New gaps discovered
   - Belief changes (what we thought vs. what we now know)

5. **Next Actions** (NEW)
   - Auto-generated from: unresolved themes + new gaps + commitments made
   - Follow-up items assigned to specific stakeholders
   - Recommended focus for next meeting

**Right Panel — Call Data**
- Full transcript with speaker attribution
- Recording playback
- Consultant performance scorecard
- Signal extraction results

---

## Landscape Briefing (Pre-Call Tactical Context)

Goal: Get the consultant fluent in the client's domain in 60 seconds.

**Data sources:**
- Project signals (transcripts, research docs already ingested)
- Client profile (industry, size, organizational context)
- Solution flow (what the proposed solution looks like)
- Research agent findings (if available)
- Feature set (what capabilities are being discussed)

**Content structure:**
```
LANDSCAPE: [Client Industry/Domain]
- What this space looks like right now (2-3 sentences)
- Common pain patterns in this domain
- Key terminology the client will use
- What peers/competitors are doing differently

THIS CLIENT:
- Where they are in their journey
- What's unique about their situation
- The strategic bet they're making
```

**Generation:** Single Haiku call with project context, cached per project (refresh on new signals).

---

## Technical Notes

### Auto-Switch Logic
```tsx
const meetingPhase = useMemo(() => {
  if (meeting.status === 'completed' || callDetails?.recording?.status === 'complete') {
    return 'post-call'
  }
  return 'pre-call'
}, [meeting.status, callDetails])
```

### Theme → Outcome Mapping
- Store theme outcomes in `call_strategy_briefs.goal_results` (existing field, currently unused for themes)
- Or add `theme_outcomes` JSONB field to briefs
- Post-call analysis pipeline maps transcript segments → theme coverage

### Stakeholder Reaction Mapping
- Already have `call_feature_insights` with per-feature reactions
- Already have `call_content_nuggets` with speaker-attributed quotes
- Need to map stakeholder names → transcript speakers (speaker_map in transcript)
- Aggregate: engagement timeline segments per stakeholder

### No-Transcript Fallback
```tsx
if (meetingPhase === 'post-call' && !callDetails?.transcript) {
  return <NoAnalysisState onViewPrepNotes={() => setShowPrep(true)} />
}
```

---

## Implementation Order (When We Pick This Up)

1. **Phase switch UI** — tabs or auto-switch based on meeting status
2. **Theme outcomes** — resolution status on each discovery theme post-call
3. **Stakeholder reactions** — map call analysis → stakeholder cards
4. **Intelligence delta** — confidence before/after comparison
5. **Landscape briefing** — tactical domain context (Haiku generation)
6. **Next actions** — auto-generated follow-ups
7. **Knowledge map** — visual explored/unexplored territory

---

## Open Questions

- Should the landscape briefing be project-level (cached) or meeting-specific?
- How to handle multi-meeting arcs? (Theme from meeting 1 resolved in meeting 3)
- Should post-call debrief auto-generate or require consultant trigger?
- Integration with the prototype pipeline — do call insights feed back into prototype refinement?

---

*Created: 2026-03-05*
*Status: Tabled — current pre-call implementation working (discovery themes + live stakeholder briefing)*
