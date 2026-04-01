# Engagement Summary — Consolidate Audit Results

Generate a comprehensive engagement summary after completing audit stages on a flow. This report serves two audiences: the user (what happened, what improved) and future agent runs (institutional memory for the next audit).

## Arguments
$ARGUMENTS

If a flow name is provided, summarize that flow's engagement.
If no arguments: auto-detect from `qa-reports/` — find the flow with the most recent audit activity.

## When to Generate

This summary should be generated when:
- All three audit stages (QA + Product + UX) have been run on a flow
- Re-audits show score improvements (fixes were applied)
- The user asks for a summary or the engagement feels "done"

The feature-audit, product-audit, and ux-audit commands should suggest this at the end of a re-audit: "All stages re-audited with improvements. Want me to generate an engagement summary?"

## Steps

### Phase 1: Gather Data

1. **Read the onboard profile** from `qa-reports/onboard-profile*.md` for system context.

2. **Read all audit reports for this flow:**
   - Check `qa-reports/[flow]/` directory for all `*-audit-*.md` files
   - Also check `qa-reports/[flow]-*-audit-*.md` for backwards compatibility
   - Sort by date — identify first audit (baseline) and latest audit (current) per stage

3. **Read the remediation plan** if one exists:
   - Check `qa-reports/[flow]/remediation-*.md` or `qa-reports/[flow]-remediation-*.md`
   - Extract the item list with effort and sprint assignments

4. **Query Forge for audit history** (if MCP available):
   - Call `get_agent_audits` for this project + flow
   - Get scores, deltas, finding counts per stage
   - Get finding statuses (open, fixed, deferred)

5. **Build the progression timeline:**
   - For each stage: first score → latest score → delta
   - For each finding: original status → current status
   - Count: total found, total fixed, total remaining

### Phase 2: Generate Summary

6. **Write the engagement summary** with this structure:

```markdown
# Engagement Summary: [flow-name]

**Agent:** feature-audit | **Project:** [project-name] | **Date:** [YYYY-MM-DD]
**Engagement duration:** [first audit date] → [last audit date]

---

## Score Progression

|              | Baseline | Current | Delta |
|--------------|----------|---------|-------|
| QA           | [N] [G]  | [N] [G] | [+/-N] |
| Product      | [N] [G]  | [N] [G] | [+/-N] |
| UX           | [N] [G]  | [N] [G] | [+/-N] |
| **Overall**  | [N] [G]  | [N] [G] | **[+/-N]** |

---

## What Was Found ([N] total findings)

| Severity | Count | Fixed | Remaining |
|----------|-------|-------|-----------|
| Critical | [N]   | [N]   | [N]       |
| High     | [N]   | [N]   | [N]       |
| Medium   | [N]   | [N]   | [N]       |
| Low      | [N]   | [N]   | [N]       |
| Design   | [N]   | [N]   | [N]       |

---

## What Was Fixed ([N] of [N])

[For each fixed finding:]
- **[R-NNN]: [Title]** — [1-sentence description of the fix]
  File: [code_ref] | Effort: [S/M/L] | Sprint: [1/2/3]

---

## What Remains ([N] items)

[For each remaining finding:]
- **[R-NNN]: [Title]** — [why it's deferred]
  Priority: [P2/P3] | Effort: [S/M/L]

---

## Key Improvements

[3-5 bullet points of the most impactful changes, written for a human reader:]
- Full CRUD for clients and stakeholders — users can now correct AI mistakes
- 1-click deep enrichment replaces 4-6 manual clicks + navigation
- Mobile usable — sidebar collapses below 768px
- [...]

---

## Regression Watch

[Items that should be specifically re-tested on the next audit:]
- **[Fix name]**: [Why it might regress — e.g., "asyncio.gather, verify no race conditions under load"]
- **[Fix name]**: [Why it might regress]

These are not bugs — they're fixes that touch complex code paths and should be monitored.

---

## Context for Next Audit

[Things the next agent run needs to know that aren't in the code:]
- [Design decisions made during remediation — e.g., "Tabs removed from client detail, now single scroll"]
- [Intentional trade-offs — e.g., "Knowledge Base collapsed by default, not removed"]
- [Backlog items that affect testing — e.g., "No back navigation in onboarding modal"]
- [Environment notes — e.g., "Test with real company URLs, not acme.com"]

---

## Artifacts

| File | Description |
|------|-------------|
| `qa-reports/[flow]/scenarios-[date].md` | Original scenario plan |
| `qa-reports/[flow]/qa-audit-[date].md` | QA audit report |
| `qa-reports/[flow]/product-audit-[date].md` | Product audit report (latest) |
| `qa-reports/[flow]/ux-audit-[date].md` | UX audit report (latest) |
| `qa-reports/[flow]/remediation-[date].md` | Remediation plan |
| `qa-reports/[flow]/engagement-summary-[date].md` | This file |
| `qa-reports/design-guide-[date].md` | Design system guide |
```

### Phase 3: Save & Record

7. **Save locally:**
   - Write to `qa-reports/[flow]/engagement-summary-[date].md`
   - This file is the primary reference for future agent runs on this flow

8. **Record to Forge** (if MCP available):
   - Call `record_audit` with:
     - stage: `engagement-summary`
     - score: the overall current score
     - grade: the overall current grade
     - report_content: the full summary markdown
     - metadata: `{ findings_total, findings_fixed, findings_remaining, score_progression: { qa: [before, after], product: [before, after], ux: [before, after] } }`

9. **Present to user:**
   - Display the summary
   - Suggest: "Engagement complete for [flow]. When you're ready to audit the next flow, run `/qa-scenarios [flow-name]`. The backlog items ([N]) will carry forward."

## Key Principles

- **Two audiences** — Write for the human who wants an executive summary AND the agent that needs to pick up where you left off. The "Context for Next Audit" section is specifically for the agent.
- **Regression Watch is not optional** — Every fix that touches async code, pipeline stages, or state management should be listed. These are the most likely regressions.
- **Be honest about what remains** — Don't spin deferred items as "nice to have." If they were in the remediation plan, they matter. State clearly why they're deferred.
- **Artifacts section enables navigation** — The next agent can find every report from this engagement without searching.
- **This summary is the engagement's deliverable** — It's what the consultant hands the client when the engagement ends.
