# Prototype Review Guide

How the prototype refinement loop works — from generation to client sign-off.

---

## The Big Picture

```
Discovery Data ──► Generate Prototype ──► AI Analyzes Every Feature
                                                    │
                                         Consultant Reviews
                                         (guided tour + verdicts)
                                                    │
                                    ┌────────────────┼────────────────┐
                                    │                │                │
                              "All Good"      "Fix First"     "Not Ready"
                              Share link      AI fixes code    Keep reviewing
                                    │         then share              │
                                    ▼                │                │
                              Client Reviews ◄───────┘        Back to session
                              (verdict cards)
                                    │
                                    ▼
                              AI Synthesizes
                              All Feedback
                                    │
                                    ▼
                              Code Updated
                              Ready for Session 2
```

---

## Step-by-Step

### 1. Prototype Generation

**What happens:** AIOS takes everything from discovery — features, personas, value path steps, company info — and writes a detailed prompt for v0 (Vercel's AI code generator). v0 builds a working Next.js app that represents the requirements as a clickable prototype.

**What you get:** A live URL (e.g., `https://v0-acme-prototype.vercel.app`) with real pages, navigation, forms, and mock data — all tagged with feature IDs so AIOS can track what maps to what.

**Your role:** None. This is automated.

---

### 2. AI Feature Analysis

**What happens:** AIOS reads every feature's source code and compares it against the requirements spec. For each feature it produces:

- **Spec vs. Code comparison** — what the requirements say vs. what the code does
- **Delta list** — concrete gaps (e.g., "Missing payment validation on submit")
- **Suggested verdict** — `aligned`, `needs_adjustment`, or `off_track`
- **One validation question** — a plain-language yes/no question for the client (e.g., "Does this form capture all the info your team needs?")
- **Impact analysis** — which personas are affected, where in the value path this sits

**Your role:** None. This runs automatically after generation.

---

### 3. Your Review Session

Navigate to **Prototype** in the project sidebar. You'll see "Prototype Ready for Review — N features analyzed." Click **Start Review Session**.

**What you see:**

| Zone | What's There |
|------|-------------|
| Left (main area) | Live prototype in an iframe — click around, try the flows |
| Right panel | Feature overlay cards — click any feature to see its analysis |
| Bottom | AI chat — ask questions about the current page/feature |

**Guided Tour:** A tour bar appears at the top. It walks you through features in value-path order — the same sequence your client would experience. For each feature:

1. The prototype navigates to the right page and highlights the feature
2. The sidebar shows the AI's analysis + the validation question
3. You can answer the question, add notes, or skip

**Setting Verdicts:** For each feature, you can set your verdict:
- **Aligned** — code matches the spec, looks good
- **Needs Adjustment** — right direction, but has gaps
- **Off Track** — significant mismatch, needs rework

You're not reviewing code quality — you're checking whether the prototype represents the *requirements* correctly.

**When you're done:** Click **End Review**.

---

### 4. Share Decision

After ending your review, you see a summary panel with three options:

| Option | When to Use |
|--------|------------|
| **Share with Client — All Good** | Prototype is ready for client eyes. Copies the client review link. |
| **Fix First, Then Share** | You found issues. AIOS runs synthesis + code fixes first, then you can share. |
| **Not Ready — Keep Working** | Go back to reviewing. Maybe you missed something. |

The **client review link** is a token-secured URL. No login required — the client just opens the link.

---

### 5. Client Review

**What the client sees:** A simplified version of your view:

- Top half: the live prototype
- Bottom half: per-feature cards, sorted by severity (off-track first)

Each card shows:
- The feature name and AI confidence score
- Your verdict and notes (so they see your assessment)
- The validation question (plain language, business-focused)
- Three verdict buttons for the client to respond
- A notes field for additional feedback

The client clicks verdicts, optionally adds notes, then hits **Complete Review**. No login, no account needed.

---

### 6. Synthesis

Once the client completes their review (or if you chose "Fix First"), AIOS synthesizes everything:

- Your verdicts + the client's verdicts
- Your notes + the client's notes
- The AI's original analysis
- Any chat feedback from your session

It produces per-feature recommendations: what's confirmed, what's new, where there are contradictions, and what code changes are needed.

**Verdict logic:**
- Both say aligned → `confirmed_client` (strongest)
- You say aligned, client says needs adjustment → `needs_client` (flag for follow-up)
- Either says off track → `needs_client`
- Only you reviewed (no client yet) → `confirmed_consultant`

---

### 7. Code Update

AIOS plans and executes code changes based on the synthesis. It:

1. Creates a session branch (`session-2`, `session-3`, etc.)
2. Plans changes (using Opus for architectural thinking)
3. Executes changes (using Sonnet with file read/write tools)
4. Validates the build passes
5. Commits and pushes

The prototype auto-deploys on Vercel. You can start Session 2 immediately.

---

## Session Lifecycle

```
pending → consultant_review → awaiting_client → client_complete → synthesizing → updating → completed
                    │                                                                          │
                    └──── "Not Ready" ◄──── back to reviewing                                  │
                                                                                               │
                                                                            Ready for next session
```

---

## Tips

- **You and AIOS are a team.** The AI analyzes the code; you validate the business intent. Focus on whether features match what the client actually needs, not on code quality.
- **Verdict questions are for the client.** They're written in plain business language — no mention of APIs, components, or data models. If you see a technical question, that's a bug.
- **You can run multiple sessions.** Each session builds on the previous one. Session 2 has the code fixes from Session 1 already applied.
- **The client link is stateless.** No account needed. Share via email, Slack, whatever. The token expires with the session.
- **Polling is automatic.** After you share the link, your page watches for client completion. When they finish, synthesis kicks off automatically.
