# Prototype Review Evolution

## Current State

Build phase allows consultants to:
1. Generate prototype from requirements (v0 prompt)
2. View prototype in iframe
3. Start review session
4. Take guided tour through features
5. Submit feedback via chat and questions
6. Trigger AI code updates
7. Iterate up to 3 sessions

## Original Assumptions

1. Prototypes help validate requirements visually
2. Consultants need guided tour (not self-exploration)
3. Feature overlays help connect UI to requirements
4. Iterative feedback produces better outcomes than waterfall
5. AI can understand and apply feedback to code

## Evolution Timeline

### 2026-01-XX - Prototype Sessions

**Trigger**: Need to track feedback across review cycles

**Before**: Single prototype, no session tracking

**After**:
- `prototype_sessions` table
- Session chat with context
- Feedback synthesis
- Code update trigger
- Up to 3 iterations per prototype

**Learning**: TBD

### 2026-01-XX - Feature Overlays

**Trigger**: Consultants couldn't tell which UI elements mapped to which features

**Before**: Raw prototype with no annotations

**After**:
- Bridge injection into prototype iframe
- `aios:show-radar` messages for feature highlighting
- Click feature → see overlay with details
- Tour steps mapped to feature IDs

**Learning**:
- Visual mapping is essential for review
- Bridge reliability varies by prototype framework

### 2026-01-XX - v0 Prompt Generation

**Trigger**: Need automated way to create prototypes from requirements

**Before**: Manual prototype creation

**After**:
- `generate_v0_prompt.py` chain
- Design selection modal (style, brand, inspirations)
- Prompt includes: features, personas, value paths, style guide
- Quality audit after generation

**Learning**:
- Prompt quality directly affects prototype quality
- Design preferences significantly impact output

---

## Open Questions

1. How many iterations are typical before "done"?
2. Do consultants use tour or free-explore more?
3. What types of feedback are most actionable?
4. How often do code updates break things?

## Related Features

- BD-001 to BD-008 (Build Phase)
- Backend: `/prototypes/*`, `/prototype-sessions/*`
