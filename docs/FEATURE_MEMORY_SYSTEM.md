# AIOS Feature Memory System

## Overview

This system maintains a living understanding of AIOS features:
1. **PROJECT_FEATURES.md** - Canonical feature inventory with feedback mapping
2. **feature-evolution/** - Memory of how/why features changed
3. **Weekly Diff Script** - Agent that analyzes changes and updates memory

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    WEEKLY CRON JOB                               │
│              (runs every Sunday 00:00 UTC)                       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                 scripts/weekly-feature-diff.ts                   │
├─────────────────────────────────────────────────────────────────┤
│ 1. Git diff last week's commits                                 │
│ 2. Identify changed files (components, endpoints, types)        │
│ 3. Call Claude to analyze: "What changed and WHY?"              │
│ 4. Update PROJECT_FEATURES.md with new entries                  │
│ 5. Update feature-evolution/*.md with learnings                 │
│ 6. Commit changes with summary                                   │
└─────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OUTPUT FILES                                  │
├─────────────────────────────────────────────────────────────────┤
│ docs/PROJECT_FEATURES.md        # Updated inventory + change log│
│ docs/feature-evolution/*.md     # Memory of WHY features evolved│
│ docs/weekly-reports/YYYY-WW.md  # Weekly summary report         │
└─────────────────────────────────────────────────────────────────┘
```

## Memory Structure

### 1. PROJECT_FEATURES.md
The canonical source of truth for:
- All features with IDs (e.g., BRD-008)
- Which pain/goal each feature addresses
- Assumptions we're making
- Change log (date, change, why)

### 2. feature-evolution/*.md
Deep memory for each major feature area:

```
docs/feature-evolution/
├── signal-ingestion.md      # How we capture client signals
├── extraction-pipeline.md   # How AI extracts entities
├── confirmation-workflow.md # How confirmation evolved
├── canvas-views.md          # Canvas vs BRD evolution
├── prototype-review.md      # How prototype review evolved
├── client-portal.md         # How client interaction evolved
└── collaboration.md         # How consultant workflow evolved
```

Each file follows this template:

```markdown
# [Feature Area] Evolution

## Current State
[What it does today]

## Original Assumptions
[What we thought users needed]

## Evolution Timeline

### [Date] - [Change Name]
**Trigger**: [What caused this change - feedback, data, intuition]
**Before**: [How it worked before]
**After**: [How it works now]
**Learning**: [What we learned]
**Evidence**: [Link to feedback, commit, or signal]

### [Earlier Date] - [Earlier Change]
...
```

### 3. weekly-reports/YYYY-WW.md
Auto-generated weekly summaries:

```markdown
# Week 06, 2026

## Code Changes
- 20 files changed in `components/workspace/brd/`
- 3 new endpoints in `app/api/workspace.py`
- 1 migration: `0098_brd_canvas_support.sql`

## Feature Impact
| Feature ID | Change Type | Summary |
|------------|-------------|---------|
| BRD-001 to BRD-013 | NEW | Added BRD Canvas view |
| DC-004 | MODIFIED | Now secondary to BRD view |

## Assumption Updates
- **Validated**: Consultants want document-style view over canvas
- **Challenged**: Drag-drop is not primary interaction pattern
- **New**: MoSCoW grouping helps scope management

## Questions for Next Week
- Is BRD view faster than canvas for real workflows?
- Do consultants use "Confirm All" frequently?
```

## Weekly Diff Script

### How It Works

```typescript
// scripts/weekly-feature-diff.ts

1. Get commits from last 7 days
   git log --since="7 days ago" --name-only --pretty=format:"%H %s"

2. Categorize changed files:
   - Frontend components (*.tsx in components/)
   - Backend endpoints (*.py in app/api/)
   - Types (*.ts in types/)
   - Migrations (*.sql in migrations/)
   - Tests (test_*.py)

3. Build context for Claude:
   - Changed file paths
   - Commit messages
   - Diff summaries (git diff --stat)
   - Current PROJECT_FEATURES.md

4. Claude analyzes with prompt:
   "Given these code changes, update the feature inventory:
    - Identify new features (assign IDs)
    - Identify modified features
    - Explain WHY each change was made
    - What assumptions were validated/challenged?
    - Update the change log"

5. Parse Claude's output and:
   - Update PROJECT_FEATURES.md
   - Append to relevant feature-evolution/*.md
   - Create weekly-reports/YYYY-WW.md

6. Commit with message:
   "chore: weekly feature inventory update (Week N)"
```

### Running Manually

```bash
# Full weekly update
npx ts-node scripts/weekly-feature-diff.ts

# Analyze specific date range
npx ts-node scripts/weekly-feature-diff.ts --since="2026-02-01" --until="2026-02-06"

# Dry run (no commits)
npx ts-node scripts/weekly-feature-diff.ts --dry-run
```

## Feedback Integration

When beta feedback comes in:

1. **Log feedback** in `docs/feedback/YYYY-MM-DD-[topic].md`
2. **Map to feature** using PROJECT_FEATURES.md feature IDs
3. **Update assumptions** if feedback challenges them
4. **Link in evolution** file when acting on feedback

### Feedback Template

```markdown
# Feedback: [Title]

**Date**: 2026-02-06
**Source**: [User name / session]
**Feature ID**: BRD-008

## Raw Feedback
"[Exact quote from user]"

## Analysis
- **Type**: [Bug | Usability | Feature Request | Confusion]
- **Severity**: [Critical | High | Medium | Low]
- **Assumption Challenged**: [Original assumption that was wrong]
- **Learning**: [What we now understand]

## Action Taken
- [ ] Code change (PR #123)
- [ ] Design change
- [ ] Documentation update
- [ ] Deferred to backlog

## Follow-up
[Any questions to ask in next session]
```

## Cron Setup

Add to crontab (or GitHub Actions):

```yaml
# .github/workflows/weekly-feature-update.yml
name: Weekly Feature Inventory Update

on:
  schedule:
    - cron: '0 0 * * 0'  # Every Sunday at midnight UTC
  workflow_dispatch:      # Allow manual trigger

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for git log

      - uses: actions/setup-node@v4
        with:
          node-version: '20'

      - run: npm install

      - run: npx ts-node scripts/weekly-feature-diff.ts
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

      - uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "chore: weekly feature inventory update"
```

## Entity Connections

The memory system connects to AIOS entities:

```
PROJECT_FEATURES.md
    │
    ├── Feature ID (e.g., BRD-008)
    │   ├── Maps to: Component path
    │   ├── Maps to: Backend endpoint
    │   ├── Solves: Pain ID (P1-P6)
    │   ├── Supports: Goal ID (G1-G6)
    │   └── Assumptions: Hypothesis we're testing
    │
    └── Feedback
        ├── Mapped to Feature ID
        ├── Challenges Assumption
        └── Triggers Evolution entry

feature-evolution/*.md
    │
    ├── Timeline of changes
    ├── Evidence links (commits, feedback, signals)
    └── Learnings captured
```

## Usage Patterns

### For Matt (Building AIOS)
1. Weekly: Review auto-generated report
2. After feedback: Log and map to features
3. Before major change: Check assumptions in evolution files
4. When confused: Read evolution timeline for context

### For Future Agents
1. Before modifying feature: Read PROJECT_FEATURES.md for context
2. After implementing: Update change log with WHY
3. When unclear: Reference evolution files for history

### For Beta Testers
1. Use feature IDs when reporting issues
2. Reference specific screens/components
3. Describe what they expected vs what happened

## Example: BRD Canvas Evolution

```markdown
# docs/feature-evolution/canvas-views.md

# Canvas Views Evolution

## Current State
Discovery phase has two views:
- **BRD View** (default): Document-style, MoSCoW grouped, Notion-like
- **Canvas View**: DnD-based, journey flow, feature mapping

## Original Assumptions
1. Consultants prefer visual drag-drop over document editing
2. Journey flow is the natural mental model
3. Feature-to-step mapping is primary interaction

## Evolution Timeline

### 2026-02-06 - Added BRD Canvas as Default
**Trigger**: Internal hypothesis that document-style better matches PRD output
**Before**: Only DnD RequirementsCanvas available
**After**: BRD Canvas is default, DnD available via toggle
**Learning**: Need to validate with real users which view they prefer
**Evidence**: [Commit cafb36b](https://github.com/...)

**New Assumptions**:
- Consultants may prefer reading/confirming over dragging
- MoSCoW grouping helps with scope conversations
- Document view better matches client expectations

### 2026-01-XX - Original Canvas Implementation
**Trigger**: Initial product vision
**Before**: No discovery workspace
**After**: DnD-based RequirementsCanvas with persona row, journey flow
**Learning**: Visual mapping is powerful but may be overwhelming
**Evidence**: Initial implementation
```

## Metrics to Track

Over time, measure:

| Metric | How to Measure | Target |
|--------|----------------|--------|
| Assumption accuracy | % of assumptions validated by feedback | >70% |
| Feature coverage | % of features with feedback | 100% of core |
| Evolution depth | Avg entries per evolution file | >5 per area |
| Memory freshness | Days since last evolution update | <14 days |
| Feedback mapping rate | % of feedback mapped to features | >90% |
