# Cortex Optimize — Prune, Score, and Sharpen Memory

Read all memory files, score their health across six dimensions, identify decay, and surgically fix it. This is the garbage collector for your knowledge graph.

## Arguments
$ARGUMENTS

If "report" — score and report only, don't modify files.
If "aggressive" — prune harder, tighter budgets, zero tolerance for filler.
If no arguments — standard optimization pass with user approval for changes.

## Steps

### Phase 1: Inventory

1. Locate the memory directory for the current project:
   - Check `~/.claude/projects/*/memory/` matching the current working directory
2. Read every file in the memory directory. For each file, record:
   - Filename
   - Line count
   - Budget (from Cortex Protocol: MEMORY.md=150, architecture=200, patterns=150, gotchas=100, decisions=150, preferences=100, corrections=100)
   - Last modified date (from git log or file content if the file tracks it)
   - Whether the file exists at all (missing = coverage gap)
3. Check for files that shouldn't exist:
   - Session log files (session-*.md) — candidates for distillation
   - Duplicate topic files
   - Files not part of the Cortex Protocol structure

### Phase 2: Score Each Dimension

Score each dimension 1–5 and show the evidence:

#### Freshness (1–5)
4. For each topic file, determine when it was last meaningfully updated
5. Score: 5 if all files updated within 3 sessions, 3 if most are recent, 1 if core files are stale

#### Signal Density (1–5)
6. Read each file line by line. Flag entries that are:
   - **Generic** — Would be identical in any project (e.g., "use TypeScript for type safety")
   - **Duplicated** — Same information appears in multiple files
   - **Obvious** — Things Claude would know without being told
   - **Verbose** — Could be said in fewer words without losing meaning
7. Calculate the ratio of actionable lines to total lines
8. Score: 5 if >95% actionable, 3 if ~75%, 1 if <50%

#### Coverage (1–5)
9. Check which of the 7 standard topic files exist and have content:
   - MEMORY.md, architecture.md, patterns.md, gotchas.md, decisions.md, preferences.md, corrections.md
10. Score: 5 if all exist with meaningful content, 3 if most exist, 1 if major gaps

#### Accuracy (1–5)
11. Cross-reference memory entries against the actual codebase:
    - Do referenced files still exist?
    - Do referenced patterns still match the code?
    - Are build/test commands still correct?
    - Have any decisions been reversed without updating decisions.md?
12. Score: 5 if all references verified, 3 if mostly accurate, 1 if significant drift

#### Size Discipline (1–5)
13. Compare each file's line count against its budget
14. Score: 5 if all files comfortably under budget, 3 if 1-2 files at edge, 1 if multiple files over budget

#### Consistency (1–5)
15. Check for contradictions between files:
    - Does MEMORY.md's project identity match architecture.md's description?
    - Do decisions.md entries align with patterns.md?
    - Are there conflicting statements about the same topic?
16. Score: 5 if zero contradictions, 3 if minor, 1 if files actively disagree

### Phase 3: Identify Issues

17. Compile a prioritized issue list, grouped by type:

**Critical (fix immediately):**
- Inaccurate entries referencing deleted code or reversed decisions
- Contradictions between files
- MEMORY.md over 150 lines

**Warning (fix recommended):**
- Stale files not updated in 5+ sessions
- Generic entries that add no project-specific value
- Session log files that should be distilled
- Entries that duplicate information across files

**Info (nice to fix):**
- Verbose entries that could be tightened
- Missing topic files (especially if the project has grown)
- Entries missing source attribution or dates

### Phase 4: Optimize

18. If mode is "report", skip to Phase 5

19. Present the issue list to the user with proposed fixes:
    ```
    CRITICAL: architecture.md references src/api/auth.py (deleted 2 weeks ago)
    → Proposed: Remove the auth.py reference, update with current auth location

    WARNING: patterns.md contains "Use functional components" (generic, not project-specific)
    → Proposed: Delete this entry

    WARNING: session-2026-01-15.md exists (should be distilled into topic files)
    → Proposed: Extract learnings into relevant topic files, then delete session file
    ```

20. If mode is "aggressive", apply all fixes without asking
21. If standard mode, ask user to approve: "Fix all", "Fix critical only", or "Let me choose"

22. For each approved fix:
    - **Stale references**: Verify current state, update or remove
    - **Generic entries**: Delete
    - **Duplicates**: Keep the version in the most appropriate file, remove others
    - **Session logs**: Extract each learning into the right topic file, then delete the session file
    - **Over-budget files**: Identify the lowest-value entries and remove them
    - **Verbose entries**: Rewrite for concision (same information, fewer words)
    - **Contradictions**: Determine which version is correct (check code), fix the incorrect one

23. After applying fixes, verify no files were accidentally emptied or corrupted

### Phase 5: Rebuild Health Score

24. Re-score all six dimensions after fixes
25. Calculate the letter grade: A (4.5+) | B (3.5–4.4) | C (2.5–3.4) | D (1.5–2.4) | F (<1.5)
26. Update the health score and last-maintained date in MEMORY.md

### Phase 6: Report

27. Display the optimization report:
    ```
    Cortex Optimization Report
    ==========================

    Health Score: [Before] → [After]

    Dimensions:
      Freshness:       [N] → [N]  [bar visualization]
      Signal Density:  [N] → [N]  [bar visualization]
      Coverage:        [N] → [N]  [bar visualization]
      Accuracy:        [N] → [N]  [bar visualization]
      Size Discipline: [N] → [N]  [bar visualization]
      Consistency:     [N] → [N]  [bar visualization]

    File Summary:
      MEMORY.md       [N]/150 lines  [status]
      architecture.md [N]/200 lines  [status]
      patterns.md     [N]/150 lines  [status]
      gotchas.md      [N]/100 lines  [status]
      decisions.md    [N]/150 lines  [status]
      preferences.md  [N]/100 lines  [status]
      corrections.md  [N]/100 lines  [status]

    Changes Made:
      - [N] entries removed (stale/generic/duplicate)
      - [N] entries updated (accuracy fixes)
      - [N] entries tightened (verbose → concise)
      - [N] session files distilled and archived

    Recommendations:
      [Any remaining issues that need manual attention]
    ```

28. If the health score is A, congratulate and note the streak
29. If below B, suggest running `/cortex-optimize` again after addressing recommendations

## Key Principles

- **Evidence-based scoring** — every score must be justified by specific observations, not vibes
- **Surgical fixes** — change the minimum needed. Don't rewrite files for style.
- **Preserve signal** — when in doubt about whether an entry is valuable, keep it. Deleting useful knowledge is worse than keeping mild clutter.
- **Cross-reference against code** — memory that doesn't match reality is actively harmful
- **Show the math** — the user should understand exactly why each score was given and what each fix does
- **Track improvement** — the before/after comparison motivates continued maintenance
