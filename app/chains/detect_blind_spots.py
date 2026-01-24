"""Blind spot detection tool for identifying consultant and client blind spots.

Analyzes project foundation, signals, and entities to detect common patterns
that indicate blind spots in understanding or approach.
"""

import json
from typing import Any
from uuid import UUID

from openai import OpenAI

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.features import list_features
from app.db.foundation import get_project_foundation
from app.db.personas import list_personas
from app.db.signals import list_project_signals

logger = get_logger(__name__)


SYSTEM_PROMPT = """You are a senior consultant expert at detecting blind spots in discovery.

Your job is to analyze project signals and foundation to identify common blind spots that consultants and clients fall into.

CONSULTANT BLIND SPOTS (things consultants miss):
1. **Symptom as problem** - Taking stated problems at face value without digging to root cause
   - Red flag: Problem statement describes a situation, not WHY it's happening
   - Example: "Users aren't logging in daily" (symptom) vs "Users don't see value in daily login" (root cause)

2. **Missing stakeholders** - Not identifying all people affected
   - Red flag: Stakeholders mentioned in signals but not in stakeholder list
   - Red flag: Only talking to requestor, not end users

3. **Jumping to features** - Discussing solutions before understanding pain
   - Red flag: Feature list appears before pain statement
   - Red flag: Requirements doc without "why" context

4. **What over why** - Focusing on requirements without understanding motivation
   - Red flag: Lots of "what" they want, little "why" they want it
   - Red flag: No stakes or consequences mentioned

5. **Not challenging assumptions** - Accepting client's framing without question
   - Red flag: Client says "we need X" and consultant builds X without asking why
   - Red flag: No discovery questions asking "why" or "what if"

CLIENT BLIND SPOTS (things clients miss):
1. **Symptom vs root cause** - Confusing effects with causes
   - Red flag: Problem statement is "users don't do X" not "users can't achieve Y"
   - Red flag: No mention of what triggers the problem

2. **Feature first thinking** - Asking for solutions instead of expressing needs
   - Red flag: First conversation is feature requests
   - Red flag: "I need a dashboard" instead of "I need to understand X"

3. **Everything in V1** - Wanting full vision without MVP thinking
   - Red flag: Long feature list with no prioritization
   - Red flag: No mention of phases or iterations

4. **Underestimating change** - Not thinking about adoption and change management
   - Red flag: No discussion of current workarounds
   - Red flag: No mention of who needs training or communication

5. **Incomplete stakeholder map** - Not identifying everyone affected
   - Red flag: Mentions "the team" without naming roles
   - Red flag: Focus on one user type, ignoring others

DETECTION APPROACH:
1. Look for patterns in signals and foundation
2. Be specific about what you see
3. Provide evidence (quote or reference)
4. Suggest how to address it
5. Be non-judgmental - these are learning opportunities

OUTPUT FORMAT:
Return JSON with:
{
  "consultant_blind_spots": [
    {
      "type": "symptom_as_problem" | "missing_stakeholders" | "jumping_to_features" | "what_over_why" | "not_challenging",
      "severity": "high" | "medium" | "low",
      "description": "What the blind spot is",
      "evidence": "Specific example from signals",
      "suggestion": "How to address it",
      "questions_to_ask": ["Question 1", "Question 2"]
    }
  ],
  "client_blind_spots": [
    {
      "type": "symptom_vs_cause" | "feature_first" | "everything_in_v1" | "underestimating_change" | "incomplete_stakeholders",
      "severity": "high" | "medium" | "low",
      "description": "What the blind spot is",
      "evidence": "Specific example from signals",
      "suggestion": "How to reframe",
      "questions_to_ask": ["Question 1", "Question 2"]
    }
  ],
  "overall_assessment": "Brief summary of biggest risks"
}

Be honest but constructive. These insights help build better products.
"""


async def detect_blind_spots(project_id: UUID) -> dict[str, Any]:
    """
    Detect consultant and client blind spots in project discovery.

    Analyzes signals, foundation, and entities to identify common patterns
    that indicate blind spots in understanding or approach.

    Args:
        project_id: Project UUID

    Returns:
        Dict with blind spot analysis:
        {
            "consultant_blind_spots": [...],
            "client_blind_spots": [...],
            "overall_assessment": "...",
            "severity_counts": {...}
        }
    """
    settings = get_settings()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    logger.info(
        f"Detecting blind spots for project {project_id}",
        extra={"project_id": str(project_id)},
    )

    # ==========================================================================
    # 1. Load project data
    # ==========================================================================
    foundation = get_project_foundation(project_id)
    features = list_features(project_id)
    personas = list_personas(project_id)
    signals_result = list_project_signals(project_id, limit=50)
    signals = signals_result.get("signals", []) if isinstance(signals_result, dict) else []

    # ==========================================================================
    # 2. Build context for LLM analysis
    # ==========================================================================
    context_parts = []

    # Foundation state
    context_parts.append("FOUNDATION STATE:")
    if foundation:
        if foundation.core_pain:
            context_parts.append(
                f"- Core Pain: {foundation.core_pain.statement} "
                f"(confidence: {foundation.core_pain.confidence:.2f})"
            )
            if foundation.core_pain.trigger:
                context_parts.append(f"  Trigger: {foundation.core_pain.trigger}")
            if foundation.core_pain.stakes:
                context_parts.append(f"  Stakes: {foundation.core_pain.stakes}")
        else:
            context_parts.append("- Core Pain: Not yet extracted")

        if foundation.primary_persona:
            context_parts.append(
                f"- Primary Persona: {foundation.primary_persona.name} - {foundation.primary_persona.role}"
            )
        else:
            context_parts.append("- Primary Persona: Not yet extracted")

        if foundation.wow_moment:
            context_parts.append(f"- Wow Moment: {foundation.wow_moment.description[:150]}")
        else:
            context_parts.append("- Wow Moment: Not yet identified")
    else:
        context_parts.append("- Foundation: Not yet established")

    # Entity counts
    context_parts.append(f"\nENTITIES:")
    context_parts.append(f"- Features: {len(features)}")
    context_parts.append(f"- Personas: {len(personas)}")

    # Recent signals (truncated for brevity)
    context_parts.append(f"\nRECENT SIGNALS ({min(len(signals), 10)} shown):")
    for i, signal in enumerate(signals[:10], 1):
        signal_type = signal.get("signal_type", "unknown")
        signal_content = signal.get("content", signal.get("raw_text", ""))[:300]
        context_parts.append(f"\nSignal {i} ({signal_type}):")
        context_parts.append(signal_content)

    # Feature list (if any)
    if features:
        context_parts.append(f"\nFEATURES ({len(features)}):")
        for feature in features[:15]:  # Limit to 15
            feature_name = feature.get("name", "Unnamed")
            feature_desc = feature.get("description", "")[:100]
            context_parts.append(f"- {feature_name}: {feature_desc}")

    context_text = "\n".join(context_parts)

    # ==========================================================================
    # 3. Perform rule-based detection first (fast checks)
    # ==========================================================================
    rule_based_spots = _detect_rule_based_blind_spots(
        foundation, features, personas, signals
    )

    # ==========================================================================
    # 4. Use LLM for pattern detection
    # ==========================================================================
    user_prompt = f"""Analyze this project for consultant and client blind spots.

{context_text}

Look for:
1. Consultant blind spots (symptom as problem, missing stakeholders, jumping to features, what over why, not challenging)
2. Client blind spots (symptom vs cause, feature first, everything in V1, underestimating change, incomplete stakeholders)

Be specific and provide evidence from the signals/foundation.
Return JSON with consultant_blind_spots and client_blind_spots arrays."""

    try:
        response = client.chat.completions.create(
            model=settings.FACTS_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=2500,
            response_format={"type": "json_object"},
        )

        raw_output = response.choices[0].message.content
        logger.debug(f"Blind spot detection raw output: {raw_output[:500]}")

        # Parse LLM response
        parsed = json.loads(raw_output)

        consultant_spots = parsed.get("consultant_blind_spots", [])
        client_spots = parsed.get("client_blind_spots", [])
        overall = parsed.get("overall_assessment", "")

    except Exception as e:
        logger.warning(f"LLM blind spot detection failed: {e}")
        consultant_spots = []
        client_spots = []
        overall = "LLM analysis unavailable"

    # ==========================================================================
    # 5. Merge rule-based and LLM detections
    # ==========================================================================
    # Add rule-based detections to LLM results
    consultant_spots.extend(rule_based_spots["consultant"])
    client_spots.extend(rule_based_spots["client"])

    # Deduplicate by type
    seen_consultant = set()
    unique_consultant = []
    for spot in consultant_spots:
        spot_type = spot.get("type", "")
        if spot_type not in seen_consultant:
            seen_consultant.add(spot_type)
            unique_consultant.append(spot)

    seen_client = set()
    unique_client = []
    for spot in client_spots:
        spot_type = spot.get("type", "")
        if spot_type not in seen_client:
            seen_client.add(spot_type)
            unique_client.append(spot)

    # ==========================================================================
    # 6. Calculate severity counts
    # ==========================================================================
    severity_counts = {
        "consultant": {"high": 0, "medium": 0, "low": 0},
        "client": {"high": 0, "medium": 0, "low": 0},
    }

    for spot in unique_consultant:
        severity = spot.get("severity", "medium")
        severity_counts["consultant"][severity] = (
            severity_counts["consultant"].get(severity, 0) + 1
        )

    for spot in unique_client:
        severity = spot.get("severity", "medium")
        severity_counts["client"][severity] = (
            severity_counts["client"].get(severity, 0) + 1
        )

    # ==========================================================================
    # 7. Return comprehensive blind spot analysis
    # ==========================================================================
    result = {
        "consultant_blind_spots": unique_consultant,
        "client_blind_spots": unique_client,
        "overall_assessment": overall,
        "severity_counts": severity_counts,
        "total_blind_spots": len(unique_consultant) + len(unique_client),
    }

    logger.info(
        f"Detected {len(unique_consultant)} consultant and {len(unique_client)} client blind spots for project {project_id}",
        extra={
            "project_id": str(project_id),
            "consultant_spots": len(unique_consultant),
            "client_spots": len(unique_client),
        },
    )

    return result


def _detect_rule_based_blind_spots(
    foundation: Any,
    features: list[dict],
    personas: list[dict],
    signals: list[dict],
) -> dict[str, list[dict]]:
    """
    Detect blind spots using rule-based heuristics.

    Fast checks for common patterns that don't require LLM analysis.
    """
    consultant_spots = []
    client_spots = []

    # Check 1: Features created before pain defined
    if len(features) > 0 and (
        not foundation or not foundation.core_pain or foundation.core_pain.confidence < 0.5
    ):
        consultant_spots.append(
            {
                "type": "jumping_to_features",
                "severity": "high",
                "description": "Features defined before core pain is clearly understood",
                "evidence": f"{len(features)} features exist but core pain not clearly defined",
                "suggestion": "Step back and define the core pain before continuing with features",
                "questions_to_ask": [
                    "What is THE singular problem we're solving?",
                    "Why is this problem urgent right now?",
                    "What happens if we don't solve this?",
                ],
            }
        )

    # Check 2: No stakes defined (what over why)
    if foundation and foundation.core_pain:
        if not foundation.core_pain.stakes or len(foundation.core_pain.stakes) < 20:
            consultant_spots.append(
                {
                    "type": "what_over_why",
                    "severity": "medium",
                    "description": "Core pain defined but stakes (why it matters) are unclear",
                    "evidence": "Stakes field is empty or too brief",
                    "suggestion": "Dig into what's at risk if this problem isn't solved",
                    "questions_to_ask": [
                        "What's at risk if we don't solve this?",
                        "What will happen in 6 months if nothing changes?",
                        "What's this costing you today?",
                    ],
                }
            )

    # Check 3: Feature-first thinking from client
    feature_request_signals = [
        s
        for s in signals
        if any(
            keyword in (s.get("content", "") + s.get("raw_text", "")).lower()
            for keyword in ["i need a", "i want a", "we need to build", "can you add"]
        )
    ]

    if len(feature_request_signals) > 2:
        client_spots.append(
            {
                "type": "feature_first",
                "severity": "medium",
                "description": "Client focused on requesting specific features rather than expressing needs",
                "evidence": f"{len(feature_request_signals)} signals contain feature requests",
                "suggestion": "Reframe feature requests as problem statements",
                "questions_to_ask": [
                    "What problem does this feature solve for you?",
                    "What are you trying to achieve?",
                    "How do you handle this today?",
                ],
            }
        )

    # Check 4: Too many features (everything in V1)
    if len(features) > 15:
        client_spots.append(
            {
                "type": "everything_in_v1",
                "severity": "medium",
                "description": "Large number of features suggests scope creep or lack of prioritization",
                "evidence": f"{len(features)} features defined",
                "suggestion": "Work with client to identify MVP scope",
                "questions_to_ask": [
                    "Which 3 features would deliver 80% of the value?",
                    "What's the minimum needed to test the core hypothesis?",
                    "What can wait until V2?",
                ],
            }
        )

    # Check 5: Core pain looks like symptom
    if foundation and foundation.core_pain:
        symptom_keywords = [
            "users don't",
            "users aren't",
            "can't see",
            "don't have",
            "takes too long",
        ]
        pain_lower = foundation.core_pain.statement.lower()

        if any(keyword in pain_lower for keyword in symptom_keywords):
            consultant_spots.append(
                {
                    "type": "symptom_as_problem",
                    "severity": "high",
                    "description": "Core pain statement appears to describe a symptom rather than root cause",
                    "evidence": f"Statement: '{foundation.core_pain.statement}'",
                    "suggestion": "Ask 'why' multiple times to get to root cause",
                    "questions_to_ask": [
                        "Why is this happening?",
                        "What's causing this situation?",
                        "What would solve this at the root?",
                    ],
                }
            )

    # Check 6: Multiple personas but no primary persona
    if len(personas) > 2 and (
        not foundation or not foundation.primary_persona
    ):
        consultant_spots.append(
            {
                "type": "missing_stakeholders",
                "severity": "medium",
                "description": "Multiple personas identified but primary persona not clearly defined",
                "evidence": f"{len(personas)} personas but no primary persona",
                "suggestion": "Identify THE primary persona who feels the pain most",
                "questions_to_ask": [
                    "Who gets fired if this doesn't get solved?",
                    "Who feels this pain most acutely?",
                    "Whose problem is this really?",
                ],
            }
        )

    return {"consultant": consultant_spots, "client": client_spots}
