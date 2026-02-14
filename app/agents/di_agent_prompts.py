"""System prompt and tool definitions for the DI Agent.

This module contains the complete system prompt and tool definitions
for the Design Intelligence Agent that drives the two-phase gating system.
"""

# =============================================================================
# DI Agent System Prompt
# =============================================================================

DI_AGENT_SYSTEM_PROMPT = """You are a Design Intelligence Agent helping consultants create Value Paths that make clients say "holy shit, you understand me."

Your job is to DRIVE TOWARD READINESS by identifying the biggest gap in project foundation, then taking action to fill it.

# YOUR NORTH STAR

Great software starts with deep understanding:
- THE core pain (singular, not a list)
- WHO feels it most (primary persona)
- The WOW MOMENT where pain inverts to delight

Your goal: Help consultants build rock-solid foundations so they can prototype/build the RIGHT thing, not just A thing.

# TWO-PHASE GATES

## Phase 1: PROTOTYPE GATES (0-40 points)
These unlock the ability to build a clickable prototype that viscerally demonstrates value.

1. **Core Pain** (15 pts) - THE problem (singular, root cause)
   - What: Statement, trigger (why now?), stakes (what if unsolved?), who feels it
   - Why: Without this, you're solving the wrong problem
   - Satisfied: Clear pain statement, confidence ≥ 0.6

2. **Primary Persona** (10 pts) - Who we build for FIRST
   - What: Name/role, goal, pain connection, daily context
   - Why: Prototype must speak to a specific human, not "users"
   - Satisfied: Clear persona, connected to pain, confidence ≥ 0.6

3. **Wow Moment** (10 pts) - The peak where pain dissolves
   - What: Description, pain inversion, emotional impact, visual concept
   - Level 1: Core pain solved
   - Level 2: Adjacent pains addressed
   - Level 3: Unstated needs met
   - Why: Prototype must nail THIS moment, not be a feature list
   - Satisfied: Description + inversion + visual, confidence ≥ 0.5

4. **Design Preferences** (5 pts, OPTIONAL) - Visual direction
   - What: Style preferences, reference products
   - Why: Reduces iteration, feels more "right" to client
   - Satisfied: Visual style OR references exist

**Score: 0-40 = INSUFFICIENT** (working toward prototype)
**Score: 41-70 = PROTOTYPE READY** (can build clickable demo)

## Phase 2: BUILD GATES (41-100 points)
These unlock the ability to build production software with clear scope and budget.

Often unlocked AFTER prototype when client sees value and can articulate:
- "Now that I see it, here's what it's worth"
- "Here's our budget and timeline"
- "Here's what's V1 vs V2"

5. **Business Case** (20 pts) - Why invest?
   - What: Value to business, ROI framing, success KPIs, why priority
   - Why: Can't build without understanding business value
   - Satisfied: Value statement, ≥1 KPI, confidence ≥ 0.7

6. **Budget Constraints** (15 pts) - Reality check
   - What: Budget range, timeline, technical/org constraints
   - Why: Must align scope to resources
   - Satisfied: Budget + timeline, confidence ≥ 0.7

7. **Full Requirements** (15 pts) - Complete feature set
   - What: ≥5 confirmed features, well-evidenced from signals
   - Why: Need comprehensive understanding to build
   - Satisfied: ≥5 features, descriptions, good signal coverage

8. **Confirmed Scope** (10 pts) - V1 vs V2 agreement
   - What: V1 features, V2 features, client sign-off
   - Why: Prevents scope creep, sets expectations
   - Satisfied: V1 list, client confirmed, specs signed

**Score: 71-100 = BUILD READY** (can build production software)

# HOW YOU THINK: OBSERVE → THINK → DECIDE → ACT

Every time you're invoked, you follow this reasoning pattern:

## 1. OBSERVE
Look at current state:
- What gates are satisfied? What's the current score/phase?
- What signals exist? (emails, transcripts, notes, research)
- What foundation elements exist? (pain, persona, wow moment, etc.)
- What's changed since last invocation?

## 2. THINK
Analyze the biggest gap:
- Which gate is blocking progress most?
- What information is missing?
- What's the highest-leverage action?
- Are there blind spots the consultant might have?

Consider:
- **Prototype gates first** - Can't build without pain/persona/wow
- **Trust gates** - Business case, budget often unlock AFTER prototype
- **Evidence quality** - 3 client signals > 10 consultant assumptions

## 3. DECIDE
Choose ONE action:
- **Tool call**: Extract foundation element, run research, analyze gaps
- **Guidance**: Provide discovery questions for consultant to ask client
- **Stop**: When you need more signal before proceeding
- **Confirmation**: When you need consultant/client validation

The decision should move toward the NEXT MILESTONE:
- Score 0-40 → work toward prototype_ready
- Score 41-70 → work toward build_ready
- Score 71-100 → work toward complete

## 4. ACT
Execute your decision:
- If tool: Call it with appropriate parameters
- If guidance: Provide specific questions to ask
- If stop: Explain what's needed to proceed

## 5. REMEMBER (Update Memory)
After significant actions, update project memory:
- **log_decision**: When a significant choice is made (architecture, scope, pivot)
- **record_learning**: When you learn something valuable (patterns, mistakes, terminology)
- **update_project_understanding**: When your understanding of the project evolves
- **add_open_question**: When you identify a question that needs answering

Memory is your persistent knowledge about this project. It survives across invocations and helps you:
- Avoid repeating mistakes
- Build on previous decisions
- Maintain continuity of understanding
- Remember WHY decisions were made, not just WHAT was decided

## WHEN TO STOP VS CONTINUE

**STOP** (use `stop_with_guidance`) when:
- Core pain confidence < 0.4 AND fewer than 3 client signals exist
- Working on Phase 2 gates but Phase 1 gates have confidence < 0.6
- No new signals in 7+ days and foundation hasn't improved
- Client hasn't validated any elements and confidence isn't increasing

**CONTINUE** (use tools or guidance) when:
- Can extract value from existing signals (even at low confidence)
- Can provide discovery questions to guide consultant
- Can run research to fill a specific knowledge gap
- Core pain exists and next gate is achievable

**DEFAULT**: When in doubt, provide discovery questions over stopping.

# STRATEGIC FOUNDATION ENTITIES

Beyond the core gates, you have access to **Strategic Foundation** extraction tools that build a comprehensive understanding of:

## Business Drivers (KPIs, Pain Points, Goals)
Strategic motivations behind the project:
- **KPIs**: Metrics the client cares about (e.g., "Reduce support tickets 40%", "Increase conversion 15%")
  - Enrichment: baseline_value, target_value, measurement_method, tracking_frequency
- **Pain Points**: Specific problems causing friction (may feed into Core Pain)
  - Enrichment: severity, frequency, affected_users, business_impact, current_workaround
- **Goals**: High-level objectives (e.g., "Launch in Q2", "Enter SMB market")
  - Enrichment: goal_timeframe, success_criteria, dependencies, owner

**When to extract**: When signals mention metrics, problems, or objectives. These provide context for business_case and help validate core_pain.

## Competitors
Products/companies the client compares themselves to:
- Market position, pricing models, target audience
- What makes competitors unique (informs wow_moment differentiation)
- Feature comparisons (informs requirements)

**When to extract**: When signals mention other products, competitive analysis, or "like X but with Y". Helps with wow_moment (what makes us different) and business_case (why we'll win).

## Stakeholders
People involved in or affected by the project:
- Roles, priorities, concerns, engagement level
- Decision authority, approval requirements
- Engagement strategy, risk if disengaged

**When to extract**: When signals mention team members, executives, end users. Helps identify hidden stakeholders and understand political landscape (affects budget_constraints and confirmed_scope).

## Risks
Potential threats to project success:
- Types: technical, business, market, team, timeline, budget, compliance, security, operational, strategic
- Severity, likelihood, impact, mitigation strategies
- Detection signals (early warning signs)

**When to extract**: When signals mention concerns, blockers, uncertainties. Proactively identifies what could go wrong (critical for business_case and budget_constraints).

## How Strategic Foundation Complements Gates

Strategic entities are **not gates** - they don't block progress. They're **enrichment layers** that:
- Provide evidence for business_case (KPIs show ROI, risks show stakes)
- Inform wow_moment (competitors show what to differentiate from)
- Support budget_constraints (stakeholder landscape shows decision makers)
- Strengthen core_pain (pain points provide specific examples)

**Use strategically**:
- Don't extract all strategic entities just because you can
- Extract when they'll directly help satisfy a gate
- Prioritize gates over strategic foundation
- Use strategic foundation to build confidence in gates

## Strategic Foundation Tools

Available tools:
- `extract_business_drivers` - Extract KPIs, pain points, and goals from signals
- `enrich_business_driver` - Deep dive on a specific driver (measurement details, severity, timeline)
- `extract_competitors` - Identify competitive landscape from signals
- `enrich_competitor` - Research a specific competitor (market position, pricing, features)
- `extract_stakeholders` - Map people involved in the project
- `extract_risks` - Identify potential threats from signals

**Tool usage pattern**:
1. Extract first (creates entities from signals)
2. Enrich selectively (deep dive on most important entities)
3. Link to gates (use insights to improve gate confidence)

# CONSTRAINTS

**You CANNOT:**
- Make up client requirements (must come from signals or client conversation)
- Skip prototype gates to work on build gates
- Confirm scope without client involvement
- Proceed when you lack confidence in core pain

**You MUST:**
- Be honest about confidence levels
- Call out when you're inferring vs. have direct evidence
- Suggest questions that will GET you to higher confidence
- Protect the consultant from building the wrong thing

**CRITICAL:**
- Phase 2 gates often unlock AFTER prototype
- Don't push for budget/timeline before client sees value
- Trust is built by understanding, then comes investment

# CONFIDENCE CALIBRATION

Different gates have different baseline confidence expectations:

**Prototype Gates (Should have 0.6+ confidence to satisfy):**
- Core Pain: 0.6+ = reasonably inferred from signals
- Primary Persona: 0.6+ = role and pain connection evident
- Wow Moment: 0.5+ acceptable (hypothesis is normal)
- Design Preferences: Optional, any confidence

**Build Gates (Often start low, increase post-prototype):**
- Business Case: 0.4-0.7 common pre-prototype
- Budget Constraints: 0.3-0.5 common pre-prototype
- Full Requirements: N/A (feature count based)
- Confirmed Scope: N/A (confirmation based)

Expect Phase 2 gates to have lower confidence early, then increase after prototype demonstrates value and builds trust.

# BLIND SPOTS TO WATCH FOR

## Consultant Blind Spots
- **Assuming vs. validating**: Did they actually ask the client, or assume?
- **Solution bias**: Jumping to features before understanding pain
- **Avoiding hard questions**: Not asking about budget/timeline/constraints
- **Feature creep**: Adding "nice to haves" instead of focusing on core pain

## Client Blind Spots
- **Symptom vs. root cause**: Stating symptoms instead of THE problem
- **Vague value**: "Better UX" instead of specific business outcomes
- **Scope explosion**: Everything is "must have" for V1
- **Hidden stakeholders**: Key decision makers not in the conversation

When you detect blind spots:
1. Don't just accept stated requirements
2. Probe deeper with questions
3. Challenge assumptions gently
4. Redirect to fundamentals (pain → persona → wow)

# EVOLUTION PHILOSOPHY: V1 vs V2

**V1 (Prototype):**
- Nail THE core pain for THE primary persona
- One clear wow moment
- Good enough to get "holy shit, you understand me"
- Deliberately incomplete - shows direction, not destination

**V2 (Build):**
- Expand to adjacent personas
- Add Level 2 & 3 wow moments
- Full feature set with confirmed scope
- Production-ready with business case

Don't let the client over-scope V1. The prototype's job is to BUILD TRUST and VALIDATE DIRECTION, not to be production software.

# YOUR REASONING TRACE

Always output your complete reasoning:
- **Observation**: What you see in current state
- **Thinking**: Your analysis of the biggest gap
- **Decision**: What action you chose and why
- **Action**: The tool/guidance/stop you're executing

This transparency helps consultants learn and trust your judgment.

# REMEMBER

You are here to help consultants be GREAT at discovery and foundation-building. Your job is to:
1. Identify what's missing
2. Suggest how to get it
3. Prevent building the wrong thing
4. Move toward readiness systematically

Be proactive, be honest about confidence, and always drive toward THE core pain, THE primary persona, and THE wow moment.
"""

# =============================================================================
# DI Agent Tool Definitions
# =============================================================================

DI_AGENT_TOOLS = [
    {
        "name": "extract_core_pain",
        "description": "Extract THE core pain from project signals - the singular root problem driving this project",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project UUID",
                },
                "signal_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional: specific signal IDs to analyze (or all if omitted)",
                },
                "depth": {
                    "type": "string",
                    "enum": ["surface", "standard", "deep"],
                    "description": "Analysis depth: surface (explicit only), standard (explicit + inferred), deep (deep analysis)",
                    "default": "standard",
                },
            },
            "required": ["project_id"],
        },
        "useful_when": [
            "Core pain gate is not satisfied",
            "Need to understand THE root problem",
            "Have signals from client (emails, transcripts, notes)",
            "Starting new project and need foundation",
        ],
        "not_useful_when": [
            "No signals exist yet - ask consultant to capture client conversations first",
            "Core pain already satisfied with high confidence",
            "Working on build gates - core pain should already be solid",
        ],
        "affects_gates": ["core_pain"],
        "confidence_impact": "High - directly extracts and validates core pain",
        "typical_confidence": "0.6-0.9 depending on signal quality",
    },
    {
        "name": "extract_primary_persona",
        "description": "Extract THE primary persona - the person who feels the core pain most and who we build for FIRST",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project UUID",
                },
            },
            "required": ["project_id"],
        },
        "useful_when": [
            "Primary persona gate is not satisfied",
            "Core pain exists but persona is unclear",
            "Have signals mentioning users/roles",
            "Need to identify who we're building for",
        ],
        "not_useful_when": [
            "Core pain doesn't exist yet - extract that first",
            "Primary persona already satisfied with high confidence",
            "No user/role mentions in signals",
        ],
        "affects_gates": ["primary_persona"],
        "confidence_impact": "High - directly extracts and validates persona",
        "typical_confidence": "0.6-0.9 depending on how clearly persona is discussed",
        "prerequisites": ["core_pain should exist"],
    },
    {
        "name": "identify_wow_moment",
        "description": "Identify THE wow moment - the peak where the primary persona's pain dissolves into delight",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project UUID",
                },
            },
            "required": ["project_id"],
        },
        "useful_when": [
            "Wow moment gate is not satisfied",
            "Core pain and persona exist",
            "Need to define the prototype's peak moment",
            "Ready to think about solution direction",
        ],
        "not_useful_when": [
            "Core pain or persona missing - need those first",
            "Wow moment already satisfied",
            "Too early - still working on understanding the problem",
        ],
        "affects_gates": ["wow_moment"],
        "confidence_impact": "Medium-High - identifies solution direction",
        "typical_confidence": "0.5-0.8 (can be hypothesis at 0.5)",
        "prerequisites": ["core_pain should exist", "primary_persona should exist"],
    },
    {
        "name": "extract_business_case",
        "description": "Extract the business case - value to business, ROI, KPIs, and why this is a priority investment",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project UUID",
                },
            },
            "required": ["project_id"],
        },
        "useful_when": [
            "Business case gate is not satisfied",
            "Signals discuss business value, ROI, or metrics",
            "Client has seen prototype and can articulate value",
            "Moving from prototype to build phase",
        ],
        "not_useful_when": [
            "Still working on prototype gates - too early",
            "No business value discussion in signals yet",
            "Business case already satisfied",
        ],
        "affects_gates": ["business_case"],
        "confidence_impact": "Medium - often inferred if not explicit",
        "typical_confidence": "0.4-0.9 (can be low if inferred from pain/stakes)",
        "note": "Build Gate - often unlocked AFTER prototype when client sees value",
    },
    {
        "name": "extract_budget_constraints",
        "description": "Extract budget range, timeline, and technical/organizational constraints",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project UUID",
                },
            },
            "required": ["project_id"],
        },
        "useful_when": [
            "Budget constraints gate is not satisfied",
            "Signals discuss budget, timeline, or constraints",
            "Client has built trust and is ready for money conversation",
            "Moving from prototype to build phase",
        ],
        "not_useful_when": [
            "Still working on prototype gates - too early",
            "No budget/timeline discussion in signals yet",
            "Budget constraints already satisfied",
        ],
        "affects_gates": ["budget_constraints"],
        "confidence_impact": "Medium - often sparse early, explicit later",
        "typical_confidence": "0.2-0.9 (can be very low if not yet discussed)",
        "note": "Build Gate - often unlocked by trust from prototype",
    },
    {
        "name": "run_foundation",
        "description": "Extract company info, business drivers, and competitors from signals using strategic foundation analysis",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project UUID",
                },
            },
            "required": ["project_id"],
        },
        "useful_when": [
            "Need broad strategic context",
            "Understanding company/industry background",
            "Extracting business drivers and competitive landscape",
            "Enriching overall foundation understanding",
        ],
        "not_useful_when": [
            "Need specific gate extraction - use specific extractors instead",
            "No signals exist yet",
            "Already have good strategic context",
        ],
        "affects_gates": ["core_pain", "primary_persona", "business_case"],
        "confidence_impact": "Medium - provides context for other gates",
        "typical_confidence": "Varies - depends on signal richness",
    },
    {
        "name": "run_research",
        "description": "Run deep research on specific topics using web search and synthesis",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project UUID",
                },
                "research_question": {
                    "type": "string",
                    "description": "Specific question to research",
                },
                "depth": {
                    "type": "string",
                    "enum": ["quick", "standard", "deep"],
                    "description": "Research depth",
                    "default": "standard",
                },
            },
            "required": ["project_id", "research_question"],
        },
        "useful_when": [
            "Need external information (industry context, competitors, best practices)",
            "Validating assumptions about market/industry",
            "Understanding technical feasibility",
            "Gap in knowledge that web research can fill",
        ],
        "not_useful_when": [
            "Information should come from client (their pain, their business)",
            "Already have sufficient context",
            "Need client-specific data, not general knowledge",
        ],
        "affects_gates": ["varies - depends on research topic"],
        "confidence_impact": "Low-Medium - supplements but doesn't replace client signal",
        "typical_confidence": "Adds context, doesn't directly satisfy gates",
    },
    {
        "name": "run_discover",
        "description": "Run data-first discovery intelligence pipeline: SerpAPI source mapping, PDL company/competitor enrichment, Firecrawl web scraping, Bright Data reviews, and Sonnet-powered business driver synthesis. Every fact traces to a real URL with a real quote. Costs ~$1.05/run, takes ~60-90s.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project UUID",
                },
                "company_name": {
                    "type": "string",
                    "description": "Company name to research (defaults to project company)",
                },
                "company_website": {
                    "type": "string",
                    "description": "Company website URL (optional)",
                },
                "industry": {
                    "type": "string",
                    "description": "Industry for market research (optional)",
                },
                "focus_areas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional focus areas (e.g., 'competitor pricing', 'user pain points')",
                },
            },
            "required": ["project_id"],
        },
        "useful_when": [
            "Starting a new project and need comprehensive market/competitive context",
            "Need real evidence (URLs, quotes) for business drivers — not AI-generated slop",
            "Want to profile competitors with real firmographic data from PDL",
            "Need user voice data from G2, Capterra, Reddit",
            "Want to populate business drivers with evidence chains",
        ],
        "not_useful_when": [
            "Already have rich signals from client conversations",
            "Only need to extract from existing signals (use run_foundation)",
            "Budget is a concern (costs ~$1.05 per run)",
        ],
        "affects_gates": ["core_pain", "primary_persona", "business_case", "wow_moment"],
        "confidence_impact": "High - produces evidence-backed business drivers with real URLs",
        "typical_confidence": "High for market/competitive context, medium for client-specific needs",
    },
    {
        "name": "suggest_discovery_questions",
        "description": "Generate specific discovery questions for consultant to ask the client to fill gaps",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project UUID",
                },
                "focus_area": {
                    "type": "string",
                    "enum": [
                        "core_pain",
                        "primary_persona",
                        "wow_moment",
                        "business_case",
                        "budget_constraints",
                        "general",
                    ],
                    "description": "Which area to focus questions on",
                },
            },
            "required": ["project_id", "focus_area"],
        },
        "useful_when": [
            "Need more client signal to satisfy a gate",
            "Confidence is low due to sparse signals",
            "Consultant needs guidance on what to ask client",
            "Ready to guide consultant toward next conversation",
        ],
        "not_useful_when": [
            "Can extract from existing signals - do that first",
            "No consultant to ask questions (fully automated flow)",
            "Gate already satisfied with high confidence",
        ],
        "affects_gates": ["varies - helps consultant gather better signal"],
        "confidence_impact": "Indirect - questions help get better signal",
        "typical_confidence": "N/A - this is guidance, not extraction",
    },
    {
        "name": "analyze_gaps",
        "description": "Analyze what's missing across all gates and identify the highest-priority gaps to address",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project UUID",
                },
            },
            "required": ["project_id"],
        },
        "useful_when": [
            "Need to understand overall foundation health",
            "Multiple gates have issues - need to prioritize",
            "Consultant asks 'what should I focus on?'",
            "Starting work on a project",
        ],
        "not_useful_when": [
            "Already know the specific gap to address",
            "Working on a specific gate extraction",
            "All gates satisfied",
        ],
        "affects_gates": ["all - provides gap overview"],
        "confidence_impact": "N/A - analysis tool, not extraction",
        "typical_confidence": "N/A - identifies gaps, doesn't fill them",
    },
    {
        "name": "stop_with_guidance",
        "description": "Stop the agent loop and provide guidance to the consultant on what's needed next",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Why stopping (e.g., 'Need more client signals', 'Waiting for prototype feedback')",
                },
                "what_would_help": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of things that would help proceed",
                },
                "recommended_next": {
                    "type": "string",
                    "description": "Recommended next action for consultant",
                },
            },
            "required": ["reason", "what_would_help", "recommended_next"],
        },
        "useful_when": [
            "Insufficient signals to proceed",
            "Need client input before continuing",
            "Waiting for external milestone (prototype, feedback)",
            "Reached a natural stopping point",
        ],
        "not_useful_when": [
            "Can still make progress with existing tools",
            "Have clear next action available",
        ],
        "affects_gates": ["none - stops progress"],
        "confidence_impact": "N/A - stops rather than improves",
        "typical_confidence": "N/A",
    },
    # Strategic Foundation Tools
    {
        "name": "extract_business_drivers",
        "description": "Extract business drivers (KPIs, pain points, goals) from project signals",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project UUID",
                },
                "signal_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional: specific signal IDs to analyze (or all if omitted)",
                },
                "enrich_top_drivers": {
                    "type": "boolean",
                    "description": "Whether to enrich the top 5 drivers with detailed analysis",
                    "default": False,
                },
            },
            "required": ["project_id"],
        },
        "useful_when": [
            "Need to understand business metrics and objectives",
            "Building business_case - KPIs show ROI potential",
            "Strengthening core_pain - pain points provide specific examples",
            "Signals mention metrics, problems, or goals",
        ],
        "not_useful_when": [
            "No signals exist yet",
            "Working on prototype gates - gates are higher priority",
            "Already have comprehensive business drivers",
        ],
        "affects_gates": ["business_case", "core_pain"],
        "confidence_impact": "Medium - provides business context",
        "typical_confidence": "0.5-0.8 depending on signal explicitness",
    },
    {
        "name": "enrich_business_driver",
        "description": "Enrich a specific business driver with detailed measurement/severity/timeline analysis",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project UUID",
                },
                "driver_id": {
                    "type": "string",
                    "description": "Business driver UUID to enrich",
                },
                "depth": {
                    "type": "string",
                    "enum": ["surface", "standard", "deep"],
                    "description": "Analysis depth",
                    "default": "standard",
                },
            },
            "required": ["project_id", "driver_id"],
        },
        "useful_when": [
            "Need detailed metrics for a key KPI (baseline, target, measurement)",
            "Quantifying a critical pain point (severity, impact, cost)",
            "Understanding goal timeline and success criteria",
            "Have a specific driver that needs deeper analysis",
        ],
        "not_useful_when": [
            "Driver doesn't exist yet - extract first",
            "Driver already has detailed enrichment",
            "Not relevant to current gate satisfaction",
        ],
        "affects_gates": ["business_case"],
        "confidence_impact": "Medium - adds detail to existing driver",
        "typical_confidence": "Enhances existing confidence, doesn't create new",
    },
    {
        "name": "extract_competitors",
        "description": "Extract competitor references from project signals to understand competitive landscape",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project UUID",
                },
                "signal_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional: specific signal IDs to analyze (or all if omitted)",
                },
                "enrich_top_competitors": {
                    "type": "boolean",
                    "description": "Whether to enrich the top 5 competitors with market analysis",
                    "default": False,
                },
            },
            "required": ["project_id"],
        },
        "useful_when": [
            "Understanding competitive positioning for wow_moment differentiation",
            "Building business_case - need to show why we'll win",
            "Signals mention other products, competitors, or comparisons",
            "Client says 'like X but with Y'",
        ],
        "not_useful_when": [
            "No competitive mentions in signals",
            "Working on core_pain - focus on problem, not competition",
            "Already have comprehensive competitor list",
        ],
        "affects_gates": ["wow_moment", "business_case"],
        "confidence_impact": "Low-Medium - informs differentiation",
        "typical_confidence": "0.4-0.7 depending on how much competitors are discussed",
    },
    {
        "name": "enrich_competitor",
        "description": "Enrich a specific competitor with market research (position, pricing, features, audience)",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project UUID",
                },
                "competitor_id": {
                    "type": "string",
                    "description": "Competitor reference UUID to enrich",
                },
                "depth": {
                    "type": "string",
                    "enum": ["surface", "standard", "deep"],
                    "description": "Analysis depth (deep includes web scraping - not yet implemented)",
                    "default": "standard",
                },
            },
            "required": ["project_id", "competitor_id"],
        },
        "useful_when": [
            "Need detailed competitive intel on a key competitor",
            "Understanding pricing models for business_case",
            "Identifying feature gaps for wow_moment differentiation",
            "Client specifically asks about a competitor",
        ],
        "not_useful_when": [
            "Competitor doesn't exist yet - extract first",
            "Competitor already has detailed enrichment",
            "Not relevant to current gate satisfaction",
        ],
        "affects_gates": ["wow_moment", "business_case"],
        "confidence_impact": "Low-Medium - adds competitive context",
        "typical_confidence": "Based on available signals, not web research yet",
        "note": "Web scraping for deep enrichment not yet implemented",
    },
    {
        "name": "extract_stakeholders",
        "description": "Extract stakeholders from project signals to map the people landscape",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project UUID",
                },
                "signal_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional: specific signal IDs to analyze (or all if omitted)",
                },
                "enrich_top_stakeholders": {
                    "type": "boolean",
                    "description": "Whether to enrich the top 10 stakeholders with engagement analysis",
                    "default": False,
                },
            },
            "required": ["project_id"],
        },
        "useful_when": [
            "Understanding decision-making structure for budget_constraints",
            "Identifying who needs to approve scope for confirmed_scope",
            "Signals mention team members, executives, or end users",
            "Detecting hidden stakeholders or political landscape",
        ],
        "not_useful_when": [
            "No people mentioned in signals yet",
            "Working on prototype gates - less critical early",
            "Already have comprehensive stakeholder map",
        ],
        "affects_gates": ["budget_constraints", "confirmed_scope"],
        "confidence_impact": "Medium - reveals decision makers",
        "typical_confidence": "0.5-0.8 depending on how stakeholders are discussed",
        "note": "Helps identify who can approve budget and scope",
    },
    {
        "name": "extract_risks",
        "description": "Extract project risks from signals to identify potential threats and blockers",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project UUID",
                },
                "signal_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional: specific signal IDs to analyze (or all if omitted)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max signals to process",
                    "default": 10,
                },
            },
            "required": ["project_id"],
        },
        "useful_when": [
            "Understanding threats for business_case (what could go wrong)",
            "Building realistic budget_constraints (risk mitigation costs)",
            "Signals mention concerns, blockers, uncertainties, or dependencies",
            "Client expresses worry about specific issues",
        ],
        "not_useful_when": [
            "No concerns mentioned in signals yet",
            "Working on basic prototype gates - risks less critical early",
            "Already have comprehensive risk register",
        ],
        "affects_gates": ["business_case", "budget_constraints"],
        "confidence_impact": "Medium - highlights what could derail project",
        "typical_confidence": "0.5-0.8 depending on explicitness of concerns",
        "note": "10 risk types: technical, business, market, team, timeline, budget, compliance, security, operational, strategic",
    },
    # Requirements Gap Analysis Tools
    {
        "name": "analyze_requirements_gaps",
        "description": "Analyze the current requirements model (features, personas, VP steps) for logical gaps, missing references, and inconsistencies",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project UUID",
                },
                "focus_areas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional: specific areas to focus on (e.g., 'persona_coverage', 'vp_flow', 'feature_references', 'orphaned_entities')",
                },
            },
            "required": ["project_id"],
        },
        "useful_when": [
            "After uploading new requirements documents",
            "After making significant changes to features/personas/VP",
            "When preparing for client review",
            "When the project feels incomplete or disconnected",
            "Checking if value path flows logically",
            "Verifying features are properly linked to personas",
        ],
        "not_useful_when": [
            "Project has no entities yet - need features/personas first",
            "Just starting discovery phase",
            "Working on prototype gates - focus on core pain/persona first",
        ],
        "affects_gates": ["full_requirements"],
        "confidence_impact": "Medium - identifies gaps but doesn't fill them",
        "typical_confidence": "N/A - analysis tool",
    },
    {
        "name": "propose_entity_updates",
        "description": "Generate proposals to fill identified requirement gaps by creating or updating features, personas, or VP steps",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project UUID",
                },
                "gap_analysis": {
                    "type": "object",
                    "description": "Output from analyze_requirements_gaps tool",
                },
                "max_proposals": {
                    "type": "integer",
                    "description": "Maximum number of proposals to generate (default: 5)",
                    "default": 5,
                },
                "entity_types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["feature", "persona", "vp_step"],
                    },
                    "description": "Types of entities to propose (default: all)",
                },
                "auto_create_proposals": {
                    "type": "boolean",
                    "description": "Whether to create proposals in DB for consultant review (default: true)",
                    "default": True,
                },
            },
            "required": ["project_id", "gap_analysis"],
        },
        "useful_when": [
            "After running analyze_requirements_gaps and finding gaps",
            "When gaps have been identified that need to be addressed",
            "Wanting to improve requirement completeness systematically",
            "Need to propose new features based on persona pain points",
            "Need to link VP steps to appropriate features",
        ],
        "not_useful_when": [
            "No gap analysis has been run - run analyze_requirements_gaps first",
            "Project is in final stages with locked requirements",
            "Gaps are about missing client information - use discovery questions instead",
        ],
        "affects_gates": ["full_requirements", "confirmed_scope"],
        "confidence_impact": "High - creates proposals that can improve requirements",
        "typical_confidence": "Varies - proposals need consultant review",
        "note": "Proposals are created for consultant review, not auto-applied",
    },
    # ==========================================================================
    # Memory Tools - Persistent Project Memory
    # ==========================================================================
    {
        "name": "read_project_memory",
        "description": "Read the project memory document containing accumulated understanding, decisions, learnings, and open questions",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project UUID",
                },
            },
            "required": ["project_id"],
        },
        "useful_when": [
            "Starting work on a project to understand history and context",
            "Need to recall previous decisions and their rationale",
            "Want to check what learnings apply to current situation",
            "Looking for open questions that need answers",
        ],
        "not_useful_when": [
            "Project memory doesn't exist yet (new project)",
        ],
        "affects_gates": [],
        "confidence_impact": "None - read-only",
        "typical_confidence": "N/A",
    },
    {
        "name": "update_project_understanding",
        "description": "Update the project understanding section of memory with new insights about the project, client, or domain",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project UUID",
                },
                "understanding": {
                    "type": "string",
                    "description": "New or updated understanding of the project (replaces previous)",
                },
                "client_profile_updates": {
                    "type": "object",
                    "description": "Optional: Updates to client profile (e.g., communication_style, domain_vocabulary)",
                },
            },
            "required": ["project_id", "understanding"],
        },
        "useful_when": [
            "Gained new insight about what the project is really about",
            "Learned something important about the client",
            "Discovered domain-specific terminology or patterns",
            "Understanding has evolved based on new signals",
        ],
        "not_useful_when": [
            "No new understanding to record",
            "Update is minor and not worth persisting",
        ],
        "affects_gates": [],
        "confidence_impact": "None - memory update",
        "typical_confidence": "N/A",
    },
    {
        "name": "log_decision",
        "description": "Log a significant decision with full rationale so we never lose the 'why' behind choices",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project UUID",
                },
                "title": {
                    "type": "string",
                    "description": "Short title for the decision (e.g., 'Chose mobile-first approach')",
                },
                "decision": {
                    "type": "string",
                    "description": "What was decided",
                },
                "rationale": {
                    "type": "string",
                    "description": "WHY this decision was made - the reasoning",
                },
                "alternatives_considered": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "option": {"type": "string"},
                            "why_rejected": {"type": "string"},
                        },
                    },
                    "description": "Other options that were considered and why they weren't chosen",
                },
                "decided_by": {
                    "type": "string",
                    "enum": ["client", "consultant", "di_agent"],
                    "description": "Who made this decision",
                },
                "decision_type": {
                    "type": "string",
                    "enum": ["feature", "architecture", "scope", "pivot", "terminology", "process"],
                    "description": "Type of decision",
                },
            },
            "required": ["project_id", "title", "decision", "rationale"],
        },
        "useful_when": [
            "A significant choice was made that affects project direction",
            "Client confirmed or rejected a proposal",
            "Architecture or approach decision was made",
            "Scope was changed or prioritized",
            "A pivot occurred based on new information",
        ],
        "not_useful_when": [
            "Decision is trivial or doesn't affect future work",
            "Already logged this decision",
        ],
        "affects_gates": [],
        "confidence_impact": "None - memory update",
        "typical_confidence": "N/A",
    },
    {
        "name": "record_learning",
        "description": "Record a learning - what worked, what didn't, patterns discovered, or terminology learned",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project UUID",
                },
                "title": {
                    "type": "string",
                    "description": "Short title for the learning",
                },
                "context": {
                    "type": "string",
                    "description": "What happened - the situation that led to this learning",
                },
                "learning": {
                    "type": "string",
                    "description": "What we learned - the insight or pattern",
                },
                "learning_type": {
                    "type": "string",
                    "enum": ["insight", "mistake", "pattern", "terminology"],
                    "description": "Type of learning",
                },
                "domain": {
                    "type": "string",
                    "enum": ["client", "domain", "process", "technical"],
                    "description": "What domain this learning applies to",
                },
            },
            "required": ["project_id", "title", "context", "learning"],
        },
        "useful_when": [
            "Made a mistake and want to avoid repeating it",
            "Discovered a pattern that works for this client/project",
            "Learned domain-specific terminology",
            "Found a better process or approach",
            "Client feedback taught us something",
        ],
        "not_useful_when": [
            "Learning is trivial or obvious",
            "Already recorded this learning",
        ],
        "affects_gates": [],
        "confidence_impact": "None - memory update",
        "typical_confidence": "N/A",
        "note": "Mistakes are especially valuable - they prevent repeated errors",
    },
    {
        "name": "update_strategy",
        "description": "Update the current strategy and working hypotheses",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project UUID",
                },
                "focus": {
                    "type": "string",
                    "description": "What we're currently focused on and why",
                },
                "hypotheses": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Working hypotheses we're testing",
                },
                "next_actions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Planned next actions",
                },
            },
            "required": ["project_id", "focus"],
        },
        "useful_when": [
            "Strategy needs to be updated based on new information",
            "Entering a new phase of the project",
            "Forming hypotheses that need validation",
            "Planning the next steps",
        ],
        "not_useful_when": [
            "Strategy hasn't changed",
            "Just minor tweaks that don't need recording",
        ],
        "affects_gates": [],
        "confidence_impact": "None - memory update",
        "typical_confidence": "N/A",
    },
    {
        "name": "add_open_question",
        "description": "Add an open question that needs to be answered",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project UUID",
                },
                "question": {
                    "type": "string",
                    "description": "The question that needs answering",
                },
                "why_important": {
                    "type": "string",
                    "description": "Why this question matters",
                },
                "affects_gate": {
                    "type": "string",
                    "description": "Which gate this question relates to (if any)",
                },
            },
            "required": ["project_id", "question"],
        },
        "useful_when": [
            "Identified a gap in knowledge that blocks progress",
            "Need client input on something specific",
            "Discovered an ambiguity that needs clarification",
        ],
        "not_useful_when": [
            "Question is already recorded",
            "Can answer the question from existing signals",
        ],
        "affects_gates": [],
        "confidence_impact": "None - memory update",
        "typical_confidence": "N/A",
    },
    {
        "name": "synthesize_value_path",
        "description": "Synthesize the optimal value path for the Canvas View prototype. "
        "Analyzes canvas actors, workflows, must-have features, and business drivers to "
        "produce a linear golden path of high-value steps the prototype must implement.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project UUID",
                },
                "focus": {
                    "type": "string",
                    "description": "Optional focus area or constraint for the synthesis",
                },
            },
            "required": ["project_id"],
        },
        "useful_when": [
            "Canvas actors have been selected and workflows are defined",
            "Project has must-have features and business drivers identified",
            "Consultant wants to generate the prototype blueprint",
        ],
        "not_useful_when": [
            "No canvas actors are selected yet",
            "Project has insufficient discovery data",
        ],
        "affects_gates": ["prototype_readiness"],
        "confidence_impact": "high",
        "typical_confidence": "0.8",
    },
    {
        "name": "check_discovery_readiness",
        "description": "Check how ready the project is for discovery intelligence. Returns a readiness score, what data exists, what's missing, and actionable suggestions. Pure data query — no LLM, no cost.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project UUID",
                },
            },
            "required": ["project_id"],
        },
        "useful_when": [
            "Before running /discover to check if the project has enough data",
            "Consultant asks 'what should I do before running discovery?'",
            "Need to assess if discovery will be effective or wasteful",
            "Want to know what data is missing to improve discovery results",
        ],
        "not_useful_when": [
            "Already running discovery — too late to check",
            "Project has no company name set — discovery can't run regardless",
        ],
        "affects_gates": [],
        "confidence_impact": "N/A — assessment tool, not extraction",
        "typical_confidence": "N/A",
    },
]

# =============================================================================
# Helper Functions
# =============================================================================


def get_tool_by_name(tool_name: str) -> dict | None:
    """Get tool definition by name.

    Args:
        tool_name: Name of the tool

    Returns:
        Tool definition dict or None if not found
    """
    for tool in DI_AGENT_TOOLS:
        if tool["name"] == tool_name:
            return tool
    return None


def get_tools_for_gate(gate_name: str) -> list[dict]:
    """Get all tools that can affect a specific gate.

    Args:
        gate_name: Name of the gate (e.g., "core_pain")

    Returns:
        List of tool definitions that affect this gate
    """
    tools = []
    for tool in DI_AGENT_TOOLS:
        affects = tool.get("affects_gates", [])
        if gate_name in affects or gate_name in str(affects):
            tools.append(tool)
    return tools


def get_extraction_tools() -> list[dict]:
    """Get all extraction tools (not guidance/analysis tools).

    Returns:
        List of extraction tool definitions
    """
    extraction_tool_names = [
        "extract_core_pain",
        "extract_primary_persona",
        "identify_wow_moment",
        "extract_business_case",
        "extract_budget_constraints",
        "run_foundation",
        "run_research",
        # Strategic Foundation extraction tools
        "extract_business_drivers",
        "enrich_business_driver",
        "extract_competitors",
        "enrich_competitor",
        "extract_stakeholders",
        "extract_risks",
        # Requirements gap tools (can propose changes)
        "propose_entity_updates",
    ]
    return [tool for tool in DI_AGENT_TOOLS if tool["name"] in extraction_tool_names]


def get_guidance_tools() -> list[dict]:
    """Get all guidance/analysis tools (not extraction).

    Returns:
        List of guidance tool definitions
    """
    guidance_tool_names = [
        "suggest_discovery_questions",
        "analyze_gaps",
        "stop_with_guidance",
        # Requirements gap analysis (read-only analysis)
        "analyze_requirements_gaps",
    ]
    return [tool for tool in DI_AGENT_TOOLS if tool["name"] in guidance_tool_names]
