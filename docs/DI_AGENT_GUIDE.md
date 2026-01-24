# Design Intelligence (DI) Agent Guide

**For Consultants Building Value Paths That Make Clients Say "Holy Shit, You Understand Me"**

## Overview

### What is the DI Agent?

The Design Intelligence Agent is an AI-powered system that helps consultants build rock-solid project foundations before writing code. Instead of guessing what clients need, the DI Agent ensures you:

- **Understand THE core pain** (singular, not a list)
- **Know WHO feels it most** (primary persona)
- **Define the WOW moment** where pain inverts to delight

The agent acts as your intelligent partner, analyzing signals (emails, transcripts, notes), identifying gaps, and guiding you toward readiness.

### How Does It Help Consultants?

The DI Agent prevents the #1 mistake in software: **building the wrong thing**. It does this by:

1. **Continuous Assessment**: Tracks foundation quality across 8 gates
2. **Gap Identification**: Spots missing information and blind spots
3. **Intelligent Extraction**: Pulls insights from client conversations
4. **Guided Discovery**: Suggests questions to ask clients
5. **Phase Management**: Tells you when you're ready to prototype vs build

**Philosophy**: Trust is built by understanding first. Investment comes after seeing value. The DI Agent respects this natural progression.

### Two-Phase Gate System

The DI Agent uses a **two-phase gate system** (0-100 points) that mirrors the natural evolution of client engagement:

```
Phase 1: Prototype Gates (0-40 pts)
├─ Core Pain (15 pts)
├─ Primary Persona (10 pts)
├─ Wow Moment (10 pts)
└─ Design Preferences (5 pts)

Phase 2: Build Gates (41-100 pts)
├─ Business Case (20 pts)
├─ Budget Constraints (15 pts)
├─ Full Requirements (15 pts)
└─ Confirmed Scope (10 pts)
```

**Key Insight**: Phase 2 gates often unlock AFTER the prototype. Don't push for budget before clients see value.

---

## Using the DI Agent

### When to Invoke the Agent

The DI Agent should be invoked at key moments:

1. **After Discovery Calls** - Analyze new signals from client conversations
2. **Before Client Meetings** - Prepare targeted questions
3. **Project Health Checks** - Assess foundation quality
4. **When Stuck** - Get guidance on what's missing
5. **Before Prototyping** - Verify readiness to build

### API Endpoints

#### Invoke the Agent

```http
POST /projects/{project_id}/di-agent/invoke
```

**Request:**
```json
{
  "trigger": "new_signal",
  "trigger_context": "Just finished discovery call with Sarah",
  "specific_request": null
}
```

**Triggers:**
- `new_signal` - After adding client conversation
- `user_request` - Specific consultant question
- `scheduled` - Periodic health check
- `pre_call` - Prepare for upcoming meeting

**Response:**
```json
{
  "observation": "Project has core pain (confidence: 0.85) but primary persona is unclear...",
  "thinking": "The biggest gap is understanding WHO feels this pain most acutely...",
  "decision": "I will suggest discovery questions to identify primary persona",
  "action_type": "guidance",
  "guidance": {
    "summary": "Need to identify THE primary persona",
    "questions_to_ask": [
      {
        "question": "Who on your team gets fired if this problem isn't solved?",
        "why_ask": "Identifies ownership and urgency",
        "listen_for": ["Job titles", "Pain intensity", "Current workarounds"]
      }
    ],
    "what_this_unlocks": "Primary persona gate → wow moment identification"
  },
  "readiness_before": 25,
  "readiness_after": 25,
  "gates_affected": ["primary_persona"]
}
```

#### Extract Specific Foundation Elements

Individual extraction endpoints for targeted work:

```http
POST /projects/{project_id}/foundation/core-pain
POST /projects/{project_id}/foundation/primary-persona
POST /projects/{project_id}/foundation/wow-moment
POST /projects/{project_id}/foundation/business-case
POST /projects/{project_id}/foundation/budget-constraints
```

#### Get Complete Foundation

```http
GET /projects/{project_id}/foundation
```

Returns all gate elements with confidence scores.

#### Analyze Gaps

```http
GET /projects/{project_id}/di-agent/gaps
```

Shows missing information across all gates with severity (critical/high/medium/low).

#### Detect Blind Spots

```http
GET /projects/{project_id}/di-agent/blind-spots
```

Identifies consultant and client blind spots:
- **Consultant blind spots**: Symptom as problem, missing stakeholders, jumping to features
- **Client blind spots**: Feature-first thinking, everything in V1, underestimating change

### Interpreting Agent Responses

The DI Agent responds in one of four ways:

#### 1. Tool Call (`action_type: "tool_call"`)

The agent took action to fill a gap:

```json
{
  "action_type": "tool_call",
  "tools_called": [
    {
      "tool_name": "extract_core_pain",
      "tool_args": {"depth": "standard"},
      "result": {"statement": "...", "confidence": 0.85}
    }
  ]
}
```

**What to do:** Review the extracted data. Validate with client if confidence < 0.7.

#### 2. Guidance (`action_type: "guidance"`)

The agent needs more signal from the client:

```json
{
  "action_type": "guidance",
  "guidance": {
    "questions_to_ask": [...],
    "signals_to_watch": ["Budget mentions", "Timeline pressure"],
    "what_this_unlocks": "Business case gate"
  }
}
```

**What to do:** Ask these questions in your next client conversation.

#### 3. Stop (`action_type: "stop"`)

The agent needs consultant/client involvement:

```json
{
  "action_type": "stop",
  "stop_reason": "Foundation is prototype-ready (75/100)",
  "what_would_help": ["Build prototype", "Test with users"]
}
```

**What to do:** Take the recommended next steps.

#### 4. Confirmation (`action_type: "confirmation"`)

The agent needs validation:

**What to do:** Review and confirm with client.

---

## Gate System Deep Dive

### Phase 1: Prototype Gates (0-40 points)

**Goal**: Build a clickable prototype that viscerally demonstrates value.

#### Core Pain (15 points)

**What It Is:**
THE singular problem (not a list) that the client is experiencing. Root cause, not symptom.

**Components:**
- **Statement**: Clear problem description (min 20 chars, confidence ≥ 0.6)
- **Trigger**: What causes this pain? Why now?
- **Stakes**: What happens if unsolved? (consequence, not just frustration)
- **Who Feels It**: Specific role or person experiencing the pain

**Why It Matters:**
Without clarity on core pain, you risk solving the wrong problem. "Users don't log in daily" is a symptom. "Users don't see value in daily login" is the root cause.

**How to Extract:**
```http
POST /projects/{project_id}/foundation/core-pain
```

The DI Agent analyzes signals for pain language ("struggling with", "can't", "frustrated") and extracts the underlying issue.

**Red Flags:**
- ❌ "We need a dashboard" (solution, not pain)
- ❌ "Users don't do X" (symptom, not cause)
- ✅ "Teams waste 10+ hours/week manually tracking data because there's no centralized system"

**Example:**
```json
{
  "statement": "Customer success teams spend 10+ hours per week manually tracking churn risk indicators across disconnected tools",
  "trigger": "When a customer stops engaging but no alert fires",
  "stakes": "We lose $50K-200K MRR per month from preventable churn",
  "who_feels_it": "Customer Success Managers",
  "confidence": 0.85
}
```

#### Primary Persona (10 points)

**What It Is:**
THE person you build for FIRST. Not "users" or "the team" - a specific human with a name, role, and context.

**Components:**
- **Name & Role**: "Sarah Chen, Customer Success Manager"
- **Goal**: What they're trying to achieve
- **Pain Connection**: How they experience the core pain
- **Daily Context**: What their day looks like
- **Pain Experienced**: Specific frustration
- **Current Behavior**: How they handle it today
- **Desired Outcome**: What success looks like

**Why It Matters:**
Prototypes must speak to a specific human, not generic "users". Sarah's needs differ from the CTO's needs.

**How to Extract:**
```http
POST /projects/{project_id}/foundation/primary-persona
```

**Red Flags:**
- ❌ "Our users" (too vague)
- ❌ Multiple personas listed with no primary
- ✅ "Sarah Chen, CSM managing 50+ enterprise accounts, who manually tracks churn in spreadsheets"

**Example:**
```json
{
  "name": "Sarah Chen",
  "role": "Customer Success Manager",
  "goal": "Prevent customer churn proactively",
  "pain_connection": "Manually tracks 50+ accounts, misses early warning signs",
  "context": "Manages enterprise accounts worth $2M+ ARR, under pressure to reduce churn",
  "confidence": 0.8
}
```

#### Wow Moment (10 points)

**What It Is:**
The peak experience where pain inverts to delight. Not a feature list - a singular visceral moment.

**3 Levels:**
- **Level 1 (Core)**: Core pain solved - "I can finally see churn risk in real-time"
- **Level 2 (Adjacent)**: Adjacent pains addressed - "And it shows me WHY they're churning"
- **Level 3 (Unstated)**: Unstated needs met - "It suggests what to say in the rescue email"

**Components:**
- **Description**: The moment itself
- **Core Pain Inversion**: How pain transforms to relief
- **Emotional Impact**: What the persona feels
- **Visual Concept**: How it looks/feels
- **Trigger Event**: What causes the wow moment

**Why It Matters:**
Prototypes must nail THIS moment, not be a comprehensive feature set. The wow moment is what gets clients to say "I need this."

**How to Extract:**
```http
POST /projects/{project_id}/foundation/wow-moment
```

**Red Flags:**
- ❌ List of features
- ❌ Generic "users will be happy"
- ✅ Specific moment of transformation

**Example:**
```json
{
  "description": "Sarah opens the dashboard Monday morning and instantly sees which 3 accounts need attention this week, ranked by churn risk with AI-suggested actions",
  "core_pain_inversion": "From 'manual spreadsheet panic' to 'confident prioritization in 30 seconds'",
  "emotional_impact": "Relief, control, confidence",
  "visual_concept": "Clean dashboard with 3 red-flagged accounts, risk scores, and action buttons",
  "level_1_core": "See churn risk instantly",
  "level_2_adjacent": "Know WHY they're at risk",
  "level_3_unstated": "Get AI-suggested rescue actions",
  "confidence": 0.75
}
```

#### Design Preferences (5 points, OPTIONAL)

**What It Is:**
Visual direction preferences that reduce iteration.

**Components:**
- Visual style keywords ("clean", "modern", "data-dense")
- Reference products ("like Stripe dashboard", "HubSpot-style")
- Color preferences
- UI patterns they like/dislike

**Why It Matters:**
Reduces back-and-forth on aesthetics, makes prototype feel more "right" to the client.

**How to Gather:**
Often emerges naturally: "I love how Stripe does X" or "Keep it simple like Notion"

**Example:**
```json
{
  "style": "Clean, data-dense like Stripe",
  "references": ["Stripe Dashboard", "Linear"],
  "avoid": "Too much color, cluttered",
  "confidence": 0.6
}
```

---

### Phase 2: Build Gates (41-100 points)

**Goal**: Build production software with clear scope and budget.

**Important**: These gates often unlock AFTER the prototype. Don't push for budget/timeline before clients see value. Trust is built first, then comes investment.

#### Business Case (20 points)

**What It Is:**
Why the client should invest. Not just "it's useful" - concrete business value.

**Components:**
- **Value to Business**: Quantified impact
- **ROI Framing**: How they'll measure success
- **Success KPIs**: Specific metrics (≥1 required)
- **Why Priority**: Why now vs other initiatives

**Why It Matters:**
Can't build without understanding business value. This gate often clicks after prototype demo: "Now that I see it, here's what it's worth."

**How to Extract:**
```http
POST /projects/{project_id}/foundation/business-case
```

**When to Extract:**
Often AFTER prototype when client can articulate value in concrete terms.

**Red Flags:**
- ❌ "It will help users" (vague)
- ❌ No KPIs mentioned
- ✅ "Reduce churn by 15% = $2.4M ARR saved annually, measured by 90-day retention rate"

**Example:**
```json
{
  "value_to_business": "Reduce customer churn by 15% through proactive intervention",
  "roi_framing": "$2.4M ARR saved annually vs $200K implementation cost = 12x ROI in year 1",
  "why_priority": "Churn is #1 threat to growth targets. Q2 board presentation requires solution",
  "success_kpis": [
    {"metric": "Customer retention rate", "target": "↑ 15%", "timeframe": "6 months"},
    {"metric": "Time to identify at-risk accounts", "target": "< 1 day", "timeframe": "immediate"}
  ],
  "confidence": 0.85
}
```

#### Budget Constraints (15 points)

**What It Is:**
Reality check on resources: budget range, timeline, constraints.

**Components:**
- **Budget Range**: "$50K-150K" (not exact, just ballpark)
- **Budget Flexibility**: How firm is the number?
- **Timeline**: "Need by Q2" or "No hard deadline"
- **Hard Deadline**: External driver (conference, board meeting)
- **Technical Constraints**: "Must integrate with Salesforce"
- **Organizational Constraints**: "Only 1 developer available"

**Why It Matters:**
Must align scope to resources. Can't build an $800K vision on a $150K budget.

**How to Extract:**
```http
POST /projects/{project_id}/foundation/budget-constraints
```

**When to Ask:**
After prototype, when client understands value: "What's the investment you're thinking?"

**Red Flags:**
- ❌ Asking about budget on discovery call #1
- ❌ No timeline mentioned
- ✅ "We have $100-150K this quarter, must launch before Q2 board meeting"

**Example:**
```json
{
  "budget_range": "$100K-150K",
  "budget_flexibility": "Can flex to $175K if ROI justifies",
  "timeline": "Must launch MVP by end of Q2 (June 30)",
  "hard_deadline": "Q2 board presentation needs progress demo",
  "deadline_driver": "Board wants proof we're addressing churn",
  "technical_constraints": ["Must integrate with Salesforce", "Use existing AWS infrastructure"],
  "organizational_constraints": ["Only 1 backend dev available until April"],
  "confidence": 0.8
}
```

#### Full Requirements (15 points)

**What It Is:**
Complete feature set with ≥5 confirmed features, well-evidenced from signals.

**Requirements:**
- **≥5 features** in the database
- Features have **descriptions** (not just names)
- **Signal coverage**: Features traced to client conversations
- **Confirmation status**: At least some client-confirmed features

**Why It Matters:**
Need comprehensive understanding to build. "Dashboard" isn't a feature. "Risk score dashboard showing top 5 at-risk accounts" is.

**How to Achieve:**
The DI Agent tracks feature extraction automatically. You satisfy this gate by:
1. Running strategic foundation extraction
2. Confirming features with clients
3. Ensuring features have good signal attribution

**Red Flags:**
- ❌ < 5 features defined
- ❌ Features are vague ("reporting", "admin panel")
- ✅ Specific, client-confirmed features with clear value

**Example Features:**
1. Risk Score Dashboard - Show top 5 at-risk accounts ranked by ML score
2. Account Timeline - Visual history of engagement drops
3. AI Action Suggestions - Recommended rescue tactics per account
4. Slack Alerts - Real-time notifications for critical risk changes
5. Weekly Digest Email - Summary of accounts needing attention

#### Confirmed Scope (10 points)

**What It Is:**
Clear agreement on V1 vs V2 features. Client sign-off prevents scope creep.

**Components:**
- **V1 Features**: What ships first (minimal viable)
- **V2 Features**: What comes later (nice-to-haves)
- **Client Confirmation**: Explicit agreement ("Yes, this is V1")
- **Rationale**: Why V1/V2 split makes sense

**Why It Matters:**
Prevents scope creep and sets expectations. V1 is about validation, V2 is about scale.

**Philosophy:**
- **V1**: Minimum to validate the wow moment with real users
- **V2**: Scale, polish, adjacent features

**How to Get Confirmation:**
Present V1/V2 split to client: "Here's what we'll build first to test if this solves your problem. Here's what we add after validation."

**Red Flags:**
- ❌ No V1/V2 distinction
- ❌ Everything lumped together
- ❌ No client confirmation
- ✅ Clear V1 list, client-approved, V2 backlog defined

**Example:**
```json
{
  "v1_features": [
    "Risk Score Dashboard (top 5 accounts)",
    "Manual risk flag override",
    "Daily Slack digest"
  ],
  "v2_features": [
    "AI action suggestions",
    "Account timeline view",
    "Salesforce bi-directional sync",
    "Team collaboration features"
  ],
  "rationale": "V1 validates core hypothesis: can we predict churn accurately? V2 adds intelligence and collaboration after validation",
  "client_confirmed": true,
  "confirmed_by": "Sarah Chen, VP Customer Success",
  "confirmed_at": "2025-01-20",
  "confidence": 0.9
}
```

---

## Best Practices

### Discovery Call Preparation

**Before the call**, invoke the DI Agent with `trigger: "pre_call"`:

```http
POST /projects/{project_id}/di-agent/invoke
{
  "trigger": "pre_call",
  "trigger_context": "Client call in 30 minutes with Sarah (CSM lead)"
}
```

The agent will:
1. Analyze current foundation gaps
2. Suggest targeted questions
3. Highlight blind spots to watch for

**During the call:**
- Listen for pain language ("struggling", "can't", "frustrated")
- Ask WHY repeatedly (root cause, not symptom)
- Note who feels the pain most
- Capture stakes (what if unsolved?)
- Listen for value signals (ROI, metrics, urgency)

**After the call:**
- Add conversation as a signal (transcript, notes, email)
- Invoke agent with `trigger: "new_signal"`
- Review extracted insights, validate accuracy

### Signal Quality Matters

**High-Quality Signals:**
- ✅ Direct client quotes from calls/emails
- ✅ Transcripts from discovery sessions
- ✅ Client-written problem descriptions
- ✅ Research on client's industry/competitors

**Low-Quality Signals:**
- ❌ Consultant assumptions without validation
- ❌ Generic market research (not client-specific)
- ❌ Feature requests without context

**The 3:1 Rule**: 3 client signals > 10 consultant assumptions

### When to Prototype vs Build

**Prototype When:**
- **Phase 1 gates satisfied** (40+ points)
- Core pain, persona, wow moment clear
- Confidence ≥ 0.7 on foundation elements
- Client eager to see something tangible

**Build When:**
- **Phase 2 gates satisfied** (71+ points)
- Business case articulated
- Budget/timeline confirmed
- Scope agreed (V1 vs V2)
- Client has seen and validated prototype

**Never Build When:**
- Core pain unclear (confidence < 0.6)
- No primary persona identified
- Client hasn't seen prototype
- Budget/timeline unknown

### Evolution Philosophy: V1 → V2

**V1 (Validation)**
- Minimum to test core hypothesis
- Focus on wow moment
- Primary persona ONLY
- Quick iteration, okay to be rough
- Goal: "Does this solve the pain?"

**V2 (Scale)**
- Polish and refinement
- Adjacent personas
- Enterprise features (SSO, admin, reporting)
- Scalability and performance
- Goal: "Can this serve 1000 users?"

**Example Evolution:**

| Feature | V1 | V2 |
|---------|----|----|
| Risk Dashboard | Top 5 accounts, manual refresh | All accounts, real-time, customizable views |
| Alerts | Daily Slack digest | Real-time alerts, multi-channel, custom triggers |
| Actions | View risk score | AI-suggested actions, collaboration tools |
| Data | Manual CSV upload | Salesforce bi-directional sync, webhooks |

---

## Troubleshooting

### "Insufficient Signal" - What to Do

**Agent Response:**
```json
{
  "action_type": "stop",
  "stop_reason": "Insufficient signal to extract core pain with confidence",
  "what_would_help": ["More client conversations", "Discovery call transcript"]
}
```

**What This Means:**
Not enough data from client conversations. Agent won't guess.

**How to Fix:**
1. **Schedule discovery call** - Talk to client, focus on pain
2. **Add existing signals** - Upload old emails, notes, transcripts
3. **Ask targeted questions** - Use agent's suggested discovery questions
4. **Be patient** - 2-3 quality signals > 10 vague assumptions

**Questions to Ask Client:**
- "What problem are you trying to solve? Why does it matter?"
- "Walk me through the last time this problem caused issues."
- "What happens if you don't solve this?"
- "Who on your team feels this pain most?"

### Low Confidence Scores - How to Improve

**Agent Response:**
```json
{
  "core_pain": {
    "statement": "Teams struggle with data silos",
    "confidence": 0.45
  }
}
```

**What This Means:**
- **< 0.5**: Very uncertain, likely inferred
- **0.5-0.7**: Moderate confidence, needs validation
- **> 0.7**: High confidence, client-confirmed

**How to Improve Confidence:**

1. **Get Direct Quotes**
   - ❌ "They mentioned data issues" (vague)
   - ✅ "Sarah said: 'We waste 10 hours/week because customer data is in 5 different tools'"

2. **Multiple Sources**
   - One person mentions pain = low confidence
   - Three people mention same pain = high confidence

3. **Validate Explicitly**
   - Ask: "Let me check I understand: the core problem is X, and it costs you Y. Is that right?"
   - Get confirmation in writing (email, Slack)

4. **Add Context**
   - Not just WHAT the pain is
   - But WHY it happens, WHO feels it, WHAT HAPPENS if unsolved

**Example Improvement:**

| Before (0.45) | After (0.85) |
|---------------|--------------|
| "Teams struggle with data silos" | "Customer success teams spend 10+ hours/week manually copying customer data between Salesforce, Intercom, and Google Sheets because there's no unified dashboard, resulting in missed churn signals and $200K/month in preventable churn" - Sarah Chen, VP CS, confirmed in email 1/15/2025 |

### Gates Not Satisfied - Next Steps

**Check Gate Status:**
```http
GET /projects/{project_id}/di-agent/gaps
```

**Response:**
```json
{
  "priority_gaps": [
    {
      "type": "foundation",
      "severity": "critical",
      "gate": "primary_persona",
      "description": "Primary Persona: Confidence too low (0.3)",
      "how_to_fix": "Ask client: Who feels this pain most? Get specific name/role"
    }
  ]
}
```

**Action Plan by Severity:**

**Critical Gaps** (Blocks prototype)
1. Review what's missing
2. Check "how_to_fix" guidance
3. Schedule client conversation
4. Ask targeted questions
5. Re-run extraction after gathering signal

**High Gaps** (Blocks build)
1. Often unlock AFTER prototype
2. Don't force prematurely
3. Let client see value first
4. Then discuss budget/timeline

**Medium/Low Gaps** (Nice to have)
1. Can proceed without these
2. Gather opportunistically
3. Don't block progress

**Common Blockers:**

| Blocked Gate | Common Issue | Fix |
|--------------|--------------|-----|
| Core Pain | Too vague, symptom not cause | Ask "WHY?" 5 times, get to root |
| Primary Persona | Generic "users" not specific person | Ask "Who gets fired if this fails?" |
| Wow Moment | Feature list not moment | Ask "What's the ONE moment that changes everything?" |
| Business Case | No KPIs | Ask "How will you measure success?" |
| Budget | Too early to ask | Show prototype first, then discuss investment |

---

## Advanced: Agent Reasoning (OBSERVE → THINK → DECIDE → ACT)

### How the Agent Thinks

Every invocation follows this pattern:

#### 1. OBSERVE
```
- Current score: 35/100 (prototype_ready)
- Gates satisfied: core_pain (✓), primary_persona (✗), wow_moment (✗)
- Blocking gates: primary_persona (confidence: 0.3)
- Signals: 8 total, 3 unanalyzed
- Next milestone: Identify primary persona to reach 45/100
```

#### 2. THINK
```
- Biggest gap: Primary persona unclear (confidence 0.3)
- Why it matters: Can't define wow moment without knowing WHO we build for
- Evidence quality: Have generic "teams" language, need specific person
- Highest leverage: Get consultant to ask targeted persona questions
```

#### 3. DECIDE
```
Decision: Provide discovery questions (action_type: "guidance")
Rationale: Insufficient signal to extract persona confidently.
          Need consultant to ask client WHO specifically.
```

#### 4. ACT
```json
{
  "action_type": "guidance",
  "guidance": {
    "questions_to_ask": [
      "Who on your team gets fired if this problem isn't solved?",
      "Walk me through a day in the life of the person who feels this pain most.",
      "What's their job title and what does success look like for them?"
    ],
    "signals_to_watch": ["Job titles", "Daily workflows", "Pain intensity"],
    "what_this_unlocks": "Primary persona gate → wow moment definition"
  }
}
```

### Blind Spots the Agent Watches For

The DI Agent actively looks for consultant and client blind spots:

**Consultant Blind Spots:**
1. **Symptom as Problem** - "Users don't log in daily" vs "Users don't see value"
2. **Missing Stakeholders** - Only talking to one person
3. **Jumping to Features** - "We need a dashboard" before understanding pain
4. **What Over Why** - Requirements without motivation
5. **Not Challenging** - Accepting client framing without "why?"

**Client Blind Spots:**
1. **Feature First** - "I need a dashboard" vs "I need to understand churn"
2. **Everything in V1** - No prioritization, wants full vision immediately
3. **Underestimating Change** - No adoption/training plan
4. **Symptom vs Root** - Describing effects, not causes
5. **Incomplete Stakeholders** - "The team" without naming roles

**Get Blind Spot Analysis:**
```http
GET /projects/{project_id}/di-agent/blind-spots
```

**Use blind spots to:**
- Improve discovery questions
- Validate assumptions
- Identify missing stakeholders
- Reframe client requests

---

## Quick Reference

### Readiness Phases

| Score | Phase | What It Means | Next Step |
|-------|-------|---------------|-----------|
| 0-40 | Insufficient | Working toward prototype | Fill Phase 1 gaps |
| 41-70 | Prototype Ready | Can build clickable demo | Build prototype, test |
| 71-100 | Build Ready | Can build production software | Define V1 scope, build |

### Confidence Levels

| Confidence | Meaning | Action |
|------------|---------|--------|
| < 0.5 | Very uncertain, likely inferred | Get direct client validation |
| 0.5-0.7 | Moderate, needs more signal | Add 1-2 more sources |
| 0.7-0.85 | High, well-evidenced | Proceed with confidence |
| > 0.85 | Very high, client-confirmed | Rock solid foundation |

### Essential API Calls

```bash
# Invoke agent after discovery call
POST /projects/{id}/di-agent/invoke
{"trigger": "new_signal"}

# Check what's missing
GET /projects/{id}/di-agent/gaps

# Detect blind spots
GET /projects/{id}/di-agent/blind-spots

# Get complete foundation
GET /projects/{id}/foundation

# Extract specific element
POST /projects/{id}/foundation/core-pain
POST /projects/{id}/foundation/primary-persona
POST /projects/{id}/foundation/wow-moment
```

### Key Principles

1. **Trust is built by understanding first** - Don't ask for budget before showing value
2. **3:1 Rule** - 3 client signals > 10 consultant assumptions
3. **Singular focus** - THE pain, THE persona, THE moment
4. **V1 = validation, V2 = scale** - Don't build everything at once
5. **Confidence matters** - Low confidence = more discovery needed
6. **Phase 2 often unlocks AFTER prototype** - Respect the natural progression

---

## Getting Help

- **API Documentation**: `/docs` endpoint on running service
- **Agent Logs**: `GET /projects/{id}/di-agent/logs` to see reasoning history
- **Foundation Data**: `GET /projects/{id}/foundation` to see current state
- **Gaps Analysis**: `GET /projects/{id}/di-agent/gaps` for what's missing
- **Blind Spots**: `GET /projects/{id}/di-agent/blind-spots` for what you might be missing

---

**Remember**: The DI Agent is your partner in building the RIGHT thing. Let it guide you toward deep understanding before you write a single line of code. Clients remember consultants who truly understood them.
