# BenyBox — Prototype Build Contract

**Compiled from the outcome graph, entity enrichment, convergence analysis, and intelligence gaps.**

This is not a feature list. This is a structural understanding of what the software must DO — the state changes it must produce, the moments it must nail, and the invisible behavior that makes the client say "how did it know that?"

---

## Prototype Thesis

> BenyBox exists because families get destroyed — financially, legally, emotionally — when critical documents are missing, inaccessible, or stale at the moment they matter most. The prototype proves that a single platform can take a family from "vaguely aware they should have a will" to "documents are organized, shared, current, and accessible in a crisis — without a lawyer, without a court, without a family fight."

**The selling moment**: Screen 9, Emergency Access. David opens his phone at 2am in the ER. Mom is unconscious. He scans the QR code on his Emergency Access Card. The Healthcare POA appears. He shows the doctor. Crisis to document: 90 seconds. No lawyer. No court. No family fight. That's when the client drops everything and says yes.

**The deepest screen**: Screen 5, Vault Completeness Score Dashboard. Three outcomes converge — document awareness, gap closure, and staleness monitoring. One metric (the Completeness Score) drives three state changes simultaneously. This is where the prototype proves it understands the problem better than a feature list ever could.

---

## Outcomes (The Five Things That Must Be True)

| # | H | Outcome | Strength | Selling Persona |
|---|---|---------|----------|----------------|
| 1 | H1 | Families know exactly which documents are missing and have a clear path to close gaps | 83 | Aging Parent (Margaret) |
| 2 | H1 | Critical documents are instantly accessible to the right family members during emergencies | **93** | Adult Child (David) — **THE scenario that sells** |
| 3 | H2 | Users consistently engage with their vault over time — not just at onboarding | 89 | Aging Parent + Adult Child |
| 4 | H2 | BenyBox is the trusted infrastructure layer for estate planning attorneys | 83 | Attorney (Sarah) |
| 5 | H1 | Sensitive documents shared with confidence — zero unauthorized access, full owner control | **93** | Aging Parent (Margaret) |

**Outcome Tension**: Outcomes 2 and 5 are in natural tension. Accessibility vs Security. The Emergency Access Card that enables David's 90-second crisis access must also produce an audit trail that proves Margaret consented. Resolution surface: Audit Trail (Screen 10).

---

## Screen Architecture (Convergence-Ordered)

### Priority Tier 1: Convergence Screens (demo FIRST — these prove understanding)

**Screen 5 — Vault Completeness Score Dashboard** `pattern: dashboard`
```
OUTCOMES SERVED: O1 (awareness) + O3 (engagement) + O4* (staleness monitoring)
CONVERGENCE: 3 outcomes on one surface — HIGHEST convergence in the prototype
ACTORS: Aging Parent, Unrepresented Individual, Adult Child Caregiver

WHY THIS SCREEN EXISTS:
  Not for "document management." For showing the user their COMPLETE
  picture — what they have, what's missing, and why it matters — in
  one glance. The Completeness Score is the single metric that drives
  awareness (O1), motivates gap closure (O3), and surfaces staleness.
  One number. Three outcomes. This is why BenyBox isn't Dropbox.

THE MOMENT:
  Margaret logs in after uploading her Healthcare POA. Her score jumps
  from 58% to 67%. She sees 4 remaining gaps, sorted by urgency. The
  top gap card says: "Transfer-on-Death Deed — Required in California.
  Average cost: $150. 3 providers near you." She didn't know she needed
  this. Now she does. And she knows how to get it.

MUST-HAVE BEHAVIOR:
  - Completeness Score: PROMINENT (biggest element, not decorative)
  - Score changes on every upload (instant feedback)
  - Gap cards link to ACTION (provider referrals, cost estimates)
  - Staleness alerts surface proactively (don't wait for user to check)
  - Score DROP matters as much as score RISE (expired docs = score decrease)
  - Different framing per persona:
    Margaret sees: "You need 12 documents. You have 8."
    David sees: "Mom's vault is 67% complete. 4 gaps remain."

INTELLIGENCE NEEDED:
  Knowledge: State Legal Requirements DB (what CA requires for Margaret's profile)
  Scoring: Vault Completeness Score (% of required docs uploaded)
  Decision: Gap Priority Ranker (which gap to close first — urgency × cost × impact)
  AI: Life Event Detector (divorce, move, new child → re-run assessment)

VOCABULARY: "completeness score", "document landscape", "gap", "staleness"
NOT: "file manager", "upload center", "document storage"
```

**Screen 10 — Audit Trail and Access Log** `pattern: dashboard`
```
OUTCOMES SERVED: O2 (accessibility proof) + O5 (security proof)
CONVERGENCE: 2 outcomes — TENSION RESOLUTION surface
ACTORS: Aging Parent, Estate Planning Attorney

WHY THIS SCREEN EXISTS:
  This is where the tension between Outcome 2 (accessibility) and
  Outcome 5 (security) gets RESOLVED. The same audit trail serves
  David's legal defense in a crisis AND Sarah's compliance reporting.
  Two personas. Two use cases. One surface. Audit isn't a cost center.
  It's a trust engine.

THE MOMENT:
  Margaret sees: "David accessed your Healthcare POA on March 15 at
  2:14am from Memorial Hospital ER. Access method: Emergency Access
  Card. Duration: 3 minutes." She feels safe — she can see everything.
  David proves consent. Sarah proves diligence. The log is the same.

MUST-HAVE BEHAVIOR:
  - Every access logged with timestamp, method, viewer, duration
  - Margaret sees simplified "who touched what" view
  - Sarah sees compliance dashboard across all client vaults
  - Emergency access flagged distinctly (not suspicious — expected)
  - Export capability for legal proceedings

INTELLIGENCE NEEDED:
  Knowledge: Access pattern baseline (what's normal vs suspicious)
  Scoring: Trust Score (based on access patterns + sharing config)
  Decision: Anomaly alerting (unusual access triggers notification)
  AI: Compliance Reporter (generates audit summaries for attorneys)
```

### Priority Tier 2: Selling Screens (demo SECOND — these create the emotional hook)

**Screen 8 — Family Sharing Setup** `pattern: wizard`
```
OUTCOMES SERVED: O2 (enables emergency access) + O5 (controlled sharing)
ACTORS: Aging Parent, Adult Child Caregiver

WHY: Margaret invites David. Sets per-document access tiers. System
generates David's Emergency Access Card — a QR-coded card he can keep
in his wallet. This is the SETUP that makes the crisis moment possible.

THE MOMENT:
  Margaret selects "Adult Child — Emergency Access" for David. The
  system explains: "David will be able to access your Healthcare POA,
  Financial POA, and Emergency Contacts. He will NOT see your will,
  trust documents, or insurance policies unless you grant additional
  access." Margaret feels in control. She taps "Generate Emergency Card."

INVISIBLE BEHAVIOR:
  - Role-based access tiers (not just "share all")
  - Per-document granularity (healthcare docs ≠ financial docs)
  - Emergency Access Card generation (QR code → wallet)
  - Consent trail starts HERE (every sharing action logged)
  - Invitation flow doubles as acquisition (David creates account)
```

**Screen 9 — Emergency Access (David's View)** `pattern: splitview`
```
OUTCOME SERVED: O2 (THE selling scenario — strength 93)
ACTORS: Adult Child Caregiver ONLY

WHY: This is the screen that sells BenyBox. Not because of the UI.
Because of what it MEANS. David's mom is in the ICU. He needs proof
of legal authority. In the old world: 3 months, $12,000, family fight.
In BenyBox: 90 seconds, $0, proof on screen.

THE MOMENT:
  David scans QR code. Fast-path auth bypasses normal login. Category-
  filtered vault shows only what he needs. Full-screen document presenter
  optimized for showing to a doctor. Healthcare POA loads. David shows
  the screen. Doctor nods. Crisis resolved.

MUST-HAVE BEHAVIOR:
  - QR-code fast auth (no password, no friction — it's 2am)
  - Category filtering (don't show everything — show what matters NOW)
  - Full-screen document presenter (optimized for showing to a third party)
  - Offline capability (hospital WiFi is unreliable)
  - Access logged immediately (feeds Audit Trail)

INTELLIGENCE NEEDED:
  Scoring: Document Relevance Scorer (which docs matter for THIS crisis type)
  AI: Crisis Context Detector (ER → surface healthcare docs first)
```

### Priority Tier 3: Foundation Screens (demo THIRD — these establish context)

**Screen 0 — Profile Onboarding** `pattern: wizard`
```
OUTCOMES SERVED: O1 (enables document landscape awareness)
ACTORS: Aging Parent, Unrepresented Individual

THE MOMENT:
  Margaret answers 7 profile questions — age, state, marital status,
  children, health conditions. Takes 3 minutes. The Assessment Engine
  generates her personalized, state-specific document checklist. She
  sees her landscape for the first time: "You need 12 documents for
  your California situation. Let's find out what you already have."

  The Unrepresented Individual sees the same — but with cost context:
  "A notarized POA costs $50, not $2,000. Here are your options."

AI: Profile Compass (maps profile → state-specific requirements)
```

**Screen 1 — Document Needs Assessment** `pattern: form`
```
OUTCOMES SERVED: O1 (the actual gap identification)
ACTORS: Aging Parent, Unrepresented Individual

THE MOMENT:
  Based on Margaret's profile, the system shows: "You need these 12
  documents. Check the ones you already have." She checks 7. The
  system immediately shows: "5 gaps found. Here's your priority
  order." She sees "Transfer-on-Death Deed" — she didn't know this
  existed. That's the "how did it know?" moment.

AI: Personalized Document Needs Agent (state rules engine)
```

**Screen 3 — Guided Upload + Auto-Categorization** `pattern: wizard`
```
OUTCOMES SERVED: O1 (gap closure) + O3 (engagement loop)

THE MOMENT:
  Margaret uploads her Healthcare POA. The system auto-categorizes it,
  extracts metadata (date, state, named agents), and immediately updates
  her Completeness Score. She sees the score jump. Gap card for Healthcare
  POA disappears. Instant feedback. She wants to upload more.

AI: DocGuard Tagger (auto-categorize, extract metadata, validate completeness)
INVISIBLE: Upload triggers immediate score recalculation — the feedback loop IS the engagement
```

### Priority Tier 4: B2B / H2 Screens (demo LAST — these show the business model)

**Screen 12 — Attorney Partner Registration** `pattern: wizard`
```
OUTCOME SERVED: O4 (attorney infrastructure play)
ACTORS: Estate Planning Attorney

WHY: Sarah registers as a B2B partner. Links to client vaults. This
screen proves BenyBox isn't just consumer — it's infrastructure.

AI: Vault Reconciler (maps attorney's existing client docs to BenyBox categories)
```

**Screen 13 — Attorney Document Handoff** `pattern: form`
```
OUTCOME SERVED: O4 (attorney delivers TO vault, not just drafts)
ACTORS: Attorney, Aging Parent, Unrepresented Individual

THE MOMENT:
  Sarah finishes drafting Margaret's Trust. Instead of handing Margaret
  a PDF, she uploads directly into Margaret's vault. Pre-categorized.
  Margaret's Completeness Score jumps. The document is already shared
  with David. The handoff is seamless.

INVISIBLE: The product category changes here. BenyBox isn't storage.
It's the place where documents are BORN. That's an H3 insight feeding
back into H1 design.
```

**Screen 14 — Attorney Portfolio Dashboard** `pattern: dashboard`
```
OUTCOME SERVED: O4 (portfolio visibility)
ACTORS: Estate Planning Attorney

THE MOMENT:
  Sarah opens her dashboard Monday morning. 12 clients. 3 flagged
  at-risk (stale documents). One-click outreach: "Hi Margaret, your
  Financial POA was signed in 2019 — California recommends refreshing
  every 3 years." Sarah's practice has a scalable aftercare model.

AI: Portfolio Risk Spotter (aggregate staleness across client vaults)
```

---

## Persona Journeys Through the Prototype

### Margaret (Aging Parent) — The Primary Journey
```
Screen 0: Profile Onboarding → "I answer 7 questions"
Screen 1: Needs Assessment → "I see my landscape for the first time — 12 docs, I have 7"
Screen 3: Guided Upload → "I upload my Healthcare POA, score jumps to 67%"
Screen 5: Vault Dashboard → "I see 4 gaps, sorted by urgency, with provider links"
Screen 8: Family Sharing → "I invite David, set his access level, generate his Emergency Card"
Screen 10: Audit Trail → "I can see David accessed my POA at 2am — I feel safe"
```

### David (Adult Child) — The Crisis Journey
```
Screen 8: (Margaret set him up) → "I get the invitation, create my account"
Screen 9: Emergency Access → "2am. Mom in ICU. QR scan. POA on screen. Show doctor. Done."
Screen 5: Vault Dashboard → "Mom's vault is 67% complete. I can trust the documents are current."
Screen 10: Audit Trail → "My access is logged. If anyone questions my authority, there's proof."
```

### Sarah (Attorney) — The B2B Journey
```
Screen 12: Registration → "I register my practice as a BenyBox partner"
Screen 13: Document Handoff → "I upload Margaret's Trust directly into her vault"
Screen 14: Portfolio Dashboard → "Monday morning: 3 clients at risk. One-click outreach."
Screen 10: Audit Trail → "Compliance reporting across all client vaults"
```

### Unrepresented Individual — The Affordable Journey
```
Screen 0: Onboarding → "Same assessment, but cost context: POA costs $50, not $2,000"
Screen 1: Assessment → "I see what I need without paying $500/hr"
Screen 4: Gap + Referrals → "3 ways to get each doc: DIY $0 / LegalZoom $79 / Attorney $250"
Screen 5: Dashboard → "I build incrementally, score shows progress"
```

---

## Intelligence Architecture (What the System Must Be Smart Enough to Do)

### Per-Outcome Intelligence Requirements

| Outcome | Knowledge | Scoring | Decision | AI |
|---------|-----------|---------|----------|-----|
| O1: Know the landscape | State Legal Requirements DB | Vault Completeness Score | Gap Priority Ranker | Profile Compass (assessment engine) |
| O2: Crisis access | Document type registry | Document Relevance Score | Permission Gate | Crisis Context Detector |
| O3: Ongoing engagement | Refresh interval rules | Engagement Score | Staleness alert trigger | Life Event Detector |
| O4: Attorney infrastructure | Client document taxonomy | Portfolio Health Score | Outreach trigger | Portfolio Risk Spotter |
| O5: Zero unauthorized access | Consent requirements | Trust Score | Anomaly alert | Compliance Reporter |

**Currently: 0% intelligence coverage across all outcomes.** Every cell in this table is a build target.

---

## Tensions the Prototype Must Resolve

| Tension | Resolution Surface | Design Implication |
|---------|-------------------|-------------------|
| Accessibility (O2) ↔ Security (O5) | Audit Trail (Screen 10) | Emergency access must LOG everything. Consent trail starts at Family Sharing. |
| Simplicity (Unrepresented) ↔ Depth (Attorney) | Role-aware views | Same data, different interfaces. Margaret sees gaps. Sarah sees portfolio risk. |
| Onboarding friction ↔ Assessment completeness | Progressive wizard (Screen 0-1) | 7 questions, not 40. Get enough to generate landscape. Refine later. |
| Cost anxiety (Unrepresented) ↔ Revenue model | Gap + Referrals (Screen 4) | Show cost IMMEDIATELY. "$50, not $2,000." Referral revenue, not paywall. |

---

## What Makes This Feel Inevitable (Not Generated)

1. **The Completeness Score** — No one asked for it. But Outcome 1 says "know what's missing" and Outcome 3 says "close the gaps" and Outcome 4 says "stay current." One metric serves all three. The system derived this from the outcome graph.

2. **The Emergency Access Card** — It exists because Outcome 2 says "90 seconds in a crisis." A login page can't do that. A QR code in David's wallet can. The system inferred this from the actor outcome's metric.

3. **Attorney handoff INTO the vault** — Not upload. Not email. Direct injection. Because Outcome 4's actor outcome for Margaret says "I leave my attorney's office with documents already organized." The system traced the workflow backward from the outcome.

4. **Cost context for Unrepresented** — Same assessment, different framing. Because the actor outcome says "without paying $500/hr." The system personalized the experience from the before_state.

5. **Staleness alerts before they matter** — Not a setting buried in preferences. Proactive. Because Outcome 3's metric says "stale docs flagged within 48 hours." The system made staleness a first-class behavior, not an afterthought.

6. **Cross-persona audit trail** — Same log serves Margaret (peace of mind), David (legal proof), and Sarah (compliance). Because the convergence analysis showed O2 and O5 resolving on the same surface. The system found the resolution point.

None of these were explicitly requested. All of them are structurally inevitable from the outcome graph. That's the magic.

---

## H3 Feedback Constraints (Design for the Future Without Building It)

From H3 computation (always running in background):

- **If "families know their gaps" works at scale** → Insurance companies want policyholders to have document prep as a benefit. **H1 constraint: Design vault to accept documents from external sources, not just uploads.**

- **If "David can present in 90 seconds" works at scale** → Hospitals want to integrate. ER admissions query for legal authority at point of care. **H1 constraint: Emergency Access must work via URL/QR, not just native app.**

- **If "Sarah delivers to vault" works at scale** → Attorneys draft INSIDE the vault. **H1 constraint: Don't hardcode "upload" as the only document input method.**

These constraints are already reflected in the screen design above. The prototype is H1, but it's H3-ready.
